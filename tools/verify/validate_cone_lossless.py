"""Definitive losslessness check for the njit cone-dominance head prune.

For a worst-case early-Great cascade, build the production cone-dominance frontier (filter ON) and
the full reduce-only frontier (filter OFF), then score BOTH with the exact floored scorer over a
dense realizable (v,c,f,g) grid. Since cone_dom is a subset of reduce_only, max(cone_dom,cell) <=
max(reduce_only,cell) always; LOSSLESS iff they are EQUAL at every cell. Any cell with a strictly
lower cone_dom max names a dropped winner (a bug in the prune).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba as B
from tools.verify.measure_head_envelope_stage0 import _build_frontier, _unpack_masks, HEAD_LIMIT


def _floored_max(fever_mat, great_mat, body, body_total, cells):
    """Max exact floored score over surfaces, per cell. Realizable region (g<=v) -> great penalty is
    perfect-min-great with no clamp; body penalties likewise inactive."""
    s, h = fever_mat.shape
    idx = np.arange(h, dtype=np.float64)
    fm = fever_mat.astype(np.float64); gm = great_mat.astype(np.float64)
    fgm = (fever_mat & great_mat).astype(np.float64)
    bf = body[:, 0].astype(np.float64); bg = body[:, 1].astype(np.float64); bfg = body[:, 2].astype(np.float64)
    bn = body_total - bf; bng = bg - bfg
    out = np.empty(len(cells), dtype=np.float64)
    for ci, (v, c, f, g) in enumerate(cells):
        sig = 1.0 + (c - 1.0) / 100.0 * (idx + 1.0)
        pf_nf = np.floor(v * sig); pf_f = np.floor(v * sig * f)
        gr_nf = np.floor(g * sig); gr_f = np.floor(g * sig * f)
        # per-position: great? gr : pf ; fever picks the *_f variant. h_i = pf - great*(pf-gr).
        dpf = pf_f - pf_nf                    # fever gain on perfect
        a = pf_nf - gr_nf                     # great penalty, non-fever
        bvec = (pf_f - gr_f) - (pf_nf - gr_nf)
        const = float(pf_nf.sum())
        head = const + fm @ dpf - gm @ a - fgm @ bvec
        cv = np.floor(v * c); fv = np.floor(v * c * f)
        pnp = max(0.0, cv - np.floor(g * c)); pfp = max(0.0, fv - np.floor(g * c * f))
        bodyv = bf * fv + bn * cv - bng * pnp - bfg * pfp
        out[ci] = float((head + bodyv).max())
    return out


def _grid():
    return [(v, c, f, g)
            for v in (250.0, 700.0, 1500.0, 3000.0, 5500.0, 7800.0)
            for c in (2.0, 2.2, 2.45, 2.67)
            for f in (3.0, 3.6, 4.3, 5.0, 5.42)
            for g in (160.0, 0.45, 0.62, 0.78, 0.95)]  # g as ratio*v when <1, else absolute


def _resolve_cells():
    cells = []
    for (v, c, f, gp) in _grid():
        g = gp if gp >= 1.0 else gp * v
        if g <= v:  # realizable region only
            cells.append((v, c, f, g))
    return cells


def _check(name, ts, nt, geometry):
    n = len(ts); head_len = min(n, HEAD_LIMIT); body_total = max(0, n - HEAD_LIMIT)
    orig = B._HEAD_FILTER_MIN_SURFACES
    fr_on, _ = _build_frontier(ts, nt, geometry)               # cone-dominance (production)
    B._HEAD_FILTER_MIN_SURFACES = 10 ** 18
    fr_off, _ = _build_frontier(ts, nt, geometry)              # full reduce-only
    B._HEAD_FILTER_MIN_SURFACES = orig
    fm_on, gm_on, b_on = _unpack_masks(fr_on, head_len)
    fm_off, gm_off, b_off = _unpack_masks(fr_off, head_len)
    cells = _resolve_cells()
    max_on = _floored_max(fm_on, gm_on, b_on, body_total, cells)
    max_off = _floored_max(fm_off, gm_off, b_off, body_total, cells)
    gap = max_off - max_on
    worst = float(gap.max())
    nbad = int((gap > 0.5).sum())
    print(f"\n=== {name} (N={n}): cone_dom={len(fr_on)} reduce_only={len(fr_off)} cells={len(cells)} ===", flush=True)
    if nbad == 0:
        print(f"  LOSSLESS: max(cone_dom)==max(reduce_only) at all {len(cells)} cells (worst gap {worst:.1f})", flush=True)
    else:
        bi = int(np.argmax(gap))
        print(f"  *** LOSSY: {nbad}/{len(cells)} cells under-report. worst gap {worst:.0f} at cell {cells[bi]} "
              f"(cone={max_on[bi]:.0f} reduce={max_off[bi]:.0f})", flush=True)
    return nbad


def main():
    rng = np.random.default_rng(44)
    gaps = rng.choice([0.090, 0.120, 0.150, 0.180, 0.240, 0.300], size=51)
    t_real = np.concatenate([[0.0], np.cumsum(gaps)]).astype(np.float32)
    nt = np.ones(t_real.shape[0], dtype=np.int16)
    nt[rng.choice(t_real.shape[0], size=13, replace=False)] = 3
    bad = _check("realistic short all-head", t_real, nt, (2.0, 4, 0.5))
    t_uni = (np.arange(80, dtype=np.float32) * 0.040)
    bad += _check("uniform-40ms N=80 (S10)", t_uni, np.ones(80, dtype=np.int16), (2.0, 4, 0.5))
    print(f"\n=> {'ALL LOSSLESS' if bad == 0 else f'{bad} LOSSY CELLS — BUG'}", flush=True)


if __name__ == "__main__":
    main()
