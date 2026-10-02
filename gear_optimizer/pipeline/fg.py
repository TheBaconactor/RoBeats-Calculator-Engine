"""A song's FG stage: its GA-invariant preparation (the FG scoring bundle), the FG plan over its GA candidates, the
materialized FG results, and the release of its FG surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_top_base_ga_candidates
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.pipeline.song import NativeSong

if TYPE_CHECKING:
    from gear_optimizer.pipeline.progress import ProgressTracker
    from gear_optimizer.solver.fg_materialization_worker import FgMaterializationResult


def prepare_fg_static(song: NativeSong) -> None:
    """
    Prepare the GA-invariant part of FG while GA is still running.
    Response-frontier FG consumes GA candidates directly. The late FG prep still owns
    candidate selection and any work that depends on GA output.
    """
    from gear_optimizer.solver.fg_response_scoring.store import ResponseFrontierStore

    ResponseFrontierStore.ensure_song_bundle(song)


def prepare_ga_candidate_surface_for_fg(song: NativeSong, *, fg_candidate_limit: int) -> list[dict]:
    """The song's GA candidates selected for FG, with their stats, stored over the raw GPU-deduped pool decode left on
    the song: the single canonical color-folded select (the FG funnel and the persistence authority), once per song."""
    runtime, gpu_inputs = song.runtime, song.gpu_inputs
    selected_color = gpu_inputs.cfg_data.get("selected_color", "")
    selected = select_top_base_ga_candidates(
        list(runtime.decode.ga_candidates or []),
        limit=fg_candidate_limit,
        registry=gpu_inputs.registry,
        minis_by_name=gpu_inputs.minis_by_name,
        primary_color=gpu_inputs.meta_primary_color,
        secondary_color=gpu_inputs.meta_secondary_color,
        selected_color=selected_color,
    )
    if selected:
        hydrate_fg_candidate_stats(
            selected, selected_color=selected_color, song=gpu_inputs.timed_song, curves=gpu_inputs.curves
        )
    runtime.decode.ga_candidates = selected
    runtime.decode.fg_surface_prepared = True
    return selected


def prepare_fg_plan(song: NativeSong) -> None:
    runtime = song.runtime
    ga_candidates = prepare_ga_candidate_surface_for_fg(song, fg_candidate_limit=LOADOUTS_PER_SONG_LIMIT)
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    # The GPU owner scored FG in the GA turn from the device base_stats7, so the FG prep only plans (candidate select,
    # per-batch base_components, paired-base + cache_key dedup); the plan's base_components key the lookup into the
    # owner score map when the results are materialized.
    runtime.fg.fg_response_frontier_plan = FgPlanner.plan_prepared_ga_candidates(song, ga_candidates)
    if runtime.fg.fg_response_frontier_plan is None:
        raise RuntimeError(
            "FG dynamic prep did not materialize the exact response frontier plan "
            f"for {song.config.task_key or song.config.song_name}"
        )


def release_fg_song_surfaces(song: NativeSong) -> None:
    """Release a song's FG response surfaces (~0.5-1.5 GB) once its FG results are materialized.

    Nothing reads its scoring bundle, FG plan or owner score map afterwards (the GA turn and the FG planner ran
    earlier). Left alone, its surfaces stay pinned by the song and by the process-wide response-frontier caches until
    the song is collected and the caches' LRU evicts them; a standalone run has no idle sweep, so they accumulate and
    trip the memory guard after a few dozen songs. Lossless: a later access rebuilds from the on-disk bundle.
    """
    fg = song.runtime.fg
    bundle = fg.fg_response_scoring_bundle
    if bundle is not None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
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
    from gear_optimizer.pipeline.progress import evaluate_fg_progress_record_update

    song.runtime.fg.fg_results = result.results
    song.runtime.db.record_info = evaluate_fg_progress_record_update(song, progress_tracker)
