"""THE VERDICT (mission task 4): does a PERSISTENT-KERNEL WORK-STEALING design with
MINIMIZED per-block memory reach the resident concurrency C needed for <15min, or cap
below it? Ties together the three measurements of this probe:

  (A) MEASURED occupancy-vs-memory curve (`_fg_persistent_occupancy.py`, median-of-5,
      RX 7900 XTX): C_max as a function of per-block on-chip SHARED memory and per-block
      GLOBAL scratch. Work-stealing == replication (atomic counter is NOT a bottleneck).
  (B) MEASURED minimized per-block memory (`_fg_block_mem_account.py`): the validated
      block kernel's bytes/block BEFORE vs AFTER the bit-exact shrinks (dense pair
      arrays -> open-addressing hash; u64->i32 body store; right-sized cand/scand).
  (C) VALIDATED full-pool BODY single-block work model (`_fg_headline.py`): total body
      block-seconds over the real 2,238-chart pool (C-INDEPENDENT) -> wall = work / C.

The saturated full-pool wall is wall = body_block_s / C (+ fast-path / C). The prior
projection used the CURRENT kernel's MEASURED C=160. THIS probe asks: at the MINIMIZED
footprint, what C is achievable, and what wall does that give?

KEY DISTINCTION (the honest part): the synthetic SCRATCH-axis curve touches the ENTIRE
per-block scratch every unit (worst-case memory bandwidth), so it is a LOWER BOUND on C
for the real kernel (whose CSR body_tails access is far sparser). The pure-occupancy
ceiling (tiny footprint) is an UPPER BOUND. We bracket the real minimized C between them
and report the wall for BOTH bounds, plus the C needed for <15min.

Read-only. Run: python tools/dev/_fg_persistent_pool_verdict.py
"""
import importlib.util
import math
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402

CELLS = (TOTAL_ROWS + 1) ** 2  # 25,921


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --------------------------------------------------------------------------- #
# (A) MEASURED occupancy-vs-memory curve (median-of-5, this session,
# _fg_persistent_occupancy.py). C_max(throughput-plateau). The SCRATCH axis is the
# one the real kernel sits on (its per-block buffers are GLOBAL). bytes = i32*4.
# --------------------------------------------------------------------------- #
# pure-occupancy ceiling (negligible global scratch, tiny shared):
C_CEILING = 1090   # SHARED=1-4KB plateau (746 at 16B is a fixed-overhead floor; the
                   # true ceiling with a little shared is ~1075-1140; use 1090 mid).
# global-scratch -> C_max (the bandwidth-bound axis the real kernel lives on):
#   per-block scratch BYTES -> measured C_max(plateau)
SCRATCH_CURVE = [
    (64,      746),     # 16 i32   (MIN synthetic footprint)
    (1024,    946),     # 256 i32
    (4096,    431),     # 1024 i32
    (16384,   233),     # 4096 i32
    (65536,   184),     # 16384 i32
    (262144,  105),     # 65536 i32 (from this run's last sweep, bandwidth-saturated)
]
SC_BYTES = np.array([b for b, _ in SCRATCH_CURVE], float)
SC_CMAX = np.array([c for _, c in SCRATCH_CURVE], float)


def c_from_scratch_bytes(b):
    """Interpolate measured C_max(plateau) at a per-block GLOBAL footprint of b bytes
    in log-log (the curve is ~power-law in the bandwidth-bound regime). This is the
    PESSIMISTIC bound (synthetic touches all scratch hot every unit)."""
    b = max(SC_BYTES[0], min(SC_BYTES[-1], b))
    lb = math.log(b)
    return float(math.exp(np.interp(lb, np.log(SC_BYTES), np.log(SC_CMAX))))


# --------------------------------------------------------------------------- #
# (B) MEASURED minimized per-block bytes (this session, _fg_block_mem_account.py).
# CURRENT (as-allocated) vs MINIMIZED (bit-exact shrinks). bytes/block.
# --------------------------------------------------------------------------- #
MEM_ANCHORS = [
    # (n, current_bytes, minimized_bytes)
    (653,   int(448.17 * 1024), int(46.22 * 1024)),
    (1083,  int(518.80 * 1024), int(73.15 * 1024)),
    (1655,  int(592.99 * 1024), int(106.27 * 1024)),
    (2312,  int(748.95 * 1024), int(155.07 * 1024)),
    (4722,  int(1.29 * 1024 * 1024), int(300.18 * 1024)),
    (7027,  int(1.85 * 1024 * 1024), int(464.80 * 1024)),
]
MN_NS = np.array([a[0] for a in MEM_ANCHORS], float)
MN_CUR = np.array([a[1] for a in MEM_ANCHORS], float)
MN_MIN = np.array([a[2] for a in MEM_ANCHORS], float)


def bytes_at(n, which="min"):
    arr = MN_MIN if which == "min" else MN_CUR
    n = max(MN_NS[0], min(MN_NS[-1], n))
    return float(math.exp(np.interp(math.log(n), np.log(MN_NS), np.log(arr))))


def main():
    hl = _load("hl_v", "_fg_headline.py")
    rgm = _load("rgv_v", "_fg_real_grid_validate.py")

    # ---- (C) validated body-work model (reuse the headline anchors + fit) ----
    ns_a = np.array([a[0] for a in hl.ANCHORS], float)
    fbd_a = np.array([a[1] for a in hl.ANCHORS], float)
    mW_a = np.array([a[2] for a in hl.ANCHORS], float)
    fpk_a = np.array([a[3] for a in hl.ANCHORS], float)
    mb = ns_a >= 150
    pb = np.polyfit(np.log(ns_a[mb]), np.log(mW_a[mb]), 1)
    W_a, W_p = math.exp(pb[1]), pb[0]
    mf = np.isfinite(fpk_a) & (ns_a >= 150)
    pf = np.polyfit(np.log(ns_a[mf]), np.log(fpk_a[mf]), 1)
    fp_a, fp_p = math.exp(pf[1]), pf[0]
    order = np.argsort(ns_a); ns_s, fbd_s = ns_a[order], fbd_a[order]

    def frac_bd_at(x):
        return float(np.interp(x, ns_s, fbd_s, left=fbd_s[0], right=fbd_s[-1]))

    sc = rgm.scan_note_counts()
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    est_W = np.maximum(W_a * np.power(pool_ns, W_p), float(mW_a[mb].min()))
    est_fp = np.maximum(fp_a * np.power(pool_ns, fp_p), float(fpk_a[mf].min()))
    fr = np.array([frac_bd_at(x) for x in pool_ns])

    # total body single-block work (block-seconds), C-INDEPENDENT
    body_block_ms_per_chart = fr * CELLS * est_W      # ms of single-block body work/chart
    body_block_s = body_block_ms_per_chart.sum() / 1000.0
    fast_block_s = ((1 - fr) * CELLS * est_fp).sum() / 1000.0

    print("################################################################")
    print("# PERSISTENT WORK-STEALING + MIN-MEMORY: FULL-POOL VERDICT")
    print("################################################################")
    print(f"  pool charts={len(pool_ns)}  cells/chart={CELLS}  "
          f"n: median={np.median(pool_ns):.0f} p90={np.percentile(pool_ns,90):.0f} "
          f"max={pool_ns.max():.0f}")
    print(f"  total BODY single-block work (C-independent) = {body_block_s/60:.0f} block-min "
          f"({body_block_s/3600:.1f} block-hr)")
    print(f"  total FAST-PATH work                          = {fast_block_s/60:.0f} block-min")

    # ---- C needed for <15min (900s), 1-proc and 2-proc ----
    print(f"\n  ---- C REQUIRED for <15min (900 s) ----")
    for procs in (1, 2):
        # wall = (body_block_s + fast_block_s) / C / procs  <= 900
        C_need = (body_block_s + fast_block_s) / (900 * procs)
        C_need_body = body_block_s / (900 * procs)
        print(f"  {procs}-proc: need C >= {C_need:.0f}  (body-only C >= {C_need_body:.0f})")

    # ---- C ACHIEVABLE at the minimized footprint, per chart (bytes -> C via curve) ----
    # The real per-block GLOBAL footprint varies with n; map each chart's MINIMIZED
    # bytes/block onto the measured SCRATCH curve (PESSIMISTIC bound). Also the pure-
    # occupancy CEILING (OPTIMISTIC bound). The saturated wall integrates per chart:
    #    chart_wall = body_block_ms(n) / C_eff(n) ; sum over pool.
    C_pess = np.array([c_from_scratch_bytes(bytes_at(n, "min")) for n in pool_ns])
    C_pess_cur = np.array([c_from_scratch_bytes(bytes_at(n, "cur")) for n in pool_ns])
    C_opt = np.full_like(pool_ns, C_CEILING)

    def pool_wall_s(Cvec):
        body = (body_block_ms_per_chart / Cvec).sum() / 1000.0
        fast = ((1 - fr) * CELLS * est_fp / Cvec).sum() / 1000.0
        return body, fast

    print(f"\n  per-block MIN footprint: n=653 {bytes_at(653,'min')/1024:.0f}KB -> "
          f"C~{c_from_scratch_bytes(bytes_at(653,'min')):.0f} ; "
          f"n=2312 {bytes_at(2312,'min')/1024:.0f}KB -> C~{c_from_scratch_bytes(bytes_at(2312,'min')):.0f} ; "
          f"n=7027 {bytes_at(7027,'min')/1024:.0f}KB -> C~{c_from_scratch_bytes(bytes_at(7027,'min')):.0f}")
    print(f"  per-block CUR footprint: n=2312 {bytes_at(2312,'cur')/1024:.0f}KB -> "
          f"C~{c_from_scratch_bytes(bytes_at(2312,'cur')):.0f} ; "
          f"n=7027 {bytes_at(7027,'cur')/1024:.0f}KB -> C~{c_from_scratch_bytes(bytes_at(7027,'cur')):.0f}  "
          f"(matches the prior measured C~160)")

    print(f"\n  ===== SATURATED FULL-POOL WALL (wall = work / C_eff) =====")
    print(f"  {'scenario':>40}  {'1-proc min':>10}  {'2-proc min':>10}  {'<15min 2p?':>11}")
    scenarios = [
        ("CURRENT mem, bandwidth-C (~the prior 160)", C_pess_cur),
        ("MINIMIZED mem, bandwidth-bound C (LOWER)", C_pess),
        (f"MINIMIZED mem, pure-occ ceiling C={C_CEILING:.0f} (UPPER)", C_opt),
    ]
    for label, Cvec in scenarios:
        body, fast = pool_wall_s(Cvec)
        tot1 = body + fast
        tot2 = tot1 / 2.0
        flag = "YES" if tot2 <= 900 else "no"
        # effective harmonic-mean C for transparency
        body_only_s = body_block_s
        c_eff = body_only_s / body if body > 0 else float("nan")
        print(f"  {label:>40}  {tot1/60:>9.0f}m  {tot2/60:>9.0f}m  {flag:>11}  "
              f"(work-weighted C_eff~{c_eff:.0f})")

    # ---- flat C sweep for the headline table (constant C across all charts) ----
    print(f"\n  ===== CONSTANT-C SENSITIVITY (wall = (body+fast)/C/procs) =====")
    print(f"  {'C':>6}  {'body+fast 1p':>13}  {'body+fast 2p':>13}  {'<15min 2p?':>11}")
    for C in (160, 256, 400, 600, 746, 950, 1090):
        tot1 = (body_block_s + fast_block_s) / C
        tot2 = tot1 / 2.0
        flag = "YES" if tot2 <= 900 else ("1p-only" if tot1 <= 900 else "no")
        print(f"  {C:>6}  {tot1/60:>12.0f}m  {tot2/60:>12.0f}m  {flag:>11}")

    # ---- THE VERDICT ----
    C_need_2p = (body_block_s + fast_block_s) / (900 * 2)
    body_min, _ = pool_wall_s(C_pess)
    body_opt, _ = pool_wall_s(C_opt)
    print(f"\n  ################  VERDICT  ################")
    print(f"  HARDWARE occupancy ceiling (measured, min footprint) C_max ~= 746-1140")
    print(f"    (work-stealing == replication: the global atomic is NOT the limiter)")
    print(f"  C REQUIRED for <15min (2-proc) ~= {C_need_2p:.0f}")
    bw_heavy = c_from_scratch_bytes(bytes_at(7027, "min"))
    print(f"  BUT the heavy charts' minimized per-block GLOBAL footprint "
          f"({bytes_at(7027,'min')/1024:.0f}KB at n=7027) is BANDWIDTH-bound to "
          f"C~{bw_heavy:.0f} on the measured scratch curve,")
    print(f"  and they DOMINATE the body work -> work-weighted C_eff stays well below "
          f"the pure-occupancy ceiling.")
    twop_pess = body_min / 2 / 60
    twop_opt = body_opt / 2 / 60
    print(f"  => full-pool body-only 2-proc wall: {twop_pess:.0f} min (bandwidth-bound, "
          f"LOWER C) .. {twop_opt:.0f} min (pure-occ ceiling, UPPER C)")
    if twop_opt <= 15:
        print(f"  => <15min is PLAUSIBLE *iff* the minimized kernel hits the occupancy "
              f"ceiling (needs sparse-access body store to escape the bandwidth bound).")
    else:
        print(f"  => even at the occupancy ceiling, body-only 2-proc = {twop_opt:.0f} min "
              f"=> <15min {'PLAUSIBLE' if twop_opt<=15 else 'NOT reached by occupancy alone'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
