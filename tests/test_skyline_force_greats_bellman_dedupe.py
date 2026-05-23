from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from gear_optimizer.solver import skyline_force_greats as sfg


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


def _prepared(*, pp: int, selected: str = "Power") -> dict[str, Any]:
    base_stats = _stats(pp=pp)
    return {
        "data": {
            "BaseStats": dict(base_stats),
            "GemCounts": {},
            "FT": 0,
            "FF": 0,
            "Selected Element": selected,
        },
        "base_stats": dict(base_stats),
        "base_score": 1_000_000 + int(pp),
        "selected_color": selected,
        "center_ft": 0,
        "center_ff": 0,
    }


def test_skyline_bellman_batch_dedupes_identical_retained_responses(monkeypatch: Any) -> None:
    variant_calls: list[dict[str, Any]] = []
    solve_calls: list[dict[str, Any]] = []

    def fake_fixed_stat_payloads(eval_data: dict[str, Any], **_kwargs: Any):
        variant_calls.append(dict(eval_data["BaseStats"]))
        return [(dict(eval_data), dict(eval_data["BaseStats"]), int(eval_data["BaseScore"]))]

    def fake_solve_bellman_fixed_payload(*, stats: dict[str, Any], **_kwargs: Any):
        solve_calls.append(dict(stats))
        score = 1_000_000 + int(stats["Perfect Points"])
        return SimpleNamespace(best_score=score + 10, best_forced_counts=(1, 2), section_count=2), 3

    monkeypatch.setattr(sfg, "_fixed_stat_payloads_for_bellman", fake_fixed_stat_payloads)
    monkeypatch.setattr(sfg, "_solve_bellman_fixed_payload", fake_solve_bellman_fixed_payload)

    results, stats = sfg._score_skyline_bellman_force_greats_batch(
        prepared=[_prepared(pp=100), _prepared(pp=100), _prepared(pp=101)],
        calc_song=_base_calc_song(),
        ref_arrays={},
    )

    assert variant_calls == [_stats(pp=100), _stats(pp=101)]
    assert solve_calls == [_stats(pp=100), _stats(pp=101)]
    assert stats == {
        "gpu_batches": 2,
        "groups": 1,
        "input_genomes": 3,
        "unique_genomes": 2,
        "deduped_genomes": 1,
        "dedupe_groups": 1,
    }
    assert results[0] == results[1]
    assert results[0] is not results[1]
    assert results[0] is not None
    assert results[2] is not None
    assert results[0]["final_score"] != results[2]["final_score"]


def test_skyline_bellman_batch_keeps_selected_color_responses_separate(monkeypatch: Any) -> None:
    variant_calls: list[dict[str, Any]] = []
    solve_calls: list[dict[str, Any]] = []

    def fake_fixed_stat_payloads(eval_data: dict[str, Any], **_kwargs: Any):
        variant_calls.append(dict(eval_data["BaseStats"]))
        return [(dict(eval_data), dict(eval_data["BaseStats"]), int(eval_data["BaseScore"]))]

    def fake_solve_bellman_fixed_payload(*, stats: dict[str, Any], **_kwargs: Any):
        solve_calls.append(dict(stats))
        return SimpleNamespace(best_score=2_000_000, best_forced_counts=(1, 2), section_count=2), 3

    monkeypatch.setattr(sfg, "_fixed_stat_payloads_for_bellman", fake_fixed_stat_payloads)
    monkeypatch.setattr(sfg, "_solve_bellman_fixed_payload", fake_solve_bellman_fixed_payload)

    results, stats = sfg._score_skyline_bellman_force_greats_batch(
        prepared=[_prepared(pp=100, selected="Power"), _prepared(pp=100, selected="Rush")],
        calc_song=_base_calc_song(),
        ref_arrays={},
    )

    assert len(variant_calls) == 2
    assert solve_calls == [_stats(pp=100), _stats(pp=100)]
    assert stats == {
        "gpu_batches": 2,
        "groups": 2,
        "input_genomes": 2,
        "unique_genomes": 2,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
    }
    assert all(result is not None for result in results)
