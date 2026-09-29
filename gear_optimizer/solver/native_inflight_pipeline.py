from __future__ import annotations

import logging
import time
from typing import Any, Optional

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.data.song_io import clone_calc_song
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_top_base_ga_candidates
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.solver.genetic_pipeline_decode import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.gpu_service import GpuServiceClient
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
    return float(time.thread_time())


def _sync_fg_runtime_calc_song_keys(source_calc_song: Any, target_calc_song: Any) -> None:
    if not isinstance(source_calc_song, dict) or not isinstance(target_calc_song, dict):
        return
    for key in _FG_RUNTIME_CALC_SONG_KEYS:
        if key in source_calc_song:
            target_calc_song[key] = source_calc_song.get(key)
        else:
            target_calc_song.pop(key, None)


def resolve_active_fg_calc_song(song: NativeSong) -> dict | None:
    calc_song = song.gpu_inputs.calc_song
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
    if fg_state is not None:
        fg_state.fg_calc_song = fg_calc_song
    return fg_calc_song


def decode_ga_payload_sync(song: NativeSong, ga_result: Any) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = thread_cpu_time_s()
    gpu_inputs = getattr(song, "gpu_inputs", song)
    song_key = str(song.config.task_key or song.config.song_name or "")
    # The fused GA->FG owner continuation (Slice 3) returns
    # {runs_payload, fg_owner_score}: the GA payload plus the owner-scored FG result
    # map. Unpack the map onto the song for the FG worker; decode consumes the payload.
    if not isinstance(ga_result, dict) or "runs_payload" not in ga_result:
        raise RuntimeError(f"GPU-native GA result must be a fused {{runs_payload, fg_owner_score}} dict for {song_key}")
    runs_payload = ga_result["runs_payload"]
    song.runtime.fg.fg_owner_score_map = ga_result.get("fg_owner_score")
    decode_cfg_data = dict(song.gpu_inputs.cfg_data or {})
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
    # ``ga_candidates`` carries the raw GPU-deduped candidate pool from decode (no
    # decode-side select anymore). This is the single canonical color-folded select
    # over that raw pool -- the FG funnel + persistence authority. It runs exactly
    # once per song (prepare_fg_job_sync, or build_deferred_post_payload when FG is
    # skipped), then overwrites ga_candidates with the selected surface below.
    source_candidates = runtime.decode.ga_candidates
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
            calc_song=resolve_active_fg_calc_song(song),
            ref_arrays=song.gpu_inputs.ref_arrays,
        )
    runtime.decode.ga_candidates = selected
    runtime.decode.fg_surface_prepared = True
    return selected, int(preselect_count), bool(hydrated)


def prepare_fg_job_sync(song: NativeSong, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = thread_cpu_time_s()
    runtime = getattr(song, "runtime", song)
    t0 = time.perf_counter()
    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT)
    resolve_active_fg_calc_song(song)
    ga_candidates, _preselect_count, _hydrated = prepare_ga_candidate_surface_for_fg(
        song,
        fg_candidate_limit=int(fg_candidate_limit),
    )
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    # Fused GA->FG handoff (Slice 3): the GPU owner scores FG in the GA turn from the
    # device base_stats7, so FG prep only builds the plan (candidate select + per-batch
    # base_components, paired-base + cache_key dedup). The plan's base_components key the
    # lookup into the owner score map at materialize time; no BUILD/SCORE owner round-trip
    # is prefetched here anymore (the former prefetch_group_builds + finalize step is gone).
    runtime.fg.fg_response_frontier_plan = FgPlanner.plan_prepared_ga_candidates(song, ga_candidates)
    if runtime.fg.fg_response_frontier_plan is None:
        raise RuntimeError(
            "FG dynamic prep did not materialize the exact response frontier plan "
            f"for {getattr(song.config, 'task_key', '') or getattr(song.config, 'song_name', '')}"
        )
    song.runtime.fg.fg_prep_wall_s = max(0.0, time.perf_counter() - t0)
    try:
        song.runtime.fg.cpu_fg_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except (AttributeError, TypeError, ValueError):
        pass
