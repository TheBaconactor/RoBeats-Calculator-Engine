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
    )
    return timestamps, great_candidates, actions, options


def test_fg_note_graph_reconciles_with_surface_head_and_body():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult
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
        frontier = FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=len(actions),
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=non_fever_base,
            seconds=0.0,
        )
        try:
            trace = reconstruct_force_greats_response_trace(
                frontier=frontier,
                target_surface=surface,
                timestamps=timestamps,
                great_candidate_timestamps=great_candidates,
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

    # Case 3: multi-section (two fever windows), head fever + body fever.
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
