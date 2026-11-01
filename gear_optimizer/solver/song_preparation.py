from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gear_optimizer.chart import load_chart
from gear_optimizer.gamedata import Mini, SongMini, song_minis
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver.timing_envelope import TimedSong, time_song


@dataclass(frozen=True, slots=True)
class PreparedSongCore:
    song: TimedSong
    fixed_stats: dict[str, int]
    # Every mini as this song sees it, in Minis.csv order.
    minis: list[SongMini]


def build_prepared_song_core(
    *,
    fp: str,
    found_song_name: str,
    mode: str,
    minis: Mapping[str, Mini],
) -> PreparedSongCore:
    song = time_song(load_chart(Path(fp)), mode)
    minis_in_song = song_minis(minis.values(), found_song_name, song.chart.primary, song.chart.secondary)
    return PreparedSongCore(song=song, fixed_stats=baseline_fixed_stats(song.chart), minis=minis_in_song)
