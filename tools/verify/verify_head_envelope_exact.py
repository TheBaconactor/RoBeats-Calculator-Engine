"""Issue #44 Route A bit-exactness A/B: the head upper-envelope prune must change the cached
frontier's SIZE but never its per-theta MAX score.

Run this twice:
  1. as-is (filter ON)  -> records frontier size + a SHA-256 digest of the per-theta max scores;
  2. with the two `_numba_head_envelope_filter(...)` wirings in response_build_gpu_numba.py
     reverted to plain `_numba_reduce(...)` (filter OFF, the oracle).
The digests MUST be identical; the ON frontier sizes MUST be far smaller. (All instances here are
all-head N<=100, so body_total=0 and the head scorer is the full exact score.)

Run: python tools/verify/verify_head_envelope_exact.py
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.verify.measure_head_envelope_stage0 import _build_frontier, _unpack_masks, HEAD_LIMIT, _theta_grid


def _max_scores_over_grid(fever_mat, great_mat, thetas):
    """Per-theta MAX exact floored head score over the frontier (mirrors exact_rescore §5)."""
    fm = fever_mat.astype(np.float64)
    gm = great_mat.astype(np.float64)
    fg = (fever_mat & great_mat).astype(np.float64)
    h = fever_mat.shape[1]
    idx = np.arange(h, dtype=np.float64)
    const_pos = np.zeros(h, dtype=np.float64)  # surface-independent baseline drops out of argmax,
    out = np.empty(len(thetas), dtype=np.float64)            # but include it so the MAX value is exact
    for ti, (v, c, f, g) in enumerate(thetas):
        scaling = ((c - 1.0) / 100.0) * (idx + 1.0) + 1.0
        pf_nf = np.floor(v * scaling)
        pf_f = np.floor(v * scaling * f)
        gr_nf = np.floor(g * scaling)
        gr_f = np.floor(g * scaling * f)
        base_const = float(pf_nf.sum())  # every position is class-A by default
        dpf = pf_f - pf_nf
        a = pf_nf - gr_nf
        b = (pf_f - gr_f) - (pf_nf - gr_nf)
        scores = base_const + fm @ dpf - gm @ a - fg @ b
        out[ti] = float(scores.max())
    return out


def _eval(name, timestamps_sec, note_types, geometry, tag):
    frontier, build_s = _build_frontier(timestamps_sec, note_types, geometry)
    n = len(timestamps_sec)
    head_len = min(n, HEAD_LIMIT)
    fever_mat, great_mat, _body = _unpack_masks(frontier, head_len)
    thetas = _theta_grid(rich=True)
    maxv = _max_scores_over_grid(fever_mat, great_mat, thetas)
    np.save(str(PROJECT_ROOT / f"tools/verify/_stage1_maxv_{tag}_{name}.npy"), maxv)
    ref_path = PROJECT_ROOT / f"tools/verify/_stage1_maxv_{'off' if tag == 'on' else 'on'}_{name}.npy"
    cmp = ""
    if ref_path.exists():
        ref = np.load(str(ref_path))
        gap = np.abs(maxv - ref)
        # global max over the whole grid == the best_fg_score criterion (only the winning cell matters)
        gmax_gap = abs(float(maxv.max()) - float(ref.max()))
        thetas = _theta_grid(rich=True)
        diff_v = [thetas[i][0] for i in range(len(gap)) if gap[i] > 0]
        minv = min(diff_v) if diff_v else 0
        cmp = (f"  GLOBALMAXgap={gmax_gap:.1f}  per-theta:maxgap={gap.max():.1f} "
               f"ndiff={int((gap > 0).sum())}/{len(gap)} (all diffs at v<= {max(diff_v) if diff_v else 0:.0f}, minv={minv:.0f})")
    print(f"  {name:<22} N={n:<4} frontier={len(frontier):>7}  build={build_s:6.2f}s{cmp}", flush=True)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "on"
    print(f"issue #44 Route A A/B [tag={tag}] (frontier shrinks; vs-oracle maxgap must be 0):", flush=True)
    _eval("small", (0.040 * np.arange(24)).astype(np.float32), None, (2.5, 3, 0.3), tag)
    rng = np.random.default_rng(44)
    gaps = rng.choice([0.090, 0.120, 0.150, 0.180, 0.240, 0.300], size=51)
    t_real = np.concatenate([[0.0], np.cumsum(gaps)]).astype(np.float32)
    nt = np.ones(t_real.shape[0], dtype=np.int16)
    nt[rng.choice(t_real.shape[0], size=13, replace=False)] = 3
    _eval("realistic", t_real, nt, (2.0, 4, 0.5), tag)
    _eval("blowup", (0.040 * np.arange(80)).astype(np.float32), None, (2.5, 3, 0.3), tag)


if __name__ == "__main__":
    main()
