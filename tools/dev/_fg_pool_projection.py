"""SATURATED full-pool projection for the PARALLEL-skyline block body DP.

The naive bench measured ms/key at small launch counts where large-n charts are
LATENCY-bound (few resident blocks, each running a long sequential backward DP) ->
a contaminated, pessimistic anchor. Here we measure SATURATED throughput properly:

  - per anchor n, build a LARGE representative uniform-grid batch (>= a few thousand
    keys) and run it through the parallel kernel split into the LARGEST TDR-safe
    sub-launch (auto-shrunk until no Vulkan device-lost), so the GPU stays full and
    the per-key cost = total_wall / n_keys INCLUDES the realistic chunking overhead.
  - report the single heaviest key's standalone backward-DP wall -> exposes the TDR
    ceiling (the residual heaviest-block-gates-the-launch divergence the mission
    flags for work-stealing).
  - fit saturated ms/key ~ a*n^p over body-bearing anchors and integrate over the
    REAL note-count histogram with the correct 25921 grid-cells/chart denominator
    (measured: the full 161x161 grid does NOT collapse -> every cell is a distinct
    geometry key), with a 2-GPU-process production factor.

Run: python tools/dev/_fg_pool_projection.py
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


par = _load("bbp_pp", "_fg_block_body_dp_parallel.py")
rgm = _load("rgv_pp", "_fg_real_grid_validate.py")
from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402


def _uniform_keys(step):
    R = TOTAL_ROWS
    return sorted({(ft, ff) for ft in range(0, R + 1, step) for ff in range(0, R + 1, step)})


def _time_batch(args, n, ts, great, nk, caps, reps=2):
    par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)  # warm
    ti.sync()
    best = math.inf
    for _ in range(reps):
        _, timing = par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
        best = min(best, timing["total_ms"])
    return best


def saturated_pk(label, n, path, ref_arrays):
    """Saturated ms/key on a representative uniform grid for chart `n`, with the
    largest TDR-safe sub-launch. Returns (ms/key, heaviest_single_key_ms, chunk)."""
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb, n2, pmn, pmx = rgm.axes_report(calc_song, ref_arrays, f"{label} {os.path.basename(path)[:24]}")
    assert n2 == n
    cb = max(64, pmx + 16)
    ccd = max(8192, (pmx + 4) * 256)
    caps = (cb, ccd)

    # representative grid: dense enough to be a fair mean + provide many blocks.
    step = 8 if n <= 1500 else (12 if n <= 3500 else 16)
    keys = _uniform_keys(step)
    args, ts, great = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
    nkeys = len(args)

    # find the largest TDR-safe sub-launch (chunk) by shrinking on device-lost.
    chunk = nkeys
    chunk_cap = {True: 192}.get(n <= 1500, None)
    if n > 1500:
        chunk = min(nkeys, 64 if n <= 3500 else (16 if n <= 5500 else 8))
    else:
        chunk = min(nkeys, 384)
    ms = math.inf
    while chunk >= 1:
        try:
            ms = _time_batch(args, n, ts, great, nk=chunk, caps=caps, reps=2)
            break
        except Exception as exc:
            msg = f"{type(exc).__name__}: {str(exc)[:80]}"
            print(f"    chunk={chunk} FAILED ({msg}); halving", flush=True)
            chunk //= 2
    pk = ms / nkeys if math.isfinite(ms) else float("nan")

    # heaviest single key (the worst low-ft/high-ff cell) standalone -> TDR headroom
    heavy_ms = float("nan")
    try:
        hk = [(0, TOTAL_ROWS)]
        hargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, hk)
        heavy_ms = _time_batch(hargs, n, ts, great, nk=1, caps=caps, reps=2)
    except Exception as exc:
        print(f"    heaviest-key timing FAILED: {type(exc).__name__}: {str(exc)[:60]}", flush=True)

    print(f"--- SATURATED [{label}] n={n} grid={nkeys} keys step={step} chunk={chunk} "
          f"pair_mod={pmn}..{pmx} ---")
    print(f"    saturated body-DP : {ms:9.1f} ms total  ({pk:8.5f} ms/key)")
    print(f"    heaviest key (0,{TOTAL_ROWS}) standalone : {heavy_ms:8.1f} ms   "
          f"(TDR watchdog ~2000ms -> {'OVER' if heavy_ms > 1800 else 'under'})", flush=True)
    return dict(label=label, n=n, nkeys=nkeys, pk=pk, heavy_ms=heavy_ms, chunk=chunk)


def main():
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    def nearest(t):
        return min(sc, key=lambda cp: abs(cp[0] - t))

    anchors = [("A60", *nearest(60)), ("A300", *nearest(300)), ("A653", *nearest(653)),
               ("A1083", *nearest(1083)), ("A1655", *nearest(1655)), ("A2312", *nearest(2312)),
               ("A3500", *nearest(3500)), ("A4722", *nearest(4722)), ("A6843", *nearest(6843)),
               ("A7027", *nearest(7027))]
    seen = set(); uanchors = []
    for lbl, c, p in anchors:
        if p in seen:
            continue
        seen.add(p); uanchors.append((lbl, c, p))

    rows = []
    for lbl, c, p in uanchors:
        try:
            rows.append(saturated_pk(lbl, c, p, ref_arrays))
        except Exception as exc:
            import traceback
            print(f"  ANCHOR {lbl} n={c} FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    print("\n\n========== SATURATED FULL-POOL PROJECTION ==========")
    keys_per_chart = (TOTAL_ROWS + 1) ** 2  # 25921 (measured: no grid collapse)
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    print(f"  pool charts={len(pool_ns)}  keys/chart={keys_per_chart}  total keys={len(pool_ns)*keys_per_chart/1e6:.1f}M")
    print(f"  pool n: min={pool_ns.min():.0f} median={np.median(pool_ns):.0f} "
          f"p90={np.percentile(pool_ns,90):.0f} p99={np.percentile(pool_ns,99):.0f} max={pool_ns.max():.0f}")

    ns = np.array([r["n"] for r in rows], dtype=float)
    pk = np.array([r["pk"] for r in rows], dtype=float)
    print(f"\n  anchor n -> saturated ms/key:")
    for r in rows:
        print(f"     n={r['n']:>5}  {r['pk']:8.5f} ms/key   heaviest_key={r['heavy_ms']:7.1f}ms  chunk={r['chunk']}")

    mask = (pk > 0) & np.isfinite(pk) & (ns >= 150)
    if mask.sum() >= 2:
        lp = np.polyfit(np.log(ns[mask]), np.log(pk[mask]), 1)
        p, a = lp[0], math.exp(lp[1])
        est = a * np.power(pool_ns, p)
        # n<150 charts: ~0 body states -> floor to the measured small-n overhead
        small = pk[(ns < 150) & np.isfinite(pk)]
        floor = float(small.min()) if small.size else float(pk[mask].min())
        est = np.maximum(est, floor)
        pool_s1 = (est * keys_per_chart).sum() / 1000.0
        print(f"\n  fit saturated ms/key = {a:.3e} * n^{p:.3f}  (floor {floor:.5f} ms/key for n<150)")
        print(f"    full-pool GPU (1 process)          : {pool_s1:9.1f} s = {pool_s1/60:6.2f} min")
        print(f"    full-pool GPU (2 production procs) : {pool_s1/2:9.1f} s = {pool_s1/2/60:6.2f} min")
        print(f"\n  ---- targets ----")
        print(f"    <15min target             :   900 s")
        print(f"    CPU Numba baseline (memo) :  1860 s  (~31 min)")
        reaches = (pool_s1 / 2) <= 900
        print(f"\n  HEADLINE: 2-proc saturated pool = {pool_s1/2/60:.1f} min  -> "
              f"{'REACHES <15min' if reaches else 'DOES NOT reach <15min'}")
    else:
        print("  insufficient finite anchors to fit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
