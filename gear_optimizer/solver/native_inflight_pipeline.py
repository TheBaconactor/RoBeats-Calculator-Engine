from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.data.song_io import clone_calc_song
from gear_optimizer.solver.exact_base_pipeline_decode import decode_exact_base_pipeline_result
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.native_fg_owner import ExactBaseOwnerResult
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline_fg import (
    NativeFGJobCompletion,
    NativeFGPipeline,
    NativeFGPipelineSettings,
    NativeFGPrepCompletion,
    read_native_fg_pipeline_settings,
    run_fg_job_sync,
)
from gear_optimizer.solver.native_inflight_pipeline_base import (
    BaseDecodeCompletion,
    BaseDecodeQueue,
    BaseSearchCompletion,
    InflightBasePipeline,
)

logger = logging.getLogger(__name__)

_FG_RUNTIME_CALC_SONG_KEYS = ("_gpu_song_slot",)

__all__ = [
    "BaseDecodeCompletion",
    "BaseDecodeQueue",
    "BaseSearchCompletion",
    "InflightBasePipeline",
    "InFlightStageProfiler",
    "NativeFGJobCompletion",
    "NativeFGPipeline",
    "NativeFGPipelineSettings",
    "NativeFGPrepCompletion",
    "_sync_fg_runtime_calc_song_keys",
    "decode_base_result_sync",
    "prepare_base_candidate_surface_for_fg",
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
        fg_calc_song = clone_calc_song(calc_song)
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    # Fail loud: FG scored without the timing envelope would silently use chart floors --
    # a plausible-but-wrong best_fg_score, not a recoverable state.
    if apply_timing_envelope(fg_calc_song) is None:
        raise ValueError("resolve_active_fg_calc_song: calc_song carries no chart timestamps to envelope")
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


def decode_base_result_sync(
    song: NativeSong,
    owner_result: ExactBaseOwnerResult,
) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = thread_cpu_time_s()
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    if not isinstance(owner_result, ExactBaseOwnerResult):
        raise TypeError(
            f"Exact Base owner returned {type(owner_result).__name__} for {song_key}; "
            "expected ExactBaseOwnerResult"
        )
    context = song.gpu_inputs.solver_context
    if context is None:
        raise RuntimeError(f"Exact Base decode is missing SolverContext for {song_key}")
    if not isinstance(owner_result.fg_owner_score, dict) or not owner_result.fg_owner_score:
        raise RuntimeError(f"Exact Base owner returned no native FG scores for {song_key}")
    song.runtime.fg.fg_owner_score_map = owner_result.fg_owner_score
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_start",
            song_key=song_key,
            metrics={"song_slot": int(getattr(song.runtime, "song_slot", 0) or 0)},
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:decode_base_result_sync: {e}")
    best_data, best_gear, best_minis, base_candidates = decode_exact_base_pipeline_result(
        result=owner_result.base_result,
        context=context,
    )
    out = (best_data, best_gear, best_minis, base_candidates)
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
                "base_candidates": int(len(base_candidates or [])),
                "cpu_s": float(cpu_s or 0.0),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:decode_base_result_sync: {e}")
    return out


def prepare_fg_static_sync(song: NativeSong) -> None:
    """
    Prepare the candidate-independent native FG bundle before exact Base runs.
    """
    from gear_optimizer.solver.fg_response_scoring.store import ResponseFrontierStore

    ResponseFrontierStore.ensure_song_bundle(song)


def prepare_base_candidate_surface_for_fg(
    song: NativeSong,
    *,
    fg_candidate_limit: int,
) -> tuple[list[dict], int]:
    runtime = getattr(song, "runtime", song)
    selected = list(runtime.decode.base_candidates or [])
    if not selected:
        raise RuntimeError("Exact Base did not provide a candidate surface for native FG")
    if len(selected) > int(fg_candidate_limit):
        raise RuntimeError(
            f"Exact Base candidate surface exceeds the FG contract: {len(selected)} > {fg_candidate_limit}"
        )
    scores = [int(candidate.get("BaseScore") or candidate.get("Score") or 0) for candidate in selected]
    if any(score <= 0 for score in scores) or any(a < b for a, b in zip(scores, scores[1:], strict=False)):
        raise RuntimeError("Exact Base candidate surface is not positive Base-score descending")
    runtime.decode.fg_surface_prepared = True
    return selected, int(len(selected))


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
    base_candidates, candidate_count = prepare_base_candidate_surface_for_fg(
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

    # Fused exact Base->FG handoff: the GPU owner scores FG in the Base turn from the
    # device base_stats7, so FG prep only builds the plan (candidate select + per-batch
    # base_components, paired-base + cache_key dedup). The plan's base_components key the
    # lookup into the owner score map at materialize time; no BUILD/SCORE owner round-trip
    # is prefetched here anymore (the former prefetch_group_builds + finalize step is gone).
    runtime.fg.fg_response_frontier_plan = FgPlanner.plan_prepared_base_candidates(song, base_candidates)
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
            f"limit={fg_candidate_limit} base_in={candidate_count} base={len(base_candidates)} "
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
                "base_candidates_in": int(candidate_count),
                "base_candidates": int(len(base_candidates or [])),
                "prepared_batches": int(len(prepared_batches)),
                "prepared_bundle_ms": float(prepared_bundle_ms),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
