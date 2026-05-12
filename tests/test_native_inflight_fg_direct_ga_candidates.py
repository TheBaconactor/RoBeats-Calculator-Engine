from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_types import make_native_song


def test_run_fg_job_sync_forwards_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator
    from gear_optimizer.solver import native_inflight_fg_pipeline as fg_pipeline

    calls: dict[str, object] = {}
    registry = object()

    def _fake_score_native_ga_force_greats(**kwargs):
        calls.update(kwargs)
        return [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ]

    monkeypatch.setattr(fg_pipeline, "score_native_ga_force_greats", _fake_score_native_ga_force_greats)

    song = make_native_song(
        fg_prep_future=None,
        loadout_entries={},
        db_loadouts_full=[],
        db_loadouts_future=None,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        ga_candidates=[
            {
                "BaseScore": 99,
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        registry=registry,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_candidate_limit=51,
        fg_direct_ga_candidates=True,
        manual_force_greats=False,
        force_greats_config=[],
        fg_search_radius=5,
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        use_evo_db=True,
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
    )

    orchestrator._run_fg_job_sync(song, gpu_client=SimpleNamespace())

    assert calls["ga_candidates"] is song.runtime.decode.ga_candidates
    assert calls["registry"] is registry
    assert calls["primary_color"] == "Rush"
    assert calls["secondary_color"] == "Flow"
    assert calls["default_selected_color"] == "Rush"
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130


def test_run_fg_job_sync_treats_exact_dp_config_as_finder(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator
    from gear_optimizer.solver import native_inflight_fg_pipeline as fg_pipeline

    calls: dict[str, object] = {}

    def _fake_score_native_ga_force_greats(**kwargs):
        calls.update(kwargs)
        return [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 140,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 2}}},
            }
        ]

    monkeypatch.setattr(fg_pipeline, "score_native_ga_force_greats", _fake_score_native_ga_force_greats)

    song = make_native_song(
        fg_prep_future=None,
        loadout_entries={},
        db_loadouts_full=[],
        db_loadouts_future=None,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        ga_candidates=[{"BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush", "fg_solver_mode": "exact_dp"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_candidate_limit=51,
        fg_direct_ga_candidates=False,
        manual_force_greats=False,
        force_greats_config=[],
        fg_search_radius=5,
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        use_evo_db=True,
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
        song_slot=9,
    )

    gpu_client = SimpleNamespace(name="gpu")
    orchestrator._run_fg_job_sync(song, gpu_client=gpu_client)

    assert calls["search_radius"] == 5
    assert calls["ga_candidates"] is None
    assert calls["registry"] is None
    assert calls["loadout_entries"] == {}
    assert calls["ref_arrays"] == {"Perfect Points": []}
    assert calls["default_selected_color"] == "Rush"
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 140
