from gear_optimizer.solver.native_inflight_config import make_native_song

import pytest
import numpy as np


def test_nojit_fixed_stats_score_matches_jit_score():
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score, evaluate_stats_score_nojit

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 1,
            "Last Note Time": 1.5,
        },
        "song_data": {"timestamps": np.asarray([0.0, 0.25, 0.5, 1.0, 1.5], dtype=np.float32)},
    }
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }
    stats = {
        "Perfect Points": 37,
        "Combo Multiplier": 41,
        "Fever Multiplier": 59,
        "Fever Time": 23,
        "Fever Fill Rate": 29,
        "Rush": 101,
        "Flow": 83,
    }

    assert evaluate_stats_score_nojit(stats, calc_song, ref_arrays) == evaluate_stats_score(stats, calc_song, ref_arrays)


def test_process_force_greats_response_frontier_failure_raises_directly(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    def _boom(*_args, **_kwargs):
        raise RuntimeError("response frontier path failed")

    monkeypatch.setattr(adapter, "process_force_greats_response_frontier_gpu", _boom)

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

    with pytest.raises(RuntimeError, match="response frontier path failed"):
        force_greats.process_force_greats(
            loadout_entries={},
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={},
            meta_primary_color="Rush",
            ga_candidates=ga_candidates,
            ga_registry=_Registry(),
        )


def test_prepare_fg_job_sync_uses_db_only_entries_for_response_frontier_route(monkeypatch):
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


def test_prepare_fg_job_sync_canonicalizes_gpu_payload_before_response_frontier(monkeypatch):
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


def test_process_force_greats_forwards_direct_ga_candidates_to_response_frontier(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    seen: list[tuple[int, object]] = []
    registry = object()

    def _fake_response_frontier(
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

    monkeypatch.setattr(adapter, "process_force_greats_response_frontier_gpu", _fake_response_frontier)

    ga_candidates = [
        {
            "Gear": ["A"],
            "Minis": ["B"],
            "BaseScore": 90,
            "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        }
    ]

    out = force_greats.process_force_greats(
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


def test_response_frontier_cache_validation_rejects_legacy_modes():
    from gear_optimizer.helpers.song_helpers.force_greats.cache_validation import (
        is_cached_force_valid_for_response_frontier,
    )

    payload = {
        "Selected Element": "Rush",
        "ForceGreats": {
            "mode": "finder",
            "config": {"NonFever1": 1},
        },
    }

    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is False

    payload["ForceGreats"]["mode"] = "bellman"
    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is False

    payload["ForceGreats"]["mode"] = "response_frontier"
    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is True


def test_response_frontier_ftff_antichain_prunes_only_same_pack_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
        _prune_dominated_ftff_response_pairs,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    dominated_same_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_a, 0.0, 0.0)
    dominator_same_pack = (0, 2, 11, {"Rush": 50, "Flow": 21}, pack_a, 0.0, 0.0)
    same_stats_other_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_b, 0.0, 0.0)

    kept = _prune_dominated_ftff_response_pairs(
        [dominated_same_pack, dominator_same_pack, same_stats_other_pack],
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert any(pair is dominator_same_pack for pair in kept)
    assert any(pair is same_stats_other_pack for pair in kept)
    assert not any(pair is dominated_same_pack for pair in kept)


def test_response_frontier_ftff_antichain_matches_naive_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
        _prune_dominated_ftff_response_pairs,
        _response_pair_dominates,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    pairs = []
    for frontier_obj in (pack_a, pack_b):
        for residual in (7, 8, 9):
            for rush in (10, 12, 12):
                for flow in (4, 5, 7):
                    pairs.append((0, 0, residual, {"Rush": rush, "Flow": flow}, frontier_obj, 0.0, 0.0))

    naive = []
    for pair in pairs:
        if any(
            _response_pair_dominates(other, pair, primary_color="Rush", secondary_color="Flow")
            for other in naive
        ):
            continue
        naive = [
            other
            for other in naive
            if not _response_pair_dominates(pair, other, primary_color="Rush", secondary_color="Flow")
        ]
        naive.append(pair)

    kept = _prune_dominated_ftff_response_pairs(pairs, primary_color="Rush", secondary_color="Flow")

    assert kept == naive


def test_process_force_greats_uses_shared_response_frontier_solver(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls = []

    def _result(base_stats, selected_color):
        surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        frontier = FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )
        inner = FgResponseInnerResult(
            best_score=150,
            surface_index=0,
            g_pp=1,
            g_cm=2,
            g_fm=3,
            g_ov=4,
            final_pp=11,
            final_cm=12,
            final_fm=13,
            final_primary=14,
            final_secondary=15,
        )
        return FgResponseFrontierSolveResult(
            best_score=150,
            ft=6,
            ff=7,
            gem_counts={"Perfect Points": 1, "Combo Multiplier": 2, "Fever Multiplier": 3, "Element": 4},
            stats={**base_stats, "Fever Time": 6, "Fever Fill Rate": 7},
            surface=surface,
            frontier=frontier,
            inner=inner,
            seconds=0.0,
            forced_counts=(5, 0),
        )

    def _fake_response_frontier_many(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        calls.append((list(base_stats_list), selected_color, calc_song, ref_arrays))
        return [_result(base_stats, selected_color) for base_stats in base_stats_list]

    monkeypatch.setattr(adapter, "extract_fg_song_inputs", lambda _song: SimpleNamespace(total_notes=2))
    monkeypatch.setattr(adapter, "solve_force_greats_response_frontier_many_gpu", _fake_response_frontier_many)
    monkeypatch.setattr(adapter, "evaluate_stats_score", lambda *_args, **_kwargs: 100)

    out = adapter.process_force_greats_response_frontier_gpu(
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

    assert len(calls) == 1
    assert len(calls[0][0]) == 1
    assert calls[0][1] == "Rush"
    assert len(out) == 1
    assert out[0]["fg_score"] == 150
    assert out[0]["base_score"] == 100
    assert out[0]["data"]["FT"] == 6
    assert out[0]["data"]["FF"] == 7
    assert out[0]["data"]["GemCounts"]["Element"] == 4
    assert out[0]["data"]["ForceGreats"]["mode"] == "response_frontier"
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 5, "NonFever2": 0}
    assert out[0]["gear"] == ["G1"]
    assert out[0]["minis"] == ["M1"]


def test_process_force_greats_batches_response_frontier_candidates(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls: list[int] = []

    def _fake_response_frontier_many(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        _ = (calc_song, ref_arrays, selected_color)
        calls.append(len(base_stats_list))
        out = []
        for idx, base_stats in enumerate(base_stats_list):
            surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, idx, 0)
            frontier = FgResponseFrontierResult(
                first_frontier=(surface,),
                state_frontiers={},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=5,
                seconds=0.0,
            )
            inner = FgResponseInnerResult(
                best_score=200 + idx,
                surface_index=0,
                g_pp=0,
                g_cm=0,
                g_fm=0,
                g_ov=1,
                final_pp=0,
                final_cm=0,
                final_fm=0,
                final_primary=0,
                final_secondary=0,
            )
            out.append(
                FgResponseFrontierSolveResult(
                    best_score=200 + idx,
                    ft=0,
                    ff=0,
                    gem_counts={"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    stats={**base_stats, "Rush": int(base_stats.get("Rush", 0) or 0) + 1},
                    surface=surface,
                    frontier=frontier,
                    inner=inner,
                    seconds=0.0,
                    forced_counts=(5, 0),
                )
            )
        return out

    monkeypatch.setattr(adapter, "extract_fg_song_inputs", lambda _song: SimpleNamespace(total_notes=2))
    monkeypatch.setattr(adapter, "solve_force_greats_response_frontier_many_gpu", _fake_response_frontier_many)
    monkeypatch.setattr(adapter, "evaluate_stats_score", lambda *_args, **_kwargs: 100)

    out = adapter.process_force_greats_response_frontier_gpu(
        {},
        {"metadata": {}, "song_data": {}},
        {},
        "Rush",
        ga_candidates=[
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 10}, "Selected Element": "Rush"},
            },
            {
                "BaseScore": 101,
                "Gear": ["G2"],
                "Minis": ["M2"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 11}, "Selected Element": "Rush"},
            },
        ],
    )

    assert calls == [2]
    assert [row["fg_score"] for row in out] == [201, 200]
