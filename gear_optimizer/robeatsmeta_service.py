from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.parsing import env_flag, env_int, env_str
from gear_optimizer.data.database import get_best_loadouts

logger = logging.getLogger(__name__)

# Stateless HTTP front-end over the canonical optimizer pipeline.
#
# The website owns identity, credits, sharing and result persistence; this service only solves.
#   GET  /songs     -> the official chart list (from Data/ headers) the website picker chooses from
#   POST /optimize  -> solve one chart (official `targetSongId` OR custom `chartText`) and return
#                      its full T5 baseline leaderboard (top 51 base + 51 FG by hash), in the exact
#                      shape `get_best_loadouts` yields for the catalog. The website persists this
#                      verbatim into a per-job evolution.db-format file and replays it across tiers /
#                      modes / ranks / colors / timing via the same on-demand re-score path the
#                      catalog uses on evolution.db, so an optimizer result is a peer of a catalog
#                      meta card.
#
# Every solve runs in a throwaway per-request dir with the song source, run state and output DB
# redirected via the ROBEATSMETA_OPTIMIZER_* path overrides, so requests never touch the catalog
# bin/ queues, the Data/ catalog, or evolution.db.
#
# The service is a concurrent pool: ThreadingHTTPServer handles requests in parallel, and a bounded
# semaphore caps concurrent solves (default 10). Each solve spawns main.py as a subprocess; the
# subprocesses share MetaFinder's canonical timeline, exact Base context, and FG frontier caches. A valid uploaded or
# previously-built entry is reused forever; a cache miss is built by the canonical runtime owner and
# persisted for every later solve.

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "Data"
GEAR_DIR = DATA_ROOT / "Gear"
DIFFICULTIES = ("Easy", "Normal", "Hard")

# Global solve pool: caps concurrent optimizer subprocesses. The GPU is the bottleneck (one song
# at a time on the Vulkan device), but exact song-context preparation + chart parse + DB write
# overlaps with the GPU work of the previous song, so a small pool keeps both fed.
_SOLVE_POOL_SIZE = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_POOL", 10))
_SOLVE_SEMAPHORE = threading.Semaphore(_SOLVE_POOL_SIZE)

# Memory-headroom admission (a hardware memory bound, not a perf flag). The semaphore caps how many
# solves may be *scheduled*, but each solve subprocess (main.py + its GPU context + worker pool) is
# memory-heavy, and on a small-RAM box enough concurrent solves exhaust RAM and thrash/OOM (measured
# on a 16 GB unified-memory Mac: 2 concurrent solves drove free memory to ~70 MB). So gate the START
# of each *additional* concurrent solve on real available memory: the first concurrent solve always
# runs (progress guarantee, never deadlocks), and a further one only starts once at least
# ROBEATSMETA_OPTIMIZER_SERVICE_MIN_FREE_MB is free -- otherwise it waits for a running solve to
# finish. This makes effective concurrency track the box's memory regardless of the pool size.
_MIN_FREE_BYTES = max(0, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_MIN_FREE_MB", 3000)) * 1024 * 1024
_admission = threading.Condition()
_active_solves = 0


@dataclass(frozen=True)
class _OfficialSongCatalog:
    songs: tuple[dict[str, str], ...]
    paths_by_song_id: dict[str, Path]


_OFFICIAL_CATALOG_LOCK = threading.Lock()
_OFFICIAL_CATALOG_CACHE_KEY: tuple[tuple[str, Path], ...] | None = None
_OFFICIAL_CATALOG_CACHE: _OfficialSongCatalog | None = None


def _available_bytes() -> int:
    import psutil

    return int(psutil.virtual_memory().available)


def _acquire_solve_slot() -> None:
    """Block until it is memory-safe to start another solve subprocess."""
    global _active_solves
    with _admission:
        while _active_solves > 0 and _MIN_FREE_BYTES and _available_bytes() < _MIN_FREE_BYTES:
            _admission.wait(timeout=1.0)  # re-check as running solves free memory
        _active_solves += 1


def _release_solve_slot() -> None:
    global _active_solves
    with _admission:
        _active_solves = max(0, _active_solves - 1)
        _admission.notify_all()

# Canonical persistent frontier caches. Website solves must use the same artifacts as direct
# MetaFinder runs and deployment prebuilds; a website-specific cache creates split authority and
# makes an uploaded production cache invisible to live requests.
_TIMELINE_FRONTIER_CACHE_DIR = REPO_ROOT / "bin" / "timeline_frontier_cache"
_EXACT_BASE_SONG_CONTEXT_CACHE_DIR = REPO_ROOT / "bin" / "exact_base_song_context_cache"
_FG_RESPONSE_FRONTIER_CACHE_DIR = REPO_ROOT / "bin" / "fg_response_frontier_cache"
_TIMELINE_FRONTIER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_EXACT_BASE_SONG_CONTEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_FG_RESPONSE_FRONTIER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Concurrent writes to the shared frontier cache are safe: both writers (timeline frontier grid and
# FG response cache) write to a unique per-thread temp file and atomically os.replace() it into
# place, so a partial file is never observed and the last writer wins on identical content.

# Body-size cap for /optimize: reject anything absurd with 413 so an oversized body can't be read
# into memory. Sized to fit the worst-case translated chart the website accepts (up to 200k hit
# objects, holds doubling rows, JSON-escaped) with margin; the website also caps chartText below
# this before sending. Belongs behind loopback/private + bearer auth regardless.
_MAX_BODY_BYTES = max(1024, env_int("ROBEATSMETA_OPTIMIZER_MAX_BODY_BYTES", 32 * 1024 * 1024))

# Hard wall-clock cap on a single solve subprocess: on timeout the whole process group is killed
# (so main.py's GPU/worker children don't linger) and the request fails. Must exceed a real solve.
_SOLVE_TIMEOUT_S = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_TIMEOUT_S", 30 * 60))

@dataclass
class _InFlightSolve:
    done: threading.Event = field(default_factory=threading.Event)
    result: list[dict[str, Any]] | None = None
    error: BaseException | None = None

    def wait(self) -> list[dict[str, Any]]:
        self.done.wait()
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise RuntimeError("optimizer solve completed without a result")
        return self.result


_INFLIGHT_SOLVES_LOCK = threading.Lock()
_INFLIGHT_SOLVES: dict[str, _InFlightSolve] = {}


def _claim_job_solve(job: str) -> tuple[_InFlightSolve, bool]:
    """Return the in-flight solve for a job and whether this caller owns running it."""
    with _INFLIGHT_SOLVES_LOCK:
        existing = _INFLIGHT_SOLVES.get(job)
        if existing is not None:
            return existing, False
        state = _InFlightSolve()
        _INFLIGHT_SOLVES[job] = state
        return state, True


def _release_job_solve(job: str, state: _InFlightSolve) -> None:
    with _INFLIGHT_SOLVES_LOCK:
        if _INFLIGHT_SOLVES.get(job) is state:
            del _INFLIGHT_SOLVES[job]


def _prebuild_catalog_frontier_caches() -> None:
    """Attempt to fill missing canonical cache entries for the official catalog at deployment.

    This runs in the service process after it starts listening. Existing uploaded entries are
    manifest/disk hits; only missing or key-invalidated songs build. A failure is logged loudly but
    does not remove live serviceability because the isolated solve path runs the same builders on a
    cache miss.
    """
    try:
        import numpy as np

        from gear_optimizer.core.config import load_config, load_paths_cache
        from gear_optimizer.core.constants import PATHS
        from gear_optimizer.data.csv_parser import read_table
        from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
        from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work

        cfg = load_config()
        paths = load_paths_cache()
        stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
        ref_arrays = build_ref_arrays_from_stats(stats_table, dtype=np.float32)
        song_paths = tuple(
            str(chart)
            for _difficulty, folder in _official_song_directories()
            for chart in sorted(folder.glob("*.txt"))
        )
        run_startup_cpu_work(
            cfg=cfg,
            song_queue=song_paths,
            ref_arrays=ref_arrays,
            data_root=DATA_ROOT,
        )
    except Exception:
        logger.exception(
            "catalog frontier cache prebuild failed; live requests will retry missing entries"
        )


def _maintain_provisioned_fg_frontier_cache() -> None:
    """Apply destination-native maintenance to an externally copied FG pool without building."""
    try:
        from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
            maintain_provisioned_fg_response_frontier_cache,
        )

        maintain_provisioned_fg_response_frontier_cache()
    except Exception:
        logger.exception("provisioned FG frontier cache maintenance failed")


def _run_catalog_frontier_cache_startup() -> None:
    if env_flag("ROBEATSMETA_SKIP_CATALOG_PREBUILD"):
        _maintain_provisioned_fg_frontier_cache()
    else:
        _prebuild_catalog_frontier_caches()


class RequestError(ValueError):
    """A bad request from the caller -> HTTP 400 (an internal failure -> 500)."""


class RequestTooLarge(RequestError):
    """The request body exceeds the configured cap -> HTTP 413."""


# --- official chart catalog --------------------------------------------------

def _read_full_header(path: Path) -> dict[str, str]:
    """Read all tab-separated header fields from a chart file (up to 'Song Data')."""
    header: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line == "Song Data":
                    break
                if "\t" in line:
                    key, _, value = line.partition("\t")
                    header[key.strip()] = value.strip()
    except OSError:
        pass
    return header


def _official_song_directories() -> tuple[tuple[str, Path], ...]:
    """Return the exact chart directories backing the API's official-song catalog.

    Direct MetaFinder runs retain the native ``Data/{difficulty}`` layout. The website service
    may instead select WebPort's canonical replay library at the deployment boundary; once that
    root is explicitly configured, every expected difficulty directory is required.
    """
    configured = env_str("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", "").strip()
    if not configured:
        return tuple((difficulty, DATA_ROOT / difficulty) for difficulty in DIFFICULTIES)

    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = REPO_ROOT / root
    root = root.resolve()
    directories = tuple(
        (difficulty, root / f"{difficulty} Songs") for difficulty in DIFFICULTIES
    )
    missing = [str(folder) for _difficulty, folder in directories if not folder.is_dir()]
    if missing:
        raise RuntimeError(
            "ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR must contain WebPort's "
            f"Easy Songs, Normal Songs, and Hard Songs directories; missing: {', '.join(missing)}"
        )
    return directories


def _official_catalog_cache_key() -> tuple[tuple[str, Path], ...]:
    return _official_song_directories()


def clear_official_song_catalog_cache() -> None:
    """Clear the process-local official song catalog cache used by tests and controlled reloads."""
    global _OFFICIAL_CATALOG_CACHE, _OFFICIAL_CATALOG_CACHE_KEY
    with _OFFICIAL_CATALOG_LOCK:
        _OFFICIAL_CATALOG_CACHE = None
        _OFFICIAL_CATALOG_CACHE_KEY = None


def _build_official_song_catalog() -> _OfficialSongCatalog:
    songs: list[dict[str, str]] = []
    paths_by_song_id: dict[str, Path] = {}
    for difficulty, diff_dir in _official_song_directories():
        if not diff_dir.is_dir():
            continue
        for chart in sorted(diff_dir.glob("*.txt")):
            h = _read_full_header(chart)
            song_id = str(h.get("Song Name") or "").strip()
            if not song_id:
                continue
            title = str(h.get("Title") or "").strip()
            for d in ("Hard", "Normal", "Easy"):
                suffix = f" ({d})"
                if title.endswith(suffix):
                    title = title[: -len(suffix)]
                    break
            audio_raw = str(h.get("Audio Asset ID") or "").strip()
            songs.append({
                "songId": song_id,
                "difficulty": difficulty,
                "primaryElement": str(h.get("Primary Color") or "").strip(),
                "secondaryElement": str(h.get("Secondary Color") or "").strip(),
                "title": title,
                "artist": str(h.get("Artist") or "").strip(),
                "audioId": audio_raw.replace("rbxassetid://", "") if audio_raw else "",
                "coverImageId": str(h.get("Cover Image ID") or "").strip(),
            })
            paths_by_song_id.setdefault(song_id, chart)
    return _OfficialSongCatalog(songs=tuple(songs), paths_by_song_id=paths_by_song_id)


def _official_song_catalog() -> _OfficialSongCatalog:
    global _OFFICIAL_CATALOG_CACHE, _OFFICIAL_CATALOG_CACHE_KEY
    cache_key = _official_catalog_cache_key()
    with _OFFICIAL_CATALOG_LOCK:
        if _OFFICIAL_CATALOG_CACHE is not None and _OFFICIAL_CATALOG_CACHE_KEY == cache_key:
            return _OFFICIAL_CATALOG_CACHE
        catalog = _build_official_song_catalog()
        _OFFICIAL_CATALOG_CACHE = catalog
        _OFFICIAL_CATALOG_CACHE_KEY = cache_key
        return catalog


def list_official_songs() -> list[dict[str, str]]:
    """The official chart list for the website picker, read from the catalog Data/ headers.

    Every chart file's header is read in full so the picker gets title, artist, audioId, and
    coverImageId directly from the source — no catalog or evolution.db dependency. The difficulty
    suffix is stripped from the title so the frontend collapses all difficulties of a song into
    one entry (same title+artist = same family key).
    """
    return [dict(song) for song in _official_song_catalog().songs]


def find_official_chart(song_id: str) -> Path:
    """Return the official chart file whose `Song Name` header equals `song_id` exactly.

    The website picks from `list_official_songs()` and echoes back the exact `songId`, so an exact
    match is the contract -- no fuzzy/substring matching.
    """
    target = str(song_id or "").strip()
    if not target:
        raise RequestError("missing targetSongId")
    chart = _official_song_catalog().paths_by_song_id.get(target)
    if chart is not None:
        return chart
    raise RequestError(f"no official chart matches {target!r}")


# --- solve -------------------------------------------------------------------

def _job_slug(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("_")
    return slug or "job"


def _normalize_timing_mode(value: Any) -> str:
    mode = str(value or "perfect_window").strip().lower()
    if mode not in {"perfect_window", "zero_ms"}:
        raise RequestError(f"unknown timingMode {value!r}")
    return mode


def _normalize_chart(chart_text: str, song_name: str, timing_mode: str) -> str:
    """Force Song Name, Difficulty, and timing mode so the isolated chart matches the request.

    The file name is the unique job slug. The Song Name header is the semantic song identity:
    Mini Ascension song targets and the output DB rows key off it.
    """
    out: list[str] = []
    have_name = have_diff = have_timing_mode = False
    for line in chart_text.splitlines():
        if line.startswith("Song Name\t") and not have_name:
            out.append(f"Song Name\t{song_name}")
            have_name = True
        elif line.startswith("Difficulty\t") and not have_diff:
            out.append("Difficulty\tHard")
            have_diff = True
        elif line.startswith("Timing Mode\t") and not have_timing_mode:
            out.append(f"Timing Mode\t{timing_mode}")
            have_timing_mode = True
        else:
            out.append(line)
    prefix: list[str] = []
    if not have_name:
        prefix.append(f"Song Name\t{song_name}")
    if not have_diff:
        prefix.append("Difficulty\tHard")
    if not have_timing_mode:
        prefix.append(f"Timing Mode\t{timing_mode}")
    return "\n".join(prefix + out) + "\n"


def chart_text_for_request(request: dict[str, Any]) -> str:
    """The chart to solve: custom `chartText` when present, else the official `targetSongId`."""
    return chart_text_and_result_song_name_for_request(
        request,
        fallback_name=_job_slug(request.get("jobId") or request.get("resultKey")),
    )[0]


def chart_text_and_result_song_name_for_request(request: dict[str, Any], *, fallback_name: str) -> tuple[str, str]:
    """Return the chart text plus the song_name key expected in the result DB."""
    fallback = _job_slug(fallback_name)
    chart_text = str(request.get("chartText") or "").strip()
    if chart_text:
        return chart_text + "\n", fallback
    song_id = str(request.get("targetSongId") or "").strip()
    if song_id:
        return find_official_chart(song_id).read_text(encoding="utf-8"), song_id
    raise RequestError("request must include targetSongId or chartText")


def _service_run_root() -> Path:
    override = env_str("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", "").strip()
    return Path(override) if override else (REPO_ROOT / "bin" / "robeatsmeta_api_runs")


def _kill_process_group(proc: subprocess.Popen) -> None:
    """SIGKILL the solve subprocess and its whole process group so no GPU/worker child lingers."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError, AttributeError):
        try:
            proc.kill()  # fallback (non-POSIX, or the group is already gone)
        except OSError:
            pass


def _solve_isolated(
    job: str,
    chart_text: str,
    result_song_name: str,
    repeats: int,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """Run the canonical optimizer pipeline once in a throwaway per-job workspace."""
    work = _service_run_root() / job
    shutil.rmtree(work, ignore_errors=True)
    data_dir = work / "Data"
    (data_dir / "Hard").mkdir(parents=True, exist_ok=True)
    shutil.copytree(GEAR_DIR, data_dir / "Gear")  # real files; discovery does not follow symlinks
    (data_dir / "Hard" / f"{job}.txt").write_text(
        _normalize_chart(chart_text, result_song_name, _normalize_timing_mode(timing_mode)),
        encoding="utf-8",
    )
    # The isolated Data dir holds exactly this one chart, so "process discovered charts once"
    # (empty Song_Name + LoopForever off) solves it; a fresh bin means no resume/candidate queue.
    (work / "config.ini").write_text(
        "[CalculateSong]\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        "IgnoreResumeQueue = true\n"
        f"SongRepeats = {repeats}\n"
        "SongQueueLimit = 1\n",
        encoding="utf-8",
    )
    db_path = work / "result.db"
    env = {
        **os.environ,
        "EVOLUTION_DB_PATH": str(db_path),
        "METAFINDER_CONFIG_PATH": str(work / "config.ini"),
        "ROBEATSMETA_OPTIMIZER_DATA_DIR": str(data_dir),
        "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(work / "bin"),
        "TIMELINE_FRONTIER_CACHE_DIR": str(_TIMELINE_FRONTIER_CACHE_DIR),
        "EXACT_BASE_SONG_CONTEXT_CACHE_DIR": str(_EXACT_BASE_SONG_CONTEXT_CACHE_DIR),
        "FG_RESPONSE_FRONTIER_CACHE_DIR": str(_FG_RESPONSE_FRONTIER_CACHE_DIR),
    }
    with _SOLVE_SEMAPHORE:
        _acquire_solve_slot()  # memory-headroom gate: hold here until it's safe to add a solve
        try:
            # start_new_session -> the solve gets its own process group, so on timeout we can reap
            # the whole tree (main.py + its GPU/worker children) instead of orphaning them.
            proc = subprocess.Popen(
                [sys.executable, str(REPO_ROOT / "main.py"), "run"],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                out, err = proc.communicate(timeout=_SOLVE_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                _kill_process_group(proc)
                proc.communicate()
                raise RuntimeError(f"optimizer timed out after {_SOLVE_TIMEOUT_S}s")
            if proc.returncode != 0:
                tail = " | ".join((err or out or "").strip().splitlines()[-20:])
                raise RuntimeError(f"optimizer exited {proc.returncode}: {tail}")
            entries = get_best_loadouts(
                result_song_name, limit=LOADOUTS_PER_SONG_LIMIT, team_buff="T5", db_path=str(db_path)
            )
            if not entries:
                raise RuntimeError("optimizer produced no T5 loadout")
            return entries
        finally:
            _release_solve_slot()
            shutil.rmtree(work, ignore_errors=True)


def solve(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Solve one chart in an isolated per-request workspace and return its full T5 leaderboard.

    The returned list is the merged top-N base + FG leaderboard (ranked by score / fg_score, deduped
    by loadout_hash) exactly as `get_best_loadouts` yields for the catalog. The website writes this
    verbatim into a per-job evolution.db-format file via `save_loadouts_batch`, so every downstream
    replay (any tier / mode / rank / color / timing) runs through the catalog's own on-demand re-score
    path (`build_team_buff_tier_db_batches`) and produces a byte-identical SongBuild.
    """
    job = _job_slug(request.get("jobId") or request.get("resultKey"))
    chart_text, result_song_name = chart_text_and_result_song_name_for_request(request, fallback_name=job)
    repeats = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_REPEATS", 1))
    timing_mode = _normalize_timing_mode(request.get("timingMode"))
    state, owner = _claim_job_solve(job)
    if not owner:
        logger.info("joining in-flight optimizer solve for job %s", job)
        return state.wait()
    try:
        state.result = _solve_isolated(job, chart_text, result_song_name, repeats, timing_mode)
        return state.result
    except BaseException as exc:
        state.error = exc
        raise
    finally:
        state.done.set()
        _release_job_solve(job, state)


# --- HTTP --------------------------------------------------------------------

class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/2.0"

    def _authorized(self) -> bool:
        token = env_str("ROBEATSMETA_OPTIMIZER_API_TOKEN", "").strip()
        return not token or self.headers.get("Authorization") == f"Bearer {token}"

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/songs":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            self._send(HTTPStatus.OK, {"songs": list_official_songs()})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary: surface as 500
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/optimize":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            request = self._read_json()
            loadouts = solve(request)
            self._send(HTTPStatus.OK, {"jobId": request.get("jobId"), "loadouts": loadouts})
        except RequestTooLarge as exc:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
        except RequestError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary: optimizer failure -> 500
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = self.headers.get("Content-Length")
        if not length or not length.isdigit():
            raise RequestError("missing Content-Length")
        if int(length) > _MAX_BODY_BYTES:
            raise RequestTooLarge(f"request body exceeds {_MAX_BODY_BYTES} bytes")
        try:
            request = json.loads(self.rfile.read(int(length)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(f"invalid JSON body: {exc}") from exc
        if not isinstance(request, dict):
            raise RequestError("request body must be a JSON object")
        return request

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[robeatsmeta-service] " + (fmt % args) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer service")
    parser.add_argument("--host", default=env_str("ROBEATSMETA_OPTIMIZER_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=env_int("ROBEATSMETA_OPTIMIZER_API_PORT", 8765))
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, int(args.port)), RoBeatsMetaServiceHandler)
    server.daemon_threads = True
    # Service-mode external boundary: when the FG/timeline caches are provisioned externally (e.g.
    # built on a beefier host and copied in), skip the deployment-time catalog prebuild so the box
    # does not grind rebuilding what is about to be dropped in. Serving is unaffected -- the isolated
    # solve path still builds any genuinely missing entry on demand.
    if env_flag("ROBEATSMETA_SKIP_CATALOG_PREBUILD"):
        print(
            "[robeatsmeta-service] catalog frontier cache prebuild SKIPPED "
            "(ROBEATSMETA_SKIP_CATALOG_PREBUILD): maintaining the provisioned FG pool; "
            "missing entries build on demand.",
            flush=True,
        )
        logger.info("catalog frontier cache prebuild skipped (ROBEATSMETA_SKIP_CATALOG_PREBUILD)")
    prebuild = threading.Thread(
        target=_run_catalog_frontier_cache_startup,
        name="catalog-frontier-cache-startup",
        daemon=True,
    )
    prebuild.start()
    print(
        f"[robeatsmeta-service] listening on http://{args.host}:{args.port}"
        f" (pool={_SOLVE_POOL_SIZE}, timeline_cache={_TIMELINE_FRONTIER_CACHE_DIR},"
        f" exact_base_context_cache={_EXACT_BASE_SONG_CONTEXT_CACHE_DIR},"
        f" fg_cache={_FG_RESPONSE_FRONTIER_CACHE_DIR})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
