from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.data.song_io import clone_calc_song
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_top_base_ga_candidates
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.solver.genetic_pipeline import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline_fg import (
    NativeFGJobCompletion,
    NativeFGPipeline,
    NativeFGPipelineSettings,
    NativeFGPrepCompletion,
    read_native_fg_pipeline_settings,
    run_fg_job_sync,
)
from gear_optimizer.solver.native_inflight_pipeline_ga import (
    GADecodeCompletion,
    GADecodeQueue,
    GARunCompletion,
    InflightGAPipeline,
)

logger = logging.getLogger(__name__)

_FG_RUNTIME_CALC_SONG_KEYS = ("_gpu_song_slot",)

__all__ = [
    "GADecodeCompletion",
    "GADecodeQueue",
    "GARunCompletion",
    "InflightGAPipeline",
    "InFlightStageProfiler",
    "NativeFGJobCompletion",
    "NativeFGPipeline",
    "NativeFGPipelineSettings",
    "NativeFGPrepCompletion",
    "_sync_fg_runtime_calc_song_keys",
    "decode_ga_payload_sync",
    "prepare_fg_job_sync",
    "prepare_fg_static_sync",
    "read_native_fg_pipeline_settings",
    "resolve_active_fg_calc_song",
    "run_fg_job_sync",
    "thread_cpu_time_s",
]


def thread_cpu_time_s() -> float:
    """Best-effort per-thread CPU timer for CPU-side stage profiling."""
    try:
        return float(time.thread_time())
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:thread_cpu_time_s: {e}")
        return 0.0


def _sync_fg_runtime_calc_song_keys(source_calc_song: Any, target_calc_song: Any) -> None:
    if not isinstance(source_calc_song, dict) or not isinstance(target_calc_song, dict):
        return
    for key in _FG_RUNTIME_CALC_SONG_KEYS:
        if key in source_calc_song:
            target_calc_song[key] = source_calc_song.get(key)
        else:
            target_calc_song.pop(key, None)


def resolve_active_fg_calc_song(song: NativeSong) -> dict | None:
    calc_song = getattr(song.gpu_inputs, "calc_song", None)
    if not isinstance(calc_song, dict):
        return None
    runtime = getattr(song, "runtime", song)
    fg_state = getattr(runtime, "fg", None)
    fg_calc_song = getattr(fg_state, "fg_calc_song", None)
    if not isinstance(fg_calc_song, dict):
        try:
            fg_calc_song = clone_calc_song(calc_song)
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:resolve_active_fg_calc_song: {e}")
            fg_calc_song = {
                "metadata": dict(calc_song.get("metadata", {}) or {}),
                "song_data": dict(calc_song.get("song_data", {}) or {}),
            }
    try:
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        apply_timing_envelope(fg_calc_song)
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:resolve_active_fg_calc_song: {e}")
        return calc_song
    _sync_fg_runtime_calc_song_keys(calc_song, fg_calc_song)
    try:
        if fg_state is not None:
            fg_state.fg_calc_song = fg_calc_song
    except AttributeError:
        pass
    return fg_calc_song


class InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}
        self._allow_prefixes = self._parse_prefixes(env_get("INFLIGHT_STAGE_PROFILE_PREFIX", ""))
        if _truthy(env_get("INFLIGHT_STAGE_PROFILE_FG_ONLY", "0")) and not self._allow_prefixes:
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


def decode_ga_payload_sync(song: NativeSong, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = thread_cpu_time_s()
    gpu_inputs = getattr(song, "gpu_inputs", song)
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_start",
            song_key=song_key,
            metrics={"song_slot": int(getattr(song.runtime, "song_slot", 0) or 0)},
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:decode_ga_payload_sync: {e}")
    decode_cfg_data = dict(getattr(song.gpu_inputs, "cfg_data", {}) or {})
    best_data, best_gear, best_minis, ga_candidates = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=gpu_inputs.registry,
        cfg_data=decode_cfg_data,
        base_stats_fixed=gpu_inputs.fixed_stats,
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
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
        logger.debug(f"native_inflight_pipeline:decode_ga_payload_sync: {e}")
    return out


def prepare_fg_static_sync(song: NativeSong) -> None:
    """
    Prepare the GA-invariant part of FG while GA is still running.
    Response-frontier FG consumes GA candidates directly. The late FG prep still owns
    candidate selection and any work that depends on GA output.
    """
    from gear_optimizer.solver.fg_response_scoring.store import ResponseFrontierStore

    ResponseFrontierStore.ensure_song_bundle(song)


def prepare_ga_candidate_surface_for_fg(
    song: NativeSong,
    *,
    fg_candidate_limit: int,
) -> tuple[list[dict], int, bool]:
    runtime = getattr(song, "runtime", song)
    gpu_inputs = getattr(song, "gpu_inputs", song)
    source_candidates = (
        runtime.decode.ga_persistence_candidates
        if isinstance(getattr(runtime.decode, "ga_persistence_candidates", None), list)
        and getattr(runtime.decode, "ga_persistence_candidates", None)
        else runtime.decode.ga_candidates
    )
    preselect_count = len(source_candidates or [])
    selected = select_top_base_ga_candidates(
        list(source_candidates or []),
        limit=int(fg_candidate_limit),
        registry=getattr(gpu_inputs, "registry", None),
        minis_by_name=getattr(gpu_inputs, "minis_by_name", None),
        primary_color=str(gpu_inputs.meta_primary_color or ""),
        secondary_color=str(gpu_inputs.meta_secondary_color or ""),
        selected_color=str((getattr(gpu_inputs, "cfg_data", None) or {}).get("selected_color", "") or ""),
    )
    hydrated = False
    if selected:
        hydrated = True
        hydrate_fg_candidate_stats(
            selected,
            base_stats_fixed=gpu_inputs.fixed_stats,
            selected_color=str((getattr(gpu_inputs, "cfg_data", None) or {}).get("selected_color", "") or ""),
            cfg_data=getattr(gpu_inputs, "cfg_data", None),
            calc_song=resolve_active_fg_calc_song(song),
            ref_arrays=getattr(song.gpu_inputs, "ref_arrays", None),
        )
    runtime.decode.ga_candidates = selected
    runtime.decode.fg_surface_prepared = True
    return selected, int(preselect_count), bool(hydrated)


def prepare_fg_job_sync(song: NativeSong, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = thread_cpu_time_s()
    runtime = getattr(song, "runtime", song)
    wall_t0 = time.perf_counter()
    prep_submit_t0 = song.runtime.fg.fg_prep_submit_t0
    queue_wait_ms = 0.0
    if isinstance(prep_submit_t0, (int, float)):
        queue_wait_ms = max(0.0, (float(wall_t0) - float(prep_submit_t0)) * 1000.0)
    perf = _truthy(env_get("PERF_TIMING", "0"))
    t0 = time.perf_counter()
    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT)
    resolve_active_fg_calc_song(song)
    t_candidate_select0 = time.perf_counter()
    ga_candidates, preselect_ga_candidates, hydrated_fg_stats = prepare_ga_candidate_surface_for_fg(
        song,
        fg_candidate_limit=int(fg_candidate_limit),
    )
    t_candidate_select = time.perf_counter()
    t_select = time.perf_counter()
    select_ms = (t_select - t0) * 1000.0
    candidate_select_ms = (t_candidate_select - t_candidate_select0) * 1000.0
    hydrate_stats_ms = (t_select - t_candidate_select) * 1000.0
    plan_t0 = time.perf_counter()
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    runtime.fg.fg_response_frontier_plan = (
        FgPlanner.plan_many(
            ga_candidates,
            resolve_active_fg_calc_song(song),
            getattr(song.gpu_inputs, "ref_arrays", None),
            getattr(song.gpu_inputs, "meta_primary_color", ""),
            ga_registry=getattr(song.gpu_inputs, "registry", None),
            scoring_bundle=getattr(song.runtime.fg, "fg_response_scoring_bundle", None),
        )
    )
    if runtime.fg.fg_response_frontier_plan is None:
        raise RuntimeError(
            "FG dynamic prep did not materialize the exact response frontier plan "
            f"for {getattr(song.config, 'task_key', '') or getattr(song.config, 'song_name', '')}"
        )
    plan_ms = (time.perf_counter() - plan_t0) * 1000.0
    prepared_batches = tuple(getattr(runtime.fg.fg_response_frontier_plan, "prepared_batches", ()) or ())
    prepared_bundle_ms = 0.0
    for prepared in prepared_batches:
        batch = getattr(prepared, "batch", None)
        if batch is None:
            continue
        prepared_bundle_ms += float(getattr(batch, "scoring_bundle_ms", 0.0) or 0.0)
    total_ms = (time.perf_counter() - t0) * 1000.0
    try:
        song.runtime.fg.fg_prep_wall_s = max(0.0, float(total_ms) / 1000.0)
    except AttributeError:
        pass
    if perf:
        logger.debug(
            "[PERF][FGPrep] "
            f"limit={fg_candidate_limit} ga_in={preselect_ga_candidates} ga={len(ga_candidates)} "
            f"select={select_ms:.1f}ms "
            f"candidate_select={candidate_select_ms:.1f}ms hydrate={hydrate_stats_ms:.1f}ms "
            f"plan={plan_ms:.1f}ms total={total_ms:.1f}ms"
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
                "candidate_select_ms": float(candidate_select_ms),
                "hydrate_stats_ms": float(hydrate_stats_ms),
                "plan_ms": float(plan_ms),
                "total_ms": float(total_ms),
                "preselect_ga_candidates": int(preselect_ga_candidates),
                "ga_candidates": int(len(ga_candidates or [])),
                "hydrated_fg_stats": int(bool(hydrated_fg_stats)),
                "prepared_batches": int(len(prepared_batches)),
                "prepared_bundle_ms": float(prepared_bundle_ms),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
