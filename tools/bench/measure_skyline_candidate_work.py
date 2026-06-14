"""Step 1 feasibility probe: per-song exact-Skyline candidate-work distribution.

GOAL (skyline-speed workstream): decide whether an EXACT outer search can be made
*consistently* (across all songs, not per-song) as cheap as the GA heuristic. GA's
cost is budget-bounded (population x generations x runs); Skyline's cost is
data-determined (the combined timing-cell frontier size x the FT/FF combo table).
This tool measures that data-determined size for every song so we can see the
DISTRIBUTION and especially the TAIL (the worst songs decide "consistent parity").

What it computes per song, reusing the canonical candidate-generation funnel
(NO GPU eval / NO ForceGreats -- only the dominance pipeline, so it sweeps fast):
  gear DP frontier  ->  gear timing-cell skyline  ->  combined gear(+)mini skyline
The combined skyline `out_pairs` IS the exact candidate set (the per-cell
(PP,CM,FM,base) antichain summed over fixed (FT,FF) cells). Everything downstream
(today's eval, Direction-1 FG-DP) scales with it.

Cost model (unit = one inner exact solve `solve_combo_warmstart_preloaded`, shared
by GA and Skyline):
  K            = FT/FF combos per genome (full table; budget-triangular upper bound)
  ga_eff       = ga_genomes * ga_gens * ga_runs * (1 - ga_dedup)
  ga_solves    ~= ga_eff * K
  current_sky  ~= n_candidates * K            (today: each frontier point x full combo table)
  direction1   ~= n_candidates                (FG-DP owns FT/FF -> combos collapse)
  r1 = n_candidates / ga_eff                  (<1  => current eval already <= GA inner-solves)
  r2 = n_candidates / (ga_eff * K)            (Direction-1 floor vs GA; expected <<1)

r1 is the headline: how far today's exact eval is from GA in inner-solve count.
If r1 < 1 for (almost) all songs, the eval is already GA-cheap and slowness lives
elsewhere (FG scoring / CPU dominance pipeline -- also timed here). If r1 has a
fat tail, Direction-1 / combo-antichain is what flattens it.

Usage (from repo root):
  python tools/bench/measure_skyline_candidate_work.py --difficulty Easy
  python tools/bench/measure_skyline_candidate_work.py --difficulty all --limit 0
  python tools/bench/measure_skyline_candidate_work.py --difficulty Hard --sample 40 --no-gear-skyline
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import traceback

import numpy as np

# Make repo root importable when run as a plain script (sys.path[0] is tools/bench).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


_STAT_FIELDS = [
    "difficulty", "song_name", "total_notes", "p_color", "s_color",
    "gear_pool_after", "mini_pool", "gear_dp_pairs", "gear_sky_out",
    "mini_points", "n_candidates", "active_cells", "per_cell_antichain",
    "n_combos_full", "ga_eff", "r1_current_vs_ga", "r2_direction1_vs_ga",
    "gear_dp_sec", "gear_sky_sec", "combined_sec", "total_sec", "error",
]


def _measure_song(song_fp, cfg_dict, all_gears, all_minis, *, budget, ga_eff, with_gear_skyline):
    """Run the dominance funnel for one song; return a dict row (never raises for
    per-song data issues -- records them in 'error' and continues the sweep)."""
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
    from gear_optimizer.solver.solver_common import GEAR_SLOTS, make_pack
    from gear_optimizer.solver.mini_skyline import mini_combo_skyline
    from gear_optimizer.solver.combined_skyline_sparse import (
        combined_global_skyline_pairs_6d_sparse,
        get_last_combined_skyline_stats,
    )
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
    from tests.parity.exact_skyline import _dp_gear_ff_base_frontier_with_codes

    row = {k: "" for k in _STAT_FIELDS}
    t_total = time.perf_counter()
    try:
        calc_song = get_base_calc_song(song_fp, cfg_dict)
        meta = (calc_song or {}).get("metadata", {}) or {}
        p_color = str(meta.get("Primary Color") or "").strip()
        s_color = str(meta.get("Secondary Color") or "").strip()
        row["difficulty"] = str(meta.get("Difficulty") or "").strip()
        row["song_name"] = str(meta.get("Song Name") or os.path.basename(song_fp)).strip()
        row["total_notes"] = int(meta.get("Total Notes") or 0)
        row["p_color"] = p_color
        row["s_color"] = s_color
        if not p_color:
            row["error"] = "no_primary_color"
            return row

        pools = initialize_pools(all_gears, all_minis, p_color, list(GEAR_SLOTS), s_color=s_color)
        if not pools or pools[0] is None or not pools[1]:
            row["error"] = "empty_pools"
            return row
        gear_pool, mini_pool = pools[0], pools[1]
        row["gear_pool_after"] = int(sum(len(gear_pool.get(s, []) or []) for s in GEAR_SLOTS))
        row["mini_pool"] = int(len(mini_pool))

        gear_pack = make_pack([len(gear_pool.get(s, []) or []) for s in GEAR_SLOTS])
        mini_pack = make_pack([len(mini_pool), len(mini_pool), len(mini_pool)])

        _ms, mini_points, _mc = mini_combo_skyline(mini_pool, p_color=p_color, s_color=s_color, pack=mini_pack)
        row["mini_points"] = int(mini_points.shape[0]) if mini_points is not None else 0

        dp_points, dp_codes, dp_stats = _dp_gear_ff_base_frontier_with_codes(
            gear_pool, p_color=p_color, s_color=s_color, pack=gear_pack
        )
        row["gear_dp_pairs"] = int(dp_stats.pairs_6d)
        row["gear_dp_sec"] = round(float(dp_stats.seconds), 4)

        if dp_points.size == 0 or mini_points is None or mini_points.size == 0:
            row["n_candidates"] = 0
            row["error"] = "empty_gear_or_mini_frontier"
            return row

        if with_gear_skyline:
            from gear_optimizer.solver.gear_skyline_gpu import global_gear_skyline_points_6d_gpu_from_arrays

            _pin, gear_points, _gc, gear_sky_sec = global_gear_skyline_points_6d_gpu_from_arrays(dp_points, dp_codes)
            row["gear_sky_sec"] = round(float(gear_sky_sec), 4)
        else:
            gear_points = dp_points
            row["gear_sky_sec"] = 0.0
        row["gear_sky_out"] = int(gear_points.shape[0])

        t_comb = time.perf_counter()
        pair_g, _pair_m = combined_global_skyline_pairs_6d_sparse(gear_points, mini_points)
        row["combined_sec"] = round(time.perf_counter() - t_comb, 4)
        cstats = get_last_combined_skyline_stats()
        counts = cstats.get("counts", {}) if isinstance(cstats, dict) else {}

        n_candidates = int(pair_g.shape[0])
        active_cells = int(counts.get("active_timing_cells", 0) or 0)
        n_combos_full = int(ftff_combo_arrays(int(budget))[0].shape[0])

        row["n_candidates"] = n_candidates
        row["active_cells"] = active_cells
        row["per_cell_antichain"] = round(n_candidates / active_cells, 2) if active_cells else 0.0
        row["n_combos_full"] = n_combos_full
        row["ga_eff"] = int(ga_eff)
        row["r1_current_vs_ga"] = round(n_candidates / ga_eff, 4) if ga_eff else 0.0
        row["r2_direction1_vs_ga"] = (
            round(n_candidates / (ga_eff * n_combos_full), 6) if (ga_eff and n_combos_full) else 0.0
        )
    except Exception as e:  # noqa: BLE001 -- per-song boundary: record + keep sweeping
        row["error"] = f"{type(e).__name__}: {e}"
        row["_traceback"] = traceback.format_exc()
    finally:
        row["total_sec"] = round(time.perf_counter() - t_total, 4)
    return row


def _enumerate_songs(difficulty: str, limit: int, sample: int) -> list[str]:
    diffs = ["Easy", "Normal", "Hard"] if difficulty.lower() == "all" else [difficulty]
    fps: list[str] = []
    for d in diffs:
        folder = os.path.join(REPO_ROOT, "Data", d)
        if not os.path.isdir(folder):
            print(f"[warn] missing difficulty folder: {folder}")
            continue
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith(".txt"):
                fps.append(os.path.join(folder, fn))
    if sample and sample > 0 and sample < len(fps):
        rng = np.random.default_rng(20260613)
        idx = np.sort(rng.choice(len(fps), size=int(sample), replace=False))
        fps = [fps[int(i)] for i in idx]
    if limit and limit > 0:
        fps = fps[:limit]
    return fps


def _pct(arr: np.ndarray, q: float) -> float:
    return float(np.percentile(arr, q)) if arr.size else 0.0


def _summarize(rows: list[dict], ga_genomes, ga_gens, ga_runs, ga_dedup) -> None:
    ok = [r for r in rows if not r.get("error") and isinstance(r.get("n_candidates"), int)]
    by_diff: dict[str, list[dict]] = {}
    for r in ok:
        by_diff.setdefault(r["difficulty"] or "?", []).append(r)

    print("\n" + "=" * 78)
    print("EXACT-SKYLINE CANDIDATE-WORK DISTRIBUTION")
    print(f"GA reference: genomes={ga_genomes} gens={ga_gens} runs={ga_runs} dedup={ga_dedup} "
          f"-> ga_eff={int(ga_genomes * ga_gens * ga_runs * (1 - ga_dedup))} effective genome-evals")
    print("r1 = n_candidates / ga_eff  (current exact eval vs GA inner-solves; <1 = already GA-cheap)")
    print("r2 = n_candidates / (ga_eff * K)  (Direction-1 FG-DP floor vs GA)")
    print("=" * 78)

    for diff, rs in sorted(by_diff.items()):
        cand = np.array([r["n_candidates"] for r in rs], dtype=np.float64)
        r1 = np.array([r["r1_current_vs_ga"] for r in rs], dtype=np.float64)
        anti = np.array([r["per_cell_antichain"] for r in rs], dtype=np.float64)
        pipe = np.array([float(r["gear_dp_sec"] or 0) + float(r["gear_sky_sec"] or 0)
                         + float(r["combined_sec"] or 0) for r in rs], dtype=np.float64)
        print(f"\n--- {diff}  (n={len(rs)} songs) ---")
        print(f"  n_candidates : median={_pct(cand,50):,.0f}  p90={_pct(cand,90):,.0f}  "
              f"p99={_pct(cand,99):,.0f}  max={cand.max():,.0f}")
        print(f"  r1 (vs GA)   : median={_pct(r1,50):.3f}  p90={_pct(r1,90):.3f}  "
              f"p99={_pct(r1,99):.3f}  max={r1.max():.3f}  "
              f"| songs with r1>1: {int((r1>1).sum())}/{len(rs)}")
        print(f"  per-cell antichain: median={_pct(anti,50):.2f}  p90={_pct(anti,90):.2f}  max={anti.max():.2f}")
        print(f"  candidate-gen pipeline sec: median={_pct(pipe,50):.3f}  p99={_pct(pipe,99):.3f}  max={pipe.max():.3f}")
        worst = sorted(rs, key=lambda r: r["n_candidates"], reverse=True)[:8]
        print("  worst (tail) by n_candidates:")
        for r in worst:
            print(f"    {r['n_candidates']:>9,}  r1={r['r1_current_vs_ga']:.2f}  "
                  f"gear={r['gear_pool_after']} mini={r['mini_pool']}  {r['song_name'][:48]}")

    errs = [r for r in rows if r.get("error")]
    if errs:
        from collections import Counter
        ec = Counter(r["error"].split(":")[0] for r in errs)
        print(f"\n[skipped/errored: {len(errs)}] {dict(ec)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--difficulty", default="Easy", help="Easy|Normal|Hard|all (default Easy)")
    ap.add_argument("--limit", type=int, default=0, help="max songs (0=all)")
    ap.add_argument("--sample", type=int, default=0, help="random deterministic sample size (0=off)")
    ap.add_argument("--budget", type=int, default=0, help="gem budget for K (0=TOTAL_GEM_BUDGET)")
    ap.add_argument("--ga-genomes", type=int, default=128, help="GA population per run (estimate)")
    ap.add_argument("--ga-gens", type=int, default=125, help="GA generations (GA_SearchDepth default)")
    ap.add_argument("--ga-runs", type=int, default=3, help="GA multistart runs (GA_MultiStart default)")
    ap.add_argument("--ga-dedup", type=float, default=0.16, help="GA duplicate-genome fraction (measured ~0.16)")
    ap.add_argument("--no-gear-skyline", action="store_true",
                    help="skip the GPU gear global skyline (CPU-only; combined gets larger input)")
    ap.add_argument("--out", default="", help="CSV output path (default artifacts/skyline_candidate_work_<diff>.csv)")
    args = ap.parse_args()

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.core.constants import TOTAL_GEM_BUDGET
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached

    budget = int(args.budget) if int(args.budget) > 0 else int(TOTAL_GEM_BUDGET)
    ga_eff = max(1, int(args.ga_genomes * args.ga_gens * args.ga_runs * (1.0 - args.ga_dedup)))

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)

    all_gears = list(get_gears_by_name_cached().values())
    all_minis = list(get_minis_by_name_cached().values())
    n_typed = sum(1 for g in all_gears if g.get("type"))
    print(f"[load] all_gears={len(all_gears)} (typed={n_typed}) all_minis={len(all_minis)} budget={budget}")
    if n_typed == 0:
        raise SystemExit("FATAL: no gear items carry a 'type' (slot) key -- gear source is wrong; cannot build pools.")

    with_gear_skyline = not args.no_gear_skyline
    if with_gear_skyline:
        from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
        print("[gpu] initializing Taichi/Vulkan for gear global skyline ...")
        ensure_ready()

    songs = _enumerate_songs(args.difficulty, args.limit, args.sample)
    print(f"[sweep] {len(songs)} songs (difficulty={args.difficulty})")

    out_path = args.out or os.path.join(
        REPO_ROOT, "artifacts", f"skyline_candidate_work_{args.difficulty.lower()}.csv"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    rows: list[dict] = []
    t0 = time.perf_counter()
    for i, fp in enumerate(songs):
        row = _measure_song(
            fp, cfg_dict, all_gears, all_minis,
            budget=budget, ga_eff=ga_eff, with_gear_skyline=with_gear_skyline,
        )
        rows.append(row)
        if (i + 1) % 10 == 0 or (i + 1) == len(songs):
            done = i + 1
            rate = done / max(0.001, time.perf_counter() - t0)
            nc = row.get("n_candidates", "")
            print(f"  [{done}/{len(songs)}] {rate:.1f} songs/s  last: n_cand={nc} {row.get('song_name','')[:40]}")

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_STAT_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _STAT_FIELDS})
    print(f"\n[out] wrote {len(rows)} rows -> {out_path}")

    _summarize(rows, args.ga_genomes, args.ga_gens, args.ga_runs, args.ga_dedup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
