from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gear_optimizer.chart import load_chart
from gear_optimizer.data.mini_ascension import MiniAscensionSongContext, materialize_minis_for_song
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver.song_db_context import PreparedSongDbContext, load_prepared_song_db_context
from gear_optimizer.solver.timing_envelope import TimedSong, time_song

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedSongCore:
    song: TimedSong
    fixed_stats: dict[str, int]
    db_context: PreparedSongDbContext
    all_minis: list[dict[str, Any]]
    minis_by_name: dict[str, dict[str, Any]]
    mini_ascension_context: MiniAscensionSongContext
    setup_sec: float
    db_load_sec: float


def prepare_song(fp: str) -> TimedSong:
    """The chart at ``fp`` in its default timing model (its Timing Mode header, else perfect_window)."""
    return time_song(load_chart(Path(fp)))


def build_prepared_song_core(
    *,
    fp: str,
    found_song_name: str,
    gears_by_name: dict,
    minis_by_name: dict,
    all_minis: list[dict] | None = None,
    cache_db_context: bool = False,
) -> PreparedSongCore:
    song = prepare_song(fp)
    materialized_minis, materialized_minis_by_name, mini_ascension_context = materialize_minis_for_song(
        all_minis=all_minis,
        minis_by_name=minis_by_name,
        chart=song.chart,
        song_name=found_song_name,
    )

    t_setup0 = time.perf_counter()
    fixed_stats = baseline_fixed_stats(song.chart)
    setup_sec = time.perf_counter() - t_setup0

    t_db0 = time.perf_counter()
    db_context = load_prepared_song_db_context(
        found_song_name=found_song_name,
        gears_by_name=gears_by_name,
        minis_by_name=materialized_minis_by_name,
        cache_db_context=bool(cache_db_context),
    )
    db_load_sec = time.perf_counter() - t_db0

    return PreparedSongCore(
        song=song,
        fixed_stats=fixed_stats,
        db_context=db_context,
        all_minis=materialized_minis,
        minis_by_name=materialized_minis_by_name,
        mini_ascension_context=mini_ascension_context,
        setup_sec=float(setup_sec),
        db_load_sec=float(db_load_sec),
    )
