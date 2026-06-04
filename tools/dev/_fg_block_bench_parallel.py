"""BENCH: thread-per-key vs SERIAL-block vs PARALLEL-block (scatter-max skyline)
body-DP wall-time + SATURATED full-pool projection vs the 900s (<15min) target.

All three produce the same body_tails (all bit-exact vs the Numba oracle):
  thread  = `_fg_layer3_probe.run_kernel(max_phase=1)`  (1 thread / key)
  serial  = `_fg_block_body_dp.run_block`                (1 block/key, thread-0 sort)
  paral   = `_fg_block_body_dp_parallel.run_block_par`   (1 block/key, scatter-max)
so the comparison isolates the skyline-parallelization win at fixed granularity.

We time the GPU kernel ONLY (no oracle in the timed path), best-of-`reps` (warm),
over a real-grid heavy-cell key set per chart at a SATURATING launch size (>= the
device CU count so the block grid fills the 7900 XTX). A separate UNIFORM full-grid
sample gives the representative mean ms/key for the pool projection (heavy-cell
ms/key over-estimates the pool). The projection fits ms/key ~ a*n^p over the
body-bearing anchors and integrates over the real note-count histogram, with a
SATURATION/overlap factor for the 2-GPU-process production reality.

Run: python tools/dev/_fg_block_bench_parallel.py
     python tools/dev/_fg_block_bench_parallel.py --quick   (skip serial-block)
"""
import argparse
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


par = _load("bbp_bench", "_fg_block_body_dp_parallel.py")
ser = _load("bbs_bench", "_fg_block_body_dp.py")
probe = par.probe
fgp = par.fgp
rgm = _load("rgv_pb", "_fg_real_grid_validate.py")

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402


def _best_ms(fn, reps):
    fn()  # warm (compile)
    ti.sync()
    best = math.inf
    for _ in range(reps):
        t0 = time.perf_counter()
        r = fn()
        ti.sync()
        best = min(best, (time.perf_counter() - t0) * 1000.0)
    return best


def _thread_ms(args, n, ts, great, chunk, reps):
    return _best_ms(lambda: probe.run_kernel(args, n, ts, great, chunk=chunk, max_phase=1, dump_bt=False), reps)


def _serial_block_ms(args, n, ts, great, nk, caps, reps):
    def go():
        ser.run_block(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
    return _best_ms(go, reps)


def _parallel_block_ms(args, n, ts, great, nk, caps, reps):
    def go():
        par.run_block_par(args, n, ts, great, n_keys_per_launch=nk, caps=caps)
    return _best_ms(go, reps)


def _heavy_keys(big=False):
    R = TOTAL_ROWS
    keys = set()
    step_h = 8 if big else 4
    step_g = 32 if big else 16
    for ft in range(0, 25, step_h):
        for ff in range(140, R + 1, step_h):
            keys.add((ft, ff))
    for ft in range(0, R + 1, step_g):
        for ff in range(0, R + 1, step_g):
            keys.add((ft, ff))
    return sorted(keys)


def bench_chart(label, n, path, ref_arrays, reps=3, launch=192, do_serial=True):
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb, n2, pmn, pmx = rgm.axes_report(calc_song, ref_arrays, f"{label} {os.path.basename(path)[:26]}")
    assert n2 == n
    keys = _heavy_keys(big=(n > 2500))
    while len(keys) < launch:
        keys = keys + keys
    keys = keys[:max(launch, 1)]
    args, ts, great = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
    nkeys = len(args)
    cb = max(64, pmx + 16)
    ccd = max(8192, (pmx + 4) * 256)

    t_ms = _thread_ms(args, n, ts, great, chunk=launch, reps=reps)
    p_ms = _parallel_block_ms(args, n, ts, great, nk=launch, caps=(cb, ccd), reps=reps)
    s_ms = _serial_block_ms(args, n, ts, great, nk=launch, caps=(cb, ccd), reps=reps) if do_serial else float("nan")

    pk_t = t_ms / nkeys
    pk_p = p_ms / nkeys
    pk_s = s_ms / nkeys
    sp_par = t_ms / p_ms if p_ms > 0 else float("nan")
    sp_ser = t_ms / s_ms if (do_serial and s_ms > 0) else float("nan")
    sp_par_vs_ser = s_ms / p_ms if (do_serial and p_ms > 0) else float("nan")
    print(f"\n--- BENCH [{label}] n={n} keys={nkeys} launch={launch} pair_mod={pmn}..{pmx} reps={reps} ---")
    print(f"  [HEAVY keys] thread-per-key  : {t_ms:9.1f} ms  ({pk_t:8.4f} ms/key)")
    if do_serial:
        print(f"  [HEAVY keys] SERIAL-block    : {s_ms:9.1f} ms  ({pk_s:8.4f} ms/key)   {sp_ser:5.2f}x vs thread")
    print(f"  [HEAVY keys] PARALLEL-block  : {p_ms:9.1f} ms  ({pk_p:8.4f} ms/key)   {sp_par:5.2f}x vs thread"
          + (f"   {sp_par_vs_ser:5.2f}x vs serial-block" if do_serial else ""))

    # representative UNIFORM full-grid mean ms/key (pool anchor) via the PARALLEL kernel
    R = TOTAL_ROWS
    gstep = 8
    gkeys = sorted({(ft, ff) for ft in range(0, R + 1, gstep) for ff in range(0, R + 1, gstep)})
    gargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, gkeys)
    gnk = min(len(gargs), max(launch, 192))
    gp_ms = _parallel_block_ms(gargs, n, ts, great, nk=gnk, caps=(cb, ccd), reps=2)
    avg_pk_p = gp_ms / len(gargs)
    print(f"  [UNIFORM grid {len(gkeys)} keys] PAR avg : {gp_ms:9.1f} ms  ({avg_pk_p:8.4f} ms/key)  <- pool anchor")
    return dict(label=label, n=n, nkeys=nkeys, t_ms=t_ms, s_ms=s_ms, p_ms=p_ms,
                pk_t=pk_t, pk_s=pk_s, pk_p=pk_p, sp_par=sp_par, sp_ser=sp_ser,
                avg_pk_p=avg_pk_p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the serial-block timing")
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()
    mididx = len(sc) // 2
    p90idx = int(len(sc) * 0.90)

    def nearest(target):
        c, p = min(sc, key=lambda cp: abs(cp[0] - target))
        return c, p

    # small / median / p90 / heavy tail. Larger n -> smaller TDR-safe launch.
    # n=7027 EXCLUDED from the TIMED bench: at any launch its single heaviest
    # low-ft/high-ff key's backward DP exceeds the ~2s Vulkan TDR watchdog (device
    # lost) -- that residual is the work-stealing/per-key-chunk closing lever, and
    # it is validated bit-exact separately. The heavy tail is anchored by n=4722.
    charts = [
        ("SMALL", *(lambda c, p: (c, p, 256))(*nearest(60))),
        ("MEDIAN", sc[mididx][0], sc[mididx][1], 192),
        ("P90", sc[p90idx][0], sc[p90idx][1], 96),
        ("HEAVY~2312", *(lambda c, p: (c, p, 96))(*nearest(2312))),
        ("HEAVY~4722", *(lambda c, p: (c, p, 48))(*nearest(4722))),
    ]
    # de-dup by path keeping first label
    seen = set(); ucharts = []
    for lbl, c, p, L in charts:
        if p in seen:
            continue
        seen.add(p); ucharts.append((lbl, c, p, L))

    rows = []
    for lbl, c, p, launch in ucharts:
        try:
            rows.append(bench_chart(lbl, c, p, ref_arrays, reps=args.reps, launch=launch, do_serial=not args.quick))
        except Exception as exc:
            import traceback
            print(f"  BENCH {lbl} n={c} FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    # ---------------- full-pool projection ----------------
    print("\n\n========== FULL-POOL PROJECTION ==========")
    keys_per_chart = (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)  # 161*161 = 25921
    ns = np.array([r["n"] for r in rows], dtype=float)
    bpk = np.array([r["avg_pk_p"] for r in rows], dtype=float)  # parallel avg ms/key (uniform grid)
    print(f"  sampled n -> PAR avg ms/key (uniform grid): {[(int(x), round(v, 4)) for x, v in zip(ns, bpk)]}")

    pool_ns = np.array([c for c, _ in sc], dtype=float)
    print(f"  pool charts={len(pool_ns)} n: min={pool_ns.min():.0f} median={np.median(pool_ns):.0f} "
          f"p90={np.percentile(pool_ns, 90):.0f} p99={np.percentile(pool_ns, 99):.0f} max={pool_ns.max():.0f}")

    fit_mask = ns >= 150  # n<150 charts have ~0 body states (empty body DP); exclude from the scaling fit

    def project(per_key_ms, name, sat=1.0):
        mask = (per_key_ms > 0) & fit_mask
        if mask.sum() < 2:
            print(f"  [{name}] insufficient anchors")
            return float("nan")
        lp = np.polyfit(np.log(ns[mask]), np.log(per_key_ms[mask]), 1)
        p, a = lp[0], math.exp(lp[1])
        est = a * np.power(pool_ns, p)
        pool_s = (est * keys_per_chart).sum() / 1000.0
        print(f"\n  [{name}] fit ms/key = {a:.3e} * n^{p:.3f}")
        print(f"    full-pool GPU (1 proc, serial launches)      : {pool_s:9.1f} s = {pool_s / 60:6.2f} min")
        print(f"    full-pool GPU (sat/overlap factor {sat:.2f})        : {pool_s * sat:9.1f} s = {pool_s * sat / 60:6.2f} min")
        return pool_s

    # sat factor: 2 production GPU procs + host/GPU overlap + bigger resident batches.
    # Conservative: model only the 2-proc split (0.5) as the realized headroom.
    pool_block = project(bpk, "PARALLEL-BLOCK", sat=0.5)
    print(f"\n  ---- targets ----")
    print(f"    <15min target             :   900 s")
    print(f"    CPU Numba baseline (memo) :  1860 s  (~31 min)")
    print(f"\n  NOTE: uniform-grid mean drives the projection; heavy-cell ms/key is the")
    print(f"  worst-case per-key, not the pool mean. ~30-50% of geometries early-out")
    print(f"  (fast path / no body DP) and cost ~0 body time, already in the mean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
