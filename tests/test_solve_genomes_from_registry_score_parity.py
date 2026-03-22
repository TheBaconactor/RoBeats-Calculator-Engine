from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_upload_base_fixed_stats, ga_upload_item_stats
from gear_optimizer.solver.taichi_gem.api.parallel_solvers import solve_genomes_from_registry, solve_genomes_with_ftff


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


@pytest.mark.gpu
@pytest.mark.parametrize(
    "use_block_kernel",
    [False, True],
    ids=["ftff_per_genome_kernel", "ftff_block_kernel_strict_raises"],
)
def test_solve_genomes_from_registry_matches_parallel_scores_with_user_gems_and_static_overflow(
    use_block_kernel: bool,
    monkeypatch,
) -> None:
    # Ensure we cover BOTH FT/FF solver paths:
    # - portable per-genome loop (default)
    # - Vulkan block-per-genome kernel (opt-in; previously had payload-parity bugs)
    import gear_optimizer.solver.taichi_gem.api.parallel_solvers as parallel_solvers

    monkeypatch.setattr(parallel_solvers, "_USE_FTFF_BLOCK_KERNEL", bool(use_block_kernel))

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
                        "Fever Time": int(rng.integers(0, 80)),
                        "Fever Fill Rate": int(rng.integers(0, 80)),
                        "Beat": int(rng.integers(0, 200)),
                        "Vibe": int(rng.integers(0, 200)),
                        "Rush": int(rng.integers(0, 200)),
                        "Flow": int(rng.integers(0, 200)),
                        "Chill": int(rng.integers(0, 200)),
                    },
                )
            )
        return items

    gear_pool = {slot: make_item_pool(f"{slot}_", 12) for slot in slots}
    mini_pool = make_item_pool("Mini_", 20)

    registry = ItemRegistry(gear_pool, mini_pool, slots)

    # Non-zero user gems + static elemental gems (exercise the base_fixed_stats adjustment path).
    user_ft = 2
    user_ff = 3
    user_pp = 1
    user_cm = 2
    user_fm = 1
    static_elem_input = 7

    p_color = "Vibe"
    s_color = "Beat"
    selected_color = "Vibe"

    timestamps = np.linspace(0.0, 120.0, 800, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "RegistryParity",
            "Primary Color": p_color,
            "Secondary Color": s_color,
            "Long Notes": 25,
            "Last Note Time": 120.0,
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

    flags = {
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

    # Build random genomes.
    n_genomes = 64
    genomes: list[list[dict]] = []
    for _ in range(n_genomes):
        gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
        minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
        genomes.append(gear + minis)

    # CPU-side genome_stats_list for solve_genomes_with_ftff (match prepare_gpu_batch_eval_plan).
    genome_stats_list: list[dict] = []
    for genome in genomes:
        stats = dict(base_stats_fixed)
        for item in genome:
            for k, v in item.items():
                if k == "Name":
                    continue
                stats[k] = int(stats.get(k, 0)) + int(v)

        base_pp = int(stats.get("Perfect Points", 0)) - user_pp * GEM_SCALE_NORMAL
        base_cm = int(stats.get("Combo Multiplier", 0)) - user_cm * GEM_SCALE_NORMAL
        base_fm = int(stats.get("Fever Multiplier", 0)) - user_fm * GEM_SCALE_FEVER
        base_ft_stat = int(stats.get("Fever Time", 0)) - user_ft * GEM_SCALE_FEVER
        base_ff_stat = int(stats.get("Fever Fill Rate", 0)) - user_ff * GEM_SCALE_FEVER

        base_beat = int(stats.get("Beat", 0)) - user_ft * GEM_STAT_TO_ELEMENT_SCALE
        base_vibe = int(stats.get("Vibe", 0)) - user_ff * GEM_STAT_TO_ELEMENT_SCALE
        base_rush = int(stats.get("Rush", 0)) - user_fm * GEM_STAT_TO_ELEMENT_SCALE
        base_flow = int(stats.get("Flow", 0)) - user_cm * GEM_STAT_TO_ELEMENT_SCALE
        base_chill = int(stats.get("Chill", 0)) - user_pp * GEM_STAT_TO_ELEMENT_SCALE

        if static_elem_input and selected_color:
            if selected_color == "Beat":
                base_beat -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif selected_color == "Vibe":
                base_vibe -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif selected_color == "Rush":
                base_rush -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif selected_color == "Flow":
                base_flow -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif selected_color == "Chill":
                base_chill -= static_elem_input * ELEMENTAL_GEM_SCALE

        color_vals = {"Beat": base_beat, "Vibe": base_vibe, "Rush": base_rush, "Flow": base_flow, "Chill": base_chill}
        base_p_val = int(color_vals.get(p_color, 0))
        base_s_val = int(color_vals.get(s_color, 0))

        genome_stats_list.append(
            {
                "base_pp": base_pp,
                "base_cm": base_cm,
                "base_fm": base_fm,
                "base_p_val": base_p_val,
                "base_s_val": base_s_val,
                "base_ft_stat": base_ft_stat,
                "base_ff_stat": base_ff_stat,
            }
        )

    pop_indices = registry.encode_population(genomes)
    gpu_arrays = registry.to_gpu_arrays()

    base_fixed_stats_arr = np.array(
        [
            base_stats_fixed["Perfect Points"] - user_pp * GEM_SCALE_NORMAL,
            base_stats_fixed["Combo Multiplier"] - user_cm * GEM_SCALE_NORMAL,
            base_stats_fixed["Fever Multiplier"] - user_fm * GEM_SCALE_FEVER,
            base_stats_fixed["Fever Time"] - user_ft * GEM_SCALE_FEVER,
            base_stats_fixed["Fever Fill Rate"] - user_ff * GEM_SCALE_FEVER,
            base_stats_fixed["Beat"] - user_ft * GEM_STAT_TO_ELEMENT_SCALE,
            base_stats_fixed["Vibe"] - user_ff * GEM_STAT_TO_ELEMENT_SCALE,
            base_stats_fixed["Rush"] - user_fm * GEM_STAT_TO_ELEMENT_SCALE,
            base_stats_fixed["Flow"] - user_cm * GEM_STAT_TO_ELEMENT_SCALE,
            base_stats_fixed["Chill"] - user_pp * GEM_STAT_TO_ELEMENT_SCALE,
        ],
        dtype=np.int32,
    )
    if static_elem_input and selected_color:
        color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
        idx = color_to_idx.get(selected_color)
        if idx is not None:
            base_fixed_stats_arr[idx] -= static_elem_input * ELEMENTAL_GEM_SCALE

    with _GPU_LOCK:
        ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
        ga_upload_base_fixed_stats(base_fixed_stats_arr)

        if use_block_kernel:
            # The experimental block kernel is explicitly guarded by the fallback monitor and
            # must fail-fast under strict policy (production default).
            from gear_optimizer.core.fallback_monitor import FallbackViolation

            monkeypatch.setenv("METAFINDER_FALLBACK_STRICT", "1")
            with pytest.raises(FallbackViolation):
                solve_genomes_with_ftff(
                    genome_stats_list,
                    calc_song,
                    flags["is_p_ft"],
                    flags["is_s_ft"],
                    flags["is_p_ff"],
                    flags["is_s_ff"],
                    flags["is_p_pp"],
                    flags["is_s_pp"],
                    flags["is_p_cm"],
                    flags["is_s_cm"],
                    flags["is_p_fm"],
                    flags["is_s_fm"],
                    flags["is_p_ov"],
                    flags["is_s_ov"],
                    ref_arrays,
                    total_budget=TOTAL_GEM_BUDGET,
                    gem_scale_fever=GEM_SCALE_FEVER,
                )
            return

        # Repeat to catch nondeterministic payload/parity issues (the exact class of GPU races
        # that previously caused multi-day debugging incidents).
        for _rep in range(3):
            parallel = solve_genomes_with_ftff(
                genome_stats_list,
                calc_song,
                flags["is_p_ft"],
                flags["is_s_ft"],
                flags["is_p_ff"],
                flags["is_s_ff"],
                flags["is_p_pp"],
                flags["is_s_pp"],
                flags["is_p_cm"],
                flags["is_s_cm"],
                flags["is_p_fm"],
                flags["is_s_fm"],
                flags["is_p_ov"],
                flags["is_s_ov"],
                ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
            )

            registry_res = solve_genomes_from_registry(
                pop_indices,
                calc_song,
                flags["is_p_ft"],
                flags["is_s_ft"],
                flags["is_p_ff"],
                flags["is_s_ff"],
                flags["is_p_pp"],
                flags["is_s_pp"],
                flags["is_p_cm"],
                flags["is_s_cm"],
                flags["is_p_fm"],
                flags["is_s_fm"],
                flags["is_p_ov"],
                flags["is_s_ov"],
                ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
            )

            assert len(parallel) == len(registry_res) == n_genomes
            assert [int(t[0]) for t in parallel] == [int(t[0]) for t in registry_res]
