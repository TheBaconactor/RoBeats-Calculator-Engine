"""A song end to end: prepare_native_song -> run_ga (the GA on the GPU executor, overlapped with loading the FG scoring
bundle once GA work is submitted, then the FG turn on the loadouts it selects) -> finish_song (decode -> FG plan -> FG
materialization -> SongSolve, host only). A run's worker processes (pipeline.workers) and the service's persistent
worker solve one song at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.results import SongSolve


def _ga_table(inputs: Any, seed: int, *, on_submitted: Callable[[], None] | None = None) -> Any:
    """On the GPU owner thread: the song's GA candidate table (gpu.ga.run_ga), stopped by its executor's abort."""
    from gear_optimizer.gpu.executor import get_gpu_executor
    from gear_optimizer.gpu.ga import run_ga

    return run_ga(inputs, seed, get_gpu_executor().abort_requested, on_submitted=on_submitted)


def run_ga(song: Any, executor: Any) -> tuple:
    """The GA result of a prepared song (prepare_native_song): its GA on the GPU executor (started), overlapped with
    loading the song's FG scoring bundle once GA work is submitted, then the FG turn on the loadouts it selects."""
    from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
    from gear_optimizer.pipeline.fg import fg_turn, prepare_fg_static
    from gear_optimizer.solver.ga_selection import select_ga_loadouts

    inputs = song.gpu_inputs

    def load_fg() -> None:
        if song.runtime.fg.fg_response_scoring_bundle is None:
            prepare_fg_static(song)

    on_submitted = load_fg if song.runtime.fg.fg_response_scoring_bundle is None else None
    table = executor.call(_ga_table, inputs, song.config.ga_seed, on_submitted=on_submitted)
    return fg_turn(song, select_ga_loadouts(table, inputs.fg_gear_name_rank, inputs.fg_mini_sig_id, LOADOUTS_PER_SONG_LIMIT))


def finish_song(song: Any, ga_result: Any) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work)."""
    from gear_optimizer.pipeline.fg import finish_fg

    return finish_fg(song, ga_result)


def solve_song(task: SongTask, executor: Any) -> SongSolve:
    """The SongSolve of one queue task."""
    from gear_optimizer.pipeline.prepare import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, executor))
