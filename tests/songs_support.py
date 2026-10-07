"""Typed test songs: a Chart built straight from arrays (no file), timed like production."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.solver.timing_envelope import TimedSong, time_song


def make_chart(
    timestamps,
    *,
    note_types=None,
    lanes=None,
    name: str = "Test Song",
    difficulty: str = "Hard",
    primary: str = "Rush",
    secondary: str = "Flow",
    long_notes: int = 0,
    last_note_time: float | None = None,
    header: Mapping[str, str] | None = None,
) -> Chart:
    """Notes default to taps in distinct lanes; Last Note Time defaults to the last timestamp."""
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    lnt = float(ts[-1]) if last_note_time is None else float(last_note_time)
    return Chart(
        header={
            "Song Name": name,
            "Difficulty": difficulty,
            "Primary Color": primary,
            "Secondary Color": secondary,
            "Last Note Time": str(lnt),
            "Total Notes": str(n),
            "Long Notes": str(int(long_notes)),
            **(header or {}),
        },
        timestamps=ts,
        note_types=np.ones(n, np.int16) if note_types is None else np.asarray(note_types, dtype=np.int16),
        lanes=np.arange(n, dtype=np.int32) if lanes is None else np.asarray(lanes, dtype=np.int32),
        last_note_time=lnt,
        long_notes=int(long_notes),
    )


def make_song(timestamps, *, mode: str = "precise", **chart_fields) -> TimedSong:
    return time_song(make_chart(timestamps, **chart_fields), mode)
