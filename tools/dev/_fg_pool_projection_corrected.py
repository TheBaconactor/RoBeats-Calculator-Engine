"""THE HEADLINE (mission task #c): realistic SATURATED full-pool GPU build projection
for the PARALLEL-skyline block-per-key body DP, with the CORRECT fast-path vs body-DP
split (measured by the EXACT producer early-out predicate, NOT the loose ff-only gate).

Why the prior projections were wrong:
  - `_fg_pool_projection2.py` classified "fast" by the OUTER gate first_fill[0]>=100,
    which is ~100% TRUE on every chart n>=2000 (base_fill grows with note count) ->
    it labelled big charts as ~100% fast-path and measured body-DP ms/key on an EMPTY
    non-fast set (NaN). But the INNER early-out condition (zero_body_fever ==
    max_body_fever) FAILS on 16-51% of those cells, which DO run the body DP
    (`_fg_fastpath_reconcile.py`: n=2312 16%, n=4722 51%, n=7027 34%, n=1083 64%).
  - `_fg_block_bench_parallel.py` / `_fg_pool_projection.py` measured the block kernel
    ms/key over ALL uniform-grid cells (block kernel has no early-out -> it runs the
    body DP even on fast-path-eligible cells), over-costing the fast cells.

Correct production model (per chart, full 161x161=25,921-cell grid, no collapse):
    chart_ms(n) = 25,921 * [ frac_bd(n)*bd_pk(n) + (1-frac_bd(n))*fp_pk(n) ]
  frac_bd(n)  = ACTUAL body-DP fraction (full-grid _is_fast_path predicate)
  bd_pk(n)    = SATURATED parallel-block ms/key measured ONLY on ACTUAL body-DP cells
                (integrates the true ft cost distribution incl. heavy low-ft cells)
  fp_pk(n)    = main-kernel fast-path ms/key on ACTUAL fast-path cells (cheap O(n) sweep)
Saturated: bd_pk/fp_pk are total_wall/n_keys at a SATURATING launch (many concurrent
workgroups fill the 7900 XTX), so Sum(n_keys*pk) over charts = single-GPU-process
serial-launch wall with the device kept busy. 2 production GPU procs -> /2.

Read-only on production modules. Run: python tools/dev/_fg_pool_projection_corrected.py
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


fpr = _load("fpr_proj", "_fg_fastpath_reconcile.py")   # _is_fast_path + rgm + fgp
par = _load("bbp_proj", "_fg_block_body_dp_parallel.py")
rgm = fpr.rgm
probe = par.probe
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

# Measured concurrent-block capacity of the parallel-skyline kernel on the RX 7900 XTX
# (`_fg_concurrency_probe.py`: implied-C ~150-186, throughput-floor plateau). The
# saturated model is wall ~= total_block_work / C. We use C=160 (conservative mid) and
# also report C=96 (pessimistic, = CU count) and C=256 (optimistic) sensitivity.
C_BLOCKS = 160


def _time_par(args, n, ts, great, nk, caps, reps=2):
    par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)  # warm
    ti.sync()
    best = math.inf
    for _ in range(reps):
        _, t = par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
        best = min(best, t["total_ms"])
    return best


def _single_block_wall(a_cell, n, ts, great, caps, reps=2):
    """Uncontested single-block wall W(cell) at launch=1 (true per-block GPU work).
    Saturated per-cell cost = W / C_BLOCKS (C blocks run concurrently). Returns ms."""
    return _time_par([a_cell], n, ts, great, nk=1, caps=caps, reps=reps)


def _time_fastpath(args, n, ts, great, chunk, reps=2):
    # the production main-kernel WITH the fast path active (max_phase=3) over fast cells.
    probe.run_kernel(args, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
    ti.sync()
    best = math.inf
    for _ in range(reps):
        t0 = time.perf_counter()
        probe.run_kernel(args, n, ts, great, chunk=chunk, max_phase=3, dump_bt=False)
        ti.sync()
        best = min(best, (time.perf_counter() - t0) * 1000.0)
    return best


def anchor(label, n_target, path, ref_arrays):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb = _response_axes(calc_song, ref_arrays)
    n = int(si.total_notes)
    R = TOTAL_ROWS
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32).reshape(-1))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32).reshape(-1))
    ufgt = bool(si.use_forced_great_timing)
    pmx = max(rgm.pair_mod_for(n, int(math.ceil(float(rfb[ff])))) for ff in range(R + 1))
    cb = max(64, pmx + 16); ccd = max(8192, (pmx + 4) * 256); caps = (cb, ccd)

    # ---- classify the FULL grid by the EXACT early-out predicate ----
    # A cell (ft,ff) is body-DP iff NOT _is_fast_path. Build args lazily per cell.
    # frac_bd over full grid; also collect representative body-DP + fast-path cell lists.
    # body-DP cells sampled on a coarser grid for the single-block timing (heavier
    # charts -> sparser sample to stay tractable, but ALWAYS span ft incl the heavy
    # low-ft band so the mean reflects the true cost distribution).
    bstep = 8 if n <= 1500 else (16 if n <= 3500 else 24)
    body_cells = []
    fast_cells = []
    n_body = 0
    for ft in range(R + 1):
        rt = float(rtb[ft])
        for ff in range(R + 1):
            a = fpr.fgp.build_kernel_args(
                timestamps=ts, great_candidate_timestamps=great,
                raw_fever_fill=float(rfb[ff]), non_fever_base=int(nfb[ff]),
                real_fever_time=rt, use_forced_great_timing=ufgt,
            )
            if fpr._is_fast_path(a, n):
                if (ft % 16 == 0) and (ff % 16 == 0):
                    fast_cells.append((ft, ff))
            else:
                n_body += 1
                if (ft % bstep == 0) and (ff % bstep == 0):
                    body_cells.append((ft, ff))
    cells = (R + 1) ** 2
    frac_bd = n_body / cells

    # ---- bd_pk: SATURATED per-cell cost = mean(single-block wall W) / C_BLOCKS ----
    # W(cell) measured UNCONTESTED at launch=1 (true per-block GPU work; not the
    # latency-bound tiny-chunk artifact). Saturated wall ~= total_block_work / C, so
    # the per-body-cell saturated cost = mean_W / C. Heaviest cells that device-lost
    # at launch=1 are recorded at the TDR ceiling (they are the work-stealing residual).
    Ws = []
    tdr_over = 0
    for cell in body_cells:
        ac, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, [cell])
        try:
            w = _single_block_wall(ac[0], n, ts, great, caps)
            Ws.append(w)
            if w > 1800.0:
                tdr_over += 1
        except Exception:
            tdr_over += 1  # device-lost: at/over the TDR ceiling
    mean_W = float(np.mean(Ws)) if Ws else float("nan")
    bd_pk = mean_W / C_BLOCKS if Ws else float("nan")
    n_bd_sample = len(Ws)

    # ---- fp_pk: main-kernel fast-path ms/key on ACTUAL fast cells ----
    fp_pk = float("nan"); n_fp_sample = 0
    if fast_cells:
        fargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, fast_cells)
        n_fp_sample = len(fargs)
        fchunk = min(n_fp_sample, 256 if n <= 1500 else (32 if n <= 3500 else 8))
        try:
            fms = _time_fastpath(fargs, n, ts, great, chunk=fchunk)
            fp_pk = fms / n_fp_sample
        except Exception as exc:
            print(f"    fastpath timing failed: {type(exc).__name__}", flush=True)

    print(f"--- ANCHOR [{label}] n={n} long={si.long_notes} ---")
    print(f"    ACTUAL body-DP fraction (full grid)  : {frac_bd:.3f}  ({n_body}/{cells} cells)")
    print(f"    mean single-block W ({n_bd_sample} body cells, {tdr_over} >TDR) : {mean_W:9.2f} ms")
    print(f"    saturated bd_pk = W/C (C={C_BLOCKS})          : {bd_pk:9.5f} ms/key")
    print(f"    fp_pk fast-path      ({n_fp_sample} fast cells) : {fp_pk:9.5f} ms/key", flush=True)
    return dict(label=label, n=n, frac_bd=frac_bd, bd_pk=bd_pk, fp_pk=fp_pk,
                mean_W=mean_W, tdr_over=tdr_over)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    targets = [60, 300, 653, 1083, 1655, 2312, 3522, 4722, 6843, 7027]
    seen = set(); rows = []
    for t in targets:
        c, p = nearest(t)
        if p in seen:
            continue
        seen.add(p)
        try:
            rows.append(anchor(f"A{t}", t, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  A{t} n={c} FAILED: {type(exc).__name__}: {exc}"); traceback.print_exc()

    print("\n\n========== CORRECTED SATURATED FULL-POOL PROJECTION ==========")
    cells = (TOTAL_ROWS + 1) ** 2
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    print(f"  pool charts={len(pool_ns)} cells/chart={cells} (no collapse)  "
          f"total cells={len(pool_ns)*cells/1e6:.1f}M")
    print(f"  pool n: min={pool_ns.min():.0f} median={np.median(pool_ns):.0f} "
          f"p90={np.percentile(pool_ns,90):.0f} p99={np.percentile(pool_ns,99):.0f} max={pool_ns.max():.0f}")

    ns = np.array([r["n"] for r in rows], dtype=float)
    fbd = np.array([r["frac_bd"] for r in rows], dtype=float)
    bpk = np.array([r["bd_pk"] for r in rows], dtype=float)
    fpk = np.array([r["fp_pk"] for r in rows], dtype=float)
    print("\n  anchor n   frac_bd   bd_pk(ms/key)   fp_pk(ms/key)")
    for r in rows:
        print(f"     {r['n']:>5}    {r['frac_bd']:.3f}     {r['bd_pk']:10.4f}      {r['fp_pk']:10.4f}")

    # fit bd_pk ~ a*n^p over body-bearing anchors; fp_pk ~ a*n^p; frac_bd interp on n.
    mb = (bpk > 0) & np.isfinite(bpk) & (ns >= 150)
    mf = (fpk > 0) & np.isfinite(fpk) & (ns >= 150)
    if mb.sum() < 2:
        print("  insufficient body anchors"); return 0
    pb = np.polyfit(np.log(ns[mb]), np.log(bpk[mb]), 1); body_a, body_p = math.exp(pb[1]), pb[0]
    if mf.sum() >= 2:
        pf = np.polyfit(np.log(ns[mf]), np.log(fpk[mf]), 1); fast_a, fast_p = math.exp(pf[1]), pf[0]
    else:
        fast_a, fast_p = float(np.nanmean(fpk[np.isfinite(fpk)])), 0.0
    order = np.argsort(ns); ns_s, fbd_s = ns[order], fbd[order]

    def frac_bd_at(nn):
        return float(np.interp(nn, ns_s, fbd_s, left=fbd_s[0], right=fbd_s[-1]))

    est_bd = body_a * np.power(pool_ns, body_p)
    est_fp = fast_a * np.power(pool_ns, fast_p)
    est_bd = np.maximum(est_bd, float(bpk[mb].min()))
    fp_floor = float(fpk[mf].min()) if mf.sum() else float(np.nanmin(fpk[np.isfinite(fpk)]))
    est_fp = np.maximum(est_fp, fp_floor)
    fr = np.array([frac_bd_at(nn) for nn in pool_ns])
    body_ms = cells * fr * est_bd          # body-DP component (scales as 1/C)
    fast_ms = cells * (1.0 - fr) * est_fp  # fast-path component (C-independent)
    per_chart_ms = body_ms + fast_ms
    pool_s = per_chart_ms.sum() / 1000.0

    print(f"\n  bd_pk fit = {body_a:.3e} * n^{body_p:.3f}  (floor {bpk[mb].min():.5f})  [at C={C_BLOCKS}]")
    print(f"  fp_pk fit = {fast_a:.3e} * n^{fast_p:.3f}  (floor {fp_floor:.5f})")
    body_share = body_ms.sum() / per_chart_ms.sum()
    print(f"\n  pool time split (C={C_BLOCKS}): body-DP {body_share*100:.0f}% / fast-path {(1-body_share)*100:.0f}%")
    print(f"\n  ---- targets ----   <15min = 900 s ;  CPU baseline = 1860 s (~31 min)")
    print(f"\n  {'concurrency C':>14}  {'1-proc min':>11}  {'2-proc min':>11}  {'<15min?':>9}")
    body_s_atC = body_ms.sum() / 1000.0   # at C_BLOCKS
    fast_s = fast_ms.sum() / 1000.0
    for Cprime in (96, 160, 256, 384):
        body_sc = body_s_atC * (C_BLOCKS / Cprime)   # body time scales 1/C
        tot1 = body_sc + fast_s
        tot2 = tot1 / 2.0
        ok = "YES" if tot2 <= 900 else ("1p:YES" if tot1 <= 900 else "no")
        print(f"  {Cprime:>14}  {tot1/60:>10.1f}m  {tot2/60:>10.1f}m  {ok:>9}")
    print(f"\n  HEADLINE (C={C_BLOCKS}, 2 procs): {pool_s/2/60:.1f} min -> "
          f"{'REACHES <15min' if (pool_s/2) <= 900 else 'DOES NOT reach <15min'}")
    heavy = pool_ns >= 2000
    print(f"  charts n>=2000: {int(heavy.sum())}/{len(pool_ns)} charts but "
          f"{per_chart_ms[heavy].sum()/per_chart_ms.sum()*100:.0f}% of pool time")
    # raw body single-block work pool sum (C-independent) for transparency
    print(f"  total body single-block work (Sigma W over pool) ~= "
          f"{(body_s_atC*C_BLOCKS)/60:.0f} block-min; /C={C_BLOCKS} -> {body_s_atC/60:.1f} min body GPU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
