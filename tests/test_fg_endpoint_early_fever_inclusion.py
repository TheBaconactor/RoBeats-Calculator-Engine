"""Issue #42 exactness gate: the FG frontier must score endpoint-early fever
inclusion exactly, like the base timeline frontier.

GROUND TRUTH = a server-order replay brute-forced over per-note hit offsets. The
real game corrects each note's event time from its hit offset, advances the fever
clock to that time, recomputes is_fever, then scores -- so a note just past the
fever end can be pulled INTO fever by a legal EARLY hit, subject to monotonic hit
order. The base frontier models this (carry-aware offset-band exit enumeration).

The FG fever-extent model does NOT: `response_builder._edge_end` -- mirrored
bit-for-bit by the production GPU builder (`response_build_gpu_precompute` /
`response_build_gpu_numba`, confirmed) -- decides the boundary with a single
`searchsorted(chart_timestamps, perfect_candidate[a] + real_fever_time)`, i.e. the
boundary note is tested at offset 0. So FG UNDER-counts fever notes near a section
end whenever a boundary note is within the early-hit reach of the cutoff.

This file holds (1) the brute-force ground truth, (2) the proven-exact FIX formula
the production change must implement, and (3) the `xfail` gate on the live FG model.

THE FIX (derived + validated here): with the activation hit at its latest Perfect
(`perfect_candidate[a] = chart[a] + perfect_upper`, already what FG uses, and
optimal since a later activation only extends the window), the max-inclusion play
hits every later note at its earliest legal monotonic time. Because chart times are
monotonic, that greedy event simplifies to `ev[i] = max(chart[a]+hi, chart[i]+lo[i])`,
and since `chart[a]+hi < cutoff`, note i is in fever iff `chart[i] + lo[i] < cutoff`.
The first exit is therefore `searchsorted(prefix_max(chart + lo), cutoff)` -- the
EARLIEST-hit envelope made monotone by a prefix-max (which is held-tail-exact even
when per-note `lo` makes the raw envelope non-monotonic). FG today searches `chart`
(i.e. `lo == 0`); the fix searches `prefix_max(chart + lo)`.
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _edge_end
from gear_optimizer.solver.timing_envelope import (
    build_perfect_candidate_envelope_sec,
    build_perfect_floor_envelope_sec,
)

# Perfect-hit window (ms): matches the optimizer envelope (timing_envelope.py defaults)
# and the game's mid-stat Perfect window (GearStats get_perfect_upper_lower_time).
# Held tails widen the early edge (held_tail_time_multiplier), e.g. -40ms.
PERFECT_LO_MS = -20
PERFECT_HI_MS = 40


def _lo_array(chart_ms, lo):
    if np.isscalar(lo):
        return np.full(len(chart_ms), int(lo), dtype=np.int64)
    return np.asarray(lo, dtype=np.int64)


def _greedy_max_fever_extent(chart_ms, a, rft_ms, lo=PERFECT_LO_MS, hi=PERFECT_HI_MS):
    """Exact max number of fever notes in the section activating at index `a`.

    For a FIXED activation event (=> fixed fever_end = event[a] + rft), hitting every
    later note at its earliest legal monotonic time (`max(prev, chart+lo)`) minimises
    every event time and so maximises how many fall before fever_end; once one is out,
    monotonicity keeps the rest out. A later activation only slides fever_end later, so
    activation-latest (chart[a]+hi) is optimal. Hence this greedy is exact. `lo` may be
    per-note (held tails)."""
    n = len(chart_ms)
    lo_arr = _lo_array(chart_ms, lo)
    fever_end = chart_ms[a] + hi + rft_ms
    ev = chart_ms[a] + hi
    count = 1  # the activation note starts the fever run
    for i in range(a + 1, n):
        ev = max(ev, chart_ms[i] + int(lo_arr[i]))
        if ev < fever_end:
            count += 1
        else:
            break
    return int(count)


def _legal_max_inclusion_assignment(chart_ms, a, rft_ms, lo=PERFECT_LO_MS, hi=PERFECT_HI_MS):
    """The EXPLICIT hit assignment (event-time per note, ms) that realizes the fix's
    fever extent: the activation note is hit at its latest Perfect; every other note is
    hit at its earliest legal time that preserves monotonic hit order. This is a single
    concrete, legal, achievable play -- the witness that the counted inclusions are not
    impossible/illegal."""
    n = len(chart_ms)
    lo_arr = _lo_array(chart_ms, lo)
    ev = [0] * n
    prev = -(10**9)
    for i in range(n):
        if i == a:
            e = chart_ms[i] + hi                       # activation: latest Perfect
        else:
            e = max(prev, chart_ms[i] + int(lo_arr[i]))  # everyone else: earliest legal monotonic
        ev[i] = int(e)
        prev = int(e)
    return ev


def _exhaustive_max_fever_extent(chart_ms, a, rft_ms, grid_per_note):
    """Assumption-free reference: enumerate every monotonic offset assignment over a
    coarse per-note integer grid and take the max fever-run length. Validates greedy."""
    n = len(chart_ms)
    best = 0
    for combo in itertools.product(*grid_per_note):
        ev = [chart_ms[i] + combo[i] for i in range(n)]
        if any(ev[i] < ev[i - 1] for i in range(1, n)):
            continue
        fever_end = ev[a] + rft_ms
        count = sum(1 for i in range(a, n) if ev[i] < fever_end)
        best = max(best, count)
    return int(best)


def _fg_fixed_fever_extent(chart_ms, a, rft_ms, lo=PERFECT_LO_MS, hi=PERFECT_HI_MS):
    """The PROPOSED production fix: searchsorted against the earliest-hit prefix-max.

    `earliest[i] = chart[i] + lo[i]`; the prefix-max keeps it monotone so a single
    `searchsorted` is exact even when held-tail `lo` makes the raw envelope dip."""
    chart = np.asarray(chart_ms, dtype=np.int64)
    earliest_prefix_max = np.maximum.accumulate(chart + _lo_array(chart_ms, lo))
    cutoff = int(chart[a]) + hi + rft_ms  # perfect_candidate[a] + rft
    e = int(np.searchsorted(earliest_prefix_max, cutoff, side="left"))
    return int(e) - int(a)


def _fg_edge_fever_extent(chart_ms, a, rft_ms, perfect_floor_sec=None):
    """The production FG model's fever-run length via `_edge_end` (the GPU builder mirrors
    it). `_edge_end` REQUIRES `perfect_floor_timestamps` (no chart fallback); this fixture
    chooses the baseline EXPLICITLY -- `perfect_floor_sec=None` passes chart (pre-fix /
    degenerate behaviour), a real envelope exercises the endpoint-early fix."""
    chart_sec = np.asarray(chart_ms, dtype=np.float32) / np.float32(1000.0)
    perfect_cand_sec = (np.asarray(chart_ms, dtype=np.float32) + np.float32(PERFECT_HI_MS)) / np.float32(1000.0)
    e, _start, _carry = _edge_end(
        n=len(chart_ms),
        a=int(a),
        activation_great=False,
        real_fever_time=float(rft_ms) / 1000.0,
        use_forced_great_timing=False,
        timestamps=chart_sec,
        perfect_candidate_timestamps=perfect_cand_sec,
        great_candidate_timestamps=perfect_cand_sec,
        perfect_floor_timestamps=chart_sec if perfect_floor_sec is None else perfect_floor_sec,
    )
    return int(e) - int(a)


# A boundary note sits 10ms past the latest-Perfect fever cutoff: out at 0ms, in at -20ms.
#   activation idx 2 @ 200ms; latest-Perfect start = 240ms; rft = 1000ms => cutoff = 1240ms.
#   boundary note @ 1250ms: chart >= 1240 (FG: out) but 1250-20 = 1230 < 1240 (legal early: in).
_CHART_MS = [0, 100, 200, 400, 600, 800, 1000, 1250, 1500]
_ACTIVATION = 2
_RFT_MS = 1000

# Uniform-Perfect and held-tail (per-note lo) cases for cross-validation.
#   "case" = (chart_ms, activation_idx, rft_ms, lo)  where lo is scalar or per-note.
_VALIDATION_CASES = [
    ([0, 300, 600, 1330, 1600], 1, 1000, PERFECT_LO_MS),
    ([0, 100, 1230, 1260, 1600], 0, 1200, PERFECT_LO_MS),
    ([0, 50, 100, 1240, 1500], 2, 1100, PERFECT_LO_MS),
    # Held-tail note (idx 4, lo=-40) sits EARLIER than idx 3 once shifted -> raw earliest
    # envelope dips (1215 < 1230); only the prefix-max keeps the searchsorted exact.
    ([0, 100, 200, 1250, 1255, 1500], 2, 1000, [-20, -20, -20, -20, -40, -20]),
]


def test_groundtruth_greedy_matches_exhaustive():
    """The greedy ground truth equals an assumption-free monotonic brute force."""
    for chart, a, rft, lo in _VALIDATION_CASES:
        lo_arr = _lo_array(chart, lo)
        grid = [list(range(int(lo_arr[i]), PERFECT_HI_MS + 1, 5)) for i in range(len(chart))]
        assert _greedy_max_fever_extent(chart, a, rft, lo=lo) == _exhaustive_max_fever_extent(
            chart, a, rft, grid
        ), (chart, a, rft, lo)


def test_proposed_fix_matches_ground_truth():
    """The earliest-hit prefix-max searchsorted reproduces the brute-force max exactly,
    including the held-tail case where the raw earliest envelope is non-monotonic."""
    for chart, a, rft, lo in _VALIDATION_CASES + [(_CHART_MS, _ACTIVATION, _RFT_MS, PERFECT_LO_MS)]:
        assert _fg_fixed_fever_extent(chart, a, rft, lo=lo) == _greedy_max_fever_extent(
            chart, a, rft, lo=lo
        ), (chart, a, rft, lo)


def test_constructed_case_exposes_the_gap():
    """Sanity: on the constructed case the ground truth (and the fix) gain exactly one
    fever note over the live FG model."""
    gt = _greedy_max_fever_extent(_CHART_MS, _ACTIVATION, _RFT_MS)
    fixed = _fg_fixed_fever_extent(_CHART_MS, _ACTIVATION, _RFT_MS)
    live = _fg_edge_fever_extent(_CHART_MS, _ACTIVATION, _RFT_MS)
    assert gt == 6  # notes 2..7 (idx 7 @ 1250ms pulled in via a legal -20ms hit)
    assert fixed == 6  # the proposed fix matches
    assert live == 5  # live FG stops at idx 7 (boundary tested at offset 0)
    assert gt - live == 1


def test_every_counted_fever_note_is_legal_and_achievable():
    """LEGALITY: every fever note the fix counts is realized by ONE explicit hit
    assignment that is (a) in-window for every note, (b) monotonic in event time (a real
    legal hit order), and (c) replays under the server-order fever rule to EXACTLY the
    fix's count -- never an impossible or illegal configuration, never more than is legal."""
    for chart, a, rft, lo in _VALIDATION_CASES + [(_CHART_MS, _ACTIVATION, _RFT_MS, PERFECT_LO_MS)]:
        lo_arr = _lo_array(chart, lo)
        ev = _legal_max_inclusion_assignment(chart, a, rft, lo=lo)
        # (a) every hit is inside its own legal Perfect window [chart+lo, chart+hi].
        for i in range(len(chart)):
            off = ev[i] - chart[i]
            assert int(lo_arr[i]) <= off <= PERFECT_HI_MS, ("illegal offset", i, off, int(lo_arr[i]))
        # (b) event times never go backwards -> a legal, playable hit order.
        assert all(ev[i] >= ev[i - 1] for i in range(1, len(chart))), ("illegal hit order", ev)
        # (c) replay THIS assignment through the server-order fever rule.
        fever_end = ev[a] + rft
        replay_count = 0
        for i in range(a, len(chart)):
            if ev[i] < fever_end:
                replay_count += 1
            else:
                break  # monotonic events: once out, stays out
        # The legal replay reproduces exactly what the fix claims -> not impossible, not over-counted.
        assert replay_count == _fg_fixed_fever_extent(chart, a, rft, lo=lo), (chart, a, rft, lo)


def test_fix_is_optimal_and_never_regresses():
    """OPTIMAL + NO-REGRESSION: the fixed extent equals the assumption-free legal max
    (so it never over-counts impossible notes) and is always >= the live FG extent (so it
    can never score lower than today). The search array prefix_max(chart+lo) is pointwise
    <= chart, so searchsorted can only push the fever boundary later, never earlier."""
    for chart, a, rft, lo in _VALIDATION_CASES + [(_CHART_MS, _ACTIVATION, _RFT_MS, PERFECT_LO_MS)]:
        fixed = _fg_fixed_fever_extent(chart, a, rft, lo=lo)
        gt = _greedy_max_fever_extent(chart, a, rft, lo=lo)
        live = _fg_edge_fever_extent(chart, a, rft)
        assert fixed == gt, ("not the legal max", chart, a, rft, lo)
        assert fixed >= live, ("regressed below live FG", chart, a, rft, fixed, live)
        assert fixed <= len(chart) - a, ("exceeds notes-after-activation bound", chart, a, rft)
        # Explicit pointwise domination => monotone no-regression for ANY cutoff.
        earliest_pm = np.maximum.accumulate(np.asarray(chart, dtype=np.int64) + _lo_array(chart, lo))
        assert bool(np.all(earliest_pm <= np.asarray(chart, dtype=np.int64))), ("search array not <= chart", chart)


def test_fg_edge_end_models_endpoint_early_inclusion():
    """GATE (issue #42, now LANDED): the production FG fever extent — `_edge_end` searching
    the production earliest-Perfect floor envelope — equals the server-legal max over hit
    offsets. The same floor feeds the GPU precompute and the forced-counts replay in
    lockstep, so all three FG fever-extent paths model endpoint-early inclusion exactly."""
    from gear_optimizer.solver.timing_envelope import build_perfect_floor_envelope_sec

    gt = _greedy_max_fever_extent(_CHART_MS, _ACTIVATION, _RFT_MS)
    chart_sec = np.asarray(_CHART_MS, dtype=np.float32) / np.float32(1000.0)
    perfect_floor_sec = build_perfect_floor_envelope_sec(chart_sec, None)
    fixed = _fg_edge_fever_extent(_CHART_MS, _ACTIVATION, _RFT_MS, perfect_floor_sec)
    assert fixed == gt


# ---------------------------------------------------------------------------
# Chord-tied held-tail exactness (pre-existing chord-collapse under-count).
#
# The game registers every note's hit INDEPENDENTLY per lane (confirmed against the decompiled
# server), so a held tail (Perfect window [-40,+80]) that shares a timestamp with a narrower note
# may legally use its OWN wider reach. The old envelopes collapsed each chord to the intersection
# (group_low = max(lows), group_high = min(highs)) via `prepare_grouped_timing_windows`, capping
# the held tail and UNDER-counting fever when a chord-tied held tail was the activation (its +80
# latest hit capped to the chord's +40) or a boundary note (its -40 earliest capped to -20).
# The fix gives the FG fever-extent envelopes per-note windows. Held tails: note_type==3.
# ---------------------------------------------------------------------------


def _per_note_windows_ms(note_types):
    """Per-note (lo, hi) Perfect windows in ms, held-tail-aware (matches the production builder)."""
    from gear_optimizer.solver.timing_envelope import build_per_note_perfect_window_ms

    low, high = build_per_note_perfect_window_ms(
        np.asarray(note_types, np.int16),
        perfect_lower_ms=PERFECT_LO_MS,
        perfect_upper_ms=PERFECT_HI_MS,
        held_tail_type=3,
        held_tail_time_multiplier=2,
    )
    return np.asarray(low, np.int64), np.asarray(high, np.int64)


def _greedy_extent_pernote_hi(chart_ms, a, rft_ms, lo, hi):
    """Exact greedy with PER-NOTE hi (a held-tail activation reaches +80, not +40)."""
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


def _exhaustive_extent_pernote(chart_ms, a, rft_ms, lo, hi):
    """Assumption-free monotonic brute force with per-note lo AND hi."""
    n = len(chart_ms)
    lo_arr = _lo_array(chart_ms, lo)
    hi_arr = _lo_array(chart_ms, hi)
    grid = [range(int(lo_arr[i]), int(hi_arr[i]) + 1, 5) for i in range(n)]
    best = 0
    for combo in itertools.product(*grid):
        ev = [chart_ms[i] + combo[i] for i in range(n)]
        if any(ev[i] < ev[i - 1] for i in range(1, n)):
            continue
        fe = ev[a] + rft_ms
        best = max(best, sum(1 for i in range(a, n) if ev[i] < fe))
    return int(best)


def _grouped_floor_candidate_sec(chart_sec, note_types):
    """The OLD chord-collapsed envelopes: group by TIMESTAMP only, group_low = max(per-note
    lows), group_high = min(per-note highs) -- the genuine pre-fix chord intersection (built
    here directly, independent of the production grouper, which now splits chords by window)."""
    from gear_optimizer.solver.timing_envelope import (
        build_per_note_perfect_window_ms,
        floor_to_int_ms,
    )

    nt = np.asarray(note_types, np.int16)
    low, high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=PERFECT_LO_MS, perfect_upper_ms=PERFECT_HI_MS,
        held_tail_type=3, held_tail_time_multiplier=2,
    )
    low = np.asarray(low, np.int64)
    high = np.asarray(high, np.int64)
    ts_ms = np.asarray(floor_to_int_ms(np.asarray(chart_sec, np.float32)), np.int64)
    n = int(np.asarray(chart_sec).shape[0])
    starts = np.concatenate([[0], np.nonzero(ts_ms[1:] != ts_ms[:-1])[0] + 1]).astype(np.int64)
    ends = np.concatenate([starts[1:], [n]]).astype(np.int64)
    cand = np.empty(n, np.int64)
    floor = np.empty(n, np.int64)
    for gi in range(int(starts.shape[0])):
        s, e = int(starts[gi]), int(ends[gi])
        raw_low = int(np.max(low[s:e]))   # chord intersection: latest earliest-hit
        raw_high = int(np.min(high[s:e]))  # chord intersection: earliest latest-hit
        glo = min(raw_low, raw_high)
        ghi = max(raw_low, raw_high)
        cand[s:e] = int(ts_ms[s]) + ghi
        floor[s:e] = int(ts_ms[s]) + glo
    np.maximum.accumulate(floor, out=floor)
    return (cand.astype(np.float32) * np.float32(0.001), floor.astype(np.float32) * np.float32(0.001))


# (chart_ms, note_types, activation_idx, rft_ms, expected_legal_max_extent, grouped_under_count)
_CHORD_TAIL_CASES = [
    # held-tail ACTIVATION in a chord: +80 latest hit (capped to +40 by the chord) gains a note.
    ([0, 100, 200, 200, 1260, 1500], [1, 1, 1, 3, 1, 1], 3, 1000, 2, 1),
    # held-tail BOUNDARY (tail first in chord order): -40 earliest pulls a note past the +40 cutoff.
    ([0, 200, 1270, 1270, 1500], [1, 1, 3, 1, 1], 1, 1000, 2, 1),
]


def test_chord_tied_held_tail_greedy_matches_brute_force():
    """Per-note greedy == assumption-free per-note brute force on chord-tied held tails."""
    for chart, types, a, rft, expected, _under in _CHORD_TAIL_CASES:
        lo, hi = _per_note_windows_ms(types)
        g = _greedy_extent_pernote_hi(chart, a, rft, lo, hi)
        b = _exhaustive_extent_pernote(chart, a, rft, lo, hi)
        assert g == b == expected, (chart, types, a, rft, g, b, expected)


def test_production_envelope_models_chord_tied_held_tail_exactly():
    """GATE: the PRODUCTION FG fever extent (`_edge_end` over the production per-note candidate +
    floor envelopes built WITH held-tail note_types) equals the legal max over hit offsets for
    chord-tied held tails, and STRICTLY exceeds the pre-fix chord-collapsed extent (proving the
    case is non-vacuous)."""
    for chart, types, a, rft, expected, under in _CHORD_TAIL_CASES:
        lo, hi = _per_note_windows_ms(types)
        gt = _greedy_extent_pernote_hi(chart, a, rft, lo, hi)
        assert gt == expected
        chart_sec = np.asarray(chart, np.float32) / np.float32(1000.0)
        nt = np.asarray(types, np.int16)
        cand = build_perfect_candidate_envelope_sec(chart_sec, nt)
        floor = build_perfect_floor_envelope_sec(chart_sec, nt)
        e, _s, _c = _edge_end(
            n=len(chart), a=int(a), activation_great=False,
            real_fever_time=float(rft) / 1000.0, use_forced_great_timing=False,
            timestamps=chart_sec, perfect_candidate_timestamps=cand,
            great_candidate_timestamps=cand, perfect_floor_timestamps=floor,
        )
        prod_extent = int(e) - int(a)
        assert prod_extent == gt, ("production != legal max", chart, types, a, prod_extent, gt)
        # The OLD chord-collapsed envelopes under-counted by `under` notes on this case.
        old_cand, old_floor = _grouped_floor_candidate_sec(chart_sec, nt)
        oe, _os, _oc = _edge_end(
            n=len(chart), a=int(a), activation_great=False,
            real_fever_time=float(rft) / 1000.0, use_forced_great_timing=False,
            timestamps=chart_sec, perfect_candidate_timestamps=old_cand,
            great_candidate_timestamps=old_cand, perfect_floor_timestamps=old_floor,
        )
        old_extent = int(oe) - int(a)
        assert prod_extent - old_extent == under, ("chord-collapse gap not reproduced", chart, types, prod_extent, old_extent, under)
