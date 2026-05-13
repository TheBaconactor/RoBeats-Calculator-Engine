from __future__ import annotations

from concurrent.futures import Future

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT
from gear_optimizer.solver.native_inflight_persistence import InflightDBPersistence
from gear_optimizer.solver.native_inflight_types import make_native_song


def test_inflight_db_persistence_owns_default_candidate_limit():
    persistence = InflightDBPersistence(prefetch_workers=1)
    try:
        assert persistence.candidate_limit_default == FG_CANDIDATE_LIMIT
    finally:
        persistence.shutdown_prefetch(wait=True, cancel_futures=True)


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


def test_inflight_db_persistence_consumes_ready_prefetch_future():
    future = Future()
    future.set_result([{"score": 100}])
    song = make_native_song(db_loadouts_full=None, db_loadouts_future=future)

    assert InflightDBPersistence.consume_ready_prefetch(song) is True
    assert song.runtime.db.db_loadouts_full == [{"score": 100}]
    assert song.runtime.db.db_loadouts_future is None


def test_inflight_db_persistence_clears_unready_prefetch_future():
    future = Future()
    song = make_native_song(db_loadouts_full=None, db_loadouts_future=future)

    assert InflightDBPersistence.consume_ready_prefetch(song) is True
    assert future.cancelled() is True
    assert song.runtime.db.db_loadouts_full is None
    assert song.runtime.db.db_loadouts_future is None


def test_inflight_db_persistence_merges_prefetched_loadouts_once():
    song = make_native_song(
        loadout_entries={
            "ga": {
                "gear_names": ["G1"],
                "mini_names": ["M1"],
                "_source": "ga",
            }
        },
        db_loadouts_full=[
            {
                "gear_names": ["G2"],
                "mini_names": ["M2"],
                "_source": "db",
            }
        ],
    )

    assert InflightDBPersistence.merge_prefetched_loadouts(song) is True
    assert any(entry.get("_source") == "db" for entry in song.runtime.fg.loadout_entries.values())
    assert InflightDBPersistence.merge_prefetched_loadouts(song) is False


def test_inflight_db_persistence_materializes_loadout_entries_for_prefetched_rows():
    song = make_native_song(
        loadout_entries=None,
        db_loadouts_full=[
            {
                "gear_names": ["G2"],
                "mini_names": ["M2"],
                "_source": "db",
            }
        ],
    )

    assert InflightDBPersistence.merge_prefetched_loadouts(song) is True
    assert isinstance(song.runtime.fg.loadout_entries, dict)
    assert any(entry.get("_source") == "db" for entry in song.runtime.fg.loadout_entries.values())


def test_inflight_db_persistence_owns_fg_build_details_cache():
    song = make_native_song(
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        fg_build_details=None,
    )

    build_details = InflightDBPersistence.ensure_fg_build_details(song)

    assert callable(build_details)
    assert song.runtime.fg.fg_build_details is build_details
    assert InflightDBPersistence.ensure_fg_build_details(song) is build_details
