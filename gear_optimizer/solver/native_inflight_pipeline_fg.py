from __future__ import annotations

from typing import TYPE_CHECKING

from gear_optimizer.solver.fg_materialization_worker import (
    FgMaterializationResult,
)
from gear_optimizer.solver.native_inflight_config import NativeSong

if TYPE_CHECKING:
    from gear_optimizer.solver.native_inflight_lifecycle import ProgressTracker


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
    progress_cb=None,
    progress_tracker: ProgressTracker | None = None,
) -> None:
    """Apply a spawned worker's FG results on the driver/persistence owner."""

    if not isinstance(result, FgMaterializationResult):
        raise TypeError("FG materialization worker returned an invalid result")

    from gear_optimizer.solver.native_inflight_lifecycle import evaluate_fg_progress_record_update

    runtime = getattr(song, "runtime", song)
    runtime.fg.fg_results = result.results
    runtime.fg.fg_run_wall_s = max(0.0, float(result.wall_seconds))
    runtime.fg.cpu_fg_run_s = max(0.0, float(result.cpu_seconds))

    runtime.db.record_info = evaluate_fg_progress_record_update(song, progress_tracker)
    if progress_cb is not None:
        progress_cb(completed_delta=0, failed_delta=0, record_info=runtime.db.record_info)
