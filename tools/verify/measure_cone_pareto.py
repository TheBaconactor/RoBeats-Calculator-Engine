"""De-risk the lossless 16-corner head dominance: how big is the TRUE cone-Pareto frontier?

For a worst-case early-Great cascade, build the full reduce-only frontier (filter OFF via the
runtime size-gate toggle), then count surfaces that survive the closed-form multilinear dominance:
K dominates C iff unfloored_score(K) - unfloored_score(C) >= per-pair floor-margin at all 16 corners
of the realizable (v,c,f,g) stat box. Compare to the lossy probe filter's output.

If cone-Pareto ~ filter output (small), the lossless prune is bounded -> ship it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba as B
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
from gear_optimizer.data.csv_parser import read_table
from tools.verify.measure_head_envelope_stage0 import _build_frontier, _unpack_masks, HEAD_LIMIT


def _scores_at_corners(fever_mat, great_mat, body, corners):
    """(S, n_corners) unfloored multilinear score. head = v*A + (g-v)*C + v(f-1)*B + (g-v)(f-1)*D
    with A=sum sigma_i, B=sum sigma_i*fever, C=sum sigma_i*great, D=sum sigma_i*great*fever;
    body = bf*v*c*f + bn*v*c - bng*c*(v-g) - bfg*c*f*(v-g)."""
    s, h = fever_mat.shape
    idx = np.arange(1, h + 1, dtype=np.float64)
    fm = fever_mat.astype(np.float64); gm = great_mat.astype(np.float64); fgm = (fever_mat & great_mat).astype(np.float64)
    bf = body[:, 0].astype(np.float64); bg = body[:, 1].astype(np.float64); bfg = body[:, 2].astype(np.float64)
    body_total = float(body[:, 0].max()) if s else 0.0  # not used; body_total passed via geometry below
    out = np.empty((s, len(corners)), dtype=np.float64)
    for ci, (v, c, f, g, body_total) in enumerate(corners):
        sigma = 1.0 + (c - 1.0) / 100.0 * idx
        A = float(sigma.sum())
        Bc = fm @ sigma; Cc = gm @ sigma; Dc = fgm @ sigma
        head = v * A + (g - v) * Cc + v * (f - 1.0) * Bc + (g - v) * (f - 1.0) * Dc
        bn = body_total - bf; bng = bg - bfg
        bodyv = bf * (v * c * f) + bn * (v * c) - bng * (c * (v - g)) - bfg * (c * f * (v - g))
        out[:, ci] = head + bodyv
    return out


def _cone_pareto_survivors(fever_mat, great_mat, body, body_total, box):
    """INCREMENTAL cone-Pareto (the real-impl shape): O(S * kept), fast even when S is large.
    K dominates C iff unfloored score(K)-score(C) >= per-pair floor-margin at all 16 box corners."""
    (v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi) = box
    corners = [(v, c, f, g, body_total)
               for v in (v_lo, v_hi) for c in (c_lo, c_hi) for f in (f_lo, f_hi) for g in (g_lo, g_hi)]
    scores = _scores_at_corners(fever_mat, great_mat, body, corners)  # (S, 16)
    s = fever_mat.shape[0]
    bf = body[:, 0].astype(np.int64); bg = body[:, 1].astype(np.int64); bfg = body[:, 2].astype(np.int64)
    bn = body_total - bf; bng = bg - bfg

    def margin(a, b):
        return float(int(((fever_mat[a] ^ fever_mat[b]) | (great_mat[a] ^ great_mat[b])).sum())
                     + abs(int(bf[a] - bf[b])) + abs(int(bn[a] - bn[b]))
                     + abs(int(bng[a] - bng[b])) + abs(int(bfg[a] - bfg[b])))

    kept: list[int] = []
    for i in range(s):
        si = scores[i]
        if any(bool((scores[k] - si >= margin(i, k)).all()) for k in kept):
            continue  # i dominated -> drop, kept unchanged
        kept = [k for k in kept if not bool((si - scores[k] >= margin(i, k)).all())]
        kept.append(i)
    return len(kept)


def _measure(name, ts, nt, geometry, boxes, labels):
    n = len(ts); head_len = min(n, HEAD_LIMIT); body_total = max(0, n - HEAD_LIMIT)
    print(f"\n=== {name} (N={n}, head_len={head_len}, body_total={body_total}) building filter-OFF ...", flush=True)
    orig = B._HEAD_FILTER_MIN_SURFACES
    B._HEAD_FILTER_MIN_SURFACES = 10 ** 18
    fr_off, t_off = _build_frontier(ts, nt, geometry)
    B._HEAD_FILTER_MIN_SURFACES = orig
    print(f"  reduce-only (filter OFF) : {len(fr_off):>7}  (build {t_off:.2f}s)", flush=True)
    fm, gm, body = _unpack_masks(fr_off, head_len)
    for lab, bx in zip(labels, boxes):
        surv = _cone_pareto_survivors(fm, gm, body, body_total, bx)
        print(f"  cone-Pareto [{lab:16}]: {surv:>7}   [LOSSLESS]", flush=True)
    fr_on, t_on = _build_frontier(ts, nt, geometry)
    print(f"  probe filter (filter ON) : {len(fr_on):>7}  (build {t_on:.2f}s)   [LOSSY]", flush=True)


def main():
    ref = build_ref_arrays_from_stats(read_table("Data/Gear/Stats.txt"), dtype=np.float64)
    cm = np.asarray(ref["Combo Multiplier"]); fmul = np.asarray(ref["Fever Multiplier"])
    c_lo, c_hi = float(cm.min()), float(cm.max())
    f_lo, f_hi = float(fmul.min()), float(fmul.max())
    # realizable box variants (v=base_value, g=great_base); generous superset vs competitive cone
    full = (200.0, 5000.0, c_lo, c_hi, f_lo, f_hi, 150.0, 3500.0)
    comp = (1000.0, 5000.0, c_lo, c_hi, f_lo, f_hi, 600.0, 3500.0)
    labels = ["full v>=200", "competitive v>=1k"]
    boxes = [full, comp]
    print(f"realizable: c in [{c_lo:.2f},{c_hi:.2f}]  f in [{f_lo:.2f},{f_hi:.2f}]", flush=True)

    rng = np.random.default_rng(44)
    gaps = rng.choice([0.090, 0.120, 0.150, 0.180, 0.240, 0.300], size=51)
    t_real = np.concatenate([[0.0], np.cumsum(gaps)]).astype(np.float32)
    nt = np.ones(t_real.shape[0], dtype=np.int16)
    nt[rng.choice(t_real.shape[0], size=13, replace=False)] = 3
    _measure("realistic short all-head", t_real, nt, (2.0, 4, 0.5), boxes, labels)

    # uniform 40ms worst case (docs S10)
    t_uni = (np.arange(80, dtype=np.float32) * 0.040)
    nt_uni = np.ones(80, dtype=np.int16)
    _measure("uniform-40ms N=80 (S10)", t_uni, nt_uni, (2.0, 4, 0.5), boxes, labels)


if __name__ == "__main__":
    main()
