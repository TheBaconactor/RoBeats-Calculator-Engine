from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver import native_inflight_stages
from gear_optimizer.solver import hit_simulation


def test_decode_ga_payload_sync_passes_candidate_pool_to_hitsim_refine(monkeypatch) -> None:
    best_data = {"Score": 100, "BaseScore": 100, "Stats": {"Perfect Points": 1}}
    ga_candidates = [
        {
            "Score": 95,
            "BaseScore": 95,
            "Data": {"Score": 95, "BaseScore": 95, "Stats": {"Perfect Points": 2}},
        }
    ]
    seen: dict[str, object] = {}

    def fake_decode_gpu_native_ga_runs_payload(**kwargs):
        return best_data, ["Gear"], ["Mini"], ga_candidates

    def fake_refine_human_hit_sim_after_ga(*args, **kwargs):
        seen["candidate_pool"] = kwargs.get("candidate_pool")
        return None

    monkeypatch.setattr(
        native_inflight_stages,
        "decode_gpu_native_ga_runs_payload",
        fake_decode_gpu_native_ga_runs_payload,
    )
    monkeypatch.setattr(
        hit_simulation,
        "refine_human_hit_sim_after_ga",
        fake_refine_human_hit_sim_after_ga,
    )

    song = SimpleNamespace(
        registry=None,
        cfg_data={"fg_candidate_limit": 51},
        fixed_stats={},
        cfg_dict={"HumanHitSim": {"RefineAfterGA": "true"}},
        calc_song={},
        ref_arrays={},
        ga_seed=123,
    )

    native_inflight_stages._decode_ga_payload_sync(song, np.zeros((1, 1, 1), dtype=np.int32))

    assert seen["candidate_pool"] is ga_candidates


def test_decode_ga_payload_sync_merges_hitsim_candidates_and_updates_selected_winner(monkeypatch) -> None:
    best_data = {"Score": 100, "BaseScore": 100, "Stats": {"Perfect Points": 1}}
    ga_candidates = [
        {
            "Score": 95,
            "BaseScore": 95,
            "Gear": ["GA Gear"],
            "Minis": ["GA Mini"],
            "Data": {"Score": 95, "BaseScore": 95, "Stats": {"Perfect Points": 2}},
        }
    ]
    selected: dict[str, object] = {}
    refined_candidate = {
        "Score": 130,
        "BaseScore": 130,
        "Gear": ["Refined Gear"],
        "Minis": ["Refined Mini"],
        "Data": {"Score": 130, "BaseScore": 130, "Stats": {"Perfect Points": 3}},
    }

    def fake_decode_gpu_native_ga_runs_payload(**kwargs):
        return best_data, ["Base Gear"], ["Base Mini"], ga_candidates

    def fake_refine_human_hit_sim_after_ga(*args, **kwargs):
        _ = (args, kwargs)
        return {
            "best_score": 130,
            "selected_candidate": {
                "Gear": ["Refined Gear"],
                "Minis": ["Refined Mini"],
                "Data": refined_candidate["Data"],
            },
            "merged_candidates": [refined_candidate],
        }

    def fake_select_fg_candidates(candidates, *, limit, primary_color="", secondary_color="", **kwargs):
        _ = kwargs
        selected["candidates"] = list(candidates)
        selected["limit"] = int(limit)
        selected["primary_color"] = str(primary_color)
        selected["secondary_color"] = str(secondary_color)
        return list(candidates)

    monkeypatch.setattr(
        native_inflight_stages,
        "decode_gpu_native_ga_runs_payload",
        fake_decode_gpu_native_ga_runs_payload,
    )
    monkeypatch.setattr(
        hit_simulation,
        "refine_human_hit_sim_after_ga",
        fake_refine_human_hit_sim_after_ga,
    )
    monkeypatch.setattr(
        native_inflight_stages,
        "select_fg_candidates",
        fake_select_fg_candidates,
    )

    song = SimpleNamespace(
        registry=None,
        cfg_data={"fg_candidate_limit": 51},
        fixed_stats={},
        cfg_dict={"HumanHitSim": {"RefineAfterGA": "true", "MatrixAfterRefine": "false"}},
        calc_song={"metadata": {"Primary Color": "Vibe", "Secondary Color": "Chill"}},
        ref_arrays={},
        ga_seed=123,
    )

    out_best_data, out_best_gear, out_best_minis, out_ga_candidates = native_inflight_stages._decode_ga_payload_sync(
        song, np.zeros((1, 1, 1), dtype=np.int32)
    )

    assert int(out_best_data["BaseScore"]) == 130
    assert out_best_gear == ["Refined Gear"]
    assert out_best_minis == ["Refined Mini"]
    assert any(candidate.get("Gear") == ["Refined Gear"] for candidate in out_ga_candidates)
    assert selected["primary_color"] == "Vibe"
    assert selected["secondary_color"] == "Chill"


def test_prepare_hitsim_continuation_jobs_builds_seeded_regime_job() -> None:
    registry = SimpleNamespace(
        item_to_id={
            **{(slot, f"G{slot}A"): (slot * 10) + 1 for slot in range(6)},
            **{(slot, f"G{slot}B"): (slot * 10) + 2 for slot in range(6)},
            **{(6 + idx, f"M{idx}A"): 100 + idx for idx in range(3)},
            **{(6 + idx, f"M{idx}B"): 110 + idx for idx in range(3)},
        }
    )
    base_candidate = {
        "Score": 120,
        "BaseScore": 120,
        "Gear": [f"G{slot}A" for slot in range(6)],
        "Minis": [f"M{idx}A" for idx in range(3)],
        "Data": {"Score": 120, "BaseScore": 120},
    }
    regime_winner = {
        "Score": 130,
        "BaseScore": 130,
        "Gear": [f"G{slot}B" for slot in range(6)],
        "Minis": [f"M{idx}B" for idx in range(3)],
        "Data": {
            "Score": 130,
            "BaseScore": 130,
            "HumanHitSimRefineMode": "exact",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
            "HumanHitSimSeed": 777,
            "HumanHitSimRegimeId": "regime-1",
            "HumanHitSimRegimeFamily": "ftff_boundary_rows",
            "HumanHitSimRegimeScope": "ALL",
            "HumanHitSimRegimeAlphaNumerator": 1,
            "HumanHitSimRegimeAlphaDenominator": 2,
            "HumanHitSimRegimeLeftNumerator": 1,
            "HumanHitSimRegimeLeftDenominator": 2,
            "HumanHitSimRegimeRightNumerator": 1,
            "HumanHitSimRegimeRightDenominator": 2,
        },
    }
    song = SimpleNamespace(
        cfg_dict={
            "HumanHitSim": {
                "ContinueMaxRegimes": "1",
                "ContinueRuns": "1",
                "ContinuePopulation": "4",
                "ContinueGenerations": "2",
                "ContinueSeedCandidateLimit": "2",
                "ContinueMutationsPerCopy": "0",
            }
        },
        cfg_data={"fg_candidate_limit": 8},
        registry=registry,
        calc_song={
            "metadata": {
                "Song Name": "Continuation Song",
                "HumanHitSimDistribution": "uniform",
                "HumanHitSimGreatMode": "full",
            },
            "song_data": {
                "chart_timestamps": np.array([0.0, 0.1, 0.2], dtype=np.float32),
                "timestamps": np.array([0.0, 0.1, 0.2], dtype=np.float32),
                "fg_timestamps": np.array([0.0, 0.1, 0.2], dtype=np.float32),
                "fg_great_candidate_timestamps": np.array([0.0, 0.1, 0.2], dtype=np.float32),
                "note_types": np.ones((3,), dtype=np.int16),
            },
        },
        slot_start=np.asarray([1, 11, 21, 31, 41, 51, 101, 111, 121], dtype=np.int32),
        slot_count=np.asarray([2, 2, 2, 2, 2, 2, 2, 2, 2], dtype=np.int32),
        meta_primary_color="Vibe",
        meta_secondary_color="Chill",
        ga_seed=123,
        num_runs=2,
        n_genomes=8,
        gens_per_run=10,
        db_seed_ids=None,
        db_seed_prob=0.0,
        db_seed_copies=0,
        db_seed_mutations=0,
    )

    jobs = native_inflight_stages._prepare_hitsim_continuation_jobs(
        song,
        refine_info={
            "selected_candidate": base_candidate,
            "merged_candidates": [base_candidate, regime_winner],
            "regime_winners": [regime_winner],
        },
        ga_candidates=[base_candidate, regime_winner],
    )

    assert len(jobs) == 1
    assert jobs[0]["regime_id"] == "regime-1"
    assert jobs[0]["initial_populations"].shape == (1, 4, 9)
    assert str(jobs[0]["calc_song"]["metadata"]["HumanHitSimRegimeId"]) == "regime-1"
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationStatus"]) == "planned"
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationReason"]) == "ok"
    assert not np.array_equal(
        jobs[0]["calc_song"]["song_data"]["timestamps"],
        jobs[0]["calc_song"]["song_data"]["chart_timestamps"],
    )


def test_advance_hitsim_continuation_resubmits_then_finalizes_best_result() -> None:
    scout_data = {"Score": 120, "BaseScore": 120}
    continuation_data = {"Score": 140, "BaseScore": 140}
    job_song = {
        "metadata": {"HumanHitSimRegimeId": "regime-1"},
        "song_data": {"timestamps": np.array([1.0], dtype=np.float32)},
    }
    song = SimpleNamespace(
        meta_primary_color="Vibe",
        meta_secondary_color="Chill",
        cfg_data={"fg_candidate_limit": 8},
        calc_song={"metadata": {}, "song_data": {"timestamps": np.array([0.0], dtype=np.float32)}},
        ga_seed=123,
        num_runs=2,
        n_genomes=8,
        gens_per_run=10,
        db_seed_ids=None,
        db_seed_prob=0.0,
        db_seed_copies=0,
        db_seed_mutations=0,
        _hitsim_continuation_jobs=[
            {
                "regime_id": "regime-1",
                "calc_song": job_song,
                "initial_populations": np.zeros((1, 4, 9), dtype=np.int32),
                "num_runs": 1,
                "n_genomes": 4,
                "n_generations": 2,
                "ga_seed": 999,
            }
        ],
        _hitsim_continuation_base_state={
            "ga_seed": 123,
            "num_runs": 2,
            "n_genomes": 8,
            "gens_per_run": 10,
            "db_seed_ids": None,
            "db_seed_prob": 0.0,
            "db_seed_copies": 0,
            "db_seed_mutations": 0,
        },
    )

    first = native_inflight_stages._advance_hitsim_continuation(
        song,
        best_data=scout_data,
        best_gear=["Scout Gear"],
        best_minis=["Scout Mini"],
        ga_candidates=[{"Score": 120, "BaseScore": 120, "Gear": ["Scout Gear"], "Minis": ["Scout Mini"], "Data": scout_data}],
    )
    assert bool(first["resubmit"]) is True
    assert int(song.ga_seed) == 999
    assert int(song.num_runs) == 1
    assert song.ga_initial_populations.shape == (1, 4, 9)
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationStatus"]) == "active"
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationActiveRegimeId"]) == "regime-1"

    second = native_inflight_stages._advance_hitsim_continuation(
        song,
        best_data=continuation_data,
        best_gear=["Cont Gear"],
        best_minis=["Cont Mini"],
        ga_candidates=[{"Score": 140, "BaseScore": 140, "Gear": ["Cont Gear"], "Minis": ["Cont Mini"], "Data": continuation_data}],
    )
    assert bool(second["resubmit"]) is False
    assert int(second["best_data"]["Score"]) == 140
    assert second["best_gear"] == ["Cont Gear"]
    assert int(song.ga_seed) == 123
    assert int(song.num_runs) == 2
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationStatus"]) == "completed"
    assert int(song.calc_song["metadata"]["HumanHitSimContinuationBestScore"]) == 140
    assert str(song.calc_song["metadata"]["HumanHitSimRegimeId"]) == "regime-1"


def test_prepare_hitsim_continuation_jobs_warns_when_regime_materialization_fails(monkeypatch) -> None:
    warnings: list[tuple[str, str]] = []

    def fake_warn(site, reason, **kwargs):
        _ = kwargs
        warnings.append((str(site), str(reason)))

    monkeypatch.setattr(native_inflight_stages, "warn_fallback", fake_warn)
    monkeypatch.setattr(hit_simulation, "materialize_human_hit_sim_regime", lambda calc_song, regime_data: None)

    song = SimpleNamespace(
        cfg_dict={"HumanHitSim": {"ContinueMaxRegimes": "1"}},
        cfg_data={"fg_candidate_limit": 8},
        registry=SimpleNamespace(item_to_id={}),
        calc_song={"metadata": {"Song Name": "Continuation Song"}, "song_data": {}},
        slot_start=np.asarray([1, 11, 21, 31, 41, 51, 101, 111, 121], dtype=np.int32),
        slot_count=np.asarray([2, 2, 2, 2, 2, 2, 2, 2, 2], dtype=np.int32),
        meta_primary_color="Vibe",
        meta_secondary_color="Chill",
        ga_seed=123,
        num_runs=2,
        n_genomes=8,
        gens_per_run=10,
        db_seed_ids=None,
        db_seed_prob=0.0,
        db_seed_copies=0,
        db_seed_mutations=0,
    )
    regime_winner = {
        "Score": 130,
        "BaseScore": 130,
        "Gear": [f"G{slot}B" for slot in range(6)],
        "Minis": [f"M{idx}B" for idx in range(3)],
        "Data": {
            "Score": 130,
            "BaseScore": 130,
            "HumanHitSimRegimeId": "regime-1",
        },
    }

    jobs = native_inflight_stages._prepare_hitsim_continuation_jobs(
        song,
        refine_info={
            "selected_candidate": {"Gear": [f"G{slot}A" for slot in range(6)], "Minis": [f"M{idx}A" for idx in range(3)]},
            "merged_candidates": [regime_winner],
            "regime_winners": [regime_winner],
        },
        ga_candidates=[regime_winner],
    )

    assert jobs == []
    assert ("hitsim.continuation.materialize", "regime materialization returned no output") in warnings
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationStatus"]) == "failed"
    assert str(song.calc_song["metadata"]["HumanHitSimContinuationReason"]) == "no_jobs"


def test_prepare_hitsim_matrix_plan_builds_regime_jobs() -> None:
    items = {
        1: {"Name": "G0A", "Perfect Points": 1},
        2: {"Name": "G1A", "Perfect Points": 1},
        3: {"Name": "G2A", "Perfect Points": 1},
        4: {"Name": "G3A", "Perfect Points": 1},
        5: {"Name": "G4A", "Perfect Points": 1},
        6: {"Name": "G5A", "Perfect Points": 1},
        7: {"Name": "M0A", "Perfect Points": 1},
        8: {"Name": "M1A", "Perfect Points": 1},
        9: {"Name": "M2A", "Perfect Points": 1},
    }
    registry = SimpleNamespace(
        decode_genome=lambda ids: [dict(items[int(x)]) for x in list(ids)[:9]],
        item_to_id={},
    )
    regime_data = {
        "HumanHitSimRefineMode": "exact",
        "HumanHitSimDistribution": "uniform",
        "HumanHitSimGreatMode": "full",
        "HumanHitSimSeed": 777,
        "HumanHitSimRegimeId": "regime-1",
        "HumanHitSimRegimeFamily": "ftff_boundary_rows",
        "HumanHitSimRegimeScope": "ALL",
        "HumanHitSimRegimeAlphaNumerator": 1,
        "HumanHitSimRegimeAlphaDenominator": 2,
        "HumanHitSimRegimeLeftNumerator": 1,
        "HumanHitSimRegimeLeftDenominator": 2,
        "HumanHitSimRegimeRightNumerator": 1,
        "HumanHitSimRegimeRightDenominator": 2,
    }
    song = SimpleNamespace(
        cfg_dict={"HumanHitSim": {"MatrixAfterRefine": "true", "MatrixCandidateLimit": "2"}},
        cfg_data={"fg_candidate_limit": 4, "selected_color": "Vibe"},
        registry=registry,
        fixed_stats={"Perfect Points": 10},
        calc_song={
            "metadata": {"Song Name": "Matrix Song", "HumanHitSimDistribution": "uniform", "HumanHitSimGreatMode": "full"},
            "song_data": {
                "chart_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "fg_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "fg_great_candidate_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "note_types": np.ones((2,), dtype=np.int16),
            },
        },
        ref_arrays={},
        item_stats=np.ones((16, 10), dtype=np.int32),
        slot_start=np.arange(9, dtype=np.int32) + 1,
        slot_count=np.ones((9,), dtype=np.int32),
        base_fixed_stats_arr=np.ones((10,), dtype=np.int32),
        color_flags={"is_p_ft": 1},
        meta_primary_color="Vibe",
        meta_secondary_color="Chill",
    )
    candidate = {
        "Score": 120,
        "BaseScore": 120,
        "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "Data": {
            "Score": 120,
            "BaseScore": 120,
            "BaseStats": {"Perfect Points": 19, "Vibe": 0, "Beat": 0, "Rush": 0, "Flow": 0, "Chill": 0},
        },
    }

    plan = native_inflight_stages._prepare_hitsim_matrix_plan(
        song,
        refine_info={"selected_candidate": candidate, "merged_candidates": [candidate], "regime_winners": [{"Data": regime_data}]},
        ga_candidates=[candidate],
    )

    assert isinstance(plan, dict)
    assert len(plan["candidate_entries"]) == 1
    assert len(plan["jobs"]) == 1
    assert plan["jobs"][0]["regime_id"] == "regime-1"
    assert tuple(plan["shared_request_payload"]["population_indices"].shape) == (1, 9)


def test_run_hitsim_matrix_jobs_sync_promotes_best_regime_candidate() -> None:
    items = {
        1: {"Name": "G0A", "Perfect Points": 1},
        2: {"Name": "G1A", "Perfect Points": 1},
        3: {"Name": "G2A", "Perfect Points": 1},
        4: {"Name": "G3A", "Perfect Points": 1},
        5: {"Name": "G4A", "Perfect Points": 1},
        6: {"Name": "G5A", "Perfect Points": 1},
        7: {"Name": "M0A", "Perfect Points": 1},
        8: {"Name": "M1A", "Perfect Points": 1},
        9: {"Name": "M2A", "Perfect Points": 1},
        11: {"Name": "G0B", "Perfect Points": 2},
        12: {"Name": "G1B", "Perfect Points": 2},
        13: {"Name": "G2B", "Perfect Points": 2},
        14: {"Name": "G3B", "Perfect Points": 2},
        15: {"Name": "G4B", "Perfect Points": 2},
        16: {"Name": "G5B", "Perfect Points": 2},
        17: {"Name": "M0B", "Perfect Points": 2},
        18: {"Name": "M1B", "Perfect Points": 2},
        19: {"Name": "M2B", "Perfect Points": 2},
    }
    registry = SimpleNamespace(
        decode_genome=lambda ids: [dict(items[int(x)]) for x in list(ids)[:9]],
        item_to_id={},
    )

    def _regime(regime_id: str) -> dict:
        return {
            "HumanHitSimRefineMode": "exact",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
            "HumanHitSimSeed": 700 + int(regime_id[-1]),
            "HumanHitSimRegimeId": regime_id,
            "HumanHitSimRegimeFamily": "ftff_boundary_rows",
            "HumanHitSimRegimeScope": "ALL",
            "HumanHitSimRegimeAlphaNumerator": 1,
            "HumanHitSimRegimeAlphaDenominator": 2,
            "HumanHitSimRegimeLeftNumerator": 1,
            "HumanHitSimRegimeLeftDenominator": 2,
            "HumanHitSimRegimeRightNumerator": 1,
            "HumanHitSimRegimeRightDenominator": 2,
        }

    candidate_a = {
        "Score": 120,
        "BaseScore": 120,
        "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "Data": {
            "Score": 120,
            "BaseScore": 120,
            "BaseStats": {"Perfect Points": 19, "Vibe": 0, "Beat": 0, "Rush": 0, "Flow": 0, "Chill": 0},
        },
    }
    candidate_b = {
        "Score": 118,
        "BaseScore": 118,
        "GenomeIDs": [11, 12, 13, 14, 15, 16, 17, 18, 19],
        "Data": {
            "Score": 118,
            "BaseScore": 118,
            "BaseStats": {"Perfect Points": 28, "Vibe": 0, "Beat": 0, "Rush": 0, "Flow": 0, "Chill": 0},
        },
    }
    song = SimpleNamespace(
        cfg_dict={"HumanHitSim": {"MatrixAfterRefine": "true", "MatrixCandidateLimit": "2"}},
        cfg_data={"fg_candidate_limit": 4, "selected_color": "Vibe"},
        registry=registry,
        fixed_stats={"Perfect Points": 10},
        calc_song={
            "metadata": {"Song Name": "Matrix Song", "HumanHitSimDistribution": "uniform", "HumanHitSimGreatMode": "full"},
            "song_data": {
                "chart_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "fg_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "fg_great_candidate_timestamps": np.array([0.0, 0.1], dtype=np.float32),
                "note_types": np.ones((2,), dtype=np.int16),
            },
        },
        ref_arrays={},
        item_stats=np.ones((32, 10), dtype=np.int32),
        slot_start=np.arange(9, dtype=np.int32) + 1,
        slot_count=np.ones((9,), dtype=np.int32),
        base_fixed_stats_arr=np.ones((10,), dtype=np.int32),
        color_flags={"is_p_ft": 1},
        meta_primary_color="Vibe",
        meta_secondary_color="Chill",
        best_data={"Score": 120, "BaseScore": 120, "HumanHitSimRegimeId": "regime-1"},
        best_gear=["Scout Gear"],
        best_minis=["Scout Mini"],
        ga_candidates=[candidate_a, candidate_b],
        _hitsim_last_refine_info={
            "selected_candidate": candidate_a,
            "merged_candidates": [candidate_a, candidate_b],
            "regime_winners": [{"Data": _regime("regime-1")}, {"Data": _regime("regime-2")}],
        },
    )
    song._hitsim_matrix_plan = native_inflight_stages._prepare_hitsim_matrix_plan(
        song,
        refine_info=song._hitsim_last_refine_info,
        ga_candidates=[candidate_a, candidate_b],
    )

    class _FakeFuture:
        def __init__(self, result):
            self._result = result

        def result(self):
            return self._result

    class _FakeClient:
        def __init__(self, results):
            self._results = list(results)
            self.calls = []
            self.batch_calls = []

        def submit_solve_genomes_from_registry(self, payload):
            self.calls.append(dict(payload))
            return SimpleNamespace(future=_FakeFuture(self._results[len(self.calls) - 1]))

        def submit_solve_genomes_from_registry_matrix(self, payload):
            self.batch_calls.append(dict(payload))
            return SimpleNamespace(future=_FakeFuture(self._results))

    gpu_client = _FakeClient(
        [
            [(130, 1, 0, 2, 0, 0, 0), (125, 0, 1, 1, 0, 0, 0)],
            [(126, 0, 1, 1, 0, 0, 0), (150, 1, 0, 3, 0, 0, 0)],
        ]
    )

    best_data, best_gear, best_minis, ga_candidates = native_inflight_stages._run_hitsim_matrix_jobs_sync(
        song,
        gpu_client=gpu_client,
    )

    assert len(gpu_client.batch_calls) == 1
    assert len(gpu_client.calls) == 0
    assert int(best_data["Score"]) == 150
    assert [it["Name"] for it in best_gear] == ["G0B", "G1B", "G2B", "G3B", "G4B", "G5B"]
    assert [it["Name"] for it in best_minis] == ["M0B", "M1B", "M2B"]
    assert any(int(c.get("Score", 0)) == 150 for c in ga_candidates)
    assert song.calc_song["metadata"]["HumanHitSimRegimeMatrixApplied"] is True
    assert int(song.calc_song["metadata"]["HumanHitSimRegimeMatrixCompletedRegimeCount"]) == 2
    assert str(song.calc_song["metadata"]["HumanHitSimRegimeMatrixExecutionMode"]) == "gpu_batch"
    assert int(song._hitsim_last_refine_info["matrix_best_score"]) == 150
    assert len(song._hitsim_last_refine_info["regime_winners"]) == 2
    assert str(song._hitsim_last_refine_info["selected_candidate"]["HumanHitSimRegimeId"]) == "regime-2"
    assert len(song._hitsim_fg_regime_groups) == 2
    assert {str(group["regime_id"]) for group in song._hitsim_fg_regime_groups} == {"regime-1", "regime-2"}
    assert all(group.get("ga_candidates") for group in song._hitsim_fg_regime_groups)
    assert {
        str(group["ga_candidates"][0]["HumanHitSimRegimeId"])
        for group in song._hitsim_fg_regime_groups
    } == {"regime-1", "regime-2"}
