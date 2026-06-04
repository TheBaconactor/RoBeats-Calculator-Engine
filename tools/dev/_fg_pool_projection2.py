"""REALISTIC saturated full-pool projection: separate FAST-PATH keys from BODY-DP
keys (the prior projection over-counted because the block kernel ran the full body
DP even on fast-path-eligible keys, which production SKIPS via the Phase-1 fast
path -- first_fill[0] >= 100). On the heaviest charts the heaviest low-ft/high-ff
cells are fast-path eligible, so costing them as body-DP work was wildly wrong.

Production cost per chart =
    (#fast-path keys) * fastpath_ms/key      [cheap O(n) sweep, no skyline]
  + (#body-DP keys)  * bodydp_ms/key(n,...)  [the PARALLEL-skyline kernel]

We measure, per anchor n over the full 161x161 grid:
  - frac_fast: fraction of cells with first_fill[0] >= 100 (fast-path eligible)
  - bodydp saturated ms/key: PARALLEL kernel over a representative sample of the
    NON-fast-path cells (TDR-safe chunk), = total_wall / n_bodydp_keys
  - fastpath ms/key: the main-kernel fast path over the fast-path cells.
Then integrate over the real note histogram (25921 cells/chart, no collapse).

Run: python tools/dev/_fg_pool_projection2.py
"""
import importlib.util
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


par = _load("bbp_p2", "_fg_block_body_dp_parallel.py")
probe = par.probe
rgm = _load("rgv_p2", "_fg_real_grid_validate.py")
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402


def _time_par(args, n, ts, great, nk, caps, reps=2):
    par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
    ti.sync()
    b = math.inf
    for _ in range(reps):
        _, t = par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
        b = min(b, t["total_ms"])
    return b


def _time_thread_fastpath(args, n, ts, great, chunk, reps=2):
    probe.run_kernel(args, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
    ti.sync()
    b = math.inf
    for _ in range(reps):
        t0 = time.perf_counter()
        probe.run_kernel(args, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
        ti.sync()
        b = min(b, (time.perf_counter() - t0) * 1000.0)
    return b


def anchor_costs(label, n, path, ref_arrays):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    pmx = max(rgm.pair_mod_for(n, int(math.ceil(float(rfb[ff])))) for ff in range(TOTAL_ROWS + 1))
    cb = max(64, pmx + 16); ccd = max(8192, (pmx + 4) * 256); caps = (cb, ccd)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))

    # classify the FULL grid by fast-path eligibility. first_fill[0] =
    # max(0, ceil(raw_fever_fill) - 1) (response_builder._action_table), and the
    # Phase-1 fast path triggers iff first_fill[0] >= 100  <=>  ceil(raw_fill_by_ff[ff]) >= 101.
    # Eligibility depends on ff ONLY (ft doesn't change first_fill) -> grid frac == ff frac.
    R = TOTAL_ROWS
    fast_ff = np.array([max(0, int(math.ceil(float(rfb[ff]))) - 1) >= 100 for ff in range(R + 1)], dtype=bool)
    frac_fast = float(fast_ff.mean())

    # BODY-DP cost: representative sample of NON-fast-path cells (ft spread x non-fast ff)
    nonfast_ff = [ff for ff in range(R + 1) if not fast_ff[ff]]
    fast_ff_list = [ff for ff in range(R + 1) if fast_ff[ff]]
    bodydp_pk = float("nan"); fastpath_pk = float("nan")
    n_body_keys = 0
    if nonfast_ff:
        step_ft = 1 if n <= 1500 else (4 if n <= 3500 else 8)
        ff_sample = nonfast_ff[:: max(1, len(nonfast_ff) // 24 or 1)]
        bkeys = sorted({(ft, ff) for ft in range(0, R + 1, step_ft) for ff in ff_sample})
        bargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, bkeys)
        n_body_keys = len(bargs)
        chunk = min(n_body_keys, 384 if n <= 1500 else (64 if n <= 3500 else (16 if n <= 5500 else 8)))
        while chunk >= 1:
            try:
                ms = _time_par(bargs, n, ts, great, nk=chunk, caps=caps)
                bodydp_pk = ms / n_body_keys
                break
            except Exception:
                chunk //= 2
    if fast_ff_list:
        step_ft = 1 if n <= 1500 else 4
        ffs = fast_ff_list[:: max(1, len(fast_ff_list) // 24 or 1)]
        fkeys = sorted({(ft, ff) for ft in range(0, R + 1, step_ft) for ff in ffs})
        fargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, fkeys)
        fchunk = min(len(fargs), 256 if n <= 1500 else (32 if n <= 3500 else 8))
        try:
            fms = _time_thread_fastpath(fargs, n, ts, great, chunk=fchunk)
            fastpath_pk = fms / len(fargs)
        except Exception as exc:
            print(f"    fastpath timing failed: {type(exc).__name__}", flush=True)

    print(f"--- [{label}] n={n} long={si.long_notes} frac_fast={frac_fast:.2f} "
          f"(#nonfast_ff={len(nonfast_ff)}) ---")
    print(f"    body-DP ms/key (parallel, {n_body_keys} keys) : {bodydp_pk:9.4f}")
    print(f"    fast-path ms/key (main kernel)               : {fastpath_pk:9.4f}", flush=True)
    return dict(label=label, n=n, frac_fast=frac_fast, bodydp_pk=bodydp_pk, fastpath_pk=fastpath_pk)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    targets = [60, 300, 653, 1083, 1655, 2312, 3522, 4722, 6843]
    seen = set(); rows = []
    for t in targets:
        c, p = nearest(t)
        if p in seen:
            continue
        seen.add(p)
        try:
            rows.append(anchor_costs(f"A{t}", c, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  A{t} n={c} FAILED: {type(exc).__name__}: {exc}"); traceback.print_exc()

    print("\n\n========== REALISTIC FULL-POOL PROJECTION ==========")
    cells = (TOTAL_ROWS + 1) ** 2
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    ns = np.array([r["n"] for r in rows], dtype=float)
    bpk = np.array([r["bodydp_pk"] for r in rows], dtype=float)
    fpk = np.array([r["fastpath_pk"] for r in rows], dtype=float)
    ffast = np.array([r["frac_fast"] for r in rows], dtype=float)

    print("  anchor n  frac_fast  bodydp_ms/key  fastpath_ms/key")
    for r in rows:
        print(f"     {r['n']:>5}    {r['frac_fast']:.2f}      {r['bodydp_pk']:9.4f}     {r['fastpath_pk']:9.4f}")

    # fit body-DP ms/key ~ a*n^p (body-bearing, finite) ; frac_fast(n) ~ linear-ish (interp)
    mb = (bpk > 0) & np.isfinite(bpk) & (ns >= 150)
    mf = (fpk > 0) & np.isfinite(fpk) & (ns >= 150)
    if mb.sum() < 2 or mf.sum() < 2:
        print("  insufficient anchors"); return 0
    pb = np.polyfit(np.log(ns[mb]), np.log(bpk[mb]), 1); body_a, body_p = math.exp(pb[1]), pb[0]
    pf = np.polyfit(np.log(ns[mf]), np.log(fpk[mf]), 1); fast_a, fast_p = math.exp(pf[1]), pf[0]
    # frac_fast vs n: monotone-ish; use nearest-anchor interpolation on sorted n.
    order = np.argsort(ns)
    ns_s, ff_s = ns[order], ffast[order]

    def frac_fast_at(nn):
        return float(np.interp(nn, ns_s, ff_s, left=ff_s[0], right=ff_s[-1]))

    est_body = body_a * np.power(pool_ns, body_p)
    est_fast = fast_a * np.power(pool_ns, fast_p)
    body_floor = float(bpk[mb].min()); fast_floor = float(fpk[mf].min())
    est_body = np.maximum(est_body, body_floor); est_fast = np.maximum(est_fast, fast_floor)
    fr = np.array([frac_fast_at(nn) for nn in pool_ns])
    per_chart_ms = cells * (fr * est_fast + (1.0 - fr) * est_body)
    pool_s = per_chart_ms.sum() / 1000.0
    print(f"\n  body-DP   fit ms/key = {body_a:.3e} * n^{body_p:.3f} (floor {body_floor:.4f})")
    print(f"  fast-path fit ms/key = {fast_a:.3e} * n^{fast_p:.3f} (floor {fast_floor:.4f})")
    print(f"\n    full-pool GPU (1 process)          : {pool_s:9.1f} s = {pool_s/60:6.2f} min")
    print(f"    full-pool GPU (2 production procs) : {pool_s/2:9.1f} s = {pool_s/2/60:6.2f} min")
    print(f"\n  ---- targets ----   <15min = 900s ;  CPU baseline = 1860s (~31min)")
    print(f"  HEADLINE: 2-proc realistic pool = {pool_s/2/60:.1f} min -> "
          f"{'REACHES' if pool_s/2 <= 900 else 'DOES NOT reach'} <15min")
    # breakdown: where does the pool time go?
    body_share = (cells * (1 - fr) * est_body).sum() / per_chart_ms.sum()
    print(f"\n  pool time split: body-DP keys {body_share*100:.0f}% / fast-path keys {(1-body_share)*100:.0f}%")
    heavy_mask = pool_ns >= 2000
    heavy_share = per_chart_ms[heavy_mask].sum() / per_chart_ms.sum()
    print(f"  charts n>=2000 are {int(heavy_mask.sum())}/{len(pool_ns)} of charts but "
          f"{heavy_share*100:.0f}% of pool time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
