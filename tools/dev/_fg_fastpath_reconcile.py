"""FAST-PATH RECONCILIATION (mission task #2 crux): over the FULL 161x161=25,921
geometry grid per real chart, count how many geometries take the Phase-1 EARLY-OUT
(fast path, NO body DP) vs actually RUN the body DP -- using the PRODUCTION Numba
producer `_first_frontier_from_precomputed_end_indices_numba` as ground truth.

The producer's early-out (response_build_gpu_numba.py:1267-1303) returns
states_evaluated (se) == 0 directly when:
  first_fill[0] >= 100  AND  (zero_body_fever >= n-100  OR  zero_body_fever == max_body_fever).
When the body DP runs, se > 0. So `se == 0` EXACTLY identifies a fast-path geometry
(no body DP); `se > 0` is a body-DP geometry. We call the REAL producer per geometry
and tally.

This reconciles the two prior claims:
  - "~53% body-DP at ft=0 for n=7027" (an earlier ft=0-row profile), vs
  - "n>=2000 is ~100% fast-path across the full grid" (a later claim).
We also report the per-ft-band fast-path% to expose whether body-DP geometries are
concentrated in a low-ft band (the early-out's inner condition is ft-dependent via
real_time_idx, the outer first_fill[0]>=100 gate is ff-only).

Read-only on production modules. Numba-only (no GPU).
Run: python tools/dev/_fg_fastpath_reconcile.py
"""
import importlib.util
import math
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _numba_zero_forced_body_fever_precomputed,
    _numba_max_body_fever_precomputed,
)


def _is_fast_path(a, n):
    """EXACT mirror of `_first_frontier_from_precomputed_end_indices_numba` early-out
    (response_build_gpu_numba.py:1267-1303). Returns True iff the producer takes the
    fast path (se==0, NO body DP). Calls only the cheap O(n*ac) predicate functions,
    NOT the full backward DP -- so classifying the whole grid is fast even on n=7027.
    """
    action_count = int(a["action_count"])
    first_fill = a["first_fill"]
    if not (action_count > 0 and int(first_fill[0]) >= 100):
        return False
    zero_body_fever = int(_numba_zero_forced_body_fever_precomputed(
        int(n), a["later_fill"], a["later_forced"], a["first_fill"], a["first_forced"],
        a["later_activation_forced"], a["first_activation_forced"],
        int(a["use_forced_great_timing_i"]), a["timestamps"], a["great_candidate_timestamps"],
        a["timestamp_end_idx"], a["great_end_idx"], int(a["real_time_idx"]),
    ))
    if zero_body_fever < 0:
        return False
    if zero_body_fever >= max(0, int(n) - 100):
        return True
    max_body_fever = int(_numba_max_body_fever_precomputed(
        int(n), int(action_count), a["later_fill"], a["first_fill"], a["later_forced"],
        a["first_forced"], a["later_activation_forced"], a["first_activation_forced"],
        int(a["use_forced_great_timing_i"]), a["timestamps"], a["great_candidate_timestamps"],
        a["timestamp_end_idx"], a["great_end_idx"], int(a["real_time_idx"]),
    ))
    return zero_body_fever == max_body_fever


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rgm = _load("rgv_fp", "_fg_real_grid_validate.py")
fgp = rgm.fgp  # parity harness: build_kernel_args / numba_first_frontier


def reconcile_chart(label, n_target, path, ref_arrays):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    R = TOTAL_ROWS
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)

    # OUTER-gate (ff-only) fast eligibility: first_fill[0] = max(0, ceil(rfb[ff])-1) >= 100.
    outer_fast_ff = np.array(
        [max(0, int(math.ceil(float(rfb[ff]))) - 1) >= 100 for ff in range(R + 1)], dtype=bool
    )
    frac_outer = float(outer_fast_ff.mean())

    # Build the per-ff kernel-arg template ONCE per ff (first_fill etc. depend only on ff),
    # then vary real_time_idx per ft. build_kernel_args bakes real_fever_time, so we must
    # rebuild per (ft,ff). To keep it tractable we cache by ff the static action arrays and
    # only swap the end-index precompute via build_kernel_args (cheap relative to the DP).
    # VERIFY the cheap early-out predicate == the real producer's se==0 on a sample
    # (incl. ft=0 + heavy corners) before trusting it grid-wide.
    vfail = 0
    vsample = [(ft, ff) for ft in (0, 5, 40, 160) for ff in (0, 80, 150, 159, 160)]
    for (ft, ff) in vsample:
        a = fgp.build_kernel_args(
            timestamps=ts, great_candidate_timestamps=great,
            raw_fever_fill=float(rfb[ff]), non_fever_base=int(nfb[ff]),
            real_fever_time=float(rtb[ft]), use_forced_great_timing=ufgt,
        )
        _o, se, _g, _r, _m = fgp.numba_first_frontier(a)
        if (int(se) == 0) != _is_fast_path(a, n):
            vfail += 1
            print(f"  VERIFY MISMATCH (ft={ft},ff={ff}): se={se} predicate_fast={_is_fast_path(a, n)}")
    if vfail:
        raise RuntimeError(f"early-out predicate disagrees with producer on {vfail} sample cells")

    t0 = time.perf_counter()
    body_dp = 0          # se > 0  (runs body DP)
    fast = 0             # se == 0 (fast-path early-out)
    per_ft_body = np.zeros(R + 1, dtype=np.int64)   # body-DP count per ft row
    per_ft_total = np.zeros(R + 1, dtype=np.int64)
    # Among OUTER-fast ff columns, how many geometries still run body DP (inner cond fails)?
    outer_fast_but_bodydp = 0
    outer_fast_cells = 0

    for ft in range(R + 1):
        rt = float(rtb[ft])
        for ff in range(R + 1):
            a = fgp.build_kernel_args(
                timestamps=ts,
                great_candidate_timestamps=great,
                raw_fever_fill=float(rfb[ff]),
                non_fever_base=int(nfb[ff]),
                real_fever_time=rt,
                use_forced_great_timing=ufgt,
            )
            is_fast = _is_fast_path(a, n)
            per_ft_total[ft] += 1
            if is_fast:
                fast += 1
            else:
                body_dp += 1
                per_ft_body[ft] += 1
                if outer_fast_ff[ff]:
                    outer_fast_but_bodydp += 1
            if outer_fast_ff[ff]:
                outer_fast_cells += 1
    wall = time.perf_counter() - t0

    cells = (R + 1) ** 2
    frac_fast_actual = fast / cells
    # ft band where body DP concentrates: lowest ft with body-DP geometries and highest.
    body_ft_rows = np.nonzero(per_ft_body > 0)[0]
    if body_ft_rows.size:
        ft_lo, ft_hi = int(body_ft_rows.min()), int(body_ft_rows.max())
    else:
        ft_lo = ft_hi = -1

    print(f"\n=== RECONCILE [{label}] n={n} (full {cells}-cell grid, {wall:.1f}s) ===")
    print(f"  OUTER-gate (ff-only, first_fill[0]>=100) fast fraction : {frac_outer:6.3f}  "
          f"({int(outer_fast_ff.sum())}/{R+1} ff-columns)")
    print(f"  ACTUAL fast-path (se==0, NO body DP)  geometries       : {fast:6d}  "
          f"({frac_fast_actual*100:5.2f}%)")
    print(f"  ACTUAL body-DP   (se> 0, runs body DP) geometries      : {body_dp:6d}  "
          f"({body_dp/cells*100:5.2f}%)")
    if outer_fast_cells:
        print(f"  of the {outer_fast_cells} OUTER-fast cells, still body-DP (inner fails): "
              f"{outer_fast_but_bodydp} ({outer_fast_but_bodydp/outer_fast_cells*100:.1f}%)")
    print(f"  body-DP geometries concentrated in ft band [{ft_lo}..{ft_hi}] "
          f"(of 0..{R})")
    # per-ft body-DP profile at a few rows incl ft=0 (the earlier-profiled row)
    sample_ft = [0, 5, 10, 20, 40, 80, 160]
    prof = ", ".join(f"ft={f}:{int(per_ft_body[f])}/{R+1}" for f in sample_ft)
    print(f"  per-ft body-DP count (sample rows): {prof}")
    return dict(label=label, n=n, cells=cells, fast=fast, body_dp=body_dp,
                frac_outer=frac_outer, frac_fast_actual=frac_fast_actual,
                ft_lo=ft_lo, ft_hi=ft_hi, per_ft_body=per_ft_body.copy())


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    # mission charts + a couple extra to see the trend in body-DP geometry counts
    targets = [1083, 2312, 4722, 7027]
    seen = set()
    rows = []
    for t in targets:
        c, p = nearest(t)
        if p in seen:
            continue
        seen.add(p)
        try:
            rows.append(reconcile_chart(f"~{t}", t, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  ~{t} n={c} FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    print("\n\n========== FAST-PATH RECONCILIATION SUMMARY ==========")
    print(f"  {'n':>6}  {'fast%':>7}  {'bodyDP%':>8}  {'bodyDP_count':>12}  {'ft_band':>10}")
    for r in rows:
        band = f"{r['ft_lo']}..{r['ft_hi']}" if r['ft_lo'] >= 0 else "none"
        print(f"  {r['n']:>6}  {r['frac_fast_actual']*100:6.2f}%  "
              f"{r['body_dp']/r['cells']*100:7.2f}%  {r['body_dp']:>12}  {band:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
