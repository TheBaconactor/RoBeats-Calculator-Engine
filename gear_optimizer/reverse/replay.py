"""A named set's play as a replay plays it: the hit offsets that give the row's score.

A lookup's set gives the score on a response surface, its fever and Greats. The live engine plans such a surface as it plans
a Force Great build: the section trace whose edges add up to the surface (trace.reconstruct), checked against a physical
replay at the build's windows (trace.physical_replay), then its notes' hit offsets (trace.note_graph). The offsets hold at
every frame timing from 60 fps up. No new timing model: what Force Great replays rely on.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import perfect_time_of
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.timing_envelope import fever_axes, fever_fill_denominators, time_song
from gear_optimizer.trace.note_graph import force_greats_plan, reconcile_force_greats_plan
from gear_optimizer.trace.physical_replay import validate_force_greats_physical_replay
from gear_optimizer.trace.reconstruct import UnplayableTrace, reconstruct_force_greats_response_trace

_MODE = "precise"


def play_offsets(chart, curves, gears, set_gear: tuple[str, ...], stats: dict[str, int], surface: FgResponseSurface) -> dict[int, float] | None:
    """Per note off its chart time, its hit offset in ms in the play behind a set's score; None when no trace plays the
    surface (the lookup's walk reaches a little past what the Force Great producer plans)."""
    inputs = time_song(chart, _MODE).fg_inputs
    real_time_by_ft, raw_fill_by_ff = fever_axes(inputs.total_notes, inputs.long_notes, inputs.last_note_time, curves)
    ft, ff = min(stats["Fever Time"], MAX_STAT), min(stats["Fever Fill Rate"], MAX_STAT)
    perfect_time = perfect_time_of(set_gear, gears)
    try:
        trace = reconstruct_force_greats_response_trace(
            inputs=inputs, non_fever_base=int(ceil(raw_fill_by_ff[ff])), target_surface=surface,
            raw_fever_fill=float(raw_fill_by_ff[ff]), real_fever_time=float(real_time_by_ft[ft]),
        )
        validate_force_greats_physical_replay(
            frontier_trace=trace, surface=surface, timestamps=inputs.timestamps, note_types=chart.note_types, lanes=inputs.lanes,
            fever_fill_denominator=float(fever_fill_denominators(int(inputs.total_notes) - int(inputs.long_notes), curves.f64["Fever Fill Rate"][ff])),
            real_fever_time=float(real_time_by_ft[ft]), timing_mode=_MODE, perfect_time=perfect_time,
        )
    except (UnplayableTrace, ValueError):
        return None
    plan = force_greats_plan(
        frontier_trace=trace, total_notes=chart.total_notes, timestamps=chart.timestamps, note_types=chart.note_types,
        lanes=chart.lanes, timing_mode=_MODE, perfect_time=perfect_time,
    )
    reconcile_force_greats_plan(
        plan, fever_words=surface[0:4], great_words=surface[4:8], body_fever=surface.body_fever, body_great=surface.body_great,
        body_fever_great=surface.body_fever_great,
    )
    deltas = np.asarray(plan.delta, dtype=np.float64)
    return {int(note): round(float(deltas[note]), 3) for note in np.flatnonzero(deltas)}
