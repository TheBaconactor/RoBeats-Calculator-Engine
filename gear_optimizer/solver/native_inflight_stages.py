from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT, TOTAL_ROWS
from gear_optimizer.core.parsing import truthy
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_caches import get_cached_chart_scorer
from gear_optimizer.helpers.song_helpers.database_context import resolve_database_baseline_team_buff
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.data.song_io import clone_calc_song

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.analytical_fg import create_chart_scorer_from_calc_song
from gear_optimizer.solver.fever_timeline import get_song_timeline_grid
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver import native_inflight_fg_db_cache as _fg_db_cache
from gear_optimizer.solver.native_inflight_timing import thread_cpu_time_s
from gear_optimizer.solver.native_inflight_types import _NativeSong
from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload

from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)

_FG_JIT_WARMED = False
_FG_FINDER_RUNTIME_WARMED = False
_FG_JIT_WARM_LOCK = threading.Lock()
_FG_FINDER_RUNTIME_WARM_LOCK = threading.Lock()
_FG_DB_LOADOUTS_CACHE = _fg_db_cache._FG_DB_LOADOUTS_CACHE
_FG_DB_LOADOUTS_CACHE_LOCK = _fg_db_cache._FG_DB_LOADOUTS_CACHE_LOCK
_fg_db_cache_put = _fg_db_cache.fg_db_cache_put
_prefetch_db_loadouts_sync = _fg_db_cache.prefetch_db_loadouts_sync
_FG_RUNTIME_CALC_SONG_KEYS = ("_gpu_song_slot",)


def _truthy(raw: Any) -> bool:
    return truthy(raw)


def _sync_fg_runtime_calc_song_keys(source_calc_song: Any, target_calc_song: Any) -> None:
    if not isinstance(source_calc_song, dict) or not isinstance(target_calc_song, dict):
        return
    for key in _FG_RUNTIME_CALC_SONG_KEYS:
        if key in source_calc_song:
            target_calc_song[key] = source_calc_song.get(key)
        else:
            target_calc_song.pop(key, None)


def resolve_active_fg_calc_song(song: _NativeSong) -> dict | None:
    calc_song = getattr(song.gpu_inputs, "calc_song", None)
    if not isinstance(calc_song, dict):
        return None

    runtime = getattr(song, 'runtime', song)
    fg_state = getattr(runtime, "fg", None)
    fg_calc_song = getattr(fg_state, "fg_calc_song", None)
    if not isinstance(fg_calc_song, dict):
        try:
            fg_calc_song = clone_calc_song(calc_song)
        except Exception as e:
            logger.debug(f"native_inflight_stages:resolve_active_fg_calc_song: {e}")
            fg_calc_song = {
                "metadata": dict(calc_song.get("metadata", {}) or {}),
                "song_data": dict(calc_song.get("song_data", {}) or {}),
            }
    try:
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        apply_timing_envelope(fg_calc_song)
    except Exception as e:
        logger.debug(f"native_inflight_stages:resolve_active_fg_calc_song: {e}")
        return calc_song

    _sync_fg_runtime_calc_song_keys(calc_song, fg_calc_song)
    try:
        if fg_state is not None:
            fg_state.fg_calc_song = fg_calc_song
    except AttributeError:
        pass
    return fg_calc_song


def _maybe_prewarm_fg_chart_scorer(song: _NativeSong) -> None:
    """
    Precompute the expensive per-song AnalyticalFGScorer during FG prep.

    This moves one-time per-song CPU work out of the FG dispatch pre-first-submit window so
    the GPU stays fed when FG work exists.

    Safe-by-default:
    - Only runs for GPU finder when chart prewarm is explicitly enabled.
    - Uses the shared LRU cache, so the later dispatch sees a cheap cache hit.
    """
    try:
        # Prewarming can be expensive on some songs; keep it opt-in so FG prep
        # doesn't stall GA->FG readiness by default.
        if not _truthy(env_get("INFLIGHT_FG_CHART_PREWARM", "0")):
            return
        if not bool(getattr(song.gpu_inputs, "force_greats_finder", False)):
            return
        calc_song = resolve_active_fg_calc_song(song)
        ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return
        if bool(getattr(song.runtime.prep, "fg_chart_scorer_prewarmed", False)):
            return

        get_cached_chart_scorer(calc_song, ref_arrays, create_chart_scorer_from_calc_song)
        song.runtime.prep.fg_chart_scorer_prewarmed = True
    except Exception as e:
        logger.debug(f"native_inflight_stages:_maybe_prewarm_fg_chart_scorer: {e}")
        return


def _cfg_section_ci(cfg_dict: dict, name: str) -> dict:
    if not isinstance(cfg_dict, dict):
        return {}
    if name in cfg_dict and isinstance(cfg_dict.get(name), dict):
        return cfg_dict.get(name) or {}
    target = str(name).lower()
    for key, value in cfg_dict.items():
        if str(key).lower() == target and isinstance(value, dict):
            return value
    return {}


def _cfg_value_ci(section: dict, key: str, default: object = None) -> object:
    if not isinstance(section, dict):
        return default
    if key in section:
        return section.get(key, default)
    target = str(key).lower()
    for cur_key, cur_value in section.items():
        if str(cur_key).lower() == target:
            return cur_value
    return default


class _InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}
        self._allow_prefixes = self._parse_prefixes(env_get("INFLIGHT_STAGE_PROFILE_PREFIX", ""))
        if _truthy(env_get("INFLIGHT_STAGE_PROFILE_FG_ONLY", "0")) and not self._allow_prefixes:
            # Convenience mode: only record FG-related stages (and the "underfed" wait marker that indicates
            # CPU-side bubbles while no GPU work is in flight).
            self._allow_prefixes = ("fg_", "underfed_wait")

    @staticmethod
    def _parse_prefixes(raw: Any) -> tuple[str, ...]:
        prefixes: list[str] = []
        for part in str(raw or "").split(","):
            part = str(part).strip()
            if part:
                prefixes.append(part)
        return tuple(prefixes)

    def record(self, stage: str, seconds: float, *, cpu_seconds: float | None = None, song: str | None = None) -> None:
        if not self.enabled:
            return
        allow = self._allow_prefixes
        if allow and not any(str(stage).startswith(p) for p in allow):
            return
        try:
            seconds = float(seconds)
        except (ValueError, TypeError):
            return
        if seconds < 0:
            return

        if cpu_seconds is not None:
            try:
                cpu_seconds = float(cpu_seconds)
            except (ValueError, TypeError):
                cpu_seconds = None
            if cpu_seconds is not None and cpu_seconds < 0:
                cpu_seconds = None

        entry = self._stage.get(stage)
        if entry is None:
            entry = {
                "count": 0,
                "total_s": 0.0,
                "max_s": 0.0,
                "samples_s": [],
                "cpu_total_s": 0.0,
                "cpu_max_s": 0.0,
                "cpu_samples_s": [],
            }
            self._stage[stage] = entry
        entry["count"] = int(entry["count"]) + 1
        entry["total_s"] = float(entry["total_s"]) + seconds
        entry["max_s"] = max(float(entry["max_s"]), seconds)
        try:
            entry["samples_s"].append(seconds)
        except (KeyError, TypeError, AttributeError):
            pass

        if cpu_seconds is not None:
            entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + float(cpu_seconds)
            entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), float(cpu_seconds))
            try:
                entry["cpu_samples_s"].append(float(cpu_seconds))
            except (KeyError, TypeError, AttributeError):
                pass

        if song:
            per_song = self._song.get(song)
            if per_song is None:
                per_song = {}
                self._song[song] = per_song
            per_song[stage] = float(per_song.get(stage, 0.0)) + seconds
            if cpu_seconds is not None:
                per_song[f"{stage}_cpu"] = float(per_song.get(f"{stage}_cpu", 0.0)) + float(cpu_seconds)

    @staticmethod
    def _quantile(samples: list[float], p: float) -> float:
        if not samples:
            return 0.0
        xs = sorted(float(x) for x in samples)
        n = len(xs)
        if n == 1:
            return xs[0]
        idx = int(round(float(p) * (n - 1)))
        idx = max(0, min(n - 1, idx))
        return xs[idx]

    def summary(self) -> dict[str, Any]:
        if not self.enabled:
            return {}
        total_wall = time.perf_counter() - self._t0
        stages: dict[str, Any] = {}
        for name, entry in self._stage.items():
            samples = entry.get("samples_s") or []
            cpu_samples = entry.get("cpu_samples_s") or []
            stages[name] = {
                "count": int(entry.get("count", 0) or 0),
                "total_s": float(entry.get("total_s", 0.0) or 0.0),
                "max_s": float(entry.get("max_s", 0.0) or 0.0),
                "p50_s": self._quantile(samples, 0.50),
                "p95_s": self._quantile(samples, 0.95),
                "cpu_total_s": float(entry.get("cpu_total_s", 0.0) or 0.0),
                "cpu_max_s": float(entry.get("cpu_max_s", 0.0) or 0.0),
                "cpu_p50_s": self._quantile(cpu_samples, 0.50),
                "cpu_p95_s": self._quantile(cpu_samples, 0.95),
            }
        return {"total_wall_s": float(total_wall), "stages": stages, "songs": self._song}

    def emit(self) -> None:
        if not self.enabled:
            return
        summary = self.summary()
        stages = summary.get("stages") or {}
        ranked = sorted(stages.items(), key=lambda kv: float(kv[1].get("total_s", 0.0) or 0.0), reverse=True)
        logger.debug("[InFlight][StageProfile] total_wall_s=%.3f", float(summary.get("total_wall_s", 0.0) or 0.0))
        for name, info in ranked[:10]:
            logger.debug(
                "[InFlight][StageProfile] %-12s total=%8.3fs cpu=%8.3fs p50=%6.3fs p95=%6.3fs max=%6.3fs n=%s",
                name,
                float(info.get("total_s", 0.0) or 0.0),
                float(info.get("cpu_total_s", 0.0) or 0.0),
                float(info.get("p50_s", 0.0) or 0.0),
                float(info.get("p95_s", 0.0) or 0.0),
                float(info.get("max_s", 0.0) or 0.0),
                int(info.get("count", 0) or 0),
            )

        ranked_cpu = sorted(stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        if ranked_cpu:
            logger.debug("[InFlight][CpuProfile] top_cpu_s")
            for name, info in ranked_cpu[:10]:
                cpu_total = float(info.get("cpu_total_s", 0.0) or 0.0)
                if cpu_total <= 0.0:
                    continue
                logger.debug(
                    "[InFlight][CpuProfile] %-12s cpu_total=%8.3fs p50=%6.3fs p95=%6.3fs max=%6.3fs n=%s",
                    name,
                    cpu_total,
                    float(info.get("cpu_p50_s", 0.0) or 0.0),
                    float(info.get("cpu_p95_s", 0.0) or 0.0),
                    float(info.get("cpu_max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )

        out_path = str(self.out_path or "").strip()
        if not out_path:
            return
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except (OSError, IOError):
            pass
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, sort_keys=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass


def _warmup_fg_jit(calc_song: dict, ref_arrays: dict) -> None:
    global _FG_JIT_WARMED
    if _FG_JIT_WARMED:
        return
    if not calc_song or not ref_arrays:
        return
    with _FG_JIT_WARM_LOCK:
        if _FG_JIT_WARMED:
            return
        try:
            fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays, prefer_grid=True)
        except Exception as e:
            logger.debug(f"native_inflight_stages:_warmup_fg_jit: {e}")
        try:
            grid = get_song_timeline_grid(calc_song, ref_arrays)
            grid.get_timeline(0, int(TOTAL_ROWS))
            grid.to_gpu_arrays_minimal()
        except Exception as e:
            logger.debug(f"native_inflight_stages:_warmup_fg_jit: {e}")
        _FG_JIT_WARMED = True


def _prewarm_fg_baseline_point(calc_song: dict, ref_arrays: dict) -> None:
    if not calc_song or not ref_arrays:
        return
    try:
        fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays, prefer_grid=False)
    except Exception as e:
        logger.debug(f"native_inflight_stages:_prewarm_fg_baseline_point: {e}")


def _prewarm_timeline_frontier_payload(calc_song: dict, ref_arrays: dict) -> None:
    if not calc_song or not ref_arrays:
        return
    try:
        from gear_optimizer.solver.taichi_gem.api.timeline import prewarm_timeline_frontier_payload

        prewarm_timeline_frontier_payload(calc_song, ref_arrays)
    except Exception as e:
        logger.debug(f"native_inflight_stages:_prewarm_timeline_frontier_payload: {e}")


def run_cpu_prewarm_for_song(song: _NativeSong) -> None:
    calc_song = getattr(song.runtime.fg, "fg_calc_song", None) or getattr(song.gpu_inputs, "calc_song", None)
    ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict) or not ref_arrays:
        return

    _prewarm_timeline_frontier_payload(calc_song, ref_arrays)

    if bool(getattr(song.gpu_inputs, "force_greats_finder", False)):
        _prewarm_fg_baseline_point(calc_song, ref_arrays)


def _warmup_fg_finder_runtime(
    calc_song: dict, ref_arrays: dict, *, gpu_client: Optional[GpuServiceClient] = None
) -> None:
    global _FG_FINDER_RUNTIME_WARMED
    if _FG_FINDER_RUNTIME_WARMED:
        return
    if not calc_song or not ref_arrays:
        return
    with _FG_FINDER_RUNTIME_WARM_LOCK:
        if _FG_FINDER_RUNTIME_WARMED:
            return
        try:
            from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_async import (
                plan_fg_async_threshold_flush,
                resolve_fg_async_batching_settings,
                warmup_force_greats_finder_runtime_imports,
            )

            warmup_force_greats_finder_runtime_imports()

            _ = (
                plan_fg_async_threshold_flush,
                resolve_fg_async_batching_settings,
                warmup_force_greats_finder_runtime_imports,
            )
            song_slot = 0
            try:
                if isinstance(calc_song, dict):
                    song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
            except (ValueError, TypeError, KeyError):
                song_slot = 0
            resolve_fg_async_batching_settings(
                gpu_client=gpu_client,
                song_slot=int(song_slot),
                perf=False,
            )
        except Exception as e:
            logger.debug(f"native_inflight_stages:_warmup_fg_finder_runtime: {e}")
            return
        _FG_FINDER_RUNTIME_WARMED = True


def read_fg_group_meta_prime_settings() -> tuple[int, bool, int]:
    prime_group_meta_limit = 0
    prime_group_meta_limit_explicit = False
    try:
        raw = env_get("INFLIGHT_FG_GROUP_META_PRIME_LIMIT")
        if raw is not None and str(raw).strip() != "":
            prime_group_meta_limit = int(raw)
            prime_group_meta_limit_explicit = True
    except (ValueError, TypeError):
        prime_group_meta_limit = 0
        prime_group_meta_limit_explicit = False

    return (
        max(0, min(int(prime_group_meta_limit), 512)),
        bool(prime_group_meta_limit_explicit),
        0,
    )


def _default_fg_group_meta_prime_limit(max_candidates: int) -> int:
    try:
        raw = env_get("INFLIGHT_FG_GROUP_META_AUTO_PRIME_CANDIDATE_LIMIT")
        if raw is not None and str(raw).strip() != "":
            return max(0, min(int(raw), int(max_candidates), 512))
    except (ValueError, TypeError):
        pass
    return max(0, min(8, int(max_candidates), 512))


def collect_fg_group_meta_payload(song: _NativeSong, *, limit: int, start_index: int = 0) -> dict[int, dict]:
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return {}
    calc_song = resolve_active_fg_calc_song(song)
    if not isinstance(calc_song, dict) or not calc_song:
        return {}

    start_i = max(0, int(start_index))
    if start_i >= len(ga_candidates):
        return {}
    limit_i = int(limit)
    if limit_i <= 0:
        stop_i = int(len(ga_candidates))
    else:
        stop_i = int(start_i + limit_i)
    stop_i = max(start_i, min(int(stop_i), int(len(ga_candidates)), 512))
    if stop_i <= start_i:
        return {}

    ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
    if not isinstance(ref_arrays, dict):
        ref_arrays = {}

    payload: dict[int, dict] = {}
    for idx, candidate in enumerate(list(ga_candidates[start_i:stop_i]), start=start_i):
        if not isinstance(candidate, dict):
            continue
        data = candidate.get("Data")
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("_fg_group_meta"), dict):
            continue
        base_stats = data.get("BaseStats")
        if not isinstance(base_stats, dict) or not base_stats:
            continue
        try:
            fg_group_meta = build_fg_group_meta(
                base_stats=base_stats,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                selected_element=str(data.get("Selected Element", "") or ""),
                center_ft=int(data.get("FT", 0) or 0),
                center_ff=int(data.get("FF", 0) or 0),
                primary_color=str(getattr(song.gpu_inputs, "meta_primary_color", "") or ""),
                secondary_color=str(getattr(song.gpu_inputs, "meta_secondary_color", "") or ""),
                run_idx=data.get("_ga_gpu_run_idx"),
                row_idx=data.get("_ga_gpu_row_idx"),
                prefer_grid=False,
            )
        except Exception as e:
            logger.debug(f"native_inflight_stages:collect_fg_group_meta_payload: {e}")
            continue
        if isinstance(fg_group_meta, dict):
            payload[int(idx)] = fg_group_meta

    return payload


def apply_fg_group_meta_payload(song: _NativeSong, payload: dict[int, dict] | None) -> int:
    if not isinstance(payload, dict) or not payload:
        return 0
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return 0

    applied = 0
    for idx, fg_group_meta in payload.items():
        try:
            idx_i = int(idx)
        except (ValueError, TypeError):
            continue
        if idx_i < 0 or idx_i >= len(ga_candidates):
            continue
        candidate = ga_candidates[idx_i]
        if not isinstance(candidate, dict):
            continue
        data = candidate.get("Data")
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("_fg_group_meta"), dict):
            continue
        if not isinstance(fg_group_meta, dict):
            continue
        data["_fg_group_meta"] = fg_group_meta
        applied += 1

    return int(applied)


def _resolve_fg_group_meta_prime_limit(
    song: Any,
    *,
    explicit_limit: int,
    explicit_enabled: bool,
) -> int:
    if not bool(getattr(song.gpu_inputs, "force_greats_finder", False)):
        return 0
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return 0
    max_candidates = max(0, min(int(len(ga_candidates)), 512))
    if max_candidates <= 0:
        return 0
    if bool(explicit_enabled):
        return max(0, min(int(explicit_limit), int(max_candidates)))
    return _default_fg_group_meta_prime_limit(max_candidates)


def prime_fg_group_meta_for_song(song: _NativeSong, *, limit: int) -> int:
    limit_i = max(0, min(int(limit), 512))
    if limit_i <= 0:
        return 0
    return int(
        apply_fg_group_meta_payload(
            song,
            collect_fg_group_meta_payload(song, limit=limit_i),
        )
    )


def _decode_ga_payload_sync(song: _NativeSong, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = thread_cpu_time_s()
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_start",
            song_key=song_key,
            metrics={"song_slot": int(getattr(song.runtime, "song_slot", 0) or 0)},
        )
    except Exception as e:
        logger.debug(f"native_inflight_stages:_decode_ga_payload_sync: {e}")
    decode_cfg_data = dict(getattr(song.gpu_inputs, "cfg_data", {}) or {})
    best_data, best_gear, best_minis, ga_candidates = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=gpu_inputs.registry,
        cfg_data=decode_cfg_data,
        base_stats_fixed=gpu_inputs.fixed_stats,
        fg_candidate_limit=safe_int(
            decode_cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
        # Keep decode focused on GA payload reconstruction. FG-specific song context,
        # runtime warmup, and group-meta priming belong to the explicit FG prep stage.
        calc_song=None,
        ref_arrays=None,
        fg_group_meta_limit=0,
    )
    out = (best_data, best_gear, best_minis, ga_candidates)
    try:
        cpu_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        song.runtime.decode.cpu_decode_s = cpu_s
    except (AttributeError, TypeError, ValueError):
        cpu_s = None
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_done",
            song_key=song_key,
            metrics={
                "song_slot": int(getattr(song.runtime, "song_slot", 0) or 0),
                "ga_candidates": int(len(ga_candidates or [])),
                "cpu_s": float(cpu_s or 0.0),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_stages:_decode_ga_payload_sync: {e}")
    return out


def prepare_fg_static_sync(song: _NativeSong) -> None:
    """
    Prepare the GA-invariant part of FG while GA is still running.

    Finder-mode FG consumes GA candidates directly, so `loadout_entries` can be
    built from DB rows before GA decode finishes. The late FG prep still owns
    candidate selection and any work that depends on GA output.
    """
    cpu_t0 = thread_cpu_time_s()
    config = getattr(song, 'config', song)
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    cfg = getattr(config, "cfg", None)

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    runtime.fg.fg_candidate_limit = int(fg_candidate_limit)
    runtime.fg.fg_search_radius = read_fg_search_radius(cfg)
    runtime.fg.fg_direct_ga_candidates = bool(gpu_inputs.force_greats_finder)
    song.runtime.fg.fg_build_details = make_build_details_fn(
        gpu_inputs.meta_primary_color,
        gpu_inputs.meta_secondary_color,
        config.effective_difficulty,
    )
    resolve_active_fg_calc_song(song)

    # Manual-only FG needs GA candidates merged into loadout_entries, so it stays
    # in the late prep phase. Finder-mode can use DB/static entries immediately.
    if not bool(runtime.fg.fg_direct_ga_candidates):
        try:
            song.runtime.fg.fg_static_prep_done = True
            song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        except AttributeError:
            pass
        return

    if getattr(song.runtime.fg, "loadout_entries", None) is not None:
        try:
            song.runtime.fg.fg_static_prep_done = True
            song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        except AttributeError:
            pass
        return

    db_loadouts_full = runtime.db.db_loadouts_full
    prefetch_pending = False
    if db_loadouts_full is None and runtime.db.db_loadouts_future is not None:
        try:
            fut = runtime.db.db_loadouts_future
            if fut.done():
                try:
                    db_loadouts_full = fut.result(timeout=0)
                    runtime.db.db_loadouts_full = db_loadouts_full
                    if isinstance(db_loadouts_full, list):
                        _fg_db_cache_put(
                            config.db_key,
                            limit=int(fg_candidate_limit),
                            rows=db_loadouts_full,
                            team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
                        )
                except Exception as e:
                    logger.debug(f"native_inflight_stages:prepare_fg_static_sync: {e}")
                    db_loadouts_full = None
                finally:
                    runtime.db.db_loadouts_future = None
            else:
                prefetch_pending = True
                db_loadouts_full = None
        except Exception as e:
            logger.debug(f"native_inflight_stages:prepare_fg_static_sync: {e}")
            db_loadouts_full = None

    runtime.fg.loadout_entries = build_loadout_entries(
        config.db_key,
        bool(config.use_evo_db),
        [],
        int(fg_candidate_limit),
        gpu_inputs.gears_by_name,
        gpu_inputs.minis_by_name,
        song.runtime.fg.fg_build_details,
        team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
        db_loadouts_full=db_loadouts_full,
        allow_db_query=not bool(prefetch_pending),
        materialize_ga_details=False,
        ga_registry=gpu_inputs.registry,
    )
    try:
        song.runtime.fg.fg_static_prep_done = True
        song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except AttributeError:
        pass


def prepare_fg_job_sync(song: _NativeSong, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = thread_cpu_time_s()
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    wall_t0 = time.perf_counter()
    prep_submit_t0 = song.runtime.fg.fg_prep_submit_t0
    queue_wait_ms = 0.0
    if isinstance(prep_submit_t0, (int, float)):
        queue_wait_ms = max(0.0, (float(wall_t0) - float(prep_submit_t0)) * 1000.0)
    static_future = getattr(song.runtime.fg, "fg_static_prep_future", None)
    if static_future is not None:
        static_done = False
        try:
            static_done = bool(static_future.done())
        except Exception as e:
            logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
            static_done = True
        if static_done:
            try:
                static_future.result()
            except Exception as e:
                logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
            try:
                song.runtime.fg.fg_static_prep_future = None
            except AttributeError:
                pass
    # Static prep is a best-effort accelerator only. If it is not ready yet, FG
    # prep proceeds directly so the runtime can keep feeding the GPU owner.

    config = getattr(song, 'config', song)
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    cfg = getattr(config, "cfg", None)

    perf = _truthy(env_get("PERF_TIMING", "0"))
    t0 = time.perf_counter()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    runtime.fg.fg_candidate_limit = int(fg_candidate_limit)
    runtime.fg.fg_search_radius = read_fg_search_radius(cfg)

    active_fg_calc_song = resolve_active_fg_calc_song(song)

    if bool(getattr(song.gpu_inputs, "force_greats_finder", False)):
        try:
            calc_song = active_fg_calc_song if isinstance(active_fg_calc_song, dict) else None
            ref_arrays = gpu_inputs.ref_arrays if isinstance(gpu_inputs.ref_arrays, dict) else None
            if calc_song and ref_arrays:
                _warmup_fg_finder_runtime(calc_song, ref_arrays, gpu_client=gpu_client)
        except Exception as e:
            logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
    t_finder_warmup = time.perf_counter()

    # Prime expensive per-song FG structures early so FG dispatch doesn't stall before the first GPU submit.
    _maybe_prewarm_fg_chart_scorer(song)
    t_chart_prewarm = time.perf_counter()

    ga_candidates = runtime.decode.ga_candidates if isinstance(runtime.decode.ga_candidates, list) else list(runtime.decode.ga_candidates or [])
    preselect_ga_candidates = len(ga_candidates)
    # If GA came from the GPU-native "selected payload" path, candidates are already GPU-selected
    # (bounded + deduped) and re-running the CPU selector is pure overhead on slower machines.
    is_gpu_selected_payload = False
    try:
        if ga_candidates:
            d0 = ga_candidates[0].get("Data") if isinstance(ga_candidates[0], dict) else None
            if isinstance(d0, dict) and ("_ga_gpu_run_idx" in d0 or "_ga_gpu_row_idx" in d0):
                is_gpu_selected_payload = True
    except (KeyError, TypeError, ValueError, AttributeError):
        is_gpu_selected_payload = False

    t_candidate_select0 = time.perf_counter()
    if is_gpu_selected_payload:
        ga_candidates = ga_candidates[: int(fg_candidate_limit)]
    else:
        ga_candidates = select_fg_candidates(
            ga_candidates,
            limit=fg_candidate_limit,
            primary_color=str(gpu_inputs.meta_primary_color or ""),
            secondary_color=str(gpu_inputs.meta_secondary_color or ""),
        )
    t_candidate_select = time.perf_counter()
    runtime.decode.ga_candidates = ga_candidates
    hydrated_fg_stats = False
    if bool(getattr(song.gpu_inputs, "force_greats_finder", False)) and ga_candidates:
        hydrated_fg_stats = True
        hydrate_fg_candidate_stats(
            ga_candidates,
            base_stats_fixed=gpu_inputs.fixed_stats,
            selected_color=str((getattr(song.gpu_inputs, "cfg_data", None) or {}).get("selected_color", "") or ""),
            cfg_data=getattr(song.gpu_inputs, "cfg_data", None),
        )
    t_select = time.perf_counter()

    (
        prime_group_meta_limit,
        prime_group_meta_limit_explicit,
        _,
    ) = read_fg_group_meta_prime_settings()
    prime_group_meta_limit = _resolve_fg_group_meta_prime_limit(
        song,
        explicit_limit=int(prime_group_meta_limit),
        explicit_enabled=bool(prime_group_meta_limit_explicit),
    )
    group_meta_primed = 0
    if int(prime_group_meta_limit) > 0:
        # Finder-mode FG depends on selected-candidate group metadata to be
        # genuinely runnable. Prime it during FG prep so `fg_prep_future.done()`
        # once again means "ready to submit", not "ready to start another CPU
        # collect stage".
        group_meta_primed = prime_fg_group_meta_for_song(song, limit=int(prime_group_meta_limit))
    t_group_meta = time.perf_counter()

    # Non-blocking DB prefetch: check if future is ready without blocking.
    # If the DB read is still in progress, proceed with GA candidates only.
    # This prevents FG worker threads from stalling on DB I/O and starving the GPU.
    db_loadouts_full = runtime.db.db_loadouts_full
    prefetch_pending = False
    if db_loadouts_full is None and runtime.db.db_loadouts_future is not None:
        try:
            fut = runtime.db.db_loadouts_future
            # Use done() check to avoid blocking - if DB read isn't ready, skip it
            if fut.done():
                try:
                    db_loadouts_full = fut.result(timeout=0)
                    runtime.db.db_loadouts_full = db_loadouts_full
                    if isinstance(db_loadouts_full, list):
                        _fg_db_cache_put(
                            config.db_key,
                            limit=int(fg_candidate_limit),
                            rows=db_loadouts_full,
                            team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
                        )
                except Exception as e:
                    logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
                    db_loadouts_full = None
                finally:
                    runtime.db.db_loadouts_future = None
            else:
                # DB prefetch still running - proceed without it to keep GPU fed
                if perf:
                    logger.debug("[PERF][FGPrep] db_prefetch not ready, proceeding without DB loadouts")
                prefetch_pending = True
                db_loadouts_full = None
        except Exception as e:
            logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
            db_loadouts_full = None
    t_db = time.perf_counter()

    build_details = song.runtime.fg.fg_build_details
    if not callable(build_details):
        build_details = make_build_details_fn(
            gpu_inputs.meta_primary_color, gpu_inputs.meta_secondary_color, config.effective_difficulty
        )
        song.runtime.fg.fg_build_details = build_details
    runtime.fg.fg_direct_ga_candidates = bool(gpu_inputs.force_greats_finder)
    # Keep FG prep focused on DB rows; GPU finder consumes GA candidates directly and
    # only the retained GA subset is merged back into `runtime.fg.loadout_entries` after FG.
    loadout_ga_candidates = [] if bool(runtime.fg.fg_direct_ga_candidates) else list(ga_candidates or [])
    if getattr(song.runtime.fg, "loadout_entries", None) is None or not bool(runtime.fg.fg_direct_ga_candidates):
        runtime.fg.loadout_entries = build_loadout_entries(
            config.db_key,
            bool(config.use_evo_db),
            loadout_ga_candidates,
            fg_candidate_limit,
            gpu_inputs.gears_by_name,
            gpu_inputs.minis_by_name,
            build_details,
            team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
            db_loadouts_full=db_loadouts_full,
            # If prefetch is still in-flight, avoid a duplicate synchronous DB read.
            allow_db_query=not bool(prefetch_pending),
            # FG grouping reads eval_data/BaseStats directly; defer details materialization
            # until persistence/retained-output paths so CPU prep does not stall the GPU.
            materialize_ga_details=False,
            ga_registry=gpu_inputs.registry,
        )
    t_build = time.perf_counter()

    select_ms = (t_select - t0) * 1000.0
    finder_warmup_ms = (t_finder_warmup - t0) * 1000.0
    chart_prewarm_ms = (t_chart_prewarm - t_finder_warmup) * 1000.0
    candidate_select_ms = (t_candidate_select - t_candidate_select0) * 1000.0
    hydrate_stats_ms = (t_select - t_candidate_select) * 1000.0
    group_meta_ms = (t_group_meta - t_select) * 1000.0
    db_wait_ms = (t_db - t_group_meta) * 1000.0
    build_ms = (t_build - t_db) * 1000.0
    total_ms = (t_build - t0) * 1000.0
    try:
        loadouts_n = len(runtime.fg.loadout_entries or {})
    except (TypeError, AttributeError):
        loadouts_n = 0
    db_n = -1
    try:
        if isinstance(db_loadouts_full, list):
            db_n = len(db_loadouts_full)
    except TypeError:
        db_n = -1
    if perf:
        logger.debug(
            "[PERF][FGPrep] "
            f"limit={fg_candidate_limit} ga_in={preselect_ga_candidates} ga={len(ga_candidates)} "
            f"loadouts={loadouts_n} select={select_ms:.1f}ms "
            f"finder_warmup={finder_warmup_ms:.1f}ms chart_prewarm={chart_prewarm_ms:.1f}ms "
            f"candidate_select={candidate_select_ms:.1f}ms hydrate={hydrate_stats_ms:.1f}ms "
            f"group_meta={group_meta_ms:.1f}ms db_wait={db_wait_ms:.1f}ms "
            f"build={build_ms:.1f}ms total={total_ms:.1f}ms "
            f"db_prefetch={int(db_n >= 0)} db_n={db_n}"
        )

    try:
        song.runtime.fg.cpu_fg_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        emit_profile_event(
            component="inflight_fg_prep",
            event="prep_done",
            song_key=str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or ""),
            metrics={
                "queue_wait_ms": float(queue_wait_ms),
                "select_ms": float(select_ms),
                "finder_warmup_ms": float(finder_warmup_ms),
                "chart_prewarm_ms": float(chart_prewarm_ms),
                "candidate_select_ms": float(candidate_select_ms),
                "hydrate_stats_ms": float(hydrate_stats_ms),
                "group_meta_ms": float(group_meta_ms),
                "group_meta_primed": int(group_meta_primed),
                "group_meta_target": int(prime_group_meta_limit),
                "db_wait_ms": float(db_wait_ms),
                "build_ms": float(build_ms),
                "total_ms": float(total_ms),
                "preselect_ga_candidates": int(preselect_ga_candidates),
                "ga_candidates": int(len(ga_candidates or [])),
                "gpu_selected_payload": int(bool(is_gpu_selected_payload)),
                "hydrated_fg_stats": int(bool(hydrated_fg_stats)),
                "loadouts": int(len(getattr(song.runtime.fg, "loadout_entries", {}) or {})),
        "direct_ga_candidates": int(bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False))),
                "db_prefetch_pending": int(bool(prefetch_pending)),
                "db_rows": int(len(db_loadouts_full or [])) if isinstance(db_loadouts_full, list) else -1,
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_stages:prepare_fg_job_sync: {e}")
