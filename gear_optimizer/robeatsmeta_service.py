"""The :8765 service: the optimizer pipeline over HTTP.

The host application owns identity, quotas, sharing and per-job persistence. This service owns catalog promotion: it is
the process that can prove a solve used an official chart and the untouched catalog.
  GET  /songs              the official chart list (chart headers, read once per Data revision or refresh)
  POST /frontiers/refresh  the song publisher wrote charts: re-read the list and look for the new revision now
  POST /optimize           solve one chart (official `targetSongId` or uploaded `chartText`) and return its T5 leaderboard
                           in the shape store.legacy.best_loadouts yields for the catalog
  POST /reverse            the sets behind a Top Scores row of an official chart: `targetSongId`, `score` and what else the
                           row shows (`accuracy`, `gearMultiplier`, `casualScore`, `gearPower`, `matchMode`)

Official charts solve on one warm worker process (service_worker), a custom item pool included. An uploaded chart gets a
worker of its own with throwaway frontier caches. A clean official solve merges into evolution.db, and each Data revision
solves the official charts evolution.db has no build for, so a published song reaches the catalog on its own.

Score lookups queue for a worker of their own (gear_optimizer.reverse.worker), with its own GPU context: they never wait for a
solve slot.

ThreadingHTTPServer handles requests in parallel; a semaphore and a free-memory gate admit the solves.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import ctypes.util
import hashlib
import hmac
import ipaddress
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
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from gear_optimizer.chart import read_header
from gear_optimizer.core.macos_background import make_process_background_only
from gear_optimizer.core.timing_modes import PRECISE, TIMING_MODES
from gear_optimizer.data.game_export import CUSTOM_GEAR_STATS, CUSTOM_MINI_STATS, game_song_names, load_catalog
from gear_optimizer.service_update import ServiceUpdater
from gear_optimizer.settings import DIFFICULTIES, REASONING_LEVELS, paths, service_settings
from gear_optimizer.store import schema
from gear_optimizer.store.db import present_songs

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]

_SOLVE_TIMEOUT_S = 30 * 60
_LOOKUP_TIMEOUT_S = 120
# Lookups in the queue and running; past that a host hears the service is busy instead of waiting.
_LOOKUPS_QUEUED = 64
_MAX_CUSTOM_CHART_EVENTS = 4_000
_MAX_CUSTOM_POOL_ITEMS = 15
_MAX_CUSTOM_STAT = 999
_MAX_EXCLUDED = {"excludeGear": 400, "excludeMinis": 200}
_CUSTOM_ITEM_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '\-_.!?()&+:]{0,31}$")
# Catalog names are only compared with these, so the rule is just printable: real names hold '*', ',' and unicode.
_EXCLUDED_NAME_RE = re.compile(r'^[^\x00-\x1f\x7f"\r\n]{1,64}$')
_CUSTOM_GEAR_SLOTS = ("Hat", "Face", "Neck", "Shirt", "Pants", "Back")
_CUSTOM_MINI_TYPES = ("Chill", "Flow", "Rush", "Beat", "Vibe")
_LISTENER_FD_ENV = "ROBEATSMETA_SERVICE_LISTENER_FD"

# The GPU solves one song at a time, but the CPU work around it overlaps, so a small pool keeps both fed. A solve is
# memory-heavy: past the first, one only starts while this much memory comes back without compressing or swapping
# (2 concurrent solves took a 16 GB Mac down to ~70 MB free). The gate samples at start, so two solves admitted at the
# same moment can both pass.
_MIN_FREE_BYTES = 3000 * 1024 * 1024
_solve_semaphore = threading.Semaphore(service_settings().solve_pool)
_admission = threading.Condition()
_active_solves = 0
_draining = False


class RequestError(ValueError):
    """A bad request from the caller -> HTTP 400 (an internal failure -> 500)."""


class RequestTooLarge(RequestError):
    """The request body exceeds the configured cap -> HTTP 413."""


class ServiceNotReady(RuntimeError):
    """The service is draining for a code update -> HTTP 503."""


if sys.platform == "darwin":
    _LIBC = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def _sysctl_uint(name: str) -> int:
    value = ctypes.c_uint64(0)
    size = ctypes.c_size_t(ctypes.sizeof(value))
    if _LIBC.sysctlbyname(name.encode("ascii"), ctypes.byref(value), ctypes.byref(size), None, ctypes.c_size_t(0)) != 0:
        raise OSError(ctypes.get_errno(), f"sysctlbyname failed: {name}")
    return int(value.value)


def _available_bytes() -> int:
    if sys.platform == "darwin":
        # psutil's macOS "available" counts inactive anonymous pages, which only come back by compressing or swapping.
        # Count what the kernel frees without either: free, file-backed and purgeable pages.
        pages = (
            _sysctl_uint("vm.page_free_count")
            + _sysctl_uint("vm.page_pageable_external_count")
            + _sysctl_uint("vm.page_purgeable_count")
        )
        return pages * _sysctl_uint("hw.pagesize")
    import psutil

    return int(psutil.virtual_memory().available)


@contextlib.contextmanager
def _solve_slot():
    """Hold a solve slot: a place in the pool, admitted by the memory gate."""
    global _active_solves
    with _solve_semaphore:
        with _admission:
            while not _draining and _active_solves > 0 and _available_bytes() < _MIN_FREE_BYTES:
                _admission.wait(timeout=1.0)
            if _draining:
                raise ServiceNotReady("the optimizer service is restarting into a new revision")
            _active_solves += 1
        try:
            yield
        finally:
            with _admission:
                _active_solves -= 1
                _admission.notify_all()


def _drain_solves() -> None:
    """Refuse new solves and wait for the running ones."""
    global _draining
    with _admission:
        _draining = True
        _admission.notify_all()
        while _active_solves:
            _admission.wait(timeout=1.0)


def _resume_solves() -> None:
    global _draining
    with _admission:
        _draining = False
        _admission.notify_all()


# --- official charts ---------------------------------------------------------

@dataclass(frozen=True)
class _OfficialCharts:
    songs: tuple[dict[str, str], ...]
    paths_by_song_id: dict[str, Path]


_official_charts_lock = threading.Lock()
_official_charts_cache: _OfficialCharts | None = None


def _official_song_directories() -> tuple[tuple[str, Path], ...]:
    """The chart folders behind the official song list: the engine's Data, or a configured library's `<level> Songs`."""
    configured = service_settings().catalog_data_dir
    if not configured:
        return tuple((difficulty, paths().chart_dir(difficulty)) for difficulty in DIFFICULTIES)
    root = Path(configured).expanduser().resolve()
    directories = tuple((difficulty, root / f"{difficulty} Songs") for difficulty in DIFFICULTIES)
    missing = [str(folder) for _difficulty, folder in directories if not folder.is_dir()]
    if missing:
        raise RuntimeError(f"ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR lacks {', '.join(missing)}")
    return directories


def _read_official_charts() -> _OfficialCharts:
    songs: list[dict[str, str]] = []
    paths_by_song_id: dict[str, Path] = {}
    for difficulty, folder in _official_song_directories():
        for chart in sorted(folder.glob("*.txt")):
            try:
                header = read_header(chart)
            except (OSError, ValueError):
                logger.warning("unreadable chart header, chart left out of the song list: %s", chart, exc_info=True)
                continue
            song_id = header.get("Song Name", "")
            if not song_id:
                continue
            title = re.sub(r" \((Hard|Normal|Easy)\)$", "", header.get("Title", ""))
            songs.append({
                "songId": song_id,
                "difficulty": difficulty,
                "primaryElement": header.get("Primary Color", ""),
                "secondaryElement": header.get("Secondary Color", ""),
                "title": title,
                "artist": header.get("Artist", ""),
                "audioId": header.get("Audio Asset ID", "").replace("rbxassetid://", ""),
                "coverImageId": header.get("Cover Image ID", ""),
            })
            paths_by_song_id.setdefault(song_id, chart)
    return _OfficialCharts(tuple(songs), paths_by_song_id)


def _official_charts() -> _OfficialCharts:
    """The official charts, read once: requests never stat the chart library (on the HDD that costs ~0.4 s)."""
    global _official_charts_cache
    with _official_charts_lock:
        if _official_charts_cache is None:
            _official_charts_cache = _read_official_charts()
        return _official_charts_cache


def clear_official_charts() -> None:
    global _official_charts_cache
    with _official_charts_lock:
        _official_charts_cache = None


def list_official_songs() -> list[dict[str, str]]:
    """The song list for a host picker. Titles lose their difficulty suffix, so a family collapses to one entry."""
    return [dict(song) for song in _official_charts().songs]


def find_official_chart(song_id: str) -> Path:
    """The chart whose Song Name header is exactly `song_id`: hosts echo back a listed songId."""
    chart = _official_charts().paths_by_song_id.get(song_id)
    if chart is None:
        raise RequestError(f"no official chart matches {song_id!r}")
    return chart


# --- requests ----------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SolveRequest:
    job: str
    song_name: str  # the song key of the result rows
    chart_text: str  # with the Song Name and Timing Mode of this solve
    timing_mode: str
    reasoning: str
    uploaded: bool
    custom_pool: dict[str, list[Any]]
    promotes: bool  # into the catalog database

    def key(self) -> str:
        """Two requests join only with the same job and the same inputs: job ids can slug alike."""
        inputs = json.dumps([self.reasoning, self.timing_mode, self.custom_pool, self.chart_text], sort_keys=True)
        return f"{self.job}:{hashlib.sha256(inputs.encode()).hexdigest()[:16]}"

    def worker_payload(self) -> dict[str, Any]:
        return {
            "chartText": self.chart_text,
            "songName": self.song_name,
            "reasoning": self.reasoning,
            "customPool": self.custom_pool,
            "promoteTo": str(paths().database) if self.promotes else None,
            "uploaded": self.uploaded,
        }


def _job_slug(value: Any) -> str:
    """A job id as a directory name: bounded and unable to climb out of the run root."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("_")[:80]
    return slug if slug.strip(".") else "job"


def _with_solve_headers(chart_text: str, song_name: str, timing_mode: str) -> str:
    """The chart with this solve's Song Name (the rows' key; Mini Ascension reads it) and Timing Mode. Every other header
    stays: the timeline cache key reads them, so an official chart finds its catalog frontier."""
    lines = chart_text.splitlines()
    for header, value in (("Timing Mode", timing_mode), ("Song Name", song_name)):
        position = next((i for i, line in enumerate(lines) if line.startswith(f"{header}\t")), None)
        if position is None:
            lines.insert(0, f"{header}\t{value}")
        else:
            lines[position] = f"{header}\t{value}"
    return "\n".join(lines) + "\n"


def _check_uploaded_chart(chart_text: str) -> None:
    lines = [line.strip() for line in chart_text.splitlines()]
    if "Song Data" not in lines:
        raise RequestError("custom chart has no Song Data section")
    if sum(map(bool, lines[lines.index("Song Data") + 1 :])) > _MAX_CUSTOM_CHART_EVENTS:
        raise RequestError(f"custom chart exceeds {_MAX_CUSTOM_CHART_EVENTS} replay events")


def _custom_items(raw: Any, field_name: str, stats: dict[str, str], types: tuple[str, ...]) -> list[dict[str, Any]]:
    """A request's custom items (an external boundary: every field is checked)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RequestError(f"{field_name} must be a list")
    if len(raw) > _MAX_CUSTOM_POOL_ITEMS:
        raise RequestError(f"{field_name} exceeds {_MAX_CUSTOM_POOL_ITEMS} items")
    items = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise RequestError("each custom pool item must be a JSON object")
        name = str(entry.get("name") or "").strip()
        if not _CUSTOM_ITEM_NAME_RE.match(name):
            raise RequestError(f"invalid custom item name {name!r}")
        if name.casefold() in seen:
            raise RequestError(f"duplicate custom item name {name!r}")
        seen.add(name.casefold())
        item_type = str(entry.get("type") or "").strip()
        if item_type not in types:
            raise RequestError(f"invalid custom item type {item_type!r} for {name!r}")
        item: dict[str, Any] = {"name": name, "type": item_type}
        for key in stats:
            value = entry.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _MAX_CUSTOM_STAT:
                raise RequestError(f"custom item {name!r} stat {key!r} must be an integer in 0..{_MAX_CUSTOM_STAT}")
            item[key] = value
        items.append(item)
    return items


def _excluded_names(request: dict[str, Any], field_name: str) -> list[str]:
    raw = request.get(field_name)
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > _MAX_EXCLUDED[field_name]:
        raise RequestError(f"{field_name} must be a list of at most {_MAX_EXCLUDED[field_name]} names")
    if not all(isinstance(entry, str) for entry in raw):
        raise RequestError(f"{field_name} entries must be strings")
    names = [name for name in map(str.strip, raw) if name]
    for name in names:
        if not _EXCLUDED_NAME_RE.match(name):
            raise RequestError(f"invalid excluded item name {name!r}")
    return names


def _refuse_taken_names(custom: list[dict[str, Any]], catalog: Iterable[str], excluded: list[str]) -> None:
    taken = {name.casefold() for name in catalog} - {name.casefold() for name in excluded}
    for item in custom:
        if item["name"].casefold() in taken:
            raise RequestError(f"custom item name {item['name']!r} is taken by a catalog item")


def _custom_pool(request: dict[str, Any]) -> dict[str, list[Any]]:
    """The request's custom items and exclusions. A custom item cannot take the name of a catalog item that stays."""
    gear = _custom_items(request.get("customGear"), "customGear", CUSTOM_GEAR_STATS, _CUSTOM_GEAR_SLOTS)
    minis = _custom_items(request.get("customMinis"), "customMinis", CUSTOM_MINI_STATS, _CUSTOM_MINI_TYPES)
    excluded_gear, excluded_minis = _excluded_names(request, "excludeGear"), _excluded_names(request, "excludeMinis")
    if gear or minis:
        catalog = load_catalog(paths().game_export)
        _refuse_taken_names(gear, catalog.gears, excluded_gear)
        _refuse_taken_names(minis, catalog.minis, excluded_minis)
    return {"customGear": gear, "customMinis": minis, "excludeGear": excluded_gear, "excludeMinis": excluded_minis}


def parse_request(request: dict[str, Any]) -> SolveRequest:
    job = _job_slug(request.get("jobId"))
    uploaded_text = str(request.get("chartText") or "").strip()
    song_id = str(request.get("targetSongId") or "").strip()
    if uploaded_text:
        chart_text, song_name = uploaded_text + "\n", job
        _check_uploaded_chart(chart_text)
    elif song_id:
        chart_text, song_name = find_official_chart(song_id).read_text(encoding="utf-8"), song_id
    else:
        raise RequestError("request must include targetSongId or chartText")
    timing_mode = str(request.get("timingMode") or "non-precise").strip().lower()
    if timing_mode not in TIMING_MODES:
        raise RequestError(f"unknown timingMode {request.get('timingMode')!r}")
    reasoning = str(request.get("reasoning") or "default").strip().lower()
    if reasoning not in REASONING_LEVELS:
        raise RequestError(f"unknown reasoning {request.get('reasoning')!r}")
    pool = _custom_pool(request)
    return SolveRequest(job, song_name, _with_solve_headers(chart_text, song_name, timing_mode), timing_mode, reasoning,
                        uploaded=bool(uploaded_text), custom_pool=pool, promotes=not uploaded_text and not any(pool.values()))


# --- solves ------------------------------------------------------------------

def _run_root() -> Path:
    configured = service_settings().run_dir
    return Path(configured) if configured else paths().bin_path("robeatsmeta_api_runs")


class _SolveWorker:
    """A service_worker process answering one JSON line per request. It starts on its first request and a failure that
    needs a new process stops it. `frontier_root`: its own frontier caches (default: the shared ones)."""

    _module = "gear_optimizer.service_worker"
    _answer = "loadouts"

    def __init__(self, root: Path, frontier_root: Path | None = None) -> None:
        self._root, self._frontier_root = root, frontier_root
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()

    def _timeout_s(self) -> float:
        return _SOLVE_TIMEOUT_S

    def _frontier_env(self) -> dict[str, str]:
        root = self._frontier_root
        return {
            "TIMELINE_FRONTIER_CACHE_DIR": str(root / "timeline" if root else paths().timeline_cache),
            "FG_RESPONSE_FRONTIER_CACHE_DIR": str(root / "fg" if root else paths().fg_cache),
        }

    def _start(self) -> subprocess.Popen[str]:
        shutil.rmtree(self._root / "bin", ignore_errors=True)
        (self._root / "bin").mkdir(parents=True)
        env = {
            **os.environ,
            "EVOLUTION_DB_PATH": str(self._root / "bin" / "service_result.db"),
            "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(self._root / "bin"),
            **self._frontier_env(),
            "ROBEATSMETA_OPTIMIZER_SERVICE_MODE": "1",
            "METAFINDER_PROGRESS": "0",
            "METAFINDER_OUTPUT": "0",
            "PYTHONUNBUFFERED": "1",
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", self._module], cwd=str(REPO_ROOT), env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, start_new_session=True,
        )
        self._responses = responses = queue.Queue()

        def read_answers() -> None:
            try:
                for line in proc.stdout:
                    try:
                        responses.put(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("solve worker emitted non-JSON output: %s", line.rstrip())
            finally:
                responses.put({"ok": False, "error": "solve worker exited", "restart": True})

        def drain_stderr() -> None:
            for line in proc.stderr:
                logger.debug("[solve-worker] %s", line.rstrip())

        threading.Thread(target=read_answers, name="solve-worker-stdout", daemon=True).start()
        threading.Thread(target=drain_stderr, name="solve-worker-stderr", daemon=True).start()
        self._proc = proc
        return proc

    def _stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, signal.SIGKILL)  # with its GPU children
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            logger.warning("solve worker pid %s did not exit within 5 s of SIGKILL", proc.pid)
        proc.stdout.close()
        proc.stderr.close()
        with contextlib.suppress(BrokenPipeError):  # flushing a request the killed worker never read
            proc.stdin.close()

    def request(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        with self._lock:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                self._stop()
                proc = self._start()
            try:
                proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
                proc.stdin.flush()
                response = self._responses.get(timeout=self._timeout_s())
            except queue.Empty as exc:
                self._stop()
                raise RuntimeError(f"the request timed out after {self._timeout_s()} s") from exc
            except OSError as exc:
                self._stop()
                raise RuntimeError("the solve worker disconnected") from exc
            if not response["ok"]:
                if response.get("restart"):
                    self._stop()
                raise RuntimeError(response["error"])
            return response[self._answer]

    def stop(self) -> None:
        with self._lock:
            self._stop()


class _LookupWorker(_SolveWorker):
    """The process that answers score lookups."""

    _module = "gear_optimizer.reverse.worker"
    _answer = "reverse"

    def _timeout_s(self) -> float:
        return _LOOKUP_TIMEOUT_S


class _LookupQueue:
    """Score lookups, in arrival order, on one worker with its own GPU context. Up to _LOOKUPS_QUEUED wait; a host past that
    hears the service is busy."""

    def __init__(self, worker: _SolveWorker) -> None:
        self.worker = worker
        self._turns = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lookup")
        self._places = threading.BoundedSemaphore(_LOOKUPS_QUEUED)

    def lookup(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._places.acquire(blocking=False):
            raise ServiceNotReady("too many score lookups are waiting")
        try:
            return self._turns.submit(self.worker.request, payload).result()
        finally:
            self._places.release()


_warm_worker = _SolveWorker(_run_root() / "persistent_solver")
_lookups = _LookupQueue(_LookupWorker(_run_root() / "lookups"))


def _solve_official(request: SolveRequest) -> list[dict[str, Any]]:
    with _solve_slot():
        return _warm_worker.request(request.worker_payload())


def _solve_uploaded(request: SolveRequest) -> list[dict[str, Any]]:
    """An uploaded chart's frontiers stay out of the shared caches: a worker of its own, in a throwaway workspace."""
    _run_root().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{request.job}-", dir=_run_root()) as workspace:
        worker = _SolveWorker(Path(workspace), frontier_root=Path(workspace))
        with _solve_slot():
            try:
                return worker.request(request.worker_payload())
            finally:
                worker.stop()


@dataclass
class _InFlightSolve:
    done: threading.Event = field(default_factory=threading.Event)
    result: list[dict[str, Any]] | None = None
    error: BaseException | None = None


_in_flight_lock = threading.Lock()
_in_flight: dict[str, _InFlightSolve] = {}


def solve(raw_request: dict[str, Any]) -> list[dict[str, Any]]:
    """Solve one chart and return its T5 leaderboard: the top base + FG rows by loadout hash, as the catalog yields them.
    A retry of a running job joins it."""
    request = parse_request(raw_request)
    key = request.key()
    with _in_flight_lock:
        state = _in_flight.get(key)
        owner = state is None
        if owner:
            state = _in_flight[key] = _InFlightSolve()
    if not owner:
        logger.info("joining the running solve of job %s", request.job)
        state.done.wait()
        if state.error is not None:
            raise state.error
        return state.result
    try:
        state.result = _solve_uploaded(request) if request.uploaded else _solve_official(request)
        return state.result
    except BaseException as exc:
        state.error = exc
        raise
    finally:
        state.done.set()
        with _in_flight_lock:
            del _in_flight[key]


# --- score lookups -----------------------------------------------------------

_SHOWN_NUMBERS = {"accuracy": (int, float), "gearMultiplier": (int, float), "casualScore": (int,), "gearPower": (int,)}


def _shown_numbers(raw: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    shown = {}
    for name in names:
        value = raw.get(name)
        if value is not None:
            if not isinstance(value, _SHOWN_NUMBERS[name]) or isinstance(value, bool) or value < 0:
                raise RequestError(f"{name} must be a non-negative number")
            shown[name] = value
    return shown


def _song_chart(raw: dict[str, Any]) -> str:
    song_id = raw.get("targetSongId")
    if not isinstance(song_id, str) or not song_id:
        raise RequestError("targetSongId is required")
    return str(find_official_chart(song_id))


def parse_lookup(raw: dict[str, Any]) -> dict[str, Any]:
    """What a Top Scores row shows, as the lookup worker takes it."""
    chart, score = _song_chart(raw), raw.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or score <= 0:
        raise RequestError("score must be a positive integer")
    shown = {"chartPath": chart, "score": score, "matchMode": raw.get("matchMode", "Compete")}
    if shown["matchMode"] not in ("Compete", "Casual"):
        raise RequestError("matchMode must be Compete or Casual")
    # The timing mode the page shows: each set's play is planned in it, as the song page plans a build's run.
    shown["timingMode"] = raw.get("timingMode", PRECISE)
    if shown["timingMode"] not in TIMING_MODES:
        raise RequestError(f"timingMode must be one of {', '.join(TIMING_MODES)}")
    return {**shown, **_shown_numbers(raw, tuple(_SHOWN_NUMBERS))}


def parse_prepare(raw: dict[str, Any]) -> dict[str, Any]:
    """A song a player is typing a row of, and its accuracy once typed: the lookup worker readies what that lookup walks."""
    return {"chartPath": _song_chart(raw), "prepare": True, **_shown_numbers(raw, ("accuracy",))}


# --- catalog builds ----------------------------------------------------------
#
# evolution.db is the website's song catalog, a chart only enters it through a promoted official solve, and the website
# refuses to publish while a published chart is unbuilt. So each Data revision solves every official chart the game data
# describes and the database lacks, one at a time. Waiting for the game data is deliberate: its Mini Ascension targets
# change a new song's scores.

def unbuilt_catalog_songs() -> list[tuple[str, str]]:
    """(song, timing mode) of each official chart the game export describes that evolution.db has no build for."""
    candidates = game_song_names(paths().game_export).intersection(_official_charts().paths_by_song_id)
    if not paths().database.exists():
        return sorted((song, mode) for song in candidates for mode in TIMING_MODES)
    conn = schema.connect(paths().database)
    try:
        return sorted((song, mode) for mode in TIMING_MODES for song in candidates - present_songs(conn, mode, candidates))
    finally:
        conn.close()


def build_missing_catalog_songs() -> None:
    missing = unbuilt_catalog_songs()
    if missing:
        print(f"[robeatsmeta-service] building {len(missing)} official chart(s) missing from the catalog", flush=True)
    for song_id, mode in missing:
        digest = hashlib.sha256(f"{song_id}|{mode}".encode()).hexdigest()[:16]
        try:
            solve({"jobId": f"catalog-{digest}", "targetSongId": song_id, "timingMode": mode})
        except ServiceNotReady:
            return
        except Exception:  # noqa: BLE001 - one bad chart must not stop the rest of the catalog
            logger.exception("catalog build failed for %s (%s); the next Data revision retries it", song_id, mode)
            continue
        print(f"[robeatsmeta-service] built catalog entry for {song_id} ({mode})", flush=True)
    if not missing:
        # One official chart solved for nothing: no job waits for a cold worker (12 s, a minute under load).
        song = min(_official_charts().paths_by_song_id)
        warmup = parse_request({"jobId": "warmup", "targetSongId": song, "timingMode": PRECISE})
        with contextlib.suppress(ServiceNotReady):
            _solve_official(replace(warmup, promotes=False))
            print(f"[robeatsmeta-service] solver warm ({song})", flush=True)


def _build_frontier_caches() -> None:
    """Verify every chart's frontier caches, building what a revision lacks."""
    from gear_optimizer.frontier.startup_prebuild import run_startup_cpu_work
    from gear_optimizer.gamedata import stat_curves

    charts = tuple(str(chart) for difficulty in DIFFICULTIES for chart in sorted(paths().chart_dir(difficulty).glob("*.txt")))
    run_startup_cpu_work(charts_by_mode={mode: charts for mode in TIMING_MODES}, curves=stat_curves(),
                         authorize_destructive_rotation=True)


def refresh_data() -> None:
    """Make the service current with the checkout's Data. The cache build runs in a short-lived process: its memory
    high-water would otherwise stay in this long-lived one."""
    with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"),
                             initializer=make_process_background_only) as executor:
        executor.submit(_build_frontier_caches).result()
    clear_official_charts()
    build_missing_catalog_songs()


# --- HTTP --------------------------------------------------------------------

class RoBeatsMetaServiceHandler(BaseHTTPRequestHandler):
    server_version = "RoBeatsMetaOptimizer/3.0"
    timeout = 60  # a client that stalls mid-body must not pin a thread for the life of the process

    def _authorized(self) -> bool:
        token = service_settings().api_token
        return not token or hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}")

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/songs":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        elif not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        else:
            try:
                self._send(HTTPStatus.OK, {"songs": list_official_songs()})
            except Exception as exc:  # noqa: BLE001 - HTTP boundary
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        if path not in {"/optimize", "/reverse", "/reverse/prepare", "/frontiers/refresh"}:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        elif not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        elif path == "/frontiers/refresh":
            clear_official_charts()
            self.server.updater.request_check()  # type: ignore[attr-defined]  # main() sets it before serving
            self._send(HTTPStatus.ACCEPTED, {"queued": True})
        elif path == "/reverse":
            self._answer(lambda request: _lookups.lookup(parse_lookup(request)))
        elif path == "/reverse/prepare":
            self._answer(lambda request: _lookups.lookup(parse_prepare(request)))
        else:
            self._answer(lambda request: {"jobId": request.get("jobId"), "loadouts": solve(request)})

    def _answer(self, work: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        try:
            self._send(HTTPStatus.OK, work(self._read_json()))
        except RequestTooLarge as exc:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
        except RequestError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except ServiceNotReady as exc:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - HTTP boundary
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = self.headers.get("Content-Length")
        if not length or not length.isdigit():
            raise RequestError("missing Content-Length")
        limit = service_settings().max_body_bytes
        if int(length) > limit:
            raise RequestTooLarge(f"request body exceeds {limit} bytes")
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
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[robeatsmeta-service] " + (fmt % args) + "\n")


def _http_server(host: str, port: int) -> ThreadingHTTPServer:
    """The service's HTTP server. After a self-update exec it serves on the socket the previous image handed over: the
    port is never unbound, so a supervisor watching the port owner never starts a second service."""
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
    settings = service_settings()
    parser = argparse.ArgumentParser(description="RoBeatsMeta optimizer service")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    args = parser.parse_args(argv)
    try:
        loopback_bind = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        loopback_bind = args.host.strip().lower() == "localhost"
    if not loopback_bind and not settings.api_token:
        raise RuntimeError("ROBEATSMETA_OPTIMIZER_API_TOKEN is required for a non-loopback bind")
    # launchd runs a single instance, so anything here was orphaned by a crash.
    shutil.rmtree(_run_root(), ignore_errors=True)
    server = _http_server(args.host, args.port)
    server.daemon_threads = True
    restart_revision: list[str] = []
    serving = threading.Event()

    def restart(commit: str) -> None:
        restart_revision[:] = [commit]

        def shutdown_when_serving() -> None:
            if serving.wait(timeout=30):
                server.shutdown()

        threading.Thread(target=shutdown_when_serving, name="service-restart", daemon=True).start()

    def handle_shutdown_signal(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, name="service-signal-shutdown", daemon=True).start()

    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    updater = ServiceUpdater(REPO_ROOT, drain=_drain_solves, resume=_resume_solves, restart=restart, refresh=refresh_data)
    server.updater = updater  # type: ignore[attr-defined]
    threading.Thread(target=updater.serve_forever, name="service-updater", daemon=True).start()
    print(f"[robeatsmeta-service] listening on http://{args.host}:{args.port}", flush=True)
    try:
        serving.set()
        server.serve_forever()  # SIGINT/SIGTERM shut it down through handle_shutdown_signal
    finally:
        _warm_worker.stop()
        _lookups.worker.stop()
        updater.stop()
        if not restart_revision:
            server.server_close()
    if restart_revision:
        print(f"[robeatsmeta-service] restarting into fetched revision {restart_revision[0][:12]}", flush=True)
        # The next image serves on this listening socket (connections wait in its backlog meanwhile).
        server.socket.set_inheritable(True)
        os.environ[_LISTENER_FD_ENV] = str(server.socket.fileno())
        command = list(sys.argv[1:] if argv is None else argv)
        os.execv(sys.executable, [sys.executable, "-m", "gear_optimizer.robeatsmeta_service", *command])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
