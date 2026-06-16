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
    """Issue #42: a fever note at/after the cutoff carries its legal EARLY delta, so replaying
    each note at its shown delta reproduces the scored fever set (frontend self-consistency)."""
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
        assert g[7]["delta_ms"] == pytest.approx(-6.0, abs=1e-3)        # 1240 - 1245 - 1, legal early
        # its event lands inside the window -> displayed per-note timing is self-consistent.
        assert g[7]["hit_time_ms"] + g[7]["delta_ms"] < 1240.0
        # comfortably-inside fever notes untouched (delta 0); activation keeps its +40.
        assert g[6]["fever"] is True and g[6]["delta_ms"] == 0.0
        assert g[2]["is_activation_witness"] is True and g[2]["delta_ms"] == pytest.approx(40.0)


def test_endpoint_early_delta_never_below_legal_lower_bound():
    """Issue #42 reconstruction legality: the displayed endpoint-early `delta_ms` is clamped to
    the note's own Perfect lower bound (-20, or -40 for a held tail). The prior `cutoff - hit - 1`
    could fall BELOW it (e.g. -20.5 ms on a -20 ms note) -- an illegal hit that "replay each note
    at its shown delta" must never produce. Needs `note_types` for the held-tail bound."""
    from gear_optimizer.helpers.song_helpers.force_greats.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    # note 3 @ chart 1019.5ms is 19.5ms past a 1000ms cutoff -> unclamped delta = 1000-1019.5-1 = -20.5.
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

    # Normal note: -20.5 is below the -20 lower bound -> must clamp to exactly -20 (legal).
    nt_normal = [1, 1, 1, 1, 1]
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt_normal),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt_normal),
    ):
        assert g[3]["delta_ms"] >= -20.0                  # never below the Perfect lower bound
        assert g[3]["delta_ms"] == pytest.approx(-20.0)   # clamped to the bound

    # Held tail (note_type 3, window [-40,+80]): -20.5 is legal (>= -40) -> kept, not clamped.
    nt = [1, 1, 1, 3, 1]
    for g in (
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt),
    ):
        assert g[3]["delta_ms"] >= -40.0                  # never below the held-tail lower bound
        assert g[3]["delta_ms"] == pytest.approx(-20.5)   # legal for a held tail -> unclamped

    # FAIL LOUD: a clawed-in note with NO note_types must raise -- never guess a (possibly false)
    # bound. (A graph with no clawed-in note does not need note_types -- not asserted here.)
    with pytest.raises(ValueError):
        force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts)


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
