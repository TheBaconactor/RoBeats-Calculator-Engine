"""READ-ONLY full-pool FG response-frontier producer wall-clock estimator.

Goal: decide whether the CURRENT code can build the FG response first-frontier
grid for ALL ~2,238 charts in under 15 minutes (900s) under the production
topology.

What it does (no production code modified, no cache touched):
  1. Loads the all-chart note-count scan (tools/dev/_fg_real_grid_validate.scan_note_counts).
  2. Warms up Numba JIT once (one full-grid build, discarded).
  3. Measures W_32 = single-chart producer wall (generation + Pareto reduce) at
     32 reducer threads, for a STRATIFIED sample (~40) of charts spanning the
     distribution, with the heavy tail (largest note counts) sampled densely.
     Each sampled chart is measured `REPEATS` times (min taken) to reduce noise.
  4. Optionally measures W_16 on a few charts to sanity-check thread scaling
     (validates the topology amortization assumption W_16 ~= 2*W_32).
  5. Fits a monotone, superlinear-capable model W_32(note_count) by piecewise
     linear interpolation over the measured (note_count -> W_32) points (sorted),
     with a power-law tail extrapolation beyond the largest measured point.
  6. Sums the model over ALL charts -> full-pool producer-wall estimate ~= Sum W_32.
  7. Reports: full-pool estimate (s and min); per-stratum table; heavy-tail
     (top-20) contribution; total core-seconds vs the 32*900 = 28,800 bound; and
     the <900s verdict.

The producer does real work on every call (no per-call cache), so timing is
honest. Fails loudly on any error.

Run:  python -u tools/dev/_fg_fullpool_estimate.py
Env:  FG_EST_REPEATS (default 3), FG_EST_SAMPLE (default 40),
      FG_EST_SCALE_CHECK (default 1: measure W_16 on a few charts)
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# Reuse the validated dev harness for song loading + axes + scan.
_v = importlib.util.spec_from_file_location(
    "v", os.path.join(REPO, "tools", "dev", "_fg_real_grid_validate.py")
)
val = importlib.util.module_from_spec(_v)
_v.loader.exec_module(val)

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    build_force_greats_response_first_frontiers_gpu_batch,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (  # noqa: E402
    configure_force_greats_response_first_frontier_threads,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (  # noqa: E402
    _response_axes,
)

TOTAL_ROWS = 160
GRID = (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)  # 25,921 geometries / chart
CORES = int(os.cpu_count() or 1)
PROD_REDUCER_THREADS = CORES            # production sets reducer_threads = cpu_count
PROD_WORKERS = 2 if CORES >= 4 else 1   # production process-pool size
SCHED_BOUND_CORE_S = float(CORES) * 900.0  # 32 * 900 = 28,800 core-sec

REPEATS = int(os.environ.get("FG_EST_REPEATS", "3"))
SAMPLE = int(os.environ.get("FG_EST_SAMPLE", "40"))
SCALE_CHECK = int(os.environ.get("FG_EST_SCALE_CHECK", "1"))


def _chart_inputs(path, ref):
    """Return (n, ts, great, geoms, ufgt) for one chart's FULL 161x161 grid."""
    calc = val.load_song(path)
    si, rfbf, nfbf, rtbf = _response_axes(calc, ref)
    n = int(si.total_notes)
    ts = np.ascontiguousarray(np.asarray(si.timestamps, dtype=np.float32))
    great = np.ascontiguousarray(np.asarray(si.great_candidates, dtype=np.float32))
    ufgt = bool(si.use_forced_great_timing)
    geoms = tuple(
        (float(rfbf[ff]), int(nfbf[ff]), float(rtbf[ft]))
        for ft in range(TOTAL_ROWS + 1)
        for ff in range(TOTAL_ROWS + 1)
    )
    return n, ts, great, geoms, ufgt


def _time_producer(ts, great, geoms, ufgt, threads, repeats):
    """Measure producer wall at `threads` reducer threads. Min of `repeats`.

    Returns (best_seconds, total_rows). Fails loudly (no try/except)."""
    configure_force_greats_response_first_frontier_threads(int(threads))
    best = math.inf
    rows = 0
    for _ in range(int(repeats)):
        t = time.perf_counter()
        frontiers = build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=ts,
            great_candidate_timestamps=great,
            geometries=geoms,
            use_forced_great_timing=ufgt,
        )
        dt = time.perf_counter() - t
        if dt < best:
            best = dt
            # first_frontier is a SurfaceRowsFirstFrontier -> supports len()
            rows = sum(len(f.first_frontier) for f in frontiers if f is not None)
    if best <= 0 or not math.isfinite(best):
        raise RuntimeError(f"non-finite producer timing: {best}")
    return float(best), int(rows)


def _stratified_indices(counts, sample):
    """Pick `sample` chart indices spanning the note-count distribution, with
    the heavy tail densely sampled. counts is ascending-by-note-count."""
    nC = len(counts)
    idxs = set()
    # Always include the extremes.
    idxs.add(0)
    idxs.add(nC - 1)
    # Even quantile spread across the whole distribution (body).
    body = max(8, sample - 16)
    for q in np.linspace(0.0, 1.0, body):
        idxs.add(int(round(q * (nC - 1))))
    # Dense heavy-tail: the top of the distribution drives cost. Take the
    # largest ~14 charts individually (last 14 indices) plus a few near p95-p99.
    for j in range(1, 15):
        idxs.add(max(0, nC - j))
    for q in (0.90, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995):
        idxs.add(int(round(q * (nC - 1))))
    return sorted(idxs)


def _fit_predict(meas_n, meas_w, all_counts):
    """Monotone superlinear model.

    - For note_count within [min_measured, max_measured]: piecewise-linear
      interpolation over the (note_count -> W_32) measured points, after
      enforcing a monotone non-decreasing envelope on the sorted measurements
      (cost is monotone in note count; small inversions are noise).
    - Below min_measured: clamp to the smallest measured W (tiny charts; floor).
    - Above max_measured: power-law extrapolation fit to the top measured
      points (captures the steep superlinear tail) -> w = a * n**b.

    Returns predicted W_32 for every count in all_counts.
    """
    order = np.argsort(meas_n)
    xs = np.asarray(meas_n, dtype=np.float64)[order]
    ys = np.asarray(meas_w, dtype=np.float64)[order]
    # Collapse duplicate note counts to their max (worst case is the honest cost).
    ux, inv = np.unique(xs, return_inverse=True)
    uy = np.zeros_like(ux)
    for i in range(len(ux)):
        uy[i] = ys[inv == i].max()
    # Monotone non-decreasing envelope (running max) so interpolation never dips.
    uy = np.maximum.accumulate(uy)

    # Power-law tail fit on the upper portion (top ~40% of distinct points,
    # at least 4) in log-log space: log w = log a + b log n.
    k = max(4, int(round(0.4 * len(ux))))
    tx = np.log(ux[-k:])
    ty = np.log(np.maximum(uy[-k:], 1e-9))
    b, log_a = np.polyfit(tx, ty, 1)
    a = math.exp(log_a)
    b = max(1.0, float(b))  # tail must be at least linear

    xmin, xmax = float(ux[0]), float(ux[-1])
    out = np.empty(len(all_counts), dtype=np.float64)
    for i, c in enumerate(all_counts):
        cf = float(c)
        if cf <= xmin:
            out[i] = float(uy[0])
        elif cf >= xmax:
            # Blend: never below the last measured point; use power law beyond.
            out[i] = max(float(uy[-1]), a * cf ** b)
        else:
            out[i] = float(np.interp(cf, ux, uy))
    return out, (a, b, xmin, xmax)


def main():
    print(f"=== FG full-pool producer wall estimate ===", flush=True)
    print(f"cores={CORES} prod_workers={PROD_WORKERS} prod_reducer_threads={PROD_REDUCER_THREADS} "
          f"grid={GRID}/chart repeats={REPEATS} sample={SAMPLE}", flush=True)

    ref = val.build_ref_arrays()
    scan = val.scan_note_counts()
    counts = np.array([c for c, _ in scan], dtype=np.int64)
    paths = [p for _, p in scan]
    nC = len(scan)
    print(f"charts={nC} note_count min/median/p90/p99/max = "
          f"{int(counts.min())}/{int(np.median(counts))}/"
          f"{int(np.percentile(counts,90))}/{int(np.percentile(counts,99))}/{int(counts.max())}",
          flush=True)

    # --- Warmup JIT once (discard timing). Use a mid-size chart. ---
    warm_idx = nC // 2
    _, ts, great, geoms, ufgt = _chart_inputs(paths[warm_idx], ref)
    configure_force_greats_response_first_frontier_threads(PROD_REDUCER_THREADS)
    t = time.perf_counter()
    _ = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=ts, great_candidate_timestamps=great, geometries=geoms,
        use_forced_great_timing=ufgt,
    )
    print(f"warmup(JIT) n={int(counts[warm_idx])} discarded={time.perf_counter()-t:.2f}s", flush=True)

    # --- Stratified sample, measure W_32 ---
    sample_idx = _stratified_indices(counts, SAMPLE)
    print(f"\n--- measuring W_32 for {len(sample_idx)} stratified charts (threads={PROD_REDUCER_THREADS}) ---", flush=True)
    print(f"{'idx':>5} {'note_n':>7} {'W_32(s)':>9} {'rows':>9} {'song'}", flush=True)
    meas_n, meas_w = [], []
    scale_rows = []  # (n, w16, w32) for scaling sanity check
    for k, idx in enumerate(sample_idx):
        n, ts, great, geoms, ufgt = _chart_inputs(paths[idx], ref)
        w32, rows = _time_producer(ts, great, geoms, ufgt, PROD_REDUCER_THREADS, REPEATS)
        meas_n.append(n)
        meas_w.append(w32)
        print(f"{idx:>5} {n:>7} {w32:>9.3f} {rows:>9} {os.path.basename(paths[idx])}", flush=True)
        # Thread-scaling sanity check on a few of the heaviest charts.
        if SCALE_CHECK and CORES >= 16 and k % max(1, len(sample_idx) // 6) == 0:
            w16, _ = _time_producer(ts, great, geoms, ufgt, 16, max(1, REPEATS - 1))
            scale_rows.append((n, w16, w32))

    meas_n = np.array(meas_n, dtype=np.float64)
    meas_w = np.array(meas_w, dtype=np.float64)

    # --- Fit + predict over ALL charts ---
    pred, (a, b, xmin, xmax) = _fit_predict(meas_n, meas_w, counts)
    total_wall = float(pred.sum())                    # ~= Sum W_32 = full-pool wall
    total_core_s = total_wall * float(CORES)          # core-seconds consumed
    # Pure scheduling lower bound = total core-seconds / cores.
    lower_bound_wall = total_core_s / float(CORES)    # identically == total_wall here;
    # The meaningful lower bound is the *ideal* one: total work spread perfectly
    # over all cores. Per-chart W_32 already uses all cores within a chart, and 2
    # charts run concurrently. The ideal floor is sum(W_32 * effective_cores)/cores.
    # Under the model each chart consumes ~W_32*CORES core-seconds at full grid,
    # so ideal_floor = total_core_s / CORES = total_wall. We instead report the
    # *throughput* lower bound: if work could be packed with zero idle across all
    # CORES, wall >= total_core_s / CORES. (Equality with model here.)

    # --- Heavy-tail (top-20 by note count) contribution ---
    order = np.argsort(counts)
    top20_idx = order[-20:]
    top20_wall = float(pred[top20_idx].sum())

    # --- Per-stratum table (use measured points as the strata) ---
    print(f"\n--- model fit ---", flush=True)
    print(f"piecewise-linear monotone over [{xmin:.0f},{xmax:.0f}] notes; "
          f"power-law tail w = {a:.3e} * n^{b:.3f} beyond {xmax:.0f}", flush=True)

    if scale_rows:
        print(f"\n--- thread-scaling sanity (W_16 vs W_32; model assumes W_16 ~= 2*W_32) ---", flush=True)
        print(f"{'note_n':>7} {'W_16(s)':>9} {'W_32(s)':>9} {'W16/W32':>8} {'speedup_16->32':>14}", flush=True)
        ratios = []
        for n, w16, w32 in scale_rows:
            r = w16 / w32 if w32 > 0 else float('nan')
            ratios.append(r)
            print(f"{int(n):>7} {w16:>9.3f} {w32:>9.3f} {r:>8.2f} {'%.2fx' % r:>14}", flush=True)
        print(f"mean W16/W32 = {np.nanmean(ratios):.2f}  "
              f"(2.0 => ideal linear scaling 16->32; <2.0 => sublinear => model OPTIMISTIC)",
              flush=True)

    # --- Heavy-tail per-chart table (top 20) ---
    print(f"\n--- heavy tail: top-20 charts by note count (predicted W_32) ---", flush=True)
    print(f"{'note_n':>7} {'pred_W_32(s)':>13} {'song'}", flush=True)
    for i in reversed(top20_idx):
        print(f"{int(counts[i]):>7} {pred[i]:>13.3f} {os.path.basename(paths[i])}", flush=True)

    # --- Verdict ---
    print(f"\n================= RESULT =================", flush=True)
    print(f"FULL-POOL producer wall estimate (~= Sum W_32): {total_wall:8.1f} s  =  {total_wall/60.0:6.2f} min", flush=True)
    print(f"  under 15 min (900s)?  {'YES' if total_wall < 900.0 else 'NO'}"
          f"   (margin {900.0-total_wall:+.0f}s)", flush=True)
    print(f"heavy-tail top-20 charts contribute: {top20_wall:8.1f} s  ({100.0*top20_wall/total_wall:4.1f}% of total)", flush=True)
    print(f"\nTotal core-seconds (Sum W_32 * {CORES}): {total_core_s:9.0f} core-s", flush=True)
    print(f"  scheduling bound (={CORES} cores * 900s): {SCHED_BOUND_CORE_S:9.0f} core-s", flush=True)
    if total_core_s <= SCHED_BOUND_CORE_S:
        print(f"  -> total core-seconds <= bound: BETTER SCHEDULING ALONE COULD HIT 15min "
              f"(headroom {SCHED_BOUND_CORE_S-total_core_s:.0f} core-s)", flush=True)
    else:
        print(f"  -> total core-seconds EXCEEDS bound by {total_core_s-SCHED_BOUND_CORE_S:.0f} core-s: "
              f"STRUCTURAL per-chart reduction REQUIRED (no scheduling can fit 15min)", flush=True)
    # Throughput floor (perfect packing across all cores), reported explicitly.
    print(f"\npure throughput lower bound (total_core_s / {CORES} cores): {total_core_s/CORES:8.1f} s "
          f"= {total_core_s/CORES/60.0:.2f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
