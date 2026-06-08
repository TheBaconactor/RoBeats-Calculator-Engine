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
    }


def _fake_score_batch(fake_solve):
    def _score_batch(batch, **_kwargs):
        base_stats = dict(batch.base_stats_list[0])
        selected_color = str(getattr(batch, "selected_color", "") or "")
        return [fake_solve(base_stats=base_stats, selected_color=selected_color)]

    return _score_batch


def test_skyline_response_batch_dedupes_identical_retained_responses(monkeypatch: Any) -> None:
    solve_calls: list[dict[str, Any]] = []
    sentinel_a = object()
    sentinel_b = object()

    def fake_solve(*, base_stats: dict[str, Any], **_kwargs: Any):
        solve_calls.append(dict(base_stats))
        return sentinel_a if int(base_stats["Perfect Points"]) == 100 else sentinel_b

    def _fake_prepare(*, base_stats_list, selected_color, **_kwargs):
        return SimpleNamespace(
            base_stats_list=[dict(base_stats_list[0])],
            selected_color=str(selected_color or ""),
        )

    monkeypatch.setattr(sfg, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare)
    monkeypatch.setattr(
        sfg,
        "score_prepared_force_greats_response_frontier_batch_sync",
        _fake_score_batch(fake_solve),
    )

    results, stats = sfg._score_skyline_response_force_greats_batch(
        prepared=[_prepared(pp=100), _prepared(pp=100), _prepared(pp=101)],
        calc_song=_base_calc_song(),
        ref_arrays={},
    )

    assert solve_calls == [_stats(pp=100), _stats(pp=101)]
    assert stats == {
        "gpu_batches": 2,
        "groups": 1,
        "input_genomes": 3,
        "unique_genomes": 2,
        "deduped_genomes": 1,
        "dedupe_groups": 1,
    }
    assert results == [sentinel_a, sentinel_a, sentinel_b]


def test_skyline_response_batch_keeps_selected_color_responses_separate(monkeypatch: Any) -> None:
    solve_calls: list[tuple[str, dict[str, Any]]] = []

    def fake_solve(*, base_stats: dict[str, Any], selected_color: str, **_kwargs: Any):
        solve_calls.append((str(selected_color), dict(base_stats)))
        return object()

    def _fake_prepare(*, base_stats_list, selected_color, **_kwargs):
        return SimpleNamespace(
            base_stats_list=[dict(base_stats_list[0])],
            selected_color=str(selected_color or ""),
        )

    monkeypatch.setattr(sfg, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare)
    monkeypatch.setattr(
        sfg,
        "score_prepared_force_greats_response_frontier_batch_sync",
        _fake_score_batch(fake_solve),
    )

    results, stats = sfg._score_skyline_response_force_greats_batch(
        prepared=[_prepared(pp=100, selected="Power"), _prepared(pp=100, selected="Rush")],
        calc_song=_base_calc_song(),
        ref_arrays={},
    )

    assert solve_calls == [("Power", _stats(pp=100)), ("Rush", _stats(pp=100))]
    assert stats == {
        "gpu_batches": 2,
        "groups": 2,
        "input_genomes": 2,
        "unique_genomes": 2,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
    }
    assert len(results) == 2
