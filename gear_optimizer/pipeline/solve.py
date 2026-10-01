"""One song end to end in this process, then its store rows.

prepare -> the GA (with its fused FG owner score) on the GPU executor -> decode -> FG plan -> FG materialization ->
SongSolve; `store_solve` canonicalizes (the meta gem re-solve runs on this process's warm GPU context) and stores.
Sequential: while the GPU executor runs a song's GA nothing else needs the device or the GIL, so the host stages
run on the calling thread with no per-song process or pool (the in-flight pipeline spawns a post-processor process
and an FG process pool per run).
"""

from __future__ import annotations

from gear_optimizer.pipeline.results import SongSolve, song_solve

# Slot 0 is the registry solves' (the meta gem re-solve); GA runs use 1..N-1 (song_slot_pool).
_GA_SLOT = 1


class SolveContext:
    """A process's GPU executor client, started once (the executor keeps Taichi and the GA kernels warm)."""

    def __init__(self) -> None:
        from gear_optimizer.solver.native_inflight_lifecycle import start_native_inflight_gpu_client

        self._executor, self.gpu_client = start_native_inflight_gpu_client()

    def close(self) -> None:
        self.gpu_client.close(timeout=2.0)


def solve_song(task: tuple, ctx: SolveContext) -> SongSolve:
    """The SongSolve of one prepared task (an app task tuple)."""
    from gear_optimizer.solver.fg_materialization_worker import (
        build_fg_materialization_request,
        materialize_fg_request,
    )
    from gear_optimizer.solver.native_inflight_lifecycle import prepare_native_song
    from gear_optimizer.solver.native_inflight_pipeline import decode_ga_payload_sync, prepare_fg_job_sync
    from gear_optimizer.solver.native_inflight_pipeline_fg import (
        apply_fg_materialization_result,
        release_fg_song_surfaces,
    )
    from gear_optimizer.solver.native_inflight_pipeline_ga import InflightGAPipeline

    song = prepare_native_song(task)
    song.runtime.song_slot = _GA_SLOT
    try:
        InflightGAPipeline.prepare_submit(song)
        ga_result = ctx.gpu_client.submit_gpu_native_ga_run(InflightGAPipeline.build_payload(song)).future.result()
    finally:
        song.runtime.song_slot = 0
    InflightGAPipeline.store_decode_result(song, decode_ga_payload_sync(song, ga_result))
    try:
        prepare_fg_job_sync(song)
        song.runtime.fg.fg_dynamic_prep_done = True
        apply_fg_materialization_result(song, materialize_fg_request(build_fg_materialization_request(song)))
    finally:
        release_fg_song_surfaces(song)
    return song_solve(song)
