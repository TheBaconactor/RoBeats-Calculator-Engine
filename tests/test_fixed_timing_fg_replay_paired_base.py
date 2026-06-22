from __future__ import annotations

from types import SimpleNamespace

from gear_optimizer.solver.fg_response_scoring import fixed_timing


def test_fixed_timing_fg_replay_pairs_base_to_resolved_stats(monkeypatch):
    gem_less_stats = {"Perfect Points": 0, "Beat": 100}
    resolved_stats = {"Perfect Points": 25, "Beat": 778}
    solved_result = SimpleNamespace(surface=object(), stats=resolved_stats)
    captured: dict[str, object] = {}

    def fake_solve(fg_rows, calc_song, ref_arrays, selected_color, total_budget=0):
        captured["solve_rows"] = [dict(row) for row in fg_rows]
        captured["total_budget"] = int(total_budget)
        return [solved_result], {"song": "zero_ms"}, {"refs": "exact"}

    def fake_score_stats(rows, calc_song, ref_arrays):
        captured["paired_base_rows"] = [dict(row) for row in rows]
        captured["paired_calc_song"] = calc_song
        captured["paired_ref_arrays"] = ref_arrays
        return [112_366_848]

    def fake_materialize(
        *,
        eval_data,
        base_stats,
        paired_base_score,
        selected_element,
        result,
        calc_song,
        ref_arrays,
    ):
        captured["materialized_base_stats"] = dict(base_stats)
        captured["materialized_base_score"] = int(paired_base_score)
        return {
            "Score": 112_516_669,
            "BaseScore": int(paired_base_score),
            "Stats": dict(result.stats),
            "BaseStats": dict(base_stats),
            "ForceGreats": {"config": {"NonFever1": 3, "NonFever2": 5}},
        }

    monkeypatch.setattr(fixed_timing, "_solve_fixed_timing_response_results", fake_solve)
    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.exact_rescore.score_stats_fixed_timing_exact_batch",
        fake_score_stats,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.fg_response_scoring.reducer.materialize_force_payload_from_response_frontier",
        fake_materialize,
    )

    replays = fixed_timing.build_fixed_timing_fg_replays(
        fg_stats_list=[gem_less_stats],
        base_stats_list=[gem_less_stats],
        calc_song={},
        ref_arrays={},
        selected_color="Beat",
        total_budget=90,
    )

    assert captured["solve_rows"] == [gem_less_stats]
    assert captured["total_budget"] == 90
    assert captured["paired_base_rows"] == [resolved_stats]
    assert captured["materialized_base_stats"] == resolved_stats
    assert captured["materialized_base_score"] == 112_366_848
    assert replays == [
        {
            "surface": solved_result.surface,
            "force": {
                "Score": 112_516_669,
                "BaseScore": 112_366_848,
                "Stats": resolved_stats,
                "BaseStats": resolved_stats,
                "ForceGreats": {"config": {"NonFever1": 3, "NonFever2": 5}},
            },
        }
    ]
