import concurrent.futures
import configparser
from types import SimpleNamespace

import gear_optimizer.solver.native_inflight_stages as stages


def _clear_fg_db_prefetch_cache() -> None:
    with stages._FG_DB_LOADOUTS_CACHE_LOCK:
        stages._FG_DB_LOADOUTS_CACHE.clear()


def test_prefetch_db_loadouts_sync_uses_song_key_cache(monkeypatch):
    _clear_fg_db_prefetch_cache()
    monkeypatch.setenv("INFLIGHT_FG_DB_CACHE_MAX", "16")

    calls = {"n": 0}

    def _fake_get_best_loadouts(song_name, *, limit, gears_by_name, minis_by_name):
        calls["n"] += 1
        return [
            {
                "gear": [f"{song_name}-gear"],
                "minis": [f"{song_name}-mini"],
                "score": int(limit),
            }
        ]

    import gear_optimizer.data.database as db

    monkeypatch.setattr(db, "get_best_loadouts", _fake_get_best_loadouts)

    a = stages._prefetch_db_loadouts_sync("song-a", limit=51, gears_by_name={}, minis_by_name={})
    b = stages._prefetch_db_loadouts_sync("song-a", limit=51, gears_by_name={}, minis_by_name={})

    assert calls["n"] == 1
    assert isinstance(a, list) and isinstance(b, list)
    assert a == b


def test_prepare_fg_job_sync_disables_sync_db_query_while_prefetch_pending(monkeypatch):
    pending = concurrent.futures.Future()
    seen = {"allow_db_query": None}

    def _fake_build_loadout_entries(
        found_song_name,
        use_evo_db,
        ga_candidates,
        db_loadouts_limit,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        db_loadouts_full=None,
        allow_db_query=True,
    ):
        seen["allow_db_query"] = bool(allow_db_query)
        return {}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = SimpleNamespace(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                "Minis": ["M1", "M2", "M3"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=pending,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=False,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages._prepare_fg_job_sync(song, gpu_client=None)

    assert seen["allow_db_query"] is False
    # Keep the future attached so FG run can consume it later if it completes.
    assert song.db_loadouts_future is pending
