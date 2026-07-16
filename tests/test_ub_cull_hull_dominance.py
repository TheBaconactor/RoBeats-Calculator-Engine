"""CPU-only soundness proof for the coupled GA combo-cull upper bound (Design 1).

This module runs WITHOUT Taichi / a GPU. It proves the two soundness facts the on-device
sweep cannot cheaply enumerate at scale:

1. Concave-envelope construction (`concave_hull.build_upper_concave_hull_segments`) yields a
   concave, dominating (>= LUT), monotone envelope, and fails loud on a LUT that is not
   monotone non-decreasing with endpoint == argmax (the single most load-bearing soundness
   fact per docs/Implementation Records/UB_CULL_BOUND_DESIGN.md section 4).

2. A pure-NumPy float32 replica of the whole tightened bound satisfies
       UB_gate >= exact_all_fever_combo   AND   UB_gate <= old_bound
   over a broad randomized sweep of reachable inputs plus the structured corners the design
   record calls out (base-saturated, all-OV, no-OV/Delta=0, budget=0, large N at high
   magnitude). The exact reference is the all-fever combo score maximised over every feasible
   (g_pp, g_cm, g_fm, g_ov) allocation; the all-fever aggregate upper-bounds every real
   frontier variant, so it is the tightest thing the relaxed bound directly dominates.

The replica mirrors the kernel's f32 associations exactly (see `_coupled_ub_fm/_cm` and
`response_score_upper_bound_relaxed` in kernels/kernels_scoring.py). It cannot certify the
final ~1-2 ULP of Vulkan rounding order — that is the job of the on-device sweep in
tests/test_gpu_ub_cull_bound_property.py (design section 4 residual). Here we certify the
algebra: floors dropped upward, hull dominance, and the folded association.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.concave_hull import (
    HULL_STAT_MAX,
    MAX_CONCAVE_HULL_SEGMENTS,
    build_upper_concave_hull_segments,
    eval_hull_at,
)

_MAX_STAT = HULL_STAT_MAX  # 160
_UB_EPS = np.float32(1024.0)
_GEM_SCALE_NORMAL = 2
_GEM_SCALE_FEVER = 3
_ELEMENTAL_GEM_SCALE = 6
_GEM_STAT_TO_ELEMENT = 3
_ROWS = _MAX_STAT + 1


# --------------------------------------------------------------------------------------------
# Synthetic + real reference LUTs
# --------------------------------------------------------------------------------------------
def _concave_lut(lo: float, hi: float) -> np.ndarray:
    """Monotone increasing, strictly concave (diminishing returns) LUT like the real CM/FM."""
    t = np.linspace(0.0, 1.0, _ROWS)
    return (lo + (hi - lo) * (2.0 * t - t * t)).astype(np.float64)


def _synthetic_refs() -> dict[str, np.ndarray]:
    return {
        "Perfect Points": _concave_lut(200.0, 485.0),
        "Combo Multiplier": _concave_lut(2.0, 2.67),
        "Fever Multiplier": _concave_lut(3.0, 5.425),
    }


def _real_refs_or_none() -> dict[str, np.ndarray] | None:
    path = Path(__file__).resolve().parents[1] / "Data" / "Gear" / "Stats.txt"
    if not path.exists():
        return None
    raw = np.loadtxt(path, skiprows=1)
    if raw.shape[0] != _ROWS:
        return None
    # File is ordered from max stat (index 160) down to 0; reverse to ascending stat index.
    return {
        "Perfect Points": raw[:, 0][::-1].copy(),
        "Combo Multiplier": raw[:, 1][::-1].copy(),
        "Fever Multiplier": raw[:, 2][::-1].copy(),
    }


# --------------------------------------------------------------------------------------------
# Hull property tests
# --------------------------------------------------------------------------------------------
def _assert_hull_props(segs: np.ndarray, lut: np.ndarray, name: str) -> None:
    assert segs.shape[1] == 4
    assert segs.shape[0] <= MAX_CONCAVE_HULL_SEGMENTS
    assert segs[0, 0] == 0.0 and segs[-1, 1] == float(_MAX_STAT)
    assert np.allclose(segs[1:, 0], segs[:-1, 1]), f"{name} not contiguous"
    assert np.all(np.diff(segs[:, 2]) <= 1e-6), f"{name} not concave"
    # Dominance evaluated on the returned float32 segment params (as uploaded/read on device):
    # the only deficits are sub-ULP at the envelope's touch points (identical to reading the LUT
    # itself in f32) and are absorbed by UB_EPS. The on-device sweep certifies the remaining ULPs.
    hull = eval_hull_at(segs.astype(np.float32), np.arange(_ROWS, dtype=np.float64))
    assert np.all(hull >= lut - 1e-5), f"{name} f32 dominance violated (max deficit {(lut - hull).max()})"


@pytest.mark.parametrize("name", ["Combo Multiplier", "Fever Multiplier"])
def test_synthetic_hull_is_concave_dominating(name: str) -> None:
    lut = _synthetic_refs()[name]
    segs = build_upper_concave_hull_segments(lut, name)
    _assert_hull_props(segs, lut, name)


def test_real_stats_hull_is_concave_dominating() -> None:
    refs = _real_refs_or_none()
    if refs is None:
        pytest.skip("Data/Gear/Stats.txt not available or unexpected shape")
    for name in ("Combo Multiplier", "Fever Multiplier"):
        lut = refs[name]
        segs = build_upper_concave_hull_segments(lut, name)
        _assert_hull_props(segs, lut, name)
        # Float32 dominance (as uploaded/evaluated on device): any deficit is sub-ULP at the
        # envelope's touch points, identical to evaluating the LUT itself in f32, and absorbed
        # by UB_EPS. Assert it stays within a tight tolerance (the on-device sweep certifies the
        # remaining ULPs of the folded product).
        xs = np.arange(_ROWS, dtype=np.float32)
        s32 = segs.astype(np.float32)
        idx = np.clip(np.searchsorted(s32[:, 0], xs, side="right") - 1, 0, s32.shape[0] - 1)
        hull32 = (s32[idx, 2] * xs + s32[idx, 3]).astype(np.float32)
        deficit = lut.astype(np.float32) - hull32
        assert deficit.max() < 1e-5, f"{name} f32 hull deficit {deficit.max()} too large"


def test_non_monotone_lut_fails_loud() -> None:
    lut = _concave_lut(2.0, 2.67)
    lut[100] = lut[99] - 0.05  # inject a decrease
    with pytest.raises(ValueError, match="monotone"):
        build_upper_concave_hull_segments(lut, "broken")


def test_interior_peak_lut_fails_loud() -> None:
    # A LUT that peaks in the interior and declines is non-monotone -> must fail loud, because
    # pinning the off-axis factor at the endpoint corner would then under-estimate.
    lut = _concave_lut(2.0, 2.67)
    lut[130:] = lut[130]  # plateau top (still monotone, ok)
    segs = build_upper_concave_hull_segments(lut, "plateau")  # should NOT raise
    _assert_hull_props(segs, lut, "plateau")
    lut2 = _concave_lut(2.0, 2.67)
    lut2[140:] = np.linspace(lut2[140], lut2[140] - 0.1, _ROWS - 140)  # declining tail
    with pytest.raises(ValueError):
        build_upper_concave_hull_segments(lut2, "declining")


# --------------------------------------------------------------------------------------------
# Float32 replica of the tightened bound and the exact all-fever reference
# --------------------------------------------------------------------------------------------
def _clamp_stat(x: int) -> int:
    return int(min(_MAX_STAT, max(0, x)))


def _weights(flags: tuple[int, ...]) -> tuple[int, int, int, int, int]:
    is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov = flags
    w_pp = ((_GEM_STAT_TO_ELEMENT * is_p_pp) << 1) + _GEM_STAT_TO_ELEMENT * is_s_pp
    w_cm = ((_GEM_STAT_TO_ELEMENT * is_p_cm) << 1) + _GEM_STAT_TO_ELEMENT * is_s_cm
    w_fm = ((_GEM_STAT_TO_ELEMENT * is_p_fm) << 1) + _GEM_STAT_TO_ELEMENT * is_s_fm
    w_ov = ((_ELEMENTAL_GEM_SCALE * is_p_ov) << 1) + _ELEMENTAL_GEM_SCALE * is_s_ov
    w_max = max(w_pp, w_cm, w_fm, w_ov)
    return w_pp, w_cm, w_fm, w_ov, w_max


def _f32(x) -> np.float32:
    return np.float32(x)


def _old_bound(p: dict, refpp, refcm, reffm) -> np.float32:
    """Mirror the pre-existing response_score_upper_bound_relaxed (current bound arm)."""
    budget = p["budget"]
    w_pp, w_cm, w_fm, w_ov, w_max = _weights(p["flags"])
    pp_stat = _clamp_stat(p["cur_pp"] + budget * _GEM_SCALE_NORMAL)
    cm_stat = _clamp_stat(p["cur_cm"] + budget * _GEM_SCALE_NORMAL)
    fm_stat = _clamp_stat(p["cur_fm"] + budget * _GEM_SCALE_FEVER)
    base_lane = (p["cur_p_val"] << 1) + p["cur_s_val"] + budget * w_max
    b0 = _f32(_f32(base_lane) + refpp[pp_stat])
    c = _f32(refcm[cm_stat])
    f = _f32(reffm[fm_stat])
    ln = min(max(p["head_len"], 0), 100)
    sigma = (ln * (ln + 1)) // 2
    n = max(0, p["body_total"])
    fever_val = np.int64(np.trunc(_f32(_f32(b0 * c) * f)))
    body = np.int64(n) * fever_val
    factor = _f32(_f32((c - _f32(1.0)) * b0) / _f32(100.0))
    head_upper = _f32(
        _f32(b0 * (_f32(0.0) + f * _f32(ln))) + _f32(factor * (_f32(0.0) + f * _f32(sigma)))
    )
    return _f32(_f32(np.float32(body)) + head_upper + _UB_EPS)


def _coupled_fm(b0, inner_fm, delta_f, cur_fm, budget, fm_segs) -> np.float32:
    budget_nn = max(0, budget)
    s_lo = _f32(_clamp_stat(cur_fm))
    s_hi = _f32(_clamp_stat(cur_fm + budget_nn * _GEM_SCALE_FEVER))
    cur_fm_f = _f32(cur_fm)
    m_f = _f32(_f32(delta_f) / _f32(_GEM_SCALE_FEVER))
    best = _f32(-1.0e30)
    for lo, hi, slope, icpt in fm_segs:
        lo, hi, slope, icpt = _f32(lo), _f32(hi), _f32(slope), _f32(icpt)
        a = max(lo, s_lo)
        b = min(hi, s_hi)
        if a <= b:
            def ev(s):
                bb = _f32(b0 - m_f * (s - cur_fm_f))
                ff = _f32(slope * s + icpt)
                return _f32(_f32(bb * ff) * inner_fm)

            cand = max(ev(a), ev(b))
            lead = _f32(m_f * slope)
            if lead > _f32(0.0):
                bhat = _f32(b0 + m_f * cur_fm_f)
                sv = _f32((bhat * slope - m_f * icpt) / (_f32(2.0) * lead))
                if a < sv < b:
                    cand = max(cand, ev(sv))
            best = max(best, cand)
    return best


def _coupled_cm(b0, fstar, a2, a1, delta_c, cur_cm, budget, cm_segs) -> np.float32:
    budget_nn = max(0, budget)
    s_lo = _f32(_clamp_stat(cur_cm))
    s_hi = _f32(_clamp_stat(cur_cm + budget_nn * _GEM_SCALE_NORMAL))
    cur_cm_f = _f32(cur_cm)
    m_c = _f32(_f32(delta_c) / _f32(_GEM_SCALE_NORMAL))
    best = _f32(-1.0e30)
    for lo, hi, slope, icpt in cm_segs:
        lo, hi, slope, icpt = _f32(lo), _f32(hi), _f32(slope), _f32(icpt)
        a = max(lo, s_lo)
        b = min(hi, s_hi)
        if a <= b:
            def ev(s):
                bb = _f32(b0 - m_c * (s - cur_cm_f))
                cval = _f32(slope * s + icpt)
                inner = _f32(cval * a2 + a1)
                return _f32(_f32(bb * fstar) * inner)

            cand = max(ev(a), ev(b))
            amp = _f32(a2 * slope)
            lead = _f32(m_c * amp)
            if lead > _f32(0.0):
                dee = _f32(a2 * icpt + a1)
                bhat = _f32(b0 + m_c * cur_cm_f)
                sv = _f32((bhat * amp - m_c * dee) / (_f32(2.0) * lead))
                if a < sv < b:
                    cand = max(cand, ev(sv))
            best = max(best, cand)
    return best


def _ub_gate(p: dict, refpp, refcm, reffm, cm_segs, fm_segs) -> tuple[np.float32, np.float32]:
    budget = p["budget"]
    w_pp, w_cm, w_fm, w_ov, w_max = _weights(p["flags"])
    pp_stat = _clamp_stat(p["cur_pp"] + budget * _GEM_SCALE_NORMAL)
    cm_stat = _clamp_stat(p["cur_cm"] + budget * _GEM_SCALE_NORMAL)
    fm_stat = _clamp_stat(p["cur_fm"] + budget * _GEM_SCALE_FEVER)
    base_lane = (p["cur_p_val"] << 1) + p["cur_s_val"] + budget * w_max
    b0 = _f32(_f32(base_lane) + refpp[pp_stat])
    c = _f32(refcm[cm_stat])
    f = _f32(reffm[fm_stat])
    ln = min(max(p["head_len"], 0), 100)
    sigma = (ln * (ln + 1)) // 2
    n = max(0, p["body_total"])
    a2 = _f32(_f32(n) + _f32(sigma) / _f32(100.0))
    a1 = _f32(_f32(ln) - _f32(sigma) / _f32(100.0))
    delta_c = w_max - w_cm
    delta_f = w_max - w_fm
    inner_fm = _f32(c * a2 + a1)
    ub_fm = _f32(_coupled_fm(b0, inner_fm, delta_f, p["cur_fm"], budget, fm_segs) + _UB_EPS)
    ub_cm = _f32(_coupled_cm(b0, f, a2, a1, delta_c, p["cur_cm"], budget, cm_segs) + _UB_EPS)
    old = _old_bound(p, refpp, refcm, reffm)
    return _f32(min(old, ub_fm, ub_cm)), old


def _exact_all_fever_max(p: dict, refpp, refcm, reffm) -> np.int64:
    """Exact all-fever combo score maximised over every feasible allocation (i64, no overflow)."""
    budget = p["budget"]
    w_pp, w_cm, w_fm, w_ov, _ = _weights(p["flags"])
    ln = min(max(p["head_len"], 0), 100)
    n = max(0, p["body_total"])
    base_init = (p["cur_p_val"] << 1) + p["cur_s_val"]
    ts = np.arange(1, ln + 1, dtype=np.float32)  # (L,)

    allocs = []
    for g_cm in range(budget + 1):
        for g_fm in range(budget + 1 - g_cm):
            leftover = budget - g_cm - g_fm
            for g_pp in range(leftover + 1):
                allocs.append((g_cm, g_fm, g_pp, leftover - g_pp))
    a = np.asarray(allocs, dtype=np.int64)
    g_cm, g_fm, g_pp, g_ov = a[:, 0], a[:, 1], a[:, 2], a[:, 3]

    pp_stat = np.clip(p["cur_pp"] + g_pp * _GEM_SCALE_NORMAL, 0, _MAX_STAT)
    cm_stat = np.clip(p["cur_cm"] + g_cm * _GEM_SCALE_NORMAL, 0, _MAX_STAT)
    fm_stat = np.clip(p["cur_fm"] + g_fm * _GEM_SCALE_FEVER, 0, _MAX_STAT)
    base_lin = base_init + g_pp * w_pp + g_cm * w_cm + g_fm * w_fm + g_ov * w_ov
    b = (base_lin.astype(np.float32) + refpp[pp_stat].astype(np.float32)).astype(np.float32)
    c = refcm[cm_stat].astype(np.float32)
    f = reffm[fm_stat].astype(np.float32)

    fever_val = np.trunc((b * c * f).astype(np.float32)).astype(np.int64)
    body = np.int64(n) * fever_val
    factor = ((c - np.float32(1.0)) * b / np.float32(100.0)).astype(np.float32)
    if ln > 0:
        ramp = b[:, None] + ts[None, :] * factor[:, None]  # (A, L) f32
        head_terms = np.trunc((ramp * f[:, None]).astype(np.float32)).astype(np.int64)
        head = head_terms.sum(axis=1)
    else:
        head = np.zeros_like(body)
    score = body + head
    return np.int64(score.max())


def _random_params(rng: np.random.Generator) -> dict:
    flags = tuple(int(rng.integers(0, 2)) for _ in range(8))
    return {
        "budget": int(rng.integers(0, 13)),
        "cur_pp": int(rng.integers(0, 161)),
        "cur_cm": int(rng.integers(0, 161)),
        "cur_fm": int(rng.integers(0, 161)),
        "cur_p_val": int(rng.integers(0, 900)),
        "cur_s_val": int(rng.integers(0, 900)),
        "head_len": int(rng.integers(0, 101)),
        "body_total": int(rng.integers(0, 8001)),
        "flags": flags,
    }


def _corner_params() -> list[dict]:
    corners = []
    # base-saturated (cur stats near 160)
    corners.append(dict(budget=8, cur_pp=158, cur_cm=159, cur_fm=157, cur_p_val=800,
                        cur_s_val=400, head_len=64, body_total=6000,
                        flags=(1, 1, 1, 1, 1, 1, 1, 1)))
    # all-OV (w_max on OV -> both Delta max)
    corners.append(dict(budget=12, cur_pp=10, cur_cm=20, cur_fm=15, cur_p_val=500,
                        cur_s_val=0, head_len=100, body_total=4000,
                        flags=(0, 0, 0, 0, 0, 0, 1, 0)))
    # no-OV, FM is max weight -> Delta_f = 0
    corners.append(dict(budget=10, cur_pp=30, cur_cm=40, cur_fm=20, cur_p_val=600,
                        cur_s_val=100, head_len=50, body_total=3000,
                        flags=(1, 0, 1, 0, 1, 0, 0, 0)))
    # budget = 0
    corners.append(dict(budget=0, cur_pp=80, cur_cm=90, cur_fm=70, cur_p_val=400,
                        cur_s_val=200, head_len=30, body_total=2000,
                        flags=(1, 1, 0, 0, 1, 1, 1, 1)))
    # large N at high magnitude (kept < 2^31 so the i32 kernel body does not overflow)
    corners.append(dict(budget=6, cur_pp=120, cur_cm=140, cur_fm=150, cur_p_val=700,
                        cur_s_val=300, head_len=0, body_total=40000,
                        flags=(1, 0, 1, 0, 0, 1, 1, 0)))
    # head-only (N = 0), Delta_c = 0 (CM is max weight)
    corners.append(dict(budget=9, cur_pp=15, cur_cm=10, cur_fm=25, cur_p_val=550,
                        cur_s_val=50, head_len=100, body_total=0,
                        flags=(0, 0, 1, 1, 0, 0, 0, 0)))
    return corners


@pytest.mark.parametrize("ref_kind", ["synthetic", "real"])
def test_ub_gate_ge_exact_and_le_old(ref_kind: str) -> None:
    if ref_kind == "real":
        refs = _real_refs_or_none()
        if refs is None:
            pytest.skip("Data/Gear/Stats.txt not available")
    else:
        refs = _synthetic_refs()
    refpp = refs["Perfect Points"].astype(np.float32)
    refcm = refs["Combo Multiplier"].astype(np.float32)
    reffm = refs["Fever Multiplier"].astype(np.float32)
    cm_segs = build_upper_concave_hull_segments(refs["Combo Multiplier"].astype(np.float64), "cm")
    fm_segs = build_upper_concave_hull_segments(refs["Fever Multiplier"].astype(np.float64), "fm")

    rng = np.random.default_rng(20260716)
    cases = _corner_params() + [_random_params(rng) for _ in range(400)]

    n_tighter = 0
    min_slack = np.inf
    for p in cases:
        gate, old = _ub_gate(p, refpp, refcm, reffm, cm_segs, fm_segs)
        exact = _exact_all_fever_max(p, refpp, refcm, reffm)
        # No i32 overflow in the regime we sweep (design corner uses N<=40000).
        assert exact < np.int64(2**31 - 1), "test input overflows the kernel i32 body score"
        slack = float(gate) - float(exact)
        min_slack = min(min_slack, slack)
        assert gate >= np.float32(exact), (
            f"UB_gate {float(gate)} < exact {int(exact)} (slack {slack}) for {p}"
        )
        assert gate <= old + np.float32(1e-3), (
            f"UB_gate {float(gate)} exceeds old bound {float(old)} for {p}"
        )
        if float(gate) < float(old) - 1e-3:
            n_tighter += 1

    # The coupled arms must actually tighten a real fraction of reachable inputs, otherwise the
    # change is a pure no-op (no cull profit). This asserts the mechanism engages.
    assert n_tighter > 0, "coupled sub-bounds never tightened below the old bound"
    # Slack must stay non-negative with headroom (design reports min in-replica slack ~710).
    assert min_slack >= 0.0


def test_ub_gate_tightens_meaningfully() -> None:
    """Directly exhibit a case where the coupled bound is strictly below the old bound."""
    refs = _synthetic_refs()
    refpp = refs["Perfect Points"].astype(np.float32)
    refcm = refs["Combo Multiplier"].astype(np.float32)
    reffm = refs["Fever Multiplier"].astype(np.float32)
    cm_segs = build_upper_concave_hull_segments(refs["Combo Multiplier"].astype(np.float64), "cm")
    fm_segs = build_upper_concave_hull_segments(refs["Fever Multiplier"].astype(np.float64), "fm")
    # OV is the top base-lane weight, so spending budget on CM/FM costs real base (Delta > 0)
    # and the coupled arms bite.
    p = dict(budget=12, cur_pp=0, cur_cm=0, cur_fm=0, cur_p_val=400, cur_s_val=0,
             head_len=80, body_total=5000, flags=(0, 0, 0, 0, 0, 0, 1, 0))
    gate, old = _ub_gate(p, refpp, refcm, reffm, cm_segs, fm_segs)
    exact = _exact_all_fever_max(p, refpp, refcm, reffm)
    assert gate >= np.float32(exact)
    assert float(gate) < float(old), f"expected tightening, gate={float(gate)} old={float(old)}"
