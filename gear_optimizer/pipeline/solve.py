"""A song end to end: prepare_native_song (incl. the GA-invariant FG static prep) -> run_ga (the GA with its fused FG
owner score, a call on the GPU executor) -> finish_song (decode -> FG plan -> FG materialization -> SongSolve, host
only). A run's worker processes (pipeline.workers) and the service's persistent worker solve one song at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.results import SongSolve

# The GPU song slot of a song's GA runs.
_GA_SLOT = 1


def _ga_turn(payload: dict, abort_requested: Callable[[], bool]) -> tuple:
    """On the GPU owner thread: the song's GA runs, then the FG turn on the payload they select (its FG scores and the
    FG search's board candidates; the search widens with the GA's runs, i.e. the reasoning level)."""
    from gear_optimizer.pipeline.fg import FG_SEARCH_BEAM_PER_GA_RUN, fg_turn
    from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt

    ga_kwargs = dict(payload)
    fg_scoring_bundle = ga_kwargs.pop("fg_scoring_bundle")
    selected_color = ga_kwargs.pop("selected_color")
    runs_payload = run_gpu_native_ga_runs_payload_prebuilt(**ga_kwargs, abort_requested=abort_requested)
    return fg_turn(
        runs_payload, song=ga_kwargs["song"], curves=ga_kwargs["curves"], selected_color=selected_color,
        fg_scoring_bundle=fg_scoring_bundle, item_stats=ga_kwargs["item_stats"], slot_start=ga_kwargs["slot_start"],
        slot_count=ga_kwargs["slot_count"], base_fixed_stats_arr=ga_kwargs["base_fixed_stats_arr"],
        beam_width=FG_SEARCH_BEAM_PER_GA_RUN * ga_kwargs["num_runs"],
    )


def run_ga(song: Any, executor: Any) -> tuple:
    """The GA result of a prepared song (prepare_native_song) on the GPU executor (started)."""
    from gear_optimizer.pipeline.ga import ga_payload

    song.runtime.song_slot = _GA_SLOT
    try:
        return executor.call(_ga_turn, ga_payload(song), executor.abort_requested)
    finally:
        song.runtime.song_slot = 0


def finish_song(song: Any, ga_result: Any) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work)."""
    from gear_optimizer.pipeline.fg import finish_fg

    return finish_fg(song, ga_result)


def solve_song(task: SongTask, executor: Any) -> SongSolve:
    """The SongSolve of one queue task."""
    from gear_optimizer.pipeline.prepare import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, executor))
