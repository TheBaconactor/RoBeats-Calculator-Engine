from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "FGSongInputs",
]


@dataclass(frozen=True, slots=True)
class FGSongInputs:
    timestamps: Any
    perfect_candidates: Any
    great_candidates: Any
    perfect_floor: Any
    great_floor: Any
    lanes: Any
    use_forced_great_timing: bool
    total_notes: int
    long_notes: int
    last_note_time: float
    primary_color: str
    secondary_color: str


def fg_song_inputs(song) -> FGSongInputs:
    """The FG solver's view of a TimedSong.

    perfect_window carries the Perfect/Great candidate and floor envelopes (carry-aware FG); zero_ms
    scores every activation and boundary at the hit timeline and has no forced-Great carry.
    """
    chart = song.chart
    hits = song.hit_timestamps
    enveloped = song.mode == "perfect_window"
    return FGSongInputs(
        timestamps=hits,
        perfect_candidates=song.perfect_candidates if enveloped else hits,
        great_candidates=song.great_candidates if enveloped else hits,
        perfect_floor=song.perfect_floor if enveloped else hits,
        great_floor=song.great_floor if enveloped else hits,
        lanes=chart.lanes,
        use_forced_great_timing=enveloped,
        total_notes=chart.total_notes,
        long_notes=chart.long_notes,
        last_note_time=chart.last_note_time,
        primary_color=chart.primary,
        secondary_color=chart.secondary,
    )
