"""How many DISTINCT FG-response geometry keys does the full 161x161 (ft,ff) grid
actually collapse to per chart? The body-DP cost is per DISTINCT key, NOT per grid
cell -- raw_fill_by_ff (ff axis) and real_time_by_ft (ft axis) take far fewer than
161 distinct values, and the body_tails frontier depends only on (fill, real_time,
nfb, ufgt). This sets the true projection denominator (the 161*161=25921 grid-cell
count over-counts the GPU body-DP work by the collapse factor).

Reports, per chart across n: the distinct count of the kernel-arg tuple that the
body DP depends on -> the production de-dup that `_requested_response_stat_keys`
+ the response-cache frontier de-dup realize.

Run: python tools/dev/_fg_distinct_keys.py
"""
import importlib.util
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rgm = _load("rgv_dk", "_fg_real_grid_validate.py")


def distinct_for_chart(path, ref_arrays):
    calc_song = rgm.load_song(path)
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes
    si, raw_fill_by_ff, nfb_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    R = TOTAL_ROWS
    # The body DP depends on: later_fill (=ceil over fill schedule), real_time (ft),
    # nfb (ff), ufgt. The kernel args are a deterministic function of
    # (raw_fill_by_ff[ff], nfb_by_ff[ff], real_time_by_ft[ft], ufgt). Distinct over
    # the full grid = distinct (ff-pair) x distinct (ft value) since they are
    # separable axes. The BODY-frontier (body_tails) depends on (fill schedule,
    # real_time, nfb) -> count distinct (round(raw_fill,6), nfb, round(real_time,6)).
    ff_keys = set()
    for ff in range(R + 1):
        ff_keys.add((round(float(raw_fill_by_ff[ff]), 6), int(nfb_by_ff[ff])))
    ft_keys = set()
    for ft in range(R + 1):
        ft_keys.add(round(float(real_time_by_ft[ft]), 6))
    distinct_ffft = len(ff_keys) * len(ft_keys)
    return n, len(ff_keys), len(ft_keys), distinct_ffft


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()
    # sample across the pool: small, quartiles, p90, p99, max
    idxs = sorted(set([0,
                       next(i for i, (c, _) in enumerate(sc) if c >= 8),
                       len(sc) // 4, len(sc) // 2, (3 * len(sc)) // 4,
                       int(len(sc) * 0.90), int(len(sc) * 0.99), len(sc) - 1]))
    print(f"  pool charts={len(sc)}  grid cells/chart = {(R := TOTAL_ROWS)+1}x{R+1} = {(R+1)*(R+1)}")
    print(f"  {'n':>6}  {'#ff-keys':>9}  {'#ft-keys':>9}  {'distinct':>9}  {'collapse':>9}")
    ratios = []
    rows = []
    for i in idxs:
        c, p = sc[i]
        n, nff, nft, dk = distinct_for_chart(p, ref_arrays)
        cells = (TOTAL_ROWS + 1) ** 2
        ratio = cells / max(1, dk)
        ratios.append((n, dk))
        rows.append((n, nff, nft, dk, ratio))
        print(f"  {n:>6}  {nff:>9}  {nft:>9}  {dk:>9}  {ratio:>8.1f}x")
    # geometric-mean collapse + a fitted distinct(n)
    dks = np.array([r[3] for r in rows], dtype=float)
    ns = np.array([r[0] for r in rows], dtype=float)
    print(f"\n  distinct-keys/chart: min={int(dks.min())} median={int(np.median(dks))} max={int(dks.max())}")
    print(f"  mean collapse factor (cells/distinct): {np.mean([r[4] for r in rows]):.1f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
