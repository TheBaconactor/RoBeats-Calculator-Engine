"""A queued solve: one run of one song in one timing mode (each SongRepeats run is a task of its own)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from gear_optimizer.gamedata import Gear, Mini, StatCurves


@dataclass(frozen=True, slots=True)
class SharedRunContext:
    """What every task of a run shares."""

    multi_start: int
    curves: StatCurves
    # Gears.csv / Minis.csv by name, in file order.
    gears: Mapping[str, Gear]
    minis: Mapping[str, Mini]
    ga_depth: int


@dataclass(frozen=True, slots=True)
class SongTask:
    file_path: str
    song_name: str
    mode: str  # the timing mode it is solved in (core.timing_modes)
    context: SharedRunContext
    ga_seed: int | None = None
    repeat_index: int = 0  # the run number (1-based) of a song solved repeat_total times
    repeat_total: int = 0

    @property
    def label(self) -> str:
        """The task's queue label: the song name and timing mode, with its run number when the song repeats."""
        if not self.song_name:
            return "Unknown"
        if self.repeat_index > 0 and self.repeat_total > 1:
            return f"{self.song_name} ({self.mode}, Run {self.repeat_index}/{self.repeat_total})"
        return f"{self.song_name} ({self.mode})"
