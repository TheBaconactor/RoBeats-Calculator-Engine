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

    def _fake_get_best_loadouts(song_name, *, limit, gears_by_name, minis_by_name, team_buff="T5"):
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
        team_buff="T5",
        db_loadouts_full=None,
        allow_db_query=True,
        materialize_ga_details=True,
        ga_registry=None,
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


def test_prepare_fg_static_sync_builds_finder_entries_without_ga_candidates(monkeypatch):
    seen = {"ga_candidates": None}

    def _fake_build_loadout_entries(
        found_song_name,
        use_evo_db,
        ga_candidates,
        db_loadouts_limit,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        **_kwargs,
    ):
        seen["ga_candidates"] = list(ga_candidates or [])
        return {"db": {"score": 100}}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = SimpleNamespace(
        cfg=cfg,
        cfg_dict={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        db_loadouts_full=[{"score": 100}],
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        registry=None,
        loadout_entries=None,
    )

    stages._prepare_fg_static_sync(song)

    assert seen["ga_candidates"] == []
    assert song.loadout_entries == {"db": {"score": 100}}
    assert song.fg_direct_ga_candidates is True
    assert song._fg_static_prep_done is True


def test_prepare_fg_job_sync_reuses_static_finder_loadout_entries(monkeypatch):
    calls = {"build": 0}

    def _fake_build_loadout_entries(*_args, **_kwargs):
        calls["build"] += 1
        return {"rebuilt": True}

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
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-db-key",
        use_evo_db=True,
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
        loadout_entries={"static": {"score": 100}},
        fg_static_prep_future=None,
        _fg_static_prep_done=True,
    )

    stages._prepare_fg_job_sync(song, gpu_client=None)

    assert calls["build"] == 0
    assert song.loadout_entries == {"static": {"score": 100}}
    assert song.ga_candidates


def test_prepare_fg_job_sync_does_not_block_on_pending_static_future(monkeypatch):
    calls = {"static": 0, "build": 0}

    class _PendingFuture:
        def done(self):
            return False

        def result(self, *_args, **_kwargs):
            raise AssertionError("pending static future should not be awaited")

    def _fake_prepare_fg_static_sync(_song):
        calls["static"] += 1

    def _fake_build_loadout_entries(*_args, **_kwargs):
        calls["build"] += 1
        return {"rebuilt": True}

    monkeypatch.setattr(stages, "_prepare_fg_static_sync", _fake_prepare_fg_static_sync)
    monkeypatch.setattr(stages, "_maybe_prewarm_fg_chart_scorer", lambda _song: None)
    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)
    monkeypatch.setattr(stages, "select_fg_candidates", lambda candidates, **_kwargs: list(candidates or []))

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    pending_static = _PendingFuture()
    song = SimpleNamespace(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 1}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
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
        loadout_entries=None,
        fg_static_prep_future=pending_static,
        _fg_static_prep_done=False,
    )

    stages._prepare_fg_job_sync(song, gpu_client=None)

    assert calls["static"] == 0
    assert calls["build"] == 1
    assert song.fg_static_prep_future is pending_static


def test_decode_ga_payload_sync_attaches_base_hitsim_delta(monkeypatch):
    seen: dict[str, object] = {}

    def _fake_decode_gpu_native_ga_runs_payload(**_kwargs):
        return {"score": 123}, ["G1"], ["M1"], []

    def _fake_attach(best_data, calc_song, ref_arrays):
        seen["best_data"] = best_data
        seen["calc_song"] = calc_song
        seen["ref_arrays"] = ref_arrays
        best_data["hitsim_offset_deltas_ms"] = [1, 2, 3]

    monkeypatch.setattr(stages, "decode_gpu_native_ga_runs_payload", _fake_decode_gpu_native_ga_runs_payload)
    monkeypatch.setattr(stages, "_attach_hitsim_delta_for_base", _fake_attach)

    song = SimpleNamespace(
        registry=None,
        cfg_data={},
        fixed_stats={},
        calc_song={"metadata": {}},
        ref_arrays={"timeline": []},
    )

    best_data, best_gear, best_minis, ga_candidates = stages._decode_ga_payload_sync(song, runs_payload=None)

    assert best_data["hitsim_offset_deltas_ms"] == [1, 2, 3]
    assert best_gear == ["G1"]
    assert best_minis == ["M1"]
    assert ga_candidates == []
    assert seen["calc_song"] == song.calc_song
    assert seen["ref_arrays"] == song.ref_arrays
