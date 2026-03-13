from __future__ import annotations

from gear_optimizer.helpers.song_helpers.fg_combo_booster import (
    _finalize_gpu_batch_eval_plan_light,
    hydrate_fg_candidate_stats,
)
from gear_optimizer.solver.scoring.genome_evaluation import prepare_gpu_batch_eval_plan, finalize_gpu_batch_eval_plan
from gear_optimizer.solver.scoring.gpu_solver import GEM_SOLVER_CACHE


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _mk_genome(*, rush_val: int, pp: int) -> list[dict]:
    gear0 = _item(
        "G0",
        **{
            "Perfect Points": pp,
            "Combo Multiplier": 5,
            "Fever Multiplier": 7,
            "Fever Fill Rate": 9,
            "Fever Time": 11,
            "Beat": 3,
            "Vibe": 4,
            # Not part of signature when P/S are Beat/Vibe; used to ensure per-genome Stats differ.
            "Rush": rush_val,
        },
    )
    gear_rest = [_item(f"G{i}") for i in range(1, 6)]
    minis = [_item("M0"), _item("M1"), _item("M2")]
    return [gear0] + gear_rest + minis


def test_fg_combo_booster_light_finalize_hydration_matches_full_finalize() -> None:
    saved_cache = dict(GEM_SOLVER_CACHE)
    GEM_SOLVER_CACHE.clear()
    try:
        base_stats_fixed = {
            "Perfect Points": 1,
            "Combo Multiplier": 2,
            "Fever Multiplier": 3,
            "Fever Time": 4,
            "Fever Fill Rate": 5,
            "Beat": 6,
            "Vibe": 7,
            "Rush": 8,
            "Flow": 9,
            "Chill": 10,
        }

        population = [
            _mk_genome(rush_val=100, pp=10),
            _mk_genome(rush_val=200, pp=10),  # same signature, different irrelevant stats
            _mk_genome(rush_val=300, pp=999),  # different signature
        ]
        cfg_data = {
            "use_gpu": True,
            "selected_color": "Beat",
            "user_ft": 1,
            "user_ff": 2,
            "user_pp": 3,
            "user_cm": 4,
            "user_fm": 5,
            "static_elem_input": 6,
        }
        calc_song = {
            "metadata": {
                "Song Name": "UNITTEST_FG_COMBO_BOOSTER_LIGHT_FINALIZE",
                "Difficulty": "Hard",
                "Primary Color": "Beat",
                "Secondary Color": "Vibe",
            }
        }

        plan, results = prepare_gpu_batch_eval_plan(population, base_stats_fixed, cfg_data, calc_song, ref_arrays={})
        assert plan is not None
        assert results is None
        assert len(plan.unique_stats or []) == 2

        gpu_results = [
            (12345, 1, 2, 3, 4, 5, 6),
            (54321, 7, 8, 9, 10, 11, 12),
        ]

        full = finalize_gpu_batch_eval_plan(plan, gpu_results)
        light = _finalize_gpu_batch_eval_plan_light(plan, gpu_results)

        assert len(light) == len(full) == len(population)
        assert all(isinstance(c, dict) and "Data" not in c for c in light)
        assert all(isinstance(c.get("BaseStats"), dict) and c["BaseStats"] for c in light)

        hydrate_fg_candidate_stats(
            light, base_stats_fixed=base_stats_fixed, selected_color=str(cfg_data["selected_color"])
        )

        for i in range(len(population)):
            assert light[i]["Score"] == full[i]["Score"]
            assert light[i]["BaseScore"] == full[i]["BaseScore"]
            assert light[i]["Data"]["FT"] == full[i]["Data"]["FT"]
            assert light[i]["Data"]["FF"] == full[i]["Data"]["FF"]
            assert light[i]["Data"]["GemCounts"] == full[i]["Data"]["GemCounts"]
            assert light[i]["Data"]["Selected Element"] == full[i]["Data"]["Selected Element"]
            assert light[i]["Data"]["Stats"] == full[i]["Data"]["Stats"]
    finally:
        GEM_SOLVER_CACHE.clear()
        GEM_SOLVER_CACHE.update(saved_cache)
