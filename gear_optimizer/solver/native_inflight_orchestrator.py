"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).

This pipeline is designed to keep the GPU continuously busy in GPU_Native_GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Scheduling ForceGreatsFinder work via continuous credit-based interleaving,
  with CPU grouping/prep performed off the GPU thread and GPU kernels submitted via the executor.
"""

from __future__ import annotations

import concurrent.futures
import os
import queue
import threading
import time
import traceback
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.core.utils import cfg_from_dict, get_selected_element, safe_float, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.fg_combo_booster import (
    build_fg_combo_booster_candidates,
    finalize_fg_combo_booster_candidates_job,
    hydrate_fg_candidate_stats,
)
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.ga_entry_utils import (
    entry_loadout_hash,
    materialize_candidate_names,
    materialize_entry_names,
)
from gear_optimizer.helpers.song_helpers.loadout_builder import (
    merge_db_loadouts_into_entries,
    refresh_ga_candidate_entries,
)
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn, evaluate_record_update
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.genetic import GA_POPULATION_SIZE
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient, GpuServiceTimeoutError
from gear_optimizer.solver.inflight_utils import (
    _build_calc_song_from_file,
    _compact_items,
    _compact_prev_record,
    _summarize_db_context,
    _truthy,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.native_inflight_stages import (
    _InFlightStageProfiler,
    _decode_ga_payload_sync,
    _prefetch_db_loadouts_sync,
    _prepare_fg_job_sync,
    _warmup_fg_jit,
)


_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_INIT_HEURISTIC_CACHE_MAX = 64
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_INIT_HEURISTIC_TOPK_CACHE: "OrderedDict[tuple[tuple[str, str, tuple[str, ...]], int], np.ndarray]" = OrderedDict()
_REGISTRY_GPU_FIXED_CACHE: "OrderedDict[tuple, tuple[ItemRegistry, dict]]" = OrderedDict()

# Optional cache hit/miss stats (helps tune CPU requirements on low-end machines).
_CACHE_STATS = {
    "pools_hit": 0,
    "pools_miss": 0,
    "registry_hit": 0,
    "registry_miss": 0,
    "heur_hit": 0,
    "heur_miss": 0,
}
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_STATS_LAST_EMIT = 0.0
_DB_CONTEXT_CACHE_LOCK = threading.Lock()
_DB_CONTEXT_CACHE: "OrderedDict[tuple[str, bool], tuple[float, Optional[dict], int, int, int]]" = OrderedDict()


def _set_fg_resident_owner(calc_song: Any, *, song_slot: int, task_key: str) -> None:
    if not isinstance(calc_song, dict):
        return
    calc_song["_fg_ga_candidate_table_slot_held"] = True
    calc_song["_fg_resident_owner_phase"] = "ga_to_fg"
    calc_song["_fg_resident_owner_slot"] = int(song_slot)
    calc_song["_fg_resident_candidate_table_slot"] = int(song_slot)
    calc_song["_fg_resident_owner_task"] = str(task_key or "")


def _clear_fg_resident_owner(calc_song: Any) -> None:
    if not isinstance(calc_song, dict):
        return
    calc_song["_fg_ga_candidate_table_slot_held"] = False
    calc_song.pop("_fg_resident_owner_phase", None)
    calc_song.pop("_fg_resident_owner_slot", None)
    calc_song.pop("_fg_resident_candidate_table_slot", None)
    calc_song.pop("_fg_resident_owner_task", None)


def _db_context_cache_max() -> int:
    try:
        raw = os.environ.get("INFLIGHT_DB_CONTEXT_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
    except Exception:
        pass
    return 1024


def _db_context_cache_ttl_s() -> float:
    try:
        raw = os.environ.get("INFLIGHT_DB_CONTEXT_CACHE_TTL_SEC")
        if raw is not None and str(raw).strip() != "":
            return max(0.0, float(raw))
    except Exception:
        pass
    return 1.0


def _db_context_cache_get(db_key: str, use_evo_db: bool) -> tuple[Optional[dict], int, int, int] | None:
    key = (str(db_key or "").strip(), bool(use_evo_db))
    if not key[0] or not key[1]:
        return None
    ttl_s = float(_db_context_cache_ttl_s())
    try:
        with _DB_CONTEXT_CACHE_LOCK:
            entry = _DB_CONTEXT_CACHE.get(key)
            if entry is None:
                return None
            ts, prev_record, db_best_fg_score, attempt_lifetime, prev_attempts_first = entry
            if ttl_s > 0.0 and (time.monotonic() - float(ts)) > ttl_s:
                _DB_CONTEXT_CACHE.pop(key, None)
                return None
            _DB_CONTEXT_CACHE.move_to_end(key)
            rec = _compact_prev_record(prev_record) if isinstance(prev_record, dict) else None
            return rec, int(db_best_fg_score), int(attempt_lifetime), int(prev_attempts_first)
    except Exception:
        return None


def _db_context_cache_put(
    db_key: str,
    use_evo_db: bool,
    prev_record: Optional[dict],
    db_best_fg_score: int,
    attempt_lifetime: int,
    prev_attempts_first: int,
) -> None:
    key = (str(db_key or "").strip(), bool(use_evo_db))
    if not key[0] or not key[1]:
        return
    try:
        record_copy = _compact_prev_record(prev_record) if isinstance(prev_record, dict) else None
        with _DB_CONTEXT_CACHE_LOCK:
            _DB_CONTEXT_CACHE[key] = (
                float(time.monotonic()),
                record_copy,
                int(db_best_fg_score or 0),
                int(attempt_lifetime or 0),
                int(prev_attempts_first or 0),
            )
            _DB_CONTEXT_CACHE.move_to_end(key)
            max_n = int(_db_context_cache_max())
            if max_n <= 0:
                _DB_CONTEXT_CACHE.clear()
                return
            while len(_DB_CONTEXT_CACHE) > max_n:
                _DB_CONTEXT_CACHE.popitem(last=False)
    except Exception:
        return


def _cache_stats_enabled() -> bool:
    return _truthy(os.environ.get("INFLIGHT_CACHE_STATS", "0"))


def _cache_stats_emit_interval_s() -> float:
    try:
        return float(os.environ.get("INFLIGHT_CACHE_STATS_EMIT_SEC", "30") or "30")
    except Exception:
        return 30.0


def _cache_stats_inc(key: str) -> None:
    try:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS[key] = int(_CACHE_STATS.get(key, 0) or 0) + 1
    except Exception:
        return


def _cache_stats_maybe_emit() -> None:
    if not _cache_stats_enabled():
        return
    interval = float(_cache_stats_emit_interval_s())
    if interval <= 0:
        return
    now = time.monotonic()
    global _CACHE_STATS_LAST_EMIT
    try:
        with _CACHE_STATS_LOCK:
            if (now - float(_CACHE_STATS_LAST_EMIT)) < interval:
                return
            _CACHE_STATS_LAST_EMIT = now
            snap = dict(_CACHE_STATS)
    except Exception:
        return
    try:
        pools_h = int(snap.get("pools_hit", 0) or 0)
        pools_m = int(snap.get("pools_miss", 0) or 0)
        reg_h = int(snap.get("registry_hit", 0) or 0)
        reg_m = int(snap.get("registry_miss", 0) or 0)
        heur_h = int(snap.get("heur_hit", 0) or 0)
        heur_m = int(snap.get("heur_miss", 0) or 0)
        print(
            "[InFlight][CacheStats] "
            f"pools hit={pools_h} miss={pools_m} | "
            f"registry hit={reg_h} miss={reg_m} | "
            f"heur_topk hit={heur_h} miss={heur_m}"
        )
    except Exception:
        pass


def _fixed_registry_cache_key(
    *,
    pool_key: tuple[str, str, tuple[str, ...]],
    fixed_gear: list[dict] | None,
    fixed_minis: list[dict] | None,
) -> tuple:
    def _n(it: dict | None) -> str:
        try:
            return str((it or {}).get("Name", "") or "")
        except Exception:
            return ""

    fg = tuple(_n(it) for it in (fixed_gear or [])[:6])
    fm = tuple(sorted(_n(it) for it in (fixed_minis or [])[:3]))
    return ("fixed", pool_key, fg, fm)


def _thread_cpu_time_s() -> float:
    """
    Best-effort per-thread CPU timer for CPU-only profiling.

    Uses `time.thread_time()` when available (Python 3.7+). Returns 0.0 on unsupported platforms.
    """
    try:
        return float(time.thread_time())
    except Exception:
        return 0.0


def _attach_hitsim_delta_for_base(best_data: dict | None, calc_song: dict | None, ref_arrays: dict | None) -> None:
    if not isinstance(best_data, dict) or not best_data:
        return
    if "hitsim_offset_delta_ms" in best_data:
        try:
            if best_data.get("hitsim_offset_delta_ms") is not None:
                return
        except Exception:
            return
    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return
    try:
        from gear_optimizer.solver.scoring.force_greats import summarize_hitsim_offset_delta_ms_for_base

        delta_ms = summarize_hitsim_offset_delta_ms_for_base(calc_song, best_data, ref_arrays)
        if delta_ms is not None:
            best_data["hitsim_offset_delta_ms"] = int(delta_ms)
    except Exception:
        return


def _nonfever_counts_from_config_for_hitsim(config: object) -> tuple[int, ...]:
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
        pairs.append((idx, max(0, safe_int(val, 0))))
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


def _materialize_fg_stats_for_hitsim(fg_data: dict) -> dict:
    if not isinstance(fg_data, dict):
        return {}
    try:
        from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
    except Exception:
        return {}
    stats = materialize_stats_from_payload(fg_data, mutate_payload=True)
    return stats if isinstance(stats, dict) else {}


def _attach_hitsim_delta_for_fg_variant(
    fg_variants: list[dict] | None,
    calc_song: dict | None,
    ref_arrays: dict | None,
) -> None:
    if not fg_variants or not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return

    try:
        from gear_optimizer.solver.scoring.force_greats import summarize_hitsim_offset_delta_ms_for_fg_variant
    except Exception:
        return

    delta_cache: dict[tuple[int, int, tuple[int, ...]], int] = {}
    for variant in fg_variants or []:
        if not isinstance(variant, dict):
            continue

        # This is a large payload; keep it only long enough to compute the delta once per cache key.
        calc_song_variant = variant.pop("_hitsim_calc_song", None)

        fg_score = safe_int(variant.get("fg_score", 0), 0)
        base_score = safe_int(variant.get("score", 0), 0)
        if fg_score <= base_score:
            continue

        fg_data = variant.get("data") or {}
        if not isinstance(fg_data, dict):
            continue
        fg_meta = fg_data.get("ForceGreats") or {}
        if not isinstance(fg_meta, dict):
            continue
        if fg_meta.get("hitsim_offset_delta_ms") is not None:
            continue

        forced_counts = _nonfever_counts_from_config_for_hitsim(fg_meta.get("config") or {})
        if not forced_counts:
            continue

        stats = fg_data.get("Stats") or {}
        if not isinstance(stats, dict) or not stats:
            stats = _materialize_fg_stats_for_hitsim(fg_data)
        if not isinstance(stats, dict) or not stats:
            continue

        ff_stat = safe_int(stats.get("Fever Fill Rate", 0), 0)
        ft_stat = safe_int(stats.get("Fever Time", 0), 0)
        cache_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in forced_counts))

        delta_ms = delta_cache.get(cache_key)
        if delta_ms is None:
            calc_song_in = calc_song_variant if isinstance(calc_song_variant, dict) else calc_song
            try:
                computed = summarize_hitsim_offset_delta_ms_for_fg_variant(calc_song_in, fg_data, ref_arrays)
            except Exception:
                computed = None
            if computed is None:
                continue
            delta_ms = int(computed)
            delta_cache[cache_key] = int(delta_ms)

        fg_meta_out = dict(fg_meta)
        fg_meta_out["hitsim_offset_delta_ms"] = int(delta_ms)
        fg_data["ForceGreats"] = fg_meta_out

        details_obj = fg_data.get("details")
        if isinstance(details_obj, dict):
            fg_det = details_obj.get("ForceGreats")
            if isinstance(fg_det, dict) and fg_det.get("hitsim_offset_delta_ms") is None:
                fg_det_out = dict(fg_det)
                fg_det_out["hitsim_offset_delta_ms"] = int(delta_ms)
                details_out = dict(details_obj)
                details_out["ForceGreats"] = fg_det_out
                fg_data["details"] = details_out

        variant["data"] = fg_data


def _default_worker_threads(*, inflight_limit: int, kind: str) -> int:
    """
    Choose conservative default worker counts for low-end CPUs.

    Goal: avoid oversubscription that can *increase* wall time (thread contention)
    and starve the GPU queue, especially on 4–8 core machines.
    """
    ncpu = os.cpu_count() or 1
    try:
        ncpu = int(ncpu)
    except Exception:
        ncpu = 1
    ncpu = max(1, ncpu)
    inflight_limit = max(1, int(inflight_limit))
    kind = str(kind or "").strip().lower()

    # Keep at most half the cores for background prep/decode work by default.
    # (The main thread + GPU owner thread + other overhead still need room.)
    base = max(1, ncpu // 2)
    # On very small machines, don't exceed 2–3 threads per pool.
    if ncpu <= 4:
        base = min(base, 2)
    elif ncpu <= 8:
        base = min(base, 3)

    # FG prep can be more expensive; keep it a bit lower by default.
    if kind in {"fg_prep", "fgprep"}:
        base = max(1, min(base, 2 if ncpu <= 8 else base))
    return max(1, min(inflight_limit, int(base)))


def _default_prime_target(*, inflight_limit: int, prep_limit: int, pending_count: int) -> int:
    """
    Pick a startup prep backlog large enough to avoid the first GA/FG feed bubble.

    For smaller in-flight runs, priming only `inflight_limit` songs tends to leave the
    GPU queue shallow while prep/decode workers are still spinning up. We bias toward
    a modest 4-8 song startup backlog, but always cap by the prep buffer and pending queue.
    """
    try:
        inflight_limit = int(inflight_limit)
    except Exception:
        inflight_limit = 1
    try:
        prep_limit = int(prep_limit)
    except Exception:
        prep_limit = 1
    try:
        pending_count = int(pending_count)
    except Exception:
        pending_count = 0

    inflight_limit = max(1, inflight_limit)
    prep_limit = max(1, prep_limit)
    pending_count = max(0, pending_count)
    if pending_count <= 0:
        return 0

    target = max(inflight_limit, min(8, max(4, inflight_limit * 2)))
    return max(1, min(target, prep_limit, pending_count))


def _is_repeat_ctx_dict(extra: Any) -> bool:
    return isinstance(extra, dict) and "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra


def _extract_repeat_ctx(task: tuple) -> dict | None:
    if not isinstance(task, (tuple, list)) or len(task) <= 16:
        return None
    for extra in task[16:]:
        if _is_repeat_ctx_dict(extra):
            return extra
    return None


def _extract_repeat_bundle(task: tuple) -> dict | None:
    if not isinstance(task, (tuple, list)) or len(task) <= 16:
        return None
    for extra in task[16:]:
        if not isinstance(extra, dict):
            continue
        if not bool(extra.get("repeat_bundle")):
            continue
        runs = extra.get("runs")
        if isinstance(runs, list) and runs:
            return extra
    return None


def _materialize_repeat_task(task: tuple, repeat_ctx: dict) -> tuple:
    if not isinstance(task, (tuple, list)):
        return task
    prefix = list(task[:16])
    extras: list[Any] = []
    for extra in task[16:]:
        if _is_repeat_ctx_dict(extra):
            continue
        if isinstance(extra, dict) and bool(extra.get("repeat_bundle")):
            continue
        extras.append(extra)
    extras.append(dict(repeat_ctx or {}))
    return tuple(prefix + extras)


def _task_key(task: tuple) -> str:
    if not isinstance(task, (tuple, list)) or len(task) < 2:
        return "Unknown"
    base = str(task[1])
    repeat_ctx = _extract_repeat_ctx(task)
    if repeat_ctx:
        try:
            idx = int(repeat_ctx.get("repeat_index") or 0)
            total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception:
            idx = 0
            total = 0
        if idx > 0 and total > 1:
            return f"{base} (Run {idx}/{total})"
    return base


def _task_ga_seed(task: tuple) -> int | None:
    repeat_ctx = _extract_repeat_ctx(task)
    if not repeat_ctx:
        return None
    try:
        seed = repeat_ctx.get("ga_seed")
        return int(seed) if seed is not None else None
    except Exception:
        return None


def _lru_get(cache: OrderedDict, key: tuple) -> Any:
    try:
        value = cache.get(key)
    except Exception:
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception:
            pass
    return value


def _lru_put(cache: OrderedDict, key: tuple, value: Any, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception:
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception:
        pass


def _loadout_entries_have_db_source(loadout_entries: dict | None) -> bool:
    if not isinstance(loadout_entries, dict) or not loadout_entries:
        return False
    for entry in loadout_entries.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("_source", "") or "").strip().lower() == "db":
            return True
    return False


def _read_fg_scheduler_mode() -> str:
    """
    In-flight scheduler is intentionally fixed to continuous mode.

    We removed backlog/drain scheduler options to keep runtime behavior
    deterministic and easier to reason about.
    """
    return "continuous"


def _read_fg_ga_credit_budget(cfg0: Any, *, default_budget: int) -> tuple[int, bool]:
    """
    GA-credit budget used by continuous FG scheduler.

    Returns: (budget, explicit)
    - budget: effective positive integer
    - explicit: True when user explicitly set the budget (config/env), False when defaulted
    """
    budget = max(1, int(default_budget))
    explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGGACreditBudget"):
                budget = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGGACreditBudget", fallback=str(budget)),
                    budget,
                )
                explicit = True
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_GA_CREDIT_BUDGET")
    if raw is not None and str(raw).strip() != "":
        try:
            budget = int(raw)
            explicit = True
        except Exception:
            pass

    return max(1, int(budget)), bool(explicit)


def _read_continuous_ga_dispatch_burst(cfg0: Any, *, default_burst: int = 2) -> int:
    """
    Max GA submissions per scheduler cycle when continuous GA/FG interleaving is active.

    Lower values reduce GA burstiness and give FG more frequent chances to submit,
    which smooths GPU utilization without changing GA/FG scoring behavior.
    """
    burst = max(1, int(default_burst))
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_ContinuousGABurst"):
            burst = safe_int(
                cfg0.get("IterationEngine", "InFlight_ContinuousGABurst", fallback=str(burst)),
                burst,
            )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_CONTINUOUS_GA_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            burst = int(raw)
        except Exception:
            pass

    return max(1, min(int(burst), 32))


def _read_continuous_fg_adaptive_submit(cfg0: Any) -> tuple[bool, int]:
    """
    Adaptive FG submit policy for continuous mode.

    Returns:
    - enabled: whether adaptive FG submit burst sizing is enabled
    - max_burst: upper bound for adaptive FG submit burst size
    """
    enabled = True
    max_burst = 3

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveSubmit"):
                enabled = cfg0.getboolean("IterationEngine", "InFlight_FGAdaptiveSubmit", fallback=True)
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveMaxBurst"):
                max_burst = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGAdaptiveMaxBurst", fallback=str(max_burst)),
                    max_burst,
                )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_ADAPTIVE_SUBMIT")
    if raw is not None and str(raw).strip() != "":
        enabled = _truthy(raw)

    raw = os.environ.get("INFLIGHT_FG_ADAPTIVE_MAX_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            max_burst = int(raw)
        except Exception:
            pass

    return bool(enabled), max(1, min(int(max_burst), 16))


def _read_fg_slot_reserve(
    cfg0: Any,
    *,
    fg_enabled: bool,
    inflight_limit: int,
    song_slot_limit: int,
) -> int:
    """
    Reserve a dedicated song-slot partition for FG work.

    This prevents GA from consuming all song slots and creating slot-pressure oscillation
    when FG submissions need to acquire slots.
    """
    if (not fg_enabled) or int(inflight_limit) <= 1 or int(song_slot_limit) <= 1:
        return 0

    reserve = 1
    reserve_ratio = 0.20
    absolute_explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGSlotReserve"):
                reserve = safe_int(cfg0.get("IterationEngine", "InFlight_FGSlotReserve", fallback="1"), 1)
                absolute_explicit = True
            elif cfg0.has_option("IterationEngine", "InFlight_FGSlotReserveRatio"):
                reserve_ratio = safe_float(
                    cfg0.get("IterationEngine", "InFlight_FGSlotReserveRatio", fallback=str(reserve_ratio)),
                    reserve_ratio,
                )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_SLOT_RESERVE")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve = int(raw)
            absolute_explicit = True
        except Exception:
            pass

    raw = os.environ.get("INFLIGHT_FG_SLOT_RESERVE_RATIO")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve_ratio = float(raw)
        except Exception:
            pass

    reserve_cap = max(1, min(max(1, int(song_slot_limit) - 1), max(1, int(inflight_limit))))
    if absolute_explicit:
        if int(reserve) <= 0:
            return 0
        return max(1, min(int(reserve), int(reserve_cap)))

    reserve_ratio = max(0.0, min(float(reserve_ratio), 0.90))
    ratio_slots = int(round(float(song_slot_limit) * float(reserve_ratio)))
    reserve = max(int(reserve), int(ratio_slots))
    return max(1, min(int(reserve), int(reserve_cap)))


def _read_inflight_event_wait_timeout_s() -> float:
    """
    Base scheduler wait timeout when waiting for in-flight futures to complete.

    Keep this modest to avoid long producer wake-up delays that can starve the
    GPU owner thread between GA/FG stage transitions.
    """
    timeout_s = 0.05
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_TIMEOUT_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            timeout_s = float(raw)
        except Exception:
            pass
    return max(0.001, min(float(timeout_s), 5.0))


def _read_inflight_event_wait_gpu_cap_s() -> float:
    """
    Optional tighter cap for wait timeout while GPU work is active.

    A small cap reduces GA->FG handoff latency jitter under Windows scheduler/timer noise.
    Set to 0 to disable this cap.
    """
    timeout_s = 0.01
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            timeout_s = float(raw)
        except Exception:
            pass
    return max(0.0, min(float(timeout_s), 1.0))


def _read_inflight_event_wait_short_spin_s() -> float:
    """
    Short-window polling threshold for completion-event waits.

    For very small waits, poll with zero-timeout checks to avoid coarse timed-wait
    quantization from stretching sub-ms/ms windows into multi-ms idle bubbles.
    """
    short_spin_ms = 3.0
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            short_spin_ms = float(raw)
        except Exception:
            pass
    return max(0.0, min(float(short_spin_ms) / 1000.0, 0.050))


def _wait_for_completion_event(
    completion_event: threading.Event,
    *,
    timeout_s: float,
    short_spin_s: float,
) -> bool:
    wait_timeout = max(0.0, float(timeout_s))
    if wait_timeout <= 0.0:
        return bool(completion_event.wait(timeout=0.0))

    if wait_timeout > max(0.0, float(short_spin_s)):
        return bool(completion_event.wait(timeout=wait_timeout))

    deadline = time.perf_counter() + wait_timeout
    while True:
        if completion_event.wait(timeout=0.0):
            return True
        if time.perf_counter() >= deadline:
            return False
        time.sleep(0)


def _continuous_fg_should_start(
    *,
    pending_fg_count: int,
    ga_credit: int,
    oldest_wait_s: float,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    fg_drain_at_end: bool,
    aging_trigger_s: float,
    aging_hard_s: float,
) -> bool:
    if int(pending_fg_count) <= 0:
        return False
    if bool(no_ga_remaining):
        return bool(fg_drain_at_end)
    if bool(blocked_on_slot):
        return True
    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        return True
    if float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        return True
    return int(ga_credit) <= 0


def _continuous_fg_submit_budget(
    *,
    pending_fg_count: int,
    fg_inflight_count: int,
    fg_workers: int,
    fg_batch_max: int,
    no_ga_remaining: bool,
    fg_drain_at_end: bool,
    blocked_on_slot: bool,
    oldest_wait_s: float,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_inflight_count: int,
    ga_queue_limit: int,
    adaptive_submit: bool,
    adaptive_max_burst: int,
) -> int:
    capacity = max(0, min(int(fg_workers) - int(fg_inflight_count), int(fg_batch_max), int(pending_fg_count)))
    if capacity <= 0:
        return 0

    if bool(no_ga_remaining):
        return capacity if bool(fg_drain_at_end) else 0

    budget = 1
    max_burst = max(1, int(adaptive_max_burst))

    if bool(blocked_on_slot):
        budget = max(int(budget), min(int(capacity), int(max_burst)))

    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        budget = max(int(budget), min(int(capacity), int(max_burst)))
    elif float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        trigger_burst = 2 if bool(adaptive_submit) else 1
        budget = max(int(budget), min(int(capacity), int(trigger_burst)))

    if bool(adaptive_submit):
        ga_util = 0.0
        if int(ga_queue_limit) > 0:
            try:
                ga_util = float(ga_inflight_count) / float(ga_queue_limit)
            except Exception:
                ga_util = 0.0
        ga_util = max(0.0, min(1.0, float(ga_util)))

        backlog_total = max(0, int(pending_fg_count) + int(fg_inflight_count))
        half_burst = max(2, int((int(max_burst) + 1) // 2))

        if ga_util <= 0.50 and backlog_total >= int(half_burst):
            budget = max(int(budget), min(int(capacity), int(half_burst)))
        if ga_util <= 0.25 and backlog_total >= int(max(4, int(max_burst) * 2)):
            budget = max(int(budget), min(int(capacity), int(max_burst)))

    return max(0, min(int(capacity), int(budget)))


class _PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        # Default to unbounded backlog to avoid ever blocking the GPU-owner pipeline.
        backlog = 0
        try:
            backlog = int(os.environ.get("POST_LOCAL_BACKLOG", backlog))
        except Exception:
            backlog = 0
        backlog = int(backlog)
        if backlog < 0:
            backlog = 0
        self._q: queue.Queue[Any] = queue.Queue(maxsize=backlog)
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except Exception:
            return
        try:
            self._thread.join(timeout=timeout)
        except Exception:
            pass

    def _run(self) -> None:
        timing = str(os.environ.get("POST_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
        threshold_ms = 50.0
        try:
            threshold_ms = float(os.environ.get("POST_TIMING_THRESHOLD_MS", str(threshold_ms)))
        except Exception:
            threshold_ms = 50.0
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            try:
                t0 = time.perf_counter()
                while True:
                    if self._stop_requested is not None and callable(self._stop_requested) and self._stop_requested():
                        return
                    try:
                        self._post_queue.put(item, block=True, timeout=0.5)
                        break
                    except Exception:
                        continue
                if timing:
                    ms = (time.perf_counter() - t0) * 1000.0
                    if ms >= threshold_ms:
                        kind = None
                        try:
                            kind = item.get("song") if isinstance(item, dict) else None
                        except Exception:
                            kind = None
                        prefix = f"[PostSender][TIMING] {kind} " if kind else "[PostSender][TIMING] "
                        print(f"{prefix}post_queue_put={ms:.1f}ms")
            except Exception:
                pass


@dataclass
class _NativeSong:
    fp: str
    song_name: str
    task_key: str
    ga_seed: int | None
    db_key: str
    effective_difficulty: str
    cfg_dict: dict
    cfg: Any
    paths: Any
    ref_arrays: dict
    all_gears: list
    all_minis: list
    gears_by_name: dict
    minis_by_name: dict
    use_evo_db: bool
    auto_buff: bool
    ga_depth: int
    fg_debug: bool

    calc_song: dict
    meta_primary_color: str
    meta_secondary_color: str
    fixed_stats: dict
    current_gear_list: list
    current_mini_list: list
    enable_gear: bool
    enable_mini: bool
    force_greats_finder: bool
    force_greats_config: list
    manual_force_greats: bool

    prev_record: Optional[dict]
    attempt_lifetime: int
    prev_attempts_first: int
    db_best_fg_score: int

    # Prepared GPU-native GA inputs
    registry: ItemRegistry
    cfg_data: dict
    color_flags: dict
    gens_per_run: int
    num_runs: int
    n_genomes: int
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats_arr: np.ndarray
    elite_count: int
    mutation_rate: float
    immigrant_rate: float
    tournament_k: int
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k: int = 0
    init_heuristic_copies: int = 25
    db_seed_ids: Optional[np.ndarray] = None
    db_seed_prob: float = 0.0
    db_seed_copies: int = 1
    db_seed_mutations: int = 1

    # Runtime state
    song_slot: int = 0
    ga_future: Optional[concurrent.futures.Future] = None
    decode_future: Optional[concurrent.futures.Future] = None
    ga_candidates: Optional[list[dict]] = None
    best_data: Optional[dict] = None
    best_gear: Optional[list] = None
    best_minis: Optional[list] = None
    record_info: Optional[dict] = None

    # DB prefetch for FG (can overlap with GA)
    db_loadouts_future: Optional[concurrent.futures.Future] = None
    db_loadouts_full: Optional[list[dict]] = None

    loadout_entries: Optional[dict] = None
    fg_variants: Optional[list[dict]] = None
    fg_candidate_limit: int = 0
    fg_search_radius: Optional[int] = None
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_queued_t0: float | None = None
    fg_direct_ga_candidates: bool = False

    def __post_init__(self) -> None:
        if self.ga_candidates is None:
            self.ga_candidates = []
        if self.fg_variants is None:
            self.fg_variants = []


def _prepare_song(task: tuple) -> _NativeSong:
    cpu_t0 = _thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_ELITISM, GA_MUTATION_RATE
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_key = _task_key(task)
    ga_seed = _task_ga_seed(task)

    (
        fp,
        found_song_name,
        effective_difficulty,
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
        _status_queue,
        _parallel_workers,
        fg_debug,
    ) = task[:16]

    cfg = cfg_from_dict(cfg_dict)

    try:
        gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
    except Exception:
        gpu_mode = False
    if not gpu_mode:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Mode=true")

    try:
        gpu_native = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=False)
    except Exception:
        gpu_native = False
    if not gpu_native:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Native_GA=true")

    calc_song = _build_calc_song_from_file(
        fp=fp,
        found_song_name=found_song_name,
        cfg=cfg,
        cfg_dict=cfg_dict,
    )
    meta_primary_color = str(calc_song.get("metadata", {}).get("Primary Color", "") or "")
    meta_secondary_color = str(calc_song.get("metadata", {}).get("Secondary Color", "") or "")

    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        current_gear_list,
        _current_mini_stats,
        current_mini_list,
        _meta_finder,
        _enable_fever,
        enable_mini,
        enable_gear,
        _force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(cfg, calc_song, bool(auto_buff), paths, gears_by_name, minis_by_name)

    if not (enable_gear or enable_mini):
        raise RuntimeError("GPU-native in-flight currently requires MetaFinder (enable gear or minis).")

    from gear_optimizer.helpers.song_helpers.database_context import build_db_key

    db_key = build_db_key(found_song_name, calc_song)

    # Load DB seed record only; full known-loadout hydration is deferred/prefetched
    # in FG prep to avoid redundant per-song DB reads during prepare.
    allow_db_seed = True
    cached_db_ctx = _db_context_cache_get(db_key, bool(use_evo_db))
    if cached_db_ctx is not None:
        prev_record, db_best_fg_score, attempt_lifetime, prev_attempts_first = cached_db_ctx
    else:
        prev_record, _known_loadouts = load_database_context(
            db_key,
            bool(use_evo_db),
            gears_by_name,
            minis_by_name,
            load_known_loadouts=False,
        )
        db_best_fg_score, attempt_lifetime, prev_attempts_first = _summarize_db_context(
            prev_record,
            None,
            db_key=db_key,
            use_evo_db=bool(use_evo_db),
        )
        _db_context_cache_put(
            db_key,
            bool(use_evo_db),
            prev_record,
            int(db_best_fg_score),
            int(attempt_lifetime),
            int(prev_attempts_first),
        )

    p_color = calc_song.get("metadata", {}).get("Primary Color", "Rush")
    s_color = calc_song.get("metadata", {}).get("Secondary Color", "")
    selected_color = p_color
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pool_key = (str(p_color), str(s_color), tuple(slots))
    with _PREP_CACHE_LOCK:
        cached_pools = _lru_get(_POOL_CACHE, pool_key)
    if cached_pools is None:
        _cache_stats_inc("pools_miss")
        pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
        if pools is None:
            raise RuntimeError("initialize_pools returned None")
        if len(pools) == 4:
            gear_pool, mini_pool, _total_before, _total_after = pools
        else:
            gear_pool, mini_pool, _total_before, _total_after, _whitelisted_minis = pools
        if gear_pool is None:
            raise RuntimeError("initialize_pools failed (gear_pool is None)")
        with _PREP_CACHE_LOCK:
            _lru_put(_POOL_CACHE, pool_key, (gear_pool, mini_pool), maxsize=_POOL_CACHE_MAX)
    else:
        _cache_stats_inc("pools_hit")
        gear_pool, mini_pool = cached_pools

    cacheable_registry = bool(enable_gear and enable_mini)
    if cacheable_registry:
        with _PREP_CACHE_LOCK:
            cached_registry = _lru_get(_REGISTRY_GPU_CACHE, pool_key)
        if cached_registry is None:
            _cache_stats_inc("registry_miss")
            registry = ItemRegistry(gear_pool, mini_pool, slots)
            gpu_data = registry.to_gpu_arrays()
            with _PREP_CACHE_LOCK:
                _lru_put(_REGISTRY_GPU_CACHE, pool_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
        else:
            _cache_stats_inc("registry_hit")
            registry, gpu_data = cached_registry
    else:
        fixed_gear = list(current_gear_list or [])[:6] if not enable_gear else None
        fixed_minis = list(current_mini_list or [])[:3] if not enable_mini else None
        cache_key = _fixed_registry_cache_key(pool_key=pool_key, fixed_gear=fixed_gear, fixed_minis=fixed_minis)
        cached_fixed = None
        with _PREP_CACHE_LOCK:
            cached_fixed = _lru_get(_REGISTRY_GPU_FIXED_CACHE, cache_key)
        if cached_fixed is None:
            _cache_stats_inc("registry_miss")
            registry = ItemRegistry(gear_pool, mini_pool, slots, fixed_gear=fixed_gear, fixed_minis=fixed_minis)
            gpu_data = registry.to_gpu_arrays()
            with _PREP_CACHE_LOCK:
                _lru_put(_REGISTRY_GPU_FIXED_CACHE, cache_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
        else:
            _cache_stats_inc("registry_hit")
            registry, gpu_data = cached_fixed
    _cache_stats_maybe_emit()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )

    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "fg_candidate_limit": int(fg_candidate_limit),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0), 0),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0), 0),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0), 0),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0), 0),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0), 0),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0), 0),
    }
    try:
        cfg_data["ga_convergence_trace_enabled"] = bool(
            cfg.getboolean("IterationEngine", "GAConvergenceTrace", fallback=False)
        )
    except Exception:
        cfg_data["ga_convergence_trace_enabled"] = False
    try:
        cfg_data["ga_convergence_trace_every"] = max(
            1,
            safe_int(cfg.get("IterationEngine", "GAConvergenceTraceEvery", fallback="1"), 1),
        )
    except Exception:
        cfg_data["ga_convergence_trace_every"] = 1
    try:
        cfg_data["ga_convergence_trace_out_dir"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceOutDir", fallback="artifacts/ga_trace")
            or "artifacts/ga_trace"
        )
    except Exception:
        cfg_data["ga_convergence_trace_out_dir"] = "artifacts/ga_trace"
    try:
        cfg_data["ga_convergence_trace_song_filter"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceSongFilter", fallback="") or ""
        )
    except Exception:
        cfg_data["ga_convergence_trace_song_filter"] = ""

    # ForceGreatsFinder runs after GA and needs per-candidate BaseStats for signature grouping.
    # The GPU-native GA decode step keeps full post-gem Stats optional so the critical
    # GA->FG handoff does not spend CPU rebuilding data that the FG grouping path does not use.
    cfg_data["fg_require_stats"] = bool(manual_force_greats or force_greats_finder)

    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)

    tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
    tournament_k = max(1, min(8, int(tournament_k)))

    mutation_rate = safe_float(
        cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
    )
    mutation_rate = max(0.0, min(1.0, float(mutation_rate)))

    immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
    immigrant_rate = max(0.0, min(1.0, float(immigrant_rate)))

    db_seed = prev_record if (allow_db_seed and prev_record) else None
    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1

    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)

    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 0
    try:
        init_heuristic_k = int(str(os.environ.get("GPU_GA_INIT_HEURISTIC_K", "64") or "64"))
    except Exception:
        init_heuristic_k = 64
    init_heuristic_k = max(0, int(init_heuristic_k))
    init_heuristic_copies = 25

    db_seed_ids: Optional[np.ndarray] = None

    try:
        from gear_optimizer.solver.genetic import build_ga_init_heuristic_topk, extract_db_seed_ids

        if init_heuristic_k > 0:
            cache_key = None
            if cacheable_registry:
                cache_key = (pool_key, int(init_heuristic_k))
                with _PREP_CACHE_LOCK:
                    init_heuristic_topk = _lru_get(_INIT_HEURISTIC_TOPK_CACHE, cache_key)
                if init_heuristic_topk is None:
                    _cache_stats_inc("heur_miss")
                else:
                    _cache_stats_inc("heur_hit")

            if init_heuristic_topk is None:
                init_heuristic_topk = build_ga_init_heuristic_topk(
                    item_stats=gpu_data["item_stats"],
                    slot_start=gpu_data["slot_start"],
                    slot_count=gpu_data["slot_count"],
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    heuristic_k=int(init_heuristic_k),
                    n_slots=9,
                )
                if cache_key is not None and init_heuristic_topk is not None:
                    with _PREP_CACHE_LOCK:
                        _lru_put(
                            _INIT_HEURISTIC_TOPK_CACHE,
                            cache_key,
                            np.asarray(init_heuristic_topk, dtype=np.int32),
                            maxsize=_INIT_HEURISTIC_CACHE_MAX,
                        )

        db_seed_ids = extract_db_seed_ids(db_seed=db_seed, registry=registry, n_slots=9)
    except Exception:
        init_heuristic_topk = None
        db_seed_ids = None

    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0

    color_flags = build_color_flags(p_color, s_color, selected_color)

    elite_count_raw = GA_ELITISM
    try:
        if hasattr(cfg, "has_option") and cfg.has_option("IterationEngine", "GPU_GA_EliteCount"):
            elite_count_raw = cfg.get("IterationEngine", "GPU_GA_EliteCount", fallback=GA_ELITISM)
    except Exception:
        elite_count_raw = GA_ELITISM
    elite_count = safe_int(elite_count_raw, GA_ELITISM)
    elite_count = max(0, int(elite_count))

    song = _NativeSong(
        fp=str(fp),
        song_name=str(found_song_name),
        task_key=str(task_key),
        ga_seed=int(ga_seed) if ga_seed is not None else None,
        db_key=str(db_key),
        effective_difficulty=str(effective_difficulty),
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
        fg_debug=bool(fg_debug),
        calc_song=calc_song,
        meta_primary_color=meta_primary_color,
        meta_secondary_color=meta_secondary_color,
        fixed_stats=fixed_stats,
        current_gear_list=current_gear_list,
        current_mini_list=current_mini_list,
        enable_gear=bool(enable_gear),
        enable_mini=bool(enable_mini),
        force_greats_finder=bool(force_greats_finder),
        force_greats_config=force_greats_config,
        manual_force_greats=bool(manual_force_greats),
        prev_record=prev_record,
        attempt_lifetime=int(attempt_lifetime),
        prev_attempts_first=int(prev_attempts_first),
        db_best_fg_score=int(db_best_fg_score),
        registry=registry,
        cfg_data=cfg_data,
        color_flags=color_flags,
        gens_per_run=int(gens_per_run),
        num_runs=int(num_runs),
        n_genomes=int(n_genomes),
        init_heuristic_topk=init_heuristic_topk,
        init_heuristic_k=int(init_heuristic_k),
        init_heuristic_copies=int(init_heuristic_copies),
        db_seed_ids=db_seed_ids,
        db_seed_prob=float(getattr(ga_settings, "db_seed_prob", 0.0) or 0.0) if db_seed_ids is not None else 0.0,
        db_seed_copies=1 if db_seed_ids is not None else 0,
        db_seed_mutations=int(getattr(ga_settings, "db_seed_mutations", 1) or 0) if db_seed_ids is not None else 0,
        item_stats=gpu_data["item_stats"],
        slot_start=gpu_data["slot_start"],
        slot_count=gpu_data["slot_count"],
        base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
        elite_count=int(elite_count),
        mutation_rate=float(mutation_rate),
        immigrant_rate=float(immigrant_rate),
        tournament_k=int(tournament_k),
    )
    try:
        setattr(song, "_cpu_prep_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    return song


def run_native_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
    stop_requested=None,
    progress_cb=None,
    bundle_completed_cb=None,
) -> None:
    if not tasks:
        return

    cfg0 = None
    try:
        cfg0 = cfg_from_dict(tasks[0][3] or {})
    except Exception:
        cfg0 = None

    inflight_ram_mode = False
    try:
        raw_env = os.environ.get("INFLIGHT_RAM_MODE")
        if raw_env is not None and str(raw_env).strip() != "":
            inflight_ram_mode = _truthy(raw_env)
        elif cfg0 is not None:
            inflight_ram_mode = cfg0.getboolean("IterationEngine", "InFlight_RamMode", fallback=False)
    except Exception:
        inflight_ram_mode = False

    if inflight_ram_mode:
        # Allow more caching when the user explicitly opts into higher RAM usage.
        global _POOL_CACHE_MAX, _REGISTRY_CACHE_MAX, _INIT_HEURISTIC_CACHE_MAX

        _POOL_CACHE_MAX = max(int(_POOL_CACHE_MAX), 128)
        _REGISTRY_CACHE_MAX = max(int(_REGISTRY_CACHE_MAX), 128)
        _INIT_HEURISTIC_CACHE_MAX = max(int(_INIT_HEURISTIC_CACHE_MAX), 256)
        try:
            print(
                "[InFlight][RAM] enabled: default InFlight_GA_QueueMult=4 InFlight_PrepBufferMult=12 "
                f"cache_max={{pool:{int(_POOL_CACHE_MAX)} registry:{int(_REGISTRY_CACHE_MAX)} heur:{int(_INIT_HEURISTIC_CACHE_MAX)}}}"
            )
        except Exception:
            pass

    requested_inflight = max(1, int(in_flight_songs))
    inflight_limit = min(int(requested_inflight), len(tasks))

    # Limit concurrent in-flight songs by available GPU timeline slots.
    # Slot 0 is shared/fallback; we reserve 1..MAX_SONG_SLOTS-1 for deterministic reuse.
    try:
        from gear_optimizer.solver.taichi_gem.fields import MAX_SONG_SLOTS

        max_song_slots = int(MAX_SONG_SLOTS)
    except Exception:
        max_song_slots = 8
    song_slot_limit = max(1, int(max_song_slots) - 1)
    inflight_limit = min(int(inflight_limit), int(song_slot_limit))
    if int(in_flight_songs) > 1:
        try:
            cap_reasons: list[str] = []
            try:
                if int(len(tasks)) < int(requested_inflight):
                    cap_reasons.append(f"queue={int(len(tasks))}")
            except Exception:
                pass
            try:
                if int(song_slot_limit) < int(requested_inflight):
                    cap_reasons.append(f"usable_slots={int(song_slot_limit)}")
            except Exception:
                pass

            msg = (
                f"[InFlight] enabled: requested={int(in_flight_songs)} effective={int(inflight_limit)} "
                f"(GPU_SONG_SLOTS={int(max_song_slots)}, usable_slots={int(song_slot_limit)})"
            )
            if int(inflight_limit) < int(in_flight_songs):
                if cap_reasons:
                    msg += f" [capped by {', '.join(cap_reasons)}"
                else:
                    msg += " [capped"
                msg += "; set GPU_SONG_SLOTS >= InFlightSongs + 1 to avoid slot caps]"
            print(msg)
        except Exception:
            pass

    from gear_optimizer.solver.inflight_utils import SongSlotPool

    slot_pool = SongSlotPool(max_song_slots=int(max_song_slots))

    # How deep we allow the GPU-native GA queue to get (number of submitted GA jobs).
    # A deeper backlog reduces GPU idle gaps when CPU-side decode / FG prep briefly stalls.
    ga_queue_mult = 0
    if cfg0 is not None:
        try:
            ga_queue_mult = safe_int(cfg0.get("IterationEngine", "InFlight_GA_QueueMult", fallback="0"), 0)
        except Exception:
            ga_queue_mult = 0
    raw = os.environ.get("INFLIGHT_GA_QUEUE_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_mult = int(raw)
        except Exception:
            pass
    if ga_queue_mult <= 0:
        ga_queue_mult = 4 if inflight_ram_mode else 2
    ga_queue_mult = max(1, min(int(ga_queue_mult), 8))
    ga_queue_limit = max(1, int(inflight_limit) * int(ga_queue_mult))
    ga_queue_limit = min(int(ga_queue_limit), int(song_slot_limit))

    # CPU prep staging buffer size (prepared songs + in-flight preps).
    # Larger buffers avoid starvation on fast GPUs at the cost of RAM.
    prep_buffer_mult = 0
    if cfg0 is not None:
        try:
            prep_buffer_mult = safe_int(cfg0.get("IterationEngine", "InFlight_PrepBufferMult", fallback="0"), 0)
        except Exception:
            prep_buffer_mult = 0
    raw = os.environ.get("INFLIGHT_PREP_BUFFER_MULT")
    if raw is not None and str(raw).strip() != "":
        try:
            prep_buffer_mult = int(raw)
        except Exception:
            pass
    if prep_buffer_mult <= 0:
        prep_buffer_mult = 12 if inflight_ram_mode else 4
    prep_buffer_mult = max(1, min(int(prep_buffer_mult), 16))
    prep_limit = max(1, int(inflight_limit) * int(prep_buffer_mult))

    # FG aging fairness controls for continuous mode.
    fg_aging_trigger_ms = 750.0
    fg_aging_hard_ms = 2500.0
    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingTriggerMs"):
                fg_aging_trigger_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingTriggerMs", fallback="750"))
            if cfg0.has_option("IterationEngine", "InFlight_FGAgingHardMs"):
                fg_aging_hard_ms = float(cfg0.get("IterationEngine", "InFlight_FGAgingHardMs", fallback="2500"))
    except Exception:
        fg_aging_trigger_ms = 750.0
        fg_aging_hard_ms = 2500.0
    raw = os.environ.get("INFLIGHT_FG_AGING_TRIGGER_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_trigger_ms = float(raw)
        except Exception:
            pass
    raw = os.environ.get("INFLIGHT_FG_AGING_HARD_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_aging_hard_ms = float(raw)
        except Exception:
            pass
    fg_aging_trigger_s = max(0.0, float(fg_aging_trigger_ms) / 1000.0)
    fg_aging_hard_s = max(0.0, float(fg_aging_hard_ms) / 1000.0)
    if fg_aging_hard_s > 0.0 and fg_aging_hard_s < fg_aging_trigger_s:
        fg_aging_hard_s = float(fg_aging_trigger_s)

    # ForceGreats scheduling strategy is fixed to continuous mode.
    fg_scheduler_norm = _read_fg_scheduler_mode()

    # `FG_DrainAtEnd` controls whether we drain pending FG jobs when GA work completes.
    #
    # IMPORTANT: This should not "randomly" flip during a run. We parse it once here
    # with explicit semantics:
    # - default: True (ensures every song gets FG evaluated)
    # - config: parse truthy strings ("1/true/yes/on")
    # - env override: `INFLIGHT_FG_DRAIN_AT_END` or `FG_DRAIN_AT_END` (same truthy parsing)
    fg_drain_at_end = True
    fg_drain_src = "default(true)"
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "FG_DrainAtEnd"):
            raw = str(cfg0.get("IterationEngine", "FG_DrainAtEnd", fallback="") or "").strip()
            fg_drain_at_end = _truthy(raw)
            fg_drain_src = f"config({raw})"
        elif cfg0 is not None:
            fg_drain_src = "config(missing->false)"
    except Exception as exc:
        fg_drain_at_end = False
        fg_drain_src = f"config_error({type(exc).__name__})"
    raw_env = os.environ.get("INFLIGHT_FG_DRAIN_AT_END")
    if raw_env is None or str(raw_env).strip() == "":
        raw_env = os.environ.get("FG_DRAIN_AT_END")
    if raw_env is not None and str(raw_env).strip() != "":
        fg_drain_at_end = _truthy(raw_env)
        fg_drain_src = f"env({raw_env})"

    fg_ga_credit_budget_cfg, _fg_ga_credit_explicit = _read_fg_ga_credit_budget(
        cfg0,
        default_budget=max(1, int(inflight_limit)),
    )
    continuous_ga_dispatch_burst = _read_continuous_ga_dispatch_burst(cfg0, default_burst=2)
    fg_adaptive_submit_enabled, fg_adaptive_submit_max_burst = _read_continuous_fg_adaptive_submit(cfg0)

    try:
        msg = f"[InFlight][FG] scheduler={fg_scheduler_norm} drain_at_end={bool(fg_drain_at_end)} source={fg_drain_src}"
        msg += (
            f" (GA_CreditBudget={int(fg_ga_credit_budget_cfg)}, "
            f"GA_DispatchBurst={int(continuous_ga_dispatch_burst)}, "
            f"FG_AdaptiveSubmit={int(bool(fg_adaptive_submit_enabled))}, "
            f"FG_AdaptiveMaxBurst={int(fg_adaptive_submit_max_burst)}, "
            f"InFlight_FGAgingTriggerMs={int(fg_aging_trigger_s * 1000.0)}, "
            f"InFlight_FGAgingHardMs={int(fg_aging_hard_s * 1000.0)})"
        )
        print(msg)
    except Exception:
        pass

    inflight_fg_hold_slots = True
    try:
        if cfg0 is not None:
            inflight_fg_hold_slots = cfg0.getboolean("IterationEngine", "InFlight_FGHoldSlots", fallback=True)
    except Exception:
        inflight_fg_hold_slots = True
    hold_slots_explicit = False
    try:
        if cfg0 is not None:
            hold_slots_explicit = bool(cfg0.has_option("IterationEngine", "InFlight_FGHoldSlots"))
    except Exception:
        hold_slots_explicit = False
    raw = os.environ.get("INFLIGHT_FG_HOLD_SLOTS")
    if raw is not None and str(raw).strip() != "":
        hold_slots_explicit = True
        inflight_fg_hold_slots = _truthy(raw)

    # Slot pressure hint + safety:
    # `InFlight_FGHoldSlots=true` keeps timeline slots reserved after GA completes so FG can reuse resident grids.
    # This only works when there is enough spare slot capacity beyond the GA queue depth; otherwise the run
    # will inevitably hit slot-acquire stalls and start FG early (often looking like "GA -> FG per song").
    try:
        from gear_optimizer.core.config import read_iteration_engine_settings

        ie = read_iteration_engine_settings(cfg0)
        fg_enabled = bool(ie.force_greats_mode) and (bool(ie.force_greats_finder) or bool(ie.manual_force_greats))
    except Exception:
        fg_enabled = False

    # Reserve a dedicated FG slot partition so GA cannot consume every slot.
    fg_slot_reserve = _read_fg_slot_reserve(
        cfg0,
        fg_enabled=bool(fg_enabled),
        inflight_limit=int(inflight_limit),
        song_slot_limit=int(song_slot_limit),
    )
    if fg_slot_reserve:
        ga_queue_limit = min(int(ga_queue_limit), max(1, int(song_slot_limit) - int(fg_slot_reserve)))

    ga_queue_limit_base = int(ga_queue_limit)

    inflight_ga_dynamic_queue = False
    try:
        # Enable by default only when inflight + FG are both active, because dynamic queue
        # sizing primarily exists to mitigate GA/FG song-slot pressure.
        inflight_ga_dynamic_queue = bool(fg_enabled and int(in_flight_songs) > 1)
    except Exception:
        inflight_ga_dynamic_queue = False
    try:
        if cfg0 is not None:
            inflight_ga_dynamic_queue = cfg0.getboolean(
                "IterationEngine",
                "InFlight_GA_DynamicQueue",
                fallback=bool(inflight_ga_dynamic_queue),
            )
    except Exception:
        pass
    raw = os.environ.get("INFLIGHT_GA_DYNAMIC_QUEUE")
    if raw is not None and str(raw).strip() != "":
        inflight_ga_dynamic_queue = _truthy(raw)

    # Reserve extra free slots when we have recently hit GA slot-acquire stalls.
    ga_queue_extra_free_on_slot_pressure = 1
    try:
        if cfg0 is not None:
            ga_queue_extra_free_on_slot_pressure = safe_int(
                cfg0.get("IterationEngine", "InFlight_GA_ExtraFreeSlotsOnSlotPressure", fallback="1"),
                1,
            )
    except Exception:
        ga_queue_extra_free_on_slot_pressure = 1
    raw = os.environ.get("INFLIGHT_GA_EXTRA_FREE_SLOTS_ON_SLOT_PRESSURE")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_extra_free_on_slot_pressure = int(raw)
        except Exception:
            pass
    ga_queue_extra_free_on_slot_pressure = max(0, min(int(ga_queue_extra_free_on_slot_pressure), 8))

    ga_queue_pressure_window_s = 1.5
    try:
        if cfg0 is not None:
            ga_queue_pressure_window_s = float(
                cfg0.get("IterationEngine", "InFlight_GA_SlotPressureWindowSec", fallback="1.5")
            )
    except Exception:
        ga_queue_pressure_window_s = 1.5
    raw = os.environ.get("INFLIGHT_GA_SLOT_PRESSURE_WINDOW_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            ga_queue_pressure_window_s = float(raw)
        except Exception:
            pass
    ga_queue_pressure_window_s = max(0.0, min(float(ga_queue_pressure_window_s), 60.0))

    ga_slack_slots = 0
    try:
        ga_slack_slots = max(0, int(song_slot_limit) - int(ga_queue_limit))
    except Exception:
        ga_slack_slots = 0

    fg_hold_budget = int(ga_slack_slots)

    if inflight_fg_hold_slots and fg_enabled and int(in_flight_songs) > 1:
        if int(fg_hold_budget) <= 0:
            required_gpu_slots = None
            try:
                required_usable = int(ga_queue_limit)
                required_gpu_slots = int(required_usable) + 1
            except Exception:
                required_gpu_slots = None
            try:
                msg = (
                    "[InFlight][WARN] Slot pressure: InFlight_FGHoldSlots=true with "
                    f"usable_slots={int(song_slot_limit)} ga_queue_limit={int(ga_queue_limit)} slack={int(ga_slack_slots)}; "
                    "FG slot reuse is impossible with the current GA queue depth."
                )
                if required_gpu_slots is not None:
                    msg += f" (For full slot reuse: set GPU_SONG_SLOTS>={int(required_gpu_slots)} or reduce InFlight_GA_QueueMult.)"
                print(msg)
            except Exception:
                pass
            # No slack beyond the GA queue depth: any attempt to hold FG slots will eventually starve GA.
            # If the user didn't explicitly request hold-slots behavior, prefer throughput stability.
            if not hold_slots_explicit:
                inflight_fg_hold_slots = False
                fg_hold_budget = 0
                try:
                    print("[InFlight][Auto] Disabling InFlight_FGHoldSlots (no slack song slots available).")
                except Exception:
                    pass

    # Configure GPU-native GA run buffers BEFORE the GPU executor initializes Taichi fields.
    # The executor warms FG kernels on startup which triggers taichi_gem field allocation; if
    # we don't size buffers up front, GA payload downloads become padded and require staging.
    try:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields

        ga_runs = 1
        try:
            from gear_optimizer.data.models import GASettings

            settings = GASettings.from_cfg(cfg0) if cfg0 is not None else GASettings.from_cfg(None)
            ga_runs = int(settings.multi_start)
        except Exception:
            ga_runs = 1

        gpu_fields.configure_ga_run_buffers(max_runs=ga_runs, max_genomes=GA_POPULATION_SIZE)
    except Exception:
        pass

    # Windows: short timed waits (0-10ms) can quantize into ~15.6ms bubbles when the system timer
    # period is left at the default. Native in-flight mode is explicitly throughput-focused and
    # benefits significantly from 1ms timer granularity in the GPU owner thread/coalescer.
    #
    # Keep this override opt-out: users can set `GPU_ALLOW_SYSTEM_TIMER_OVERRIDE=0` to disable.
    try:
        if os.name == "nt" and os.environ.get("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE") is None:
            os.environ["GPU_ALLOW_SYSTEM_TIMER_OVERRIDE"] = "1"
            if _truthy(os.environ.get("PERF_TIMING", "0")):
                print(
                    "[InFlight][Perf] Enabled 1ms Windows timer period for GPU batching "
                    "(set GPU_ALLOW_SYSTEM_TIMER_OVERRIDE=0 to disable)."
                )
    except Exception:
        pass

    gpu_executor = get_gpu_executor()
    gpu_executor.start(in_process=True)
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    stage_profile_enabled = _truthy(os.environ.get("INFLIGHT_STAGE_PROFILE", "0"))
    stage_profile_path = os.environ.get("INFLIGHT_STAGE_PROFILE_PATH")
    if stage_profile_enabled and not stage_profile_path:
        try:
            from gear_optimizer.core.constants import PATHS

            stage_profile_path = PATHS.bin_path("inflight_stage_profile.json")
        except Exception:
            stage_profile_path = None
    stage_profiler = _InFlightStageProfiler(enabled=stage_profile_enabled, out_path=stage_profile_path)

    post_sender = _PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
    fg_decision_debug = _truthy(os.environ.get("INFLIGHT_FG_DECISION_DEBUG", "0"))
    fg_submit_debug = _truthy(os.environ.get("INFLIGHT_FG_SUBMIT_DEBUG", "0"))

    # Progress UI "New" counter should reflect *session-best* improvements, not the stale DB snapshot
    # that in-flight tasks can start with (DB persistence is async, and many repeats can overlap).
    progress_best_lock = threading.Lock()
    progress_best: dict[str, tuple[int, int]] = {}

    def _progress_best_snapshot(db_key: str) -> tuple[int, int]:
        key = str(db_key or "").strip()
        if not key:
            return (0, 0)
        with progress_best_lock:
            return progress_best.get(key, (0, 0))

    def _progress_best_update(db_key: str, *, best_score: int | None = None, best_fg: int | None = None) -> None:
        key = str(db_key or "").strip()
        if not key:
            return
        try:
            score_new = int(best_score) if best_score is not None else None
        except Exception:
            score_new = None
        try:
            fg_new = int(best_fg) if best_fg is not None else None
        except Exception:
            fg_new = None
        with progress_best_lock:
            score0, fg0 = progress_best.get(key, (0, 0))
            if score_new is not None and score_new > int(score0):
                score0 = int(score_new)
            if fg_new is not None and fg_new > int(fg0):
                fg0 = int(fg_new)
            progress_best[key] = (int(score0), int(fg0))

    def _emit_progress(*, completed_delta: int = 0, failed_delta: int = 0, record_info: dict | None = None) -> None:
        if progress_cb is None:
            return
        try:
            progress_cb(completed_delta=completed_delta, failed_delta=failed_delta, record_info=record_info)
        except Exception:
            pass

    def _post(item: dict) -> None:
        if post_sender is not None:
            post_sender.send(item)
        if isinstance(item, dict) and item.get("_error") and not bool(item.get("_suppress_progress")):
            try:
                song_label = (
                    item.get("song")
                    or item.get("_song_name")
                    or item.get("song_name")
                    or item.get("_queue_label")
                    or item.get("_queue_key")
                )
            except Exception:
                song_label = None
            _emit_progress(
                completed_delta=1,
                failed_delta=1,
                record_info={"song": song_label, "status": "FAILED"},
            )

    pending_tasks = deque(t for t in tasks if _task_key(t) not in completed_songs)
    bundle_progress: dict[int, int] = {}
    prepared: deque[_NativeSong] = deque()
    pending_fg: deque[_NativeSong] = deque()

    def _bundle_runs(task: tuple) -> list[dict]:
        bundle = _extract_repeat_bundle(task)
        if not isinstance(bundle, dict):
            return []
        runs = bundle.get("runs")
        if not isinstance(runs, list):
            return []
        out: list[dict] = []
        for ctx in runs:
            if _is_repeat_ctx_dict(ctx):
                out.append(dict(ctx))
        return out

    def _next_logical_task(task: tuple) -> tuple[tuple, dict | None]:
        runs = _bundle_runs(task)
        if not runs:
            return task, None
        cursor = max(0, int(bundle_progress.get(id(task), 0)))
        if cursor >= len(runs):
            cursor = len(runs) - 1
        repeat_ctx = dict(runs[cursor])
        return _materialize_repeat_task(task, repeat_ctx), repeat_ctx

    def _bind_bundle_song(song: _NativeSong, parent_task: tuple, repeat_ctx: dict | None) -> None:
        if repeat_ctx is None or not _bundle_runs(parent_task):
            return
        setattr(song, "_bundle_parent_task", parent_task)
        setattr(song, "_bundle_task_key", _task_key(parent_task))
        try:
            setattr(song, "_bundle_repeat_index", int(repeat_ctx.get("repeat_index") or 0))
            setattr(song, "_bundle_repeat_total", int(repeat_ctx.get("repeat_total") or 0))
        except Exception:
            setattr(song, "_bundle_repeat_index", 0)
            setattr(song, "_bundle_repeat_total", 0)

    def _advance_bundle(parent_task: tuple, *, song_name: str, record_info: dict | None = None, failed: bool = False) -> bool:
        runs = _bundle_runs(parent_task)
        if not runs:
            return False
        next_idx = max(0, int(bundle_progress.get(id(parent_task), 0))) + 1
        bundle_progress[id(parent_task)] = int(next_idx)

        # Bundled repeats behave like a queue "inflation" to N repeat-runs, but the optimizer queues them as
        # a single bundle to reduce overhead. Emit progress once per repeat-run so the UI/throughput reflects
        # real work (and so repeat failures are visible).
        info: dict = {}
        if isinstance(record_info, dict):
            try:
                info = dict(record_info)
            except Exception:
                info = {}

        repeat_label = None
        try:
            ctx = runs[int(next_idx) - 1] if int(next_idx) > 0 and int(next_idx) <= len(runs) else None
            if _is_repeat_ctx_dict(ctx):
                ridx = int(ctx.get("repeat_index") or next_idx)
                rtotal = int(ctx.get("repeat_total") or len(runs))
                if ridx > 0 and rtotal > 1:
                    repeat_label = f"{song_name} (Run {ridx}/{rtotal})"
        except Exception:
            repeat_label = None

        info.setdefault("song", repeat_label or song_name)
        info.setdefault("status", "FAILED" if failed else "DONE")

        _emit_progress(
            completed_delta=1,
            failed_delta=1 if failed else 0,
            record_info=info,
        )

        if next_idx < len(runs):
            pending_tasks.appendleft(parent_task)
            return True

        bundle_key = _task_key(parent_task)
        completed_songs.add(bundle_key)
        if memory_resume_tracker:
            memory_resume_tracker.mark_completed(song_name)
        if bundle_completed_cb is not None:
            try:
                bundle_completed_cb(bundle_key, completed_songs)
            except Exception:
                pass
        return True

    # GA jobs submitted to the GPU executor (in-order). We intentionally keep a
    # backlog so CPU-side decode/post-processing can't create GPU idle gaps.
    ga_inflight: deque[_NativeSong] = deque()

    ga_seed = str(os.environ.get("GA_SEED") or "").strip()
    prep_workers = 0
    if cfg0 is not None:
        try:
            prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_PrepWorkers", fallback="0"), 0)
        except Exception:
            prep_workers = 0
    raw = os.environ.get("INFLIGHT_PREP_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            prep_workers = int(raw)
        except Exception:
            pass
    if prep_workers <= 0:
        if ga_seed:
            prep_workers = 1
        else:
            prep_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="prep")

    prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=prep_workers, thread_name_prefix="SongPrep")
    prep_inflight: deque[tuple[tuple, tuple, concurrent.futures.Future, float]] = deque()

    decode_workers = 0
    if cfg0 is not None:
        try:
            decode_workers = safe_int(cfg0.get("IterationEngine", "InFlight_DecodeWorkers", fallback="0"), 0)
        except Exception:
            decode_workers = 0
    raw = os.environ.get("INFLIGHT_DECODE_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            decode_workers = int(raw)
        except Exception:
            pass
    if decode_workers <= 0:
        decode_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="decode")
    decode_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=decode_workers,
        thread_name_prefix="GADecode",
    )
    decode_inflight: deque[_NativeSong] = deque()

    active_runtime_song_label = ""

    def _active_runtime_song() -> str:
        try:
            if ga_inflight:
                song = ga_inflight[0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        try:
            if decode_inflight:
                song = decode_inflight[0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        try:
            if fg_futures:
                song = fg_futures[0][0]
                return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            pass
        return ""

    def _emit_active_runtime_song(*, force: bool = False) -> None:
        nonlocal active_runtime_song_label
        song_label = _active_runtime_song()
        if not force and song_label == active_runtime_song_label:
            return
        active_runtime_song_label = str(song_label or "").strip()
        if not active_runtime_song_label:
            return
        _emit_progress(
            completed_delta=0,
            failed_delta=0,
            record_info={"song": active_runtime_song_label, "status": "RUNNING"},
        )

    fg_workers_default = min(4, inflight_limit)
    fg_workers = fg_workers_default
    if cfg0 is not None:
        try:
            fg_workers = safe_int(
                cfg0.get("IterationEngine", "InFlight_FGWorkers", fallback=str(fg_workers_default)),
                fg_workers_default,
            )
        except Exception:
            fg_workers = fg_workers_default
    raw = os.environ.get("INFLIGHT_FG_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_workers = int(raw)
        except Exception:
            pass
    fg_workers = max(1, min(int(fg_workers), inflight_limit))

    fg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=fg_workers, thread_name_prefix="FG")
    fg_futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
    fg_ga_credit_budget = max(1, int(fg_ga_credit_budget_cfg))
    fg_ga_credit = int(fg_ga_credit_budget)

    fg_batch_max = int(fg_workers)
    try:
        raw = os.environ.get("INFLIGHT_FG_BATCH_MAX")
        if raw is not None and str(raw).strip() != "":
            fg_batch_max = int(raw)
    except Exception:
        fg_batch_max = int(fg_workers)
    fg_batch_max = max(1, min(int(fg_batch_max), int(fg_workers)))

    fg_prep_workers = 0
    if cfg0 is not None:
        try:
            fg_prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_FGPrepWorkers", fallback="0"), 0)
        except Exception:
            fg_prep_workers = 0
    raw = os.environ.get("INFLIGHT_FG_PREP_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_prep_workers = int(raw)
        except Exception:
            pass
    if fg_prep_workers <= 0:
        fg_prep_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="fg_prep")
    fg_prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=fg_prep_workers, thread_name_prefix="FGPrep")

    db_prefetch_workers = 0
    if cfg0 is not None:
        try:
            db_prefetch_workers = safe_int(cfg0.get("IterationEngine", "InFlight_DBPrefetchWorkers", fallback="0"), 0)
        except Exception:
            db_prefetch_workers = 0
    raw = os.environ.get("INFLIGHT_DB_PREFETCH_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            db_prefetch_workers = int(raw)
        except Exception:
            pass
    if db_prefetch_workers <= 0:
        db_prefetch_workers = max(1, min(int(fg_prep_workers), 4))
    db_prefetch_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=int(db_prefetch_workers),
        thread_name_prefix="FGDBPrefetch",
    )

    fg_prep_inflight: deque[_NativeSong] = deque()
    fg_jit_warmup_submitted = False

    last_slot_block_t: float | None = None
    ga_queue_debug = _truthy(os.environ.get("INFLIGHT_GA_QUEUE_DEBUG", "0"))
    last_ga_queue_limit_effective: int | None = None
    completion_event = threading.Event()
    completion_future_ids: set[int] = set()
    completion_lock = threading.Lock()
    completion_registered_attr = "_metafinder_completion_registered"
    ga_queue_limit_cache_key: tuple[bool, int, int, int, int] | None = None
    ga_queue_limit_cache_value = int(ga_queue_limit_base)
    stop_poll_interval_s = 0.05
    stop_next_check_mono = 0.0
    stop_cached_requested = False
    memory_poll_interval_s = 0.05
    memory_next_check_mono = 0.0
    memory_cached_requested = False

    def _register_completion_future(fut: concurrent.futures.Future | None) -> None:
        if fut is None:
            return
        marked_registered = False
        try:
            if bool(getattr(fut, completion_registered_attr, False)):
                return
            setattr(fut, completion_registered_attr, True)
            marked_registered = True
        except Exception:
            pass
        try:
            fut_id = int(id(fut))
        except Exception:
            if marked_registered:
                try:
                    setattr(fut, completion_registered_attr, False)
                except Exception:
                    pass
            return
        try:
            with completion_lock:
                if fut_id in completion_future_ids:
                    return
                completion_future_ids.add(fut_id)
        except Exception:
            if marked_registered:
                try:
                    setattr(fut, completion_registered_attr, False)
                except Exception:
                    pass
            return

        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            try:
                completion_event.set()
            except Exception:
                pass
            try:
                with completion_lock:
                    completion_future_ids.discard(_fut_id)
            except Exception:
                pass

        try:
            fut.add_done_callback(_on_done)
        except Exception:
            try:
                setattr(fut, completion_registered_attr, False)
            except Exception:
                pass
            try:
                completion_event.set()
            except Exception:
                pass

    def _effective_ga_queue_limit() -> int:
        nonlocal ga_queue_limit_cache_key, ga_queue_limit_cache_value
        if not inflight_ga_dynamic_queue:
            return int(ga_queue_limit_base)

        extra_free = 0
        slot_pressure_active = False

        if last_slot_block_t is not None and ga_queue_pressure_window_s > 0.0:
            try:
                if (time.monotonic() - float(last_slot_block_t)) <= float(ga_queue_pressure_window_s):
                    slot_pressure_active = True
                    extra_free = max(int(extra_free), int(ga_queue_extra_free_on_slot_pressure))
            except Exception:
                pass

        cache_key = (
            bool(slot_pressure_active),
            int(extra_free),
            int(fg_slot_reserve),
            int(song_slot_limit),
            int(ga_queue_limit_base),
        )
        if cache_key == ga_queue_limit_cache_key:
            return int(ga_queue_limit_cache_value)

        min_free = int(fg_slot_reserve) + int(extra_free)
        # Keep at least 1 slot usable; (song_slot_limit - min_free) must be >= 1.
        min_free = max(0, min(int(min_free), max(0, int(song_slot_limit) - 1)))
        limit_from_free = max(1, int(song_slot_limit) - int(min_free))
        ga_queue_limit_cache_value = max(1, min(int(ga_queue_limit_base), int(limit_from_free)))
        ga_queue_limit_cache_key = cache_key
        return int(ga_queue_limit_cache_value)

    def _stop_requested_cached(now_mono: float | None = None) -> bool:
        nonlocal stop_next_check_mono, stop_cached_requested
        if stop_cached_requested:
            return True
        if stop_requested is None or not callable(stop_requested):
            return False
        now_val = float(time.monotonic() if now_mono is None else now_mono)
        if now_val < float(stop_next_check_mono):
            return False
        stop_cached_requested = bool(stop_requested())
        if stop_cached_requested:
            return True
        stop_next_check_mono = now_val + float(stop_poll_interval_s)
        return False

    def _memory_release_requested_cached(now_mono: float | None = None) -> bool:
        nonlocal memory_next_check_mono, memory_cached_requested
        if memory_cached_requested:
            return True
        now_val = float(time.monotonic() if now_mono is None else now_mono)
        if now_val < float(memory_next_check_mono):
            return False
        memory_cached_requested = bool(memory_release_requested())
        if memory_cached_requested:
            return True
        memory_next_check_mono = now_val + float(memory_poll_interval_s)
        return False

    def _has_waitable_futures() -> bool:
        if ga_inflight or prep_inflight or decode_inflight or fg_prep_inflight or fg_futures:
            return True
        for song in pending_fg:
            if song.db_loadouts_future is not None:
                return True
        return False

    def _log_abort(exc: Exception) -> None:
        try:
            from gear_optimizer.core.constants import PATHS

            path = PATHS.bin_path("inflight_native_abort.log")
        except Exception:
            path = None
        if not path:
            return
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            snapshot = (
                f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)}"
            )
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{ts}] {type(exc).__name__}: {exc}\n")
                fh.write(snapshot + "\n")
                fh.write(traceback.format_exc() + "\n")
        except Exception:
            pass

    # Prime the pipeline: pre-prepare a backlog synchronously so the GPU queue
    # doesn't starve on early song boundaries while prep workers spin up.
    #
    # High-end GPUs can burn through the first GA jobs quickly; priming only 1–2 songs
    # can still leave the GPU idle while CPU prep catches up. Default to priming up to
    # a modest 4-8 song backlog on smaller in-flight runs, but allow override via env
    # var/config for experimentation.
    prime_target = 0
    if cfg0 is not None:
        try:
            prime_target = safe_int(cfg0.get("IterationEngine", "InFlight_PrimeTarget", fallback="0"), 0)
        except Exception:
            prime_target = 0
    raw = os.environ.get("INFLIGHT_PRIME_TARGET")
    if raw is not None and str(raw).strip() != "":
        try:
            prime_target = int(raw)
        except Exception:
            pass
    if prime_target <= 0:
        prime_target = _default_prime_target(
            inflight_limit=inflight_limit,
            prep_limit=prep_limit,
            pending_count=len(pending_tasks),
        )
    else:
        prime_target = max(0, min(int(prime_target), int(prep_limit), len(pending_tasks)))
    for _ in range(int(prime_target)):
        first = pending_tasks.popleft()
        song_name = first[1]
        bundle_key = _task_key(first)
        if bundle_key in completed_songs:
            continue
        logical_task, repeat_ctx = _next_logical_task(first)
        task_key = _task_key(logical_task)
        try:
            t0 = time.perf_counter()
            prepared_song = _prepare_song(logical_task)
            _bind_bundle_song(prepared_song, first, repeat_ctx)
            prepared.append(prepared_song)
            stage_profiler.record(
                "prep",
                time.perf_counter() - t0,
                cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                song=task_key,
            )
        except Exception as exc:
            payload = build_error_payload(
                song_name=str(song_name),
                queue_key=str(task_key),
                queue_label=str(task_key),
                exc=exc,
                trace=traceback.format_exc(),
            )
            if repeat_ctx is not None:
                payload["_suppress_progress"] = True
            _post(payload)
            if repeat_ctx is not None:
                _advance_bundle(first, song_name=str(song_name), failed=True)
            else:
                completed_songs.add(task_key)
                if memory_resume_tracker:
                    memory_resume_tracker.mark_completed(song_name)

    try:
        if prepared and not fg_jit_warmup_submitted:
            fg_prep_executor.submit(_warmup_fg_jit, prepared[0].calc_song, prepared[0].ref_arrays)
            fg_jit_warmup_submitted = True
    except Exception:
        pass

    def _pop_next_fg(*, allow_not_ready: bool) -> Optional[_NativeSong]:
        """
        Pick a song for FG submission.

        Normally, we only pop songs whose FG prep is complete (so the FG worker can immediately
        start GPU work). However, when we're blocked on slot acquisition, waiting for prep
        completion can stall GA submission and create prolonged GPU bubbles. In that case,
        we allow popping a not-yet-ready FG song and let the FG worker block on the prep future.
        """
        for candidate in list(pending_fg):
            fut = candidate.fg_prep_future
            if fut is None:
                try:
                    pending_fg.remove(candidate)
                except Exception:
                    pass
                return candidate
            if allow_not_ready:
                try:
                    pending_fg.remove(candidate)
                except Exception:
                    pass
                return candidate
            try:
                if fut.done():
                    pending_fg.remove(candidate)
                    return candidate
            except Exception:
                continue
        return None

    def _oldest_pending_fg_wait_s(now_s: float) -> float:
        if not pending_fg:
            return 0.0
        oldest_t0 = None
        for candidate in pending_fg:
            t0 = getattr(candidate, "fg_queued_t0", None)
            if not isinstance(t0, (int, float)) or float(t0) <= 0.0:
                try:
                    candidate.fg_queued_t0 = float(now_s)
                except Exception:
                    pass
                t0 = float(now_s)
            if oldest_t0 is None or float(t0) < float(oldest_t0):
                oldest_t0 = float(t0)
        if oldest_t0 is None:
            return 0.0
        return max(0.0, float(now_s) - float(oldest_t0))

    def _continuous_note_ga_submit() -> None:
        nonlocal fg_ga_credit
        if pending_fg:
            fg_ga_credit = max(-int(fg_ga_credit_budget), int(fg_ga_credit) - 1)
        else:
            fg_ga_credit = int(fg_ga_credit_budget)

    def _continuous_note_fg_submit() -> None:
        nonlocal fg_ga_credit
        fg_ga_credit = int(fg_ga_credit_budget)

    try:
        last_progress = time.monotonic()
        last_stall_report = last_progress
        last_heartbeat = last_progress
        last_throughput = last_progress
        last_stage_emit = last_progress
        heartbeat_sec = 0.0
        try:
            heartbeat_sec = float(os.environ.get("INFLIGHT_HEARTBEAT_SEC", "0") or "0")
        except Exception:
            heartbeat_sec = 0.0

        throughput_sec = 0.0
        try:
            throughput_sec = float(os.environ.get("INFLIGHT_THROUGHPUT_SEC", "0") or "0")
        except Exception:
            throughput_sec = 0.0

        stage_emit_sec = 0.0
        try:
            stage_emit_sec = float(os.environ.get("INFLIGHT_STAGE_PROFILE_EMIT_SEC", "0") or "0")
        except Exception:
            stage_emit_sec = 0.0

        event_wait_timeout_s = float(_read_inflight_event_wait_timeout_s())
        event_wait_gpu_cap_s = float(_read_inflight_event_wait_gpu_cap_s())
        event_wait_short_spin_s = float(_read_inflight_event_wait_short_spin_s())

        profile_max_songs = 0
        try:
            profile_max_songs = int(os.environ.get("INFLIGHT_PROFILE_MAX_SONGS", "0") or "0")
        except Exception:
            profile_max_songs = 0
        profile_max_songs = max(0, int(profile_max_songs))
        completed_baseline = 0
        try:
            completed_baseline = int(len(completed_songs))
        except Exception:
            completed_baseline = 0

        stopping = False
        while (
            pending_tasks
            or prepared
            or prep_inflight
            or pending_fg
            or ga_inflight
            or decode_inflight
            or fg_prep_inflight
            or fg_futures
        ):
            now = time.monotonic()
            if _memory_release_requested_cached(now):
                break

            # Optional profiling cap: stop after N completed songs/tasks.
            if (not stopping) and profile_max_songs > 0:
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now >= int(profile_max_songs):
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass

            if _stop_requested_cached(now):
                if not stopping:
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass
                    # Best-effort cancel of queued prep/decode work.
                    try:
                        for _task, fut, _t0 in list(prep_inflight):
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                        prep_inflight.clear()
                    except Exception:
                        pass
                    try:
                        for song in list(decode_inflight):
                            try:
                                if song.decode_future is not None:
                                    song.decode_future.cancel()
                            except Exception:
                                pass
                        # Keep entries so we can still drain the deque safely.
                    except Exception:
                        pass

            # Periodic throughput reporting (opt-in via env).
            if throughput_sec > 0 and (now - last_throughput) >= float(throughput_sec):
                last_throughput = now
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now > 0:
                    wall_s = max(1e-9, float(time.perf_counter() - float(stage_profiler._t0)))
                    per_h = float(completed_now) * 3600.0 / wall_s
                    try:
                        pending_now = int(len(pending_tasks)) + int(len(prepared)) + int(len(pending_fg))
                    except Exception:
                        pending_now = 0
                    try:
                        avg_s = wall_s / float(completed_now)
                        eta_s = float(pending_now) * avg_s if pending_now > 0 else 0.0
                    except Exception:
                        avg_s = 0.0
                        eta_s = 0.0
                    try:
                        print(
                            f"[InFlight][Throughput] done={completed_now} pending~{pending_now} "
                            f"rate={per_h:.1f}/h avg={avg_s:.2f}s ETA={eta_s / 60.0:.1f}m"
                        )
                    except Exception:
                        pass
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="throughput",
                        metrics={
                            "completed": int(completed_now),
                            "pending": int(pending_now),
                            "rate_per_hour": float(per_h),
                            "avg_task_sec": float(avg_s),
                            "eta_sec": float(eta_s),
                        },
                    )

            # Periodic stage profile emission (opt-in via env).
            if stage_emit_sec > 0 and stage_profiler.enabled and (now - last_stage_emit) >= float(stage_emit_sec):
                last_stage_emit = now
                try:
                    stage_profiler.emit()
                except Exception:
                    pass

            did_work = False
            blocked_on_slot_acquire = False

            # Move completed song preps into the staging queue.
            for task, logical_task, fut, t_submit in list(prep_inflight):
                if not fut.done():
                    continue
                prep_inflight.remove((task, logical_task, fut, t_submit))
                did_work = True
                song_name = task[1]
                bundle_key = _task_key(task)
                task_key = _task_key(logical_task)
                if bundle_key in completed_songs:
                    continue
                try:
                    prepared_song = fut.result()
                    repeat_ctx = _extract_repeat_ctx(logical_task)
                    _bind_bundle_song(prepared_song, task, repeat_ctx)
                    stage_profiler.record(
                        "prep",
                        time.perf_counter() - float(t_submit),
                        cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                        song=task_key,
                    )
                    prepared.append(prepared_song)
                    try:
                        prev_best_score = safe_int((prepared_song.prev_record or {}).get("score", 0), 0)
                    except Exception:
                        prev_best_score = 0
                    _progress_best_update(
                        prepared_song.db_key,
                        best_score=int(prev_best_score),
                        best_fg=int(getattr(prepared_song, "db_best_fg_score", 0) or 0),
                    )
                    if prepared and not fg_jit_warmup_submitted:
                        try:
                            fg_prep_executor.submit(_warmup_fg_jit, prepared[0].calc_song, prepared[0].ref_arrays)
                            fg_jit_warmup_submitted = True
                        except Exception:
                            pass
                except Exception as exc:
                    payload = build_error_payload(
                        song_name=str(song_name),
                        queue_key=str(task_key),
                        queue_label=str(task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                    )
                    repeat_ctx = _extract_repeat_ctx(logical_task)
                    if repeat_ctx is not None:
                        payload["_suppress_progress"] = True
                    _post(payload)
                    if repeat_ctx is not None:
                        _advance_bundle(task, song_name=str(song_name), failed=True)
                    else:
                        completed_songs.add(task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song_name)

            # Finalize prepared FG jobs (CPU prep done) so the GPU stage can start immediately when scheduled.
            for song in list(fg_prep_inflight):
                # `fg_prep_future` may be consumed by the FG worker (it waits on the
                # future and then clears it). Ensure we still drain the tracking deque
                # so the main loop can terminate cleanly.
                if song.fg_prep_future is None:
                    fg_prep_inflight.remove(song)
                    did_work = True
                    continue
                if not song.fg_prep_future.done():
                    continue
                fg_prep_inflight.remove(song)
                did_work = True
                try:
                    t_submit = getattr(song, "_fg_prep_submit_t0", None)
                    if t_submit is not None:
                        stage_profiler.record(
                            "fg_prep",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(song, "_cpu_fg_prep_s", None),
                            song=song.song_name,
                        )
                        setattr(song, "_fg_prep_submit_t0", None)
                    song.fg_prep_future.result()
                except Exception as exc:
                    _post(
                        build_error_payload(
                            song_name=str(song.song_name),
                            queue_key=str(song.task_key),
                            queue_label=str(song.task_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                    )
                finally:
                    song.fg_prep_future = None

            # Keep the GPU queue full while using spare CPU time to prep future songs.
            #
            # - `ga_inflight` bounds the number of submitted GPU-native GA jobs.
            # - `prepared` is a CPU-side staging buffer; keeping it non-empty prevents
            #   starvation if CPU prep briefly falls behind GPU throughput.
            # - We alternate submit/prep to minimize the initial "startup bubble".
            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = _oldest_pending_fg_wait_s(float(now))
            except Exception:
                fg_oldest_wait_s = 0.0

            ga_dispatch_count = 0
            while True:
                # Submit GA jobs whenever we have prepared work and GPU queue capacity.
                # We allow `ga_inflight` to exceed `inflight_limit` to create a backlog
                # that keeps the GPU fed while CPU decode/FG prep runs.
                if stopping:
                    break
                if pending_fg:
                    try:
                        fg_oldest_wait_s = _oldest_pending_fg_wait_s(time.monotonic())
                    except Exception:
                        fg_oldest_wait_s = 0.0
                    if _continuous_fg_should_start(
                        pending_fg_count=len(pending_fg),
                        ga_credit=int(fg_ga_credit),
                        oldest_wait_s=float(fg_oldest_wait_s),
                        blocked_on_slot=bool(blocked_on_slot_acquire),
                        no_ga_remaining=False,
                        fg_drain_at_end=bool(fg_drain_at_end),
                        aging_trigger_s=float(fg_aging_trigger_s),
                        aging_hard_s=float(fg_aging_hard_s),
                    ):
                        break
                ga_queue_limit_effective = _effective_ga_queue_limit()
                if ga_queue_debug and ga_queue_limit_effective != last_ga_queue_limit_effective:
                    last_ga_queue_limit_effective = int(ga_queue_limit_effective)
                    try:
                        print(
                            "[InFlight][GAQueue] "
                            f"effective={int(ga_queue_limit_effective)} base={int(ga_queue_limit_base)} "
                            f"ga_inflight={len(ga_inflight)} prepared={len(prepared)} pending_fg={len(pending_fg)} "
                            f"fg_prep={len(fg_prep_inflight)} fg_inflight={len(fg_futures)} "
                            f"slot_reserve={int(fg_slot_reserve)} "
                            f"oldest_fg_wait_ms={fg_oldest_wait_s * 1000.0:.0f}"
                        )
                    except Exception:
                        pass

                can_submit_ga = bool(prepared) and len(ga_inflight) < ga_queue_limit_effective

                if can_submit_ga:
                    song = prepared.popleft()
                    # Reserve a per-song GPU timeline slot so GA -> FG can reuse the resident grid
                    # even while other songs are in-flight (avoids clobbering slot 0).
                    if int(getattr(song, "song_slot", 0) or 0) <= 0:
                        try:
                            song.song_slot = int(slot_pool.acquire())
                        except Exception:
                            # No free slots: defer GA submission until FG drains.
                            blocked_on_slot_acquire = True
                            last_slot_block_t = time.monotonic()
                            stage_profiler.record("slot_block", 0.0)
                            prepared.appendleft(song)
                            break
                        try:
                            song.calc_song["_gpu_song_slot"] = int(song.song_slot)
                        except Exception:
                            pass
                    setattr(song, "_ga_submit_t0", time.perf_counter())
                    payload = {
                        "calc_song": song.calc_song,
                        "ref_arrays": song.ref_arrays,
                        "song_slot": int(song.song_slot),
                        "item_stats": song.item_stats,
                        "slot_start": song.slot_start,
                        "slot_count": song.slot_count,
                        "base_fixed_stats_arr": song.base_fixed_stats_arr,
                        "initial_populations": getattr(song, "ga_initial_populations", None),
                        "num_runs": int(song.num_runs),
                        "n_genomes": int(song.n_genomes),
                        "init_heuristic_topk": song.init_heuristic_topk,
                        "init_heuristic_k": int(song.init_heuristic_k),
                        "init_heuristic_copies": int(song.init_heuristic_copies),
                        "db_seed_ids": song.db_seed_ids,
                        "db_seed_prob": float(song.db_seed_prob),
                        "db_seed_copies": int(song.db_seed_copies),
                        "db_seed_mutations": int(song.db_seed_mutations),
                        "n_generations": int(song.gens_per_run),
                        "elite_count": int(song.elite_count),
                        "mutation_rate": float(song.mutation_rate),
                        "immigrant_rate": float(song.immigrant_rate),
                        "tournament_k": int(song.tournament_k),
                        "color_flags": dict(song.color_flags),
                        "cfg_data": dict(song.cfg_data),
                        "ga_seed": song.ga_seed,
                    }
                    try:
                        handle = gpu_client.submit_gpu_native_ga_run(payload)
                    except Exception as exc:
                        # Ensure we don't leak the reserved slot on submission failure.
                        try:
                            _clear_fg_resident_owner(getattr(song, "calc_song", None))
                            slot_pool.release(int(song.song_slot))
                            song.song_slot = 0
                        except Exception:
                            pass
                        payload = build_error_payload(
                            song_name=str(song.song_name),
                            queue_key=str(song.task_key),
                            queue_label=str(song.task_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        bundle_parent = getattr(song, "_bundle_parent_task", None)
                        if bundle_parent is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                        if bundle_parent is not None:
                            _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                        else:
                            completed_songs.add(song.task_key)
                            if memory_resume_tracker:
                                memory_resume_tracker.mark_completed(song.song_name)
                        did_work = True
                        continue

                    song.ga_future = handle.future
                    try:
                        song.ga_initial_populations = None
                    except Exception:
                        pass
                    _register_completion_future(song.ga_future)
                    ga_inflight.append(song)
                    did_work = True
                    _continuous_note_ga_submit()
                    ga_dispatch_count += 1

                    # Prefetch DB loadouts early so FG prep after GA decode doesn't stall
                    # waiting on SQLite reads (keeps the GPU fed during song boundaries).
                    if (
                        (song.manual_force_greats or song.force_greats_finder)
                        and song.use_evo_db
                        and song.db_loadouts_future is None
                        and song.db_loadouts_full is None
                    ):
                        try:
                            prefetch_limit = safe_int(
                                song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
                                FG_CANDIDATE_LIMIT,
                            )
                            song.db_loadouts_future = db_prefetch_executor.submit(
                                _prefetch_db_loadouts_sync,
                                song.db_key,
                                limit=int(prefetch_limit),
                                gears_by_name=song.gears_by_name,
                                minis_by_name=song.minis_by_name,
                            )
                            _register_completion_future(song.db_loadouts_future)
                        except Exception:
                            song.db_loadouts_future = None

                    # Continuous scheduler: cap GA micro-bursts so FG gets frequent dispatch
                    # opportunities instead of waiting for large GA-only phases to complete.
                    if pending_fg and int(ga_dispatch_count) >= int(continuous_ga_dispatch_burst):
                        break
                    continue

                # CPU prep: keep a staging buffer of prepared jobs so the GPU queue
                # doesn't starve if CPU prep briefly falls behind GPU throughput.
                if stopping:
                    break
                if pending_tasks and (len(prepared) + len(prep_inflight) < prep_limit):
                    nxt = pending_tasks.popleft()
                    nxt_bundle_key = _task_key(nxt)
                    if nxt_bundle_key in completed_songs:
                        did_work = True
                        continue
                    logical_nxt, repeat_ctx = _next_logical_task(nxt)
                    nxt_key = _task_key(logical_nxt)
                    try:
                        prep_future = prep_executor.submit(_prepare_song, logical_nxt)
                        _register_completion_future(prep_future)
                        prep_inflight.append((nxt, logical_nxt, prep_future, time.perf_counter()))
                    except Exception as exc:
                        payload = build_error_payload(
                            song_name=str(nxt[1]),
                            queue_key=str(nxt_key),
                            queue_label=str(nxt_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        if repeat_ctx is not None:
                            payload["_suppress_progress"] = True
                        _post(payload)
                        if repeat_ctx is not None:
                            _advance_bundle(nxt, song_name=str(nxt[1]), failed=True)
                        else:
                            completed_songs.add(nxt_key)
                            if memory_resume_tracker:
                                memory_resume_tracker.mark_completed(nxt[1])
                        did_work = True
                        continue
                    did_work = True
                    continue

                break

            # Drain completed GA jobs quickly to free inflight capacity; do the heavier
            # CPU-side decode on a background thread so the GPU queue stays fed.
            for song in list(ga_inflight):
                if song.ga_future is None or not song.ga_future.done():
                    continue
                ga_inflight.remove(song)
                did_work = True

                try:
                    runs_payload = song.ga_future.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    payload = build_error_payload(
                        song_name=str(song.song_name),
                        queue_key=str(song.task_key),
                        queue_label=str(song.task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                    )
                    bundle_parent = getattr(song, "_bundle_parent_task", None)
                    if bundle_parent is not None:
                        payload["_suppress_progress"] = True
                    _post(payload)
                    # GA failed: release the reserved timeline slot for this song.
                    try:
                        _clear_fg_resident_owner(getattr(song, "calc_song", None))
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                    else:
                        completed_songs.add(song.task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                    continue

                t_submit = getattr(song, "_ga_submit_t0", None)
                if t_submit is not None:
                    stage_profiler.record("ga_gpu", time.perf_counter() - float(t_submit), song=song.task_key)
                    setattr(song, "_ga_submit_t0", None)

                song.ga_future = None

                needs_fg_stage = bool(song.manual_force_greats or song.force_greats_finder)
                hold_budget = int(fg_hold_budget or 0)
                keep_slot_for_fg = False
                if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                    held_slots = 0
                    try:
                        for s in decode_inflight:
                            if int(getattr(s, "song_slot", 0) or 0) <= 0:
                                continue
                            if bool(getattr(s, "manual_force_greats", False)) or bool(
                                getattr(s, "force_greats_finder", False)
                            ):
                                held_slots += 1
                    except Exception:
                        pass
                    try:
                        for s in pending_fg:
                            if int(getattr(s, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception:
                        pass
                    try:
                        for fg_song, _fut, _t_submit in fg_futures:
                            if int(getattr(fg_song, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception:
                        pass
                    keep_slot_for_fg = int(held_slots) < int(hold_budget)

                # When the song slot is released after GA, the GA->FG candidate table for that slot may be
                # overwritten by other in-flight songs before FG runs. Mark whether the GA slot remained
                # reserved so FG can safely decide whether to use that fast-path.
                try:
                    if isinstance(song.calc_song, dict):
                        if bool(keep_slot_for_fg):
                            _set_fg_resident_owner(song.calc_song, song_slot=int(song.song_slot), task_key=str(song.task_key))
                        else:
                            _clear_fg_resident_owner(song.calc_song)
                except Exception:
                    pass

                if not keep_slot_for_fg:
                    # Release the song slot immediately after GA completes unless we're keeping it
                    # resident for FG reuse (bounded by `fg_hold_budget` so GA won't deadlock on slots).
                    if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                        stage_profiler.record("fg_hold_drop", 0.0)
                    try:
                        _clear_fg_resident_owner(getattr(song, "calc_song", None))
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                    except Exception:
                        pass
                    try:
                        song.song_slot = 0
                    except Exception:
                        pass
                    try:
                        if isinstance(song.calc_song, dict):
                            song.calc_song.pop("_gpu_song_slot", None)
                    except Exception:
                        pass

                setattr(song, "_decode_submit_t0", time.perf_counter())
                song.decode_future = decode_executor.submit(_decode_ga_payload_sync, song, runs_payload)
                _register_completion_future(song.decode_future)
                decode_inflight.append(song)

            # Finalize decoded GA results (lightweight formatting + enqueue for post/FG).
            for song in list(decode_inflight):
                if song.decode_future is None or not song.decode_future.done():
                    continue
                decode_inflight.remove(song)
                did_work = True

                try:
                    best_data, best_gear, best_minis, ga_candidates = song.decode_future.result()
                except Exception as exc:
                    payload = build_error_payload(
                        song_name=str(song.song_name),
                        queue_key=str(song.task_key),
                        queue_label=str(song.task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                    )
                    bundle_parent = getattr(song, "_bundle_parent_task", None)
                    if bundle_parent is not None:
                        payload["_suppress_progress"] = True
                    _post(payload)
                    # Decode failed: release the reserved timeline slot for this song.
                    try:
                        _clear_fg_resident_owner(getattr(song, "calc_song", None))
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.song_name), failed=True)
                    else:
                        completed_songs.add(song.task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                    continue
                finally:
                    song.decode_future = None

                t_decode = getattr(song, "_decode_submit_t0", None)
                t_hitsim_matrix = getattr(song, "_hitsim_matrix_submit_t0", None)
                if t_decode is not None:
                    stage_profiler.record(
                        "decode",
                        time.perf_counter() - float(t_decode),
                        cpu_seconds=getattr(song, "_cpu_decode_s", None),
                        song=song.task_key,
                    )
                    setattr(song, "_decode_submit_t0", None)
                elif t_hitsim_matrix is not None:
                    stage_profiler.record(
                        "hitsim_matrix",
                        time.perf_counter() - float(t_hitsim_matrix),
                        song=song.task_key,
                    )
                    try:
                        delattr(song, "_hitsim_matrix_submit_t0")
                    except Exception:
                        pass

                song.best_data = best_data
                song.best_gear = best_gear
                song.best_minis = best_minis
                song.ga_candidates = list(ga_candidates or [])
                _attach_hitsim_delta_for_base(song.best_data, song.calc_song, song.ref_arrays)

                if song.manual_force_greats or song.force_greats_finder:
                    pending_fg.append(song)
                    try:
                        if not isinstance(getattr(song, "fg_queued_t0", None), (int, float)):
                            song.fg_queued_t0 = time.monotonic()
                    except Exception:
                        pass
                    if song.fg_prep_future is None:
                        try:
                            setattr(song, "_fg_prep_submit_t0", time.perf_counter())
                            song.fg_prep_future = fg_prep_executor.submit(
                                _prepare_fg_job_sync, song, gpu_client=gpu_client
                            )
                            _register_completion_future(song.fg_prep_future)
                            fg_prep_inflight.append(song)
                        except Exception:
                            song.fg_prep_future = None
                else:
                    # No FG stage for this song: release its reserved timeline slot immediately.
                    try:
                        _clear_fg_resident_owner(getattr(song, "calc_song", None))
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass

                record_info = None
                try:
                    prev_best_score, prev_best_fg = _progress_best_snapshot(song.db_key)
                    record_info = evaluate_record_update(
                        song.best_data or {},
                        {"score": int(prev_best_score)},
                        [],
                        db_best_fg_score=int(prev_best_fg),
                    )
                    if isinstance(record_info, dict) and record_info.get("is_better"):
                        _progress_best_update(song.db_key, best_score=int(record_info.get("score", 0) or 0))
                except Exception:
                    record_info = None
                song.record_info = record_info

                # Backfill base HitSim delta for the deferred-post payload (best_data + GA candidates).
                #
                # Why here?
                # - In native in-flight mode we don't ship `calc_song`/`ref_arrays` across the post-process queue.
                # - TeamBuff tier postprocess intentionally excludes T5, so T5's base rows must already contain
                #   `details_json.hitsim_offset_delta_ms` or the frontend will see nulls for top51.
                # - Compute using the in-process `calc_song` (has the true per-run HitSim seed/timestamps).
                best_data_for_post = song.best_data or {}
                best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
                ga_candidates_post: list[dict] = []
                for cand in song.ga_candidates or []:
                    if not isinstance(cand, dict):
                        continue
                    data0 = cand.get("Data") or {}
                    gear_names, mini_names = materialize_candidate_names(cand, registry=song.registry, mutate=False)
                    ga_candidates_post.append(
                        {
                            "Score": cand.get("Score", 0),
                            "BaseScore": cand.get("BaseScore", cand.get("Score", 0)),
                            "Gear": list(gear_names),
                            "Minis": list(mini_names),
                            # Copy so we don't race with FG prep mutating candidate dicts.
                            "Data": dict(data0) if isinstance(data0, dict) else {},
                            "_fg_priority": cand.get("_fg_priority", 0),
                        }
                    )

                hitsim_meta = song.calc_song.get("metadata") if isinstance(song.calc_song, dict) else None
                hitsim_enabled = False
                hitsim_seed = None
                try:
                    hitsim_enabled = (
                        bool(hitsim_meta and hitsim_meta.get("HumanHitSimApplied"))
                        and str((hitsim_meta or {}).get("HumanHitSimApplyTo", "") or "").strip().upper() == "ALL"
                    )
                except Exception:
                    hitsim_enabled = False
                try:
                    if isinstance(hitsim_meta, dict):
                        hitsim_seed = int((hitsim_meta or {}).get("HumanHitSimSeed", 0) or 0)
                    else:
                        hitsim_seed = None
                except Exception:
                    hitsim_seed = None
                if hitsim_seed is not None and int(hitsim_seed) <= 0:
                    hitsim_seed = None

                delta_cache_by_ff: dict[int, int] = {}
                if hitsim_enabled and isinstance(song.calc_song, dict) and isinstance(song.ref_arrays, dict):
                    try:
                        from gear_optimizer.solver.scoring.force_greats import summarize_hitsim_offset_delta_ms_for_base
                    except Exception:
                        summarize_hitsim_offset_delta_ms_for_base = None

                    if summarize_hitsim_offset_delta_ms_for_base is not None:

                        def _maybe_attach(entry_data: dict) -> None:
                            if not isinstance(entry_data, dict):
                                return
                            if entry_data.get("hitsim_offset_delta_ms") is not None:
                                return
                            stats0 = entry_data.get("Stats")
                            if not isinstance(stats0, dict) or not stats0:
                                return
                            try:
                                ff0 = int(stats0.get("Fever Fill Rate", 0) or 0)
                            except Exception:
                                ff0 = 0
                            delta0 = delta_cache_by_ff.get(int(ff0))
                            if delta0 is None:
                                try:
                                    computed = summarize_hitsim_offset_delta_ms_for_base(
                                        song.calc_song,
                                        {"Stats": stats0},
                                        song.ref_arrays,
                                    )
                                except Exception:
                                    computed = None
                                if computed is not None:
                                    delta0 = int(computed)
                                    delta_cache_by_ff[int(ff0)] = int(delta0)
                            if delta0 is not None:
                                entry_data["hitsim_offset_delta_ms"] = int(delta0)

                        # Best-data backfill
                        _maybe_attach(best_data_post)
                        for cand in ga_candidates_post:
                            _maybe_attach(cand.get("Data") or {})

                _post(
                    {
                        "_deferred_post": True,
                        "_pending_fg_job": bool(song.manual_force_greats or song.force_greats_finder),
                        "song": song.song_name,
                        "_queue_key": song.task_key,
                        "_queue_label": song.task_key,
                        "_ga_seed": song.ga_seed,
                        "db_key": song.db_key,
                        "file_path": song.fp,
                        "difficulty": song.effective_difficulty,
                        "use_evo_db": bool(song.use_evo_db),
                        "cfg_dict": song.cfg_dict,
                        "hitsim_seed": hitsim_seed,
                        # Avoid pickling large song/ref objects across the post-process queue
                        # unless FG debug output explicitly needs them.
                        "ref_arrays": song.ref_arrays if song.fg_debug else None,
                        "calc_song": song.calc_song if song.fg_debug else None,
                        "best_data": best_data_post,
                        "best_gear": _compact_items(best_gear),
                        "best_minis": _compact_items(best_minis),
                        "current_gear": _compact_items(song.current_gear_list),
                        "current_minis": _compact_items(song.current_mini_list),
                        "enable_gear": bool(song.enable_gear),
                        "enable_mini": bool(song.enable_mini),
                        "fg_variants": [],
                        "ga_candidates": ga_candidates_post,
                        "loadout_entries": None,
                        "prev_record": _compact_prev_record(song.prev_record),
                        "attempt_lifetime": int(song.attempt_lifetime or 0),
                        "prev_attempts_first": int(song.prev_attempts_first or 0),
                        "db_best_fg_score": int(song.db_best_fg_score or 0),
                        "meta_primary_color": song.meta_primary_color,
                        "meta_secondary_color": song.meta_secondary_color,
                        "fg_debug": bool(song.fg_debug),
                        "log": "",
                    }
                )

                bundle_parent = getattr(song, "_bundle_parent_task", None)
                if bundle_parent is not None and bool(song.manual_force_greats or song.force_greats_finder):
                    setattr(song, "_bundle_wait_for_fg", True)
                elif bundle_parent is not None:
                    _advance_bundle(
                        bundle_parent,
                        song_name=str(song.song_name),
                        record_info=record_info,
                        failed=False,
                    )
                else:
                    completed_songs.add(song.task_key)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song.song_name)
                    if bundle_completed_cb is not None:
                        try:
                            bundle_completed_cb(song.task_key, completed_songs)
                        except Exception:
                            pass
                    try:
                        record_info = dict(record_info or {})
                        # Prefer the task key so repeats show "(Run i/N)" and don't look like a single song run.
                        record_info.setdefault("song", song.task_key or song.song_name)
                        record_info.setdefault("status", "DONE")
                    except Exception:
                        pass
                    _emit_progress(completed_delta=1, record_info=record_info)

            # Reap completed FG workers (capture errors).
            if fg_futures:
                still_pending: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
                for fg_song, fut, t_submit in list(fg_futures):
                    try:
                        done = fut.done()
                    except Exception:
                        done = False
                    if done:
                        did_work = True
                        bundle_parent = getattr(fg_song, "_bundle_parent_task", None)
                        fg_failed = False
                        try:
                            fut.result()
                        except GpuServiceTimeoutError:
                            raise
                        except Exception:
                            fg_failed = True
                            try:
                                if post_sender is not None and bool(getattr(fg_song, "_bundle_wait_for_fg", False)):
                                    post_sender.send(
                                        {
                                            "_fg_update": True,
                                            "song": fg_song.song_name,
                                            "db_key": fg_song.db_key,
                                            "use_evo_db": bool(fg_song.use_evo_db),
                                            "persist_entries": [],
                                            "file_path": fg_song.fp,
                                            "cfg_dict": fg_song.cfg_dict,
                                        }
                                    )
                            except Exception:
                                pass
                        # Release this song's reserved timeline slot now that FG is complete.
                        try:
                            _clear_fg_resident_owner(getattr(fg_song, "calc_song", None))
                            slot_pool.release(int(getattr(fg_song, "song_slot", 0) or 0))
                            fg_song.song_slot = 0
                        except Exception:
                            pass
                        stage_profiler.record(
                            "fg_run",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(fg_song, "_cpu_fg_run_s", None),
                            song=fg_song.task_key,
                        )
                        if bundle_parent is not None and bool(getattr(fg_song, "_bundle_wait_for_fg", False)):
                            _advance_bundle(
                                bundle_parent,
                                song_name=str(fg_song.song_name),
                                record_info=getattr(fg_song, "record_info", None),
                                failed=bool(fg_failed),
                            )
                            try:
                                delattr(fg_song, "_bundle_wait_for_fg")
                            except Exception:
                                pass
                    else:
                        still_pending.append((fg_song, fut, t_submit))
                fg_futures = still_pending

            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = _oldest_pending_fg_wait_s(float(now))
            except Exception:
                fg_oldest_wait_s = 0.0

            if not pending_fg:
                fg_ga_credit = int(fg_ga_credit_budget)

            no_ga_remaining = (
                (not pending_tasks)
                and (not prepared)
                and (not prep_inflight)
                and (not ga_inflight)
                and (not decode_inflight)
            )

            # If we're not draining FG at end, do not start new FG work once GA has
            # completed the queue; defer remaining FG candidates to DB for later processing.
            if (not fg_drain_at_end) and pending_fg and no_ga_remaining:
                # If any FG work is already running, let it complete (don't submit more).
                if fg_futures:
                    should_start_fg = False
                else:
                    try:
                        print(
                            f"[InFlight][FG] Deferred {len(pending_fg)} pending FG job(s) "
                            "(FG_DrainAtEnd=false). "
                            "Candidates were persisted to DB for later processing."
                        )
                    except Exception:
                        pass

                    # Best-effort: stop tracking FG prep for deferred songs so we can exit
                    # without waiting on CPU prep threads.
                    try:
                        for s in list(fg_prep_inflight):
                            try:
                                s.fg_prep_future = None
                            except Exception:
                                pass
                        fg_prep_inflight.clear()
                    except Exception:
                        pass

                    # Release any reserved timeline slots for deferred FG songs.
                    try:
                        for s in list(pending_fg):
                            try:
                                _clear_fg_resident_owner(getattr(s, "calc_song", None))
                                slot_pool.release(int(getattr(s, "song_slot", 0) or 0))
                                s.song_slot = 0
                            except Exception:
                                continue
                        pending_fg.clear()
                    except Exception:
                        pass
                    break

            should_start_fg = _continuous_fg_should_start(
                pending_fg_count=len(pending_fg),
                ga_credit=int(fg_ga_credit),
                oldest_wait_s=float(fg_oldest_wait_s),
                blocked_on_slot=bool(blocked_on_slot_acquire),
                no_ga_remaining=bool(no_ga_remaining),
                fg_drain_at_end=bool(fg_drain_at_end),
                aging_trigger_s=float(fg_aging_trigger_s),
                aging_hard_s=float(fg_aging_hard_s),
            )
            ga_queue_limit_effective = _effective_ga_queue_limit()

            if should_start_fg:
                if fg_decision_debug:
                    try:
                        reasons: list[str] = []
                        if no_ga_remaining:
                            reasons.append("drain_end")
                        if blocked_on_slot_acquire:
                            reasons.append("slot_pressure")
                        if fg_oldest_wait_s >= float(fg_aging_hard_s) and float(fg_aging_hard_s) > 0.0:
                            reasons.append("aging_hard")
                        elif fg_oldest_wait_s >= float(fg_aging_trigger_s) and float(fg_aging_trigger_s) > 0.0:
                            reasons.append("aging_trigger")
                        if int(fg_ga_credit) <= 0:
                            reasons.append("credit")

                        print(
                            "[InFlight][FGDecision] start "
                            f"reasons={','.join(reasons) or 'unknown'} "
                            f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_inflight={len(fg_futures)} "
                            f"oldest_fg_wait_ms={fg_oldest_wait_s * 1000.0:.0f}"
                        )
                    except Exception:
                        pass

                submit_budget = _continuous_fg_submit_budget(
                    pending_fg_count=len(pending_fg),
                    fg_inflight_count=len(fg_futures),
                    fg_workers=int(fg_workers),
                    fg_batch_max=int(fg_batch_max),
                    no_ga_remaining=bool(no_ga_remaining),
                    fg_drain_at_end=bool(fg_drain_at_end),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    aging_trigger_s=float(fg_aging_trigger_s),
                    aging_hard_s=float(fg_aging_hard_s),
                    ga_inflight_count=len(ga_inflight),
                    ga_queue_limit=int(ga_queue_limit_effective),
                    adaptive_submit=bool(fg_adaptive_submit_enabled),
                    adaptive_max_burst=int(fg_adaptive_submit_max_burst),
                )

                if submit_budget > 0 and len(fg_futures) < fg_workers:
                    # Process pending FG jobs (up to worker + batch budget).
                    while submit_budget > 0 and len(fg_futures) < fg_workers and pending_fg:
                        allow_not_ready = bool(blocked_on_slot_acquire)
                        fg_song = _pop_next_fg(allow_not_ready=allow_not_ready)
                        if fg_song is None:
                            break
                        if int(getattr(fg_song, "song_slot", 0) or 0) <= 0:
                            try:
                                fg_song.song_slot = int(slot_pool.acquire())
                            except Exception:
                                # No free slots: put the song back and defer FG submission
                                # until GA releases slots. Without this, the song would be
                                # dropped from FG processing entirely (it was removed from
                                # pending_fg by _pop_next_fg but never submitted).
                                pending_fg.appendleft(fg_song)
                                break
                            try:
                                if isinstance(fg_song.calc_song, dict):
                                    fg_song.calc_song["_gpu_song_slot"] = int(fg_song.song_slot)
                            except Exception:
                                pass
                        if fg_submit_debug:
                            try:
                                print(
                                    "[InFlight][FGSubmit] "
                                    f"song={fg_song.task_key} "
                                    f"pending_fg={len(pending_fg)} fg_inflight={len(fg_futures)}"
                                )
                            except Exception:
                                pass
                        try:
                            fg_song.fg_queued_t0 = None
                        except Exception:
                            pass
                        t_submit = time.perf_counter()
                        fg_future = fg_executor.submit(
                            _run_fg_job_sync,
                            fg_song,
                            gpu_client=gpu_client,
                            post_sender=post_sender,
                            progress_cb=progress_cb,
                            progress_best=progress_best,
                            progress_best_lock=progress_best_lock,
                        )
                        _register_completion_future(fg_future)
                        fg_futures.append(
                            (
                                fg_song,
                                fg_future,
                                t_submit,
                            )
                        )
                        _continuous_note_fg_submit()
                        did_work = True
                        submit_budget -= 1

            _emit_active_runtime_song()

            if did_work:
                last_progress = time.monotonic()

            # Avoid tight spin.
            if not did_work:
                if heartbeat_sec > 0.0 and (time.monotonic() - last_heartbeat) >= heartbeat_sec:
                    last_heartbeat = time.monotonic()
                    oldest_ga_s = None
                    try:
                        now = time.perf_counter()
                        t0s = [getattr(s, "_ga_submit_t0", None) for s in ga_inflight]
                        t0s = [t for t in t0s if t is not None]
                        if t0s:
                            oldest_ga_s = max(0.0, now - float(min(t0s)))
                    except Exception:
                        oldest_ga_s = None

                    try:
                        msg = (
                            "[InFlight][HB] "
                            f"idle={time.monotonic() - last_progress:.1f}s "
                            f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)}"
                        )
                        if blocked_on_slot_acquire:
                            msg += " blocked_slots=1"
                        if oldest_ga_s is not None:
                            msg += f" oldest_ga={oldest_ga_s:.1f}s"
                        print(msg)
                    except Exception:
                        pass
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="heartbeat",
                        metrics={
                            "idle_sec": float(time.monotonic() - last_progress),
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_futures": int(len(fg_futures)),
                            "blocked_slots": int(bool(blocked_on_slot_acquire)),
                            "oldest_ga_sec": float(oldest_ga_s) if oldest_ga_s is not None else -1.0,
                        },
                    )

                no_active_work = (
                    (not ga_inflight)
                    and (not decode_inflight)
                    and (not prep_inflight)
                    and (not fg_prep_inflight)
                    and (not fg_futures)
                )
                if (
                    no_active_work
                    and (pending_tasks or prepared or pending_fg or fg_futures)
                    and (time.monotonic() - last_stall_report) >= 10.0
                    and _truthy(os.environ.get("INFLIGHT_STALL_DEBUG", "0"))
                ):
                    last_stall_report = time.monotonic()
                    try:
                        fg_done = sum(1 for _song, fut, _t0 in fg_futures if fut.done())
                        fg_inflight = len(fg_futures)
                    except Exception:
                        fg_done = None
                        fg_inflight = None
                    print(
                        "[InFlight][STALL] "
                        f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                        f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                        f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} "
                        f"fg_inflight={fg_inflight} fg_done={fg_done}"
                    )
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="stall",
                        metrics={
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_inflight": int(fg_inflight) if fg_inflight is not None else -1,
                            "fg_done": int(fg_done) if fg_done is not None else -1,
                        },
                    )

                if _has_waitable_futures():
                    t_wait = time.perf_counter()
                    has_gpu = bool(ga_inflight) or bool(fg_futures)
                    has_cpu = bool(prep_inflight) or bool(decode_inflight) or bool(fg_prep_inflight)
                    signaled = False
                    try:
                        signaled = bool(completion_event.is_set())
                        if signaled:
                            completion_event.clear()
                    except Exception:
                        signaled = False
                    if not signaled:
                        wait_timeout_s = float(event_wait_timeout_s)
                        if has_gpu and float(event_wait_gpu_cap_s) > 0.0:
                            wait_timeout_s = min(float(wait_timeout_s), float(event_wait_gpu_cap_s))
                        signaled = _wait_for_completion_event(
                            completion_event,
                            timeout_s=float(wait_timeout_s),
                            short_spin_s=float(event_wait_short_spin_s),
                        )
                        if signaled:
                            try:
                                completion_event.clear()
                            except Exception:
                                pass
                    dt_wait = time.perf_counter() - t_wait
                    stage_profiler.record("main_wait", dt_wait)
                    if (not has_gpu) and has_cpu:
                        stage_profiler.record("underfed_wait", dt_wait)
                else:
                    t_sleep = time.perf_counter()
                    time.sleep(0.001)
                    stage_profiler.record("main_sleep", time.perf_counter() - t_sleep)

    except Exception as exc:
        _log_abort(exc)
        raise
    finally:
        try:
            stage_profiler.emit()
        except Exception:
            pass
        shutdown_debug = _truthy(os.environ.get("INFLIGHT_SHUTDOWN_DEBUG", "0"))
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] fg_executor.shutdown")
            fg_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] decode_executor.shutdown")
            decode_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] db_prefetch_executor.shutdown")
            db_prefetch_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] fg_prep_executor.shutdown")
            fg_prep_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] prep_executor.shutdown")
            prep_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if post_sender is not None:
                if shutdown_debug:
                    print("[InFlight][SHUTDOWN] post_sender.close")
                post_sender.close(timeout=10.0)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] gpu_client.close")
            gpu_client.close(timeout=2.0)
        except Exception:
            pass
        try:
            if gpu_executor.is_running:
                if shutdown_debug:
                    print("[InFlight][SHUTDOWN] gpu_executor.stop")
                gpu_executor.stop()
        except Exception:
            pass


# NOTE: `_decode_ga_payload_sync`, `_prefetch_db_loadouts_sync`, `_prepare_fg_job_sync` are imported
# from `gear_optimizer/solver/native_inflight_stages.py` to keep the orchestrator loop leaner.


def _run_fg_job_sync(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: Optional[_PostSender] = None,
    progress_cb=None,
    progress_best: dict[str, tuple[int, int]] | None = None,
    progress_best_lock: Any | None = None,
) -> None:
    cpu_t0 = _thread_cpu_time_s()
    if song.fg_prep_future is not None:
        try:
            song.fg_prep_future.result()
        except Exception:
            pass
        finally:
            song.fg_prep_future = None

    if song.loadout_entries is None:
        _prepare_fg_job_sync(song, gpu_client=gpu_client)

    # Late non-blocking DB prefetch consume:
    # - If FG prep skipped DB rows because prefetch was still in-flight, harvest now if ready.
    # - Never block FG worker threads on SQLite here.
    if song.db_loadouts_full is None and song.db_loadouts_future is not None:
        fut = song.db_loadouts_future
        try:
            if fut.done():
                try:
                    db_rows = fut.result(timeout=0)
                    if isinstance(db_rows, list):
                        song.db_loadouts_full = db_rows
                except Exception:
                    song.db_loadouts_full = None
            else:
                # Best effort: avoid keeping stale prefetch work around if FG is already running.
                try:
                    fut.cancel()
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            song.db_loadouts_future = None

    build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)
    hitsim_regime_groups = list(getattr(song, "_hitsim_fg_regime_groups", []) or [])

    # If FG prep built GA-only entries while DB prefetch was pending, merge DB rows now
    # without rebuilding the full GA union.
    if song.db_loadouts_full is not None and not _loadout_entries_have_db_source(song.loadout_entries):
        if not isinstance(song.loadout_entries, dict):
            song.loadout_entries = {}
        merge_db_loadouts_into_entries(song.loadout_entries, song.db_loadouts_full)

    # Always-on (ForceGreatsFinder): evaluate a capped set of 1–2-position combos around
    # GA seeds to improve FG coverage when deeper GA runs crowd out fever-heavy variants.
    try:
        combo_enabled = _truthy(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1"))

        boosted = None
        if (not hitsim_regime_groups) and song.force_greats_finder and song.ga_candidates and combo_enabled:
            job = getattr(song, "fg_combo_job", None)
            if isinstance(job, dict):
                boosted = finalize_fg_combo_booster_candidates_job(job)
                song.fg_combo_job = None
            if not boosted:
                boosted = build_fg_combo_booster_candidates(
                    existing_candidates=list(song.ga_candidates or []),
                    registry=song.registry,
                    base_stats_fixed=song.fixed_stats,
                    cfg_data=song.cfg_data,
                    calc_song=song.calc_song,
                    ref_arrays=song.ref_arrays,
                    primary_color=str(song.meta_primary_color or ""),
                    secondary_color=str(song.meta_secondary_color or ""),
                    song_slot=int(song.song_slot or 0),
                    gpu_client=gpu_client,
                )

            if boosted:
                song.ga_candidates = select_fg_candidates(
                    list(song.ga_candidates or []) + list(boosted),
                    limit=int(song.fg_candidate_limit or 0),
                    primary_color=str(song.meta_primary_color or ""),
                    secondary_color=str(song.meta_secondary_color or ""),
                )
                hydrate_fg_candidate_stats(
                    song.ga_candidates,
                    base_stats_fixed=song.fixed_stats,
                    selected_color=str(song.cfg_data.get("selected_color", "") or ""),
                    cfg_data=song.cfg_data,
                )
                if not bool(getattr(song, "fg_direct_ga_candidates", False)):
                    if not isinstance(song.loadout_entries, dict):
                        song.loadout_entries = {}
                    if song.db_loadouts_full is not None and not _loadout_entries_have_db_source(song.loadout_entries):
                        merge_db_loadouts_into_entries(song.loadout_entries, song.db_loadouts_full)
                    refresh_ga_candidate_entries(song.loadout_entries, song.ga_candidates, build_details)
    except Exception:
        pass

    fg_variants = process_force_greats(
        song.loadout_entries or {},
        bool(song.manual_force_greats),
        bool(song.force_greats_finder),
        song.force_greats_config,
        song.calc_song,
        song.ref_arrays,
        song.meta_primary_color,
        build_details,
        use_gpu=True,
        fg_search_radius=song.fg_search_radius,
        perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
        gpu_client=gpu_client,
        ga_candidates=song.ga_candidates if (bool(getattr(song, "fg_direct_ga_candidates", False)) and not hitsim_regime_groups) else None,
        ga_registry=song.registry if bool(getattr(song, "fg_direct_ga_candidates", False)) else None,
        hitsim_regime_groups=hitsim_regime_groups if hitsim_regime_groups else None,
    )

    song.fg_variants = list(fg_variants or [])
    _attach_hitsim_delta_for_fg_variant(song.fg_variants, song.calc_song, song.ref_arrays)
    try:
        setattr(song, "_cpu_fg_run_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass

    if progress_cb is not None:
        fg_record_info = None
        try:
            prev_best_score = 0
            prev_best_fg = 0
            try:
                prev_best_score = safe_int((song.prev_record or {}).get("score", 0), 0)
            except Exception:
                prev_best_score = 0
            try:
                prev_best_fg = safe_int(getattr(song, "db_best_fg_score", 0), 0)
            except Exception:
                prev_best_fg = 0

            key = str(getattr(song, "db_key", "") or "").strip()
            if progress_best is not None and progress_best_lock is not None and key:
                try:
                    with progress_best_lock:
                        best_pair = progress_best.get(key)
                    if isinstance(best_pair, tuple) and len(best_pair) == 2:
                        prev_best_score = safe_int(best_pair[0], prev_best_score)
                        prev_best_fg = safe_int(best_pair[1], prev_best_fg)
                except Exception:
                    pass

            fg_record_info = evaluate_record_update(
                song.best_data or {},
                {"score": int(prev_best_score)},
                song.fg_variants or [],
                db_best_fg_score=int(prev_best_fg),
            )
        except Exception:
            fg_record_info = None
        if isinstance(fg_record_info, dict):
            fg_record_info = dict(fg_record_info)
            # Only count FG improvements in this stage (independent of base GA updates).
            fg_record_info["record_update"] = bool(fg_record_info.get("is_fg_better"))
            if fg_record_info.get("is_fg_better") and progress_best is not None and progress_best_lock is not None:
                try:
                    best_fg_new = safe_int(fg_record_info.get("best_fg_score_run", 0), 0)
                except Exception:
                    best_fg_new = 0
                if best_fg_new > 0:
                    key = str(getattr(song, "db_key", "") or "").strip()
                    if key:
                        try:
                            with progress_best_lock:
                                score0, fg0 = progress_best.get(key, (int(prev_best_score), int(prev_best_fg)))
                                if int(best_fg_new) > int(fg0):
                                    progress_best[key] = (int(score0), int(best_fg_new))
                        except Exception:
                            pass
            try:
                progress_cb(completed_delta=0, failed_delta=0, record_info=fg_record_info)
            except Exception:
                pass

    if post_sender is not None:
        post_sender.send(
            {
                "_fg_update": True,
                "song": song.song_name,
                "db_key": song.db_key,
                "use_evo_db": bool(song.use_evo_db),
                "persist_entries": _build_fg_persist_entries(song),
                # Allow downstream post-process / async DB hooks (e.g., TeamBuff tier leaderboards)
                # to run without requiring ForceGreatsDebug (which ships large objects).
                "file_path": song.fp,
                "cfg_dict": song.cfg_dict,
            }
        )


def _build_fg_persist_entries(song: _NativeSong) -> list[dict]:
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value) if value is not None else int(default)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                return int(default)

    entries: list[dict] = []
    loadout_entries = song.loadout_entries if isinstance(song.loadout_entries, dict) else {}
    loadout_hash_index: dict[str, dict] = {}
    if loadout_entries:
        for loadout_key, entry in loadout_entries.items():
            if isinstance(entry, dict):
                loadout_hash_index.setdefault(str(loadout_key), entry)
            try:
                loadout_hash = entry_loadout_hash(entry)
            except Exception:
                loadout_hash = None
            if not loadout_hash or not isinstance(entry, dict):
                continue
            loadout_hash_index.setdefault(str(loadout_hash), entry)

    for v in song.fg_variants or []:
        if not isinstance(v, dict):
            continue
        is_ga = bool(v.get("_is_ga"))
        base_score = _safe_int(v.get("base_score", v.get("score", 0)), 0)
        fg_score = _safe_int(v.get("fg_score", 0), 0)
        gear_names = _compact_items(v.get("gear") or [])
        mini_names = _compact_items(v.get("minis") or [])
        data = v.get("data") or {}
        base_entry = None
        if (not gear_names and not mini_names) and isinstance(v.get("_entry_ref"), dict):
            try:
                gear_names, mini_names = materialize_entry_names(v.get("_entry_ref"), mutate=True)
            except Exception:
                gear_names, mini_names = [], []
        if gear_names or mini_names:
            try:
                from gear_optimizer.data.database import get_loadout_hash as _get_loadout_hash

                candidate = loadout_hash_index.get(str(_get_loadout_hash(gear_names, mini_names)))
                if isinstance(candidate, dict):
                    base_entry = candidate
            except Exception:
                base_entry = None

        if isinstance(base_entry, dict):
            entry_base_score = _safe_int(
                base_entry.get("base_score"),
                _safe_int(base_entry.get("score", 0), base_score),
            )
            if entry_base_score > 0:
                base_score = entry_base_score

        details_obj = base_entry.get("details") if isinstance(base_entry, dict) else None
        if isinstance(details_obj, dict) and details_obj:
            # Keep base payload consistent with base score on deferred FG updates.
            details = dict(details_obj)
        else:
            stats_obj = data.get("Stats", {})
            if not stats_obj:
                try:
                    from gear_optimizer.helpers.song_helpers.force_greats.result_application import (
                        materialize_stats_from_payload,
                    )

                    stats_obj = materialize_stats_from_payload(data, mutate_payload=True) or {}
                except Exception:
                    stats_obj = stats_obj or {}

            details = {
                "FT": data.get("FT", 0),
                "FF": data.get("FF", 0),
                "GemCounts": data.get("GemCounts", {}),
                "Stats": stats_obj or {},
                "SelectedElement": get_selected_element(data, ""),
                "PrimaryColor": song.meta_primary_color,
                "SecondaryColor": song.meta_secondary_color,
                "Difficulty": song.effective_difficulty,
                "ForceGreats": data.get("ForceGreats", {}),
            }

        force_obj = None
        try:
            fg_meta = (data.get("ForceGreats") or {}) if isinstance(data, dict) else {}
            cfg_obj = fg_meta.get("config") if isinstance(fg_meta, dict) else None
            if cfg_obj and isinstance(cfg_obj, dict) and sum(int(x or 0) for x in cfg_obj.values()) > 0:
                force_obj = dict(data) if isinstance(data, dict) else None
        except Exception:
            force_obj = None
        entries.append(
            {
                "score": int(base_score),
                "fg_score": int(fg_score),
                "gear": gear_names,
                "minis": mini_names,
                "details": details,
                "force": force_obj,
                "_is_ga": bool(is_ga),
            }
        )
    return entries
