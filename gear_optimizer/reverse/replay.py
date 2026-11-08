"""A named set's play as the song page plays it: the hit offsets that give the row's score.

A lookup's set gives the score on a response surface, its fever and Greats. The song page plans a build's run from the section
trace whose edges add up to its surface (trace.reconstruct), in the timing mode it shows: a surface without Greats as it plans a
Meta build, one with Greats as it plans a Force Great build. The trace is checked against a physical replay at the build's
windows (trace.physical_replay), then gives its notes' hit offsets (trace.note_graph). So a set that is a stored build, at the
build's own score, plays the build's own run, and the page shows the build's own frame guarantee for it.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import perfect_time_of
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.score import HEAD_NOTES
from gear_optimizer.solver.timing_envelope import fever_axes, fever_fill_denominators, time_song
from gear_optimizer.trace.note_graph import force_greats_plan, reconcile_force_greats_plan, timeline_frontier_plan
from gear_optimizer.trace.physical_replay import validate_base_physical_replay, validate_force_greats_physical_replay
from gear_optimizer.trace.reconstruct import UnplayableTrace, reconstruct_base_trace, reconstruct_force_greats_response_trace


def play_offsets(chart, curves, gears, set_gear: tuple[str, ...], stats: dict[str, int], surface: FgResponseSurface, mode: str) -> dict[int, float] | None:
    """Per note off its chart time, its hit offset in ms in the play behind a set's score, planned in timing mode `mode`; None
    when no trace plays the surface in that mode (the lookup's walk reaches a little past what the planners plan)."""
    inputs = time_song(chart, mode).fg_inputs
    real_time_by_ft, raw_fill_by_ff = fever_axes(inputs.total_notes, inputs.long_notes, inputs.last_note_time, curves)
    ft, ff = min(stats["Fever Time"], MAX_STAT), min(stats["Fever Fill Rate"], MAX_STAT)
    raw_fill, real_time = float(raw_fill_by_ff[ff]), float(real_time_by_ft[ft])
    denominator = float(fever_fill_denominators(int(inputs.total_notes) - int(inputs.long_notes), curves.f64["Fever Fill Rate"][ff]))
    notes = dict(timestamps=chart.timestamps, note_types=chart.note_types, lanes=chart.lanes, timing_mode=mode, perfect_time=perfect_time_of(set_gear, gears))
    head = (surface.fever0, surface.fever1, surface.fever2, surface.fever3)
    try:
        if surface.body_great == 0 and not any((surface.great0, surface.great1, surface.great2, surface.great3)):
            trace = reconstruct_base_trace(inputs, head_words=head, body_fever=surface.body_fever, raw_fever_fill=raw_fill, real_fever_time=real_time)
            response = [*head, surface.body_fever, max(0, chart.total_notes - HEAD_NOTES) - surface.body_fever]
            validate_base_physical_replay(frontier_trace=trace, response_surface=response, fever_fill_denominator=denominator, fever_duration_ms=real_time * 1000.0, **notes)
            plan = timeline_frontier_plan(frontier_trace=trace, total_notes=chart.total_notes, **notes)
        else:
            trace = reconstruct_force_greats_response_trace(
                inputs=inputs, non_fever_base=int(ceil(raw_fill)), target_surface=surface, raw_fever_fill=raw_fill, real_fever_time=real_time,
            )
            validate_force_greats_physical_replay(
                frontier_trace=trace, surface=surface, fever_fill_denominator=denominator, real_fever_time=real_time, **{**notes, "lanes": inputs.lanes, "timestamps": inputs.timestamps},
            )
            plan = force_greats_plan(frontier_trace=trace, total_notes=chart.total_notes, **notes)
            reconcile_force_greats_plan(
                plan, fever_words=surface[0:4], great_words=surface[4:8], body_fever=surface.body_fever, body_great=surface.body_great,
                body_fever_great=surface.body_fever_great,
            )
    except (UnplayableTrace, ValueError):
        return None
    deltas = np.asarray(plan.delta, dtype=np.float64)
    return {int(note): round(float(deltas[note]), 3) for note in np.flatnonzero(deltas)}
