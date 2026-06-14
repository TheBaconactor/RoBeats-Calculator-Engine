"""Deterministic proof + magnitude census for the Skyline (P,S)->2P+S FG-fold gap.

The skyline candidate generation represents a loadout's elemental stats by the single
scalar base_lane = 2P+S and keeps one survivor per (PP,CM,FM,base_lane) per (FT,FF) cell.
The base score IS a function of 2P+S, but the two-color FG Great-penalty base is
  compute_great_penalty_base(P,S) = floor(4P/3) + floor(2S/3) + 150
and 4P/3 + 2S/3 = 2(2P+S)/3, so the (P,S) sensitivity is ONLY the floor-rounding wobble
(bounded ~±1-2 in penalty base, head notes only). This script measures the ACTUAL
final-FG-score spread across (P,S)-twins that share 2P+S (hence identical base score),
on real TWO-color songs, via the CPU exact FG scorer. Single-color songs are unaffected.

It answers: is the gap big enough to flip a per-song FG winner (=> fix the representation),
or sub-0.01% rounding (=> fail-loud guard + document)?

Usage: python tools/dev/prove_skyline_fg_fold_gap.py [--difficulty Easy] [--songs 5] [--forced 20]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _twin_partitions(C: int) -> list[tuple[int, int]]:
    """All (P,S) with 2P+S = C, S>=0, P>=0, spanning the floor-rounding residues."""
    out = []
    for P in range(0, C // 2 + 1):
        S = C - 2 * P
        if S < 0:
            continue
        out.append((int(P), int(S)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--songs", type=int, default=5, help="number of two-color songs to test")
    ap.add_argument("--forced", type=int, default=20, help="forced greats in section 0")
    args = ap.parse_args()

    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact
    from gear_optimizer.solver.scoring.fg_policy import compute_great_penalty_base

    ref_arrays = build_ref_arrays_from_stats(read_table(os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")), dtype=np.float64)

    folder = os.path.join(REPO_ROOT, "Data", args.difficulty)
    two_color = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".txt"):
            continue
        cs = get_base_calc_song(os.path.join(folder, fn), {})
        m = (cs or {}).get("metadata", {}) or {}
        p, s = str(m.get("Primary Color") or ""), str(m.get("Secondary Color") or "")
        if p and s and p != s:
            two_color.append((fn, p, s, cs))
            if len(two_color) >= args.songs:
                break

    print(f"[scan] found {len(two_color)} two-color {args.difficulty} songs (primary != secondary)")
    if not two_color:
        print("No two-color songs -> the fold is lossless for this difficulty's corpus.")
        return 0

    # Fixed non-color stats; large CM amplifies the per-great penalty scaling.
    base_stats = {"Perfect Points": 50, "Combo Multiplier": 90, "Fever Multiplier": 80,
                  "Fever Fill Rate": 60, "Fever Time": 40}
    C_levels = [9, 60, 150]  # 2P+S totals to probe (small, mid, near-cap)

    worst_overall = 0
    for fn, p, s, cs in two_color:
        print(f"\n=== {fn}  (primary={p}, secondary={s}) ===")
        for C in C_levels:
            twins = _twin_partitions(C)
            rows = []
            for (P, S) in twins:
                stats = dict(base_stats)
                stats[p] = int(P)
                stats[s] = int(S)
                r = evaluate_force_greats_exact(stats, cs, ref_arrays, [int(args.forced), 0])
                if r is None:
                    continue
                rows.append((P, S, int(r["base_score"]), int(r["final_score"]),
                             int(r.get("score_penalty", 0) or 0),
                             int(compute_great_penalty_base(P, S, single_color=False))))
            if not rows:
                continue
            bases = {b for *_h, b, _f, _pen, _pb in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]}
            base_scores = sorted({r[2] for r in rows})
            finals = sorted({r[3] for r in rows})
            fg_spread = finals[-1] - finals[0]
            pb_spread = max(r[5] for r in rows) - min(r[5] for r in rows)
            base_equal = (len(base_scores) == 1)
            worst_overall = max(worst_overall, fg_spread)
            pct = (fg_spread / finals[-1] * 100.0) if finals[-1] else 0.0
            flag = "  <-- BASE NOT EQUAL (unexpected!)" if not base_equal else ""
            print(f"  C=2P+S={C:>3}: twins={len(rows):>3}  base_score={'EQUAL' if base_equal else base_scores}  "
                  f"penalty_base_spread={pb_spread}  FG_spread={fg_spread:,} ({pct:.5f}% of {finals[-1]:,}){flag}")
            # show the extreme twins
            best = max(rows, key=lambda r: r[3])
            worst = min(rows, key=lambda r: r[3])
            print(f"            best FG (P={best[0]},S={best[1]}) final={best[3]:,}  vs  "
                  f"worst FG (P={worst[0]},S={worst[1]}) final={worst[3]:,}")

    print(f"\n=== SUMMARY ===")
    print(f"max FG spread across all base-equal (P,S)-twins tested: {worst_overall:,} points")
    print("Interpretation: this is the largest FG error the (P,S)->2P+S fold can cause for a")
    print("FIXED base score. If << typical winner margins, the fold ~never flips a winner")
    print("(=> guard+document); if comparable, the representation must carry (P,S).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
