"""M2 — where does GA fall short of EXACT? (the value measurement)

Decides the deployment: is "exact only on the songs where GA fails" worth wiring? Per song,
compares GA's best base score against the exact optimum (the max over the combined-skyline
frontier). Full exact eval is ~15 min/song, so the exact side scores the TOP-K frontier
candidates by raw stat (these contain / bracket the true max and run in seconds) -> a strong
LOWER BOUND on the exact optimum. If GA < this, GA is PROVABLY suboptimal by >= the gap.

Both sides run on the same real pools + timeline. GA strength is a parameter (report it; a
stronger GA shrinks the gap). Base score is the clean signal: it has the combo-mul breakpoints
GA is said to miss, and FG >= base follows it.

Usage:
  python tools/bench/measure_m2_ga_vs_exact.py --difficulty Easy --songs 8
  python tools/bench/measure_m2_ga_vs_exact.py --song "Starry Night" --ga-genomes 128
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

_ALL_GEARS: list = []
_ALL_MINIS: list = []
_RNG = np.random.default_rng(20260614)


def _log(m):
    print(m, flush=True)


def _ref_arrays():
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    return build_ref_arrays_from_stats(read_table(os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")), dtype=np.float64)


def _pick_songs(difficulty, song, want):
    folder = os.path.join(REPO_ROOT, "Data", difficulty)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".txt"))
    if song:
        return [os.path.join(folder, f) for f in files if song.lower() in f.lower()][:max(1, want)]
    return [os.path.join(folder, f) for f in files[:max(1, want)]]


def _ga_best_base(ctx, calc_song, ref_arrays, *, gens, runs, genomes, seed, p_color, s_color):
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
    from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt
    cf = build_color_flags(p_color, s_color, ctx.selected_color)
    gnr, msi = effective_tables_for_context(ctx.registry, primary_color=p_color, secondary_color=s_color, selected_color=ctx.selected_color)
    payload = run_gpu_native_ga_runs_payload_prebuilt(
        calc_song=calc_song, ref_arrays=ref_arrays, song_slot=0,
        item_stats=np.asarray(ctx.gpu_arrays["item_stats"], dtype=np.int32),
        slot_start=np.asarray(ctx.gpu_arrays["slot_start"], dtype=np.int32),
        slot_count=np.asarray(ctx.gpu_arrays["slot_count"], dtype=np.int32),
        base_fixed_stats_arr=np.asarray(ctx.base_fixed_stats_arr, dtype=np.int32),
        n_generations=int(gens), initial_populations=None, num_runs=int(runs), n_genomes=int(genomes),
        color_flags=cf, cfg_data=ctx.cfg_data, ga_seed=int(seed),
        fg_gear_name_rank=gnr, fg_mini_sig_id=msi)
    p = np.asarray(payload, dtype=np.int64)
    # payload col 1 = best base score per run row (bench_ga_plateau_ab); take the max over runs.
    return int(p[:, 1].max()) if p.ndim == 2 and p.shape[1] > 1 else int(p.max())


def _exact_sample_base(ctx, *, sample, total_budget, gem_scale, p_color, s_color):
    """Exact base lower bound: max base over an UNBIASED RANDOM frontier sample (raw-stat ranking
    does NOT predict the gem-optimized score, so top-by-raw under-samples; random is a true LB)."""
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
    from gear_optimizer.solver.solver_common import gear_ids_from_codes, mini_ids_from_codes
    from tests.parity.gear_skyline_gpu import global_gear_skyline_points_6d_gpu_from_arrays
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import skyline_operations
    from tests.parity.exact_skyline import (
        _dp_gear_ff_base_frontier_with_codes, _combined_global_skyline_pairs_6d_lane_base_with_indices,
    )
    dp_points, dp_codes, _ = _dp_gear_ff_base_frontier_with_codes(ctx.gear_pool, p_color=p_color, s_color=s_color, pack=ctx.gear_pack)
    _pin, gear_points, gear_codes, _s = global_gear_skyline_points_6d_gpu_from_arrays(dp_points, dp_codes)
    pair_g, pair_m = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, ctx.mini_points)
    n = int(pair_g.shape[0])
    S = int(min(sample, n))
    idx = _RNG.choice(n, size=S, replace=False)
    g_codes = np.asarray(gear_codes, dtype=np.uint64)[pair_g[idx].astype(np.intp)]
    m_codes = np.asarray(ctx.mini_codes, dtype=np.uint64)[pair_m[idx].astype(np.intp)]
    g_ids = gear_ids_from_codes(g_codes, pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)   # (S,6) vectorized
    m_ids = mini_ids_from_codes(m_codes, pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)    # (S,3)
    pop_all = np.ascontiguousarray(np.concatenate([g_ids, m_ids], axis=1).astype(np.int32))      # (S,9)

    cf = build_color_flags(p_color, s_color, ctx.selected_color)
    cf12 = {k: int(cf.get(k, 0)) for k in ("is_p_ft","is_s_ft","is_p_ff","is_s_ff","is_p_pp","is_s_pp","is_p_cm","is_s_cm","is_p_fm","is_s_fm","is_p_ov","is_s_ov")}
    gnr, msi = effective_tables_for_context(ctx.registry, primary_color=p_color, secondary_color=s_color, selected_color=ctx.selected_color)
    skyline_operations.skyline_upload_item_stats(np.asarray(ctx.gpu_arrays["item_stats"], dtype=np.int32),
                                                 np.asarray(ctx.gpu_arrays["slot_start"], dtype=np.int32),
                                                 np.asarray(ctx.gpu_arrays["slot_count"], dtype=np.int32))
    skyline_operations.skyline_upload_base_fixed_stats(np.asarray(ctx.base_fixed_stats_arr, dtype=np.int32))
    skyline_operations.skyline_upload_fg_effective_tables(gnr, msi)
    chunk = int(min(4096, int(getattr(fields, "MAX_GENOMES", 4096))))
    best = 0
    for off in range(0, S, chunk):
        sub = pop_all[off:off + chunk]
        skyline_operations.skyline_upload_population_indices(sub, n_slots=9)
        skyline_operations.skyline_evaluate_population(int(sub.shape[0]), 9, total_budget=int(total_budget),
                                                       gem_scale_fever=int(gem_scale), materialize_mode="results", **cf12)
        res = np.asarray(skyline_operations.skyline_download_results(int(sub.shape[0])), dtype=np.int64)
        if res.size:
            best = max(best, int(res[:, 0].max()))
    return n, S, best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--song", default="")
    ap.add_argument("--songs", type=int, default=1)
    ap.add_argument("--ga-gens", type=int, default=125)
    ap.add_argument("--ga-runs", type=int, default=3)
    ap.add_argument("--ga-genomes", type=int, default=64)
    ap.add_argument("--ga-seed", type=int, default=1337)
    ap.add_argument("--exact-sample", type=int, default=40000, help="random frontier candidates scored for the exact lower bound")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import MAX_STAT_INDEX, TOTAL_GEM_BUDGET, GEM_SCALE_FEVER
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.solver_common import prepare_solver_context
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload, precompute_timeline_gpu

    global _ALL_GEARS, _ALL_MINIS
    cfg = load_config()
    ref_arrays = _ref_arrays()
    _ALL_GEARS = list(get_gears_by_name_cached().values())
    _ALL_MINIS = list(get_minis_by_name_cached().values())
    songs = _pick_songs(args.difficulty, args.song, args.songs)
    print(f"[m2] songs={len(songs)} GA(gens={args.ga_gens},runs={args.ga_runs},genomes={args.ga_genomes}) exact_sample={args.exact_sample}", flush=True)
    ensure_ready()

    rows = []
    for fp in songs:
        calc_song = get_base_calc_song(fp, {})
        apply_timing_envelope(calc_song)
        meta = (calc_song or {}).get("metadata", {}) or {}
        p_color = str(meta.get("Primary Color") or ""); s_color = str(meta.get("Secondary Color") or "")
        name = str(meta.get("Song Name") or os.path.basename(fp))
        print(f"\n=== {name[:48]} ({p_color}/{s_color}, notes={meta.get('Total Notes')}) ===", flush=True)
        try:
            prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)
            ctx = prepare_solver_context(cfg, {}, calc_song, ref_arrays, list(_ALL_GEARS), list(_ALL_MINIS), status_cb=None, song_slot=0, gpu_client=None)
            t0 = time.perf_counter()
            ga = _ga_best_base(ctx, calc_song, ref_arrays, gens=args.ga_gens, runs=args.ga_runs, genomes=args.ga_genomes, seed=args.ga_seed, p_color=p_color, s_color=s_color)
            t_ga = time.perf_counter() - t0
            t1 = time.perf_counter()
            n_front, n_samp, ex = _exact_sample_base(ctx, sample=args.exact_sample, total_budget=int(TOTAL_GEM_BUDGET), gem_scale=int(GEM_SCALE_FEVER), p_color=p_color, s_color=s_color)
            t_ex = time.perf_counter() - t1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}", flush=True)
            continue
        gap = ex - ga
        gap_pct = (gap / ex * 100.0) if ex else 0.0
        rows.append({"name": name, "two_color": bool(p_color and s_color and p_color != s_color), "ga": ga, "exact_lb": ex, "gap": gap, "gap_pct": gap_pct, "n_front": n_front})
        verdict = "GA OPTIMAL (>= exact LB)" if gap <= 0 else f"GA SUBOPTIMAL by >= {gap:,} ({gap_pct:.3f}%)"
        print(f"  GA best base   = {ga:,}   (GA {t_ga:.1f}s)", flush=True)
        print(f"  exact LB (random {n_samp:,} of {n_front:,}) = {ex:,}   (exact {t_ex:.1f}s)", flush=True)
        print(f"  >>> {verdict}", flush=True)

    if rows:
        gaps = np.array([r["gap_pct"] for r in rows], dtype=np.float64)
        n_sub = int((gaps > 1e-9).sum())
        print("\n=== M2 SUMMARY ===", flush=True)
        print(f"  songs={len(rows)}  GA provably suboptimal on {n_sub}/{len(rows)}", flush=True)
        print(f"  gap%% (exact_LB vs GA): median={np.median(gaps):.3f}  p90={np.quantile(gaps,0.9):.3f}  max={gaps.max():.3f}", flush=True)
        worst = sorted(rows, key=lambda r: r["gap_pct"], reverse=True)[:8]
        print("  worst (GA furthest below exact):", flush=True)
        for r in worst:
            print(f"    gap={r['gap_pct']:7.3f}%  GA={r['ga']:,} exact_LB={r['exact_lb']:,}  {r['name'][:40]}", flush=True)
        print("\n  READ: gap>0 => GA provably misses the optimum (exact-where-it-matters has value there).", flush=True)
        print("        gap~0 across the board => GA is already near-optimal; exact buys little.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
