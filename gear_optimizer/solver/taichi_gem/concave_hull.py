"""Concave dominating envelope of the reference multiplier LUTs (pure NumPy, no Taichi).

The GA combo-cull upper bound (`response_score_upper_bound_relaxed`) tightens its value
with two Lagrangian exchange sub-bounds that couple the base lane against the
Combo-Multiplier (CM) and Fever-Multiplier (FM) axes. Each sub-bound maximises a concave
quadratic over a piecewise-linear *concave upper envelope* of the corresponding integer
LUT (`refcm` / `reffm`) — an envelope that is concave and `>=` every LUT entry.

This module builds those envelopes host-side, once per run, from the same reference arrays
that are uploaded to the GPU. It is deliberately Taichi-free so the envelope math and its
soundness assertions can be exercised by a CPU-only test without `ti.init()`.

Soundness contract (all fail loud — the design record marks LUT monotonicity the single
most load-bearing fact):
  * the LUT must be monotone non-decreasing with its maximum attained at index 160
    (endpoint == argmax); an interior peak would make the pinned-off-axis sub-bound
    under-estimate (design UB_CULL_BOUND_DESIGN.md section 4, factor-domination lemma).
  * the returned envelope is concave (segment slopes non-increasing) — required for the
    per-segment closed-form concave-quadratic maximum.
  * the returned envelope dominates the LUT at every integer stat (envelope(s) >= LUT[s]) —
    required so C_a <= Ê_cm(c) / F_a <= Ê_fm(f); an envelope that dipped below the LUT would
    corrupt best_score corpus-wide.

Design deviation (documented in docs/CODEX_WORKLOG.md and the implementation record): the
design text projected "<= 4 segments each" assuming a piecewise-linear game table. The real
Data/Gear/Stats.txt CM/FM columns are a smooth, strictly-concave-ish curve sampled at 161
points, whose exact concave majorant has ~111-114 segments. Soundness needs only a concave
dominating envelope (not the exact majorant, and NOT the design's "Ê <= C*" tightness
claim, which is not required for `UB_cm >= exact` — see the worklog derivation). We therefore
build a tight bounded-segment envelope: the lower envelope (pointwise min) of a greedily
selected subset of the exact hull's segment lines (each of which dominates the LUT), refined
until the max relative gap falls below HULL_REL_TOL or the segment cap is reached. On real
data this yields ~9-12 segments at ~0.2% gap — near-exact tightness with a bounded in-kernel
sweep. A coarser 4-segment envelope would be materially looser (less cull profit) with no
perf benefit: the in-kernel sweep is a runtime while-loop, so its iteration count does not
raise VGPR/occupancy, and its ALU cost is negligible against the ~1e5-op exact solve it gates.
"""

from __future__ import annotations

import numpy as np

# Field capacity for one hull's segment table. The greedy envelope stops at this many
# segments even if the tightness target is not yet met (a lower-segment envelope is still
# sound, just slightly looser). Real CM/FM LUTs reach ~0.2% gap in 9-12 segments, so 16 is
# comfortable headroom. The in-kernel sweep is bounded by the stored segment count, not by
# this capacity.
MAX_CONCAVE_HULL_SEGMENTS = 16

# Best-effort tightness target for the greedy envelope: max (envelope - LUT) relative to the
# LUT mean. Purely a cull-profit knob; it has no bearing on soundness.
HULL_REL_TOL = 0.002

# LUT domain is the stat index range [0, 160] (161 rows), matching GRID_SIZE - 1.
HULL_STAT_MAX = 160
_HULL_ROWS = HULL_STAT_MAX + 1

# Column layout of one hull segment row: [seg_lo, seg_hi, slope, intercept].
# On stat s in [seg_lo, seg_hi], envelope(s) = slope * s + intercept.
HULL_SEG_COLS = 4


def _validate_monotone_endpoint_argmax(values: np.ndarray, name: str) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    if v.ndim != 1 or v.shape[0] != _HULL_ROWS:
        raise ValueError(
            f"{name} LUT must be shape ({_HULL_ROWS},) for concave-envelope build, got {v.shape}"
        )
    diffs = np.diff(v)
    if np.any(diffs < 0.0):
        first = int(np.argmax(diffs < 0.0))
        raise ValueError(
            f"{name} LUT is not monotone non-decreasing: "
            f"values[{first + 1}]={v[first + 1]!r} < values[{first}]={v[first]!r}. "
            "The coupled cull sub-bounds pin the off-axis factor at the endpoint corner and "
            "would under-estimate against an interior peak (design UB_CULL_BOUND_DESIGN.md "
            "section 4, load-bearing soundness fact)."
        )
    # Monotone non-decreasing already guarantees the endpoint holds the maximum; assert it
    # explicitly per the design record (endpoint == argmax is the load-bearing fact).
    if v[HULL_STAT_MAX] < v.max():
        raise ValueError(
            f"{name} LUT maximum is not attained at index {HULL_STAT_MAX} (endpoint != argmax)."
        )
    return v


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _upper_concave_hull_vertices(values: np.ndarray) -> list[tuple[float, float]]:
    """Andrew monotone-chain upper hull -> the exact concave majorant vertices of the LUT.

    Points are (stat_index, value) with strictly increasing x, so a single left-to-right scan
    that pops any non-clockwise turn yields the upper (concave) chain. Endpoints (0, v0) and
    (160, v160) are extreme in x and always retained.
    """
    hull: list[tuple[float, float]] = []
    for i in range(values.shape[0]):
        p = (float(i), float(values[i]))
        while len(hull) >= 2 and _cross(hull[-2], hull[-1], p) >= 0.0:
            hull.pop()
        hull.append(p)
    return hull


def _hull_segment_lines(values: np.ndarray) -> list[tuple[float, float, float, float]]:
    """Exact concave-majorant segment lines as (slope, intercept, seg_lo, seg_hi).

    Each line dominates the LUT everywhere (a concave function lies below any of its own
    segment lines), so the lower envelope of any subset of these lines still dominates the LUT.
    Slopes are strictly decreasing (collinear runs are already merged by the hull scan).
    """
    verts = _upper_concave_hull_vertices(values)
    if len(verts) < 2:
        raise ValueError("concave hull collapsed to < 2 vertices; LUT is degenerate")
    lines: list[tuple[float, float, float, float]] = []
    for i in range(len(verts) - 1):
        x0, y0 = verts[i]
        x1, y1 = verts[i + 1]
        slope = (y1 - y0) / (x1 - x0)
        intercept = y0 - slope * x0
        lines.append((slope, intercept, x0, x1))
    return lines


def _lower_envelope_segments(lines: list[tuple[float, float]]) -> np.ndarray:
    """Lower envelope (pointwise min) of a set of lines, as contiguous segments over [0, 160].

    Returns float64 array (K, 4): [seg_lo, seg_hi, slope, intercept]. Min-of-affine is concave,
    so the result is a concave piecewise-linear function; with the hull's strictly-decreasing
    slopes it partitions [0, 160] left-to-right from steepest to shallowest line.
    """
    # Sort by slope descending (steepest first); for equal slope keep the lower intercept.
    ordered = sorted(lines, key=lambda ln: (-ln[0], ln[1]))
    stack: list[tuple[float, float]] = []
    for slope, icpt in ordered:
        if stack and stack[-1][0] == slope:
            # Parallel line: only the lower intercept can ever be the min.
            if stack[-1][1] <= icpt:
                continue
            stack.pop()
        while len(stack) >= 1:
            s0, i0 = stack[-1]
            x_new = (i0 - icpt) / (slope - s0)  # intersection of new line with stack top
            if len(stack) >= 2:
                s1, i1 = stack[-2]
                x_prev = (i1 - i0) / (s0 - s1)
                if x_new <= x_prev:
                    stack.pop()
                    continue
            break
        stack.append((slope, icpt))

    segs: list[tuple[float, float, float, float]] = []
    lo = 0.0
    for k in range(len(stack)):
        slope, icpt = stack[k]
        if k + 1 < len(stack):
            s1, i1 = stack[k + 1]
            x_break = (icpt - i1) / (s1 - slope)
            hi = min(float(HULL_STAT_MAX), max(lo, x_break))
        else:
            hi = float(HULL_STAT_MAX)
        if hi > lo or k == len(stack) - 1:
            segs.append((lo, hi, slope, icpt))
            lo = hi
    # Guarantee the last segment closes at 160 (the shallowest line owns the tail).
    if segs:
        last = segs[-1]
        segs[-1] = (last[0], float(HULL_STAT_MAX), last[2], last[3])
        segs[0] = (0.0, segs[0][1], segs[0][2], segs[0][3])
    return np.asarray(segs, dtype=np.float64)


def eval_hull_at(segs: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Evaluate a hull segment table at stat positions ``xs`` (float64)."""
    segs = np.asarray(segs, dtype=np.float64)
    xs = np.asarray(xs, dtype=np.float64)
    los = segs[:, 0]
    idx = np.searchsorted(los, xs, side="right") - 1
    idx = np.clip(idx, 0, segs.shape[0] - 1)
    return segs[idx, 2] * xs + segs[idx, 3]


def _assert_envelope_sound(segs: np.ndarray, v: np.ndarray, name: str) -> None:
    # Coverage: contiguous partition of [0, 160].
    if segs[0, 0] != 0.0 or segs[-1, 1] != float(HULL_STAT_MAX):
        raise AssertionError(
            f"{name} envelope does not span [0, {HULL_STAT_MAX}] (got [{segs[0, 0]}, {segs[-1, 1]}])"
        )
    if not np.allclose(segs[1:, 0], segs[:-1, 1]):
        raise AssertionError(f"{name} envelope segments are not contiguous")
    # Concavity: slopes non-increasing.
    if np.any(np.diff(segs[:, 2]) > 1e-9):
        raise AssertionError(f"{name} envelope is not concave (segment slopes not non-increasing)")
    # Dominance: envelope(s) >= LUT[s] at every integer stat. This is the mandated assertion —
    # an envelope that dips below the LUT would corrupt best_score.
    hull_vals = eval_hull_at(segs, np.arange(_HULL_ROWS, dtype=np.float64))
    deficit = v - hull_vals
    if np.any(deficit > 1e-9):
        worst = int(np.argmax(deficit))
        raise AssertionError(
            f"{name} concave envelope does not dominate the LUT at stat {worst}: "
            f"envelope={hull_vals[worst]!r} < value={v[worst]!r}"
        )


def build_upper_concave_hull_segments(
    values: np.ndarray,
    name: str,
    *,
    max_segments: int = MAX_CONCAVE_HULL_SEGMENTS,
    rel_tol: float = HULL_REL_TOL,
) -> np.ndarray:
    """Build the concave dominating envelope segment table for one reference LUT.

    Returns a float32 array (K, 4): [seg_lo, seg_hi, slope, intercept], contiguous over
    [0, 160], concave, and dominating the LUT. Fails loud on any violated soundness
    precondition. K <= max_segments.
    """
    v = _validate_monotone_endpoint_argmax(values, name)
    lines = _hull_segment_lines(v)

    if len(lines) <= max_segments:
        selected_idx = set(range(len(lines)))
    else:
        xs = np.arange(_HULL_ROWS, dtype=np.float64)
        line_slopes = np.array([ln[0] for ln in lines])
        line_icpts = np.array([ln[1] for ln in lines])
        # Precompute which exact-hull line covers each integer stat (its tightest line there).
        covering = np.empty(_HULL_ROWS, dtype=np.int64)
        for j, (_s, _i, lo, hi) in enumerate(lines):
            covering[int(np.ceil(lo)) : int(np.floor(hi)) + 1] = j
        covering[0] = 0
        covering[_HULL_ROWS - 1] = len(lines) - 1

        selected_idx = {0, len(lines) - 1}
        target = rel_tol * float(v.mean())
        while len(selected_idx) < max_segments:
            sel = sorted(selected_idx)
            env = np.min(
                line_slopes[sel][:, None] * xs[None, :] + line_icpts[sel][:, None], axis=0
            )
            gap = env - v
            worst = int(np.argmax(gap))
            if gap[worst] <= target:
                break
            cand = int(covering[worst])
            if cand in selected_idx:
                # The tightest line at the worst stat is already in; no single-line add can beat
                # the current gap there. Stop — the envelope is as tight as this candidate set allows.
                break
            selected_idx.add(cand)

    selected = [(lines[j][0], lines[j][1]) for j in sorted(selected_idx)]
    segs = _lower_envelope_segments(selected)

    _assert_envelope_sound(segs, v, name)
    if segs.shape[0] > max_segments:
        raise AssertionError(
            f"{name} envelope produced {segs.shape[0]} segments, exceeding cap {max_segments}"
        )
    return segs.astype(np.float32)


def pack_hull_field(segs: np.ndarray, *, max_segments: int = MAX_CONCAVE_HULL_SEGMENTS) -> np.ndarray:
    """Pad a segment table to the fixed field capacity (max_segments, 4) float32."""
    segs = np.asarray(segs, dtype=np.float32)
    if segs.shape[0] > max_segments:
        raise ValueError(f"hull has {segs.shape[0]} segments, exceeds capacity {max_segments}")
    out = np.zeros((max_segments, HULL_SEG_COLS), dtype=np.float32)
    out[: segs.shape[0]] = segs
    return out
