"""CONCURRENCY PROBE: how many block-per-key WORKGROUPS does the RX 7900 XTX run
CONCURRENTLY for the parallel-skyline body-DP kernel? This is the load-bearing
constant for the saturated full-pool model (mission task #c):
    wall ~= total_block_work / concurrent_blocks.

Method: pick a FIXED moderately-heavy body-DP cell (one (ft,ff) geometry on a
mid/heavy chart) and run it REPLICATED at launch sizes K=1,2,4,...,N (all lanes
identical -> each block does the SAME single-block work W). Measure total wall T(K).
  - If blocks run concurrently, T(K) ~= W (flat) while K <= C (capacity).
  - Once K > C, T(K) ~= W * ceil(K/C) (linear in waves).
So C = the knee: the largest K with T(K) ~= T(1) (within ~1.5x). Equivalently
C ~= K / (T(K)/T(1)) on the linear branch. We report T(K), the per-block amortized
T(K)/K, and the inferred concurrent-block capacity C.

BD=64 threads/block = one AMD wavefront. The 7900 XTX has 96 CUs; each CU can hold
several wavefronts -> C is an EMPIRICAL throughput width, not a nameplate number.

Read-only. Run: python tools/dev/_fg_concurrency_probe.py
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


par = _load("bbp_cc", "_fg_block_body_dp_parallel.py")
rgm = _load("rgv_cc", "_fg_real_grid_validate.py")
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402


def _time_one_launch(a_single, n, ts, great, K, caps, reps=3):
    """Replicate the single geometry K times into ONE launch; return best wall ms."""
    args = [a_single] * K
    # warm
    par.run_block_par(args, n, ts, great, n_keys_per_launch=K, caps=caps)
    ti.sync()
    best = math.inf
    for _ in range(reps):
        _, t = par.run_block_par(args, n, ts, great, n_keys_per_launch=K, caps=caps)
        best = min(best, t["total_ms"])
    return best


def probe_chart(label, n_target, path, ref_arrays, cell, Ks):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    pmx = max(rgm.pair_mod_for(n, int(math.ceil(float(rfb[ff])))) for ff in range(TOTAL_ROWS + 1))
    cb = max(64, pmx + 16); ccd = max(8192, (pmx + 4) * 256); caps = (cb, ccd)
    ft, ff = cell
    a, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, [cell])
    a0 = a[0]
    print(f"\n=== CONCURRENCY [{label}] n={n} cell=(ft={ft},ff={ff}) pair_mod_max={pmx} ===")
    T1 = None
    print(f"  {'K':>5}  {'T(K) ms':>10}  {'T/K ms':>9}  {'T(K)/T(1)':>10}  {'implied C':>10}")
    rows = []
    for K in Ks:
        try:
            T = _time_one_launch(a0, n, ts, great, K, caps)
        except Exception as exc:
            print(f"  {K:>5}  FAILED ({type(exc).__name__}: {str(exc)[:50]})")
            break
        if T1 is None:
            T1 = T
        ratio = T / T1
        impliedC = K / ratio if ratio > 0 else float("nan")  # on linear branch ~= capacity
        print(f"  {K:>5}  {T:>10.1f}  {T/K:>9.3f}  {ratio:>10.2f}  {impliedC:>10.1f}")
        rows.append((K, T, T / K, ratio, impliedC))
    # capacity estimate: max implied-C over the measured Ks where ratio>1.3 (linear branch)
    lin = [r for r in rows if r[3] >= 1.3]
    if lin:
        Cest = max(r[4] for r in lin)
        # also the throughput-plateau: min T/K reached
        tpk_floor = min(r[2] for r in rows)
        print(f"  -> inferred concurrent-block capacity C ~= {Cest:.0f}  "
              f"(per-block throughput floor {tpk_floor:.3f} ms at saturation)")
        return dict(n=n, Cest=Cest, tpk_floor=tpk_floor)
    print(f"  -> launches stayed flat (latency-bound) up to K={Ks[-1]}: C >= {Ks[-1]}")
    return dict(n=n, Cest=float(Ks[-1]), tpk_floor=min(r[2] for r in rows) if rows else float("nan"))


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    # Use mid-weight cells so a single block is long enough to expose waves but not
    # TDR-bomb at large K. (ft=40,ff=120) is a solid body-DP cell (not the extreme
    # (0,160)). Sweep K geometrically.
    Ks = [1, 2, 4, 8, 16, 32, 48, 64, 96, 128, 192, 256, 384, 512]
    probes = [
        ("MED1083", 1083, (40, 120)),
        ("P90-2312", 2312, (40, 120)),
    ]
    results = []
    for lbl, tgt, cell in probes:
        c, p = nearest(tgt)
        try:
            results.append(probe_chart(lbl, tgt, p, ref_arrays, cell, Ks))
        except Exception as exc:
            import traceback
            print(f"  {lbl} FAILED: {type(exc).__name__}: {exc}"); traceback.print_exc()
    if results:
        Cs = [r["Cest"] for r in results if math.isfinite(r["Cest"])]
        print(f"\n  CONCURRENT-BLOCK CAPACITY (median over probes): C ~= {int(np.median(Cs))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
