from __future__ import annotations

from gear_optimizer.solver.native_inflight_persistence import InflightDBPersistence
from gear_optimizer.solver.native_inflight_types import make_native_song


def test_inflight_db_persistence_owns_prefetch_executor_submission():
    persistence = InflightDBPersistence(candidate_limit_default=99, prefetch_workers=2)
    try:
        song = make_native_song(
            task_key="song-a",
            song_name="Song A",
            db_key="song-a-db",
            manual_force_greats=True,
            use_evo_db=True,
            cfg_data={"fg_candidate_limit": "7"},
            cfg_dict={
                "IterationEngine": {"AutoSelectBuffAndColor": "False"},
                "TeamContributionBuffConstant": {"TeamBuff": "T20"},
            },
            gears_by_name={"gear": object()},
            minis_by_name={"mini": object()},
        )
        registered = []

        def _prefetch(db_key, *, limit, gears_by_name, minis_by_name, team_buff):
            return {
                "db_key": db_key,
                "limit": limit,
                "gears": tuple(gears_by_name),
                "minis": tuple(minis_by_name),
                "team_buff": team_buff,
            }

        assert persistence.maybe_submit_prefetch(song, _prefetch, register_future=registered.append) is True
        assert len(registered) == 1
        assert song.runtime.db.db_loadouts_future is registered[0]
        assert registered[0].result(timeout=2) == {
            "db_key": "song-a-db",
            "limit": 7,
            "gears": ("gear",),
            "minis": ("mini",),
            "team_buff": "T20",
        }
    finally:
        persistence.shutdown_prefetch(wait=True, cancel_futures=True)


def test_inflight_db_persistence_prefetch_guards_and_submit_failure_cleanup():
    persistence = InflightDBPersistence(candidate_limit_default=99, prefetch_workers=1)
    try:
        disabled = make_native_song(
            task_key="disabled",
            song_name="Disabled",
            db_key="disabled-db",
            manual_force_greats=False,
            force_greats_finder=False,
            use_evo_db=True,
        )
        assert persistence.maybe_submit_prefetch(disabled, lambda *_args, **_kwargs: [], register_future=lambda _future: None) is False
        assert disabled.runtime.db.db_loadouts_future is None

        persistence.shutdown_prefetch(wait=True, cancel_futures=True)

        song = make_native_song(
            task_key="song-b",
            song_name="Song B",
            db_key="song-b-db",
            manual_force_greats=True,
            use_evo_db=True,
        )
        assert persistence.maybe_submit_prefetch(song, lambda *_args, **_kwargs: [], register_future=lambda _future: None) is False
        assert song.runtime.db.db_loadouts_future is None
    finally:
        persistence.shutdown_prefetch(wait=True, cancel_futures=True)
