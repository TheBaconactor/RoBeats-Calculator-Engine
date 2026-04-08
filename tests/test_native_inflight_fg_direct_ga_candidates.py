from types import SimpleNamespace


def test_run_fg_job_sync_forwards_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator

    calls: dict[str, object] = {}
    registry = object()

    def _fake_process_force_greats(
        loadout_entries,
        manual_force_greats,
        force_greats_finder,
        force_greats_config,
        calc_song,
        ref_arrays,
        meta_primary_color,
        build_details_fn,
        **kwargs,
    ):
        calls["loadout_entries"] = loadout_entries
        calls["manual_force_greats"] = manual_force_greats
        calls["force_greats_finder"] = force_greats_finder
        calls["force_greats_config"] = force_greats_config
        calls["calc_song"] = calc_song
        calls["ref_arrays"] = ref_arrays
        calls["meta_primary_color"] = meta_primary_color
        calls["ga_candidates"] = kwargs.get("ga_candidates")
        calls["ga_registry"] = kwargs.get("ga_registry")
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

    def _fake_attach(fg_variants, calc_song, ref_arrays):
        calls["attach"] = {
            "fg_variants": list(fg_variants or []),
            "calc_song": calc_song,
            "ref_arrays": ref_arrays,
        }

    monkeypatch.setattr(orchestrator, "process_force_greats", _fake_process_force_greats)
    monkeypatch.setattr(orchestrator, "_attach_hitsim_delta_for_fg_variant", _fake_attach)

    song = SimpleNamespace(
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
        fg_combo_job=None,
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

    assert calls["ga_candidates"] is song.ga_candidates
    assert calls["ga_registry"] is registry
    assert song.fg_variants == calls["attach"]["fg_variants"]
    assert int(song.fg_variants[0]["fg_score"]) == 130


def test_run_fg_job_sync_routes_exact_dp_with_gpu_client(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator

    calls: dict[str, object] = {}

    def _fake_process_fg_exact_dp(ga_candidates, calc_song, ref_arrays, **kwargs):
        calls["ga_candidates"] = list(ga_candidates or [])
        calls["calc_song"] = calc_song
        calls["ref_arrays"] = ref_arrays
        calls["kwargs"] = dict(kwargs)
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

    def _fake_attach(fg_variants, calc_song, ref_arrays):
        calls["attach"] = {
            "fg_variants": list(fg_variants or []),
            "calc_song": calc_song,
            "ref_arrays": ref_arrays,
        }

    monkeypatch.setattr("gear_optimizer.solver.fused_exact.process_fg_exact_dp", _fake_process_fg_exact_dp)
    monkeypatch.setattr(orchestrator, "_attach_hitsim_delta_for_fg_variant", _fake_attach)

    song = SimpleNamespace(
        fg_prep_future=None,
        loadout_entries={},
        db_loadouts_full=[],
        db_loadouts_future=None,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        force_greats_finder=True,
        ga_candidates=[{"BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        fg_combo_job=None,
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

    assert calls["kwargs"]["use_gpu"] is True
    assert calls["kwargs"]["gpu_client"] is gpu_client
    assert calls["kwargs"]["song_slot"] == 9
    assert song.fg_variants == calls["attach"]["fg_variants"]
    assert int(song.fg_variants[0]["fg_score"]) == 140
