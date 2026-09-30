from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gear_optimizer.chart import load_chart
from gear_optimizer.gamedata import Mini, SongMini, song_minis
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver.song_db_context import PreparedSongDbContext, load_prepared_song_db_context
from gear_optimizer.solver.timing_envelope import TimedSong, time_song

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedSongCore:
    song: TimedSong
    fixed_stats: dict[str, int]
    db_context: PreparedSongDbContext
    # Every mini as this song sees it, in Minis.csv order.
    minis: list[SongMini]
    setup_sec: float
    db_load_sec: float


def prepare_song(fp: str) -> TimedSong:
    """The chart at ``fp`` in its default timing model (its Timing Mode header, else perfect_window)."""
    return time_song(load_chart(Path(fp)))


def build_prepared_song_core(
    *,
    fp: str,
    found_song_name: str,
    minis: Mapping[str, Mini],
    cache_db_context: bool = False,
) -> PreparedSongCore:
    song = prepare_song(fp)
    minis_in_song = song_minis(minis.values(), found_song_name, song.chart.primary, song.chart.secondary)

    t_setup0 = time.perf_counter()
    fixed_stats = baseline_fixed_stats(song.chart)
    setup_sec = time.perf_counter() - t_setup0

    t_db0 = time.perf_counter()
    db_context = load_prepared_song_db_context(
        found_song_name=found_song_name,
        cache_db_context=bool(cache_db_context),
    )
    db_load_sec = time.perf_counter() - t_db0

    return PreparedSongCore(
        song=song,
        fixed_stats=fixed_stats,
        db_context=db_context,
        minis=minis_in_song,
        setup_sec=float(setup_sec),
        db_load_sec=float(db_load_sec),
    )
