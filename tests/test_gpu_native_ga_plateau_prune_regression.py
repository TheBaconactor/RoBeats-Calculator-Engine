from __future__ import annotations

import os

import numpy as np
import pytest

from gear_optimizer.core.constants import GEM_SCALE_FEVER
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
from gear_optimizer.solver.taichi_gem.api.ga_operations import (
    ga_download_results,
    ga_evaluate_population,
    ga_upload_base_fixed_stats,
    ga_upload_item_stats,
    ga_upload_population_indices,
    ga_write_best_and_update_global,
)
from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu


from gear_optimizer.core.parsing import env_get
pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _make_calc_song(*, name: str, p_color: str, s_color: str, n: int = 800) -> dict:
    ts = np.linspace(0.0, 120.0, n, dtype=np.float32)
    return {
        "metadata": {
            "Song Name": name,
            "Primary Color": p_color,
            "Secondary Color": s_color,
            "Long Notes": 25,
            "Last Note Time": float(ts[-1]),
        },
        "song_data": {"timestamps": ts},
    }


def _color_flags(*, p_color: str, s_color: str, selected_color: str) -> dict[str, int]:
    return {
        "is_p_pp": 1 if p_color == "Chill" else 0,
        "is_s_pp": 1 if s_color == "Chill" else 0,
        "is_p_cm": 1 if p_color == "Flow" else 0,
        "is_s_cm": 1 if s_color == "Flow" else 0,
        "is_p_fm": 1 if p_color == "Rush" else 0,
        "is_s_fm": 1 if s_color == "Rush" else 0,
        "is_p_ov": 1 if selected_color == p_color else 0,
        "is_s_ov": 1 if selected_color == s_color else 0,
        "is_p_ft": 1 if p_color == "Beat" else 0,
        "is_s_ft": 1 if s_color == "Beat" else 0,
        "is_p_ff": 1 if p_color == "Vibe" else 0,
        "is_s_ff": 1 if s_color == "Vibe" else 0,
    }


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_native_ga_plateau_prune_score_regression_off_vs_on() -> None:
    trials = int(env_get("PLATEAU_PRUNE_REGRESSION_TRIALS", "20"))
    n_genomes = int(env_get("PLATEAU_PRUNE_REGRESSION_GENOMES", "96"))
    total_budget = int(env_get("PLATEAU_PRUNE_REGRESSION_BUDGET", "30"))

    rng = np.random.default_rng(1337)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def make_item_pool(prefix: str, n: int) -> list[dict]:
        items: list[dict] = []
        for i in range(n):
            items.append(
                _mk_item(
                    f"{prefix}{i}",
                    **{
                        "Perfect Points": int(rng.integers(0, 120)),
                        "Combo Multiplier": int(rng.integers(0, 120)),
                        "Fever Multiplier": int(rng.integers(0, 120)),
                        "Fever Time": int(rng.integers(0, 120)),
                        "Fever Fill Rate": int(rng.integers(0, 120)),
                        "Beat": int(rng.integers(0, 200)),
                        "Vibe": int(rng.integers(0, 200)),
                        "Rush": int(rng.integers(0, 200)),
                        "Flow": int(rng.integers(0, 200)),
                        "Chill": int(rng.integers(0, 200)),
                    },
                )
            )
        return items

    gear_pool = {slot: make_item_pool(f"{slot}_", 14) for slot in slots}
    mini_pool = make_item_pool("Mini_", 24)
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    base_stats_fixed = {
        "Perfect Points": 250,
        "Combo Multiplier": 200,
        "Fever Multiplier": 180,
        "Fever Time": 150,
        "Fever Fill Rate": 150,
        "Beat": 300,
        "Vibe": 310,
        "Rush": 290,
        "Flow": 280,
        "Chill": 270,
    }
    base_fixed_stats_arr = np.array(
        [
            base_stats_fixed["Perfect Points"],
            base_stats_fixed["Combo Multiplier"],
            base_stats_fixed["Fever Multiplier"],
            base_stats_fixed["Fever Time"],
            base_stats_fixed["Fever Fill Rate"],
            base_stats_fixed["Beat"],
            base_stats_fixed["Vibe"],
            base_stats_fixed["Rush"],
            base_stats_fixed["Flow"],
            base_stats_fixed["Chill"],
        ],
        dtype=np.int32,
    )

    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }

    songs = [
        (
            _make_calc_song(name="PlateauPrune_ChillFlow", p_color="Chill", s_color="Flow"),
            _color_flags(p_color="Chill", s_color="Flow", selected_color="Chill"),
        ),
        (
            _make_calc_song(name="PlateauPrune_BeatVibe", p_color="Beat", s_color="Vibe"),
            _color_flags(p_color="Beat", s_color="Vibe", selected_color="Beat"),
        ),
    ]

    def eval_scores(*, prune: int, flags: dict[str, int]) -> np.ndarray:
        old = env_get("GPU_NATIVE_GA_PLATEAU_PRUNE")
        os.environ["GPU_NATIVE_GA_PLATEAU_PRUNE"] = "1" if prune else "0"
        try:
            ga_evaluate_population(
                n_genomes=n_genomes,
                n_slots=9,
                total_budget=total_budget,
                gem_scale_fever=GEM_SCALE_FEVER,
                song_slot=0,
                is_p_ft=flags["is_p_ft"],
                is_s_ft=flags["is_s_ft"],
                is_p_ff=flags["is_p_ff"],
                is_s_ff=flags["is_s_ff"],
                is_p_pp=flags["is_p_pp"],
                is_s_pp=flags["is_s_pp"],
                is_p_cm=flags["is_p_cm"],
                is_s_cm=flags["is_s_cm"],
                is_p_fm=flags["is_p_fm"],
                is_s_fm=flags["is_s_fm"],
                is_p_ov=flags["is_p_ov"],
                is_s_ov=flags["is_s_ov"],
            )
            ga_write_best_and_update_global(
                n_genomes=n_genomes,
                n_slots=9,
                total_budget=total_budget,
                gem_scale_fever=GEM_SCALE_FEVER,
                song_slot=0,
                is_p_ft=flags["is_p_ft"],
                is_s_ft=flags["is_s_ft"],
                is_p_ff=flags["is_p_ff"],
                is_s_ff=flags["is_s_ff"],
                is_p_pp=flags["is_p_pp"],
                is_s_pp=flags["is_s_pp"],
                is_p_cm=flags["is_p_cm"],
                is_s_cm=flags["is_s_cm"],
                is_p_fm=flags["is_p_fm"],
                is_s_fm=flags["is_s_fm"],
                is_p_ov=flags["is_p_ov"],
                is_s_ov=flags["is_s_ov"],
            )
            results = ga_download_results(n_genomes)
            return np.asarray(results[:, 0], dtype=np.int32).copy()
        finally:
            if old is None:
                os.environ.pop("GPU_NATIVE_GA_PLATEAU_PRUNE", None)
            else:
                os.environ["GPU_NATIVE_GA_PLATEAU_PRUNE"] = old

    with _GPU_LOCK:
        ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
        ga_upload_base_fixed_stats(base_fixed_stats_arr)

        for calc_song, flags in songs:
            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

            mismatched = 0
            for _ in range(trials):
                genomes: list[list[dict]] = []
                for _g in range(n_genomes):
                    gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
                    minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
                    genomes.append(gear + minis)

                pop_indices = registry.encode_population(genomes)
                ga_upload_population_indices(pop_indices, n_slots=9)

                off_scores = eval_scores(prune=0, flags=flags)
                on_scores = eval_scores(prune=1, flags=flags)

                if not np.array_equal(off_scores, on_scores):
                    mismatched += 1

            assert mismatched == 0, (
                f"{calc_song['metadata']['Song Name']}: mismatched score trials={mismatched}/{trials}"
            )
