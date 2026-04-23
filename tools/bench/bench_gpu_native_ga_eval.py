"""
Benchmark GPU-native GA evaluation (exact no-hints path).

Focus: measure wall time of `ga_evaluate_population()` which is dominated by
FT/FF combo evaluation and any associated reductions/atomics.

Usage (example):
  python tools/bench/bench_gpu_native_ga_eval.py --genomes 512 --budget 90 --iters 10
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.bench._bench_reporting import (
    add_kernel_profiler_metrics,
    add_kernel_profiler_kernel_entries,
    clear_taichi_kernel_profiler,
    emit_bench_result,
    env_flag,
    snapshot_env,
)

from gear_optimizer.core.constants import GEM_SCALE_FEVER
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK

GA_KERNEL_PROFILER_NAMES = (
    "ga_build_exact_eval_reuse_map_kernel",
    "ga_aggregate_and_init_best_kernel",
    "ga_propagate_exact_eval_reuse_base_stats_kernel",
    "ga_build_exact_eval_reuse_map_from_base_stats_kernel",
    "ga_find_best_combo_warmstart_kernel",
    "ga_propagate_exact_eval_reuse_chunk_best_kernel",
    "ga_write_best_results_from_key_kernel",
    "ga_update_global_best_kernel",
    "ga_write_best_and_update_global_kernel",
)


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _make_calc_song(*, name: str, p_color: str, s_color: str, n: int = 1200) -> dict:
    ts = np.linspace(0.0, 160.0, n, dtype=np.float32)
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


def _build_registry(
    *,
    rng: np.random.Generator,
    item_ft_max: int,
    item_ff_max: int,
) -> tuple[ItemRegistry, dict, list[dict], dict, list[str]]:
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
                        # Keep FT/FF stats comfortably below 160 so FT/FF combo iteration
                        # doesn't trivially prune almost everything via headroom checks.
                        "Fever Time": int(rng.integers(0, max(0, int(item_ft_max)) + 1)),
                        "Fever Fill Rate": int(rng.integers(0, max(0, int(item_ff_max)) + 1)),
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
    return registry, gear_pool, mini_pool, gpu_arrays, slots


def _make_ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }


def _make_base_fixed_stats(*, rng: np.random.Generator, base_ft: int, base_ff: int) -> np.ndarray:
    base = {
        "Perfect Points": int(rng.integers(100, 300)),
        "Combo Multiplier": int(rng.integers(100, 300)),
        "Fever Multiplier": int(rng.integers(100, 300)),
        # Keep FT/FF comfortably below 160 so most FT/FF gem combos are viable.
        "Fever Time": int(rng.integers(0, 40)),
        "Fever Fill Rate": int(rng.integers(0, 40)),
        "Beat": int(rng.integers(200, 400)),
        "Vibe": int(rng.integers(200, 400)),
        "Rush": int(rng.integers(200, 400)),
        "Flow": int(rng.integers(200, 400)),
        "Chill": int(rng.integers(200, 400)),
    }
    if int(base_ft) >= 0:
        base["Fever Time"] = int(base_ft)
    if int(base_ff) >= 0:
        base["Fever Fill Rate"] = int(base_ff)
    return np.array(
        [
            base["Perfect Points"],
            base["Combo Multiplier"],
            base["Fever Multiplier"],
            base["Fever Time"],
            base["Fever Fill Rate"],
            base["Beat"],
            base["Vibe"],
            base["Rush"],
            base["Flow"],
            base["Chill"],
        ],
        dtype=np.int32,
    )


def _make_population(
    *,
    rng: np.random.Generator,
    n_genomes: int,
    slots: list[str],
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
    registry: ItemRegistry,
) -> np.ndarray:
    genomes: list[list[dict]] = []
    for _g in range(int(n_genomes)):
        gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
        minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
        genomes.append(gear + minis)
    return registry.encode_population(genomes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--genomes", type=int, default=int(os.environ.get("BENCH_GA_GENOMES", "512")))
    ap.add_argument("--budget", type=int, default=int(os.environ.get("BENCH_GA_BUDGET", "90")))
    ap.add_argument("--iters", type=int, default=int(os.environ.get("BENCH_GA_ITERS", "10")))
    ap.add_argument("--warmup", type=int, default=int(os.environ.get("BENCH_GA_WARMUP", "2")))
    ap.add_argument("--seed", type=int, default=int(os.environ.get("BENCH_GA_SEED", "1337")))
    ap.add_argument("--prune-plateaus", type=int, default=int(os.environ.get("BENCH_GA_PRUNE", "1")))
    ap.add_argument(
        "--materialize-mode",
        choices=("none", "results", "update_global"),
        default=str(os.environ.get("BENCH_GA_MATERIALIZE_MODE", "none") or "none").strip().lower(),
        help="Mirror the live GA subpath more closely by choosing how results are materialized.",
    )
    ap.add_argument(
        "--kernel-profiler",
        action="store_true",
        help="Enable Taichi kernel-profiler totals for the measured steady-state window.",
    )
    ap.add_argument(
        "--base-ft",
        type=int,
        default=int(os.environ.get("BENCH_GA_BASE_FT", "-1")),
        help="Override base fixed Fever Time stat (default: random). Set ~160 to force FT headroom scarcity.",
    )
    ap.add_argument(
        "--base-ff",
        type=int,
        default=int(os.environ.get("BENCH_GA_BASE_FF", "-1")),
        help="Override base fixed Fever Fill Rate stat (default: random). Set ~160 to force FF headroom scarcity.",
    )
    ap.add_argument(
        "--item-ft-max",
        type=int,
        default=int(os.environ.get("BENCH_GA_ITEM_FT_MAX", "40")),
        help="Max Fever Time stat on generated items (default: 40).",
    )
    ap.add_argument(
        "--item-ff-max",
        type=int,
        default=int(os.environ.get("BENCH_GA_ITEM_FF_MAX", "40")),
        help="Max Fever Fill Rate stat on generated items (default: 40).",
    )
    ap.add_argument("--json", action="store_true", help="Emit final metrics as machine-readable JSON on stdout.")
    ap.add_argument("--json-out", type=str, default="", help="Write final metrics JSON to this path.")
    args = ap.parse_args()

    # `ga_operations` caches GPU_NATIVE_GA_PLATEAU_PRUNE at module import time to avoid per-call overhead.
    # Set it BEFORE importing ga_operations so the benchmark matches the printed configuration.
    os.environ["GPU_NATIVE_GA_PLATEAU_PRUNE"] = "1" if int(args.prune_plateaus) else "0"
    if bool(args.kernel_profiler):
        os.environ["TAICHI_KERNEL_PROFILER"] = "1"

    from gear_optimizer.solver.taichi_gem.api import ga_operations as _ga_ops
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        ga_evaluate_population,
        ga_upload_base_fixed_stats,
        ga_upload_item_stats,
        ga_upload_population_indices,
    )
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

    prune_effective = int(getattr(_ga_ops, "_GA_PLATEAU_PRUNE_ENABLED", 0))
    materialize_mode = str(args.materialize_mode or "none").strip().lower()
    kernel_profiler_requested = bool(args.kernel_profiler) or env_flag("TAICHI_KERNEL_PROFILER", "0")

    rng = np.random.default_rng(int(args.seed))
    registry, gear_pool, mini_pool, gpu_arrays, slots = _build_registry(
        rng=rng,
        item_ft_max=int(args.item_ft_max),
        item_ff_max=int(args.item_ff_max),
    )
    ref_arrays = _make_ref_arrays()
    base_fixed_stats_arr = _make_base_fixed_stats(rng=rng, base_ft=int(args.base_ft), base_ff=int(args.base_ff))

    calc_song = _make_calc_song(name="BenchGAEval_BeatVibe", p_color="Beat", s_color="Vibe")
    flags = _color_flags(p_color="Beat", s_color="Vibe", selected_color="Beat")

    with _GPU_LOCK:
        ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
        ga_upload_base_fixed_stats(base_fixed_stats_arr)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

        pop_indices = _make_population(
            rng=rng,
            n_genomes=int(args.genomes),
            slots=slots,
            gear_pool=gear_pool,
            mini_pool=mini_pool,
            registry=registry,
        )
        ga_upload_population_indices(pop_indices, n_slots=9)

        # Warmup (compilation + cache)
        for _ in range(int(args.warmup)):
            ga_evaluate_population(
                n_genomes=int(args.genomes),
                n_slots=9,
                total_budget=int(args.budget),
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
                materialize_mode=materialize_mode,
            )
            try:
                import taichi as ti

                ti.sync()
            except Exception:
                pass

        clear_taichi_kernel_profiler(enabled=kernel_profiler_requested)
        start = time.perf_counter()
        for _ in range(int(args.iters)):
            ga_evaluate_population(
                n_genomes=int(args.genomes),
                n_slots=9,
                total_budget=int(args.budget),
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
                materialize_mode=materialize_mode,
            )
        try:
            import taichi as ti

            ti.sync()
        except Exception:
            pass
        elapsed = time.perf_counter() - start

    iters = max(1, int(args.iters))
    per_iter = elapsed / iters
    print(
        f"ga_evaluate_population: genomes={int(args.genomes)} budget={int(args.budget)} "
        f"iters={iters} warmup={int(args.warmup)} mode=exact_no_hints "
        f"materialize_mode={materialize_mode} "
        f"prune_arg={int(args.prune_plateaus)} prune_effective={prune_effective} "
        f"base_ft={int(args.base_ft)} base_ff={int(args.base_ff)} "
        f"item_ft_max={int(args.item_ft_max)} item_ff_max={int(args.item_ff_max)}"
    )
    print(f"total_sec={elapsed:.6f} per_iter_sec={per_iter:.6f} iters_per_sec={iters / elapsed:.3f}")
    result = {
        "bench": "ga_eval",
        "genomes": int(args.genomes),
        "budget": int(args.budget),
        "iters": int(iters),
        "warmup": int(args.warmup),
        "seed": int(args.seed),
        "prune_arg": int(args.prune_plateaus),
        "prune_effective": int(prune_effective),
        "materialize_mode": materialize_mode,
        "kernel_profiler_requested": bool(kernel_profiler_requested),
        "base_ft": int(args.base_ft),
        "base_ff": int(args.base_ff),
        "item_ft_max": int(args.item_ft_max),
        "item_ff_max": int(args.item_ff_max),
        "total_sec": float(elapsed),
        "per_iter_sec": float(per_iter),
        "iters_per_sec": float(iters / elapsed),
        "env": snapshot_env(
            [
                "TAICHI_BLOCK_DIM",
                "GA_FTFF_REDUCE_BLOCK_DIM",
                "GPU_NATIVE_GA_BATCH_RUNS",
                "GPU_NATIVE_GA_PLATEAU_PRUNE",
                "TAICHI_KERNEL_PROFILER",
            ]
        ),
    }
    add_kernel_profiler_metrics(result, enabled=kernel_profiler_requested, wall_sec=float(elapsed))
    add_kernel_profiler_kernel_entries(
        result,
        enabled=kernel_profiler_requested,
        kernel_names=GA_KERNEL_PROFILER_NAMES,
    )
    if result.get("kernel_profiler_total_sec") is not None:
        print(
            "kernel_profiler_total_sec="
            f"{float(result['kernel_profiler_total_sec']):.6f} "
            "kernel_profiler_wall_pct="
            f"{float(result['kernel_profiler_wall_pct']):.2f}"
        )
        top_kernel = ((result.get("kernel_profiler_kernels", None) or [])[:1] or [None])[0]
        if isinstance(top_kernel, dict):
            print(
                "kernel_top="
                f"{str(top_kernel.get('name', ''))} "
                "kernel_top_total_sec="
                f"{float(top_kernel.get('total_sec', 0.0)):.6f} "
                "kernel_top_avg_ms="
                f"{float(top_kernel.get('avg_ms', 0.0)):.6f}"
            )
    emit_bench_result(result, json_stdout=bool(args.json), json_out=str(args.json_out or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
