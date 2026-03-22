from __future__ import annotations

import configparser

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _mk_gear(*, name: str, slot: str, rng: np.random.Generator) -> dict:
    return {
        "Name": name,
        "type": slot,
        "Perfect Points": int(rng.integers(0, 120)),
        "Combo Multiplier": int(rng.integers(0, 120)),
        "Fever Multiplier": int(rng.integers(0, 120)),
        "Fever Time": int(rng.integers(0, 80)),
        "Fever Fill Rate": int(rng.integers(0, 80)),
        "Beat": int(rng.integers(0, 200)),
        "Vibe": int(rng.integers(0, 200)),
        "Rush": int(rng.integers(0, 200)),
        "Flow": int(rng.integers(0, 200)),
        "Chill": int(rng.integers(0, 200)),
    }


def _mk_mini(*, name: str, rng: np.random.Generator) -> dict:
    # Bias minis towards Beat/Vibe so they reliably match songs with Beat/Vibe colors.
    return {
        "Name": name,
        "Perfect Points": int(rng.integers(0, 50)),
        "Combo Multiplier": int(rng.integers(0, 50)),
        "Fever Multiplier": int(rng.integers(0, 50)),
        "Fever Time": int(rng.integers(0, 30)),
        "Fever Fill Rate": int(rng.integers(0, 30)),
        "Beat": int(rng.integers(50, 250)),
        "Vibe": int(rng.integers(50, 250)),
        "Rush": int(rng.integers(0, 50)),
        "Flow": int(rng.integers(0, 50)),
        "Chill": int(rng.integers(0, 50)),
    }


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_native_ga_winner_refinement_is_enforced(monkeypatch) -> None:
    """
    Regression guard for "hidden top-1 misses" where GPU-native GA can select the correct
    gear/minis but return a suboptimal gem allocation for that loadout.

    Product contract: the GA winner is refined via the canonical registry solver before
    being returned/persisted. If winner refinement is disabled, this guard must fail.
    """
    from gear_optimizer.data.models import GASettings
    from gear_optimizer.solver.genetic import solve_coevolution_genetic
    import gear_optimizer.solver.scoring.fever_solver as fever_solver

    called = {"n": 0}
    refined_score = 2_000_000_000

    def _fake_solve_best_fever_combination(cfg, base_stats, calc_song, ref_arrays, *, silent=False, override_cfg=None):
        called["n"] += 1
        selected_color = ""
        if isinstance(override_cfg, dict):
            selected_color = str(override_cfg.get("selected_color") or "")
        return {
            "Score": int(refined_score),
            "FT": 0,
            "FF": 0,
            "GemCounts": {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Element": 0,
            },
            "Stats": dict(base_stats or {}),
            "Selected Element": selected_color,
        }

    monkeypatch.setattr(fever_solver, "solve_best_fever_combination", _fake_solve_best_fever_combination)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {
        "GPU_Mode": "true",
        "GPU_Native_GA": "true",
    }
    cfg["UserInputStatsGems"] = {
        "fever_time": "0",
        "fever_fill": "0",
        "perfect_points": "0",
        "combo_multiplier": "0",
        "fever_multiplier": "0",
    }
    cfg["ElementalGems"] = {"Beat": "0", "Vibe": "0", "Rush": "0", "Flow": "0", "Chill": "0"}

    rng = np.random.default_rng(1337)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    all_gears: list[dict] = []
    for slot in slots:
        for i in range(6):
            all_gears.append(_mk_gear(name=f"{slot}_{i}", slot=slot, rng=rng))

    all_minis: list[dict] = []
    for i in range(12):
        all_minis.append(_mk_mini(name=f"Mini_{i}", rng=rng))

    gears_by_name = {str(g["Name"]): g for g in all_gears}
    minis_by_name = {str(m["Name"]): m for m in all_minis}

    base_stats_fixed = {
        "Perfect Points": 250,
        "Combo Multiplier": 200,
        "Fever Multiplier": 180,
        "Fever Time": 120,
        "Fever Fill Rate": 110,
        "Beat": 300,
        "Vibe": 310,
        "Rush": 290,
        "Flow": 280,
        "Chill": 270,
    }

    timestamps = np.linspace(0.0, 120.0, 900, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "WinnerRefinementGuard",
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
            "Long Notes": 25,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }

    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }

    ga_settings = GASettings(
        db_seed_prob=0.0,
        fixed_seed_copies=0,
        memetic_elites=0,
        memetic_steps=0,
        memetic_top_gear=1,
        memetic_top_minis=1,
        multi_start=1,
        deep_mining_enabled=False,
        allow_3_swap=False,
        gear_rank_max=10,
        mini_rank_max=10,
        db_seed_mutations=0,
    )

    best_data, _best_gear, _best_minis, _none, _a, _b, _evaluated = solve_coevolution_genetic(
        cfg,
        base_stats_fixed,
        {},  # paths (unused for this synthetic test)
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=True,
        optimize_minis=True,
        ga_depth=2,
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=None,
        executor=None,
        known_loadouts=None,
        song_slot=0,
        ga_seed=123,
    )

    assert called["n"] > 0, "winner refinement did not call solve_best_fever_combination()"
    assert int(best_data.get("Score", 0) or 0) == refined_score

