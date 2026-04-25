"""
Song processing orchestration.

This module handles song file reading, optimization execution, and result persistence.
Contains the main process_song_task function that coordinates:
- Song data loading
- Fixed stats calculation
- GA optimization
- Force greats evaluation
- Database persistence

REFACTORED: Helper functions extracted to .helpers.song_helpers for maintainability.
"""

import atexit
import contextlib
import gc
import hashlib
import json
import logging
import os
import sys
import threading
import time
import traceback
from collections import OrderedDict
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Callable, cast

import numpy as np
from cachetools import LRUCache

from ..data.models import Tee, WarnOnce
from ..core.env_config import ENV
from ..core.result_payloads import build_error_payload
from ..core.types import SongResultPayload
from ..core.constants import (
    LOADOUTS_PER_SONG_LIMIT,
    FG_CANDIDATE_LIMIT,
    PATHS,
)

from ..core.config import (
    read_fg_candidate_limit,
    read_fg_search_radius,
    read_fg_solver_mode,
    read_outer_search_engine,
)
from ..solver.genetic import GA_POPULATION_SIZE, solve_coevolution_genetic
from ..solver.scoring import (
    GEM_SOLVER_CACHE,
    FEVER_TIMELINE_CACHE,
    FG_CACHE,
    solve_best_fever_combination,
)
from ..solver.gpu_profiler import get_gpu_profiler
from ..solver.solver_common import SolverContext, prepare_solver_context
from ..core.memory import log_memory_usage
from ..core.utils import cfg_from_dict
from ..core.array_signature import array_sig16
from ..helpers.song_helpers import (
    load_database_progress_baseline,
    setup_song_config,
    build_loadout_entries,
    # Candidate selection for FG funnel (keeps low-base/high-FG candidates)
    # without increasing FG_CandidateLimit.
    process_force_greats,
    build_db_payload,
    build_persistence_entries,
    print_results,
)
from ..helpers.song_helpers.persistence import make_build_details_fn, evaluate_progress_record_update
from ..helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from ..helpers.song_helpers.ga_entry_utils import materialize_candidate_names, materialize_entry_names
from ..helpers.song_helpers.item_utils import names_list

# Global warn-once instance
WARN_ONCE = WarnOnce()

# Global counter for deterministic garbage collection
_SONG_GC_COUNTER = 0
_SONG_GC_GEN2_INTERVAL = max(1, int(os.environ.get("SONG_GC_GEN2_INTERVAL", "25") or "25"))

# Performance timing flag (set via env var)
PERF_TIMING_ENABLED = bool(getattr(ENV, "perf_timing_unconditional", False))
_CAPTURE_SONG_LOG_PAYLOAD = str(os.environ.get("SONG_CAPTURE_LOG_PAYLOAD", "0") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# GPU profiler for songs/hour tracking
_gpu_profiler = get_gpu_profiler()


@dataclass
class SongContext:
    fp: str
    found_song_name: str
    queue_label: str
    effective_difficulty: str
    cfg_dict: dict[str, Any]
    cfg: Any
    paths: Any
    ref_arrays: dict[str, Any]
    all_gears: list[dict]
    all_minis: list[dict]
    gears_by_name: dict[str, Any]
    minis_by_name: dict[str, Any]
    use_evo_db: bool
    auto_buff: bool
    ga_depth: int
    status_queue: Any
    defer_post: bool
    emit: Callable[[str], None]
    stage_timing: dict[str, float]
    repeat_index: int
    repeat_total: int
    fg_debug: bool
    calc_song: dict[str, Any]
    meta_primary_color: str
    meta_secondary_color: str
    ga_settings: Any
    fixed_stats: dict[str, Any]
    current_gear_stats: dict[str, Any]
    current_gear_list: list[dict]
    current_mini_stats: dict[str, Any]
    current_mini_list: list[dict]
    meta_finder: bool
    enable_fever: bool
    enable_mini: bool
    enable_gear: bool
    force_greats_mode: bool
    force_greats_finder: bool
    force_greats_config: Any
    manual_force_greats: bool
    baseline_team_buff: str
    db_key: str
    prev_record: Any
    known_loadouts: Any
    db_best_score: int
    db_best_fg_score: int
    attempt_lifetime: int
    attempts_first: int
    prev_attempts_first: int
    db_baseline_valid: bool
    outer_engine: str = "ga"
    pre_prune_mode: str = "auto"
    fg_solver_mode: str = "finder"
    fg_search_radius: int | None = None
    gpu_mode: bool = True
    gpu_song_slot: int = 0
    ga_seed: int | None = None
    solver_ctx: SolverContext | None = None


@dataclass
class OuterSearchResult:
    best_data: dict[str, Any] | None
    best_gear: list[dict]
    best_minis: list[dict]
    all_evaluated: list[dict[str, Any]]
    ga_candidates: list[dict[str, Any]]
    wall_sec: float = 0.0


@dataclass
class FGResult:
    fg_variants: list[dict[str, Any]] = field(default_factory=list)
    loadout_entries: Any = None
    wall_sec: float = 0.0


class _NullLogBuffer:
    """File-like sink that discards writes and avoids per-song StringIO growth."""

    __slots__ = ()

    def write(self, data):
        try:
            return len(data)
        except Exception:
            return 0

    def flush(self):
        return None

    def getvalue(self):
        return ""

    def close(self):
        return None


# ---------------------------------------------------------------------------
# Base calc_song cache (pre-timing-envelope mutation), keyed by file path + config hash.
#
# Motivation:
# - When the same song is processed multiple times (SongRepeats / repeated queue),
#   we were fully parsing the file + building arrays on every run.
# - Timing-envelope FG streams are attached per run, so we cache the base
#   calc_song and clone it before adding runtime analysis payloads.
# ---------------------------------------------------------------------------
_CFG_HASH_CACHE: dict[int, tuple[int, str]] = {}
_CFG_HASH_CACHE_LOCK = threading.Lock()


def _stable_cfg_hash(cfg_dict: dict | None) -> str:
    if not isinstance(cfg_dict, dict) or not cfg_dict:
        return "cfg0"
    cfg_id = int(id(cfg_dict))
    cfg_len = int(len(cfg_dict))
    with _CFG_HASH_CACHE_LOCK:
        cached = _CFG_HASH_CACHE.get(cfg_id)
        if cached is not None and int(cached[0]) == cfg_len:
            return str(cached[1])
    try:
        payload = json.dumps(cfg_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception:
        payload = repr(sorted(cfg_dict.items(), key=lambda kv: str(kv[0])))
    h = hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()
    out = h[:16]
    with _CFG_HASH_CACHE_LOCK:
        _CFG_HASH_CACHE[cfg_id] = (cfg_len, out)
        if len(_CFG_HASH_CACHE) > 32:
            _CFG_HASH_CACHE.clear()
    return out


_BASE_CALC_SONG_CACHE_MAX = max(1, int(os.environ.get("BASE_CALC_SONG_CACHE_MAX", "64") or "64"))
_BASE_CALC_SONG_CACHE: LRUCache = LRUCache(maxsize=_BASE_CALC_SONG_CACHE_MAX)
_BASE_CALC_SONG_CACHE_LOCK = threading.Lock()

_SONG_HEADER_CACHE_PATH = PATHS.bin_path("song_header_cache.json")
_SONG_HEADER_CACHE_MAX = max(256, int(os.environ.get("SONG_HEADER_CACHE_MAX", "4096") or "4096"))
_SONG_HEADER_CACHE_LOCK = threading.Lock()
_SONG_HEADER_CACHE: OrderedDict[str, dict[str, object]] = OrderedDict()
_SONG_HEADER_CACHE_LOADED = False
_SONG_HEADER_CACHE_DIRTY = False


def clone_calc_song(calc_song: dict) -> dict:
    """
    Clone a calc_song dict for per-run mutation.

    Arrays are shared by reference (read-only); dicts are copied.
    """
    if not isinstance(calc_song, dict):
        return {}
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    return {"metadata": dict(meta), "song_data": dict(song_data)}


def _build_base_calc_song_from_file(fp: str) -> dict:
    song_data = read_song_file(fp)

    timestamps_raw = song_data.get("timestamps")
    note_types_raw = song_data.get("note_types")
    if isinstance(timestamps_raw, np.ndarray):
        song_timestamps_np = timestamps_raw.astype(np.float32, copy=False)
    else:
        song_timestamps_np = np.asarray(timestamps_raw if timestamps_raw is not None else [], dtype=np.float32)

    if isinstance(note_types_raw, np.ndarray):
        song_note_types_np = note_types_raw.astype(np.int16, copy=False)
    else:
        song_note_types_np = np.asarray(note_types_raw if note_types_raw is not None else [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    # Cache stable content signatures on the base calc_song so GPU timeline caching
    # doesn't need to hash full arrays on every request (pickling breaks `id()` reuse).
    ts_sig = array_sig16(song_timestamps_np)
    nt_sig = array_sig16(song_note_types_np)

    return {
        "metadata": song_data.get("song_details", {}) or {},
        "song_data": {
            "timestamps": song_timestamps_np,
            "chart_timestamps": song_timestamps_np,
            "note_types": song_note_types_np,
            "_timestamps_sig": ts_sig,
            "_chart_timestamps_sig": ts_sig,
            "_note_types_sig": nt_sig,
        },
    }


def get_base_calc_song(fp: str, cfg_dict: dict | None = None) -> dict:
    """
    Get cached base calc_song for this file/config pair.

    The returned object is shared; callers must clone via clone_calc_song()
    before applying timing-envelope streams or any other per-run mutation.
    """
    if not fp:
        return {}

    abs_fp = os.path.abspath(fp)
    cfg_h = _stable_cfg_hash(cfg_dict)
    key = (abs_fp, cfg_h)

    try:
        st = os.stat(abs_fp)
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
    except Exception:
        mtime_ns = -1

    with _BASE_CALC_SONG_CACHE_LOCK:
        entry = _BASE_CALC_SONG_CACHE.get(key)
        if entry is not None:
            cached_mtime_ns, cached_calc_song = entry
            if int(cached_mtime_ns) == int(mtime_ns) and isinstance(cached_calc_song, dict):
                return cached_calc_song

    base = _build_base_calc_song_from_file(abs_fp)
    with _BASE_CALC_SONG_CACHE_LOCK:
        _BASE_CALC_SONG_CACHE[key] = (int(mtime_ns), base)
    return base


def _prune_song_header_cache_locked() -> None:
    while len(_SONG_HEADER_CACHE) > int(_SONG_HEADER_CACHE_MAX):
        _SONG_HEADER_CACHE.popitem(last=False)


def _load_song_header_cache_locked() -> None:
    global _SONG_HEADER_CACHE_LOADED
    if _SONG_HEADER_CACHE_LOADED:
        return
    _SONG_HEADER_CACHE_LOADED = True
    try:
        with open(_SONG_HEADER_CACHE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    for key, entry in payload.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        try:
            mtime_ns = int(entry.get("mtime_ns", -1))
            file_size = int(entry.get("size", -1))
        except Exception:
            continue
        meta = entry.get("meta")
        if meta is not None and not isinstance(meta, dict):
            continue
        _SONG_HEADER_CACHE[key] = {"mtime_ns": mtime_ns, "size": file_size, "meta": meta}
    _prune_song_header_cache_locked()


def _flush_song_header_cache() -> None:
    global _SONG_HEADER_CACHE_DIRTY
    with _SONG_HEADER_CACHE_LOCK:
        if not _SONG_HEADER_CACHE_DIRTY:
            return
        payload = {
            key: {
                "mtime_ns": int(str(entry.get("mtime_ns", -1) or -1)),
                "size": int(str(entry.get("size", -1) or -1)),
                "meta": entry.get("meta"),
            }
            for key, entry in _SONG_HEADER_CACHE.items()
        }
        _SONG_HEADER_CACHE_DIRTY = False
    try:
        os.makedirs(os.path.dirname(_SONG_HEADER_CACHE_PATH), exist_ok=True)
        tmp_path = f"{_SONG_HEADER_CACHE_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, separators=(",", ":"))
        os.replace(tmp_path, _SONG_HEADER_CACHE_PATH)
    except Exception:
        with _SONG_HEADER_CACHE_LOCK:
            _SONG_HEADER_CACHE_DIRTY = True


def _reset_song_header_cache_for_tests() -> None:
    global _SONG_HEADER_CACHE_LOADED, _SONG_HEADER_CACHE_DIRTY
    with _SONG_HEADER_CACHE_LOCK:
        _SONG_HEADER_CACHE.clear()
        _SONG_HEADER_CACHE_LOADED = False
        _SONG_HEADER_CACHE_DIRTY = False


atexit.register(_flush_song_header_cache)


def scan_song_header(fp):
    """
    Scan first 20 lines of song file for metadata (fast check).

    Args:
        fp: File path to song file

    Returns:
        dict: Metadata dictionary or None if parse fails
    """
    abs_fp = os.path.abspath(fp)
    try:
        st = os.stat(abs_fp)
        mtime_ns_raw = getattr(st, "st_mtime_ns", None)
        mtime_ns = int(mtime_ns_raw) if isinstance(mtime_ns_raw, int) else int(st.st_mtime * 1e9)
        file_size = int(st.st_size)
    except Exception:
        mtime_ns = -1
        file_size = -1

    with _SONG_HEADER_CACHE_LOCK:
        _load_song_header_cache_locked()
        cached = _SONG_HEADER_CACHE.get(abs_fp)
        if isinstance(cached, dict):
            try:
                if int(str(cached.get("mtime_ns", -2) or -2)) == int(mtime_ns) and int(
                    str(cached.get("size", -2) or -2)
                ) == int(file_size):
                    _SONG_HEADER_CACHE.move_to_end(abs_fp)
                    meta_cached = cached.get("meta")
                    return dict(meta_cached) if isinstance(meta_cached, dict) else None
            except Exception:
                pass

    meta = {"Song Name": "", "Primary Color": "", "Secondary Color": "", "Difficulty": ""}
    try:
        with open(abs_fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                # Handle both TAB and COLON separators
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
                elif ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        result = meta if meta["Song Name"] else None
        with _SONG_HEADER_CACHE_LOCK:
            _SONG_HEADER_CACHE[abs_fp] = {"mtime_ns": int(mtime_ns), "size": int(file_size), "meta": result}
            _SONG_HEADER_CACHE.move_to_end(abs_fp)
            _prune_song_header_cache_locked()
            global _SONG_HEADER_CACHE_DIRTY
            _SONG_HEADER_CACHE_DIRTY = True
        return dict(result) if isinstance(result, dict) else None
    except Exception:
        return None


def _nonfever_counts_from_config(config: object) -> tuple[int, ...]:
    if not isinstance(config, dict) or not config:
        return ()
    pairs: list[tuple[int, int]] = []
    for key, val in config.items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "").strip()) - 1
        except Exception:
            continue
        try:
            cnt = int(val or 0)
        except Exception:
            cnt = 0
        pairs.append((idx, max(0, cnt)))
    if not pairs:
        return ()
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    if max_idx < 0:
        return ()
    out = [0] * (max_idx + 1)
    for idx, cnt in pairs:
        if 0 <= idx < len(out):
            out[idx] = int(cnt)
    if sum(out) <= 0:
        return ()
    return tuple(int(v) for v in out)


def read_song_file(fp):
    """
    Read complete song file including metadata and note timestamps.

    Args:
        fp: File path to song file

    Returns:
        dict: Song data with song_details and timestamps
    """
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": np.empty((0,), dtype=np.float32),
        "note_types": np.empty((0,), dtype=np.int16),
    }
    if not fp:
        return data
    try:
        found_song_data = False
        note_lines = []
        with open(fp, "r", encoding="utf-8-sig") as f:
            for raw_line in f:
                line = raw_line.rstrip("\r\n")
                stripped = line.strip()
                if not found_song_data:
                    if stripped == "Song Data":
                        found_song_data = True
                        continue
                    if not stripped:
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in data["song_details"]:
                            data["song_details"][key] = parts[1].strip() or "0"
                    continue

                if not stripped:
                    continue
                c = stripped[0]
                if ("0" <= c <= "9") or c == ".":
                    note_lines.append(line)

        if not found_song_data:
            return data

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = np.asarray(nd[:, 0], dtype=np.float32)
                    # Column 4 is the note type: 1=normal, 2=held head, 3=held tail.
                    # Keep as int so we can apply held-tail timing rules when needed.
                    data["note_types"] = nd[:, 3].astype(np.int16, copy=False)
        return data
    except Exception as exc:
        WARN_ONCE.warn("song-file", f"Failed to read song file {fp}: {exc}")
        return data


def _setup_song_context(
    *,
    fp: str,
    found_song_name: str,
    effective_difficulty: str,
    cfg_dict: dict[str, Any],
    paths: Any,
    ref_arrays: dict[str, Any],
    all_gears: list[dict],
    all_minis: list[dict],
    gears_by_name: dict[str, Any],
    minis_by_name: dict[str, Any],
    use_evo_db: bool,
    auto_buff: bool,
    ga_depth: int,
    status_queue: Any,
    fg_debug: bool,
    defer_post: bool,
    preloaded_calc_song: dict[str, Any] | None,
    repeat_index: int,
    repeat_total: int,
    ga_seed: int | None,
    emit: Callable[[str], None],
    stage_timing: dict[str, float],
) -> SongContext:
    cfg = cfg_from_dict(cfg_dict)
    gpu_mode_requested = True
    try:
        gpu_mode_requested = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=True)
    except Exception:
        gpu_mode_requested = True
    if not gpu_mode_requested:
        print("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
    gpu_mode = True

    if isinstance(preloaded_calc_song, dict) and preloaded_calc_song.get("song_data"):
        calc_song = clone_calc_song(preloaded_calc_song)
        stage_timing["cpu_read_sec"] = 0.0
    else:
        t_read0 = time.perf_counter()
        base_calc_song = get_base_calc_song(fp, cfg_dict)
        calc_song = clone_calc_song(base_calc_song)
        stage_timing["cpu_read_sec"] = time.perf_counter() - t_read0

    try:
        song_data = calc_song.get("song_data", {}) or {}
        if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
            song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)
    except Exception:
        pass

    try:
        from ..solver.timing_envelope import apply_timing_envelope

        t_sim0 = time.perf_counter()
        sim_info = apply_timing_envelope(calc_song)
        if sim_info is not None:
            stage_timing["cpu_timing_envelope_sec"] = time.perf_counter() - t_sim0
            try:
                print(
                    f"[TimingEnvelope] Applied (mode={sim_info.get('mode')}, "
                    f"great={sim_info.get('great_mode')}, notes={sim_info.get('notes')})"
                )
            except Exception:
                pass
    except Exception:
        pass

    meta_primary_color = calc_song["metadata"].get("Primary Color", "")
    meta_secondary_color = calc_song["metadata"].get("Secondary Color", "")

    t_setup0 = time.perf_counter()
    (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)
    stage_timing["cpu_setup_sec"] = time.perf_counter() - t_setup0

    try:
        from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg

        baseline_team_buff = resolve_baseline_team_buff_from_cfg(cfg)
    except Exception:
        baseline_team_buff = "T5"

    from gear_optimizer.helpers.song_helpers.database_context import build_db_key

    db_key = build_db_key(found_song_name, calc_song)

    t_db0 = time.perf_counter()
    (
        prev_record,
        known_loadouts,
        db_best_score,
        db_best_fg_score,
        attempt_lifetime,
        prev_attempts_first,
        db_baseline_valid,
    ) = load_database_progress_baseline(
        db_key,
        use_evo_db,
        gears_by_name,
        minis_by_name,
        allow_fallback=False,
        team_buff=str(baseline_team_buff or "T5"),
    )
    stage_timing["cpu_db_load_sec"] = time.perf_counter() - t_db0

    attempts_first = (prev_attempts_first + 1) if prev_attempts_first else 1
    emit("START")
    stage_timing["cpu_prep_sec"] = sum(
        float(stage_timing.get(key, 0.0) or 0.0)
        for key in ("cpu_read_sec", "cpu_human_hit_sim_sec", "cpu_setup_sec", "cpu_db_load_sec")
    )

    outer_engine = "ga"
    pre_prune_mode = "none"
    fg_solver_mode = read_fg_solver_mode(cfg, default="finder")
    fg_search_radius = read_fg_search_radius(cfg)
    if enable_gear or enable_mini:
        outer_engine = read_outer_search_engine(cfg, default="ga")

    return SongContext(
        fp=fp,
        found_song_name=found_song_name,
        queue_label=str(found_song_name),
        effective_difficulty=effective_difficulty,
        cfg_dict=cfg_dict,
        cfg=cfg,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        use_evo_db=bool(use_evo_db),
        auto_buff=bool(auto_buff),
        ga_depth=int(ga_depth),
        status_queue=status_queue,
        defer_post=bool(defer_post),
        emit=emit,
        stage_timing=stage_timing,
        repeat_index=int(repeat_index),
        repeat_total=int(repeat_total),
        fg_debug=bool(fg_debug),
        calc_song=calc_song,
        meta_primary_color=str(meta_primary_color or ""),
        meta_secondary_color=str(meta_secondary_color or ""),
        ga_settings=ga_settings,
        fixed_stats=fixed_stats,
        current_gear_stats=current_gear_stats,
        current_gear_list=current_gear_list,
        current_mini_stats=current_mini_stats,
        current_mini_list=current_mini_list,
        meta_finder=bool(meta_finder),
        enable_fever=bool(enable_fever),
        enable_mini=bool(enable_mini),
        enable_gear=bool(enable_gear),
        force_greats_mode=bool(force_greats_mode),
        force_greats_finder=bool(force_greats_finder),
        force_greats_config=force_greats_config,
        manual_force_greats=bool(manual_force_greats),
        baseline_team_buff=str(baseline_team_buff or "T5"),
        db_key=db_key,
        prev_record=prev_record,
        known_loadouts=known_loadouts,
        db_best_score=int(db_best_score or 0),
        db_best_fg_score=int(db_best_fg_score or 0),
        attempt_lifetime=int(attempt_lifetime or 0),
        attempts_first=int(attempts_first),
        prev_attempts_first=int(prev_attempts_first or 0),
        db_baseline_valid=bool(db_baseline_valid),
        outer_engine=outer_engine,
        pre_prune_mode=pre_prune_mode,
        fg_solver_mode=fg_solver_mode,
        fg_search_radius=fg_search_radius,
        gpu_mode=bool(gpu_mode),
        gpu_song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=ga_seed,
    )


def _run_outer_search(ctx: SongContext) -> OuterSearchResult:
    if ctx.enable_gear or ctx.enable_mini:
        if ctx.gpu_mode:
            try:
                ctx.gpu_song_slot = int(ctx.calc_song.get("_gpu_song_slot", 0) or 0)
            except Exception:
                ctx.gpu_song_slot = 0
            try:
                ctx.calc_song["_gpu_song_slot"] = int(ctx.gpu_song_slot)
            except Exception:
                pass
            try:
                from gear_optimizer.solver.taichi_gem import fields as gpu_fields

                gpu_fields.configure_ga_run_buffers(
                    max_runs=ctx.ga_settings.multi_start,
                    max_genomes=GA_POPULATION_SIZE,
                )
            except Exception:
                pass

        ctx.solver_ctx = prepare_solver_context(
            ctx.cfg,
            ctx.fixed_stats,
            ctx.calc_song,
            ctx.ref_arrays,
            ctx.all_gears,
            ctx.all_minis,
            optimize_gear=ctx.enable_gear,
            optimize_minis=ctx.enable_mini,
            fixed_gear=ctx.current_gear_list,
            fixed_minis=ctx.current_mini_list,
            pre_prune_mode="none",
            status_cb=lambda message: ctx.emit(message),
            song_slot=int(ctx.gpu_song_slot),
        )

        ga_start = time.perf_counter()
        best_data, best_gear, best_minis, _, _, _, all_evaluated = solve_coevolution_genetic(
            ctx.cfg,
            ctx.fixed_stats,
            ctx.paths,
            ctx.calc_song,
            ctx.ref_arrays,
            ctx.all_gears,
            ctx.all_minis,
            ctx.gears_by_name,
            ctx.minis_by_name,
            optimize_gear=ctx.enable_gear,
            optimize_minis=ctx.enable_mini,
            fixed_gear=ctx.current_gear_list,
            fixed_minis=ctx.current_mini_list,
            ga_depth=ctx.ga_depth,
            db_seed=ctx.prev_record if ctx.prev_record else None,
            ga_settings=ctx.ga_settings,
            status_cb=lambda message: ctx.emit(message),
            executor=None,
            known_loadouts=ctx.known_loadouts,
            song_slot=int(ctx.gpu_song_slot),
            ga_seed=ctx.ga_seed,
            solver_ctx=ctx.solver_ctx,
        )
        wall_sec = time.perf_counter() - ga_start
        if PERF_TIMING_ENABLED:
            print(f"[PERF] GA: {wall_sec:.2f}s")
        if ctx.known_loadouts:
            ctx.known_loadouts.clear()
    else:
        all_evaluated = []
        if not ctx.enable_fever:
            print("[Calculate-Only Mode] MetaFinder disabled - calculating score with current config...")

        combined_stats = ctx.fixed_stats.copy()
        for key, value in ctx.current_gear_stats.items():
            combined_stats[key] = combined_stats.get(key, 0) + value
        for key, value in ctx.current_mini_stats.items():
            combined_stats[key] = combined_stats.get(key, 0) + value

        best_data = solve_best_fever_combination(
            ctx.cfg,
            combined_stats,
            ctx.calc_song,
            ctx.ref_arrays,
            silent=ctx.enable_fever,
            skip_optimizer=not ctx.enable_fever,
        )
        best_gear = ctx.current_gear_list
        best_minis = ctx.current_mini_list
        if best_data:
            base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
            all_evaluated = [
                {
                    "Score": base_score,
                    "BaseScore": base_score,
                    "Gear": best_gear,
                    "Minis": best_minis,
                    "Data": best_data,
                }
            ]
        wall_sec = 0.0

    ga_candidates = list(all_evaluated or [])
    if best_data and best_gear and best_minis:
        base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
        ga_candidates.append(
            {
                "Score": base_score,
                "BaseScore": base_score,
                "Gear": best_gear,
                "Minis": best_minis,
                "Data": best_data,
            }
        )

    return OuterSearchResult(
        best_data=best_data,
        best_gear=list(best_gear or []),
        best_minis=list(best_minis or []),
        all_evaluated=list(all_evaluated or []),
        ga_candidates=ga_candidates,
        wall_sec=float(wall_sec),
    )


def _run_force_greats(ctx: SongContext, outer: OuterSearchResult) -> FGResult:
    ga_candidates = list(outer.ga_candidates or [])
    fg_candidate_limit = read_fg_candidate_limit(
        ctx.cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    if ctx.manual_force_greats or ctx.force_greats_finder:
        ga_candidates = select_fg_candidates(
            ga_candidates,
            limit=fg_candidate_limit,
            primary_color=str(ctx.meta_primary_color or ""),
            secondary_color=str(ctx.meta_secondary_color or ""),
        )

    build_details = make_build_details_fn(ctx.meta_primary_color, ctx.meta_secondary_color, ctx.effective_difficulty)
    fg_variants: list[dict[str, Any]] = []
    loadout_entries = None
    fg_wall_sec = 0.0
    direct_ga_candidates_for_fg = bool(ctx.outer_engine == "ga" and ctx.force_greats_finder and ctx.gpu_mode)

    if ctx.fg_solver_mode in {"finder", "manual"} and (ctx.manual_force_greats or ctx.force_greats_finder):
        loadout_entries = build_loadout_entries(
            ctx.found_song_name,
            ctx.use_evo_db,
            [] if direct_ga_candidates_for_fg else ga_candidates,
            fg_candidate_limit,
            ctx.gears_by_name,
            ctx.minis_by_name,
            build_details,
            team_buff=str(ctx.baseline_team_buff or "T5"),
            materialize_ga_details=False,
        )

    if ctx.fg_solver_mode in {"finder", "manual"} and (ctx.manual_force_greats or ctx.force_greats_finder):
        fg_start = time.perf_counter()
        fg_variants = process_force_greats(
            loadout_entries,
            ctx.manual_force_greats,
            ctx.force_greats_finder,
            ctx.force_greats_config,
            ctx.calc_song,
            ctx.ref_arrays,
            ctx.meta_primary_color,
            build_details,
            use_gpu=ctx.gpu_mode,
            fg_search_radius=ctx.fg_search_radius,
            perf_timing=PERF_TIMING_ENABLED,
            ga_candidates=ga_candidates if direct_ga_candidates_for_fg else None,
            ga_registry=ctx.solver_ctx.registry if direct_ga_candidates_for_fg and ctx.solver_ctx is not None else None,
        )
        fg_wall_sec = time.perf_counter() - fg_start
        if PERF_TIMING_ENABLED:
            n_loadouts = len(loadout_entries) if loadout_entries else 0
            print(f"[PERF] ForceGreats: {fg_wall_sec:.2f}s ({n_loadouts} loadouts, finder={ctx.force_greats_finder})")

    outer.ga_candidates = ga_candidates
    return FGResult(fg_variants=fg_variants, loadout_entries=loadout_entries, wall_sec=float(fg_wall_sec))


def _build_and_persist(
    ctx: SongContext,
    outer: OuterSearchResult,
    fg: FGResult,
    *,
    buf: Any,
    capture_log_payload: bool,
) -> SongResultPayload:
    build_details = make_build_details_fn(ctx.meta_primary_color, ctx.meta_secondary_color, ctx.effective_difficulty)
    db_payload = None
    persist_entries = None
    buf_content = ""

    if ctx.defer_post and outer.best_data:

        def _compact_items(items):
            return names_list(items)

        def _compact_fg_variants(variants):
            out = []
            for variant in variants or []:
                if not isinstance(variant, dict):
                    continue
                out.append(
                    {
                        "score": variant.get("score", 0),
                        "fg_score": variant.get("fg_score", 0),
                        "gear": _compact_items(variant.get("gear")),
                        "minis": _compact_items(variant.get("minis")),
                        "data": variant.get("data") or {},
                    }
                )
            return out

        def _compact_ga_candidates(candidates):
            out = []
            for candidate in candidates or []:
                if not isinstance(candidate, dict):
                    continue
                gear_names, mini_names = materialize_candidate_names(candidate, mutate=False)
                out.append(
                    {
                        "Score": candidate.get("Score", 0),
                        "BaseScore": candidate.get("BaseScore", candidate.get("Score", 0)),
                        "Gear": list(gear_names),
                        "Minis": list(mini_names),
                        "Data": candidate.get("Data") or {},
                        "_fg_priority": candidate.get("_fg_priority", 0),
                    }
                )
            return out

        def _compact_loadout_entries(entries):
            if entries is None:
                return None
            out = {}
            for key, value in entries.items():
                if not isinstance(value, dict):
                    continue
                gear_names, mini_names = materialize_entry_names(value, mutate=False)
                out[str(key)] = {
                    "score": value.get("score", 0),
                    "base_score": value.get("base_score", value.get("score", 0)),
                    "fg_score": value.get("fg_score", 0),
                    "gear": list(gear_names),
                    "minis": list(mini_names),
                    "details": value.get("details") or {},
                    "force": value.get("force"),
                }
            return out

        def _compact_prev_record(record):
            if not isinstance(record, dict):
                return None
            out = dict(record)
            out["gear"] = _compact_items(record.get("gear"))
            out["minis"] = _compact_items(record.get("minis"))
            loadout = out.get("loadout")
            if isinstance(loadout, (list, tuple)):
                out["loadout"] = [str(item) if item is not None else "" for item in loadout]
            force_obj = out.get("force")
            if isinstance(force_obj, dict):
                force_copy = dict(force_obj)
                force_gear = force_copy.get("gear")
                if isinstance(force_gear, (list, tuple)):
                    force_copy["gear"] = [str(item) if item is not None else "" for item in force_gear]
                force_minis = force_copy.get("minis")
                if isinstance(force_minis, (list, tuple)):
                    force_copy["minis"] = [str(item) if item is not None else "" for item in force_minis]
                out["force"] = force_copy
            return out

        if capture_log_payload:
            buf_content = buf.getvalue() if buf else ""

        try:
            record_info = evaluate_progress_record_update(
                outer.best_data,
                ctx.prev_record,
                fg.fg_variants,
                db_best_fg_score=ctx.db_best_fg_score,
                baseline_valid=bool(ctx.db_baseline_valid),
            )
        except Exception:
            record_info = None

        return cast(
            SongResultPayload,
            {
                "_deferred_post": True,
                "song": ctx.found_song_name,
                "_queue_key": ctx.queue_label,
                "_queue_label": ctx.queue_label,
                "_repeat_index": int(ctx.repeat_index),
                "_repeat_total": int(ctx.repeat_total),
                "_ga_seed": int(ctx.ga_seed) if ctx.ga_seed is not None else None,
                "db_key": ctx.db_key,
                "file_path": ctx.fp,
                "difficulty": ctx.effective_difficulty,
                "use_evo_db": bool(ctx.use_evo_db),
                "cfg_dict": ctx.cfg_dict,
                "ref_arrays": ctx.ref_arrays,
                "calc_song": ctx.calc_song,
                "best_data": outer.best_data,
                "best_gear": _compact_items(outer.best_gear),
                "best_minis": _compact_items(outer.best_minis),
                "current_gear": _compact_items(ctx.current_gear_list),
                "current_minis": _compact_items(ctx.current_mini_list),
                "enable_gear": bool(ctx.enable_gear),
                "enable_mini": bool(ctx.enable_mini),
                "fg_variants": _compact_fg_variants(fg.fg_variants),
                "ga_candidates": _compact_ga_candidates(outer.ga_candidates),
                "loadout_entries": _compact_loadout_entries(fg.loadout_entries),
                "prev_record": _compact_prev_record(ctx.prev_record),
                "attempt_lifetime": ctx.attempt_lifetime,
                "prev_attempts_first": ctx.prev_attempts_first,
                "db_best_score": ctx.db_best_score,
                "db_best_fg_score": ctx.db_best_fg_score,
                "db_baseline_valid": bool(ctx.db_baseline_valid),
                "meta_primary_color": ctx.meta_primary_color,
                "meta_secondary_color": ctx.meta_secondary_color,
                "fg_debug": bool(ctx.fg_debug),
                "_record": record_info,
                "log": buf_content,
            },
        )

    if outer.best_data:
        t_db0 = time.perf_counter()
        db_payload = build_db_payload(
            outer.best_data,
            outer.best_gear,
            outer.best_minis,
            ctx.prev_record,
            ctx.attempt_lifetime,
            ctx.attempts_first,
            fg.fg_variants,
            build_details,
            db_best_fg_score=ctx.db_best_fg_score,
        )
        ctx.stage_timing["_db_payload_sec"] = time.perf_counter() - t_db0

        t_persist0 = time.perf_counter()
        persist_entries = build_persistence_entries(
            db_payload,
            outer.ga_candidates,
            fg.loadout_entries,
            build_details,
            calc_song=ctx.calc_song,
            ref_arrays=ctx.ref_arrays,
            cfg_dict=ctx.cfg_dict,
        )
        ctx.stage_timing["_persist_build_sec"] = time.perf_counter() - t_persist0

        t_report0 = time.perf_counter()
        print_results(
            ctx.found_song_name,
            outer.best_data,
            outer.best_gear,
            outer.best_minis,
            ctx.current_gear_list,
            ctx.current_mini_list,
            ctx.enable_gear,
            ctx.enable_mini,
            fg.fg_variants,
            ctx.emit,
            fg_debug=ctx.fg_debug,
            ref_arrays=ctx.ref_arrays,
            calc_song=ctx.calc_song,
            cfg=ctx.cfg,
            db_best_fg_score=ctx.db_best_fg_score,
            prev_record=ctx.prev_record,
        )
        ctx.stage_timing["_report_sec"] = time.perf_counter() - t_report0

        if PERF_TIMING_ENABLED:
            print(
                f"[PERF] DB/Persist/Report: payload={ctx.stage_timing.get('_db_payload_sec', 0.0):.3f}s "
                f"persist={ctx.stage_timing.get('_persist_build_sec', 0.0):.3f}s "
                f"report={ctx.stage_timing.get('_report_sec', 0.0):.3f}s"
            )
    else:
        print(f"[ERROR] Optimization failed for {ctx.found_song_name} - best_data is None")
        log_tail = buf.getvalue()[-500:] if buf else "No log buffer"
        db_payload = {
            "score": 0,
            "fg_score": 0,
            "gear": [],
            "minis": [],
            "details": {"Error": "Optimization failed - no valid loadout found", "LogTail": log_tail},
            "force": None,
        }

    if capture_log_payload:
        buf_content = buf.getvalue() if buf else ""

    return cast(
        SongResultPayload,
        {
            "song": ctx.found_song_name,
            "_queue_key": ctx.queue_label,
            "_queue_label": ctx.queue_label,
            "_repeat_index": int(ctx.repeat_index),
            "_repeat_total": int(ctx.repeat_total),
            "_ga_seed": int(ctx.ga_seed) if ctx.ga_seed is not None else None,
            "db_key": ctx.db_key,
            "file_path": ctx.fp,
            "difficulty": ctx.effective_difficulty,
            "cfg_dict": ctx.cfg_dict,
            "db_payload": db_payload,
            "_record": db_payload.get("_record") if isinstance(db_payload, dict) else None,
            "prev_record": ctx.prev_record,
            "fg_variants": fg.fg_variants,
            "attempt_lifetime": ctx.attempt_lifetime,
            "prev_attempts_first": ctx.prev_attempts_first,
            "db_best_score": ctx.db_best_score,
            "db_best_fg_score": ctx.db_best_fg_score,
            "db_baseline_valid": bool(ctx.db_baseline_valid),
            "best_data": outer.best_data,
            "best_gear": outer.best_gear,
            "best_minis": outer.best_minis,
            "persist_entries": persist_entries if outer.best_data else [],
            "log": buf_content,
        },
    )


def process_song_task(args) -> SongResultPayload:
    """
    Run a single song end-to-end optimization.

    REFACTORED: Extracted helper functions where practical; this entrypoint remains
    orchestration-heavy because it owns per-song setup, solver routing, and persistence.

    Main steps:
    1. Parse arguments and setup
    2. Read song file
    3. Load previous best from database (if using DB)
    4. Run GA or gem solver only
    5. Apply force greats if enabled
    6. Build persistence payload
    7. Cleanup and return results

    Args:
        args: Tuple of (fp, song_name, difficulty, cfg_dict, paths, ref_arrays,
                        all_gears, all_minis, gears_by_name, minis_by_name,
                        use_evo_db, auto_buff, ga_depth, status_queue, parallel_workers)

    Returns:
        dict: Result with song, db_key, db_payload, best_data, persist_entries, log
    """
    # --- CRITICAL: Clear caches at start of task to prevent OOM in worker process ---
    # These globals persist in the worker process if not cleared, leading to memory leaks
    # especially when GA is skipped (Calculate-Only mode) but caches are still populated.
    GEM_SOLVER_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()
    FG_CACHE.clear()

    args_list = list(args) if isinstance(args, (list, tuple)) else [args]
    (
        fp,
        found_song_name,
        effective_difficulty,  # Difficulty determined from file header or folder path
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        status_queue,
        _parallel_workers,
        fg_debug,
    ) = args_list[:16]

    # Optional extras (sequential pipeline mode):
    # - preloaded calc_song dict to avoid repeated disk I/O + parsing
    # - defer_post: if True, skip persistence/reporting and return raw compute payload
    preloaded_calc_song = None
    repeat_ctx = None
    defer_post = False
    extras = args_list[16:] if len(args_list) > 16 else []
    if extras:
        for extra in extras:
            if isinstance(extra, dict):
                if extra.get("song_data") is not None:
                    preloaded_calc_song = extra
                    continue
                if "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra:
                    repeat_ctx = extra
                    continue
            if isinstance(extra, bool) and not defer_post:
                defer_post = bool(extra)

    queue_label = found_song_name
    ga_seed = None
    repeat_index = 0
    repeat_total = 0
    if isinstance(repeat_ctx, dict):
        try:
            repeat_index = int(str(repeat_ctx.get("repeat_index") or 0))
            repeat_total = int(str(repeat_ctx.get("repeat_total") or 0))
        except Exception:
            repeat_index = 0
            repeat_total = 0
        try:
            raw_seed = repeat_ctx.get("ga_seed")
            ga_seed = int(str(raw_seed)) if raw_seed is not None else None
        except Exception:
            ga_seed = None
        if repeat_index > 0 and repeat_total > 1:
            queue_label = f"{found_song_name} (Run {repeat_index}/{repeat_total})"

    # Initialize variables at function start to avoid 'in locals()' pattern issues
    loadout_entries = None
    known_loadouts = None

    # Capture logs only when explicitly requested; otherwise sink output without growing
    # per-song buffers that are discarded by the coordinator.
    buf = StringIO() if _CAPTURE_SONG_LOG_PAYLOAD else _NullLogBuffer()
    output_enabled = bool(getattr(ENV, "output_enabled", False))
    tee = Tee(sys.stdout, buf) if output_enabled else Tee(buf)
    redirect_ctx = contextlib.redirect_stdout(tee)
    redirect_err_ctx = contextlib.redirect_stderr(tee)
    redirect_ctx.__enter__()
    redirect_err_ctx.__enter__()

    # Memory leak tracking: Log memory at start of song
    log_memory_usage(f"Start: {found_song_name}")

    # GPU profiler: track song processing time
    _gpu_profiler.start_song(found_song_name)

    result_payload = None
    stage_timing: dict[str, float] = {}
    _song_wall_t0 = time.perf_counter()
    _cpu_prep_t0 = _song_wall_t0
    ga_time_sec = 0.0
    fg_time_sec = 0.0
    db_payload_time_sec = 0.0
    persist_build_time_sec = 0.0
    report_time_sec = 0.0
    # GPU timeline slot reuse (GA -> FG). Keep these in outer scope for cleanup.
    _gpu_song_slot = 0

    try:
        def emit(msg):
            if not status_queue:
                return
            try:
                payload = f"[{queue_label or found_song_name}] {msg}"
            except Exception:
                payload = str(msg)
            try:
                put_nowait = getattr(status_queue, "put_nowait", None)
                if callable(put_nowait):
                    put_nowait(payload)
                else:
                    status_queue.put(payload, block=False)
            except Exception:
                pass

        song_ctx = _setup_song_context(
            fp=fp,
            found_song_name=found_song_name,
            effective_difficulty=effective_difficulty,
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            use_evo_db=use_evo_db,
            auto_buff=auto_buff,
            ga_depth=ga_depth,
            status_queue=status_queue,
            fg_debug=fg_debug,
            defer_post=defer_post,
            preloaded_calc_song=preloaded_calc_song,
            repeat_index=repeat_index,
            repeat_total=repeat_total,
            ga_seed=ga_seed,
            emit=emit,
            stage_timing=stage_timing,
        )
        song_ctx.queue_label = queue_label

        outer_result = _run_outer_search(song_ctx)
        fg_result = _run_force_greats(song_ctx, outer_result)
        loadout_entries = fg_result.loadout_entries
        known_loadouts = song_ctx.known_loadouts
        _gpu_song_slot = int(song_ctx.gpu_song_slot)

        result_payload = _build_and_persist(
            song_ctx,
            outer_result,
            fg_result,
            buf=buf,
            capture_log_payload=_CAPTURE_SONG_LOG_PAYLOAD,
        )

        ga_time_sec = float(outer_result.wall_sec)
        fg_time_sec = float(fg_result.wall_sec)
        db_payload_time_sec = float(song_ctx.stage_timing.get("_db_payload_sec", 0.0) or 0.0)
        persist_build_time_sec = float(song_ctx.stage_timing.get("_persist_build_sec", 0.0) or 0.0)
        report_time_sec = float(song_ctx.stage_timing.get("_report_sec", 0.0) or 0.0)
        return cast(SongResultPayload, result_payload)
    finally:
        # Memory leak tracking: Log before cleanup
        log_memory_usage(f"Before cleanup: {found_song_name}")

        # GPU profiler: end song tracking
        _song_gpu_timing = _gpu_profiler.end_song()
        stage_timing["song_wall_sec"] = time.perf_counter() - _song_wall_t0
        stage_timing["cpu_post_sec"] = (
            float(db_payload_time_sec) + float(persist_build_time_sec) + float(report_time_sec)
        )
        stage_timing["cpu_ga_wall_sec"] = float(ga_time_sec)
        stage_timing["cpu_fg_wall_sec"] = float(fg_time_sec)

        if isinstance(result_payload, dict):
            result_payload.setdefault("_stage_timing", {}).update(stage_timing)
            if _song_gpu_timing is not None:
                result_payload.setdefault("_gpu_timing", {}).update(
                    {
                        "kernel_sec": float(getattr(_song_gpu_timing, "kernel_sec", 0.0) or 0.0),
                        "upload_sec": float(getattr(_song_gpu_timing, "upload_sec", 0.0) or 0.0),
                        "download_sec": float(getattr(_song_gpu_timing, "download_sec", 0.0) or 0.0),
                        "kernel_calls": int(getattr(_song_gpu_timing, "kernel_calls", 0) or 0),
                        "genome_evaluations": int(getattr(_song_gpu_timing, "genome_evaluations", 0) or 0),
                        "total_sec": float(getattr(_song_gpu_timing, "total_sec", 0.0) or 0.0),
                    }
                )

        # Prevent memory leak from unbounded cache growth across thousands of songs
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        # Memory leak fix: Clear local data structures explicitly
        # Using direct checks instead of 'in locals()' pattern (more reliable)
        if loadout_entries is not None:
            loadout_entries.clear()
        if known_loadouts is not None:
            known_loadouts.clear()

        # Memory leak fix: Close StringIO buffer explicitly
        # This buffer can hold 10-100MB of captured output per song
        if buf is not None:
            try:
                buf.close()
            except Exception as e:
                # Log buffer close failures (was silently suppressed)
                logging.debug(f"[StringIO] Failed to close buffer: {e}")

        # Deterministic periodic full GC to cap long-run memory growth.
        global _SONG_GC_COUNTER
        _SONG_GC_COUNTER += 1
        if _SONG_GC_COUNTER % _SONG_GC_GEN2_INTERVAL == 0:
            gc.collect(generation=2)

        # Memory leak tracking: Log after cleanup
        log_memory_usage(f"After cleanup: {found_song_name}")

        redirect_ctx.__exit__(None, None, None)
        redirect_err_ctx.__exit__(None, None, None)


def safe_process_song_task(args) -> SongResultPayload:
    """
    Wrapper around process_song_task that never raises across process boundaries.
    Returns an error payload with traceback if anything escapes, to avoid crashing pools.

    Args:
        args: Arguments tuple for process_song_task

    Returns:
        dict: Result dict or error dict with _error and _trace keys
    """
    song_name = "Unknown"
    queue_label = None
    try:
        if isinstance(args, (list, tuple)) and len(args) > 1:
            song_name = args[1]
            queue_label = str(song_name)
            try:
                if len(args) > 16:
                    for extra in args[16:]:
                        if not isinstance(extra, dict):
                            continue
                        if "repeat_index" in extra and "repeat_total" in extra:
                            idx = int(extra.get("repeat_index") or 0)
                            total = int(extra.get("repeat_total") or 0)
                            if idx > 0 and total > 1:
                                queue_label = f"{song_name} (Run {idx}/{total})"
                            break
            except Exception:
                queue_label = str(song_name)
        return process_song_task(args)
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[safe_process_song_task] {song_name} failed: {type(exc).__name__}: {exc}"
        try:
            logging.error(msg + "\n" + tb)
            print(msg, file=sys.stderr)
        except Exception:
            pass
        return build_error_payload(
            song_name=str(song_name),
            queue_key=str(queue_label or song_name),
            queue_label=str(queue_label or song_name),
            exc=exc,
            trace=tb,
        )
