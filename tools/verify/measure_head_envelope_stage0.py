"""Issue #44 Route-A Stage 0 route-decider (CPU only, no Vulkan).

Measures the HEAD parametric upper-envelope size of the early-Great frontier, to decide
whether Route A (build-time head-envelope prune, GPU score path untouched) is viable, or
whether we must fall back to Route B (per-theta head DP in the Vulkan kernel).

Key fact exploited (see docs/FG_EARLY_GREAT_FRONTIER_MATH_PROBLEM.md S5):
  head per-item floor-free value with sigma_i = 1 + (c-1)(i+1)/100 is a LINEAR functional of
  the 8-tuple (count, pos-sum) over each of the 4 (fever?, great?) classes. Two surfaces with
  the same 8-tuple have identical floor-free head value for EVERY theta. So

      |distinct head 8-tuples|  >=  |floor-free head upper envelope|  (an upper bound)

  If that is poly-small (tens..low hundreds, like the body's 319,699 -> 175 collapse), Route A
  wins: prune to it at build time and the cached frontier shrinks back toward pre-#44 size.

Also reports the floor-AWARE argmax envelope over a realistic theta grid (exact §5 scorer) as
the decisive confirmation that the integer floors do not blow the envelope back up.

Run: python tools/verify/measure_head_envelope_stage0.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.solver.timing_envelope import (
    build_perfect_floor_envelope_sec,
    build_great_floor_envelope_sec,
    build_perfect_candidate_envelope_sec,
    build_great_candidate_envelope_sec,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
    build_force_greats_response_first_frontiers_gpu_batch,
)


HEAD_LIMIT = 100


def _build_frontier(timestamps_sec, note_types, geometry):
    """Run the production (current exact early-Great) first-frontier build. Pure CPU/numba."""
    ts = np.ascontiguousarray(np.asarray(timestamps_sec, dtype=np.float32).reshape(-1))
    perfect_floor = build_perfect_floor_envelope_sec(ts, note_types)
    great_floor = build_great_floor_envelope_sec(ts, note_types)
    perfect_cand = build_perfect_candidate_envelope_sec(ts, note_types)
    great_cand = build_great_candidate_envelope_sec(ts, note_types)
    t0 = time.perf_counter()
    results = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=ts,
        perfect_candidate_timestamps=perfect_cand,
        great_candidate_timestamps=great_cand,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        geometries=(geometry,),
        use_forced_great_timing=True,
    )
    build_s = time.perf_counter() - t0
    return results[0].first_frontier, build_s


def _unpack_masks(frontier, head_len):
    """Return (fever_mat, great_mat) boolean S x head_len, plus body-count S x 3."""
    s = len(frontier)
    fever_words = np.empty((s, 4), dtype=np.uint32)
    great_words = np.empty((s, 4), dtype=np.uint32)
    body = np.empty((s, 3), dtype=np.int64)
    for i, surf in enumerate(frontier):
        fever_words[i, 0] = np.uint32(surf.fever0)
        fever_words[i, 1] = np.uint32(surf.fever1)
        fever_words[i, 2] = np.uint32(surf.fever2)
        fever_words[i, 3] = np.uint32(surf.fever3)
        great_words[i, 0] = np.uint32(surf.great0)
        great_words[i, 1] = np.uint32(surf.great1)
        great_words[i, 2] = np.uint32(surf.great2)
        great_words[i, 3] = np.uint32(surf.great3)
        body[i, 0] = int(surf.body_fever)
        body[i, 1] = int(surf.body_great)
        body[i, 2] = int(surf.body_fever_great)
    fever_mat = np.zeros((s, head_len), dtype=bool)
    great_mat = np.zeros((s, head_len), dtype=bool)
    for pos in range(head_len):
        w, b = divmod(pos, 32)
        fever_mat[:, pos] = ((fever_words[:, w] >> np.uint32(b)) & np.uint32(1)).astype(bool)
        great_mat[:, pos] = ((great_words[:, w] >> np.uint32(b)) & np.uint32(1)).astype(bool)
    return fever_mat, great_mat, body


def _eight_tuples(fever_mat, great_mat):
    """Per-surface 8-tuple (count, pos-sum) for each of the 4 (fever?,great?) classes.

    These fully determine the floor-free head value for every theta, so the count of DISTINCT
    8-tuples is an upper bound on the floor-free head upper-envelope size.
    """
    s, h = fever_mat.shape
    pos = np.arange(1, h + 1, dtype=np.int64)[None, :]
    nf = ~fever_mat
    ng = ~great_mat
    classes = {
        "nf_ng": nf & ng,
        "f_ng": fever_mat & ng,
        "nf_g": nf & great_mat,
        "f_g": fever_mat & great_mat,
    }
    cols = []
    for _, m in classes.items():
        cols.append(m.sum(axis=1).astype(np.int64))
        cols.append((m * pos).sum(axis=1).astype(np.int64))
    return np.stack(cols, axis=1)  # S x 8


def _floorfree_envelope(eight, thetas):
    """Distinct argmax surfaces under the floor-free head value over the theta grid.

    Floor-free head value = v*A + vf*B + gamma*C + gammaf*D, and each of A,B,C,D = count +
    (c-1)/100 * pos-sum. So value = coeffs . eight with the 8 coeffs derived from theta.
    """
    won = set()
    for (v, c, f, g) in thetas:
        k = (c - 1.0) / 100.0
        # order: (cnt_nf_ng,pos),(cnt_f_ng,pos),(cnt_nf_g,pos),(cnt_f_g,pos)
        coeffs = np.array([
            v, v * k,
            v * f, v * f * k,
            g, g * k,
            g * f, g * f * k,
        ], dtype=np.float64)
        scores = eight.astype(np.float64) @ coeffs
        won.add(int(np.argmax(scores)))
    return won


def _flooraware_envelope(fever_mat, great_mat, thetas):
    """Distinct argmax surfaces under the EXACT §5 floored head score over the theta grid.

    Memory-light: the per-surface floored head score (mirrors exact_rescore.py:747-759) is, up
    to an additive surface-independent constant,
        fever@dpf - great@a - fevergreat@b
    where per-position H-vectors dpf=pf_f-pf_nf, a=pf_nf-gr_nf, b=(pf_f-gr_f)-(pf_nf-gr_nf).
    Because gamma<=v gives floor(v*sig*) >= floor(gamma*sig*), max(0, base-grv) = base-grv
    exactly, so this is the EXACT floored score (argmax-invariant under the dropped constant).
    Each theta is then three S x H @ H matvecs -- no S x H temporaries.
    """
    fm = fever_mat.astype(np.float64)
    gm = great_mat.astype(np.float64)
    fg = (fever_mat & great_mat).astype(np.float64)
    h = fever_mat.shape[1]
    idx = np.arange(h, dtype=np.float64)
    won = set()
    for (v, c, f, g) in thetas:
        scaling = ((c - 1.0) / 100.0) * (idx + 1.0) + 1.0
        pf_nf = np.floor(v * scaling)
        pf_f = np.floor(v * scaling * f)
        gr_nf = np.floor(g * scaling)
        gr_f = np.floor(g * scaling * f)
        dpf = pf_f - pf_nf
        a = pf_nf - gr_nf
        b = (pf_f - gr_f) - (pf_nf - gr_nf)
        scores = fm @ dpf - gm @ a - fg @ b
        won.add(int(np.argmax(scores)))
    return won


def _theta_grid(rich):
    """rich=True: dense grid for the (cheap) floor-free envelope; rich=False: small confirm grid."""
    vs = (300.0, 900.0, 2500.0) if rich else (900.0,)
    cs = (1.2, 1.5, 2.0, 2.5, 3.0) if rich else (1.5, 2.5)
    fs = (1.05, 1.3, 1.6, 2.0, 3.0, 4.0) if rich else (1.05, 1.6, 3.0)
    ratios = (0.5, 0.65, 0.8, 0.9, 0.97, 1.0) if rich else (0.5, 0.8, 0.97)
    return [(v, c, f, v * r) for v in vs for c in cs for f in fs for r in ratios]


def _report(name, timestamps_sec, note_types, geometry):
    print(f"\n=== {name} (N={len(timestamps_sec)}) ===", flush=True)
    frontier, build_s = _build_frontier(timestamps_sec, note_types, geometry)
    n = len(timestamps_sec)
    head_len = min(n, HEAD_LIMIT)
    print(f"  full frontier surfaces : {len(frontier):>8}   (build {build_s:.2f}s)", flush=True)
    fever_mat, great_mat, body = _unpack_masks(frontier, head_len)
    eight = _eight_tuples(fever_mat, great_mat)
    distinct8 = np.unique(eight, axis=0).shape[0]
    body_classes = np.unique(body, axis=0).shape[0]
    print(f"  distinct head 8-tuples : {distinct8:>8}   <-- upper bound on floor-free head envelope", flush=True)
    print(f"  distinct body classes  : {body_classes:>8}", flush=True)
    rich = _theta_grid(rich=True)
    ff_env = _floorfree_envelope(eight, rich)
    print(f"  floor-free argmax env  : {len(ff_env):>8}   (over {len(rich)} theta)", flush=True)
    confirm = _theta_grid(rich=False)
    fa_env = _flooraware_envelope(fever_mat, great_mat, confirm)
    print(f"  floor-AWARE argmax env : {len(fa_env):>8}   (over {len(confirm)} theta)", flush=True)
    keep = max(distinct8, len(fa_env))
    print(f"  => Route-A frontier ~  : {keep:>8}   ({keep / max(1, len(frontier)) * 100:.2f}% of full)", flush=True)
    return len(frontier), distinct8, len(fa_env)


def main():
    # Realistic short all-head song: non-uniform gaps (varied note timing) + held tails. Kept
    # small (N=52) -- non-uniform timing widens the early-Great cascade far more than uniform, so
    # this stays buildable while still exercising irregular geometry. (The uniform N=40..80 sweep
    # already showed envelope ~4-7 vs frontier up to 247k; this confirms it off-grid.)
    rng = np.random.default_rng(44)
    gaps = rng.choice([0.090, 0.120, 0.150, 0.180, 0.240, 0.300], size=51)
    t_real = np.concatenate([[0.0], np.cumsum(gaps)]).astype(np.float32)  # N=52
    nt = np.ones(t_real.shape[0], dtype=np.int16)
    nt[rng.choice(t_real.shape[0], size=13, replace=False)] = 3  # ~25% held tails
    _report("realistic short all-head", t_real, nt, (2.0, 4, 0.5))


if __name__ == "__main__":
    main()
