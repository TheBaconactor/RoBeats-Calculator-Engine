"""THE HEADLINE (mission task #c), final arithmetic over the MEASURED anchors.

All inputs below are MEASURED in this session (read-only dev harnesses, GPU = parallel-
skyline block-per-key kernel on RX 7900 XTX, Taichi 1.7.4 ti.vulkan):
  - frac_bd(n)  : ACTUAL body-DP fraction over the full 161x161=25,921 grid, from the
                  EXACT producer early-out predicate (`_fg_fastpath_reconcile.py` /
                  `_fg_pool_projection_corrected.py`); verified == real producer se==0.
  - mean_W(n)   : mean UNCONTESTED single-block wall (launch=1) over a representative
                  body-DP-cell sample incl the heavy low-ft band (`_corr` run).
  - fp_pk(n)    : saturated fast-path ms/key over a 512-cell tiled launch
                  (`_fg_fastpath_cost.py`); the production O(n*ac) early-out cost.
  - C           : measured concurrent-block capacity (`_fg_concurrency_probe.py`),
                  implied-C ~150-186 -> use 160 (mid), sensitivity 96/160/256/384.

Saturated model (mission): wall ~= total_block_work / C. Per chart:
  body_ms(n)  = frac_bd(n) * 25,921 * (mean_W(n) / C)        [scales 1/C]
  fast_ms(n)  = (1-frac_bd(n)) * 25,921 * fp_pk_sat(n)        [fast-path early-out]
Integrate over the real 2,238-chart note histogram. 2 production GPU procs -> /2.

Run: python tools/dev/_fg_headline.py
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

CELLS = (TOTAL_ROWS + 1) ** 2  # 25,921 (measured: no grid collapse, _fg_distinct_keys)
C_BLOCKS = 160                 # measured concurrent-block capacity (mid of 150-186)

# ---- MEASURED anchors (this session) ----
# (n, frac_bd, mean_W ms [single-block uncontested], fp_pk ms/key [saturated 512-launch])
ANCHORS = [
    (61,   1.000,    1.54,  float("nan")),
    (300,  1.000,    2.90,  float("nan")),
    (653,  0.801,    7.60,   7.64484),
    (1083, 0.639,   15.95,   9.52969),
    (1655, 0.453,   51.02,  float("nan")),
    (2312, 0.160,  216.03,  15.87963),
    (3522, 0.589,  179.55,  float("nan")),
    (4722, 0.506,  448.01,  39.77851),
    (6843, 0.421, 2118.95,  float("nan")),
    (7027, 0.336, 3510.86,  63.38227),
]


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    rgm = _load("rgv_hl", "_fg_real_grid_validate.py")
    sc = rgm.scan_note_counts()
    pool_ns = np.array([c for c, _ in sc], dtype=float)
    print(f"  pool charts={len(pool_ns)} cells/chart={CELLS} (no collapse)  "
          f"total cells={len(pool_ns)*CELLS/1e6:.1f}M")
    print(f"  pool n: min={pool_ns.min():.0f} median={np.median(pool_ns):.0f} "
          f"p90={np.percentile(pool_ns,90):.0f} p99={np.percentile(pool_ns,99):.0f} max={pool_ns.max():.0f}")

    ns = np.array([a[0] for a in ANCHORS], float)
    fbd = np.array([a[1] for a in ANCHORS], float)
    mW = np.array([a[2] for a in ANCHORS], float)
    fpk = np.array([a[3] for a in ANCHORS], float)

    # fit mean_W ~ a*n^p (body single-block work) over body-bearing anchors n>=150
    mb = ns >= 150
    pb = np.polyfit(np.log(ns[mb]), np.log(mW[mb]), 1)
    W_a, W_p = math.exp(pb[1]), pb[0]
    # fast-path: a*n^p over finite anchors
    mf = np.isfinite(fpk) & (ns >= 150)
    pf = np.polyfit(np.log(ns[mf]), np.log(fpk[mf]), 1)
    fp_a, fp_p = math.exp(pf[1]), pf[0]
    # frac_bd interp on n
    order = np.argsort(ns); ns_s, fbd_s = ns[order], fbd[order]

    def frac_bd_at(x):
        return float(np.interp(x, ns_s, fbd_s, left=fbd_s[0], right=fbd_s[-1]))

    print(f"\n  mean_W fit (single-block) = {W_a:.3e} * n^{W_p:.3f}  ms")
    print(f"  fast-path fit (saturated) = {fp_a:.3e} * n^{fp_p:.3f}  ms/key")

    est_W = np.maximum(W_a * np.power(pool_ns, W_p), float(mW[mb].min()))
    est_fp = np.maximum(fp_a * np.power(pool_ns, fp_p), float(fpk[mf].min()))
    fr = np.array([frac_bd_at(x) for x in pool_ns])

    # body single-block work (C-independent) -> block-seconds, then /C for wall
    body_block_s = (fr * CELLS * est_W).sum() / 1000.0      # total block-seconds of body work
    fast_block_s = ((1 - fr) * CELLS * est_fp).sum() / 1000.0  # fast-path ms/key already amortized

    print(f"\n  total BODY single-block work (Sigma over pool, C-independent) : "
          f"{body_block_s/60:8.0f} block-min  ({body_block_s/3600:.1f} block-hr)")
    print(f"  total FAST-PATH work (saturated ms/key * cells)               : "
          f"{fast_block_s/60:8.0f} min")

    print(f"\n  ===== SATURATED FULL-POOL WALL (wall = work / C) =====")
    print(f"  {'C':>5}  {'body 1p':>8}  {'body+fast 1p':>13}  {'body+fast 2p':>13}  {'<15min?':>9}")
    for Cp in (96, 160, 256, 384):
        body_s = body_block_s / Cp
        # fast-path is also block-parallel in a GPU build -> /C (conservative: the
        # measured fp_pk already reflects a 512-thread launch; treat as /C upper bound).
        fast_s = fast_block_s / Cp
        tot1 = body_s + fast_s
        tot2 = tot1 / 2.0
        body_only_2p = body_s / 2.0
        flag = "YES" if tot2 <= 900 else "no"
        print(f"  {Cp:>5}  {body_s/60:>7.0f}m  {tot1/60:>12.0f}m  {tot2/60:>12.0f}m  {flag:>9}  "
              f"(body-only 2p {body_only_2p/60:.0f}m)")

    body_s160 = body_block_s / C_BLOCKS
    fast_s160 = fast_block_s / C_BLOCKS
    tot2_160 = (body_s160 + fast_s160) / 2.0
    print(f"\n  ---- targets ----   <15min = 900 s ;  CPU baseline = 1860 s (~31 min)")
    print(f"\n  HEADLINE (C=160): body-only 2-proc = {body_s160/2/60:.0f} min ; "
          f"body+fast 2-proc = {tot2_160/60:.0f} min")
    print(f"  -> {'REACHES' if tot2_160 <= 900 else 'DOES NOT reach'} <15min "
          f"(over by {tot2_160/900:.1f}x even body-only 2p={body_s160/2/900:.1f}x)")
    heavy = pool_ns >= 2000
    body_per_chart = fr * CELLS * est_W
    print(f"\n  charts n>=2000: {int(heavy.sum())}/{len(pool_ns)} but "
          f"{body_per_chart[heavy].sum()/body_per_chart.sum()*100:.0f}% of BODY work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
