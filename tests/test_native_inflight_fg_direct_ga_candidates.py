from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_config import make_native_song


def test_run_fg_job_sync_forwards_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    calls: dict[str, object] = {}
    registry = object()

    def _fake_process_force_greats(*args, **kwargs):
        calls["args"] = args
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

    monkeypatch.setattr(fg_pipeline, "process_force_greats", _fake_process_force_greats)

    song = make_native_song(
        fg_prep_future=None,
        loadout_entries={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
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
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=SimpleNamespace())

    assert calls["args"][0] == {}
    assert calls["ga_candidates"] is song.runtime.decode.ga_candidates
    assert calls["ga_registry"] is registry
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130


def test_run_fg_job_sync_uses_bellman_entry_for_non_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    calls: dict[str, object] = {}

    def _fake_process_force_greats(*args, **kwargs):
        calls["args"] = args
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

    monkeypatch.setattr(fg_pipeline, "process_force_greats", _fake_process_force_greats)

    song = make_native_song(
        fg_prep_future=None,
        loadout_entries={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[{"BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_candidate_limit=51,
        fg_direct_ga_candidates=False,
        manual_force_greats=False,
        force_greats_config=[],
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
        song_slot=9,
    )

    gpu_client = SimpleNamespace(name="gpu")
    fg_pipeline.run_fg_job_sync(song, gpu_client=gpu_client)

    assert calls["args"][0] == {}
    assert calls["args"][2] == {"Perfect Points": []}
    assert calls["ga_candidates"] is None
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 140
