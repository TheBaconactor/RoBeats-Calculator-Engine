"""DECISIVE OCCUPANCY PROBE: with a PERSISTENT-KERNEL WORK-STEALING design and
MINIMAL per-block memory, what is the maximum resident-workgroup concurrency C_max
on the RX 7900 XTX, and does it reach ~950 (=> <15min PLAUSIBLE for the FG frontier
full-pool build) or cap well below (=> physically out of reach on this hardware)?

THE QUESTION (mission): the validated bit-exact BLOCK-PER-KEY body-DP kernel
(`_fg_block_body_dp_parallel.py`) runs at a MEASURED resident concurrency C~=160.
Full-pool projection at C=160 is ~106min (~7x over the 900s target). To hit <15min
you need C~=950-1130. C~160 was capped by (a) per-block memory and (b) the Vulkan
TDR watchdog forcing tiny launches (the heaviest single-block cells take 2.7-7.1s,
over ~2s). A persistent kernel with a FIXED grid of G workgroups + work-stealing
removes the per-launch heaviest-cell gating (finished blocks grab the next key), so
the OCCUPANCY ceiling can be measured directly -- independent of the TDR-heavy-cell
issue -- by saturating a UNIFORM synthetic workload and watching aggregate throughput
plateau. The plateau / per-block throughput = C_max.

DESIGN (mission tasks 2,3):
  * A persistent kernel launches a FIXED grid of G workgroups (BD=64 = 1 AMD
    wavefront each). Each workgroup loops: grab the next unprocessed unit via a
    single global `ti.atomic_add(work_counter, 1)`; if >= total_units, exit; else
    run one UNIT of a SYNTHETIC, UNIFORM body-DP-like workload; repeat.
  * The synthetic unit is a fixed-iteration arithmetic+shared-memory loop sized so
    one unit ~= a light real body-DP cell (sub-TDR, uniform => isolates OCCUPANCY
    from heavy-cell divergence). All G workgroups do identical-cost units, so the
    persistent grid stays fully busy until the counter drains.
  * THROUGHPUT-SATURATION method: fix a large total_units U; sweep G; measure wall
    T(G). Aggregate throughput thru(G) = U / T(G) RISES with G until all CUs are
    saturated, then PLATEAUS. C_max = the G at the plateau knee (equivalently the
    plateau throughput / single-block throughput). We also report T(G), units/ms,
    and the per-G speedup vs G=ngroups_min.
  * PER-BLOCK MEMORY SWEEP (mission task 1+3): the synthetic kernel takes a
    per-block GLOBAL scratch buffer sized SCRATCH_I32 int32 per workgroup AND a
    per-block SHARED-MEMORY array sized SHARED_I32 int32. Sweeping these two knobs
    maps the OCCUPANCY-vs-memory curve: shared memory + register/scratch pressure
    is what caps resident wavefronts per CU. We report C_max at several
    (shared, scratch) footprints, including the MINIMIZED footprint and the
    CURRENT block-kernel footprint (measured separately in
    `_fg_persistent_worksteal.py`).

Read-only on production. Run: python tools/dev/_fg_persistent_occupancy.py
"""
import argparse
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

BD = 64  # threads per workgroup = 1 AMD wavefront

# Number of GPU device hardware threads (CUs * SIMDs * lanes is the nameplate; the
# 7900 XTX is 96 CUs). The plateau is EMPIRICAL, not nameplate.
N_CU = 96


# --------------------------------------------------------------------------- #
# PERSISTENT WORK-STEALING SYNTHETIC KERNEL.
# Fixed grid of G*BD threads (G workgroups). Each workgroup repeatedly claims a
# unit via one global atomic_add and runs `unit_iters` of a uniform body-DP-like
# arithmetic loop touching its per-block shared array + per-block global scratch.
# This isolates the OCCUPANCY ceiling: all units are identical cost (no heavy-cell
# divergence), sub-TDR, and the persistent grid auto-balances (finished blocks grab
# the next unit) so the device stays saturated until the counter drains.
# --------------------------------------------------------------------------- #
@ti.kernel
def persistent_uniform(
    n_groups: ti.i32,
    total_units: ti.i32,
    unit_iters: ti.i32,
    shared_i32: ti.i32,        # per-block SHARED-memory int32 count (occupancy knob)
    scratch_i32: ti.i32,       # per-block GLOBAL scratch int32 count (occupancy knob)
    work_counter: ti.types.ndarray(dtype=ti.i32, ndim=1),   # [1] global claim counter
    scratch: ti.types.ndarray(dtype=ti.i32, ndim=2),        # [n_groups, scratch_cap]
    out_acc: ti.types.ndarray(dtype=ti.i64, ndim=1),        # [n_groups] sink (anti-DCE)
    units_done: ti.types.ndarray(dtype=ti.i32, ndim=1),     # [n_groups] units this block ran
    SHARED_CAP: ti.template(),
):
    ti.loop_config(block_dim=BD)
    for gid in range(n_groups * BD):
        block = gid // BD
        t = ti.simt.block.thread_idx()
        sh = ti.simt.block.SharedArray((SHARED_CAP,), ti.i32)
        # block-local claim mailbox in shared mem slot 0 (reuse SHARED_CAP[0]).
        local_done = ti.i32(0)
        acc = ti.i64(0)

        keep_going = True
        while keep_going:
            # ---- claim one unit cooperatively: thread 0 does the atomic, broadcasts ----
            if t == 0:
                sh[0] = ti.atomic_add(work_counter[0], 1)
            ti.simt.block.sync()
            unit = sh[0]
            ti.simt.block.sync()
            if unit >= total_units:
                keep_going = False
            else:
                local_done += 1
                # ---- run ONE uniform unit: BD threads cooperate over a body-DP-like
                #      loop. Touch shared mem (sized shared_i32) + global scratch
                #      (sized scratch_i32) to load the occupancy knobs. ----
                # init the used portion of shared mem (cooperative).
                j = t
                while j < shared_i32:
                    sh[j] = (unit * 1103 + j * 7919) & 0x7fffffff
                    j += BD
                ti.simt.block.sync()
                # init the used portion of global scratch (cooperative).
                j = t
                while j < scratch_i32:
                    scratch[block, j] = (unit + j * 40503) & 0x7fffffff
                    j += BD
                ti.simt.block.sync()
                # the uniform compute body: each thread does `unit_iters` mixed
                # ALU ops reading/writing shared + scratch (a stand-in for the
                # per-state skyline arithmetic; uniform cost => occupancy probe).
                v = ti.i32(unit * 7 + t)
                it = 0
                while it < unit_iters:
                    si = (v & 0x7fffffff) % shared_i32 if shared_i32 > 0 else 0
                    sc = (v >> 3) & 0x7fffffff
                    sci = sc % scratch_i32 if scratch_i32 > 0 else 0
                    a = sh[si] if shared_i32 > 0 else v
                    b = scratch[block, sci] if scratch_i32 > 0 else v
                    v = (a * 8121 + b * 28411 + 12345) & 0x7fffffff
                    if shared_i32 > 0:
                        ti.atomic_max(sh[si], v)
                    if scratch_i32 > 0:
                        scratch[block, sci] = (scratch[block, sci] + v) & 0x7fffffff
                    acc += ti.i64(v)
                    it += 1
                ti.simt.block.sync()
        if t == 0:
            out_acc[block] = acc
            units_done[block] = local_done


# --------------------------------------------------------------------------- #
# NO-STEAL REPLICATION CROSS-CHECK KERNEL. Identical per-unit body, but each block
# does EXACTLY `units_per_block` units with NO global atomic (the unit id = block-
# local counter offset by block). This isolates the PURE occupancy ceiling from any
# atomic-counter contention in the work-stealing variant: if both give the same
# C_max, the contention is not the limiter (the occupancy ceiling is real); if the
# work-stealing C_max is lower, the atomic is a bottleneck (fixable with a batched/
# hierarchical claim). Same flat-then-waves signature => same C_max method.
# --------------------------------------------------------------------------- #
@ti.kernel
def replicate_uniform(
    n_groups: ti.i32,
    units_per_block: ti.i32,
    unit_iters: ti.i32,
    shared_i32: ti.i32,
    scratch_i32: ti.i32,
    scratch: ti.types.ndarray(dtype=ti.i32, ndim=2),
    out_acc: ti.types.ndarray(dtype=ti.i64, ndim=1),
    SHARED_CAP: ti.template(),
):
    ti.loop_config(block_dim=BD)
    for gid in range(n_groups * BD):
        block = gid // BD
        t = ti.simt.block.thread_idx()
        sh = ti.simt.block.SharedArray((SHARED_CAP,), ti.i32)
        acc = ti.i64(0)
        u = 0
        while u < units_per_block:
            unit = block * units_per_block + u  # unique-per-block id (no atomic)
            j = t
            while j < shared_i32:
                sh[j] = (unit * 1103 + j * 7919) & 0x7fffffff
                j += BD
            ti.simt.block.sync()
            j = t
            while j < scratch_i32:
                scratch[block, j] = (unit + j * 40503) & 0x7fffffff
                j += BD
            ti.simt.block.sync()
            v = ti.i32(unit * 7 + t)
            it = 0
            while it < unit_iters:
                si = (v & 0x7fffffff) % shared_i32 if shared_i32 > 0 else 0
                sc = (v >> 3) & 0x7fffffff
                sci = sc % scratch_i32 if scratch_i32 > 0 else 0
                a = sh[si] if shared_i32 > 0 else v
                b = scratch[block, sci] if scratch_i32 > 0 else v
                v = (a * 8121 + b * 28411 + 12345) & 0x7fffffff
                if shared_i32 > 0:
                    ti.atomic_max(sh[si], v)
                if scratch_i32 > 0:
                    scratch[block, sci] = (scratch[block, sci] + v) & 0x7fffffff
                acc += ti.i64(v)
                it += 1
            ti.simt.block.sync()
            u += 1
        if t == 0:
            out_acc[block] = acc


# --------------------------------------------------------------------------- #
# SPARSE-ACCESS work-stealing kernel (THE DECISIVE DISAMBIGUATION). Decouples the
# RESERVED per-block global footprint (alloc_i32 -> bounds total resident lanes via
# the SSBO/VRAM budget, NOT per-CU occupancy) from the HOT working set actually
# touched per unit (hot_i32 -> drives memory bandwidth + cache pressure). The REAL
# block kernel reserves a large per-block CSR body_tails store (hundreds of KB) but
# touches only ~rho rows per state => its access is SPARSE. If a large alloc with a
# SMALL hot window still reaches the occupancy ceiling, then the real minimized kernel
# is occupancy-bound (not bandwidth-bound) and the pessimistic dense-scratch curve
# under-counts its C. Each unit: init only the hot window, then unit_iters ALU ops
# over the hot window (offset into the large alloc by a per-unit base, to exercise the
# footprint's address range without streaming all of it).
# --------------------------------------------------------------------------- #
@ti.kernel
def persistent_sparse(
    n_groups: ti.i32,
    total_units: ti.i32,
    unit_iters: ti.i32,
    hot_i32: ti.i32,           # bytes ACTUALLY touched per unit (bandwidth knob)
    alloc_i32: ti.i32,         # per-block RESERVED footprint (VRAM/SSBO knob)
    work_counter: ti.types.ndarray(dtype=ti.i32, ndim=1),
    scratch: ti.types.ndarray(dtype=ti.i32, ndim=2),   # [n_groups, alloc_cap]
    out_acc: ti.types.ndarray(dtype=ti.i64, ndim=1),
    units_done: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    ti.loop_config(block_dim=BD)
    for gid in range(n_groups * BD):
        block = gid // BD
        t = ti.simt.block.thread_idx()
        sh = ti.simt.block.SharedArray((4,), ti.i32)   # tiny shared (like the real kernel)
        local_done = ti.i32(0)
        acc = ti.i64(0)
        keep_going = True
        while keep_going:
            if t == 0:
                sh[0] = ti.atomic_add(work_counter[0], 1)
            ti.simt.block.sync()
            unit = sh[0]
            ti.simt.block.sync()
            if unit >= total_units:
                keep_going = False
            else:
                local_done += 1
                # hot window base WANDERS over the large alloc (sparse touch of the
                # reserved footprint), wrapped so base+hot stays in-bounds.
                span = alloc_i32 - hot_i32
                base = (unit * 131) % (span + 1) if span > 0 else 0
                j = t
                while j < hot_i32:
                    scratch[block, base + j] = (unit + j * 40503) & 0x7fffffff
                    j += BD
                ti.simt.block.sync()
                v = ti.i32(unit * 7 + t)
                it = 0
                while it < unit_iters:
                    idx = base + ((v & 0x7fffffff) % hot_i32 if hot_i32 > 0 else 0)
                    b = scratch[block, idx] if hot_i32 > 0 else v
                    v = (b * 28411 + 12345) & 0x7fffffff
                    if hot_i32 > 0:
                        scratch[block, idx] = (scratch[block, idx] + v) & 0x7fffffff
                    acc += ti.i64(v)
                    it += 1
                ti.simt.block.sync()
        if t == 0:
            out_acc[block] = acc
            units_done[block] = local_done


def _time_sparse(n_groups, units_per_block, unit_iters, hot_i32, alloc_i32, reps=5):
    total_units = n_groups * units_per_block
    work_counter = np.zeros(1, dtype=np.int32)
    scratch = np.zeros((n_groups, max(1, alloc_i32)), dtype=np.int32)
    out_acc = np.zeros(n_groups, dtype=np.int64)
    units_done = np.zeros(n_groups, dtype=np.int32)

    def _launch():
        work_counter[0] = 0
        persistent_sparse(n_groups, total_units, unit_iters, hot_i32, alloc_i32,
                          work_counter, scratch, out_acc, units_done)
    _launch(); ti.sync()
    samples = []
    for _ in range(reps):
        out_acc[:] = 0; units_done[:] = 0
        t0 = time.perf_counter(); _launch(); ti.sync()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return float(np.median(samples)), float(np.min(samples))


def sweep_sparse(label, hot_i32, alloc_i32, unit_iters, units_per_block, Gs):
    """Same flat-then-waves C_max method, for the sparse-access kernel."""
    print(f"\n=== SPARSE [{label}] hot={hot_i32}i32({hot_i32*4}B) "
          f"alloc={alloc_i32}i32({alloc_i32*4}B/blk) unit_iters={unit_iters} "
          f"units/block={units_per_block} ===")
    print(f"  {'G(blocks)':>10}  {'Tmed ms':>9}  {'T/T(G0)':>8}  {'units/ms':>9}  "
          f"{'impliedC':>9}")
    rows = []; peak_thru = 0.0; T0 = None
    for G in Gs:
        total_units = G * units_per_block
        try:
            Tmed, Tmin = _time_sparse(G, units_per_block, unit_iters, hot_i32, alloc_i32)
        except Exception as exc:
            print(f"  {G:>10}  FAILED ({type(exc).__name__}: {str(exc)[:48]})")
            break
        if T0 is None:
            T0 = Tmed
        thru = total_units / Tmed
        peak_thru = max(peak_thru, thru)
        ratio = Tmed / T0
        impliedC = G / ratio if ratio > 0 else float("nan")
        rows.append((G, Tmed, ratio, thru, impliedC))
        print(f"  {G:>10}  {Tmed:>9.2f}  {ratio:>8.2f}  {thru:>9.2f}  {impliedC:>9.1f}")
    if not rows:
        return None
    small = [r for r in rows if r[0] <= 96]
    per_block_thru = max((r[3] / r[0]) for r in small) if small else rows[0][3] / rows[0][0]
    c_max = peak_thru / per_block_thru if per_block_thru > 0 else float("nan")
    c_max_impl = max(r[4] for r in rows)
    print(f"  -> C_max(plateau) ~= {c_max:.0f} ; C_max(impliedC) ~= {c_max_impl:.0f}")
    return dict(label=label, hot_i32=hot_i32, alloc_i32=alloc_i32,
                c_max=c_max, c_max_impl=c_max_impl, peak_thru=peak_thru)


def _time_persistent(n_groups, units_per_block, unit_iters, shared_i32, scratch_i32,
                     shared_cap, scratch_cap, reps=5, mode="steal"):
    """Return (median_ms, min_ms, units_done). mode: 'steal' = work-stealing global
    atomic; 'replicate' = no-atomic fixed-per-block (pure-occupancy cross-check)."""
    total_units = n_groups * units_per_block
    work_counter = np.zeros(1, dtype=np.int32)
    scratch = np.zeros((n_groups, max(1, scratch_cap)), dtype=np.int32)
    out_acc = np.zeros(n_groups, dtype=np.int64)
    units_done = np.zeros(n_groups, dtype=np.int32)

    def _launch():
        if mode == "steal":
            work_counter[0] = 0
            persistent_uniform(n_groups, total_units, unit_iters, shared_i32, scratch_i32,
                               work_counter, scratch, out_acc, units_done, shared_cap)
        else:
            replicate_uniform(n_groups, units_per_block, unit_iters, shared_i32,
                              scratch_i32, scratch, out_acc, shared_cap)
    _launch(); ti.sync()  # warm (compile + first upload)
    samples = []
    for _ in range(reps):
        out_acc[:] = 0
        if mode == "steal":
            units_done[:] = 0
        t0 = time.perf_counter()
        _launch()
        ti.sync()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return float(np.median(samples)), float(np.min(samples)), units_done.copy()


def sweep_occupancy(label, shared_i32, scratch_i32, unit_iters, units_per_block, Gs,
                    shared_cap=None, scratch_cap=None, mode="steal"):
    """FIXED-WORK-PER-BLOCK wave-counting method (mission task 3). Each grid of G
    workgroups is given total_units = G*units_per_block, so EVERY block does the SAME
    fixed `units_per_block` of work regardless of G (every launch is bounded -> no
    G=1 pathology, no TDR). If C blocks run concurrently:
        T(G) ~= units_per_block * unit_time           for G <= C   (flat: 1 wave)
        T(G) ~= units_per_block * unit_time * ceil(G/C) for G > C   (rises in waves)
    so wall is FLAT until G hits the resident ceiling C_max, then climbs ~linearly.
    C_max = the knee. T uses the MEDIAN of reps (jitter-robust); min reported too.
    """
    if shared_cap is None:
        shared_cap = max(1, shared_i32)
    if scratch_cap is None:
        scratch_cap = max(1, scratch_i32)
    print(f"\n=== OCCUPANCY [{label}] mode={mode} shared={shared_i32}i32({shared_i32*4}B) "
          f"scratch={scratch_i32}i32({scratch_i32*4}B/blk) unit_iters={unit_iters} "
          f"units/block={units_per_block} ===")
    print(f"  {'G(blocks)':>10}  {'Tmed ms':>9}  {'Tmin ms':>9}  {'T/T(G0)':>8}  "
          f"{'units/ms':>9}  {'speedupx':>9}  {'impliedC':>9}")
    rows = []
    peak_thru = 0.0
    T0 = None
    for G in Gs:
        total_units = G * units_per_block
        try:
            Tmed, Tmin, ud = _time_persistent(G, units_per_block, unit_iters, shared_i32,
                                              scratch_i32, shared_cap, scratch_cap, mode=mode)
        except Exception as exc:
            print(f"  {G:>10}  FAILED ({type(exc).__name__}: {str(exc)[:48]})")
            break
        T = Tmed
        if T0 is None:
            T0 = T
        thru = total_units / T
        peak_thru = max(peak_thru, thru)
        speedup = thru / (rows[0][3] if rows else thru)
        ratio = T / T0
        impliedC = G / ratio if ratio > 0 else float("nan")
        rows.append((G, T, ratio, thru, speedup, impliedC))
        print(f"  {G:>10}  {Tmed:>9.2f}  {Tmin:>9.2f}  {ratio:>8.2f}  {thru:>9.2f}  "
              f"{speedup:>8.2f}x  {impliedC:>9.1f}")
    if not rows:
        return None
    # --- C_max from the FLAT-then-WAVES signature (rows: G,T,ratio,thru,speedup,impC) ---
    # While G <= C_max the wall is FLAT (ratio ~ 1, all blocks resident, 1 wave) and
    # throughput rises ~linearly with G. Past C_max the wall climbs ~linearly (waves)
    # and throughput PLATEAUS. Two independent estimators:
    #  (1) PLATEAU: C_max ~= peak aggregate throughput / per-block throughput. Per-block
    #      throughput = thru/G on the FLAT branch (where it is ~constant & maximal).
    #  (2) KNEE: the largest G whose wall is still within 1.5x of T(G0) (the flat band
    #      end == the resident ceiling). On the wave branch impliedC = G/(T/T(G0))
    #      plateaus AT C_max, so max impliedC is a third cross-check.
    # Per-block throughput from SMALL G only (G<=96 << any plausible C_max -> these are
    # cleanly in the flat band, thru/G = single-block throughput, jitter-robust). The
    # plateau (peak aggregate throughput) is itself robust. C_max = plateau/per-block.
    small = [r for r in rows if r[0] <= 96]
    per_block_thru = max((r[3] / r[0]) for r in small) if small else rows[0][3] / rows[0][0]
    c_max_plateau = peak_thru / per_block_thru if per_block_thru > 0 else float("nan")
    # flat-knee: largest G of a CONTIGUOUS flat run from G0 (ratio<=1.5), jitter-robust.
    knee = rows[0][0]
    for r in rows:
        if r[2] <= 1.5:
            knee = r[0]
        else:
            break
    c_max_impl = max(r[5] for r in rows)               # plateau of impliedC on wave branch
    c_max = c_max_plateau
    print(f"  -> contiguous-flat-knee G<={knee} ; peak {peak_thru:.1f} units/ms ; "
          f"per-block {per_block_thru:.4f} units/ms")
    print(f"  -> C_max(throughput-plateau) ~= {c_max_plateau:.0f} ; "
          f"C_max(wave impliedC plateau) ~= {c_max_impl:.0f} ; flat-knee ~= {knee}")
    return dict(label=label, mode=mode, shared_i32=shared_i32, scratch_i32=scratch_i32,
                c_max=c_max, c_max_impl=c_max_impl, peak_thru=peak_thru, knee=knee, rows=rows)


def main_sparse():
    """DECISIVE DISAMBIGUATION: is a LARGE reserved per-block footprint occupancy-bound
    or bandwidth-bound when accessed SPARSELY (like the real CSR body_tails store)?
    Fix alloc = the heavy chart's minimized footprint (118K i32 = 465KB, n=7027) and
    sweep the HOT window from tiny (sparse, like real rho-row access) to full (dense,
    streaming the whole footprint). If small-hot recovers C~750-1100, the real kernel
    is occupancy-bound and the dense-scratch curve under-counts its C."""
    Gs = [4, 8, 16, 32, 48, 64, 96, 128, 160, 192, 256, 384, 512, 768, 960, 1280,
          1536, 2048, 2304, 3072]
    upb = 400
    unit_iters = 256
    ALLOC = 118_988   # n=7027 minimized bytes/block / 4 (the heaviest real footprint)
    print("################################################################")
    print("# SPARSE-ACCESS DISAMBIGUATION (alloc fixed = heavy MIN footprint)")
    print(f"# alloc={ALLOC} i32 ({ALLOC*4/1024:.0f} KB/block); sweep HOT window")
    print("################################################################")
    results = []
    # hot window sizes: from ~rho rows (a few hundred i32) up to streaming the whole
    # alloc. body_tails row = 3 i32; rho_peak<=236 => ~700 i32 hot is realistic; cand
    # stage ~ a few thousand i32. Sweep across the spectrum.
    for hot in (96, 384, 768, 3072, 12288, 49152, ALLOC):
        h = min(hot, ALLOC)
        results.append(sweep_sparse(f"hot={h*4//1024 if h*4>=1024 else 0}KB", h, ALLOC,
                                    unit_iters, upb, Gs))
    print("\n\n############ SPARSE-ACCESS SUMMARY (alloc fixed = 465KB/block) ############")
    print(f"  {'hot window':>14}  {'C_max(plat)':>11}  {'C_max(impl)':>11}  {'peak u/ms':>9}")
    for r in results:
        if r is None:
            continue
        hk = r['hot_i32'] * 4
        hs = f"{hk/1024:.1f}KB" if hk >= 1024 else f"{hk}B"
        print(f"  {hs:>14}  {r['c_max']:>11.0f}  {r['c_max_impl']:>11.0f}  {r['peak_thru']:>9.1f}")
    print("\n  READING: if a SMALL hot window (a few KB, ~ real rho-row CSR access) over")
    print("  a 465KB alloc reaches C~750+, the real minimized kernel is OCCUPANCY-bound")
    print("  (the dense-scratch curve's C~105 is too pessimistic). If even small-hot")
    print("  caps low, the large reserved footprint itself bounds C (VRAM/SSBO budget).")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer G points / units")
    ap.add_argument("--sparse", action="store_true",
                    help="run the sparse-access disambiguation (large alloc, small hot)")
    args = ap.parse_args()
    if args.sparse:
        return main_sparse()

    # Grid sweep: span well past the ~160 prior measurement and past the ~950 target,
    # up to a few thousand workgroups so the flat-then-waves knee is unambiguous.
    if args.quick:
        Gs = [4, 16, 48, 96, 160, 256, 512, 960, 1536, 2304]
        upb = 200
    else:
        Gs = [4, 8, 16, 32, 48, 64, 96, 128, 160, 192, 256, 384, 512, 768,
              960, 1280, 1536, 2048, 2304, 3072, 4096, 6144]
        upb = 400

    # FIXED units-per-block: each grid of G blocks runs G*upb total units, so every
    # block does exactly `upb` units => every launch is bounded (no G=1 pathology, no
    # TDR). unit_iters tuned so one unit ~ a light body-DP cell. The flat band of T(G)
    # (all blocks resident, 1 wave) ends at the resident ceiling C_max; past it the
    # wall climbs in waves.
    unit_iters = 256

    print("################################################################")
    print("# PERSISTENT WORK-STEALING OCCUPANCY PROBE (RX 7900 XTX, ti.vulkan)")
    print(f"# BD={BD} (1 wavefront/block), {N_CU} CUs, target C ~= 950 for <15min")
    print(f"# fixed units/block={upb}, unit_iters={unit_iters}")
    print("################################################################")

    results = []
    # (0) PURE-OCCUPANCY CROSS-CHECK: no-atomic replication at the MIN footprint.
    # Isolates the occupancy ceiling from work-stealing atomic-counter contention.
    r_rep = sweep_occupancy("MIN replicate (no-atomic)", shared_i32=4, scratch_i32=16,
                            unit_iters=unit_iters, units_per_block=upb, Gs=Gs,
                            mode="replicate")
    results.append(r_rep)
    # (1) MINIMIZED footprint, WORK-STEALING (the mission's design): tiny shared mem
    # (the block kernel uses only 4 i32 shared = 16 B) + small global scratch.
    r_min = sweep_occupancy("MIN steal (4sh/16scr)", shared_i32=4, scratch_i32=16,
                            unit_iters=unit_iters, units_per_block=upb, Gs=Gs,
                            mode="steal")
    results.append(r_min)
    # (2) Occupancy-vs-SHARED-memory curve (on-chip LDS limiter; 64KB LDS/CU on AMD).
    for sh in (256, 1024, 4096, 8192):
        results.append(sweep_occupancy(f"SHARED={sh}i32({sh*4}B)", shared_i32=sh,
                                       scratch_i32=16, unit_iters=unit_iters,
                                       units_per_block=upb, Gs=Gs, mode="steal"))
    # (3) Occupancy-vs-global-SCRATCH curve (memory-bandwidth + SSBO budget limiter).
    # This is the axis the REAL block kernel sits on (its per-block buffers are GLOBAL,
    # ~hundreds of KB to ~1.5 MB/lane). Mapping the kernel's bytes/block here gives
    # C_max for the current vs minimized footprint.
    for sc in (256, 1024, 4096, 16384, 65536):
        results.append(sweep_occupancy(f"SCRATCH={sc}i32({sc*4}B/blk)", shared_i32=4,
                                       scratch_i32=sc, unit_iters=unit_iters,
                                       units_per_block=upb, Gs=Gs, mode="steal"))

    print("\n\n################ OCCUPANCY-vs-MEMORY SUMMARY ################")
    print(f"  {'footprint':>30}  {'mode':>9}  {'C_max(plat)':>11}  {'C_max(impl)':>11}  "
          f"{'peak u/ms':>9}  {'knee G':>7}")
    for r in results:
        if r is None:
            continue
        print(f"  {r['label']:>30}  {r.get('mode','?'):>9}  {r['c_max']:>11.0f}  "
              f"{r['c_max_impl']:>11.0f}  {r['peak_thru']:>9.1f}  {r['knee']:>7}")
    cm = [r["c_max"] for r in results if r and math.isfinite(r["c_max"])]
    if cm:
        cmax_steal = r_min["c_max"] if r_min else float("nan")
        cmax_rep = r_rep["c_max"] if r_rep else float("nan")
        print(f"\n  MIN-FOOTPRINT C_max: work-stealing={cmax_steal:.0f}  "
              f"replicate(no-atomic)={cmax_rep:.0f}  (the occupancy CEILING)")
        ceiling = max(cmax_steal, cmax_rep)  # the true HW ceiling = best of both
        print(f"  HARDWARE OCCUPANCY CEILING (best of steal/replicate) = {ceiling:.0f}")
        print(f"  C_max range over memory sweep: {min(cm):.0f} .. {max(cm):.0f}")
        target = 950
        verdict = "REACHES ~950 (<15min PLAUSIBLE at min footprint)" if ceiling >= target \
            else f"CEILING ~{ceiling:.0f} < 950 (<15min OUT OF REACH for serial-per-key)"
        print(f"\n  ==> VERDICT: HW occupancy ceiling {'>=' if ceiling>=target else '<'} {target} "
              f"==> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
