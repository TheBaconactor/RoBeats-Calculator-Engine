"""Micro-benchmark for the GA eval kernel in isolation (Vulkan).

Uploads one real song's device state (timeline + items + a seeded population),
then times ``ga_prepare_population_base_stats`` + ``ga_evaluate_prepared_population``
over many iterations with a trailing ti.sync() per iteration. This isolates the
eval kernel from the full pipeline so block-dim / grid-layout experiments get a
fast, low-variance signal.

Usage:
  python tools/dev/bench_ga_eval.py [--genomes 705] [--iters 80] [--warmup 15]

Prints: block_dim, n_combos, mean/p50/min eval-call ms over the timed iters.
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_PRIMARY, _SECONDARY, _SELECTED = "Beat", "Flow", "Rush"
_N_SLOTS = 9
_TOTAL_BUDGET = 90
_GEM_SCALE_FEVER = 3
_SONG_SLOT = 0


def _item(name, **stats):
    out = {"Name": name}
    out.update(stats)
    return out


def _build_registry():
    from gear_optimizer.solver.item_registry import ItemRegistry

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {}
    for s_idx, slot in enumerate(slots):
        gear_pool[slot] = [
            _item(
                f"{slot}{i}",
                **{
                    "Perfect Points": 7 + s_idx + i, "Combo Multiplier": 3 + i,
                    "Fever Multiplier": 2 + s_idx, "Fever Time": 4 + i, "Fever Fill Rate": 5 + s_idx,
                    "Beat": 6 + i, "Vibe": 2 + s_idx, "Rush": 3 + i, "Flow": 4 + s_idx, "Chill": 1 + i,
                },
            )
            for i in range(4)
        ]
    mini_pool = [
        _item(
            f"M{i}",
            **{
                "Perfect Points": 2 + (i % 5), "Combo Multiplier": 1 + (i % 3),
                "Fever Multiplier": 1 + (i % 4), "Fever Time": 1 + (i % 2), "Fever Fill Rate": 2 + (i % 3),
                "Beat": 1 + (i % 4), "Vibe": 2 + (i % 2), "Rush": 1 + (i % 5), "Flow": 3 + (i % 2), "Chill": 1 + (i % 3),
            },
        )
        for i in range(12)
    ]
    return ItemRegistry(gear_pool, mini_pool, slots)


def _ref_arrays():
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(n_notes=400):
    ts = np.linspace(0, 90, n_notes, dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "ga eval bench", "Difficulty": "Hard",
            "Primary Color": _PRIMARY, "Secondary Color": _SECONDARY,
            "Total Notes": n_notes, "Long Notes": 10, "Last Note Time": float(ts[-1]),
            "TimingEnvelopeApplied": True, "TimingEnvelopeMode": "perfect", "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": ts},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genomes", type=int, default=705)
    ap.add_argument("--iters", type=int, default=80)
    ap.add_argument("--warmup", type=int, default=15)
    ns = ap.parse_args()

    import importlib

    import taichi as ti

    from gear_optimizer.core.color_flags import build_color_flags, normalize_color_flags
    from gear_optimizer.solver import genetic_pipeline as genetic
    from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    n_genomes = int(ns.genomes)

    reg = _build_registry()
    arr = reg.to_gpu_arrays()
    item_stats = np.asarray(arr["item_stats"], dtype=np.int32)
    slot_start = np.asarray(arr["slot_start"], dtype=np.int32)
    slot_count = np.asarray(arr["slot_count"], dtype=np.int32)
    base_fixed, _ = genetic.build_base_fixed_stats_array(
        {}, {"selected_color": _SELECTED, "primary_color": _PRIMARY, "secondary_color": _SECONDARY}
    )
    base_fixed = np.asarray(base_fixed, dtype=np.int32)
    flags = normalize_color_flags(build_color_flags(_PRIMARY, _SECONDARY, _SELECTED)).as_tuple()
    (is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
     is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov) = flags

    calc, refs = _calc_song(), _ref_arrays()

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc, refs)
        precompute_timeline_gpu(calc, refs, song_slot=_SONG_SLOT, prebuilt_frontier=prebuilt)
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0, n_runs=1, n_genomes=n_genomes, n_slots=_N_SLOTS,
            seed=20260612, heuristic_prob=0.0, heuristic_k=0, heuristic_copies=0,
        )
        gpu_api.ga_load_initial_populations_batch(
            run_idx_start=0, n_runs=1, n_genomes_per_run=n_genomes, n_slots=_N_SLOTS,
        )
        gpu_api.ga_seed_rng_runs_indexed(n_runs=1, n_genomes_per_run=n_genomes, seed_base=20260612, run_idx_start=0)

        prep_kw = dict(
            is_p_ft=is_p_ft, is_s_ft=is_s_ft, is_p_ff=is_p_ff, is_s_ff=is_s_ff,
            is_p_pp=is_p_pp, is_s_pp=is_s_pp, is_p_cm=is_p_cm, is_s_cm=is_s_cm,
            is_p_fm=is_p_fm, is_s_fm=is_s_fm, is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        )
        eval_kw = dict(total_budget=_TOTAL_BUDGET, gem_scale_fever=_GEM_SCALE_FEVER, song_slot=_SONG_SLOT, **prep_kw)

        def one():
            gpu_api.ga_prepare_population_base_stats(n_genomes, _N_SLOTS, **prep_kw)
            gpu_api.ga_evaluate_prepared_population(n_genomes, _N_SLOTS, **eval_kw)

        for _ in range(int(ns.warmup)):
            one()
        ti.sync()

        times = []
        for _ in range(int(ns.iters)):
            t0 = time.perf_counter()
            one()
            ti.sync()
            times.append((time.perf_counter() - t0) * 1000.0)

    bd = int(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
    print(
        f"block_dim={bd} genomes={n_genomes} "
        f"prep+eval: mean {statistics.mean(times):.3f}ms  p50 {statistics.median(times):.3f}ms  "
        f"min {min(times):.3f}ms  (iters={len(times)})"
    )


if __name__ == "__main__":
    main()
