"""Plateau-prune A/B for the GPU-native GA and Skyline exact eval (investigation harness).

Both engines share the identical inner kernel ``solve_combo_warmstart_preloaded``; the
only difference is the candidate distribution. This harness toggles each engine's plateau
flag and measures bit-exact parity + wall-clock so the per-engine flag asymmetry
(``_GA_PLATEAU_PRUNE_ENABLED=0`` vs ``_SKYLINE_PLATEAU_PRUNE_ENABLED=1``) can be resolved
to one canonical setting.

The GA flag has NO env hook, so the A/B patches the module constant directly. Each
``prune_plateaus`` value is a ``ti.template()`` -> its own JIT variant, so each variant is
warmed up before timing.

Parity proof: full payload / full results-array byte-equality is STRONGER than best_score
parity -- identical results => identical selected candidates (incl. base stats that feed FG)
=> identical downstream best_fg_score.

Inputs/builders copied from tests/test_gpu_ga_batch_width_invariance.py (known-good driver).

Usage (from repo root):
  python tools/bench/bench_ga_plateau_ab.py --engine ga --genomes 64 --runs 4 --gens 40
  python tools/bench/bench_ga_plateau_ab.py --engine skyline --sky-genomes 256
  python tools/bench/bench_ga_plateau_ab.py --smoke
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

import numpy as np

# Make the repo root importable when run as a plain script (sys.path[0] is tools/bench).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import taichi as ti  # noqa: E402

from gear_optimizer.core.color_flags import build_color_flags  # noqa: E402
from gear_optimizer.solver import genetic_pipeline as genetic  # noqa: E402
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context  # noqa: E402
from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt  # noqa: E402
from gear_optimizer.solver.item_registry import ItemRegistry  # noqa: E402
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK  # noqa: E402
from gear_optimizer.solver.taichi_gem.api import ga_operations  # noqa: E402
from gear_optimizer.solver.taichi_gem.api import skyline_operations  # noqa: E402
from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready  # noqa: E402
from gear_optimizer.solver.taichi_gem.api.timeline import (  # noqa: E402
    build_or_load_timeline_frontier_payload,
    precompute_timeline_gpu,
)

_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"
_GA_SEED = 20260612

_CF_KEYS = (
    "is_p_ft", "is_s_ft", "is_p_ff", "is_s_ff", "is_p_pp", "is_s_pp",
    "is_p_cm", "is_s_cm", "is_p_fm", "is_s_fm", "is_p_ov", "is_s_ov",
)


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _build_registry() -> ItemRegistry:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool: dict[str, list[dict]] = {}
    for s_idx, slot in enumerate(slots):
        items = []
        for i in range(4):
            items.append(
                _item(
                    f"{slot}{i}",
                    **{
                        "Perfect Points": 7 + s_idx + i,
                        "Combo Multiplier": 3 + i,
                        "Fever Multiplier": 2 + s_idx,
                        "Fever Time": 4 + i,
                        "Fever Fill Rate": 5 + s_idx,
                        "Beat": 6 + i,
                        "Vibe": 2 + s_idx,
                        "Rush": 3 + i,
                        "Flow": 4 + s_idx,
                        "Chill": 1 + i,
                    },
                )
            )
        gear_pool[slot] = items

    mini_pool = []
    for i in range(12):
        mini_pool.append(
            _item(
                f"M{i}",
                **{
                    "Perfect Points": 2 + (i % 5),
                    "Combo Multiplier": 1 + (i % 3),
                    "Fever Multiplier": 1 + (i % 4),
                    "Fever Time": 1 + (i % 2),
                    "Fever Fill Rate": 2 + (i % 3),
                    "Beat": 1 + (i % 4),
                    "Vibe": 2 + (i % 2),
                    "Rush": 1 + (i % 5),
                    "Flow": 3 + (i % 2),
                    "Chill": 1 + (i % 3),
                },
            )
        )
    return ItemRegistry(gear_pool, mini_pool, slots)


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(*, n_notes: int = 600) -> dict:
    timestamps = np.linspace(0, 120, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "GA plateau A/B song",
            "Difficulty": "Hard",
            "Primary Color": _PRIMARY_COLOR,
            "Secondary Color": _SECONDARY_COLOR,
            "Total Notes": int(n_notes),
            "Long Notes": 10,
            "Last Note Time": float(timestamps[-1]),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": timestamps},
    }


def _build_context(args) -> dict:
    registry = _build_registry()
    gpu_arrays = registry.to_gpu_arrays()
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(gpu_arrays["slot_count"], dtype=np.int32)
    cfg_data = {
        "selected_color": _SELECTED_COLOR,
        "primary_color": _PRIMARY_COLOR,
        "secondary_color": _SECONDARY_COLOR,
        "TotalBudget": 90,
        "GemScaleFever": 3,
        "fg_candidate_limit": 51,
    }
    base_fixed_stats_arr, _sel = genetic.build_base_fixed_stats_array({}, cfg_data)
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)
    gear_name_rank, mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=_PRIMARY_COLOR,
        secondary_color=_SECONDARY_COLOR,
        selected_color=_SELECTED_COLOR,
    )
    color_flags = build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)
    return {
        "registry": registry,
        "item_stats": item_stats,
        "slot_start": slot_start,
        "slot_count": slot_count,
        "cfg_data": cfg_data,
        "base_fixed_stats_arr": base_fixed_stats_arr,
        "gear_name_rank": gear_name_rank,
        "mini_sig_id": mini_sig_id,
        "color_flags": color_flags,
        "cf12": {k: int(color_flags.get(k, 0)) for k in _CF_KEYS},
        "calc_song": _calc_song(n_notes=args.notes),
        "ref_arrays": _ref_arrays(),
    }


# ----------------------------- GA arm -----------------------------
def _ga_run_once(ctx, *, n_genomes, num_runs, n_gens) -> np.ndarray:
    payload = run_gpu_native_ga_runs_payload_prebuilt(
        calc_song=ctx["calc_song"],
        ref_arrays=ctx["ref_arrays"],
        song_slot=0,
        item_stats=ctx["item_stats"],
        slot_start=ctx["slot_start"],
        slot_count=ctx["slot_count"],
        base_fixed_stats_arr=ctx["base_fixed_stats_arr"],
        n_generations=n_gens,
        initial_populations=None,
        num_runs=num_runs,
        n_genomes=n_genomes,
        color_flags=ctx["color_flags"],
        cfg_data=ctx["cfg_data"],
        ga_seed=_GA_SEED,
        fg_gear_name_rank=ctx["gear_name_rank"],
        fg_mini_sig_id=ctx["mini_sig_id"],
    )
    return np.asarray(payload, dtype=np.int32)


def _ga_measure(setting_value, *, ctx, warmups, timed, n_genomes, num_runs, n_gens):
    has_flag = hasattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED")
    orig = getattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", None)
    if has_flag:
        ga_operations._GA_PLATEAU_PRUNE_ENABLED = int(setting_value)
    try:
        last = None
        for _ in range(max(1, warmups)):
            last = _ga_run_once(ctx, n_genomes=n_genomes, num_runs=num_runs, n_gens=n_gens)
        times = []
        for _ in range(max(1, timed)):
            t0 = time.perf_counter()
            last = _ga_run_once(ctx, n_genomes=n_genomes, num_runs=num_runs, n_gens=n_gens)
            times.append((time.perf_counter() - t0) * 1000.0)
        return last, times
    finally:
        if has_flag:
            ga_operations._GA_PLATEAU_PRUNE_ENABLED = orig


def _run_ga_ab(ctx, args) -> None:
    assert int(getattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", 0)) == 0, "expected GA plateau default OFF (or flag removed)"
    p_off, t_off = _ga_measure(0, ctx=ctx, warmups=args.warmups, timed=args.timed,
                               n_genomes=args.genomes, num_runs=args.runs, n_gens=args.gens)
    p_on, t_on = _ga_measure(1, ctx=ctx, warmups=args.warmups, timed=args.timed,
                             n_genomes=args.genomes, num_runs=args.runs, n_gens=args.gens)
    identical = bool(p_off.shape == p_on.shape and np.array_equal(p_off, p_on))
    print("\n=== GA plateau-prune A/B ===")
    print(f"config: genomes={args.genomes} runs={args.runs} gens={args.gens} notes={args.notes} budget=90 timed={args.timed}")
    print(f"plateau OFF: best_score[0,1]={int(p_off[0, 1])} time_ms min={min(t_off):.1f} median={statistics.median(t_off):.1f} all={[round(x, 1) for x in t_off]}")
    print(f"plateau ON : best_score[0,1]={int(p_on[0, 1])} time_ms min={min(t_on):.1f} median={statistics.median(t_on):.1f} all={[round(x, 1) for x in t_on]}")
    print(f"PAYLOAD BYTE-IDENTICAL (=> best_score & best_fg parity): {identical}")
    if min(t_off) > 0:
        print(f"min-time delta (ON vs OFF): {(min(t_off) - min(t_on)) / min(t_off) * 100.0:+.1f}%  (positive = ON faster)")


# --------------------------- Skyline arm ---------------------------
def _sky_measure(setting_value, *, n_genomes, cf12, warmups, timed):
    has_flag = hasattr(skyline_operations, "_SKYLINE_PLATEAU_PRUNE_ENABLED")
    orig = getattr(skyline_operations, "_SKYLINE_PLATEAU_PRUNE_ENABLED", None)
    if has_flag:
        skyline_operations._SKYLINE_PLATEAU_PRUNE_ENABLED = int(setting_value)

    def _eval():
        skyline_operations.skyline_evaluate_population(
            n_genomes, 9, total_budget=90, gem_scale_fever=3,
            materialize_mode="results", **cf12,
        )
        ti.sync()

    try:
        for _ in range(max(1, warmups)):
            _eval()
        times = []
        for _ in range(max(1, timed)):
            t0 = time.perf_counter()
            _eval()
            times.append((time.perf_counter() - t0) * 1000.0)
        results = np.asarray(skyline_operations.skyline_download_results(n_genomes), dtype=np.int32)
        return results, times
    finally:
        if has_flag:
            skyline_operations._SKYLINE_PLATEAU_PRUNE_ENABLED = orig


def _run_skyline_ab(ctx, args) -> None:
    n = int(args.sky_genomes)
    skyline_operations.skyline_upload_item_stats(ctx["item_stats"], ctx["slot_start"], ctx["slot_count"])
    skyline_operations.skyline_upload_base_fixed_stats(ctx["base_fixed_stats_arr"])
    skyline_operations.skyline_upload_fg_effective_tables(ctx["gear_name_rank"], ctx["mini_sig_id"])
    skyline_operations.skyline_generate_initial_populations(
        run_idx_start=0, n_runs=1, n_genomes=n, n_slots=9, seed=_GA_SEED,
    )
    skyline_operations.skyline_load_initial_population(run_idx=0, n_genomes=n, n_slots=9)

    assert int(getattr(skyline_operations, "_SKYLINE_PLATEAU_PRUNE_ENABLED", 1)) == 1, "expected Skyline plateau default ON (or flag removed)"
    r_off, t_off = _sky_measure(0, n_genomes=n, cf12=ctx["cf12"], warmups=args.warmups, timed=args.timed)
    r_on, t_on = _sky_measure(1, n_genomes=n, cf12=ctx["cf12"], warmups=args.warmups, timed=args.timed)
    identical = bool(r_off.shape == r_on.shape and np.array_equal(r_off, r_on))
    best_off = int(r_off[:, 0].max()) if r_off.size else -1
    best_on = int(r_on[:, 0].max()) if r_on.size else -1
    print("\n=== Skyline plateau-prune A/B ===")
    print(f"config: sky_genomes={n} notes={args.notes} budget=90 timed={args.timed}")
    print(f"plateau OFF: best_score={best_off} time_ms min={min(t_off):.1f} median={statistics.median(t_off):.1f} all={[round(x, 1) for x in t_off]}")
    print(f"plateau ON : best_score={best_on} time_ms min={min(t_on):.1f} median={statistics.median(t_on):.1f} all={[round(x, 1) for x in t_on]}")
    print(f"RESULTS BYTE-IDENTICAL (=> score & gem-split parity): {identical}")
    if min(t_on) > 0:
        print(f"min-time delta (ON vs OFF): {(min(t_off) - min(t_on)) / min(t_off) * 100.0:+.1f}%  (positive = ON faster)")
    if not identical and r_off.shape == r_on.shape:
        diff_rows = sorted({int(r) for r, _ in np.argwhere(r_off != r_on)})
        print(f"DIVERGENCE rows (first 12): {diff_rows[:12]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["ga", "skyline", "both"], default="both")
    ap.add_argument("--genomes", type=int, default=64)
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--gens", type=int, default=40)
    ap.add_argument("--sky-genomes", type=int, default=256)
    ap.add_argument("--timed", type=int, default=7)
    ap.add_argument("--warmups", type=int, default=2)
    ap.add_argument("--notes", type=int, default=600)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--diag", action="store_true", help="print timeline frontier_count distribution (plateau-fire opportunity) and exit")
    args = ap.parse_args()
    if args.smoke:
        (args.genomes, args.runs, args.gens, args.sky_genomes,
         args.timed, args.warmups, args.notes) = 16, 2, 2, 32, 1, 1, 200

    ctx = _build_context(args)
    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(ctx["calc_song"], ctx["ref_arrays"])
        precompute_timeline_gpu(ctx["calc_song"], ctx["ref_arrays"], song_slot=0, prebuilt_frontier=prebuilt)
        if args.diag:
            fc = np.asarray(prebuilt.payload.grid_frontier_count)[0]
            reachable = int((fc > 0).sum())
            eq1 = int((fc == 1).sum())
            gt1 = int((fc > 1).sum())
            print("\n=== timeline frontier_count (slot 0) ===")
            print(f"cells: total={fc.size} reachable(>0)={reachable} single-surface(==1)={eq1} multi-surface(>1)={gt1} max={int(fc.max())}")
            print(f"plateau-fire eligibility: {eq1}/{reachable} reachable cells are single-surface (==1) -> plateau can fire there")
            return
        if args.engine in ("ga", "both"):
            _run_ga_ab(ctx, args)
        if args.engine in ("skyline", "both"):
            _run_skyline_ab(ctx, args)


if __name__ == "__main__":
    main()
