"""M1 — the branch-and-bound prune-rate GATE for exact Skyline (frontier separability).

A candidate's true score requires the inner gem-allocation solve, so a cheap closed-form upper
bound on raw frontier stats is NOT admissible (gems push PP/CM/FM up; raw-stat UB undershoots by
~2x). Instead M1 measures the question directly: SAMPLE the frontier's true (base) score
distribution and report, for a hypothetical admissible bound of looseness factor f (UB = f * true),

    prune_rate(f) = fraction of candidates with true_score <= incumbent / f

(a candidate is prunable iff its UB <= incumbent, i.e. true_score <= incumbent/f). This says how
tight a bound Track B would need and whether the frontier is separable at all:
  - prune_rate(f) high at a LOOSE f (e.g. 2-3x): exact-by-construction B&B is ALIVE (an easy cheap
    bound prunes the bulk) -> worth building.
  - need f ~1.0 (near-perfect bound) for high prune: the frontier is a near-equal cluster, no cheap
    bound separates it -> B&B effectively dead, the ~5-10x engineering ceiling stands.

Base score is a tight proxy for FG (FG in [base, ~1.3*base]); single/two-color both sampled.
Reuses the EXISTING skyline funnel (gear DP -> gear skyline -> GPU-dense combined). Score via the
canonical base solver (build_candidate_payload -> solve_best_fever_combination), which does the
real gem allocation.

Usage:
  python tools/bench/measure_m1_fg_prune_gate.py --difficulty Easy --song "Starry Night" --sample 800
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
_RNG = np.random.default_rng(20260613)


def _log(msg: str) -> None:
    print(f"   {msg}", flush=True)


def _ref_arrays() -> dict:
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

    return build_ref_arrays_from_stats(read_table(os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")), dtype=np.float64)


def _pick_songs(difficulty: str, song: str, want: int) -> list[str]:
    folder = os.path.join(REPO_ROOT, "Data", difficulty)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".txt"))
    if song:
        return [os.path.join(folder, f) for f in files if song.lower() in f.lower()][:max(1, want)]
    return [os.path.join(folder, f) for f in files[:max(1, want)]]


def _score_candidates(idxs, *, ctx, calc_song, ref_arrays, gear_codes, pair_g, pair_m, override_cfg):
    from gear_optimizer.solver.solver_common import gear_ids_from_code, mini_ids_from_code, build_candidate_payload
    scores = np.zeros(len(idxs), dtype=np.float64)
    for k, j in enumerate(idxs):
        g_ids = gear_ids_from_code(int(gear_codes[int(pair_g[j])]), pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)
        m_ids = mini_ids_from_code(int(ctx.mini_codes[int(pair_m[j])]), pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)
        ids = np.concatenate((g_ids, m_ids)).astype(np.int32)
        genome = ctx.registry.decode_genome(ids)
        data = build_candidate_payload(cfg=ctx.cfg, base_stats_fixed=ctx.base_stats_fixed, calc_song=calc_song,
                                       ref_arrays=ref_arrays, genome=genome, override_cfg=override_cfg, gpu_client=None)
        scores[k] = float(data.get("BaseScore") or data.get("Score", 0) or 0)
        if k == 0:
            _log("  first payload built (base-solve kernels compiled)")
    return scores


def _measure_one(fp, cfg, ref_arrays, *, sample, topk, max_stat):
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.solver_common import prepare_solver_context, build_solver_override_cfg
    from tests.parity.gear_skyline_gpu import global_gear_skyline_points_6d_gpu_from_arrays
    from tests.parity.exact_skyline import (
        _dp_gear_ff_base_frontier_with_codes,
        _combined_global_skyline_pairs_6d_lane_base_with_indices,  # GPU-dense-first
    )

    calc_song = get_base_calc_song(fp, {})
    meta = (calc_song or {}).get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color") or ""); s_color = str(meta.get("Secondary Color") or "")
    n_notes = int(meta.get("Total Notes") or 0)
    row = {"song": str(meta.get("Song Name") or os.path.basename(fp)), "p_color": p_color, "s_color": s_color,
           "two_color": bool(p_color and s_color and p_color != s_color), "n_notes": n_notes, "error": ""}
    if n_notes <= 0 or not p_color:
        row["error"] = "bad_metadata"; return row

    _log("prepare_solver_context ...")
    ctx = prepare_solver_context(cfg, {}, calc_song, ref_arrays, list(_ALL_GEARS), list(_ALL_MINIS),
                                 status_cb=None, song_slot=0, gpu_client=None)
    if ctx is None:
        row["error"] = "no_ctx"; return row
    _log("gear DP ...")
    dp_points, dp_codes, _dp = _dp_gear_ff_base_frontier_with_codes(ctx.gear_pool, p_color=p_color, s_color=s_color, pack=ctx.gear_pack)
    if dp_points.size == 0 or ctx.mini_points.size == 0:
        row["error"] = "empty_frontier"; return row
    _log(f"gear skyline (GPU) ... dp_pairs={dp_points.shape[0]:,}")
    _pin, gear_points, gear_codes, _sec = global_gear_skyline_points_6d_gpu_from_arrays(dp_points, dp_codes)
    _log(f"combined skyline (GPU-dense) ... gear_sky={gear_points.shape[0]:,} minis={ctx.mini_points.shape[0]:,}")
    pair_g, pair_m = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, ctx.mini_points)
    n = int(pair_g.shape[0]); row["n_candidates"] = n
    _log(f"combined done: n_candidates={n:,}")
    if n == 0:
        row["error"] = "empty_combined"; return row

    # raw base_value (lane + pp) is only a coarse ranker for the incumbent anchor.
    gp = gear_points.astype(np.int64); mp = ctx.mini_points.astype(np.int64)
    gi = pair_g.astype(np.intp); mi = pair_m.astype(np.intp)
    ref_pp = np.asarray(ref_arrays["Perfect Points"], dtype=np.float64)
    raw_bv = (gp[gi, 5] + mp[mi, 4]).astype(np.float64) + ref_pp[np.clip(gp[gi, 0], 0, max_stat).astype(np.intp)]

    override_cfg = build_solver_override_cfg(ctx.cfg_data, p_color=p_color, selected_color=ctx.selected_color)

    # Representative random sample of the frontier (for the distribution) + top-by-raw (for the incumbent anchor).
    S = int(min(sample, n)); K = int(min(topk, n))
    rand_idx = _RNG.choice(n, size=S, replace=False)
    top_idx = np.argpartition(raw_bv, n - K)[n - K:]
    _log(f"scoring {S} random + {K} top-by-raw candidates via the base solver (inner gem allocation) ...")
    t = time.perf_counter()
    rand_scores = _score_candidates(rand_idx.tolist(), ctx=ctx, calc_song=calc_song, ref_arrays=ref_arrays,
                                    gear_codes=gear_codes, pair_g=pair_g, pair_m=pair_m, override_cfg=override_cfg)
    top_scores = _score_candidates(top_idx.tolist(), ctx=ctx, calc_song=calc_song, ref_arrays=ref_arrays,
                                   gear_codes=gear_codes, pair_g=pair_g, pair_m=pair_m, override_cfg=override_cfg)
    _log(f"scored {S+K} candidates in {time.perf_counter()-t:.1f}s")

    incumbent = float(max(rand_scores.max(), top_scores.max()))   # strong incumbent (base; FG >= base)
    mx = float(rand_scores.max())
    row.update({
        "incumbent_base": int(incumbent), "sample": S,
        "score_max_rand": int(rand_scores.max()), "score_p50": int(np.median(rand_scores)),
        "score_p10": int(np.quantile(rand_scores, 0.10)), "score_p90": int(np.quantile(rand_scores, 0.90)),
        "score_min": int(rand_scores.min()),
    })
    # prune_rate(f) over the REPRESENTATIVE random sample: a bound UB = f*true prunes c iff true <= incumbent/f.
    fs = [1.0, 1.05, 1.1, 1.25, 1.5, 2.0, 3.0]
    row["prune_curve"] = [(f, round(float(np.mean(rand_scores <= incumbent / f)), 4)) for f in fs]
    # also: spread of the random sample relative to the incumbent
    row["frac_within_90pct_of_incumbent"] = round(float(np.mean(rand_scores >= 0.90 * incumbent)), 4)
    row["frac_within_99pct_of_incumbent"] = round(float(np.mean(rand_scores >= 0.99 * incumbent)), 4)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--song", default="")
    ap.add_argument("--songs", type=int, default=1)
    ap.add_argument("--sample", type=int, default=800, help="random frontier candidates to score (distribution)")
    ap.add_argument("--topk", type=int, default=64, help="top-by-raw candidates to score (incumbent anchor)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import MAX_STAT_INDEX
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload, precompute_timeline_gpu

    global _ALL_GEARS, _ALL_MINIS
    cfg = load_config()
    ref_arrays = _ref_arrays()
    _ALL_GEARS = list(get_gears_by_name_cached().values())
    _ALL_MINIS = list(get_minis_by_name_cached().values())
    songs = _pick_songs(args.difficulty, args.song, args.songs)
    print(f"[m1] songs={len(songs)} sample={args.sample} topk={args.topk}", flush=True)
    print("[m1] ensure_ready (GPU init) ...", flush=True)
    ensure_ready()
    print("[m1] ensure_ready OK", flush=True)

    results = []
    for fp in songs:
        calc_song = get_base_calc_song(fp, {})
        meta = (calc_song or {}).get("metadata", {}) or {}
        print(f"\n=== {str(meta.get('Song Name') or os.path.basename(fp))[:50]} "
              f"({meta.get('Primary Color')}/{meta.get('Secondary Color')}, notes={meta.get('Total Notes')}) ===", flush=True)
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)
        t0 = time.perf_counter()
        row = _measure_one(fp, cfg, ref_arrays, sample=args.sample, topk=args.topk, max_stat=int(MAX_STAT_INDEX))
        row["sec"] = round(time.perf_counter() - t0, 1)
        results.append(row)
        if row.get("error"):
            print(f"  ERROR: {row['error']}", flush=True); continue
        print(f"  n_candidates={row['n_candidates']:,}  incumbent(base)={row['incumbent_base']:,}  sec={row['sec']}", flush=True)
        print(f"  random-sample score dist: min={row['score_min']:,} p10={row['score_p10']:,} p50={row['score_p50']:,} "
              f"p90={row['score_p90']:,} max={row['score_max_rand']:,}", flush=True)
        print(f"  fraction within 90% of incumbent: {row['frac_within_90pct_of_incumbent']*100:.1f}%   "
              f"within 99%: {row['frac_within_99pct_of_incumbent']*100:.2f}%", flush=True)
        print("  >>> PRUNE_RATE(f) -- with an admissible bound of looseness f, fraction of frontier pruned:", flush=True)
        for f, pr in row["prune_curve"]:
            print(f"        f={f:<4}  prune={pr*100:6.2f}%", flush=True)

    ok = [r for r in results if not r.get("error")]
    if ok:
        print("\n=== M1 READ ===", flush=True)
        print("  B&B ALIVE if prune_rate is high (>=95%) at a LOOSE f (2-3x).", flush=True)
        print("  B&B DEAD if you need f~1.0 (near-perfect bound) for high prune (frontier is a near-equal cluster).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
