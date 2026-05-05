"""
Repro: GPU registry eval vs parallel FT/FF eval mismatch.

This mirrors `tests/test_solve_genomes_from_registry_score_parity.py` but prints
diagnostics (base stats seen by GPU, per-genome outputs) to help isolate the
root cause of score mismatches/regressions.

Run from repo root:
  python scripts/debug/repro_registry_parallel_parity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Ensure repo root is on sys.path when running this file directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
from gear_optimizer.solver.taichi_gem import fields
from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels
from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_upload_base_fixed_stats, ga_upload_item_stats
from gear_optimizer.solver.taichi_gem.api.parallel_solvers import solve_genomes_from_registry, solve_genomes_with_ftff


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _calc_score_py_bits(
    *,
    base_value: np.float32,
    combo_mul: np.float32,
    fever_mul: np.float32,
    m0: np.uint32,
    m1: np.uint32,
    m2: np.uint32,
    m3: np.uint32,
    head_len: int,
    count_fever: int,
    count_normal: int,
) -> int:
    # Match Taichi semantics: f32 math + i32 truncation per term.
    base_value = np.float32(base_value)
    combo_mul = np.float32(combo_mul)
    fever_mul = np.float32(fever_mul)
    head_len = max(0, min(int(head_len), 100))
    count_fever = int(count_fever)
    count_normal = int(count_normal)

    combo_val = int(np.int32(base_value * combo_mul))
    fever_val = int(np.int32(base_value * combo_mul * fever_mul))
    body_score = (count_fever * fever_val) + (count_normal * combo_val)

    factor = np.float32((combo_mul - np.float32(1.0)) * base_value / np.float32(100.0))
    fever_delta = np.float32(fever_mul - np.float32(1.0))

    head_score = 0
    for i in range(head_len):
        if i < 32:
            is_fever = (int(m0) >> i) & 1
        elif i < 64:
            is_fever = (int(m1) >> (i - 32)) & 1
        elif i < 96:
            is_fever = (int(m2) >> (i - 64)) & 1
        else:
            is_fever = (int(m3) >> (i - 96)) & 1

        t = np.float32(i + 1)
        ramp = np.float32(base_value + (t * factor))
        mul = np.float32(1.0 + fever_delta * np.float32(is_fever))
        head_score += int(np.int32(ramp * mul))

    return int(body_score + head_score)


def main() -> None:
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

        # Sanity: read back base_fixed_stats immediately after upload.
        base_fixed_gpu = fields.base_fixed_stats.to_numpy().astype(np.int32, copy=False)
        print("base_fixed_stats_arr (host):", base_fixed_stats_arr.tolist())
        print("base_fixed_stats (gpu):     ", base_fixed_gpu[:10].tolist())

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
        base_stats_after_parallel = fields.genome_base_stats.to_numpy()[:n_genomes].astype(np.int32, copy=False)

        # Run the portable per-genome kernel directly (no block/subgroup reduction) to isolate block-kernel issues.
        kern = get_kernels()
        kern.solve_genomes_with_ftff_kernel(
            int(n_genomes),
            int(TOTAL_GEM_BUDGET),
            int(GEM_SCALE_FEVER),
            int(flags["is_p_ft"]),
            int(flags["is_s_ft"]),
            int(flags["is_p_ff"]),
            int(flags["is_s_ff"]),
            int(flags["is_p_pp"]),
            int(flags["is_s_pp"]),
            int(flags["is_p_cm"]),
            int(flags["is_s_cm"]),
            int(flags["is_p_fm"]),
            int(flags["is_s_fm"]),
            int(flags["is_p_ov"]),
            int(flags["is_s_ov"]),
            0,
        )
        portable_np = fields.genome_result_stats.to_numpy()[:n_genomes].astype(np.int32, copy=False)
        portable = [tuple(row) for row in portable_np[:, :7].tolist()]

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
        base_stats_after_registry = fields.genome_base_stats.to_numpy()[:n_genomes].astype(np.int32, copy=False)

        # Re-run parallel after registry to see if the mismatch is a "first-run" ordering issue.
        parallel2 = solve_genomes_with_ftff(
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

    print("\nFirst 5 results: (score, ft, ff, pp, cm, fm, ov)")
    for i in range(5):
        print(f"  g{i:02d} parallel={parallel[i]} registry={registry_res[i]}")
    print("\nFirst 5 results (portable kernel):")
    for i in range(5):
        print(f"  g{i:02d} portable={portable[i]} registry={registry_res[i]}")
    print("\nFirst 5 results (parallel2 after registry):")
    for i in range(5):
        print(f"  g{i:02d} parallel2={parallel2[i]} registry={registry_res[i]}")

    scores_parallel = np.array([int(t[0]) for t in parallel], dtype=np.int64)
    scores_parallel2 = np.array([int(t[0]) for t in parallel2], dtype=np.int64)
    scores_portable = np.array([int(t[0]) for t in portable], dtype=np.int64)
    scores_registry = np.array([int(t[0]) for t in registry_res], dtype=np.int64)
    mismatch = np.nonzero(scores_parallel != scores_registry)[0]
    print(f"\nScore mismatches: {len(mismatch)}/{n_genomes}")
    mismatch2 = np.nonzero(scores_parallel2 != scores_registry)[0]
    print(f"Score mismatches (parallel2): {len(mismatch2)}/{n_genomes}")
    mismatch_portable = np.nonzero(scores_portable != scores_registry)[0]
    print(f"Score mismatches (portable): {len(mismatch_portable)}/{n_genomes}")
    if mismatch.size:
        i = int(mismatch[0])
        print("first mismatch idx:", i)
        print("parallel:", parallel[i])
        print("registry:", registry_res[i])

        cpu_stats = np.array(
            [
                genome_stats_list[i]["base_pp"],
                genome_stats_list[i]["base_cm"],
                genome_stats_list[i]["base_fm"],
                genome_stats_list[i]["base_p_val"],
                genome_stats_list[i]["base_s_val"],
                genome_stats_list[i]["base_ft_stat"],
                genome_stats_list[i]["base_ff_stat"],
            ],
            dtype=np.int32,
        )
        print("\nbase stats g0 (cpu expected):", cpu_stats.tolist())
        print("base stats g0 (after parallel upload):", base_stats_after_parallel[i, :7].tolist())
        print("base stats g0 (after registry aggregate):", base_stats_after_registry[i, :7].tolist())

        diff_parallel = base_stats_after_parallel[i, :7] - cpu_stats
        diff_registry = base_stats_after_registry[i, :7] - cpu_stats
        print("delta (parallel - cpu):", diff_parallel.tolist())
        print("delta (registry - cpu):", diff_registry.tolist())

        # Recompute score in pure Python from the bitpacked grid to identify the correct path.
        ft = int(parallel[i][1])
        ff = int(parallel[i][2])
        pp_g = int(parallel[i][3])
        cm_g = int(parallel[i][4])
        fm_g = int(parallel[i][5])
        ov_g = int(parallel[i][6])

        MAX_STAT = 160
        GEM_STAT_TO_ELEMENT = 3
        elemental_gem_scale = int(ELEMENTAL_GEM_SCALE)

        ft_idx = min(MAX_STAT, max(0, int(cpu_stats[5] + ft * GEM_SCALE_FEVER)))
        ff_idx = min(MAX_STAT, max(0, int(cpu_stats[6] + ff * GEM_SCALE_FEVER)))

        # Pull the single (ft_idx, ff_idx) cell from the GPU grid.
        cbf = int(fields.grid_count_body_fever.to_numpy()[0, ft_idx, ff_idx])
        cbn = int(fields.grid_count_body_normal.to_numpy()[0, ft_idx, ff_idx])
        hl = int(fields.grid_head_len.to_numpy()[0, ft_idx, ff_idx])
        bits = fields.grid_fever_masks_bits.to_numpy()[0, ft_idx, ff_idx, :4]
        m0, m1, m2, m3 = (np.uint32(bits[0]), np.uint32(bits[1]), np.uint32(bits[2]), np.uint32(bits[3]))

        # Stat factors (GPU fields are f32).
        pp_stat = min(MAX_STAT, int(cpu_stats[0] + pp_g * GEM_SCALE_NORMAL))
        cm_stat = min(MAX_STAT, int(cpu_stats[1] + cm_g * GEM_SCALE_NORMAL))
        fm_stat = min(MAX_STAT, int(cpu_stats[2] + fm_g * GEM_SCALE_FEVER))

        ref_pp = np.asarray(ref_arrays["Perfect Points"], dtype=np.float32)
        ref_cm = np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32)
        ref_fm = np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32)
        pp_factor = np.float32(ref_pp[min(MAX_STAT, max(0, pp_stat))])
        combo_mul = np.float32(ref_cm[min(MAX_STAT, max(0, cm_stat))])
        fever_mul = np.float32(ref_fm[min(MAX_STAT, max(0, fm_stat))])

        # Element totals after gems.
        p_val = int(cpu_stats[3] + (ft * GEM_STAT_TO_ELEMENT * flags["is_p_ft"]) + (ff * GEM_STAT_TO_ELEMENT * flags["is_p_ff"]))
        s_val = int(cpu_stats[4] + (ft * GEM_STAT_TO_ELEMENT * flags["is_s_ft"]) + (ff * GEM_STAT_TO_ELEMENT * flags["is_s_ff"]))
        p_val += pp_g * GEM_STAT_TO_ELEMENT * flags["is_p_pp"]
        p_val += cm_g * GEM_STAT_TO_ELEMENT * flags["is_p_cm"]
        p_val += fm_g * GEM_STAT_TO_ELEMENT * flags["is_p_fm"]
        p_val += ov_g * elemental_gem_scale * flags["is_p_ov"]
        s_val += pp_g * GEM_STAT_TO_ELEMENT * flags["is_s_pp"]
        s_val += cm_g * GEM_STAT_TO_ELEMENT * flags["is_s_cm"]
        s_val += fm_g * GEM_STAT_TO_ELEMENT * flags["is_s_fm"]
        s_val += ov_g * elemental_gem_scale * flags["is_s_ov"]

        base_value = np.float32((p_val * 2) + s_val) + pp_factor
        py_score = _calc_score_py_bits(
            base_value=base_value,
            combo_mul=combo_mul,
            fever_mul=fever_mul,
            m0=m0,
            m1=m1,
            m2=m2,
            m3=m3,
            head_len=hl,
            count_fever=cbf,
            count_normal=cbn,
        )

        print("\npython score (bits):", int(py_score))
        print("parallel score:", int(parallel[i][0]))
        print("portable score:", int(portable[i][0]))
        print("registry score:", int(registry_res[i][0]))


if __name__ == "__main__":
    main()
