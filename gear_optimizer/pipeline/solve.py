"""A song end to end: prepare_native_song (incl. the GA-invariant FG static prep) -> run_ga (the GA with its fused FG
owner score, a call on the GPU executor) -> finish_song (decode -> FG plan -> FG materialization -> SongSolve, host
only). A run's worker processes (pipeline.workers) and the service's persistent worker solve one song at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.results import SongSolve

def _ga_turn(song: Any, abort_requested: Callable[[], bool]) -> tuple:
    """On the GPU owner thread: the song's GA, then the FG turn on the loadouts it selects (their FG scores and the FG
    search's board candidates)."""
    from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
    from gear_optimizer.gpu.ga import run_ga
    from gear_optimizer.pipeline.fg import fg_turn
    from gear_optimizer.solver.ga_selection import select_ga_loadouts

    inputs = song.gpu_inputs
    table = run_ga(inputs, song.config.ga_seed, abort_requested)
    return fg_turn(song, select_ga_loadouts(table, inputs.fg_gear_name_rank, inputs.fg_mini_sig_id, LOADOUTS_PER_SONG_LIMIT))


def run_ga(song: Any, executor: Any) -> tuple:
    """The GA result of a prepared song (prepare_native_song) on the GPU executor (started)."""
    return executor.call(_ga_turn, song, executor.abort_requested)


def finish_song(song: Any, ga_result: Any) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work)."""
    from gear_optimizer.pipeline.fg import finish_fg

    return finish_fg(song, ga_result)


def solve_song(task: SongTask, executor: Any) -> SongSolve:
    """The SongSolve of one queue task."""
    from gear_optimizer.pipeline.prepare import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, executor))
