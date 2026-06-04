"""Measure the TRUE saturated fast-path per-cell GPU cost (the production early-out),
amortized over a SATURATING launch so per-launch fixed overhead is negligible. The
corrected projection's fp_pk was measured over tiny 20-97-cell launches -> overhead-
dominated (9.8-154 ms/key, absurd for an O(n*ac) early-out). Here we tile ACTUAL
fast-path cells up to >=512 per launch and divide -> the real per-cell fast cost.

The fast path runs the main kernel with max_phase=3 (reachability + fast-path branch,
no body DP) on first_fill[0]>=100 + inner-early-out cells. Production GPU build would
dispatch only this cheap path on fast cells; it is structurally <= any body-DP cell.

Read-only. Run: python tools/dev/_fg_fastpath_cost.py
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

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


fpr = _load("fpr_fc", "_fg_fastpath_reconcile.py")
rgm = fpr.rgm
probe = _load("bbp_fc", "_fg_block_body_dp_parallel.py").probe
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402


def fp_cost(label, n_target, path, ref_arrays, launch=512):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    R = TOTAL_ROWS
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)
    # collect ACTUAL fast-path cells (sample the grid)
    fast = []
    for ft in range(0, R + 1, 8):
        for ff in range(0, R + 1, 4):
            a = fpr.fgp.build_kernel_args(
                timestamps=ts, great_candidate_timestamps=great,
                raw_fever_fill=float(rfb[ff]), non_fever_base=int(nfb[ff]),
                real_fever_time=float(rtb[ft]), use_forced_great_timing=ufgt,
            )
            if fpr._is_fast_path(a, n):
                fast.append((ft, ff))
    if not fast:
        print(f"--- FP [{label}] n={n}: NO fast-path cells (frac_fast=0) ---")
        return dict(n=n, fp_pk=float("nan"))
    while len(fast) < launch:
        fast = fast + fast
    fast = fast[:launch]
    fargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, fast)
    chunk = min(len(fargs), launch)
    # shrink on device-lost (big n)
    while chunk >= 1:
        try:
            probe.run_kernel(fargs, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
            ti.sync()
            best = math.inf
            for _ in range(3):
                t0 = time.perf_counter()
                probe.run_kernel(fargs, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
                ti.sync()
                best = min(best, (time.perf_counter() - t0) * 1000.0)
            break
        except Exception:
            chunk //= 2
    fp_pk = best / len(fargs)
    print(f"--- FP [{label}] n={n}  launch={len(fargs)} chunk={chunk} : "
          f"{best:8.1f} ms total -> {fp_pk:7.5f} ms/key ---", flush=True)
    return dict(n=n, fp_pk=fp_pk)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    rows = []
    for tgt in (653, 1083, 2312, 4722, 7027):
        c, p = nearest(tgt)
        try:
            rows.append(fp_cost(f"A{tgt}", tgt, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  A{tgt} FAILED: {type(exc).__name__}: {exc}"); traceback.print_exc()
    finite = [r for r in rows if math.isfinite(r["fp_pk"])]
    if finite:
        ns = np.array([r["n"] for r in finite], float)
        fp = np.array([r["fp_pk"] for r in finite], float)
        lp = np.polyfit(np.log(ns), np.log(fp), 1)
        print(f"\n  saturated fast-path fit ms/key = {math.exp(lp[1]):.3e} * n^{lp[0]:.3f}")
        print(f"  fast-path ms/key range: {fp.min():.5f} (n={int(ns[fp.argmin()])}) .. "
              f"{fp.max():.5f} (n={int(ns[fp.argmax()])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
