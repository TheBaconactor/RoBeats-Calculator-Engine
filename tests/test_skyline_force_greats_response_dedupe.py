from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np

import gear_optimizer.solver.fg_response_scoring.planner as planner_mod
import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
from gear_optimizer.solver import skyline_force_greats as sfg
from gear_optimizer.solver.candidate_cache import reset_candidate_cache_for_tests
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService
from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
)


def _base_calc_song() -> dict[str, Any]:
    return {
        "metadata": {
            "Primary Color": "Power",
            "Secondary Color": "Rush",
            "Long Notes": 0,
            "Last Note Time": 1.0,
        },
        "song_data": {"timestamps": [0.0, 1.0]},
    }


def _ref_arrays() -> dict[str, np.ndarray]:
    base = np.linspace(1.0, 2.0, 161, dtype=np.float32)
    return {
        "Perfect Points": base,
        "Combo Multiplier": base + np.float32(0.1),
        "Fever Multiplier": base + np.float32(0.2),
        "Fever Time": base + np.float32(0.3),
        "Fever Fill Rate": base + np.float32(0.4),
    }


def _stats(*, pp: int = 100) -> dict[str, int]:
    return {
        "Perfect Points": int(pp),
        "Combo Multiplier": 200,
        "Fever Multiplier": 300,
        "Power": 400,
        "Rush": 500,
        "Fever Time": 600,
        "Fever Fill Rate": 700,
    }


def _record(*, pp: int, selected: str = "Power") -> dict[str, Any]:
    base_stats = _stats(pp=pp)
    return {
        "data": {
            "BaseStats": dict(base_stats),
            "GemCounts": {},
            "FT": 0,
            "FF": 0,
            "Selected Element": selected,
        },
        "base_score": 1_000_000 + int(pp),
    }


def _solve_result(base_stats: dict[str, Any], *, selected_color: str) -> FgResponseFrontierSolveResult:
    pp = int(base_stats["Perfect Points"])
    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, pp, 0, 0)
    frontier = FgResponseFrontierResult(
        first_frontier=(surface,),
        state_frontiers={},
        states_evaluated=1,
        actions=1,
        transitions_evaluated=1,
        generated_surfaces=1,
        retained_surfaces_total=1,
        max_state_frontier=1,
        non_fever_base=7,
        seconds=0.0,
    )
    inner = FgResponseInnerResult(
        best_score=1_000_200 + pp,
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
    return FgResponseFrontierSolveResult(
        best_score=1_000_200 + pp,
        ft=2,
        ff=3,
        gem_counts={"Perfect Points": pp, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
        stats={**base_stats, selected_color: int(base_stats.get(selected_color, 0) or 0) + 1},
        surface=surface,
        frontier=frontier,
        inner=inner,
        seconds=0.0,
        forced_counts=(),
    )


def _install_shared_path_fakes(monkeypatch: Any) -> list[tuple[str, list[dict[str, Any]]]]:
    prepare_calls: list[tuple[str, list[dict[str, Any]]]] = []

    monkeypatch.setattr(
        planner_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(total_notes=2),
    )
    monkeypatch.setattr(
        reducer_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(
            timestamps=[0.0, 1.0],
            perfect_candidates=[0.0, 1.0],
            great_candidates=[0.0, 1.0],
            perfect_floor=[0.0, 1.0],
            use_forced_great_timing=True,
        ),
    )
    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: ({"forced_count": 1}, {"forced_count": 0}),
    )
    monkeypatch.setattr(
        reducer_mod,
        "score_force_greats_response_surface_exact",
        lambda stats, *_args, **_kwargs: 1_000_200 + int(stats["Perfect Points"]),
    )

    def _fake_prepare(*, base_stats_list, selected_color, **kwargs):
        rows = [dict(base_stats) for base_stats in base_stats_list]
        prepare_calls.append((str(selected_color or ""), rows))
        calc_song = kwargs.get("calc_song") or _base_calc_song()
        metadata = dict((calc_song.get("metadata") if isinstance(calc_song, dict) else {}) or {})
        base_components = np.asarray(
            [
                response_frontier_base_components_row(
                    base_stats,
                    None,
                    primary_color=str(metadata.get("Primary Color", "") or ""),
                    secondary_color=str(metadata.get("Secondary Color", "") or ""),
                )
                for base_stats in rows
            ],
            dtype=np.int32,
        )
        return SimpleNamespace(
            base_stats_list=rows,
            selected_color=str(selected_color or ""),
            base_components=base_components,
        )

    def _fake_score_plan(plan, **_kwargs):
        scored = []
        for prepared in plan.prepared_batches:
            selected_color = str(getattr(prepared.batch, "selected_color", "") or "")
            scored.append(
                [
                    _solve_result(dict(base_stats), selected_color=selected_color)
                    for _cache_key, base_stats in prepared.rows
                ]
            )
        return scored

    monkeypatch.setattr(planner_mod, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare)
    monkeypatch.setattr(
        GpuScoreEngine,
        "score_plan",
        staticmethod(lambda plan, **_kwargs: (_fake_score_plan(plan), [])),
    )
    return prepare_calls


def test_skyline_scores_retained_candidates_through_shared_service(tmp_path: Any, monkeypatch: Any) -> None:
    reset_candidate_cache_for_tests(tmp_path / "candidate_cache.sqlite3")
    prepare_calls = _install_shared_path_fakes(monkeypatch)
    seen: dict[str, Any] = {}
    original = FgResponseScoringService.score_candidates_with_stats

    def _spy_score_candidates_with_stats(*args, **kwargs):
        seen["mode"] = kwargs.get("mode")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        FgResponseScoringService,
        "score_candidates_with_stats",
        staticmethod(_spy_score_candidates_with_stats),
    )
    records = [_record(pp=100), _record(pp=100), _record(pp=101)]

    summary, best_record = sfg.score_retained_skyline_force_greats(
        records,
        calc_song=_base_calc_song(),
        ref_arrays=_ref_arrays(),
        default_selected_color="Power",
        use_gpu=True,
    )

    assert seen["mode"] == "skyline"
    assert prepare_calls == [("Power", [_stats(pp=100), _stats(pp=101)])]
    assert {
        "candidate_count": summary["candidate_count"],
        "exact_calls": summary["exact_calls"],
        "response_frontier_calls": summary["response_frontier_calls"],
        "gpu_batches": summary["gpu_batches"],
        "batch_groups": summary["batch_groups"],
        "fg_batch_input_genomes": summary["fg_batch_input_genomes"],
        "fg_batch_unique_genomes": summary["fg_batch_unique_genomes"],
        "fg_batch_deduped_genomes": summary["fg_batch_deduped_genomes"],
        "fg_batch_dedupe_groups": summary["fg_batch_dedupe_groups"],
        "fg_gains": summary["fg_gains"],
        "best_fg_score": summary["best_fg_score"],
    } == {
        "candidate_count": 3,
        "exact_calls": 3,
        "response_frontier_calls": 3,
        "gpu_batches": 2,
        "batch_groups": 1,
        "fg_batch_input_genomes": 3,
        "fg_batch_unique_genomes": 2,
        "fg_batch_deduped_genomes": 1,
        "fg_batch_dedupe_groups": 1,
        "fg_gains": 3,
        "best_fg_score": 1_000_301,
    }
    assert best_record is records[2]
    for record in records:
        payload = record["force"]
        assert record["data"]["force"] is payload
        assert payload["ForceGreats"]["frontier_trace"] == [{"forced_count": 1}, {"forced_count": 0}]
        assert payload["response_surface"] == [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            int(record["data"]["BaseStats"]["Perfect Points"]),
            0,
            0,
        ]
        assert record["fg_score"] == 1_000_200 + int(record["data"]["BaseStats"]["Perfect Points"])


def test_skyline_mode_keeps_selected_color_responses_separate(tmp_path: Any, monkeypatch: Any) -> None:
    reset_candidate_cache_for_tests(tmp_path / "candidate_cache.sqlite3")
    prepare_calls = _install_shared_path_fakes(monkeypatch)

    rows, stats = FgResponseScoringService.score_candidates_with_stats(
        [_record(pp=100, selected="Power"), _record(pp=100, selected="Rush")],
        calc_song=_base_calc_song(),
        ref_arrays=_ref_arrays(),
        meta_primary_color="Power",
        mode="skyline",
    )

    assert prepare_calls == [("Power", [_stats(pp=100)]), ("Rush", [_stats(pp=100)])]
    assert stats == {
        "gpu_batches": 2,
        "groups": 2,
        "input_genomes": 2,
        "unique_genomes": 2,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
    }
    assert [row["selected"] for row in rows] == ["Power", "Rush"]
