"""Issue #44 exactness reference: the FG frontier must also model a boundary note
pulled INTO fever by an early **GREAT** hit -- the greats-side analog of the #42
Perfect-early fix.

GROUND TRUTH = the decompiled server scorer (place 706824758 Spotco_Robeats_dev,
`ServerPlayerNoteSequenceInfo:push_note_sequence` + `GearStats`):
  * fever membership = powerbar active at the note's verified event time;
    `get_verified_event_time` clamps only to +-(okay width=380ms) -> a no-op for any
    legal hit, so the verified time IS the chosen hit offset;
  * the judgment is assigned SEPARATELY from the offset by `timedelta_to_result`
    against the CUMULATIVE windows Perfect [-20,+40], **Great [-95,+190]**, Okay [-235,+430]
    (`get_note_times` ADDS each tier's gear-stat extra to the prior boundary; held tail x2).

So a note sitting D ms PAST the fever cutoff can still be pulled into fever by hitting
it early, and the *best* judgment that still reaches fever depends on D:
  * D <= 20ms  -> Perfect-fever  (issue #42, already landed: perfect_floor = chart-20)
  * 20 < D <= 95ms -> **Great-fever** (issue #44, THIS FILE: great_floor = chart-95)
  * 95 < D <= 235ms -> Okay-fever   (out of #44 scope; documented follow-up)

Unlike #42 (a monotone floor shift, pure gain because Perfect-fever >= Perfect-non-
fever pointwise) the greats-side is a SCORE/PENALTY PARETO tradeoff: the extra boundary
notes can only be in fever as GREATS (Great base < Perfect base) in exchange for the
fever multiplier. So the frontier must ENUMERATE the early-Great boundary as additional
surfaces (fever end extended from `e_perfect` to each `e` in `(e_perfect, e_great]`,
the extra notes [e_perfect, e) marked great-in-fever) and let the exact rescore pick the
winner per stat cell.

THE FORMULA (proven here, mirrors #42 with the cumulative Great lower edge): with the
activation fixed at its latest Perfect (optimal for extent), the maximal fever extent
allowing early-Great boundary hits is
    e_great = searchsorted(prefix_max(chart + great_lo), perfect_candidate[a] + rft)
with great_lo = -95ms (held tail -190). e_perfect uses perfect_lo = -20 (held -40). The
notes [e_perfect, e_great) are reachable into fever ONLY as Greats; [a, e_perfect) stay
Perfect.
"""
from __future__ import annotations

import itertools
from math import floor

import numpy as np

# CUMULATIVE judgment-window edges (ms), from the decompiled game's GearStats.get_note_times +
# SPUtil.timedelta_to_result (place 706824758): each tier ADDS its gear-stat extra to the previous
# boundary (great = perfect +- great_extra, okay = great +- okay_extra). Held tail (note_type 3)
# doubles every edge. Negative = early. (NoteTimeGraph renders "-95ms (Great)" / "+190ms (Great)".)
PERFECT_LO_MS = -20
PERFECT_HI_MS = 40
GREAT_LO_MS = -95   # = perfect_lower(-20) + great_lower_extra(-75)
GREAT_HI_MS = 190   # = perfect_upper(+40) + great_upper_extra(+150)
OKAY_LO_MS = -235   # = great_lower(-95) + okay_lower_extra(-140)
OKAY_HI_MS = 430    # = great_upper(+190) + okay_upper_extra(+240)
HELD_TAIL_TYPE = 3
HELD_TAIL_MULT = 2


def _lo_array(chart_ms, lo):
    if np.isscalar(lo):
        return np.full(len(chart_ms), int(lo), dtype=np.int64)
    return np.asarray(lo, dtype=np.int64)


def _per_note_lo(note_types, base_lo):
    """Per-note early edge (ms), held-tail-aware: base_lo, doubled for held tails."""
    nt = np.asarray(note_types, dtype=np.int16)
    mult = np.where(nt == HELD_TAIL_TYPE, HELD_TAIL_MULT, 1).astype(np.int64)
    return (int(base_lo) * mult).astype(np.int64)


# ---------------------------------------------------------------------------
# Fever-extent ground truth (server-order greedy == assumption-free brute force).
# ---------------------------------------------------------------------------
def _greedy_extent(chart_ms, a, rft_ms, lo, hi=PERFECT_HI_MS):
    """Max fever notes in the section activating at `a`, hitting every later note at its
    earliest legal monotonic time `max(prev, chart+lo)`. Exact for a fixed activation
    (proven in #42); `lo` is per-note. `hi` is the activation's latest hit."""
    n = len(chart_ms)
    lo_arr = _lo_array(chart_ms, lo)
    hi_arr = _lo_array(chart_ms, hi)
    fever_end = chart_ms[a] + int(hi_arr[a]) + rft_ms
    ev = chart_ms[a] + int(hi_arr[a])
    count = 1
    for i in range(a + 1, n):
        ev = max(ev, chart_ms[i] + int(lo_arr[i]))
        if ev < fever_end:
            count += 1
        else:
            break
    return int(count)


def _exhaustive_extent(chart_ms, a, rft_ms, lo, hi=PERFECT_HI_MS):
    """Assumption-free: every monotonic per-note offset assignment over a 5ms grid (step 5 keeps
    BOTH each note's floor `lo` and the activation's `hi=+40` as grid points). Exponential in n, so
    the caller restricts it to the small (n<=5) cases; the held-tail n=6 case is covered by the
    fast `formula==greedy` check instead."""
    n = len(chart_ms)
    lo_arr = _lo_array(chart_ms, lo)
    hi_arr = _lo_array(chart_ms, hi)
    grid = [range(int(lo_arr[i]), int(hi_arr[i]) + 1, 5) for i in range(n)]
    best = 0
    for combo in itertools.product(*grid):
        ev = [chart_ms[i] + combo[i] for i in range(n)]
        if any(ev[j] < ev[j - 1] for j in range(1, n)):
            continue
        fe = ev[a] + rft_ms
        best = max(best, sum(1 for i in range(a, n) if ev[i] < fe))
    return int(best)


def _floor_extent(chart_ms, a, rft_ms, lo, hi=PERFECT_HI_MS):
    """PROPOSED production formula: searchsorted against prefix_max(chart + lo)."""
    chart = np.asarray(chart_ms, dtype=np.int64)
    floor_pm = np.maximum.accumulate(chart + _lo_array(chart_ms, lo))
    hi_arr = _lo_array(chart_ms, hi)
    cutoff = int(chart[a]) + int(hi_arr[a]) + rft_ms  # perfect_candidate[a] + rft
    return int(np.searchsorted(floor_pm, cutoff, side="left")) - int(a)


# Constructed case: a boundary note 50ms past the latest-Perfect cutoff -- out of Perfect
# reach (50 > 20) but inside Great reach (50 < 95).
#   activation idx 2 @ 200ms; latest-Perfect start = 240; rft = 1000 => cutoff = 1240.
#   boundary @ 1290ms: chart-20=1270 >= 1240 (no Perfect) but chart-95=1195 < 1240 (Great in).
_CHART_MS = [0, 100, 200, 400, 600, 800, 1000, 1290, 1600]
_ACTIVATION = 2
_RFT_MS = 1000

_VALIDATION_CASES = [
    # (chart_ms, note_types, activation_idx, rft_ms)
    ([0, 300, 600, 1310, 1700], [1, 1, 1, 1, 1], 1, 1000),
    ([0, 100, 1280, 1330, 1700], [1, 1, 1, 1, 1], 0, 1200),
    ([0, 50, 100, 1300, 1700], [1, 1, 1, 1, 1], 2, 1100),
    # Held tail (idx 4) reaches -190 early; sits earlier-effective than idx 3 -> the raw
    # great floor dips and only the prefix-max keeps searchsorted exact.
    ([0, 100, 200, 1300, 1305, 1700], [1, 1, 1, 1, 3, 1], 2, 1000),
]


def test_great_greedy_matches_exhaustive():
    """The greedy great-extent ground truth equals assumption-free monotonic brute force.

    Restricted to n<=5 cases: the brute force is exponential in n and the cumulative -95/-190 early
    range widens the per-note grid, so the n=6 held-tail case would be prohibitively slow here (it
    is validated by `test_great_floor_formula_matches_ground_truth` via greedy==floor instead)."""
    for chart, types, a, rft in _VALIDATION_CASES:
        if len(chart) > 5:
            continue
        great_lo = _per_note_lo(types, GREAT_LO_MS)
        assert _greedy_extent(chart, a, rft, lo=great_lo) == _exhaustive_extent(
            chart, a, rft, lo=great_lo
        ), (chart, types, a, rft)


def test_great_floor_formula_matches_ground_truth():
    """prefix_max(chart + great_lo) searchsorted reproduces the brute-force great extent,
    including the held-tail case where the raw great floor is non-monotone."""
    for chart, types, a, rft in _VALIDATION_CASES + [(_CHART_MS, [1] * len(_CHART_MS), _ACTIVATION, _RFT_MS)]:
        great_lo = _per_note_lo(types, GREAT_LO_MS)
        assert _floor_extent(chart, a, rft, lo=great_lo) == _greedy_extent(
            chart, a, rft, lo=great_lo
        ), (chart, types, a, rft)


def test_constructed_case_exposes_the_greats_gap():
    """On the constructed case the early-Great boundary gains exactly one fever note over
    the Perfect-only (#42) boundary -- and that note is Great-only (no Perfect reaches it)."""
    types = [1] * len(_CHART_MS)
    perfect_lo = _per_note_lo(types, PERFECT_LO_MS)
    great_lo = _per_note_lo(types, GREAT_LO_MS)
    e_perfect = _floor_extent(_CHART_MS, _ACTIVATION, _RFT_MS, lo=perfect_lo)
    e_great = _floor_extent(_CHART_MS, _ACTIVATION, _RFT_MS, lo=great_lo)
    assert e_perfect == 5  # notes 2..6 (idx 7 @ 1290 is 50ms past cutoff: no Perfect)
    assert e_great == 6  # idx 7 pulled in via a legal -95ms Great hit
    assert e_great - e_perfect == 1


# ---------------------------------------------------------------------------
# Legality: every enumerated Pareto surface e in [e_perfect, e_great] is realized by an
# explicit, in-window, monotonic hit assignment whose server-order replay yields fever
# exactly [a, e) with [a, e_perfect) Perfect and [e_perfect, e) Great.
# ---------------------------------------------------------------------------
def _legal_surface_assignment(chart_ms, a, rft_ms, note_types, e, e_perfect):
    """Explicit event time per note realizing fever=[a,e): activation at latest Perfect,
    [a, e_perfect) at earliest Perfect, [e_perfect, e) at earliest Great, the rest late."""
    n = len(chart_ms)
    perfect_lo = _per_note_lo(note_types, PERFECT_LO_MS)
    great_lo = _per_note_lo(note_types, GREAT_LO_MS)
    perfect_hi = _per_note_lo(note_types, PERFECT_HI_MS)
    ev = [0] * n
    prev = -(10 ** 9)
    for i in range(n):
        if i == a:
            e_i = chart_ms[i] + int(perfect_hi[i])          # activation: latest Perfect
        elif i < e_perfect:
            e_i = max(prev, chart_ms[i] + int(perfect_lo[i]))  # earliest Perfect
        elif i < e:
            e_i = max(prev, chart_ms[i] + int(great_lo[i]))    # earliest Great
        else:
            e_i = max(prev, chart_ms[i] + int(perfect_hi[i]))  # latest Perfect (push out of fever)
        ev[i] = int(e_i)
        prev = int(e_i)
    return ev


def _judge(offset, note_type):
    mult = HELD_TAIL_MULT if note_type == HELD_TAIL_TYPE else 1
    if PERFECT_LO_MS * mult <= offset <= PERFECT_HI_MS * mult:
        return "perfect"
    if GREAT_LO_MS * mult <= offset <= GREAT_HI_MS * mult:
        return "great"
    if OKAY_LO_MS * mult <= offset <= OKAY_HI_MS * mult:
        return "okay"
    return "miss"


def test_every_enumerated_surface_is_legal_and_correctly_judged():
    """For each e in [e_perfect, e_great]: the explicit assignment is in-window, monotonic,
    and server-order-replays to fever=[a,e) with [a,e_perfect) Perfect and [e_perfect,e)
    Great -- never an impossible/illegal hit, never a Perfect where the surface claims Great."""
    for chart, types, a, rft in _VALIDATION_CASES + [(_CHART_MS, [1] * len(_CHART_MS), _ACTIVATION, _RFT_MS)]:
        perfect_lo = _per_note_lo(types, PERFECT_LO_MS)
        great_lo = _per_note_lo(types, GREAT_LO_MS)
        e_perfect = _floor_extent(chart, a, rft, lo=perfect_lo) + a
        e_great = _floor_extent(chart, a, rft, lo=great_lo) + a
        for e in range(e_perfect, e_great + 1):
            ev = _legal_surface_assignment(chart, a, rft, types, e, e_perfect)
            # (a) monotonic event order (a legal, playable hit sequence).
            assert all(ev[i] >= ev[i - 1] for i in range(1, len(chart))), (chart, e, ev)
            # (b) server-order fever replay: contiguous prefix [a, replay_e).
            cutoff = ev[a] + rft
            replay_e = a
            for i in range(a, len(chart)):
                if ev[i] < cutoff:
                    replay_e = i + 1
                else:
                    break
            assert replay_e == e, ("fever extent mismatch", chart, e, replay_e)
            # (c) judgments: activation + [a,e_perfect) Perfect; [e_perfect,e) Great; all in-window.
            for i in range(a, e):
                judged = _judge(ev[i] - chart[i], types[i])
                expected = "perfect" if i < e_perfect else "great"
                assert judged == expected, ("wrong judgment", chart, i, e, judged, expected)


def test_perfect_extension_notes_are_not_reachable():
    """TIGHTNESS: the notes [e_perfect, e_great) cannot be Perfect-in-fever (their earliest
    Perfect hit is at/after the cutoff) -- so they are Great-only, never an over-counted
    Perfect-fever. This is what makes #44 a tradeoff, not a #42-style pure floor shift."""
    for chart, types, a, rft in _VALIDATION_CASES + [(_CHART_MS, [1] * len(_CHART_MS), _ACTIVATION, _RFT_MS)]:
        perfect_lo = _per_note_lo(types, PERFECT_LO_MS)
        great_lo = _per_note_lo(types, GREAT_LO_MS)
        perfect_hi = _per_note_lo(types, PERFECT_HI_MS)
        e_perfect = _floor_extent(chart, a, rft, lo=perfect_lo) + a
        e_great = _floor_extent(chart, a, rft, lo=great_lo) + a
        cutoff = chart[a] + int(perfect_hi[a]) + rft
        for j in range(e_perfect, e_great):
            assert chart[j] + int(perfect_lo[j]) >= cutoff, ("note reachable as Perfect", chart, j)
            assert chart[j] + int(great_lo[j]) < cutoff, ("note NOT reachable as Great", chart, j)


# ---------------------------------------------------------------------------
# The Pareto tradeoff is real: great-fever beats perfect-non-fever for some stat cells and
# loses for others, so EVERY intermediate e can be the winner -> the frontier must
# enumerate them all (cannot just take the maximal extension). Uses the exact-rescore
# per-note value model.
# ---------------------------------------------------------------------------
def _great_head_base(primary, secondary, single_color):
    if single_color:
        return (primary * 2) + 150
    return floor(primary * (4.0 / 3.0)) + floor(secondary * (2.0 / 3.0)) + 150


def _note_value(i, base_value, combo_mul, fever_mul, *, is_fever, is_great, great_base):
    """Per-note score, matching score_force_greats_response_surface_exact (head index i)."""
    scaling = ((combo_mul - 1.0) / 100.0) * float(i + 1) + 1.0
    perfect_score = floor(base_value * scaling * fever_mul) if is_fever else floor(base_value * scaling)
    if is_great:
        great_score = floor(great_base * scaling * fever_mul) if is_fever else floor(great_base * scaling)
        perfect_score -= max(0, perfect_score - great_score)
    return int(perfect_score)


def _body_hull_filter_reference(points):
    """Pure-Python mirror of `_numba_hull_filter_body_pairs` (response_build_gpu_numba.py): within
    each normal_great level, keep the 2-D upper hull in (body_fever, -fever_great). Points are
    (body_fever, body_great, body_fever_great)."""
    if len(points) <= 2:
        return list(points)
    groups: dict[int, list] = {}
    for bf, bg, bfg in points:
        groups.setdefault(bg - bfg, []).append((bf, bg, bfg))
    kept = []
    for grp in groups.values():
        if len(grp) <= 2:
            kept.extend(grp)
            continue
        grp = sorted(grp, key=lambda p: (p[0], -p[2]))
        stack: list = []
        for p in grp:
            x, y = p[0], -p[2]
            while len(stack) >= 2:
                x1, y1 = stack[-2][0], -stack[-2][2]
                x2, y2 = stack[-1][0], -stack[-1][2]
                if (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1) >= 0:
                    stack.pop()
                else:
                    break
            stack.append(p)
        kept.extend(stack)
    return kept


def test_body_hull_filter_preserves_max_for_every_cone_direction():
    """Issue #44 perf: the body-tail hull filter (fused into `_numba_reduce_touched_body_pairs`) is BIT-EXACT.
    For any fixed stat cell the body score is linear: A*body_fever - pnp*normal_great -
    pfp*fever_great with A,pnp,pfp >= 0. So pruning each body-tail frontier to its convex hull may
    NEVER change the max for any (A,pnp,pfp) in the cone. This locks that invariant against a
    brute force over a dense cone grid (mirrors the in-kernel algorithm)."""
    import random

    rng = random.Random(20260617)
    cone = [(A, pnp, pfp) for A in range(5) for pnp in range(5) for pfp in range(5) if (A, pnp, pfp) != (0, 0, 0)]
    for _trial in range(1200):
        n = rng.randint(1, 16)
        pts = set()
        for _ in range(n):
            bf = rng.randint(0, 12)
            bfg = rng.randint(0, bf)
            ng = rng.randint(0, 7)
            pts.add((bf, ng + bfg, bfg))
        pts = list(pts)
        kept = _body_hull_filter_reference(pts)
        # kept is a subset that must preserve the max for every cone direction.
        assert set(kept).issubset(set(pts))
        for A, pnp, pfp in cone:
            mx_all = max(A * bf - pnp * (bg - bfg) - pfp * bfg for bf, bg, bfg in pts)
            mx_keep = max(A * bf - pnp * (bg - bfg) - pfp * bfg for bf, bg, bfg in kept)
            assert mx_keep == mx_all, (pts, kept, (A, pnp, pfp))


def _mk_head_surface(fever_positions, great_positions):
    """A numba response surface (uint64 head masks + zero body) over head positions."""
    fl = fh = gl = gh = 0
    for p in fever_positions:
        if p < 64:
            fl |= 1 << p
        else:
            fh |= 1 << (p - 64)
    for p in great_positions:
        if p < 64:
            gl |= 1 << p
        else:
            gh |= 1 << (p - 64)
    return (np.uint64(fl), np.uint64(fh), np.uint64(gl), np.uint64(gh),
            np.uint64(0), np.uint64(0), np.uint64(0))


def _head_surface_score(fever_positions, great_positions, head_len, base_value, combo_mul, fever_mul, great_base):
    total = 0
    fset = set(fever_positions)
    gset = set(great_positions)
    for i in range(head_len):
        total += _note_value(i, base_value, combo_mul, fever_mul,
                             is_fever=(i in fset), is_great=(i in gset), great_base=great_base)
    return total


def test_head_envelope_filter_preserves_best_score_and_prunes():
    """Issue #44 Route A: `_numba_head_envelope_filter` is the LOSSLESS cone-dominance prune. It must
    (a) keep a strict SUBSET, (b) shrink a rich early-Great family hard (most surfaces are
    cone-dominated -- optimal for NO realizable cell), and (c) preserve the max for EVERY realizable
    stat cell (the best_fg_score criterion) -- EXACTLY, by the 16-corner proof, not probe sampling."""
    import random

    from numba.typed import List
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_head_envelope_filter,
        _HEAD_DOM_C,
        _HEAD_DOM_F,
        _NUMBA_SURFACE_TYPE,
    )

    head_len = 24
    rng = random.Random(20260617)
    # Early-Great-style family: fever over [0, e); a suffix [e-g, e) pulled in as fever-greats.
    raw = set()
    for _ in range(400):
        e = rng.randint(4, head_len)
        g = rng.randint(0, e)
        fever = tuple(range(0, e))
        great = tuple(range(e - g, e))
        raw.add((fever, great))
    family = sorted(raw)
    assert len(family) > 60  # a genuinely rich set

    lst = List.empty_list(_NUMBA_SURFACE_TYPE)
    for fever, great in family:
        lst.append(_mk_head_surface(fever, great))
    kept = _numba_head_envelope_filter(lst, 0, head_len, 0)  # min_surfaces=0 -> always prune

    kept_keys = {(int(s[0]), int(s[2])) for s in kept}
    family_keys = {(sum(1 << p for p in fv), sum(1 << p for p in gr)) for fv, gr in family}
    assert kept_keys.issubset(family_keys)              # (a) subset
    assert len(kept) < len(family) // 2                 # (b) prunes hard

    # Cells spanning the REALIZABLE stat box (combo/fever-mul within _HEAD_DOM_C/_HEAD_DOM_F, great
    # base g <= v): the cone-dominance is lossless for EVERY such cell by the 16-corner argument, so
    # the max is preserved EXACTLY. (Cells outside the box carry no guarantee and are not reachable.)
    cs = (_HEAD_DOM_C[0], 0.5 * (_HEAD_DOM_C[0] + _HEAD_DOM_C[1]), _HEAD_DOM_C[1])
    fs = (_HEAD_DOM_F[0], 0.5 * (_HEAD_DOM_F[0] + _HEAD_DOM_F[1]), _HEAD_DOM_F[1])
    grid = [(v, c, f, u * v)
            for v in (700.0, 1400.0, 2600.0)
            for c in cs
            for f in fs
            for u in (0.35, 0.62, 0.78, 0.95)]
    kept_family = [(fv, gr) for fv, gr in family
                   if (sum(1 << p for p in fv), sum(1 << p for p in gr)) in kept_keys]
    for v, c, f, g in grid:
        all_max = max(_head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in family)
        keep_max = max(_head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in kept_family)
        assert keep_max == all_max, (v, c, f, g, all_max, keep_max)  # (c) max preserved at every realizable cell


def test_head_generated_incremental_bound_preserves_best_score():
    """Incremental head checkpointing must be equivalent to one-shot full reduction.

    This derisks generation-time bounding: surfaces may be dropped before the final reducer only
    when the same 16-corner cone certificate proves they cannot win for any realizable stat cell.
    """
    import random

    from numba.typed import List
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _HEAD_DOM_C,
        _HEAD_DOM_F,
        _NUMBA_HEAD_SCORES_TYPE,
        _NUMBA_SURFACE_TYPE,
        _numba_head_envelope_filter,
        _numba_maybe_promote_head_generated_with_scores,
        _numba_reduce,
    )

    head_len = 32
    rng = random.Random(20260618)
    family = []
    for _ in range(5200):
        e = rng.randint(4, head_len)
        g = rng.randint(0, e)
        family.append((tuple(range(0, e)), tuple(range(e - g, e))))

    full = List.empty_list(_NUMBA_SURFACE_TYPE)
    stream = List.empty_list(_NUMBA_SURFACE_TYPE)
    stream_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    for idx, (fever, great) in enumerate(family):
        surface = _mk_head_surface(fever, great)
        full.append(surface)
        stream.append(surface)
        if idx % 137 == 0:
            # `_numba_maybe_promote_head_generated_with_scores` with bounded_mode=0 is the
            # score-carrying periodic bound: over threshold it returns the same
            # `_numba_head_envelope_filter(_numba_reduce(...))` reduction the deleted
            # `_numba_bound_head_generated` did, else the stream unchanged.
            stream, stream_scores, _bounded = (
                _numba_maybe_promote_head_generated_with_scores(
                    stream, stream_scores, 0, head_len, 0, 0
                )
            )

    full_once = _numba_head_envelope_filter(_numba_reduce(full), 0, head_len, 0)
    stream = _numba_head_envelope_filter(_numba_reduce(stream), 0, head_len, 0)
    assert len(stream) < len(family) // 10
    assert {(int(s[0]), int(s[1]), int(s[2]), int(s[3])) for s in stream}.issubset(
        {(int(s[0]), int(s[1]), int(s[2]), int(s[3])) for s in full_once}
    )

    def positions(surface, offset):
        out = []
        lo = int(surface[offset])
        hi = int(surface[offset + 1])
        for pos in range(head_len):
            if pos < 64:
                hit = (lo >> pos) & 1
            else:
                hit = (hi >> (pos - 64)) & 1
            if hit:
                out.append(pos)
        return tuple(out)

    cs = (_HEAD_DOM_C[0], 0.5 * (_HEAD_DOM_C[0] + _HEAD_DOM_C[1]), _HEAD_DOM_C[1])
    fs = (_HEAD_DOM_F[0], 0.5 * (_HEAD_DOM_F[0] + _HEAD_DOM_F[1]), _HEAD_DOM_F[1])
    grid = [
        (v, c, f, u * v)
        for v in (700.0, 1800.0, 4200.0, 7600.0)
        for c in cs
        for f in fs
        for u in (0.35, 0.62, 0.95)
    ]
    full_positions = [(positions(s, 0), positions(s, 2)) for s in full]
    stream_positions = [(positions(s, 0), positions(s, 2)) for s in stream]
    for v, c, f, g in grid:
        full_max = max(_head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in full_positions)
        stream_max = max(_head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in stream_positions)
        assert stream_max == full_max, (v, c, f, g, full_max, stream_max)


def test_head_generation_promotion_then_bounded_insert_preserves_best_score():
    """Once a stream is promoted into bounded mode, exact candidate-by-candidate insertion must
    preserve the same winners as the full one-shot head envelope."""
    import random

    import numpy as np
    from numba.typed import List
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _HEAD_DOM_C,
        _HEAD_DOM_F,
        _NUMBA_HEAD_SCORES_TYPE,
        _NUMBA_SURFACE_TYPE,
        _numba_head_basis_corner_scores_row,
        _numba_head_envelope_filter,
        _numba_head_envelope_insert_with_scores,
        _numba_head_surface_basis,
        _numba_maybe_promote_head_generated_with_scores,
        _numba_reduce,
    )

    head_len = 32
    rng = random.Random(20260619)
    family = []
    for _ in range(5600):
        e = rng.randint(4, head_len)
        g = rng.randint(0, e)
        family.append((tuple(range(0, e)), tuple(range(e - g, e))))

    full = List.empty_list(_NUMBA_SURFACE_TYPE)
    stream = List.empty_list(_NUMBA_SURFACE_TYPE)
    stream_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    cand_scores = np.empty(16, dtype=np.float64)
    bounded_mode = 0
    promoted_at = -1
    for idx, (fever, great) in enumerate(family):
        surface = _mk_head_surface(fever, great)
        full.append(surface)
        if bounded_mode == 0:
            stream.append(surface)
            stream, stream_scores, bounded_mode = (
                _numba_maybe_promote_head_generated_with_scores(
                    stream, stream_scores, 0, head_len, 0, bounded_mode
                )
            )
            if bounded_mode != 0 and promoted_at < 0:
                promoted_at = idx
        else:
            candidate_basis = _numba_head_surface_basis(surface, 0, head_len)
            _numba_head_basis_corner_scores_row(candidate_basis, cand_scores)
            stream, stream_scores = _numba_head_envelope_insert_with_scores(
                stream, stream_scores, surface, cand_scores
            )

    assert promoted_at >= 4096
    assert promoted_at < len(family) - 500

    full_once = _numba_head_envelope_filter(_numba_reduce(full), 0, head_len, 0)
    bounded_once = _numba_head_envelope_filter(_numba_reduce(stream), 0, head_len, 0)
    assert len(stream) == len(bounded_once)

    def positions(surface, offset):
        out = []
        lo = int(surface[offset])
        hi = int(surface[offset + 1])
        for pos in range(head_len):
            if pos < 64:
                hit = (lo >> pos) & 1
            else:
                hit = (hi >> (pos - 64)) & 1
            if hit:
                out.append(pos)
        return tuple(out)

    cs = (_HEAD_DOM_C[0], 0.5 * (_HEAD_DOM_C[0] + _HEAD_DOM_C[1]), _HEAD_DOM_C[1])
    fs = (_HEAD_DOM_F[0], 0.5 * (_HEAD_DOM_F[0] + _HEAD_DOM_F[1]), _HEAD_DOM_F[1])
    grid = [
        (v, c, f, u * v)
        for v in (700.0, 1800.0, 4200.0, 7600.0)
        for c in cs
        for f in fs
        for u in (0.35, 0.62, 0.95)
    ]
    full_positions = [(positions(s, 0), positions(s, 2)) for s in full_once]
    bounded_positions = [(positions(s, 0), positions(s, 2)) for s in stream]
    for v, c, f, g in grid:
        full_max = max(_head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in full_positions)
        bounded_max = max(
            _head_surface_score(fv, gr, head_len, v, c, f, g) for fv, gr in bounded_positions
        )
        assert bounded_max == full_max, (v, c, f, g, full_max, bounded_max)


def test_early_great_is_a_genuine_pareto_tradeoff():
    """A boundary note's early-Great-fever value vs its Perfect-non-fever value flips sign
    with fever_mul: high fever_mul -> great-fever wins (extend), low -> loses (don't). So the
    early-Great surface is NOT dominated and NOT always dominating; intermediate e matter."""
    base_value, combo_mul = 900.0, 2.0
    primary, secondary, single_color = 300, 300, False
    great_base = _great_head_base(primary, secondary, single_color)
    i = 40  # a head index
    # High fever multiplier: pulling the boundary note in as a Great BEATS leaving it a
    # non-fever Perfect.
    hi_fever = 3.0
    great_fever = _note_value(i, base_value, combo_mul, hi_fever, is_fever=True, is_great=True, great_base=great_base)
    perfect_plain = _note_value(i, base_value, combo_mul, hi_fever, is_fever=False, is_great=False, great_base=great_base)
    assert great_fever > perfect_plain, (great_fever, perfect_plain)
    # Low fever multiplier: the Great penalty outweighs the fever bonus -> do NOT extend.
    lo_fever = 1.05
    great_fever_lo = _note_value(i, base_value, combo_mul, lo_fever, is_fever=True, is_great=True, great_base=great_base)
    perfect_plain_lo = _note_value(i, base_value, combo_mul, lo_fever, is_fever=False, is_great=False, great_base=great_base)
    assert great_fever_lo < perfect_plain_lo, (great_fever_lo, perfect_plain_lo)
