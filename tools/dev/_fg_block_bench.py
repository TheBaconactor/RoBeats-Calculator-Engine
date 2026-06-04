"""BENCH (mission task #4): block-per-key vs thread-per-key body DP wall-time +
full-pool projection vs the 900s (<15min) target / 31-min CPU baseline.

Apples-to-apples: the THREAD-PER-KEY baseline is the main-kernel Phase-1
(`_fg_layer3_probe.run_kernel(max_phase=1)`) which uses the SAME per-state
algorithm (`_append_cand` + `_skyline_compact`) as the block kernel — the ONLY
difference is the parallelization granularity (1 thread/key vs 1 block/key), so
the speedup isolates the occupancy effect. Both produce the same body_tails;
both are bit-exact vs the Numba oracle (validated in _fg_block_body_dp.py).

We time the GPU kernel ONLY (no numba oracle in the timed path) over a real-grid
key set per chart, at a fixed launch size, repeated for stable medians. Heavy
low-ft/high-ff cells (the rho-up-to-183 cost) are over-represented.

Run: python tools/dev/_fg_block_bench.py
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

_BB = os.path.join(os.path.dirname(__file__), "_fg_block_body_dp.py")
_spec = importlib.util.spec_from_file_location("bb_bench", _BB)
bb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bb)
probe = bb.probe
fgp = bb.fgp

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402


def _thread_per_key_phase1_ms(args_list, n, ts, great_ts, chunk, reps):
    """Time the THREAD-PER-KEY main-kernel Phase-1 (body DP only) over args_list.
    Returns best (min) total ms over `reps` (warm)."""
    # warm once (compile)
    probe.run_kernel(args_list, n, ts, great_ts, chunk=chunk, max_phase=1, dump_bt=False)
    ti.sync()
    best = math.inf
    for _ in range(reps):
        t0 = time.perf_counter()
        probe.run_kernel(args_list, n, ts, great_ts, chunk=chunk, max_phase=1, dump_bt=False)
        ti.sync()
        best = min(best, (time.perf_counter() - t0) * 1000.0)
    return best


def _block_per_key_ms(args_list, n, ts, great_ts, nk, caps, reps):
    """Time the BLOCK-PER-KEY body DP over args_list. Returns best (min) total ms."""
    bb.run_block(args_list, n, ts, great_ts, n_keys_per_launch=nk, caps=caps)  # warm
    ti.sync()
    best = math.inf
    for _ in range(reps):
        _, timing = bb.run_block(args_list, n, ts, great_ts, n_keys_per_launch=nk, caps=caps)
        best = min(best, timing["total_ms"])
    return best


def _heavy_keys(big=False):
    """A real-grid key set biased toward heavy low-ft/high-ff cells, but spanning
    the grid so the per-key average reflects the true pool mix. For very large n
    we use a coarser set to stay TDR/time-tractable while keeping heavy cells."""
    R = TOTAL_ROWS
    keys = set()
    step_h = 8 if big else 4
    step_g = 32 if big else 16
    # heavy band: low ft, high ff (the rho-up-to-183 cost)
    for ft in range(0, 25, step_h):
        for ff in range(140, R + 1, step_h):
            keys.add((ft, ff))
    # spread over the grid so the mean is representative
    for ft in range(0, R + 1, step_g):
        for ff in range(0, R + 1, step_g):
            keys.add((ft, ff))
    return sorted(keys)


def bench_chart(label, n, path, rgm, ref_arrays, reps=3, launch=192):
    """Bench at a SATURATING launch size (`launch` keys/launch = `launch` blocks for
    the block kernel; `launch` lanes for the thread kernel). The 7900 XTX has ~96
    CUs so `launch` >= ~96-192 keeps the block grid filling the device. We keep the
    SAME launch size for both kernels so the comparison is apples-to-apples. For
    large n this is capped to stay TDR-safe (the per-launch wall is bounded by the
    heaviest key's still-serial skyline -> shrink launch as n grows)."""
    calc_song = rgm.load_song(path)
    si, rfb, nfb, rtb, n2, pmn, pmx = rgm.axes_report(calc_song, ref_arrays, f"{label} {os.path.basename(path)[:26]}")
    assert n2 == n
    keys = _heavy_keys(big=(n > 2500))
    # tile keys up to >= launch so a launch is full (repeat the heavy set; identical
    # keys just measure throughput, which is what saturation is about).
    while len(keys) < launch:
        keys = keys + keys
    keys = keys[:max(launch, 1)]
    args, ts, great = rgm.build_args_for_keys(si, rfb, nfb, rtb, keys)
    nkeys = len(args)
    cb = max(64, pmx + 16)
    ccd = max(8192, (pmx + 4) * 256)

    t_ms = _thread_per_key_phase1_ms(args, n, ts, great, chunk=launch, reps=reps)
    b_ms = _block_per_key_ms(args, n, ts, great, nk=launch, caps=(cb, ccd), reps=reps)

    per_key_t = t_ms / nkeys
    per_key_b = b_ms / nkeys
    speedup = t_ms / b_ms if b_ms > 0 else float("nan")
    print(f"\n--- BENCH [{label}] n={n} keys={nkeys} launch={launch} pair_mod={pmn}..{pmx} reps={reps} ---")
    print(f"  [HEAVY-CELL keys] thread-per-key P1 : {t_ms:8.1f} ms  ({per_key_t:7.4f} ms/key)")
    print(f"  [HEAVY-CELL keys] block-per-key     : {b_ms:8.1f} ms  ({per_key_b:7.4f} ms/key)")
    print(f"  SPEEDUP (thread/block)              : {speedup:5.2f}x")

    # REPRESENTATIVE average-per-key for the pool projection: a UNIFORM full-grid
    # sample (cheap + heavy mix, like the real 161x161 build) through the block
    # kernel only. Heavy-cell ms/key over-estimates the pool; this is the true mean.
    R = TOTAL_ROWS
    gstep = 8
    gkeys = sorted({(ft, ff) for ft in range(0, R + 1, gstep) for ff in range(0, R + 1, gstep)})
    gargs, _, _ = rgm.build_args_for_keys(si, rfb, nfb, rtb, gkeys)
    gb_ms = _block_per_key_ms(gargs, n, ts, great, nk=min(len(gargs), max(launch, 192)),
                              caps=(cb, ccd), reps=2)
    avg_pk_b = gb_ms / len(gargs)
    print(f"  [UNIFORM grid {len(gkeys)} keys] block avg : {gb_ms:8.1f} ms  ({avg_pk_b:7.4f} ms/key)  <- pool anchor")
    return dict(label=label, n=n, nkeys=nkeys, t_ms=t_ms, b_ms=b_ms,
                per_key_t=per_key_t, per_key_b=per_key_b, speedup=speedup,
                avg_pk_b=avg_pk_b)


def main():
    rg = importlib.util.spec_from_file_location("rgv_b", os.path.join(os.path.dirname(__file__), "_fg_real_grid_validate.py"))
    rgm = importlib.util.module_from_spec(rg)
    rg.loader.exec_module(rgm)
    ref_arrays = rgm.build_ref_arrays()
    sc = rgm.scan_note_counts()

    # Bench charts where a SATURATING launch is TDR-feasible (the absolute-max
    # n=7027 chart is excluded from the timed bench: at TDR-safe launch sizes it
    # starves BOTH kernels and is unrepresentative; it is validated bit-exact
    # separately). Anchor the projection on small / median / p90.
    mididx = len(sc) // 2
    p90idx = int(len(sc) * 0.90)
    charts = [
        ("SMALL", sc[next(i for i, (c, _) in enumerate(sc) if c >= 8)][0],
         sc[next(i for i, (c, _) in enumerate(sc) if c >= 8)][1], 256),
        ("MEDIAN", sc[mididx][0], sc[mididx][1], 192),
        ("P90", sc[p90idx][0], sc[p90idx][1], 96),
    ]

    rows = []
    for lbl, c, p, launch in charts:
        try:
            rows.append(bench_chart(lbl, c, p, rgm, ref_arrays, reps=3, launch=launch))
        except Exception as exc:
            import traceback
            print(f"  BENCH {lbl} n={c} FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    # ---- full-pool projection ----
    # The body DP per key scales ~ n*L*rho; the per-key ms at the sampled n's lets
    # us fit per-key cost vs n and integrate over the real note-count histogram
    # (25,921 keys per chart = 161*161 ft/ff grid, all built per chart).
    print("\n\n========== FULL-POOL PROJECTION ==========")
    keys_per_chart = (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)
    ns = np.array([r["n"] for r in rows], dtype=float)
    # pool projection uses the REPRESENTATIVE uniform-grid avg ms/key (not heavy-cell).
    bpk = np.array([r["avg_pk_b"] for r in rows], dtype=float)  # avg ms/key block
    tpk = np.array([r["per_key_t"] for r in rows], dtype=float)  # heavy ms/key thread (ref only)
    print(f"  sampled n -> AVG ms/key block (uniform grid): {[ (int(n), round(v,4)) for n,v in zip(ns,bpk) ]}")

    # full note-count histogram of the pool
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    print(f"  pool charts={len(pool_ns)} n: min={pool_ns.min():.0f} median={np.median(pool_ns):.0f} "
          f"p90={np.percentile(pool_ns,90):.0f} max={pool_ns.max():.0f}")

    # Fit ms/key ~ a*n^p (log-log least squares). EXCLUDE n<150 anchors: charts
    # with n<100 have ZERO body states (the body DP loop is empty) so their per-key
    # time is pure reachability/overhead and would corrupt the body-DP scaling fit.
    fit_mask_n = ns >= 150

    def fit_and_project(per_key_ms, name):
        mask = (per_key_ms > 0) & fit_mask_n
        if mask.sum() < 2:
            print(f"\n  [{name}] insufficient body-bearing anchors to fit")
            return float("nan")
        lp = np.polyfit(np.log(ns[mask]), np.log(per_key_ms[mask]), 1)
        p, a = lp[0], math.exp(lp[1])
        est_per_key = a * np.power(pool_ns, p)  # ms/key for every real chart
        chart_ms = est_per_key * keys_per_chart
        pool_ms = chart_ms.sum()
        pool_s = pool_ms / 1000.0
        print(f"\n  [{name}] fit ms/key = {a:.3e} * n^{p:.3f}")
        print(f"    full-pool GPU (1 process, serial launches): {pool_s:9.1f} s  = {pool_s/60:6.2f} min")
        return pool_s
    pool_block = fit_and_project(bpk, "BLOCK-PER-KEY")
    pool_thread = fit_and_project(tpk, "THREAD-PER-KEY")
    print(f"\n  ---- targets ----")
    print(f"    <15min target            :   900 s")
    print(f"    CPU Numba baseline (memo) :  1860 s  (~31 min)")
    print(f"    block/thread pool ratio   : {pool_thread/pool_block:5.2f}x")
    print("\n  NOTE: single-process serial-launch projection. Production runs 2 GPU")
    print("  procs; overlapping host prep with GPU + larger resident batches give")
    print("  additional headroom not modeled here. Projection is conservative.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
