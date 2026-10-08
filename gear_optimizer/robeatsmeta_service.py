from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
import ctypes.util
import hashlib
import hmac
import ipaddress
import contextlib
import json
import logging
import multiprocessing
import os
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from gear_optimizer.chart import read_header
from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.macos_background import make_process_background_only
from gear_optimizer.settings import (
    DIFFICULTIES,
    REASONING_LEVELS,
    paths,
    reasoning_search,
    service_settings,
)
from gear_optimizer.store import db, legacy, schema
from gear_optimizer.store.db import present_songs
from gear_optimizer.data.exported_game_data_sync import exported_song_names
from gear_optimizer.frontier_auth import FrontierRequestAuthenticator
from gear_optimizer.solver.timing_envelope import TIMING_MODES
from gear_optimizer.frontier_server import (
    FrontierDistributionState,
    FrontierServerMaintainer,
    source_snapshot_root,
)

logger = logging.getLogger(__name__)

# Stateless HTTP front-end over the canonical optimizer pipeline.
#
# The host application owns identity, quotas, sharing, and per-job persistence. This service owns
# canonical catalog promotion because it is the process that can prove a solve used an official
# chart and the untouched item catalog.
#   GET  /songs     -> the official chart list (from Data/ headers)
#   POST /optimize  -> solve one chart (official `targetSongId` OR custom `chartText`) and return
#                      its full T5 baseline leaderboard (top 51 base + 51 FG by hash), in the exact
#                      shape store.legacy.best_loadouts yields for the catalog. A host may persist this
#                      into a per-job evolution.db-format file and replay it through the same
#                      on-demand rescore path used by the catalog.
#
# Official charts are solved on one warm persistent worker process (service_worker); an uploaded chart
# runs `main.py run` in a throwaway per-request dir with its own frontier caches, the song source, run
# state and output DB redirected via the ROBEATSMETA_OPTIMIZER_* path overrides. After a clean official
# solve finishes, its canonical-format leaderboard is merged into evolution.db; custom inputs remain
# isolated. Each activated publication also solves the official charts evolution.db has no build for
# yet, so a newly published song reaches the catalog without waiting for someone to optimize it.
#
# ThreadingHTTPServer handles requests in parallel; a bounded semaphore and a free-memory gate admit
# the solves. Official solves share MetaFinder's canonical timeline and FG frontier caches: a valid
# uploaded or previously-built entry is reused forever; a cache miss is built and persisted for every
# later solve.

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "Data"
GEAR_DIR = DATA_ROOT / "Gear"

# Global solve pool: caps concurrent optimizer subprocesses. The GPU is the bottleneck (one song
# at a time on the Vulkan device), but the CPU-side frontier build + chart parse + DB write
# overlaps with the GPU work of the previous song, so a small pool keeps both fed.
_SOLVE_POOL_SIZE = service_settings().solve_pool
_SOLVE_SEMAPHORE = threading.Semaphore(_SOLVE_POOL_SIZE)

# Memory-headroom admission (a hardware memory bound, not a perf flag). The semaphore caps how many
# solves may be *scheduled*, but each solve subprocess (main.py + its GPU context + worker pool) is
# memory-heavy, and on a small-RAM box enough concurrent solves exhaust RAM and thrash/OOM (measured
# on a 16 GB unified-memory Mac: 2 concurrent solves drove free memory to ~70 MB). So gate the START
# of each *additional* concurrent solve on real available memory: the first concurrent solve always
# runs (progress guarantee, never deadlocks), and a further one only starts once at least
# ROBEATSMETA_OPTIMIZER_SERVICE_MIN_FREE_MB is reclaimable without compressing or swapping (see
# _available_bytes: psutil on macOS counts inactive anonymous pages as available) -- otherwise it
# waits for a running solve to finish. This makes effective concurrency track the box's memory
# regardless of the pool size. The gate samples memory at start time, so two solves admitted at the
# same moment can both pass before either one allocates.
_MIN_FREE_BYTES = service_settings().min_free_mb * 1024 * 1024
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


if sys.platform == "darwin":
    _LIBC = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def _sysctl_uint(name: str) -> int:
    value = ctypes.c_uint64(0)
    size = ctypes.c_size_t(ctypes.sizeof(value))
    if _LIBC.sysctlbyname(name.encode("ascii"), ctypes.byref(value), ctypes.byref(size), None, ctypes.c_size_t(0)) != 0:
        raise OSError(ctypes.get_errno(), f"sysctlbyname failed: {name}")
    if size.value not in (4, 8):  # page counts are 4 bytes; purgeable and pagesize are 8
        raise OSError(f"sysctl {name} returned {size.value} bytes, expected 4 or 8")
    return int(value.value)


def _available_bytes() -> int:
    if sys.platform == "darwin":
        # psutil's macOS "available" is inactive + free, and inactive anonymous pages only come back
        # by compressing or swapping them, so it stays high while the box swaps. Count what the
        # kernel frees without either: free, file-backed (pageable external, which already holds
        # the speculative pages) and purgeable.
        pages = (
            _sysctl_uint("vm.page_free_count")
            + _sysctl_uint("vm.page_pageable_external_count")
            + _sysctl_uint("vm.page_purgeable_count")
        )
        return pages * _sysctl_uint("hw.pagesize")
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


@contextlib.contextmanager
def _solve_slot():
    """Hold one of the pool's solve slots, admitted by the memory-headroom gate (_acquire_solve_slot)."""
    with _SOLVE_SEMAPHORE:
        _acquire_solve_slot()
        try:
            yield
        finally:
            _release_solve_slot()

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
# into memory. Sized above the supported custom-chart event limit with JSON-escape margin. Deploy
# behind loopback/private networking and bearer authentication.
_MAX_BODY_BYTES = service_settings().max_body_bytes
_MAX_CUSTOM_CHART_EVENTS = service_settings().max_custom_chart_events

# Hard wall-clock cap on a single solve subprocess: on timeout the whole process group is killed
# (so main.py's GPU/worker children don't linger) and the request fails. Must exceed a real solve.
_SOLVE_TIMEOUT_S = service_settings().solve_timeout_s

# An idle persistent solver still holds its whole Taichi device, prewarmed app and per-song caches
# (~0.8 GB). Stop it after this long without a request; the next official solve respawns it cold.
_PERSISTENT_WORKER_IDLE_EXIT_S = service_settings().persistent_idle_exit_s

# Reasoning effort lets a host request a larger optimizer search budget (settings.reasoning_search).
def _normalize_reasoning(value: Any) -> str:
    level = str(value or "").strip().lower()
    return level if level in REASONING_LEVELS else "default"


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


def _prebuild_frontier_caches(
    data_root: Path,
    changed_charts: tuple[Path, ...] | None = None,
) -> dict[str, set[str]]:
    """Build every missing canonical cache before a Data revision becomes downloadable.

    Returns only the files of the charts it verified; _prebuild_frontier_caches_isolated runs it
    in a child process and adds the active publication's files for an incremental build.
    """
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work

    curves = load_stat_curves(data_root / "Gear" / "Stats.txt")
    song_paths = (
        tuple(str(chart) for chart in changed_charts)
        if changed_charts is not None
        else tuple(
            str(chart)
            for difficulty in DIFFICULTIES
            for chart in sorted((data_root / difficulty).glob("*.txt"))
        )
    )
    if not song_paths:
        raise RuntimeError(f"frontier server Data revision has no song charts: {data_root}")
    run_startup_cpu_work(
        song_queue=tuple((path,) for path in song_paths),  # queue entries are (chart path, ...) tuples
        curves=curves,
        data_root=data_root,
        build_missing=True,
        authorize_destructive_rotation=True,
    )
    from gear_optimizer.solver.taichi_gem.api.timeline import TIMELINE_FRONTIER_CACHE
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import FG_RESPONSE_FRONTIER_CACHE

    def recorded_files(cache, cache_root: Path) -> set[str]:
        """The files of every chart in every timing mode (the prebuild built them all)."""
        plans = [
            cache.manifest_plan(song_paths, curves, timing_mode=mode, persist_validated_entries=False)
            for mode in TIMING_MODES
        ]
        payload = json.loads(cache.manifest_path().read_text(encoding="utf-8"))
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, dict) or any(plan.missing_paths for plan in plans):
            raise RuntimeError("frontier prebuild did not produce a complete publication manifest")
        files: set[str] = set()
        for key in {key for plan in plans for key in plan.key_by_norm_path.values()}:
            entry = entries.get(key)
            cache_file = Path(str(entry.get("cache_file") or "")) if isinstance(entry, dict) else Path()
            if cache_file.parent.resolve() != cache_root.resolve() or not cache_file.is_file():
                raise RuntimeError(f"frontier manifest references an invalid cache file: {cache_file}")
            files.add(cache_file.name)
        return files

    return {
        "timeline": recorded_files(TIMELINE_FRONTIER_CACHE, _TIMELINE_FRONTIER_CACHE_DIR),
        "fg": recorded_files(FG_RESPONSE_FRONTIER_CACHE, _FG_RESPONSE_FRONTIER_CACHE_DIR),
    }


def _prebuild_frontier_caches_isolated(
    data_root: Path,
    changed_charts: tuple[Path, ...] | None = None,
) -> dict[str, set[str]]:
    """Run the prebuild in a short-lived spawned process, then merge the active publication.

    The prebuild imports the solver stack and may build a single chart in-process; its memory
    high-water would otherwise stay resident in this long-lived service after every publication.
    """
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=multiprocessing.get_context("spawn"),
        # Before the prebuild imports Taichi/MoltenVK, keep the child out of the Dock like the solver.
        initializer=make_process_background_only,
    ) as executor:
        files = executor.submit(
            _prebuild_frontier_caches,
            Path(data_root),
            tuple(changed_charts) if changed_charts is not None else None,
        ).result()
    if changed_charts is not None:
        # The active publication is this process's in-memory state; a fresh child has none.
        previous_body = _FRONTIER_DISTRIBUTION.manifest_bytes()
        previous = json.loads(previous_body) if previous_body is not None else None
        if not isinstance(previous, dict):
            raise RuntimeError("incremental frontier build requires the active complete publication")
        for bundle in previous.get("bundles", []):
            if not isinstance(bundle, dict):
                continue
            for entry in bundle.get("files", []):
                if not isinstance(entry, dict):
                    continue
                scope = str(entry.get("scope") or "")
                path = str(entry.get("path") or "")
                if scope == "timeline" and path:
                    files["timeline"].add(path)
                elif scope == "fg" and path:
                    files["fg"].add(path)
    return files


class RequestError(ValueError):
    """A bad request from the caller -> HTTP 400 (an internal failure -> 500)."""


class RequestTooLarge(RequestError):
    """The request body exceeds the configured cap -> HTTP 413."""


# --- official chart catalog --------------------------------------------------

def _read_full_header(path: Path) -> dict[str, str]:
    """The chart's header fields; empty (the catalog skips the chart) when it cannot be read."""
    try:
        return read_header(path)
    except (OSError, ValueError):
        # Never swallow silently: an empty header makes the catalog builder skip the chart, so a
        # permissions/disk hiccup or a malformed file would quietly shrink /songs with no trace.
        logger.warning("unreadable chart header, chart will be missing from the catalog: %s", path, exc_info=True)
        return {}


def _official_song_directories() -> tuple[tuple[str, Path], ...]:
    """Return the exact chart directories backing the API's official-song catalog.

    Direct runs retain the native ``Data/{difficulty}`` layout. A service deployment may instead
    select an external canonical chart library; once that root is explicitly configured, every
    expected difficulty directory is required.
    """
    configured = service_settings().catalog_data_dir
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
            "ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR must contain "
            f"Easy Songs, Normal Songs, and Hard Songs directories; missing: {', '.join(missing)}"
        )
    return directories


def _official_catalog_cache_key() -> tuple[tuple[str, Path, tuple[tuple[str, int, int], ...]], ...]:
    """Track chart-file state so an external catalog cannot stay stale after a song import."""
    directories = _official_song_directories()
    return tuple(
        (
            difficulty,
            diff_dir,
            tuple(
                (chart.name, chart.stat().st_mtime_ns, chart.stat().st_size)
                for chart in sorted(diff_dir.glob("*.txt"), key=lambda path: path.name)
            ),
        )
        for difficulty, diff_dir in directories
    )


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


def _activate_last_complete_publication(
    state: FrontierDistributionState,
    *,
    snapshots_root: Path | None = None,
) -> bool:
    manifest_body = state.manifest_bytes()
    if manifest_body is None:
        return False
    try:
        manifest = json.loads(manifest_body)
        code_revision = str(manifest.get("code_revision") or "")
        if re.fullmatch(r"[0-9a-f]{40,64}", code_revision) is None:
            return False
        data_root = (snapshots_root or source_snapshot_root()) / code_revision / "Data"
        _activate_published_data(data_root)
    except (OSError, ValueError, TypeError, RuntimeError):  # JSONDecodeError is a ValueError
        logger.warning("last complete frontier publication could not be activated", exc_info=True)
        return False
    logger.info("activated last complete frontier publication %s at startup", code_revision)
    return True


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
            h = _read_full_header(chart)  # values come stripped
            song_id = h.get("Song Name", "")
            if not song_id:
                continue
            title = h.get("Title", "")
            for d in ("Hard", "Normal", "Easy"):
                suffix = f" ({d})"
                if title.endswith(suffix):
                    title = title[: -len(suffix)]
                    break
            songs.append({
                "songId": song_id,
                "difficulty": difficulty,
                "primaryElement": h.get("Primary Color", ""),
                "secondaryElement": h.get("Secondary Color", ""),
                "title": title,
                "artist": h.get("Artist", ""),
                "audioId": h.get("Audio Asset ID", "").replace("rbxassetid://", ""),
                "coverImageId": h.get("Cover Image ID", ""),
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
    """The official chart list for a host picker, read from the catalog Data/ headers.

    Every chart file's header is read in full so the picker gets title, artist, audioId, and
    coverImageId directly from the source — no catalog or evolution.db dependency. The difficulty
    suffix is stripped from the title so the frontend collapses all difficulties of a song into
    one entry (same title+artist = same family key).
    """
    return [dict(song) for song in _official_song_catalog().songs]


def find_official_chart(song_id: str) -> Path:
    """Return the official chart file whose `Song Name` header equals `song_id` exactly.

    Hosts pick from `list_official_songs()` and echo back the exact `songId`, so an exact
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
    mode = str(value or "non-precise").strip().lower()
    if mode not in TIMING_MODES:
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


# --- custom gear / mini pool -------------------------------------------------
#
# A caller may pool up to 5 hypothetical gear pieces and 5 hypothetical minis alongside the real
# catalog FOR ONE SOLVE. They are written as extra rows into the per-request Data/Gear CSV copies,
# so the canonical pipeline discovers them exactly like catalog items and nothing outside the
# throwaway workspace is touched. This is an external boundary, so every field is validated here.

_MAX_CUSTOM_POOL_ITEMS = 5
_MAX_CUSTOM_ITEM_NAME = 32
_MAX_CUSTOM_STAT = 999
_CUSTOM_ITEM_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '\-_.!?()&+:]{0,31}$")
_CUSTOM_GEAR_SLOTS = ("Hat", "Face", "Neck", "Shirt", "Pants", "Back")
_CUSTOM_MINI_TYPES = ("Chill", "Flow", "Rush", "Beat", "Vibe")
# Request stat key -> CSV column header, per item kind (the two CSVs spell the same stats
# differently). Keys the CSV lacks are simply never written.
_CUSTOM_GEAR_COLUMNS = {
    "chill": "Chill", "flow": "Flow", "rush": "Rush", "beat": "Beat", "vibe": "Vibe",
    "ppoint": "PPoint", "cmult": "CMult", "fmult": "FMult", "time": "Time", "fill": "Fill",
}
# No PPoint: Minis.csv has no such column (a mini's Perfect Points come from ascension level only).
_CUSTOM_MINI_COLUMNS = {
    "chill": "Chill", "flow": "Flow", "rush": "Rush", "beat": "Beat", "vibe": "Vibe",
    "cbmlt": "CbMlt", "fvmlt": "FvMlt", "fvtim": "FvTim", "fvfil": "FvFil",
}


def _custom_item(raw: Any, *, columns: dict[str, str], types: tuple[str, ...], seen: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RequestError("each custom pool item must be a JSON object")
    name = str(raw.get("name") or "").strip()
    if not _CUSTOM_ITEM_NAME_RE.match(name) or len(name) > _MAX_CUSTOM_ITEM_NAME:
        raise RequestError(f"invalid custom item name {name!r}")
    if name.casefold() in seen:
        raise RequestError(f"duplicate custom item name {name!r}")
    seen.add(name.casefold())
    item_type = str(raw.get("type") or "").strip()
    if item_type not in types:
        raise RequestError(f"invalid custom item type {item_type!r} for {name!r}")
    item: dict[str, Any] = {"name": name, "type": item_type}
    for key in columns:
        value = raw.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RequestError(f"custom item {name!r} stat {key!r} must be an integer")
        if value < 0 or value > _MAX_CUSTOM_STAT:
            raise RequestError(f"custom item {name!r} stat {key!r} out of range")
        item[key] = value
    return item


_MAX_EXCLUDED = {"excludeGear": 400, "excludeMinis": 200}
# Catalog names are only ever COMPARED against CSV cells here, never written into one, so the rule is
# just "printable, no control chars / quotes / newlines" — real names contain '*', ',', unicode, etc.
_EXCLUDED_NAME_RE = re.compile(r'^[^\x00-\x1f\x7f"\r\n]{1,64}$')


def _excluded_names(request: dict[str, Any], field: str) -> list[str]:
    raw = request.get(field)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RequestError(f"{field} must be a list")
    if len(raw) > _MAX_EXCLUDED[field]:
        raise RequestError(f"{field} exceeds {_MAX_EXCLUDED[field]} items")
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise RequestError(f"{field} entries must be strings")
        name = entry.strip()
        if not name:
            continue
        if not _EXCLUDED_NAME_RE.match(name):
            raise RequestError(f"invalid excluded item name {name!r}")
        out.append(name)
    return out


def _custom_pool_for_request(request: dict[str, Any]) -> dict[str, list[Any]]:
    pool: dict[str, list[Any]] = {"gear": [], "minis": [], "excludeGear": [], "excludeMinis": []}
    for field_name, key, columns, types in (
        ("customGear", "gear", _CUSTOM_GEAR_COLUMNS, _CUSTOM_GEAR_SLOTS),
        ("customMinis", "minis", _CUSTOM_MINI_COLUMNS, _CUSTOM_MINI_TYPES),
    ):
        raw = request.get(field_name)
        if raw is None:
            continue
        if not isinstance(raw, list):
            raise RequestError(f"{field_name} must be a list")
        if len(raw) > _MAX_CUSTOM_POOL_ITEMS:
            raise RequestError(f"{field_name} exceeds {_MAX_CUSTOM_POOL_ITEMS} items")
        seen: set[str] = set()
        pool[key] = [_custom_item(entry, columns=columns, types=types, seen=seen) for entry in raw]
    pool["excludeGear"] = _excluded_names(request, "excludeGear")
    pool["excludeMinis"] = _excluded_names(request, "excludeMinis")
    return pool


def _promotion_target(request: dict[str, Any], *, custom_pool: dict[str, list[Any]]) -> str | None:
    """The catalog database a clean official solve merges its results into, under its timing mode (None: the
    results are the caller's)."""
    if str(request.get("chartText") or "").strip() or not str(request.get("targetSongId") or "").strip():
        return None
    if any(custom_pool.values()):
        return None
    return str(paths().database)


def _remove_excluded_rows(gear_dir: Path, pool: dict[str, list[Any]]) -> None:
    """Delete the caller's excluded catalog rows from the per-request CSV copies.

    Rewrites each file without those rows, so the pipeline simply never discovers them — the same
    mechanism as appending custom rows, in reverse. Names are matched case-insensitively; an
    unknown name is a no-op (the catalog moves, a stale exclusion should not fail a solve).
    """
    import csv

    for filename, names, name_column in (
        ("Gears.csv", pool["excludeGear"], "Gear Name"),
        ("Minis.csv", pool["excludeMinis"], "Mini Name"),
    ):
        if not names:
            continue
        drop = {n.casefold() for n in names}  # validated, stripped (_excluded_names)
        path = gear_dir / filename
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            continue
        header = [h.strip() for h in rows[0]]
        name_index = header.index(name_column)
        kept = [rows[0]] + [
            row for row in rows[1:]
            if not (len(row) > name_index and str(row[name_index]).strip().casefold() in drop)
        ]
        if len(kept) == len(rows):
            continue
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(kept)


def _append_custom_pool_rows(gear_dir: Path, pool: dict[str, list[dict[str, Any]]]) -> None:
    """Append the pool's rows to the per-request Gears.csv / Minis.csv copies."""
    import csv

    for filename, items, columns, name_column in (
        ("Gears.csv", pool["gear"], _CUSTOM_GEAR_COLUMNS, "Gear Name"),
        ("Minis.csv", pool["minis"], _CUSTOM_MINI_COLUMNS, "Mini Name"),
    ):
        if not items:
            continue
        path = gear_dir / filename
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        header = [h.strip() for h in rows[0]]
        # A custom row that reuses a catalog name would silently redefine that catalog item for the
        # whole solve (name->stats maps are last-write-wins), so refuse instead.
        name_index = header.index(name_column)
        existing = {str(row[name_index]).strip().casefold() for row in rows[1:] if len(row) > name_index}
        new_rows: list[list[str]] = []
        for item in items:
            if item["name"].casefold() in existing:
                raise RequestError(f"custom item name {item['name']!r} already exists in {filename}")
            cell_by_column = {columns[key]: str(item[key]) for key in columns if item[key]}
            cell_by_column[name_column] = item["name"]
            cell_by_column["Type"] = item["type"]
            # Minis.csv repeats every stat column for the L1 ascension block; fill only the FIRST
            # occurrence of each header (which is what the parser reads for live stats) and leave
            # the repeats blank, so a custom mini has no L1 ascension stats.
            filled: set[str] = set()
            row_out: list[str] = []
            for column in header:
                row_out.append("" if column in filled else cell_by_column.get(column, ""))
                filled.add(column)
            new_rows.append(row_out)
        with path.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(new_rows)


def _service_run_root() -> Path:
    override = service_settings().run_dir
    return Path(override) if override else (REPO_ROOT / "bin" / "robeatsmeta_api_runs")


def _kill_process_group(proc: subprocess.Popen) -> None:
    """SIGKILL the solve subprocess and its whole process group so no GPU/worker child lingers."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, AttributeError):
        # The process is gone already (Popen.kill is then a no-op), or there are no process groups (Windows).
        proc.kill()


class _PersistentSolveWorker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._root = _service_run_root() / "persistent_solver"
        # The worker copies and loads the item catalog once, at spawn. A newly activated publication
        # (new gear, minis or ascension targets) must restart it, or official solves keep scoring
        # against the catalog that was active when the worker started.
        self._gear_source: Path | None = None
        self._idle_since = time.monotonic()

    def _read_stdout(self, proc: subprocess.Popen[str], responses: queue.Queue[dict[str, Any]]) -> None:
        try:
            for line in proc.stdout:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("persistent solver emitted non-JSON output: %s", line.rstrip())
                    continue
                if isinstance(payload, dict):
                    responses.put(payload)
        finally:
            responses.put({"ok": False, "error": "persistent solver exited", "eof": True})

    @staticmethod
    def _drain_stderr(proc: subprocess.Popen[str]) -> None:
        for line in proc.stderr:
            text = line.rstrip()
            if text:
                logger.debug("[persistent-solver] %s", text)

    def _start_locked(self) -> subprocess.Popen[str]:
        shutil.rmtree(self._root, ignore_errors=True)
        data_dir = self._root / "Data"
        bin_dir = self._root / "bin"
        data_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(parents=True, exist_ok=True)
        gear_dir = GEAR_DIR  # one read: a concurrent activation must not split copy and record
        self._gear_source = gear_dir
        shutil.copytree(gear_dir, data_dir / "Gear")
        env = {
            **os.environ,
            "EVOLUTION_DB_PATH": str(bin_dir / "service_result.db"),
            "ROBEATSMETA_OPTIMIZER_DATA_DIR": str(data_dir),
            "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(bin_dir),
            "ROBEATSMETA_OPTIMIZER_GEAR_SOURCE_DIR": str(gear_dir),
            "TIMELINE_FRONTIER_CACHE_DIR": str(_TIMELINE_FRONTIER_CACHE_DIR),
            "FG_RESPONSE_FRONTIER_CACHE_DIR": str(_FG_RESPONSE_FRONTIER_CACHE_DIR),
            "ROBEATSMETA_OPTIMIZER_SERVICE_MODE": "1",
            "ROBEATSMETA_OPTIMIZER_PERSISTENT_WORKER": "1",
            "METAFINDER_PROGRESS": "0",
            "METAFINDER_OUTPUT": "0",
            "PYTHONUNBUFFERED": "1",
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", "gear_optimizer.service_worker"],
            cwd=str(REPO_ROOT),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._responses = responses
        threading.Thread(
            target=self._read_stdout,
            args=(proc, responses),
            name="persistent-solver-stdout",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._drain_stderr,
            args=(proc,),
            name="persistent-solver-stderr",
            daemon=True,
        ).start()
        self._proc = proc
        return proc

    def _stop_locked(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        _kill_process_group(proc)
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            logger.warning("persistent solver pid %s did not exit within 5 s of SIGKILL", proc.pid)
        proc.stdout.close()
        proc.stderr.close()
        try:
            proc.stdin.close()
        except BrokenPipeError:  # flushing a request the killed worker never read
            pass

    def request(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self._lock:
            try:
                proc = self._proc
                if proc is None or proc.poll() is not None or self._gear_source != GEAR_DIR:
                    self._stop_locked()
                    proc = self._start_locked()
                try:
                    proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
                    proc.stdin.flush()
                    response = self._responses.get(timeout=_SOLVE_TIMEOUT_S)
                except queue.Empty as exc:
                    self._stop_locked()
                    raise RuntimeError(f"persistent optimizer timed out after {_SOLVE_TIMEOUT_S}s") from exc
                except (BrokenPipeError, OSError) as exc:
                    self._stop_locked()
                    raise RuntimeError("persistent optimizer worker disconnected") from exc
                if not bool(response.get("ok")):
                    if response.get("eof") or response.get("restart"):
                        self._stop_locked()
                    raise RuntimeError(str(response.get("error") or "persistent optimizer failed"))
                loadouts = response.get("loadouts")
                if not isinstance(loadouts, list):
                    raise RuntimeError("persistent optimizer returned an invalid loadout payload")
                return loadouts
            finally:
                self._idle_since = time.monotonic()

    def reap_if_idle(self) -> bool:
        """Stop the worker once it has sat idle past the timeout; never waits behind a solve."""
        if not self._lock.acquire(blocking=False):
            return False  # a solve is in flight
        try:
            idle_s = time.monotonic() - self._idle_since
            if self._proc is None or idle_s < _PERSISTENT_WORKER_IDLE_EXIT_S:
                return False
            logger.info("stopping idle persistent solver after %ss", int(idle_s))
            # SIGKILL like every publication and shutdown: a graceful stdin-EOF exit would tear
            # Taichi down under the live daemon GPU-executor thread.
            self._stop_locked()
            return True
        finally:
            self._lock.release()

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()


_PERSISTENT_SOLVE_WORKER: _PersistentSolveWorker | None = None


def _get_persistent_solve_worker() -> _PersistentSolveWorker:
    global _PERSISTENT_SOLVE_WORKER
    if _PERSISTENT_SOLVE_WORKER is None:
        _PERSISTENT_SOLVE_WORKER = _PersistentSolveWorker()
    return _PERSISTENT_SOLVE_WORKER


def _stop_persistent_solve_worker() -> None:
    global _PERSISTENT_SOLVE_WORKER
    worker = _PERSISTENT_SOLVE_WORKER
    _PERSISTENT_SOLVE_WORKER = None
    if worker is not None:
        worker.stop()


def _reap_idle_persistent_worker_forever() -> None:
    while True:
        time.sleep(60)
        worker = _PERSISTENT_SOLVE_WORKER
        if worker is not None:
            worker.reap_if_idle()


def _solve_persistent(
    job: str,
    chart: str,
    result_song_name: str,
    repeats: int,
    reasoning: str,
    *,
    promote_to: str | None = None,
    custom_pool: dict[str, list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Solve `chart` (_normalize_chart) on the warm persistent worker; a custom pool travels as a per-request
    Gears.csv / Minis.csv copy (built and validated exactly as for an isolated solve) that the worker loads for this
    request only."""
    payload = {"jobId": job, "chartText": chart, "songName": result_song_name, "repeats": repeats, "reasoning": reasoning}
    if promote_to:
        payload["promoteTo"] = promote_to
    with contextlib.ExitStack() as stack:
        if custom_pool and any(custom_pool.values()):
            run_root = _service_run_root()
            run_root.mkdir(parents=True, exist_ok=True)
            gear_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=f"{job}-", dir=run_root))) / "Gear"
            _copy_gear(gear_dir, custom_pool)
            payload["gearDir"] = str(gear_dir)
        with _solve_slot():
            return _get_persistent_solve_worker().request(payload)


def _copy_gear(gear_dir: Path, custom_pool: dict[str, list[Any]] | None) -> None:
    """The request's own copy of the catalog's Gear dir (real files; discovery does not follow symlinks), with its
    custom pool's exclusions and rows: the catalog Data/Gear CSVs are never touched."""
    shutil.copytree(GEAR_DIR, gear_dir)
    if custom_pool and any(custom_pool.values()):
        _remove_excluded_rows(gear_dir, custom_pool)
        _append_custom_pool_rows(gear_dir, custom_pool)


def _solve_isolated(
    job: str,
    chart: str,
    result_song_name: str,
    repeats: int,
    reasoning: str = "default",
    ephemeral_frontiers: bool = False,
    custom_pool: dict[str, list[dict[str, Any]]] | None = None,
    promote_to: str | None = None,
) -> list[dict[str, Any]]:
    """Run the canonical optimizer pipeline on `chart` (_normalize_chart) in an execution-owned workspace
    (`promote_to`: see _promotion_target)."""
    run_root = _service_run_root()
    run_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{job}-", dir=run_root) as workspace:
        work = Path(workspace)
        data_dir = work / "Data"
        (data_dir / "Hard").mkdir(parents=True, exist_ok=True)
        _copy_gear(data_dir / "Gear", custom_pool)
        chart_path = data_dir / "Hard" / f"{job}.txt"
        chart_path.write_text(chart, encoding="utf-8")
        mode = read_header(chart_path)["Timing Mode"]  # _normalize_chart wrote the request's
        # Reasoning effort scales the GA search knobs; "default" writes none (the run settings' defaults apply).
        reasoning_lines = ""
        if reasoning != "default":
            depth, multi_start = reasoning_search(reasoning)
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
        with _solve_slot():
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
            entries = legacy.read_best_loadouts(db_path, mode, result_song_name, "T5", limit=LOADOUTS_PER_SONG_LIMIT)
            if not entries:
                raise RuntimeError("optimizer produced no T5 loadout")
            if promote_to:
                db.promote(db_path, promote_to, mode, result_song_name, "T5")
            return entries


def solve(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Solve one chart and return its full T5 leaderboard.

    The returned list is the merged top-N base + FG leaderboard (ranked by score / fg_score, deduped
    by loadout_hash) exactly as store.legacy.best_loadouts yields for the catalog. A host can persist
    the result into an evolution.db-format file and replay it through the catalog's on-demand rescore
    path.
    """
    job = _job_slug(request.get("jobId") or request.get("resultKey"))
    chart_text, result_song_name = chart_text_and_result_song_name_for_request(request, fallback_name=job)
    if str(request.get("chartText") or "").strip():
        _validate_custom_chart_event_limit(chart_text)
    repeats = service_settings().repeats
    reasoning = _normalize_reasoning(request.get("reasoning"))
    timing_mode = _normalize_timing_mode(request.get("timingMode"))
    custom_pool = _custom_pool_for_request(request)
    # Dedup on the job AND the solve inputs: two concurrent requests whose ids merely slug
    # identically (or both fall back to "job") must never silently join and hand the second
    # caller a leaderboard computed for a different chart/reasoning/timing/custom pool.
    pool_key = json.dumps(custom_pool, sort_keys=True, separators=(",", ":"))
    solve_key = job + ":" + hashlib.sha256(
        f"{reasoning}|{timing_mode}|{repeats}|{pool_key}|{chart_text}".encode("utf-8")
    ).hexdigest()[:16]
    state, owner = _claim_job_solve(solve_key)
    if not owner:
        logger.info("joining in-flight optimizer solve for job %s", job)
        return state.wait()
    try:
        custom_chart = bool(str(request.get("chartText") or "").strip())
        promote_to = _promotion_target(request, custom_pool=custom_pool)
        chart = _normalize_chart(chart_text, result_song_name, timing_mode)
        # An uploaded chart keeps the isolated path (its frontier caches must stay out of the shared ones); a
        # custom item pool on an official chart is solved warm.
        if service_settings().persistent_solver and not custom_chart:
            state.result = _solve_persistent(
                job, chart, result_song_name, repeats, reasoning, promote_to=promote_to, custom_pool=custom_pool
            )
        else:
            state.result = _solve_isolated(
                job,
                chart,
                result_song_name,
                repeats,
                reasoning,
                ephemeral_frontiers=custom_chart or any(custom_pool.values()),
                custom_pool=custom_pool,
                promote_to=promote_to,
            )
        if promote_to:
            logger.info("promoted official optimizer result for %s into evolution.db", result_song_name)
        return state.result
    except BaseException as exc:
        state.error = exc
        raise
    finally:
        state.done.set()
        _release_job_solve(solve_key, state)


# --- catalog builds ----------------------------------------------------------
#
# evolution.db is the website's song catalog, and a chart only enters it through a promoted official
# solve. The website also refuses to publish while any published chart is unbuilt, so a new chart
# that nobody happened to optimize froze every website data update. After each publication
# activates, solve every official chart the active game data describes but evolution.db has no build
# for, one at a time, through the same path as a user's request. Waiting for the game data is
# deliberate: its mini ascension targets change a new song's scores.

def unbuilt_catalog_song_ids() -> list[tuple[str, str]]:
    """(song id, timing mode) of each official chart the active game data describes that evolution.db has no build
    for in that mode."""
    payload = json.loads((DATA_ROOT / "exported_game_data.json").read_text(encoding="utf-8"))
    candidates = exported_song_names(payload).intersection(_official_song_catalog().paths_by_song_id)
    catalog = paths().database
    if not catalog.exists():
        return sorted((song, mode) for song in candidates for mode in TIMING_MODES)
    conn = schema.connect(catalog)
    try:
        return sorted((song, mode) for mode in TIMING_MODES for song in candidates - present_songs(conn, mode, candidates))
    finally:
        conn.close()


def build_missing_catalog_songs() -> None:
    missing = unbuilt_catalog_song_ids()
    if missing:
        print(f"[robeatsmeta-service] building {len(missing)} official chart(s) missing from the catalog", flush=True)
    for song_id, mode in missing:
        if not _AUTHORITATIVE_PUBLICATION_READY.is_set():
            return  # a code update is draining; the next activation starts a fresh pass
        digest = hashlib.sha256(f"{song_id}|{mode}".encode("utf-8")).hexdigest()[:16]
        try:
            solve({"jobId": f"catalog-{digest}", "targetSongId": song_id, "timingMode": mode})
        except ServiceNotReady:
            return
        except Exception:  # noqa: BLE001 - one bad chart must not stop the rest of the catalog
            logger.exception("catalog build failed for %s (%s)", song_id, mode)
            print(
                f"[robeatsmeta-service] catalog build FAILED for {song_id} ({mode}); retried on the next publication",
                flush=True,
            )
            continue
        print(f"[robeatsmeta-service] built catalog entry for {song_id} ({mode})", flush=True)


class _CatalogBuilder:
    """Run build passes on a background thread; a request during a pass queues exactly one more."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending = False
        self._running = False

    def request(self) -> None:
        with self._lock:
            self._pending = True
            if self._running:
                return
            self._running = True
        threading.Thread(target=self._run, name="catalog-builder", daemon=True).start()

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._pending:
                    self._running = False
                    return
                self._pending = False
            try:
                build_missing_catalog_songs()
            except Exception:  # noqa: BLE001 - background thread: record it, the next publication retries
                logger.exception("catalog build pass failed")


# --- HTTP --------------------------------------------------------------------

class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/3.0"
    # Socket timeout for reads AND writes: without it a client that stalls mid-body (or mid-bundle
    # download) pins a daemon thread and its fds for the life of the process. Remote standalone
    # installs talk to this service over real networks; stalls happen.
    timeout = 60

    def _authorized(self) -> bool:
        token = service_settings().api_token
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
        path = self.path.rstrip("/")
        if path not in {"/optimize", "/frontiers/refresh"}:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if path == "/frontiers/refresh":
            maintainer = getattr(self.server, "frontier_maintainer", None)
            if maintainer is None:
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "frontier_maintainer_unavailable"})
                return
            maintainer.request_refresh()
            self._send(HTTPStatus.ACCEPTED, {"queued": True})
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


_LISTENER_FD_ENV = "ROBEATSMETA_SERVICE_LISTENER_FD"


def _http_server(host: str, port: int) -> ThreadingHTTPServer:
    """The service's HTTP server. After a self-update exec it serves on the listening socket the previous image
    handed over: the port is never unbound, so a supervisor watching the port owner never starts a second service
    (the hub's start() did, whenever its tick fell between the old image's close and the new one's bind)."""
    inherited = os.environ.pop(_LISTENER_FD_ENV, "")
    if not inherited:
        return ThreadingHTTPServer((host, port), RoBeatsMetaServiceHandler)
    server = ThreadingHTTPServer((host, port), RoBeatsMetaServiceHandler, bind_and_activate=False)
    server.socket.close()
    server.socket = socket.socket(fileno=int(inherited))
    server.server_address = server.socket.getsockname()
    server.server_name, server.server_port = host, port
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer service")
    settings = service_settings()
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    args = parser.parse_args(argv)
    try:
        loopback_bind = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        loopback_bind = args.host.strip().lower() == "localhost"
    if not loopback_bind and not settings.api_token:
        raise RuntimeError("ROBEATSMETA_OPTIMIZER_API_TOKEN is required for a non-loopback bind")
    # Reclaim workspaces orphaned by a crash/SIGKILL: _solve_isolated cleans up in its finally, but
    # nothing else ever sweeps here. Safe because launchd runs a single service instance.
    shutil.rmtree(_service_run_root(), ignore_errors=True)
    server = _http_server(args.host, args.port)
    server.daemon_threads = True
    _activate_last_complete_publication(_FRONTIER_DISTRIBUTION)
    restart_revision: list[str] = []
    serving = threading.Event()

    def request_restart(commit: str) -> None:
        restart_revision[:] = [commit]
        _finish_server_code_update(aborted=False)

        def shutdown_when_serving() -> None:
            if serving.wait(timeout=30):
                server.shutdown()

        threading.Thread(target=shutdown_when_serving, name="frontier-server-restart", daemon=True).start()

    def handle_shutdown_signal(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, name="optimizer-signal-shutdown", daemon=True).start()

    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    catalog_builder = _CatalogBuilder()

    def publication_ready(data_root: Path) -> None:
        _activate_published_data(data_root)
        catalog_builder.request()

    maintainer = FrontierServerMaintainer(
        repo_root=REPO_ROOT,
        timeline_cache_root=_TIMELINE_FRONTIER_CACHE_DIR,
        fg_cache_root=_FG_RESPONSE_FRONTIER_CACHE_DIR,
        state=_FRONTIER_DISTRIBUTION,
        prebuild=_prebuild_frontier_caches_isolated,
        restart_requested=request_restart,
        publication_ready=publication_ready,
        prepare_code_update=_prepare_server_code_update,
        code_update_aborted=lambda: _finish_server_code_update(aborted=True),
    )
    server.frontier_maintainer = maintainer  # type: ignore[attr-defined]
    maintenance = threading.Thread(
        target=maintainer.serve_forever,
        name="frontier-server-maintenance",
        daemon=True,
    )
    maintenance.start()
    threading.Thread(
        target=_reap_idle_persistent_worker_forever,
        name="persistent-solver-idle-reaper",
        daemon=True,
    ).start()
    print(
        f"[robeatsmeta-service] listening on http://{args.host}:{args.port}"
        f" (pool={_SOLVE_POOL_SIZE}, timeline_cache={_TIMELINE_FRONTIER_CACHE_DIR},"
        f" fg_cache={_FG_RESPONSE_FRONTIER_CACHE_DIR})",
        flush=True,
    )
    try:
        serving.set()
        server.serve_forever()  # SIGINT/SIGTERM shut it down through handle_shutdown_signal
    finally:
        _stop_persistent_solve_worker()
        maintainer.stop()
        if not restart_revision:
            server.server_close()
    if restart_revision:
        print(
            f"[robeatsmeta-service] restarting into fetched revision {restart_revision[0][:12]}",
            flush=True,
        )
        # The next image serves on this listening socket (connections wait in its backlog meanwhile).
        server.socket.set_inheritable(True)
        os.environ[_LISTENER_FD_ENV] = str(server.socket.fileno())
        command_args = list(sys.argv[1:] if argv is None else argv)
        os.execv(
            sys.executable,
            [sys.executable, "-m", "gear_optimizer.robeatsmeta_service", *command_args],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
