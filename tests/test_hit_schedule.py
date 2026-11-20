"""The hit schedule through the plans: what a plan keeps, the room each input gets, and the plans no frame timing plays."""

import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS
from gear_optimizer.trace.hit_schedule import input_order, warm
from gear_optimizer.trace.reconstruct import UnplayableTrace
from tests.trace_support import force_greats_note_graph


_FASTEST_FRAME_MS = 1000.0 / 360.0


def _press(note):
    return note["hit_time_ms"] + note["delta_ms"]


def _section(activation, fever_end, cutoff_ms, **fields):
    return {"section": 1, "activation_index": activation, "fever_end_index": fever_end, "forced_start_index": 0,
            "forced_run_start_index": 0, "forced_run_count": 0, "activation_judgment": "perfect",
            "activation_hit_offset_ms": 0.0, "fever_window_end_ms": cutoff_ms, **fields}


def _plan(times_ms, lanes, trace, *, note_types=None, timing_mode="precise"):
    n = len(times_ms)
    return force_greats_note_graph(
        frontier_trace=trace, total_notes=n, timestamps=np.asarray(times_ms, dtype=np.float64) / 1000.0,
        note_types=np.ones(n, dtype=np.int16) if note_types is None else np.asarray(note_types, dtype=np.int16),
        lanes=np.asarray(lanes, dtype=np.int32), timing_mode=timing_mode,
    )


def _late_activation_chord(follower_ms, last_fever_ms):
    """A late-Great activation on lane 4 with a forced Great of its chord on lane 3, the next Perfect of lane 3 at
    `follower_ms`, and a last fever note that holds the activation late: the window lasts 8,000 ms."""
    times = [0, 500, 1000, 1000, follower_ms, 1400, last_fever_ms, 12000, 12500]
    lanes = [1, 2, 4, 3, 3, 1, 2, 1, 2]
    trace = [_section(2, 7, 9000.0 + 1000.0 + 149.0, forced_run_start_index=2, forced_run_count=2,
                      activation_judgment="late_great", activation_hit_offset_ms=149.0, fever_duration_ms=8000.0)]
    return times, lanes, trace


def test_a_tie_on_one_lane_shares_the_room_its_bands_leave():
    # The activation lands no earlier than 1,132 for the last fever note, and the next Perfect of lane 3 no later than
    # 1,150: the Great before it and that Perfect share those 18 ms.
    times, lanes, trace = _late_activation_chord(1110, 9150)
    graph = _plan(times, lanes, trace)

    great, perfect = graph[3], graph[4]
    assert great["input_order"] < perfect["input_order"]
    assert _press(perfect) - _press(great) >= _FASTEST_FRAME_MS
    assert 1150.0 - _press(perfect) >= _FASTEST_FRAME_MS


def test_inputs_with_no_frame_of_their_own_have_no_plan():
    # The same, with 1 ms between the activation's earliest hit and the Perfect's latest.
    times, lanes, trace = _late_activation_chord(1110, 9167)
    with pytest.raises(UnplayableTrace, match="no frame of its own"):
        _plan(times, lanes, trace)


def test_a_pair_just_a_fastest_frame_apart_has_a_plan():
    times, lanes, trace = _late_activation_chord(1110, 9165)
    graph = _plan(times, lanes, trace)
    assert _press(graph[4]) > _press(graph[3])


def test_one_tight_place_costs_only_its_own_inputs():
    # Notes 2 and 3 share lane 3 far from the tight chord: they are 20 ms apart and keep a frame margin.
    times, lanes, trace = _late_activation_chord(1110, 9150)
    times = [0, 500, *times[2:6], 5000, 5020, *times[6:]]
    lanes = [1, 2, *lanes[2:6], 3, 3, *lanes[6:]]
    trace[0]["fever_end_index"] += 2
    graph = _plan(times, lanes, trace)

    assert _press(graph[7]) - _press(graph[6]) >= FRAME_MARGIN_MS
    assert _press(graph[4]) - _press(graph[3]) < FRAME_MARGIN_MS


def test_a_window_keeps_a_frame_margin_on_both_sides_of_its_cutoff():
    # The window lasts 1,000 ms from note 1: note 2 at 1,950 stays in it, note 3 at 2,020 out.
    graph = _plan([0, 1000, 1950, 2020, 3000], [1, 2, 3, 4, 1], [_section(1, 3, 2000.0)])
    cutoff = graph[2]["fever_end_ms"]

    assert cutoff == _press(graph[1]) + 1000.0
    assert _press(graph[2]) <= cutoff - FRAME_MARGIN_MS + 1e-6
    assert _press(graph[3]) >= cutoff + FRAME_MARGIN_MS - 1e-6
    assert [note["fever"] for note in graph] == [False, True, True, False, False]


def test_an_on_time_activation_moves_only_as_far_as_its_window_needs():
    graph = _plan([0, 1000, 1950, 3000], [1, 2, 3, 4], [_section(1, 3, 2000.0)])
    assert graph[1]["delta_ms"] == 0.0


def test_a_great_goes_early_when_its_order_leaves_it_no_late_hit():
    # Through the ramp a chord keeps its chart order: the Great goes first, and a late hit would pass the Perfect's band.
    graph = _plan([0, 1000, 1000, 2000], [1, 2, 3, 4], [_section(3, 4, 3000.0, forced_run_start_index=1, forced_run_count=1)])

    assert graph[1]["delta_ms"] == pytest.approx(-20.0 - FRAME_MARGIN_MS)
    assert graph[2]["delta_ms"] == 0.0
    assert graph[1]["input_order"] < graph[2]["input_order"]


def test_non_precise_perfects_stay_on_time_and_a_tie_on_one_lane_has_no_plan():
    # A Great's first late hit lands on the next press of its lane, and the press before it leaves it no early hit.
    trace = [_section(4, 5, 2500.0, forced_run_start_index=1, forced_run_count=1)]
    with pytest.raises(UnplayableTrace, match="no frame of its own"):
        _plan([0, 10, 51, 1000, 1500], [1, 1, 1, 2, 3], trace, timing_mode="non-precise")


def test_non_precise_only_moves_greats():
    times = [0, 300, 395, 395, 1000, 1500]
    lanes, note_types = [1, 1, 1, 2, 3, 4], [2, 3, 1, 1, 1, 1]
    trace = [_section(5, 6, 2500.0, forced_run_start_index=1, forced_run_count=2)]
    graph = _plan(times, lanes, trace, note_types=note_types, timing_mode="non-precise")

    assert [note["delta_ms"] for note in graph if note["note_result"] == "Perfect"] == [0.0] * 4
    assert [note["input_order"] for note in graph] == sorted(note["input_order"] for note in graph)


def test_plans_use_the_games_whole_ms_chart_times():
    # float32 seconds carry noise that could invert the tie: chart times come back whole.
    seconds = np.asarray([0.095, 104.363, 104.363], dtype=np.float32)
    graph = force_greats_note_graph(
        frontier_trace=[_section(1, 3, 200000.0)], total_notes=3, timestamps=seconds,
        note_types=np.ones(3, dtype=np.int16), lanes=np.asarray([1, 2, 3], dtype=np.int32),
    )
    assert [note["hit_time_ms"] for note in graph] == [95.0, 104363.0, 104363.0]


def _order(lanes, ranks, links=()):
    pairs = np.asarray(links, dtype=np.int64).reshape(-1, 2)
    return input_order(np.asarray(lanes, dtype=np.int64), np.asarray(ranks, dtype=np.int64), pairs[:, 0], pairs[:, 1]).tolist()


def test_input_order_merges_the_lanes_by_rank():
    assert _order([1, 2, 1, 2], [0, 3, 1, 2]) == [0, 2, 1, 3]


def test_input_order_keeps_a_lanes_chart_order_whatever_the_rank():
    assert _order([1, 1, 2], [2, 0, 1]) == [2, 0, 1]


def test_input_order_holds_a_note_for_its_link():
    assert _order([1, 2, 3], [0, 1, 2], [(2, 0)]) == [1, 2, 0]


def test_input_order_of_contradictory_links_is_empty():
    assert _order([1, 2], [0, 1], [(0, 1), (1, 0)]) == []


def test_warm_runs_the_kernels():
    warm()


def _reference_hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle):
    """The per-activation full-pass _hits implementation replaced by the incremental sweep, verbatim."""
    from gear_optimizer.trace import hit_schedule as hs

    n = low_ms.shape[0]
    low_ms, ceiling_ms = low_ms.copy(), ceiling_ms.copy()
    earliest, latest = np.empty(n, np.float64), np.empty(n, np.float64)
    source = np.empty(n, np.int64)
    for row in range(sections.shape[0]):
        k = int(sections[row, 0])
        hs._earliest(links, margin, low_ms, ceiling_ms, earliest, source)
        hs._latest(links, margin, ceiling_ms, latest)
        at = 0.5 * (earliest[k] + latest[k]) if middle[row] else min(max(inputs.chart_ms[k], earliest[k]), latest[k])
        low_ms[k], ceiling_ms[k] = at, at
    hs._latest(links, margin, ceiling_ms, latest)
    hits = np.empty(n, np.float64)
    for k in range(n):
        floor = low_ms[k]
        if k:
            floor = max(floor, hits[k - 1])
        for c in range(links.into_start[k], links.into_start[k + 1]):
            link = links.into[c]
            floor = max(floor, hits[links.before[link]] + links.fixed[link] + margin[link])
        hits[k] = min(max(inputs.chart_ms[k], floor), latest[k])
    return hits


def test_incremental_hits_matches_reference_at_sub_slack_activation_boundary():
    """A fixed activation rising by less than _SLACK_MS (1e-9 ms) still propagates forward to later activations."""
    from gear_optimizer.trace import hit_schedule as hs

    chart_ms = np.array([0.8e-9, 0.0, 0.0, 0.0], dtype=np.float64)
    low_ms = np.array([0.0, -40.0, -40.0, -40.0], dtype=np.float64)
    ceiling_ms = np.array([1.6e-9, 1.6e-9, 0.9e-9, 100.0], dtype=np.float64)
    lanes = np.array([0, 1, 2, 3], dtype=np.int64)
    flag = np.zeros(4, dtype=np.bool_)
    fever = np.array([True, False, True, False], dtype=np.bool_)
    inputs = hs.Inputs(
        chart_ms, low_ms, ceiling_ms, np.zeros(4), np.full(4, np.inf), np.full(4, -np.inf), lanes, flag, flag, fever
    )
    sections = np.array([[0.0, 2.0, 500.0], [2.0, 4.0, 500.0]], dtype=np.float64)
    middle = np.array([False, True], dtype=np.bool_)
    links = hs._Links(
        np.array([0], dtype=np.int64),
        np.array([2], dtype=np.int64),
        np.array([0.0]),
        np.array([0], dtype=np.int64),
        np.array([0, 0, 0, 1, 1], dtype=np.int64),
        np.empty(0, dtype=np.int64),
    )
    margin = np.array([0.0])
    got = hs._hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle)
    ref = _reference_hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle)
    assert np.array_equal(got, ref)
    assert got[2] > got[0]


def test_incremental_hits_matches_reference_across_tails_chords_and_back_links():
    """Differential test of _hits against _reference_hits across held tails, dense chords, multiple activation
    sections, back-links, settled tight margins, and mixed centered/chart-time activations."""
    from gear_optimizer.trace import hit_schedule as hs, note_graph as ng

    rng = np.random.default_rng(2026)
    checked = 0
    with_back_links = 0
    for _ in range(800):
        n = int(rng.integers(8, 130))
        gaps = rng.choice([0.0, 0.0, 3.0, 8.0, 17.0, 40.0, 120.0, 240.0], size=n)
        chart_ms = np.cumsum(gaps)
        lanes = rng.integers(0, 4, size=n, dtype=np.int64)
        tail = rng.random(n) < 0.25
        great = rng.random(n) < 0.22
        n_sec = int(rng.integers(2, 6))
        starts = np.sort(rng.choice(np.arange(0, max(1, n - 2)), size=min(n_sec, max(1, n - 2)), replace=False))
        fever = np.zeros(n, dtype=np.bool_)
        sec_rows = []
        for idx, s in enumerate(starts):
            stop = int(starts[idx + 1]) if idx + 1 < len(starts) else n
            great[s] = bool(rng.random() < 0.2)
            end_in = int(rng.integers(s, stop))
            fever[s : end_in + 1] = True
            dur = float(max(5.0, chart_ms[end_in] - chart_ms[s] + rng.uniform(5.0, 85.0)))
            sec_rows.append((float(s), float(stop), dur))
        sections = np.array(sec_rows, dtype=np.float64).reshape(-1, 3)
        middle = rng.random(sections.shape[0]) < 0.6
        p_hi = np.where(tail, 80.0, 40.0)
        p_lo = np.where(tail, -80.0, -40.0)
        g_lo = np.where(great, np.where(tail, 80.0, 40.0), p_lo)
        g_hi = np.where(great, np.where(tail, 200.0, 140.0), p_hi)
        may_early = great.copy()
        may_early[starts] = False
        inputs = hs.Inputs(
            chart_ms,
            chart_ms + g_lo,
            chart_ms + g_hi,
            np.zeros(n, dtype=np.float64),
            np.where(may_early, chart_ms + np.where(tail, -190.0, -140.0), np.inf),
            np.where(may_early, chart_ms + np.where(tail, -80.0, -40.0), -np.inf),
            lanes,
            tail,
            great,
            fever,
        )
        links = hs._links_of(inputs, sections)
        whole_ms = np.ceil(links.fixed) - links.fixed + hs._STRICT_MS
        margin = np.where(links.fixed == 0.0, hs._FASTEST_FRAME_MS, np.where(links.fixed > 0.0, whole_ms, 0.0))
        earliest, source = np.empty(n, np.float64), np.empty(n, np.int64)
        low_ms, high_ms = hs._pick_bands(links, inputs, FRAME_MARGIN_MS)
        if hs._earliest(links, margin, low_ms, high_ms + inputs.reach_ms, earliest, source) >= 0:
            low_ms, high_ms = hs._pick_bands(links, inputs, hs._FASTEST_FRAME_MS)
            if hs._earliest(links, margin, low_ms, high_ms + inputs.reach_ms, earliest, source) >= 0:
                continue
        margin[:] = FRAME_MARGIN_MS
        ceiling_ms = np.maximum(high_ms - FRAME_MARGIN_MS, low_ms)
        try:
            if hs._settle_margins(links, low_ms, high_ms, margin, ceiling_ms) >= 0:
                continue
        except ValueError:
            continue
        checked += 1
        if links.back.shape[0] >= 2:
            with_back_links += 1
        got = hs._hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle)
        ref = _reference_hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle)
        assert np.allclose(got, ref, rtol=0.0, atol=1e-12)
    assert checked >= 80 and with_back_links >= 40

    # Also check _early_greats O(N) prefix-max sweep against the per-anchor loop it replaced.
    for seed in range(25):
        sub_rng = np.random.default_rng(seed)
        n = 90
        ts = np.cumsum(sub_rng.choice([0, 0, 15, 45, 110], size=n)).astype(np.float64) / 1000.0
        ntypes = np.where(sub_rng.random(n) < 0.25, 3, 1).astype(np.int16)
        lanes = sub_rng.integers(1, 5, size=n, dtype=np.int32)
        plan = ng._new_plan(n, ts, ntypes, lanes, "non-precise", 0)
        plan.great[:] = sub_rng.random(n) < 0.3
        secs = [
            ng._Section(1, 10, 28, "perfect", 0.0, 2000.0, 1000.0, 0, 0, 0, 0, 0, ()),
            ng._Section(2, 42, 67, "perfect", 0.0, 4000.0, 1000.0, 28, 28, 0, 28, 28, ()),
        ]
        got_early = ng._early_greats(plan, secs)
        # Recompute anchor check via the original per-section loop.
        ref_early = got_early.copy()
        # Verify no False positive or False negative vs explicit anchor loop on unconstrained base mask:
        hit_ms, great, band_ms = plan.hit_ms, plan.great, plan.band_ms
        late_ms = hit_ms + np.where(great, band_ms[:, 2, 0], 0.0)
        next_late_ms, from_last = np.full(n, np.inf), np.full(n, np.inf)
        for lane in np.unique(plan.lanes):
            notes = np.flatnonzero(plan.lanes == lane)
            next_late_ms[notes[:-1]] = late_ms[notes[1:]]
            from_last[notes[1:]] = np.diff(hit_ms[notes])
        chord = np.cumsum(np.r_[0, np.diff(hit_ms) != 0.0])
        first_perfect = np.full(chord[-1] + 1, n, dtype=np.int64)
        np.minimum.at(first_perfect, chord[~great], np.flatnonzero(~great))
        room_late, room_early = next_late_ms - late_ms, from_last + band_ms[:, 1, 1]
        ref_early = ((room_late < FRAME_MARGIN_MS) & (room_early > room_late)) | (
            (np.arange(n) < first_perfect[chord]) & (first_perfect[chord] < n)
        )
        ref_early &= great
        ref_early[[sec.activation for sec in secs]] = False
        for sec in secs:
            for anchor in (sec.activation, min(sec.fever_end, n - 1)):
                ref_early[anchor + 1 :] &= (hit_ms + band_ms[:, 1, 1] - FRAME_MARGIN_MS)[anchor + 1 :] >= hit_ms[anchor]
        assert np.array_equal(got_early, ref_early)


def test_scored_pairs_matches_bruteforce_with_reordered_high_perfect_time_notes():
    """_scored_pairs matches a truly exhaustive O(N^2) oracle across both branches even when input order reorders
    chart_ms and high Perfect Time widens hit bands past 390 ms."""
    from gear_optimizer.trace import hit_schedule as hs
    from gear_optimizer.trace.note_graph import _tap_and_tail_bands

    rng = np.random.default_rng(77)
    bands = _tap_and_tail_bands(160)  # max Perfect Time (tail band spans > 600 ms)
    n = 140
    base_chart = np.cumsum(rng.choice([0.0, 12.0, 28.0, 65.0], size=n))
    # Reorder note 115 earlier than distant note 112 so BOTH branch 1 (x=99) and branch 2 (x=108) must look past 112.
    chart_ms = base_chart.copy()
    chart_ms[112] = chart_ms[108] + 900.0
    chart_ms[115] = chart_ms[108] + 45.0
    tail = rng.random(n) < 0.35
    great = rng.random(n) < 0.4
    lanes = rng.integers(0, 4, size=n, dtype=np.int64)
    great[99], great[108], great[115] = False, False, True
    lanes[99], lanes[108], lanes[115] = 0, 0, 1
    t_idx = tail.astype(np.int64)
    low_ms = chart_ms + np.where(great, bands[t_idx, 2, 0], bands[t_idx, 0, 0])
    high_ms = chart_ms + np.where(great, bands[t_idx, 2, 1], bands[t_idx, 0, 1])
    early_lo = np.where(great, chart_ms + bands[t_idx, 1, 0], np.inf)
    early_hi = np.where(great, chart_ms + bands[t_idx, 1, 1], -np.inf)
    activation = np.zeros(n, dtype=np.bool_)
    wasted = np.zeros(n, dtype=np.bool_)
    activation[[15, 112, 115]] = True
    wasted[[45, 118]] = True
    inputs = hs.Inputs(
        chart_ms, low_ms, high_ms, np.zeros(n), early_lo, early_hi, lanes, tail, great, np.zeros(n, dtype=np.bool_)
    )

    got = hs._scored_pairs(inputs, activation, wasted)
    # Truly exhaustive O(N^2) reference: never breaks on timestamp order and uses no span constant.
    expected = []
    for x in range(n):
        x_sp = bool(activation[x] or wasted[x])
        if activation[x] and great[x] and x >= hs.HEAD_NOTES:
            continue
        x_hi = high_ms[x] + FRAME_MARGIN_MS
        for y in range(x + 1, n):
            if (
                lanes[x] != lanes[y]
                and great[x] != great[y]
                and min(low_ms[y], early_lo[y]) < x_hi
                and (y < hs.HEAD_NOTES or x_sp or activation[y] or wasted[y])
            ):
                expected.append([x, y])
    expected_arr = np.asarray(expected, dtype=np.int64).reshape(-1, 2)
    np.testing.assert_array_equal(got, expected_arr)
    got_pairs = {(p[0], p[1]) for p in got.tolist()}
    assert (99, 115) in got_pairs and (108, 115) in got_pairs
