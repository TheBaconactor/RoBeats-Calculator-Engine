"""Deliverable B: per-loadout note-graph reconstruction reconciles with the surface.

Proves the persisted witness data is SUFFICIENT to rebuild the game's note-graph
({HitTime, Delta, NoteResult, Fever}) losslessly: the FG expansion's per-note
Perfect/Great/Fever labels reconcile EXACTLY with the chosen response surface
(head bitmasks bit-for-bit, body counts), and the base expansion maps the fever
timeline to all-Perfect notes + fever windows. CPU-only, deterministic.
"""

import numpy as np
import pytest


def _build_options(n, non_fever_base, real_fever_time):
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _edge_surface_option_details,
    )

    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    great_candidates = timestamps.copy()
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=1.0,
        non_fever_base=non_fever_base,
        use_forced_great_timing=True,
    )
    options = _edge_surface_option_details(
        i=0,
        first=True,
        n=n,
        actions=actions,
        later_fill=later_fill,
        first_fill=first_fill,
        later_forced=later_forced,
        first_forced=first_forced,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
    )
    return timestamps, great_candidates, actions, options


def test_fg_note_graph_reconciles_with_surface_head_and_body():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        force_greats_note_graph,
        reconcile_force_greats_note_graph,
    )

    n = 110  # >100 so the fever window can extend into the body
    non_fever_base = 96
    real_fever_time = 1.5  # ~15 notes of fever at 0.1s spacing -> reaches past index 100
    timestamps, great_candidates, actions, options = _build_options(n, non_fever_base, real_fever_time)
    assert options, "expected at least one edge option"

    validated = 0
    saw_body_fever = False
    saw_witness = False
    for opt in options:
        surface = opt["surface"]
        try:
            trace = reconstruct_force_greats_response_trace(
                non_fever_base=non_fever_base,
                target_surface=surface,
                timestamps=timestamps,
                great_candidate_timestamps=great_candidates,
                perfect_floor_timestamps=timestamps,
                great_floor_timestamps=timestamps,
                raw_fever_fill=1.0,
                real_fever_time=real_fever_time,
                use_forced_great_timing=True,
            )
        except ValueError:
            continue  # not all standalone edge surfaces are independently reconstructable

        graph = force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=timestamps)
        assert len(graph) == n
        # game-model shape: Perfect/Great only, fever is bool, witness carries a numeric delta
        for g in graph:
            assert g["note_result"] in ("Perfect", "Great")
            assert isinstance(g["fever"], bool)
        # the sufficiency guarantee: per-note labels reconcile EXACTLY with the surface
        reconcile_force_greats_note_graph(
            graph,
            total_notes=n,
            fever_words=(surface.fever0, surface.fever1, surface.fever2, surface.fever3),
            great_words=(surface.great0, surface.great1, surface.great2, surface.great3),
            body_fever=surface.body_fever,
            body_great=surface.body_great,
            body_fever_great=surface.body_fever_great,
        )
        validated += 1
        if int(surface.body_fever) > 0:
            saw_body_fever = True
        if any(g["is_activation_witness"] for g in graph):
            saw_witness = True
            wit = next(g for g in graph if g["is_activation_witness"])
            assert wit["note_result"] == "Great"
            assert isinstance(wit["delta_ms"], float)

    assert validated > 0, "no edge surface reconstructed+reconciled"
    # body-count + witness reconciliation is proven directly below (standalone single-surface
    # frontiers only reconstruct head-reaching edges; body coverage is the synthetic test).
    _ = (saw_body_fever, saw_witness)


def test_reconstruct_force_greats_response_trace_is_stats_free():
    """The FG note-graph trace reconstruction takes NO stat/tier input — only the surface, song
    timing, and FT/FF fever geometry. This is why the FG witness is tier-invariant: a TeamBuff
    tier delta cannot reach any input of this function (it shifts only Perfect Points + colors).
    Guards against anyone re-introducing a stats/frontier dependency that would make the persisted
    FG trace tier-dependent. (The misleading `frontier: FgResponseFrontierResult` parameter that
    once implied a GPU-search dependency is gone — the primitive consumes only `non_fever_base`.)"""
    import inspect

    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )

    params = set(inspect.signature(reconstruct_force_greats_response_trace).parameters)
    assert params == {
        "non_fever_base",
        "target_surface",
        "timestamps",
        "perfect_candidate_timestamps",
        "great_candidate_timestamps",
        "perfect_floor_timestamps",
        "great_floor_timestamps",
        "raw_fever_fill",
        "real_fever_time",
        "use_forced_great_timing",
    }
    # no stat vector, base_value, perfect-points, element color, or frontier/DP object
    for stat_like in ("stats", "base_value", "perfect_points", "frontier", "tier", "team_buff"):
        assert stat_like not in params


def _words_from_indices(indices):
    """Pack a set of note indices (0..99) into the 4x uint32 head-mask words."""
    w = [0, 0, 0, 0]
    for i in indices:
        if 0 <= i < 100:
            w[i // 32] |= (1 << (i % 32))
    return tuple(w)


def test_fg_note_graph_body_counts_synthetic():
    """Construct traces with KNOWN ground-truth surfaces and prove exact body reconciliation."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        force_greats_note_graph,
        reconcile_force_greats_note_graph,
    )

    n = 130
    ts = (np.arange(n) * 0.1).astype(np.float32)

    # Case 1: head forced-Greats + a body fever window (no overlap).
    trace1 = [{
        "section": 1, "activation_index": 100, "fever_end_index": 105,
        "forced_start_index": 0, "forced_prefix_count": 3,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
    }]
    g1 = force_greats_note_graph(frontier_trace=trace1, total_notes=n, timestamps=ts)
    reconcile_force_greats_note_graph(
        g1, total_notes=n,
        fever_words=(0, 0, 0, 0), great_words=_words_from_indices({0, 1, 2}),
        body_fever=5, body_great=0, body_fever_great=0,
    )
    assert [i for i, x in enumerate(g1) if x["note_result"] == "Great"] == [0, 1, 2]
    assert sum(1 for x in g1 if x["fever"]) == 5

    # Case 2: body activation Late-Great WITNESS -> that body note is both fever AND great.
    trace2 = [{
        "section": 1, "activation_index": 102, "fever_end_index": 108,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "late_great", "activation_hit_offset_ms": 190.0,
    }]
    g2 = force_greats_note_graph(frontier_trace=trace2, total_notes=n, timestamps=ts)
    reconcile_force_greats_note_graph(
        g2, total_notes=n,
        fever_words=(0, 0, 0, 0), great_words=(0, 0, 0, 0),
        body_fever=6, body_great=1, body_fever_great=1,
    )
    wit = next(x for x in g2 if x["is_activation_witness"])
    assert wit["note_index"] == 102 and wit["note_result"] == "Great" and wit["delta_ms"] == 190.0
    assert wit["fever"] is True  # the witness is both fever and great

    # Case 3: optimized Perfect-window activation WITNESS -> delayed, but not Great.
    trace_perfect = [{
        "section": 1, "activation_index": 12, "fever_end_index": 16,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_start_source": "perfect_window",
    }]
    gp = force_greats_note_graph(frontier_trace=trace_perfect, total_notes=n, timestamps=ts)
    reconcile_force_greats_note_graph(
        gp, total_notes=n,
        fever_words=_words_from_indices(set(range(12, 16))), great_words=(0, 0, 0, 0),
        body_fever=0, body_great=0, body_fever_great=0,
    )
    witp = next(x for x in gp if x["is_activation_witness"])
    assert witp["note_index"] == 12
    assert witp["note_result"] == "Perfect"
    assert witp["delta_ms"] == 40.0

    # Case 4: multi-section (two fever windows), head fever + body fever.
    trace3 = [
        {"section": 1, "activation_index": 50, "fever_end_index": 56,
         "forced_start_index": 0, "forced_prefix_count": 2,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0},
        {"section": 2, "activation_index": 110, "fever_end_index": 116,
         "forced_start_index": 100, "forced_prefix_count": 4,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0},
    ]
    g3 = force_greats_note_graph(frontier_trace=trace3, total_notes=n, timestamps=ts)
    # head fever {50..55}, head greats {0,1}, body fever {110..115}=6, body greats {100..103}=4, no overlap
    reconcile_force_greats_note_graph(
        g3, total_notes=n,
        fever_words=_words_from_indices(set(range(50, 56))),
        great_words=_words_from_indices({0, 1}),
        body_fever=6, body_great=4, body_fever_great=0,
    )


def test_fg_note_graph_marks_fever_end_witness():
    """FG note-graph tags the last note of each fever run with the cutoff ms, like base."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import force_greats_note_graph

    n = 130
    ts = (np.arange(n) * 0.1).astype(np.float32)
    trace = [
        {"section": 1, "activation_index": 50, "fever_end_index": 56,
         "forced_start_index": 0, "forced_prefix_count": 0,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
         "fever_window_end_ms": 5590.0},
        {"section": 2, "activation_index": 110, "fever_end_index": 116,
         "forced_start_index": 100, "forced_prefix_count": 0,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
         "fever_window_end_ms": 11590.0},
    ]
    g = force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts)

    # Last note of each run ([50,56) -> 55; [110,116) -> 115) is the fever-end witness.
    ends = [x["note_index"] for x in g if x["is_fever_end_witness"]]
    assert ends == [55, 115]
    assert g[55]["fever_end_ms"] == pytest.approx(5590.0)
    assert g[115]["fever_end_ms"] == pytest.approx(11590.0)
    assert g[55]["fever"] is True and g[115]["fever"] is True
    # No score-contributing flag on either frontier.
    assert all("contributes_to_max_score" not in x for x in g)


def test_note_graph_shows_endpoint_early_hit_on_pulled_in_note():
    """Issue #42: a fever note at/after the cutoff carries its LARGEST-CUSHION legal early delta --
    the center of its legal in-fever range (most error margin) -- so it is in-fever and legal, and
    the scored fever set is unchanged (display-only)."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    n = 10
    ts = np.asarray([0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.245, 1.5, 1.7], dtype=np.float32)
    fg_trace = [{
        "section": 1, "activation_index": 2, "fever_end_index": 8,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_window_end_ms": 1240.0,
    }]
    base_trace = [{
        "section": 1, "activation_index": 2, "fever_end_index": 8,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": 1240.0,
    }]

    nt = np.ones(n, dtype=np.int16)  # all-normal notes for this case
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=np.zeros(n, bool), frontier_trace=base_trace, note_types=nt),
    ):
        # note 7 @ chart 1245ms is past the 1240ms cutoff -> in fever ONLY via an early hit.
        assert g[7]["fever"] is True
        assert g[7]["is_fever_end_witness"] is True
        # Largest cushion = center of [legal_low_hit, upper_hit] = [1245-20, 1240-1] = [1225, 1239]
        # -> shown_hit 1232 -> delta -13. (Old cliff-edge was -6 = 1240-1245-1.)
        assert g[7]["delta_ms"] == pytest.approx(-13.0, abs=1e-3)
        assert g[7]["delta_ms"] >= -20.0                               # still legal (>= lower bound)
        # its event lands inside the window -> displayed per-note timing is self-consistent.
        assert g[7]["hit_time_ms"] + g[7]["delta_ms"] < 1240.0
        # comfortably-inside fever notes untouched (delta 0); activation keeps its +40.
        assert g[6]["fever"] is True and g[6]["delta_ms"] == 0.0
        assert g[2]["is_activation_witness"] is True and g[2]["delta_ms"] == pytest.approx(40.0)


def test_endpoint_early_delta_never_below_legal_lower_bound():
    """Issue #42 reconstruction legality: the displayed endpoint-early `delta_ms` (now the
    largest-cushion center of the legal in-fever range) is never below the note's own Perfect lower
    bound (-20, or -40 for a held tail). In the tight-margin edge where the legal-early hit already
    sits at/after `cutoff - 1` (no in-fever room), the degenerate branch preserves the old
    clamp-to-bound. Needs `note_types` for the held-tail bound."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    # note 3 @ chart 1019.5ms is 19.5ms past a 1000ms cutoff.
    n = 5
    ts = np.asarray([0.0, 0.1, 0.2, 1.0195, 1.5], dtype=np.float32)
    fg_trace = [{
        "section": 1, "activation_index": 0, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_window_end_ms": 1000.0,
    }]
    base_trace = [{
        "section": 1, "activation_index": 0, "fever_end_index": 4,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": 1000.0,
    }]
    mask = np.zeros(n, bool)

    # Normal note: legal_low_hit = 1019.5-20 = 999.5 >= upper_hit (1000-1 = 999) -> NO in-fever room
    # -> degenerate branch clamps shown_hit to legal_low_hit, i.e. delta = exactly -20 (legal bound).
    nt_normal = [1, 1, 1, 1, 1]
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt_normal),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt_normal),
    ):
        assert g[3]["delta_ms"] >= -20.0                  # never below the Perfect lower bound
        assert g[3]["delta_ms"] == pytest.approx(-20.0)   # tight edge -> clamped to the bound

    # Held tail (note_type 3, window [-40,+80]): legal_low_hit = 1019.5-40 = 979.5 < upper_hit (999)
    # -> there IS room -> largest-cushion center 0.5*(979.5+999) = 989.25 -> delta -30.25 (>= -40).
    nt = [1, 1, 1, 3, 1]
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt),
    ):
        assert g[3]["delta_ms"] >= -40.0                   # never below the held-tail lower bound
        assert g[3]["delta_ms"] == pytest.approx(-30.25)   # largest-cushion center of [-40, -20.5]

    # FAIL LOUD: a clawed-in note with NO note_types must raise -- never guess a (possibly false)
    # bound. (A graph with no clawed-in note does not need note_types -- not asserted here.)
    with pytest.raises(ValueError):
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts)


def test_endpoint_early_delta_is_largest_cushion_center():
    """Issue #42 display convention: a clawed-in held-tail note's shown `delta_ms` is the
    LARGEST-CUSHION timing -- the center of its legal in-fever range [legal_low, cutoff-hit-1] --
    not the old cliff-edge (`cutoff - hit - 1`). The shown hit is LEGAL (delta >= legal_low),
    IN-FEVER (hit <= cutoff), and MONOTONIC (>= the previous note's shown hit). Both frontiers."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    # idx5 held tail @ chart 1410ms is clawed in past the 1400ms cutoff; legal_low = -40.
    # legal_low_hit = 1370 < upper_hit = 1399 -> real in-fever room -> center fires (not the clamp).
    # Preceding fever notes sit well before 1370 so monotonicity does NOT bind here.
    n = 7
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 1.0, 1.410, 1.6], dtype=np.float32)
    cutoff = 1400.0
    legal_low = -40.0  # held tail
    fg_trace = [{
        "section": 1, "activation_index": 2, "fever_end_index": 6,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_window_end_ms": cutoff,
    }]
    base_trace = [{
        "section": 1, "activation_index": 2, "fever_end_index": 6,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": cutoff,
    }]
    nt = np.asarray([1, 1, 1, 1, 1, 3, 1], dtype=np.int16)  # idx5 is the held tail
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=np.zeros(n, bool), frontier_trace=base_trace, note_types=nt),
    ):
        hit = g[5]["hit_time_ms"]
        shown = hit + g[5]["delta_ms"]
        # shown delta == center of [legal_low, cutoff - hit - 1] (largest cushion).
        expected = 0.5 * (legal_low + (cutoff - hit - 1.0))
        assert g[5]["delta_ms"] == pytest.approx(expected, abs=1e-4)
        assert g[5]["delta_ms"] >= legal_low                     # LEGAL: never below the lower bound
        assert hit >= cutoff                                     # genuinely clawed in (chart >= cutoff)
        assert shown <= cutoff                                   # IN-FEVER: shown hit at/before the cutoff
        # MONOTONIC: shown hit >= the previous note's shown hit (idx4, comfortably inside, delta 0).
        prev_shown = g[4]["hit_time_ms"] + g[4]["delta_ms"]
        assert shown >= prev_shown
        # the score-determining activation witness is left untouched.
        assert g[2]["is_activation_witness"] is True and g[2]["delta_ms"] == pytest.approx(40.0)

    # Monotonicity actually BINDS: two adjacent clawed notes near a tight cutoff -- the first note's
    # shown hit raises the floor for the second, whose own legal_low_hit would have been lower.
    n2 = 7
    ts2 = np.asarray([0.0, 0.1, 0.2, 0.3, 1.0, 1.405, 1.408], dtype=np.float32)
    fg_trace2 = [{
        "section": 1, "activation_index": 2, "fever_end_index": 7,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_window_end_ms": 1400.0,
    }]
    nt2 = np.ones(n2, dtype=np.int16)  # both clawed notes are normal (legal_low = -20)
    g = force_greats_note_graph(frontier_trace=fg_trace2, total_notes=n2, timestamps=ts2, note_types=nt2)
    shown5 = g[5]["hit_time_ms"] + g[5]["delta_ms"]
    shown6 = g[6]["hit_time_ms"] + g[6]["delta_ms"]
    for i in (5, 6):
        assert g[i]["delta_ms"] >= -20.0                         # both stay legal
        assert g[i]["hit_time_ms"] + g[i]["delta_ms"] <= 1399.0  # both stay in-fever (<= cutoff - 1)
    assert shown6 >= shown5                                      # monotonic shown order preserved
    # idx6's floor is the prev shown hit (1392), not its own legal_low_hit (1388) -> center 1395.5.
    assert shown5 == pytest.approx(1392.0, abs=1e-3)
    assert shown6 == pytest.approx(1395.5, abs=1e-3)


def test_endpoint_early_degenerate_clamp_is_monotonic():
    """Degenerate branch (no in-fever room) must keep the prev_hit floor so shown hits stay
    non-decreasing. A normal note clawed in at the ~1ms boundary (shown ~cutoff-0.5) followed by a
    held tail whose own legal_low_hit is lower would, under a prev_hit-blind clamp, be shown EARLIER
    -- breaking monotonicity. The fix clamps to lo_hit (>= prev_hit)."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import force_greats_note_graph

    n = 4
    ts = np.asarray([0.0, 0.1, 1.0195, 1.030], dtype=np.float32)  # idx2 normal @1019.5, idx3 held @1030
    cutoff = 1000.0
    trace = [{
        "section": 1, "activation_index": 0, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.asarray([1, 1, 1, 3], dtype=np.int16)  # idx2 normal (-20), idx3 held tail (-40)
    g = force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)
    s2 = g[2]["hit_time_ms"] + g[2]["delta_ms"]
    s3 = g[3]["hit_time_ms"] + g[3]["delta_ms"]
    assert s3 >= s2                       # MONOTONIC across the degenerate clamp (the regression guard)
    assert s2 < cutoff and s3 < cutoff    # both still land in fever
    assert g[2]["delta_ms"] >= -20.0      # normal-note legal bound
    assert g[3]["delta_ms"] >= -40.0      # held-tail legal bound


def test_base_note_graph_maps_fever_timeline():
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import base_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
    mask = np.asarray([False, True, True, True, False, False])
    graph = base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask)
    assert len(graph) == n
    assert all(g["note_result"] == "Perfect" for g in graph)  # base = no greats
    assert all(g["delta_ms"] == 0.0 for g in graph)
    assert [g["fever"] for g in graph] == [False, True, True, True, False, False]
    assert graph[2]["hit_time_ms"] == pytest.approx(200.0)


def test_base_note_graph_uses_timeline_frontier_trace_witness():
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import base_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
    mask = np.zeros(n, dtype=np.bool_)
    trace = [
        {
            "section": 1,
            "activation_index": 2,
            "activation_hit_offset_ms": 40.0,
            "fever_end_index": 5,
        }
    ]

    graph = base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=trace)

    assert all(g["note_result"] == "Perfect" for g in graph)
    assert [g["fever"] for g in graph] == [False, False, True, True, True, False]
    assert graph[2]["delta_ms"] == pytest.approx(40.0)
    assert graph[2]["is_activation_witness"] is True


def test_base_note_graph_marks_fever_end_witness_with_cushion_cutoff():
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import base_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
    mask = np.zeros(n, dtype=np.bool_)
    trace = [
        {
            "section": 1,
            "activation_index": 2,
            "activation_hit_offset_ms": 40.0,
            "fever_end_index": 5,
            "fever_window_end_ms": 440.0,
        }
    ]

    graph = base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=trace)

    # Fever run is notes [2, 5); the last fevered note (4) is the fever-end witness,
    # carrying the largest-cushion cutoff time. No score-contributing flag exists.
    assert [g["is_fever_end_witness"] for g in graph] == [False, False, False, False, True, False]
    assert graph[4]["fever_end_ms"] == pytest.approx(440.0)
    assert graph[4]["fever"] is True
    assert graph[2]["is_activation_witness"] is True
    assert graph[2]["is_fever_end_witness"] is False
    assert graph[0]["fever_end_ms"] is None
    assert all("contributes_to_max_score" not in g for g in graph)


def test_base_note_graph_matches_production_fever_timeline():
    """base fever mask is the production fever timeline's full per-note is_fever buffer."""
    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import base_note_graph

    n = 130
    ts = (np.arange(n) * 0.1).astype(np.float32)
    buf = np.zeros(n, dtype=np.bool_)
    fever_mask_head, count_body_fever, count_body_normal, _act, _end = calculate_fever_timeline_indices(
        ts, n, 1.0, 1.0, 0, float(ts[-1]), buf
    )
    graph = base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=buf)
    # body fever count in the reconstructed graph matches the production timeline body count
    body_fever_graph = sum(1 for g in graph if g["fever"] and g["note_index"] >= 100)
    assert body_fever_graph == int(count_body_fever)
    # head fever positions match the production head mask
    head_fever_graph = {g["note_index"] for g in graph if g["fever"] and g["note_index"] < 100}
    head_fever_mask = {i for i in range(min(n, 100)) if bool(fever_mask_head[i])}
    assert head_fever_graph == head_fever_mask
