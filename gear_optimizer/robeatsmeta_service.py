from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
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
from urllib.parse import urlsplit

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.parsing import env_int, env_str
from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.frontier_auth import FrontierRequestAuthenticator
from gear_optimizer.frontier_server import FrontierDistributionState, FrontierServerMaintainer

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
# subprocesses share MetaFinder's canonical timeline and FG frontier caches. A valid uploaded or
# previously-built entry is reused forever; a cache miss is built by the canonical runtime owner and
# persisted for every later solve.

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "Data"
GEAR_DIR = DATA_ROOT / "Gear"
DIFFICULTIES = ("Easy", "Normal", "Hard")

# Global solve pool: caps concurrent optimizer subprocesses. The GPU is the bottleneck (one song
# at a time on the Vulkan device), but the CPU-side frontier build + chart parse + DB write
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
_SERVICE_DRAINING_FOR_UPDATE = False


class ServiceNotReady(RuntimeError):
    pass


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
        if _SERVICE_DRAINING_FOR_UPDATE:
            raise ServiceNotReady("optimizer service is activating a new MetaFinder revision")
        while _active_solves > 0 and _MIN_FREE_BYTES and _available_bytes() < _MIN_FREE_BYTES:
            _admission.wait(timeout=1.0)  # re-check as running solves free memory
            if _SERVICE_DRAINING_FOR_UPDATE:
                raise ServiceNotReady("optimizer service is activating a new MetaFinder revision")
        _active_solves += 1


def _release_solve_slot() -> None:
    global _active_solves
    with _admission:
        _active_solves = max(0, _active_solves - 1)
        _admission.notify_all()

# Canonical persistent frontier caches for official charts. Custom charts override both paths with
# their disposable per-job workspace; official solves keep the same authority as direct MetaFinder
# runs and deployment prebuilds.
_TIMELINE_FRONTIER_CACHE_DIR = REPO_ROOT / "bin" / "timeline_frontier_cache"
_FG_RESPONSE_FRONTIER_CACHE_DIR = REPO_ROOT / "bin" / "fg_response_frontier_cache"
_TIMELINE_FRONTIER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_FG_RESPONSE_FRONTIER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_FRONTIER_DISTRIBUTION = FrontierDistributionState()
_FRONTIER_AUTH = FrontierRequestAuthenticator()
_AUTHORITATIVE_PUBLICATION_READY = threading.Event()

# Concurrent writes to the shared frontier cache are safe: both writers (timeline frontier grid and
# FG response cache) write to a unique per-thread temp file and atomically os.replace() it into
# place, so a partial file is never observed and the last writer wins on identical content.

# Body-size cap for /optimize: reject anything absurd with 413 so an oversized body can't be read
# into memory. Sized above the website's 4k optimizer-event translated-chart limit with JSON-escape
# margin; the website also caps chartText before sending. Belongs behind loopback/private + bearer
# auth regardless.
_MAX_BODY_BYTES = max(1024, env_int("ROBEATSMETA_OPTIMIZER_MAX_BODY_BYTES", 32 * 1024 * 1024))
_MAX_CUSTOM_CHART_EVENTS = max(1, env_int("ROBEATSMETA_OPTIMIZER_MAX_CUSTOM_EVENTS", 4_000))

# Hard wall-clock cap on a single solve subprocess: on timeout the whole process group is killed
# (so main.py's GPU/worker children don't linger) and the request fails. Must exceed a real solve.
_SOLVE_TIMEOUT_S = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_TIMEOUT_S", 30 * 60))

# Reasoning effort: the website lets a user spend extra credits to make the optimizer search harder.
# The chosen level scales the GA search knobs that most directly raise the odds of reaching the true
# optimum -- how deep the GA evolves (GA_SearchDepth) and how many independent starting populations
# it searches in parallel (GA_MultiStart, ~free since it runs concurrently on the GPU). Scaling is
# linear in the multiplier; "default" reproduces the stock config defaults exactly (nothing is
# written, so config.py's own fallbacks apply). This levels/multipliers table is a cross-repo
# contract mirrored by the website (optimizer_job_contract.py).
_REASONING_MULTIPLIERS: dict[str, float] = {"default": 1.0, "strong": 2.0, "max": 4.0}
# Bases mirror the canonical config defaults: GA_SearchDepth fallback (gear_optimizer/core/config.py)
# and GA_MULTI_RUNS_DEFAULT (gear_optimizer/core/constants.py). "default" reasoning => these exact
# values, i.e. no behavior change from before this knob existed.
_REASONING_BASE_SEARCH_DEPTH = 125
_REASONING_BASE_MULTI_START = 3


def _normalize_reasoning(value: Any) -> str:
    level = str(value or "").strip().lower()
    return level if level in _REASONING_MULTIPLIERS else "default"


def _reasoning_search_knobs(reasoning: str) -> tuple[int, int]:
    """(GA_SearchDepth, GA_MultiStart) for a reasoning level -- ceil(base x multiplier), linear."""
    import math

    mult = _REASONING_MULTIPLIERS[_normalize_reasoning(reasoning)]
    depth = int(math.ceil(_REASONING_BASE_SEARCH_DEPTH * mult))
    multi_start = int(math.ceil(_REASONING_BASE_MULTI_START * mult))
    return depth, multi_start


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


def _prebuild_frontier_caches(data_root: Path) -> dict[str, set[str]]:
    """Build every missing canonical cache before a Data revision becomes downloadable."""
    import numpy as np

    from gear_optimizer.core.config import load_config
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work

    stats_path = data_root / "Gear" / "Stats.txt"
    stats_table = read_table(str(stats_path))
    ref_arrays = build_ref_arrays_from_stats(stats_table, dtype=np.float32)
    song_paths = tuple(
        str(chart)
        for difficulty in DIFFICULTIES
        for chart in sorted((data_root / difficulty).glob("*.txt"))
    )
    if not song_paths:
        raise RuntimeError(f"frontier server Data revision has no song charts: {data_root}")
    run_startup_cpu_work(
        cfg=load_config(),
        song_queue=song_paths,
        ref_arrays=ref_arrays,
        data_root=data_root,
        build_missing=True,
        authorize_destructive_rotation=True,
    )
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
        _build_manifest_plan as build_fg_manifest_plan,
        _manifest_path as fg_manifest_path,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _surface_sidecar_paths,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import (
        _build_manifest_plan as build_timeline_manifest_plan,
        _manifest_path as timeline_manifest_path,
    )

    def recorded_files(plan, manifest_path: Path, cache_root: Path) -> set[str]:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, dict) or plan.missing_paths:
            raise RuntimeError("frontier prebuild did not produce a complete publication manifest")
        files: set[str] = set()
        for key in set(plan.key_by_norm_path.values()):
            entry = entries.get(key)
            cache_file = Path(str(entry.get("cache_file") or "")) if isinstance(entry, dict) else Path()
            if cache_file.parent.resolve() != cache_root.resolve() or not cache_file.is_file():
                raise RuntimeError(f"frontier manifest references an invalid cache file: {cache_file}")
            files.add(cache_file.name)
        return files

    timeline_plan = build_timeline_manifest_plan(song_paths, ref_arrays, persist_validated_entries=False)
    timeline_files = recorded_files(
        timeline_plan,
        timeline_manifest_path(),
        _TIMELINE_FRONTIER_CACHE_DIR,
    )
    fg_plan = build_fg_manifest_plan(
        song_paths,
        ref_arrays,
        stat_keys=all_response_stat_keys(),
        persist_validated_entries=False,
    )
    fg_bundles = recorded_files(fg_plan, fg_manifest_path(), _FG_RESPONSE_FRONTIER_CACHE_DIR)
    fg_files = set(fg_bundles)
    for bundle_name in fg_bundles:
        for sidecar in _surface_sidecar_paths(_FG_RESPONSE_FRONTIER_CACHE_DIR / bundle_name):
            if not sidecar.is_file():
                raise RuntimeError(f"FG frontier bundle is missing a sidecar: {sidecar}")
            fg_files.add(sidecar.name)
    return {"timeline": timeline_files, "fg": fg_files}


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
        # Never swallow silently: an empty header makes the catalog builder skip the chart, so a
        # permissions/disk hiccup would quietly shrink /songs with no trace.
        logger.warning("unreadable chart header, chart will be missing from the catalog: %s", path)
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


def _activate_published_data(data_root: Path) -> None:
    global DATA_ROOT, GEAR_DIR, _SERVICE_DRAINING_FOR_UPDATE
    root = Path(data_root).resolve()
    if not (root / "Gear").is_dir():
        raise RuntimeError(f"published MetaFinder Data has no Gear directory: {root}")
    DATA_ROOT = root
    GEAR_DIR = root / "Gear"
    clear_official_song_catalog_cache()
    with _admission:
        _SERVICE_DRAINING_FOR_UPDATE = False
        _admission.notify_all()
    _AUTHORITATIVE_PUBLICATION_READY.set()


def _prepare_server_code_update() -> None:
    global _SERVICE_DRAINING_FOR_UPDATE
    _AUTHORITATIVE_PUBLICATION_READY.clear()
    with _admission:
        _SERVICE_DRAINING_FOR_UPDATE = True
        while _active_solves:
            _admission.wait(timeout=1.0)
    _OFFICIAL_CATALOG_LOCK.acquire()


def _finish_server_code_update(*, aborted: bool) -> None:
    global _SERVICE_DRAINING_FOR_UPDATE
    if _OFFICIAL_CATALOG_LOCK.locked():
        _OFFICIAL_CATALOG_LOCK.release()
    if aborted:
        with _admission:
            _SERVICE_DRAINING_FOR_UPDATE = False
            _admission.notify_all()
        _AUTHORITATIVE_PUBLICATION_READY.set()


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
    # Length cap: the slug becomes a directory name, so a multi-KB jobId would otherwise hit
    # ENAMETOOLONG at mkdir and surface as a 500 instead of a client error.
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("_")[:80]
    # This slug is joined onto the run root and shutil.rmtree'd; a pure-dot slug ("." / ".." / "...")
    # would escape the per-request sandbox and wipe <repo>/bin (the frontier caches). Slashes are
    # already neutralized above, so rejecting all-dots is the only remaining traversal to close.
    if not slug or slug.strip(".") == "":
        return "job"
    return slug


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


def _validate_custom_chart_event_limit(chart_text: str) -> None:
    in_song_data = False
    event_count = 0
    for raw in chart_text.splitlines():
        line = raw.strip()
        if not in_song_data:
            in_song_data = line == "Song Data"
            continue
        if not line:
            continue
        event_count += 1
        if event_count > _MAX_CUSTOM_CHART_EVENTS:
            raise RequestError(
                f"custom chart exceeds {_MAX_CUSTOM_CHART_EVENTS} replay events"
            )
    if not in_song_data:
        # A chart with no "Song Data" marker would count zero events, pass this gate at up to the
        # 32 MB body cap, and waste a full subprocess spawn before failing loudly in the child.
        raise RequestError("custom chart has no Song Data section")


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
    reasoning: str = "default",
    timing_mode: str = "perfect_window",
    ephemeral_frontiers: bool = False,
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
    # Reasoning effort scales the GA search knobs. Only write them above "default" so the default
    # path stays byte-identical to before this knob existed (config.py's own fallbacks apply).
    level = _normalize_reasoning(reasoning)
    reasoning_lines = ""
    if level != "default":
        depth, multi_start = _reasoning_search_knobs(level)
        reasoning_lines = f"GA_SearchDepth = {depth}\nGA_MultiStart = {multi_start}\n"
    # The isolated Data dir holds exactly this one chart, so "process discovered charts once"
    # (empty Song_Name + LoopForever off) solves it; a fresh bin means no resume/candidate queue.
    (work / "config.ini").write_text(
        "[CalculateSong]\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        "IgnoreResumeQueue = true\n"
        f"SongRepeats = {repeats}\n"
        "SongQueueLimit = 1\n"
        f"{reasoning_lines}",
        encoding="utf-8",
    )
    db_path = work / "result.db"
    timeline_cache_dir = work / "bin" / "timeline_frontier_cache" if ephemeral_frontiers else _TIMELINE_FRONTIER_CACHE_DIR
    fg_cache_dir = work / "bin" / "fg_response_frontier_cache" if ephemeral_frontiers else _FG_RESPONSE_FRONTIER_CACHE_DIR
    env = {
        **os.environ,
        "EVOLUTION_DB_PATH": str(db_path),
        "METAFINDER_CONFIG_PATH": str(work / "config.ini"),
        "ROBEATSMETA_OPTIMIZER_DATA_DIR": str(data_dir),
        "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(work / "bin"),
        "TIMELINE_FRONTIER_CACHE_DIR": str(timeline_cache_dir),
        "FG_RESPONSE_FRONTIER_CACHE_DIR": str(fg_cache_dir),
        # Pin service mode for the child regardless of how THIS process was started: without it a
        # solve child re-enables the frontier self-update client and can network-sync + os.execv
        # itself mid-job (the launchd wrapper happens to export this, but nothing else does).
        "ROBEATSMETA_OPTIMIZER_SERVICE_MODE": "1",
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
    if str(request.get("chartText") or "").strip():
        _validate_custom_chart_event_limit(chart_text)
    repeats = max(1, env_int("ROBEATSMETA_OPTIMIZER_SERVICE_REPEATS", 1))
    reasoning = _normalize_reasoning(request.get("reasoning"))
    timing_mode = _normalize_timing_mode(request.get("timingMode"))
    # Dedup on the job AND the solve inputs: two concurrent requests whose ids merely slug
    # identically (or both fall back to "job") must never silently join and hand the second
    # caller a leaderboard computed for a different chart/reasoning/timing.
    solve_key = job + ":" + hashlib.sha256(
        f"{reasoning}|{timing_mode}|{repeats}|{chart_text}".encode("utf-8")
    ).hexdigest()[:16]
    state, owner = _claim_job_solve(solve_key)
    if not owner:
        logger.info("joining in-flight optimizer solve for job %s", job)
        return state.wait()
    try:
        state.result = _solve_isolated(
            job,
            chart_text,
            result_song_name,
            repeats,
            reasoning,
            timing_mode,
            ephemeral_frontiers=bool(str(request.get("chartText") or "").strip()),
        )
        return state.result
    except BaseException as exc:
        state.error = exc
        raise
    finally:
        state.done.set()
        _release_job_solve(solve_key, state)


# --- HTTP --------------------------------------------------------------------

class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/3.0"
    # Socket timeout for reads AND writes: without it a client that stalls mid-body (or mid-bundle
    # download) pins a daemon thread and its fds for the life of the process. Remote standalone
    # installs talk to this service over real networks; stalls happen.
    timeout = 60

    def _authorized(self) -> bool:
        token = env_str("ROBEATSMETA_OPTIMIZER_API_TOKEN", "").strip()
        supplied = self.headers.get("Authorization", "")
        return not token or hmac.compare_digest(supplied, f"Bearer {token}")

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/metafinder/v1/"):
            self._serve_frontier_distribution(parsed.path, parsed.query)
            return
        if parsed.path.rstrip("/") != "/songs" or parsed.query:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if not _AUTHORITATIVE_PUBLICATION_READY.is_set():
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "frontier_publication_not_ready"})
            return
        try:
            self._send(HTTPStatus.OK, {"songs": list_official_songs()})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary: surface as 500
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _serve_frontier_distribution(self, path: str, query: str) -> None:
        if query or not _FRONTIER_AUTH.authorize(method="GET", path=path, headers=self.headers):
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if path == "/metafinder/v1/manifest":
            body = _FRONTIER_DISTRIBUTION.manifest_bytes()
            if body is None:
                self._send(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "frontier_publication_not_ready"},
                )
                return
            self._send_bytes(
                HTTPStatus.OK,
                body,
                content_type="application/json",
                cache_control="private, no-store",
            )
            return
        parts = path.strip("/").split("/")
        if len(parts) != 5 or parts[:3] != ["metafinder", "v1", "bundles"]:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        bundle = _FRONTIER_DISTRIBUTION.bundle_info(parts[3], parts[4])
        if bundle is None:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        bundle_path, digest = bundle
        try:
            size = int(bundle_path.stat().st_size)
            self.send_response(int(HTTPStatus.OK))
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(size))
            self.send_header("X-Content-SHA256", digest)
            self.send_header("Cache-Control", "private, max-age=31536000, immutable")
            self.end_headers()
            with bundle_path.open("rb") as handle:
                shutil.copyfileobj(handle, self.wfile, length=1024 * 1024)
        except OSError:
            logger.exception("failed to stream frontier bundle %s", bundle_path)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/optimize":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if not _AUTHORITATIVE_PUBLICATION_READY.is_set():
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "frontier_publication_not_ready"})
            return
        try:
            request = self._read_json()
            loadouts = solve(request)
            self._send(HTTPStatus.OK, {"jobId": request.get("jobId"), "loadouts": loadouts})
        except RequestTooLarge as exc:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
        except RequestError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except ServiceNotReady as exc:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
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
        self._send_bytes(status, body, content_type="application/json", cache_control="no-store")

    def _send_bytes(
        self,
        status: HTTPStatus,
        body: bytes,
        *,
        content_type: str,
        cache_control: str,
    ) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[robeatsmeta-service] " + (fmt % args) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer service")
    parser.add_argument("--host", default=env_str("ROBEATSMETA_OPTIMIZER_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=env_int("ROBEATSMETA_OPTIMIZER_API_PORT", 8765))
    args = parser.parse_args(argv)
    try:
        loopback_bind = ipaddress.ip_address(str(args.host)).is_loopback
    except ValueError:
        loopback_bind = str(args.host).strip().lower() == "localhost"
    if not loopback_bind and not env_str("ROBEATSMETA_OPTIMIZER_API_TOKEN", ""):
        raise RuntimeError("ROBEATSMETA_OPTIMIZER_API_TOKEN is required for a non-loopback bind")
    # Reclaim workspaces orphaned by a crash/SIGKILL: _solve_isolated cleans up in its finally, but
    # nothing else ever sweeps here. Safe because launchd runs a single service instance.
    shutil.rmtree(_service_run_root(), ignore_errors=True)
    server = ThreadingHTTPServer((args.host, int(args.port)), RoBeatsMetaServiceHandler)
    server.daemon_threads = True
    restart_revision: list[str] = []
    serving = threading.Event()

    def request_restart(commit: str) -> None:
        restart_revision[:] = [commit]
        _finish_server_code_update(aborted=False)

        def shutdown_when_serving() -> None:
            if serving.wait(timeout=30):
                server.shutdown()

        threading.Thread(target=shutdown_when_serving, name="frontier-server-restart", daemon=True).start()

    maintainer = FrontierServerMaintainer(
        repo_root=REPO_ROOT,
        timeline_cache_root=_TIMELINE_FRONTIER_CACHE_DIR,
        fg_cache_root=_FG_RESPONSE_FRONTIER_CACHE_DIR,
        state=_FRONTIER_DISTRIBUTION,
        prebuild=_prebuild_frontier_caches,
        restart_requested=request_restart,
        publication_ready=_activate_published_data,
        prepare_code_update=_prepare_server_code_update,
        code_update_aborted=lambda: _finish_server_code_update(aborted=True),
    )
    maintenance = threading.Thread(
        target=maintainer.serve_forever,
        name="frontier-server-maintenance",
        daemon=True,
    )
    maintenance.start()
    print(
        f"[robeatsmeta-service] listening on http://{args.host}:{args.port}"
        f" (pool={_SOLVE_POOL_SIZE}, timeline_cache={_TIMELINE_FRONTIER_CACHE_DIR},"
        f" fg_cache={_FG_RESPONSE_FRONTIER_CACHE_DIR})",
        flush=True,
    )
    try:
        serving.set()
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        maintainer.stop()
        server.server_close()
    if restart_revision:
        print(
            f"[robeatsmeta-service] restarting into fetched revision {restart_revision[0][:12]}",
            flush=True,
        )
        command_args = list(sys.argv[1:] if argv is None else argv)
        os.execv(
            sys.executable,
            [sys.executable, "-m", "gear_optimizer.robeatsmeta_service", *command_args],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
