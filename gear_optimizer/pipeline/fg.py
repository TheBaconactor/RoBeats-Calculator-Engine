"""A song's FG stage: its GA-invariant preparation (the FG scoring bundle), the FG plan over its GA candidates, the
materialized FG results, and the release of its FG surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_top_base_ga_candidates
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.pipeline.song import NativeSong
from gear_optimizer.solver.fg_materialization_worker import FgMaterializationResult

if TYPE_CHECKING:
    from gear_optimizer.pipeline.progress import ProgressTracker


def prepare_fg_static(song: NativeSong) -> None:
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
    # once per song (prepare_fg_plan), then overwrites ga_candidates with the selected surface below.
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
            song=song.gpu_inputs.timed_song,
            curves=song.gpu_inputs.curves,
        )
    runtime.decode.ga_candidates = selected
    runtime.decode.fg_surface_prepared = True
    return selected, int(preselect_count), bool(hydrated)


def prepare_fg_plan(song: NativeSong) -> None:
    runtime = getattr(song, "runtime", song)
    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT)
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


def release_fg_song_surfaces(song: NativeSong) -> None:
    """Release a song's ~0.5-1.5 GB FG response surfaces once its FG scoring is complete.

    After this job's `materialize_from_owner_score_map`, nothing else reads the per-song scoring
    bundle, prepared plan, or owner score map -- the fused GA turn and the FG planner are the only
    other readers and both run earlier. Left alone, each song's surface pool stays resident, pinned
    by BOTH the per-song bundle handle and the process-global response-frontier caches, until the
    song object is garbage-collected and the entry-count LRU evicts it. A standalone optimizer run
    never runs the serving-mode idle sweep, so ~prep_limit songs' worth accumulates and trips the
    memory guard after only a few dozen songs. Dropping all three references here bounds resident FG
    surfaces to the songs actively scoring. Lossless: any later access rebuilds from the on-disk
    bundle. Best-effort -- a cleanup error must not fail the already-complete FG job.
    """
    fg = song.runtime.fg
    if fg is None:
        return
    bundle = getattr(fg, "fg_response_scoring_bundle", None)
    if bundle is not None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            release_fg_response_song_memory,
        )

        release_fg_response_song_memory(getattr(bundle, "cache_key", ()))
    fg.fg_response_scoring_bundle = None
    fg.fg_response_frontier_plan = None
    fg.fg_owner_score_map = None


def apply_fg_materialization_result(
    song: NativeSong,
    result: FgMaterializationResult,
    *,
    progress_tracker: ProgressTracker | None = None,
) -> None:
    """The song's FG results, and its records judged against `progress_tracker` (a run's bests) when given."""

    if not isinstance(result, FgMaterializationResult):
        raise TypeError("FG materialization worker returned an invalid result")

    from gear_optimizer.pipeline.progress import evaluate_fg_progress_record_update

    runtime = getattr(song, "runtime", song)
    runtime.fg.fg_results = result.results
    runtime.db.record_info = evaluate_fg_progress_record_update(song, progress_tracker)
