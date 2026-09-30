"""The deterministic fever timeline of play at fixed hit times (Non-Precise / zero_ms, or chart + offset).

The fever bar fills after `fill` scored notes: ceil((notes - long notes) x 0.333 x the Fever Fill Rate
factor). The note that fills it is the first fever note, and the first section needs one note less
because the fill is applied before the note is scored. Fever lasts (last note time x 0.15 + 0.15) x the
Fever Time factor seconds; the note where it ends is scored outside fever without adding fill.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from .rules import FEVER_FILL_PER_NOTE, FEVER_TIME_OFFSET, FEVER_TIME_PER_SECOND
from .score import HEAD_NOTES, TimelineCell, single_surface_cell


def fever_fill_notes(total_notes: int, long_notes: int, fill_factor: float) -> int:
    return ceil((total_notes - long_notes) * FEVER_FILL_PER_NOTE * fill_factor)


def fever_duration(last_note_time: float, time_factor: float) -> float:
    return (last_note_time * FEVER_TIME_PER_SECOND + FEVER_TIME_OFFSET) * time_factor


def fixed_timeline_cell(
    hit_times: np.ndarray, *, long_notes: int, last_note_time: float, fill_factor: float, time_factor: float
) -> TimelineCell:
    """The single timing surface of play at `hit_times` (float32, non-decreasing), as a TimelineCell.

    `long_notes` and `last_note_time` are the chart's (the hit offsets shift play, not the song).
    """
    total = int(hit_times.shape[0])
    fill = fever_fill_notes(total, long_notes, fill_factor)
    duration = fever_duration(last_note_time, time_factor)
    in_fever = np.zeros(total, dtype=np.bool_)
    index = fill - 1
    while 0 < index < total:
        end = np.float32(float(hit_times[index]) + duration)
        stop = int(np.searchsorted(hit_times, end, side="left"))
        in_fever[index:stop] = True
        index = stop + fill

    body_fever = int(in_fever[HEAD_NOTES:].sum())
    return single_surface_cell(in_fever[:HEAD_NOTES], body_fever, max(0, total - HEAD_NOTES) - body_fever)
