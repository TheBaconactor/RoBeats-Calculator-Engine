from __future__ import annotations

from types import SimpleNamespace
import sqlite3

import numpy as np
import pytest

from gear_optimizer.solver.candidate_cache import (
    CandidateCache,
    base_candidate_cache_key,
    base_payload_from_result,
    fg_candidate_cache_key,
    reset_candidate_cache_for_tests,
)
from gear_optimizer.solver.solver_common import batched_registry_eval
from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer
from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService
from gear_optimizer.solver.fg_response_scoring.planner import (
    FgResponseFrontierPreparedBatch,
    FgResponseFrontierPreparedPlan,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    FgResponseFrontierPackedScoringBatch,
)


def _calc_song() -> dict:
    timestamps = np.asarray([0.1, 0.4, 0.9], dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "cache test",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Last Note Time": 0.9,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": np.zeros((3,), dtype=np.int32),
            "fg_timestamps": timestamps,
            "fg_perfect_candidate_timestamps": timestamps,
            "fg_great_candidate_timestamps": timestamps + np.float32(0.015),
            "fg_perfect_floor_timestamps": timestamps,
        },
    }


def _compatible_calc_song(name: str) -> dict:
    song = _calc_song()
    song["metadata"] = dict(song["metadata"])
    song["metadata"]["Song Name"] = str(name)
    return song


def _ref_arrays() -> dict[str, np.ndarray]:
    base = np.linspace(1.0, 2.0, 161, dtype=np.float32)
    return {
        "Perfect Points": base,
        "Combo Multiplier": base + np.float32(0.1),
        "Fever Multiplier": base + np.float32(0.2),
        "Fever Time": base + np.float32(0.3),
        "Fever Fill Rate": base + np.float32(0.4),
    }


def _base_stats() -> dict[str, int]:
    return {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Fever Time": 40,
        "Fever Fill Rate": 50,
        "Beat": 60,
        "Vibe": 70,
        "Rush": 80,
        "Flow": 90,
        "Chill": 100,
    }


def _fg_cached_payload() -> dict:
    return {
        "raw_best_score": 150,
        "exact_score": 140,
        "FT": 1,
        "FF": 2,
        "GemCounts": {
            "Perfect Points": 3,
            "Combo Multiplier": 4,
            "Fever Multiplier": 5,
            "Overflow": 6,
        },
        "forced_counts": [1, 0],
        "response_surface": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "ForceGreats": {
            "config": {"NonFever1": 1},
            "final_score": 140,
            "frontier_trace": [{"section": 1, "forced_count": 1}],
            "frontier_first_surfaces": 1,
            "frontier_states": 2,
            "frontier_max_state": 3,
            "frontier_transitions": 4,
            "non_fever_base": 5,
        },
    }


def _fg_plan() -> FgResponseFrontierPreparedPlan:
    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    base_stats = _base_stats()
    planner_key = (
        "Rush",
        tuple(sorted((str(key), int(value)) for key, value in base_stats.items())),
    )
    eval_data = {
        "BaseScore": 100,
        "BaseStats": dict(base_stats),
        "Selected Element": "Rush",
        "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }
    entry = {
        "gear": ["Hat A"],
        "minis": ["Mini A"],
        "base_score": 100,
        "score": 100,
        "eval_data": eval_data,
        "selected_element": "Rush",
        "loadout_hash": "loadout-a",
        "_source": "ga",
    }
    batch = FgResponseFrontierPackedScoringBatch(
        started=0.0,
        stats_inputs=(base_stats,),
        calc_song=calc_song,
        song_inputs=None,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
        scoring_bundle=object(),
        scoring_bundle_ms=0.0,
        base_components=np.asarray([[10, 20, 30, 80, 90, 40, 50]], dtype=np.int32),
        ft_values=np.asarray([0], dtype=np.int32),
        ff_values=np.asarray([0], dtype=np.int32),
        residual_values=np.asarray([0], dtype=np.int32),
        frontier_idx_by_stat=np.zeros((1, 1), dtype=np.int32),
        primary_ftff_delta_values=np.zeros((1, 1), dtype=np.int32),
        secondary_ftff_delta_values=np.zeros((1, 1), dtype=np.int32),
        score_elements_constant=True,
        head_len=0,
        body_total=0,
    )
    return FgResponseFrontierPreparedPlan(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        pending_jobs=((entry, eval_data, "Rush", base_stats, 100, planner_key),),
        prepared_batches=(FgResponseFrontierPreparedBatch(rows=((planner_key, base_stats),), batch=batch),),
    )


def test_candidate_cache_keeps_base_and_fg_separate_and_reloads_disk(tmp_path):
    db_path = tmp_path / "candidate_cache.sqlite3"
    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    flags = {"is_p_pp": 0, "is_s_pp": 0}
    base_key = base_candidate_cache_key(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        base_stats=_base_stats(),
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        flags=flags,
    )
    fg_key = fg_candidate_cache_key(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        base_components=(10, 20, 30, 80, 90, 40, 50),
    )

    cache = CandidateCache(db_path)
    cache.put_base(
        base_key,
        base_payload_from_result(
            result={
                "Score": 123,
                "FT": 1,
                "FF": 2,
                "GemCounts": {
                    "Perfect Points": 3,
                    "Combo Multiplier": 4,
                    "Fever Multiplier": 5,
                    "Overflow": 6,
                },
                "Stats": _base_stats(),
                "Selected Element": "Rush",
            },
            selected_color="Rush",
        ),
    )
    cache.put_fg(fg_key, _fg_cached_payload())

    assert cache.get_fg(base_key) is None
    assert cache.get_base(fg_key) is None
    assert cache.stats()["pending_disk_rows"] == 2
    assert CandidateCache(db_path).get_base(base_key) is None

    cache.flush()
    reloaded = CandidateCache(db_path)
    assert reloaded.get_base(base_key)["Score"] == 123
    assert reloaded.get_fg(fg_key)["exact_score"] == 140


def test_candidate_cache_reuses_semantically_compatible_cross_song_keys(tmp_path):
    db_path = tmp_path / "candidate_cache.sqlite3"
    cache = CandidateCache(db_path)
    ref_arrays = _ref_arrays()
    flags = {"is_p_pp": 0, "is_s_pp": 0}
    base_key_a = base_candidate_cache_key(
        calc_song=_compatible_calc_song("cache test A"),
        ref_arrays=ref_arrays,
        base_stats=_base_stats(),
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        flags=flags,
    )
    base_key_b = base_candidate_cache_key(
        calc_song=_compatible_calc_song("cache test B"),
        ref_arrays=ref_arrays,
        base_stats=_base_stats(),
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        flags=flags,
    )
    fg_key_a = fg_candidate_cache_key(
        calc_song=_compatible_calc_song("cache test A"),
        ref_arrays=ref_arrays,
        selected_color="Rush",
        base_components=(10, 20, 30, 80, 90, 40, 50),
    )
    fg_key_b = fg_candidate_cache_key(
        calc_song=_compatible_calc_song("cache test B"),
        ref_arrays=ref_arrays,
        selected_color="Rush",
        base_components=(10, 20, 30, 80, 90, 40, 50),
    )
    assert base_key_a == base_key_b
    assert fg_key_a == fg_key_b

    cache.put_base(
        base_key_a,
        base_payload_from_result(
            result={
                "Score": 123,
                "FT": 1,
                "FF": 2,
                "GemCounts": {
                    "Perfect Points": 3,
                    "Combo Multiplier": 4,
                    "Fever Multiplier": 5,
                    "Overflow": 6,
                },
                "Stats": _base_stats(),
                "Selected Element": "Rush",
            },
            selected_color="Rush",
        ),
    )
    cache.put_fg(fg_key_a, _fg_cached_payload())

    assert cache.get_base(base_key_b)["Score"] == 123
    assert cache.get_fg(fg_key_b)["exact_score"] == 140


def test_candidate_cache_corrupt_disk_payload_fails_loudly(tmp_path):
    db_path = tmp_path / "candidate_cache.sqlite3"
    cache = CandidateCache(db_path)
    fg_key = fg_candidate_cache_key(
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        selected_color="Rush",
        base_components=(10, 20, 30, 80, 90, 40, 50),
    )
    cache.put_fg(fg_key, _fg_cached_payload())
    cache.flush()
    with sqlite3.connect(db_path) as con:
        con.execute("UPDATE candidate_cache SET payload_json='{}' WHERE namespace='fg'")

    with pytest.raises(ValueError, match="FG candidate cache payload"):
        CandidateCache(db_path)


def test_fg_reducer_admits_miss_then_service_hit_skips_scorer(tmp_path, monkeypatch):
    db_path = tmp_path / "candidate_cache.sqlite3"
    reset_candidate_cache_for_tests(db_path)
    plan = _fg_plan()

    def _fake_materialize_force_payload(**kwargs):
        from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

        gem_counts = {
            "Perfect Points": 3,
            "Combo Multiplier": 4,
            "Fever Multiplier": 5,
            "Overflow": 6,
        }
        final_stats = apply_gems_to_base_stats(
            dict(kwargs["base_stats"]),
            str(kwargs["selected_element"]),
            1,
            2,
            int(gem_counts["Perfect Points"]),
            int(gem_counts["Combo Multiplier"]),
            int(gem_counts["Fever Multiplier"]),
            int(gem_counts["Overflow"]),
        )
        payload = dict(kwargs["eval_data"])
        payload.update(
            {
                "BaseStats": dict(kwargs["base_stats"]),
                "Stats": final_stats,
                "BaseScore": int(kwargs["paired_base_score"]),
                "Score": 140,
                "Selected Element": kwargs["selected_element"],
                "GemCounts": gem_counts,
                "FT": 1,
                "FF": 2,
                "forced_counts": [1, 0],
                "response_surface": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "ForceGreats": _fg_cached_payload()["ForceGreats"],
            }
        )
        return payload

    monkeypatch.setattr(
        "gear_optimizer.solver.fg_response_scoring.reducer.materialize_force_payload_from_response_frontier",
        _fake_materialize_force_payload,
    )
    first = FgResultReducer.materialize(plan, [[SimpleNamespace(best_score=150)]])
    assert first[0]["fg_score"] == 140
    fresh_payload = first[0]["data"]

    reset_candidate_cache_for_tests(db_path)

    def _unexpected_score_plan(*_args, **_kwargs):
        raise AssertionError("cached FG plan should not invoke GPU scoring")

    monkeypatch.setattr(
        "gear_optimizer.solver.fg_response_scoring.service.GpuScoreEngine.score_plan",
        staticmethod(_unexpected_score_plan),
    )
    second = FgResponseScoringService.score_prepared_plan(plan, gpu_client=None, mode="skyline")

    assert second[0]["fg_score"] == 140
    assert second[0]["data"]["GenomeIDs"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    cached_payload = second[0]["data"]
    for field in (
        "BaseStats",
        "Stats",
        "BaseScore",
        "Score",
        "Selected Element",
        "GemCounts",
        "FT",
        "FF",
        "forced_counts",
        "response_surface",
        "ForceGreats",
    ):
        assert cached_payload[field] == fresh_payload[field]


def test_base_batch_cache_hit_skips_registry_dispatch_after_disk_reload(tmp_path, monkeypatch):
    db_path = tmp_path / "candidate_cache.sqlite3"
    reset_candidate_cache_for_tests(db_path)
    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    flags = {
        "is_p_ft": 0,
        "is_s_ft": 0,
        "is_p_ff": 0,
        "is_s_ff": 0,
        "is_p_pp": 0,
        "is_s_pp": 0,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 0,
        "is_s_fm": 0,
        "is_p_ov": 0,
        "is_s_ov": 0,
    }
    batch_ids = np.zeros((1, 9), dtype=np.int32)
    gpu_arrays = {
        "item_stats": np.zeros((1, 10), dtype=np.int32),
        "slot_start": np.zeros((9,), dtype=np.int32),
        "slot_count": np.ones((9,), dtype=np.int32),
    }
    base_fixed_stats_arr = np.asarray(list(_base_stats().values()), dtype=np.int32)
    dispatch_calls = {"count": 0}

    def _dispatch_once(request, *, gpu_client=None):
        del gpu_client
        dispatch_calls["count"] += 1
        assert request.score_only is False
        return [(123, 1, 2, 3, 4, 5, 6)]

    monkeypatch.setattr("gear_optimizer.solver.solver_common.dispatch_registry_solve", _dispatch_once)
    best_ids, heap = batched_registry_eval(
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        flags=flags,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        song_slot=0,
        candidate_total=1,
        candidate_batches=[(batch_ids, np.asarray([11], dtype=np.uint64), np.asarray([22], dtype=np.uint64))],
        keep_top_k=1,
    )
    assert dispatch_calls["count"] == 1
    assert best_ids.tolist() == batch_ids[0].tolist()
    assert heap == [(123, 11, 22)]

    reset_candidate_cache_for_tests(db_path)

    def _unexpected_dispatch(*_args, **_kwargs):
        raise AssertionError("disk-reloaded base cache hit should skip registry dispatch")

    monkeypatch.setattr("gear_optimizer.solver.solver_common.dispatch_registry_solve", _unexpected_dispatch)
    best_ids, heap = batched_registry_eval(
        gpu_arrays=gpu_arrays,
        base_fixed_stats_arr=base_fixed_stats_arr,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        flags=flags,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        song_slot=0,
        candidate_total=1,
        candidate_batches=[(batch_ids, np.asarray([11], dtype=np.uint64), np.asarray([22], dtype=np.uint64))],
        keep_top_k=1,
    )
    assert best_ids.tolist() == batch_ids[0].tolist()
    assert heap == [(123, 11, 22)]


def test_fused_fg_selected_payload_cache_hit_skips_owner_scoring_after_disk_reload(tmp_path, monkeypatch):
    db_path = tmp_path / "candidate_cache.sqlite3"
    cache = reset_candidate_cache_for_tests(db_path)
    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    base_components = (10, 20, 30, 80, 90, 40, 50)
    cache.put_fg(
        fg_candidate_cache_key(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color="Rush",
            base_components=base_components,
            total_budget=90,
        ),
        _fg_cached_payload(),
    )
    reset_candidate_cache_for_tests(db_path)

    runs_payload = np.zeros((2, 26), dtype=np.int32)
    runs_payload[0, 0] = 1
    runs_payload[1, 19:26] = np.asarray(base_components, dtype=np.int32)

    def _unexpected_owner_score(*_args, **_kwargs):
        raise AssertionError("disk-reloaded FG cache hit should skip fused owner scoring")

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_frontier."
        "score_fused_owner_base_components_on_gpu_owner",
        _unexpected_owner_score,
    )

    from gear_optimizer.solver.genetic_pipeline import score_fused_fg_from_selected_payload

    assert (
        score_fused_fg_from_selected_payload(
            runs_payload=runs_payload,
            fg_scoring_bundle=object(),
            fg_calc_song=calc_song,
            ref_arrays=ref_arrays,
            cfg_data={"TotalBudget": 90, "selected_color": "Rush"},
        )
        == {}
    )
