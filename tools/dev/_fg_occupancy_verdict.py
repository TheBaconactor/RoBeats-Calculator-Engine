"""FG <15-min FEASIBILITY VERDICT: GPU resident-block occupancy ceiling probe.

THE QUESTION (bounded — NOT building the full production kernel):
  A validated bit-exact block/warp-per-key body-DP kernel exists
  (`tools/dev/_fg_block_body_dp_parallel.py`): 1 workgroup per (ft,ff) key,
  BD=64, parallel scatter-max skyline. Full-pool (25,921 keys) projected at the
  previously-measured resident concurrency C~160 is ~106 min (~7x over the 900 s
  <15-min target). To hit <15 min we need C~950-1130 RESIDENT blocks.

  C~160 was capped by (a) per-block memory (resident blocks/CU) and (b) the
  Vulkan TDR watchdog (heaviest single-block cells 2.7-7.1 s > ~2 s).

  DETERMINE: with a PERSISTENT-KERNEL WORK-STEALING design + MINIMAL per-block
  memory, what is the MAX achievable resident block concurrency C_max on this
  GPU (RX 7900 XTX, 96 CUs, Taichi ti.vulkan)? Does it reach ~950 (=> <15 min
  PLAUSIBLE) or cap well below (=> <15 min out of reach for this serial-per-key
  workload)?

METHOD (occupancy ceiling, isolated from the TDR-heavy-cell issue):
  1. Persistent kernel: launch a FIXED grid of G workgroups (BD=64). Each
     workgroup loops { idx = atomic_add(global_counter, 1); if idx >= N break;
     run a LIGHT, UNIFORM synthetic body-DP-SHAPED workload for that key }.
     Minimal per-block shared/scratch memory (tight dtypes/sizing) — bytes/block
     reported. Light uniform workload isolates the OCCUPANCY ceiling from the
     per-key heavy-cell TDR variance (per-key math is bit-exact-validated
     elsewhere; here we measure how many blocks stay RESIDENT).
  2. Measure C_max via THROUGHPUT SATURATION: sweep G; aggregate throughput
     (keys/sec) rises ~linearly with G until G == C_max resident blocks, then
     plateaus. The plateau width / saturation point == C_max. Also sweep a
     couple of per-block memory sizes to get the occupancy-vs-memory curve.
  3. VERDICT: C_max >= ~950 ? plausible : out of reach. If plausible, give the
     work-stealing full-pool projection (total single-block body work ~28,367
     block-min / C_max, 2 procs; heavy cells still need TDR-chunking).

WHY THROUGHPUT SATURATION MEASURES RESIDENT C (not launched G):
  The GPU scheduler only co-resides as many workgroups as fit given per-CU
  register/LDS/wavefront-slot limits (occupancy). Launching G > C_max does NOT
  increase resident blocks; the extra workgroups queue. With a PERSISTENT grid
  the queued blocks never start until a resident one finishes — but since each
  block steals MANY keys in its loop, the FIXED grid of G blocks just =
  exactly G resident blocks when G <= C_max, and = C_max resident (rest queued,
  but with persistent loops the launch of G blocks where G>C_max means only
  C_max ever run concurrently and they drain the whole counter). So aggregate
  keys/sec saturates exactly at C_max. We detect the knee.

Taichi gotchas honored: no `from __future__ import annotations`; pooled ndarray
scratch reset per use; dev launches kept TDR-safe (each launch sized so total
synthetic work / expected concurrency stays well under ~2 s, and we cap the
per-launch key budget); block size 64 == AMD wavefront.

READ-ONLY production. Self-contained: depends on NO other tools/dev file.

Run: python -u tools/dev/_fg_occupancy_verdict.py
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

BD = 64  # threads/workgroup == AMD wavefront (subgroup) size

# Full-pool problem constants (from the mission brief / validated kernel).
N_KEYS_FULL = 25_921           # 161 ft x 161 ff grid of (ft,ff) keys
TOTAL_BODY_BLOCK_MIN = 28_367  # measured total single-block body work, block-minutes
N_PROCS = 2                    # dual in-flight processes share the GPU
TARGET_SEC = 900.0             # <15 min
C_TARGET = 950                 # resident-block concurrency needed for <15 min


# --------------------------------------------------------------------------- #
# Persistent work-stealing occupancy kernel.
#
# A FIXED grid of G workgroups (block_dim=BD). Each workgroup repeatedly steals
# the next key index from a single global atomic counter and runs a LIGHT,
# UNIFORM, body-DP-SHAPED synthetic workload for that key, until the counter
# exhausts N keys. We measure aggregate keys/sec as a function of G; it
# saturates at the resident-block concurrency C_max.
#
# Per-block memory is MINIMIZED: one tiny shared scratch array of SCR i32 lanes
# (the body-DP "skyline" stand-in) plus a couple of shared scalars. SCR is a
# kernel template arg so we can sweep the occupancy-vs-per-block-memory curve.
#
# The synthetic per-key workload shape mirrors the real body DP cost structure
# WITHOUT its data: an outer "states" loop (sequential dependency, like the
# backward DP over states) wrapping an inner block-parallel "candidate" reduce
# into the shared scratch (like the scatter-max skyline). ITERS scales the work
# so we can keep each launch TDR-safe while still saturating the schedulers.
# --------------------------------------------------------------------------- #
def _build_kernel(SCR, STATES, ITERS, BATCH):
    """Self-contained persistent work-stealing kernel.

    Per-block shared bytes = SCR*4 (i32 scratch) + 4*4 (4 i32 scalars).

    BATCH-stealing: thread 0 claims BATCH keys per global atomic_add, so the
    single global counter is NOT the bottleneck (we are measuring the OCCUPANCY
    ceiling, not atomic-counter throughput). Each block then runs the per-key
    body-DP-shaped synthetic workload for every key in its claimed batch.
    """

    @ti.kernel
    def occ_kernel(
        G: ti.i32,
        n_keys: ti.i32,
        counter: ti.types.ndarray(dtype=ti.i32, ndim=1),
        sink: ti.types.ndarray(dtype=ti.i64, ndim=1),
        done_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ):
        ti.loop_config(block_dim=BD)
        for gid in range(G * BD):
            block = gid // BD
            t = ti.simt.block.thread_idx()

            scr = ti.simt.block.SharedArray((SCR,), ti.i32)
            # sh[0]=batch base idx, sh[1]=dependency-acc broadcast, sh[2..3] pad.
            sh = ti.simt.block.SharedArray((4,), ti.i32)

            local_acc = ti.i64(0)
            keys_here = 0
            keep_going = 1
            while keep_going == 1:
                # claim a BATCH of keys with ONE global atomic (low counter pressure).
                if t == 0:
                    sh[0] = ti.atomic_add(counter[0], BATCH)
                ti.simt.block.sync()
                base = sh[0]
                if base >= n_keys:
                    keep_going = 0
                else:
                    bk = 0
                    while bk < BATCH:
                        idx = base + bk
                        bk += 1
                        if idx < n_keys:
                            keys_here += 1
                            j = t
                            while j < SCR:
                                scr[j] = 0
                                j += BD
                            ti.simt.block.sync()

                            # All constants fit signed i32 (the two hash
                            # multipliers use their bit-equivalent negative i32
                            # form: -1640531535 == 0x9E3779B1,
                            # -2048144777 == 0x85EBCA77); every result is masked
                            # to 31-bit non-negative so the i32 lanes never
                            # overflow Vulkan codegen.
                            acc = (ti.i32(idx) * -1640531535) & 0x7FFFFFFF
                            acc = (acc ^ (ti.i32(idx) << 1)) & 0x7FFFFFFF
                            for s in range(STATES):
                                c = t
                                while c < ITERS:
                                    v = (acc + c * 40503 + s * -2048144777) & 0x7FFFFFFF
                                    slot = (v >> 7) % SCR
                                    ti.atomic_max(scr[slot], v)
                                    c += BD
                                ti.simt.block.sync()
                                if t == 0:
                                    sh[1] = (acc * 1103515245 + 12345 + scr[s % SCR]) & 0x7FFFFFFF
                                ti.simt.block.sync()
                                acc = sh[1]  # broadcast dependency to all threads
                                ti.simt.block.sync()
                            local_acc += ti.i64(acc)

            if t == 0:
                sink[block] = local_acc
                ti.atomic_add(done_cnt[0], keys_here)

    return occ_kernel


def run_once(kern, G, n_keys):
    """One persistent launch over n_keys with a fixed grid of G workgroups.

    Returns (wall_seconds, keys_processed, sink_checksum). Pooled scratch is
    reset each call (counter/done_cnt zeroed, sink reallocated to G).
    """
    counter = np.zeros(1, dtype=np.int32)
    done_cnt = np.zeros(1, dtype=np.int32)
    sink = np.zeros(G, dtype=np.int64)
    ti.sync()
    t0 = time.perf_counter()
    kern(G, n_keys, counter, sink, done_cnt)
    ti.sync()
    wall = time.perf_counter() - t0
    return wall, int(done_cnt[0]), int(sink.sum())


# TDR-safety budget: each timed launch targets ~this wall; the per-launch key
# count is sized PER-G from a cheap rate pre-probe so even small-G (low-rate)
# launches stay well under the ~2 s Vulkan TDR watchdog. The throughput measure
# rate=keys/wall is independent of the key count, so adaptive budgeting does not
# bias the saturation curve.
TARGET_LAUNCH_S = 1.0
TDR_HARD_CAP_S = 1.8       # never let an estimated launch exceed this
PROBE_KEYS = 50_000        # cheap rate pre-probe per G (sub-ms..few-ms)


def _measure_rate(kern, G, n_keys):
    """One launch; assert work-stealing processed exactly n_keys; return rate."""
    wall, done, _ = run_once(kern, G, n_keys)
    if done != n_keys:
        raise RuntimeError(
            f"work-stealing lost keys: G={G} done={done} expected={n_keys}"
        )
    return (done / wall if wall > 0 else 0.0), wall


def _budget_for_G(kern, G):
    """Size a TDR-safe key budget for this G from a cheap rate pre-probe, so the
    timed launch lands near TARGET_LAUNCH_S and never exceeds TDR_HARD_CAP_S."""
    rate, _ = _measure_rate(kern, G, PROBE_KEYS)
    keys = int(rate * TARGET_LAUNCH_S)
    keys = max(PROBE_KEYS, keys)
    keys = min(keys, int(rate * TDR_HARD_CAP_S) if rate > 0 else keys)
    return keys


def sweep_G(kern, G_list, repeats=3):
    """Throughput-saturation sweep. For each G: pre-probe its rate to size a
    TDR-safe per-G key budget, then run `repeats` timed launches and keep the
    BEST (max) keys/sec (best == least scheduler/driver noise). Each launch is
    bounded under the TDR watchdog regardless of G. Returns list of dicts.
    """
    rows = []
    for G in G_list:
        budget = _budget_for_G(kern, G)
        best_rate = 0.0
        best_wall = float("inf")
        for _ in range(repeats):
            rate, wall = _measure_rate(kern, G, budget)
            if rate > best_rate:
                best_rate = rate
                best_wall = wall
        rows.append(dict(G=G, rate=best_rate, wall=best_wall, keys=budget))
    return rows


def detect_knee(rows):
    """Recover the resident-block concurrency C_max from a throughput-vs-G sweep.

    Physics: while G <= C_max EVERY launched block is co-resident, so aggregate
    throughput rises ~linearly with G (each block contributes ~one block's
    rate). Once G > C_max the extra blocks cannot co-reside; aggregate
    throughput plateaus at R_plateau = C_max * per_block_rate. Therefore:

        C_max  ==  R_plateau / per_block_rate          (the HEADLINE estimate)

    where per_block_rate is measured at the SMALLEST G (deep in the linear
    region, all G blocks resident, minimal contention amortization artifacts).
    This throughput-RATIO is the authoritative resident-block count and does NOT
    depend on the sweep happening to bracket the knee.

    We ALSO report the empirical saturation onset `knee_G` = smallest G whose
    rate is within 5% of R_plateau, but flag `saturated_in_sweep`: if knee_G is
    the largest G tested, saturation was NOT bracketed and knee_G is only a
    LOWER BOUND on where the plateau begins (NOT an upper estimate of C_max).
    The headline implied_Cmax is the number to trust.
    """
    R_plateau = max(r["rate"] for r in rows)
    max_G = max(r["G"] for r in rows)
    knee_G = max_G
    for r in sorted(rows, key=lambda x: x["G"]):
        if r["rate"] >= 0.95 * R_plateau:
            knee_G = r["G"]
            break
    saturated_in_sweep = knee_G < max_G
    # per-block rate from the smallest G (linear region: all blocks resident).
    small = min(rows, key=lambda x: x["G"])
    per_block_rate = small["rate"] / small["G"]
    implied_Cmax = R_plateau / per_block_rate if per_block_rate > 0 else float("inf")
    return dict(
        R_plateau=R_plateau,
        knee_G=knee_G,
        saturated_in_sweep=saturated_in_sweep,
        per_block_rate=per_block_rate,
        implied_Cmax=implied_Cmax,
    )


def fmt_rows(rows):
    out = []
    for r in sorted(rows, key=lambda x: x["G"]):
        out.append(
            f"    G={r['G']:5d}  rate={r['rate']:12,.0f} keys/s  "
            f"wall={r['wall']*1000:8.1f} ms  (budget {r['keys']:,} keys)"
        )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller sweep for a fast read")
    args = ap.parse_args()

    print("=" * 78, flush=True)
    print("FG <15-min FEASIBILITY: GPU RESIDENT-BLOCK OCCUPANCY CEILING (C_max)", flush=True)
    print("=" * 78, flush=True)
    print(f"  backend = ti.vulkan (RX 7900 XTX, 96 CUs)   BD={BD} (wavefront)", flush=True)
    print(f"  need C ~ {C_TARGET} resident blocks for <{TARGET_SEC/60:.0f} min full-pool", flush=True)
    print(flush=True)

    # ---------------------------------------------------------------- #
    # (a) MINIMAL per-block memory. The body DP per-state skyline needs a small
    # scratch; we probe a tight size and a couple larger ones for the curve.
    # The minimal viable scratch for a per-state scatter-max stand-in is small
    # (here SCR=32 i32 = 128 B). The real kernel's *global* per-lane arrays
    # (best_fever_by_pair etc.) live in DEVICE memory, NOT shared/LDS, so they
    # do NOT count against per-block LDS occupancy — only the block-shared
    # scratch + scalars do. We minimize the LDS footprint here.
    # ---------------------------------------------------------------- #
    STATES = 64      # synthetic sequential state-chain length (per-key work,
                     #   heavy enough that batch-steal overhead is amortized so
                     #   the measured ceiling is OCCUPANCY, not atomic-counter).
    ITERS = 192      # inner candidate-reduce width per state (uniform).
    BATCH = 8        # keys claimed per global atomic (cuts counter pressure).

    scr_sizes = [16, 32, 64, 128]  # i32 lanes -> 80,144,272,528 bytes LDS scratch
    if args.quick:
        scr_sizes = [32, 128]

    # Sweep well past the expected knee so saturation is genuinely BRACKETED
    # (the prior coarse sweep was still creeping at 2048).
    G_list = [32, 64, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096]
    if args.quick:
        G_list = [64, 128, 256, 512, 1024, 2048, 4096]

    print("(a) PER-BLOCK SHARED-MEMORY FOOTPRINT (minimized):", flush=True)
    for scr in scr_sizes:
        b = (scr + 4) * 4  # SCR i32 scratch + 4 i32 shared scalars
        tag = "  <-- minimized" if scr == scr_sizes[0] else ""
        print(f"    SCR={scr:4d} i32  ->  {b:5d} bytes/block LDS{tag}", flush=True)
    print(flush=True)

    # Build + warm-compile a kernel per scratch size.
    kernels = {}
    print("  compiling/warming kernels (Vulkan)...", flush=True)
    for scr in scr_sizes:
        k = _build_kernel(scr, STATES, ITERS, BATCH)
        # warm compile with a tiny launch.
        run_once(k, 64, 4096)
        kernels[scr] = k
    print("  done.\n", flush=True)

    print(f"  per-G key budget is sized adaptively from a {PROBE_KEYS:,}-key rate "
          f"pre-probe to target ~{TARGET_LAUNCH_S:.1f} s/launch (hard-capped "
          f"{TDR_HARD_CAP_S:.1f} s) so EVERY launch is TDR-safe.\n", flush=True)

    # ---------------------------------------------------------------- #
    # (b) THROUGHPUT-SATURATION SWEEP + occupancy-vs-memory curve.
    # ---------------------------------------------------------------- #
    results = {}
    for scr in scr_sizes:
        b = (scr + 4) * 4
        print(f"(b) THROUGHPUT SWEEP @ SCR={scr} ({b} B/block):", flush=True)
        rows = sweep_G(kernels[scr], G_list, repeats=2 if args.quick else 3)
        knee = detect_knee(rows)
        results[scr] = dict(rows=rows, knee=knee, bytes=b)
        print(fmt_rows(rows), flush=True)
        sat = "saturated" if knee["saturated_in_sweep"] else "NOT bracketed (lower bound)"
        print(f"    -> R_plateau={knee['R_plateau']:,.0f} keys/s  "
              f"knee@G={knee['knee_G']} [{sat}]  "
              f"per-block-rate~{knee['per_block_rate']:,.0f} keys/s  "
              f"==> C_max~{knee['implied_Cmax']:,.0f} resident blocks", flush=True)
        print(flush=True)

    # ---------------------------------------------------------------- #
    # OCCUPANCY-vs-MEMORY CURVE summary.
    # ---------------------------------------------------------------- #
    print("OCCUPANCY-vs-PER-BLOCK-MEMORY CURVE:", flush=True)
    print(f"    {'bytes/blk':>10} {'knee G':>8} {'C_max(impl)':>12} {'R_plateau keys/s':>18} {'saturated?':>12}", flush=True)
    for scr in scr_sizes:
        r = results[scr]
        k = r["knee"]
        print(f"    {r['bytes']:>10} {k['knee_G']:>8} "
              f"{k['implied_Cmax']:>12,.0f} {k['R_plateau']:>18,.0f} "
              f"{('yes' if k['saturated_in_sweep'] else 'lower-bnd'):>12}", flush=True)
    print(flush=True)

    # HEADLINE C_max = the throughput-RATIO estimate (R_plateau / per_block_rate),
    # which is the PHYSICAL resident-block count and is independent of whether the
    # sweep bracketed the knee. Take the BEST (max) across the minimized-memory
    # configs as the most generous achievable concurrency.
    implied_vals = [results[scr]["knee"]["implied_Cmax"] for scr in scr_sizes]
    C_max_headline = max(implied_vals)
    min_scr = scr_sizes[0]
    cmax_implied_min = results[min_scr]["knee"]["implied_Cmax"]
    any_saturated = any(results[scr]["knee"]["saturated_in_sweep"] for scr in scr_sizes)

    print("=" * 78, flush=True)
    print("VERDICT", flush=True)
    print("=" * 78, flush=True)
    print(f"  Measured resident-block concurrency C_max (throughput-ratio):", flush=True)
    print(f"    best over configs                          : ~{C_max_headline:,.0f} blocks", flush=True)
    print(f"    at MINIMIZED footprint ({(min_scr+4)*4} B/block)        : ~{cmax_implied_min:,.0f} blocks", flush=True)
    print(f"    throughput saturation observed in sweep    : {'yes' if any_saturated else 'no (plateau past max G)'}", flush=True)
    print(flush=True)

    # PLAUSIBILITY is decided by the PHYSICAL resident concurrency (implied
    # C_max), NOT by the swept knee position (a knee pinned at max-G means
    # saturation was not bracketed, which would FALSELY look like high C).
    plausible = C_max_headline >= C_TARGET
    print(f"  Target for <15 min: C ~ {C_TARGET} resident blocks.", flush=True)
    if plausible:
        print(f"  ==> C_max (~{C_max_headline:,.0f}) REACHES ~{C_TARGET}: <15 min is PLAUSIBLE.", flush=True)
        # work-stealing full-pool projection.
        eff_C = C_max_headline
        # total body single-block work / resident concurrency / procs.
        proj_min = TOTAL_BODY_BLOCK_MIN / eff_C / N_PROCS
        print(flush=True)
        print(f"  WORK-STEALING FULL-POOL PROJECTION:", flush=True)
        print(f"    total single-block body work = {TOTAL_BODY_BLOCK_MIN:,} block-min", flush=True)
        print(f"    / C_max~{eff_C:,.0f} resident blocks / {N_PROCS} procs", flush=True)
        print(f"    ~= {proj_min:.1f} min  ({'UNDER' if proj_min < 15 else 'OVER'} the 15-min target)", flush=True)
        print(f"    NOTE: heavy single-block cells (2.7-7.1 s) STILL need TDR-chunking;", flush=True)
        print(f"          this projection is the occupancy-bound floor, not the chunked wall.", flush=True)
    else:
        print(f"  ==> C_max (~{C_max_headline:,.0f}) is WELL BELOW ~{C_TARGET}: <15 min is OUT OF REACH", flush=True)
        print(f"      on this hardware for this SERIAL-PER-KEY (1 block/key) workload.", flush=True)
        floor_min = TOTAL_BODY_BLOCK_MIN / C_max_headline / N_PROCS
        over = floor_min / (TARGET_SEC / 60.0)
        print(flush=True)
        print(f"  HARD OCCUPANCY CEILING: ~{C_max_headline:,.0f} resident blocks (max).", flush=True)
        print(f"    occupancy-bound floor = {TOTAL_BODY_BLOCK_MIN:,} block-min / "
              f"{C_max_headline:,.0f} / {N_PROCS} = {floor_min:.1f} min "
              f"(~{over:.1f}x over 15 min).", flush=True)
        print(f"    The 1-block-per-key mapping cannot reach <15 min; would require a", flush=True)
        print(f"    finer-grained decomposition (multiple blocks per heavy key) to lift", flush=True)
        print(f"    effective parallelism past the per-key serial ceiling.", flush=True)

    print("=" * 78, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
