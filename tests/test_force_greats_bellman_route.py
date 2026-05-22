from gear_optimizer.solver.native_inflight_config import make_native_song

import pytest


def test_process_force_greats_bellman_failure_raises_directly(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import core

    def _boom(*_args, **_kwargs):
        raise RuntimeError("bellman path failed")

    monkeypatch.setattr(core, "process_force_greats_bellman_fixed_gpu", _boom)

    class _Registry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    ga_candidates = [
        {
            "BaseScore": 321,
            "GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 8, 7],
            "Data": {
                "BaseStats": {"Perfect Points": 5, "Rush": 7},
                "GemCounts": {"Perfect Points": 1},
                "FT": 1,
                "FF": 2,
                "Selected Element": "Rush",
            },
        }
    ]

    with pytest.raises(RuntimeError, match="bellman path failed"):
        core.process_force_greats(
            loadout_entries={},
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={},
            meta_primary_color="Rush",
            ga_candidates=ga_candidates,
            ga_registry=_Registry(),
        )


def test_prepare_fg_job_sync_uses_db_only_entries_for_bellman_route(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages

    seen = {"ga_n": None}

    def _fake_build_loadout_entries(
        found_song_name,
        ga_candidates,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        team_buff="T5",
        materialize_ga_details=True,
        ga_registry=None,
    ):
        seen["ga_n"] = len(ga_candidates or [])
        return {}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen["ga_n"] == 0
    assert song.runtime.fg.fg_direct_ga_candidates is True
    assert len(song.runtime.decode.ga_candidates or []) == 1


def test_prepare_fg_job_sync_canonicalizes_gpu_payload_before_bellman(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *args, **kwargs: {})

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    duplicate_prefix = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": ["DupG1", "DupG2", "DupG3", "DupG4", "DupG5", "DupG6"],
            "Minis": ["DupM1", "DupM2", "DupM3"],
            "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": i, "Selected Element": "Rush"},
        }
        for i in range(60)
    ]
    keeper = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["KeepG1", "KeepG2", "KeepG3", "KeepG4", "KeepG5", "KeepG6"],
        "Minis": ["KeepM1", "KeepM2", "KeepM3"],
        "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": 60, "Selected Element": "Rush"},
    }

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=duplicate_prefix + [keeper],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    selected = song.runtime.decode.ga_candidates or []
    assert len(selected) == 2
    assert any((cand.get("Gear") or [None])[0] == "KeepG1" for cand in selected)


def test_process_force_greats_forwards_direct_ga_candidates_to_bellman(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import core

    seen: list[tuple[int, object]] = []
    registry = object()

    def _fake_bellman(
        loadout_entries,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_candidates=None,
        ga_registry=None,
    ):
        _ = (
            loadout_entries,
            calc_song,
            ref_arrays,
            meta_primary_color,
            ga_registry,
        )
        seen.append((len(list(ga_candidates or [])), ga_registry))
        return [
            {
                "data": {
                    "Score": 100 + len(seen),
                    "BaseScore": 90,
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
                "gear": [f"G{len(seen)}"],
                "minis": [f"M{len(seen)}"],
                "score": 90,
                "fg_score": 100 + len(seen),
            }
        ]

    monkeypatch.setattr(core, "process_force_greats_bellman_fixed_gpu", _fake_bellman)

    ga_candidates = [
        {
            "Gear": ["A"],
            "Minis": ["B"],
            "BaseScore": 90,
            "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        }
    ]

    out = core.process_force_greats(
        loadout_entries={},
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        ga_candidates=ga_candidates,
        ga_registry=registry,
    )

    assert seen == [(1, registry)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 101


def test_bellman_cache_validation_rejects_legacy_finder_mode():
    from gear_optimizer.helpers.song_helpers.force_greats.cache_validation import is_cached_force_valid_for_bellman

    payload = {
        "Selected Element": "Rush",
        "ForceGreats": {
            "mode": "finder",
            "config": {"NonFever1": 1},
        },
    }

    assert is_cached_force_valid_for_bellman(payload, "Rush", 0, 0) is False


def test_process_force_greats_expands_overflow_to_fever_fill_for_bellman(monkeypatch):
    import numpy as np
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import bellman_fixed_adapter as adapter

    def _fake_surfaces(stats, calc_song, ref_arrays):
        fill = int((stats or {}).get("Fever Fill Rate", 0) or 0)
        song_inputs = SimpleNamespace(
            timestamps=np.asarray([0.0, 1.0], dtype=np.float32),
            great_candidates=np.asarray([0.0, 1.0], dtype=np.float32),
            use_forced_great_timing=False,
        )
        return (
            song_inputs,
            np.asarray([1, 1], dtype=np.int32),
            np.asarray([2, 2], dtype=np.int32),
            np.asarray([0, 0, 0], dtype=np.int64),
            float(fill),
            2,
            1.0,
        )

    def _fake_bellman(*, raw_fever_fill, **_kwargs):
        if int(raw_fever_fill) >= 3:
            return SimpleNamespace(best_score=150, best_forced_counts=(5, 0))
        return SimpleNamespace(best_score=100, best_forced_counts=(0, 0))

    monkeypatch.setattr(adapter, "_fixed_note_surfaces", _fake_surfaces)
    monkeypatch.setattr(adapter, "solve_force_greats_bellman_fixed_stats_gpu", _fake_bellman)
    monkeypatch.setattr(adapter, "evaluate_stats_score", lambda *_args, **_kwargs: 100)

    out = adapter.process_force_greats_bellman_fixed_gpu(
        {},
        {"metadata": {}, "song_data": {}},
        {},
        "Rush",
        ga_candidates=[
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {
                    "BaseStats": {
                        "Perfect Points": 0,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Fever Time": 0,
                        "Fever Fill Rate": 0,
                        "Rush": 10,
                    },
                    "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    "FT": 0,
                    "FF": 0,
                    "Selected Element": "Rush",
                },
            }
        ],
    )

    assert len(out) == 1
    assert out[0]["fg_score"] == 150
    assert out[0]["base_score"] == 100
    assert out[0]["data"]["FF"] == 1
    assert out[0]["data"]["GemCounts"]["Element"] == 0
    assert out[0]["data"]["ForceGreats"]["mode"] == "bellman"
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 5, "NonFever2": 0}
    assert out[0]["gear"] == ["G1"]
    assert out[0]["minis"] == ["M1"]
