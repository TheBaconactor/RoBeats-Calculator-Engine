"""Deliverable B: per-loadout note-graph reconstruction reconciles with the surface.

Proves the persisted witness data is SUFFICIENT to rebuild the game's note-graph
({HitTime, Delta, NoteResult, Fever}) losslessly: the FG expansion's per-note
Perfect/Great/Fever labels reconcile EXACTLY with the chosen response surface
(head bitmasks bit-for-bit, body counts), and the base expansion maps the fever
timeline to all-Perfect notes + fever windows. CPU-only, deterministic.
"""

from pathlib import Path

import numpy as np
import pytest


def _exact_force_greats_note_graph(
    *,
    frontier_trace,
    total_notes,
    timestamps,
    note_types=None,
    lanes=None,
    **kwargs,
):
    """Give hand-authored fixtures the same schema-v1 schedule as canonical reconstruction."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        force_greats_note_graph as production_force_greats_note_graph,
    )

    n = int(total_notes)
    timestamp_arr = np.asarray(timestamps, dtype=np.float64).reshape(-1)
    lane_arr = (
        np.arange(n, dtype=np.int32)
        if lanes is None
        else np.asarray(lanes, dtype=np.int32).reshape(-1)
    )
    exact_trace = []
    for source in frontier_trace:
        row = dict(source)
        activation = int(row["activation_index"])
        section_start = int(row.get("forced_start_index", 0))
        forced_start = int(row.get("forced_run_start_index", section_start))
        forced_count = int(row.get("forced_run_count", row.get("forced_prefix_count", 0)))
        order = tuple(range(section_start, activation))
        great_count = sum(
            1 for index in order if forced_start <= int(index) < forced_start + forced_count
        )
        lane_counts: dict[int, int] = {}
        lane_order: list[int] = []
        for index in range(section_start, n):
            lane_id = int(lane_arr[index])
            if lane_id not in lane_counts:
                lane_counts[lane_id] = 0
                lane_order.append(lane_id)
            if index < activation:
                lane_counts[lane_id] += 1
        row.update(
            {
                "activation_schedule_schema_version": 1,
                "preactivation_order": list(order),
                "preactivation_lane_prefixes": [
                    {"lane": int(lane_id), "count": int(lane_counts[lane_id])}
                    for lane_id in lane_order
                ],
                "preactivation_fill_half_units": 2 * len(order) - int(great_count),
                "preactivation_event_count": len(order),
                "preactivation_great_count": int(great_count),
            }
        )
        activation_hit_ms = float(timestamp_arr[activation]) * 1000.0 + float(
            row.get("activation_hit_offset_ms", 0.0) or 0.0
        )
        if row.get("fever_window_end_ms") is None:
            fever_end = int(row.get("fever_end_index", n))
            if 0 <= fever_end < n:
                cutoff_ms = float(timestamp_arr[fever_end]) * 1000.0
            else:
                cutoff_ms = max(
                    float(activation_hit_ms) + 1.0,
                    float(timestamp_arr[-1]) * 1000.0 + 1000.0,
                )
            row["fever_window_end_ms"] = float(cutoff_ms)
        row.setdefault(
            "fever_duration_ms",
            float(row["fever_window_end_ms"]) - float(activation_hit_ms),
        )
        exact_trace.append(row)
    return production_force_greats_note_graph(
        frontier_trace=exact_trace,
        total_notes=n,
        timestamps=timestamps,
        note_types=note_types,
        lanes=lane_arr,
        **kwargs,
    )


def _build_options(n, non_fever_base, real_fever_time):
    from gear_optimizer.solver.timing_envelope import (
        build_great_candidate_envelope_sec,
        build_great_floor_envelope_sec,
        build_perfect_candidate_envelope_sec,
        build_perfect_floor_envelope_sec,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _edge_surface_option_details,
    )

    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    note_types = np.ones(n, dtype=np.int16)
    perfect_candidates = build_perfect_candidate_envelope_sec(timestamps, note_types)
    great_candidates = build_great_candidate_envelope_sec(timestamps, note_types)
    perfect_floor = build_perfect_floor_envelope_sec(timestamps, note_types)
    great_floor = build_great_floor_envelope_sec(timestamps, note_types)
    raw_fever_fill = 1.0
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
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
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=np.arange(int(timestamps.shape[0]), dtype=np.int32),
        raw_fever_fill=raw_fever_fill,
    )
    return (
        timestamps,
        perfect_candidates,
        great_candidates,
        perfect_floor,
        great_floor,
        actions,
        options,
    )


def test_fg_note_graph_reconciles_with_surface_head_and_body():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        FgTraceEdgeOptionsCache,
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        force_greats_note_graph,
        reconcile_force_greats_note_graph,
    )

    n = 110  # >100 so the fever window can extend into the body
    non_fever_base = 96
    real_fever_time = 1.5  # ~15 notes of fever at 0.1s spacing -> reaches past index 100
    (
        timestamps,
        perfect_candidates,
        great_candidates,
        perfect_floor,
        great_floor,
        actions,
        options,
    ) = _build_options(n, non_fever_base, real_fever_time)
    assert options, "expected at least one edge option"

    validated = 0
    saw_body_fever = False
    saw_witness = False
    note_types = np.ones(n, dtype=np.int16)
    edge_options_cache = FgTraceEdgeOptionsCache()
    for opt in options:
        surface = opt["surface"]
        try:
            trace = reconstruct_force_greats_response_trace(
                non_fever_base=non_fever_base,
                target_surface=surface,
                timestamps=timestamps,
                perfect_candidate_timestamps=perfect_candidates,
                great_candidate_timestamps=great_candidates,
                perfect_floor_timestamps=perfect_floor,
                great_floor_timestamps=great_floor,
                lanes=np.arange(n, dtype=np.int32),
                raw_fever_fill=1.0,
                real_fever_time=real_fever_time,
                use_forced_great_timing=True,
                edge_options_cache=edge_options_cache,
            )
        except ValueError:
            continue  # not all standalone edge surfaces are independently reconstructable

        graph = _exact_force_greats_note_graph(
            frontier_trace=trace, total_notes=n, timestamps=timestamps, note_types=note_types,
            lanes=np.arange(n, dtype=np.int32),
        )
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
            trace_row = next(row for row in trace if int(row["activation_index"]) == int(wit["note_index"]))
            expected_result = (
                "Great" if str(trace_row["activation_judgment"]) == "late_great" else "Perfect"
            )
            assert wit["note_result"] == expected_result
            assert isinstance(wit["delta_ms"], float)

    assert validated > 0, "no edge surface reconstructed+reconciled"
    assert edge_options_cache
    assert edge_options_cache.option_count <= 8192
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
        "lanes",
        "raw_fever_fill",
        "real_fever_time",
        "use_forced_great_timing",
        "edge_options_cache",
    }
    # no stat vector, base_value, perfect-points, element color, or frontier/DP object
    for stat_like in ("stats", "base_value", "perfect_points", "frontier", "tier", "team_buff"):
        assert stat_like not in params


def test_trace_edge_cache_rejects_cross_song_geometry_reuse():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        FgTraceEdgeOptionsCache,
        reconstruct_force_greats_response_trace,
    )

    (
        timestamps,
        perfect_candidates,
        great_candidates,
        perfect_floor,
        great_floor,
        _actions,
        options,
    ) = _build_options(110, 96, 1.5)
    cache = FgTraceEdgeOptionsCache()
    kwargs = {
        "non_fever_base": 96,
        "target_surface": options[0]["surface"],
        "timestamps": timestamps,
        "perfect_candidate_timestamps": perfect_candidates,
        "great_candidate_timestamps": great_candidates,
        "perfect_floor_timestamps": perfect_floor,
        "great_floor_timestamps": great_floor,
        "lanes": np.arange(110, dtype=np.int32),
        "raw_fever_fill": 1.0,
        "real_fever_time": 1.5,
        "use_forced_great_timing": True,
        "edge_options_cache": cache,
    }
    reconstruct_force_greats_response_trace(**kwargs)

    with pytest.raises(ValueError, match="cannot be reused across song timing owners"):
        reconstruct_force_greats_response_trace(**{**kwargs, "timestamps": timestamps.copy()})


def test_trace_edge_cache_bounds_retained_options_and_skips_oversized_states():
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import FgTraceEdgeOptionsCache

    cache = FgTraceEdgeOptionsCache()
    owner = object()
    cache.bind_owner(owner, note_count=1)
    option = {"surface": "sentinel"}
    cache.put(("first",), (option,) * 5000)
    cache.put(("second",), (option,) * 4000)

    assert cache.get(("first",)) is None
    assert len(cache.get(("second",)) or ()) == 4000
    assert cache.option_count == 4000

    cache.put(("oversized",), (option,) * 8193)
    assert cache.get(("oversized",)) is None
    assert cache.option_count == 4000

    empty_cache = FgTraceEdgeOptionsCache()
    empty_cache.bind_owner(owner, note_count=1)
    for index in range(300):
        empty_cache.put(("empty", index), ())
    assert len(empty_cache) == 256
    assert empty_cache.option_count == 0


def _words_from_indices(indices):
    """Pack a set of note indices (0..99) into the 4x uint32 head-mask words."""
    w = [0, 0, 0, 0]
    for i in indices:
        if 0 <= i < 100:
            w[i // 32] |= (1 << (i % 32))
    return tuple(w)


def test_fg_note_graph_body_counts_synthetic():
    """Construct traces with KNOWN ground-truth surfaces and prove exact body reconciliation."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
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
    g1 = _exact_force_greats_note_graph(frontier_trace=trace1, total_notes=n, timestamps=ts, note_types=np.ones(n, dtype=np.int16))
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
        "activation_judgment": "late_great", "activation_hit_offset_ms": 41.0,
    }]
    g2 = _exact_force_greats_note_graph(frontier_trace=trace2, total_notes=n, timestamps=ts, note_types=np.ones(n, dtype=np.int16))
    reconcile_force_greats_note_graph(
        g2, total_notes=n,
        fever_words=(0, 0, 0, 0), great_words=(0, 0, 0, 0),
        body_fever=6, body_great=1, body_fever_great=1,
    )
    wit = next(x for x in g2 if x["is_activation_witness"])
    assert wit["note_index"] == 102 and wit["note_result"] == "Great" and wit["delta_ms"] == 41.0
    assert wit["fever"] is True  # the witness is both fever and great

    # Case 3: optimized Perfect-window activation WITNESS -> delayed, but not Great.
    trace_perfect = [{
        "section": 1, "activation_index": 12, "fever_end_index": 16,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_start_source": "perfect_window",
    }]
    gp = _exact_force_greats_note_graph(frontier_trace=trace_perfect, total_notes=n, timestamps=ts, note_types=np.ones(n, dtype=np.int16))
    reconcile_force_greats_note_graph(
        gp, total_notes=n,
        fever_words=_words_from_indices(set(range(12, 16))), great_words=(0, 0, 0, 0),
        body_fever=0, body_great=0, body_fever_great=0,
    )
    witp = next(x for x in gp if x["is_activation_witness"])
    assert witp["note_index"] == 12
    assert witp["note_result"] == "Perfect"
    assert witp["delta_ms"] == 40.0

    # Case 3b: non-prefix forced-Great run. The legacy prefix fields say "none"; the load-bearing
    # run fields place Greats at {2, 3}, with idx3 also carrying the late-Great witness.
    trace_run = [{
        "section": 1, "activation_index": 3, "fever_end_index": 6,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "forced_run_start_index": 2, "forced_run_count": 2,
        "activation_judgment": "late_great", "activation_hit_offset_ms": 41.0,
    }]
    gr = _exact_force_greats_note_graph(
        frontier_trace=trace_run,
        total_notes=n,
        timestamps=ts,
        note_types=np.ones(n, dtype=np.int16),
    )
    reconcile_force_greats_note_graph(
        gr, total_notes=n,
        fever_words=_words_from_indices(set(range(3, 6))), great_words=_words_from_indices({2, 3}),
        body_fever=0, body_great=0, body_fever_great=0,
    )
    assert [i for i, x in enumerate(gr) if x["note_result"] == "Great"] == [2, 3]
    assert gr[3]["is_activation_witness"] is True

    # Case 4: multi-section (two fever windows), head fever + body fever.
    trace3 = [
        {"section": 1, "activation_index": 50, "fever_end_index": 56,
         "forced_start_index": 0, "forced_prefix_count": 2,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0},
        {"section": 2, "activation_index": 110, "fever_end_index": 116,
         "forced_start_index": 100, "forced_prefix_count": 4,
         "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0},
    ]
    g3 = _exact_force_greats_note_graph(frontier_trace=trace3, total_notes=n, timestamps=ts, note_types=np.ones(n, dtype=np.int16))
    # head fever {50..55}, head greats {0,1}, body fever {110..115}=6, body greats {100..103}=4, no overlap
    reconcile_force_greats_note_graph(
        g3, total_notes=n,
        fever_words=_words_from_indices(set(range(50, 56))),
        great_words=_words_from_indices({0, 1}),
        body_fever=6, body_great=4, body_fever_great=0,
    )


def test_fg_note_graph_same_time_head_great_selector_preserves_ramp_order():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 8
    ts = np.asarray([0.095, 0.581, 0.743, 0.743, 1.067, 1.392, 1.878, 2.040], dtype=np.float32)
    trace = [
        {
            "section": 1,
            "activation_index": 6,
            "fever_end_index": 8,
            "forced_start_index": 2,
            "forced_prefix_count": 1,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 0.0,
        }
    ]
    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=n,
        timestamps=ts,
        note_types=np.ones(n, dtype=np.int16),
    )

    assert graph[2]["note_result"] == "Great"
    assert graph[3]["note_result"] == "Perfect"
    assert graph[2]["delta_ms"] < -20.0
    assert graph[3]["delta_ms"] == 0.0
    assert graph[2]["hit_time_ms"] + graph[2]["delta_ms"] < graph[3]["hit_time_ms"] + graph[3]["delta_ms"]


def test_same_time_body_selector_uses_physical_order_not_head_chart_order():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _assign_exact_input_order,
        _mark_same_time_selector_order_deltas,
        _materialize_remaining_selector_deltas,
        _perfect_note_graph,
    )

    n = 144
    timestamps = np.arange(n, dtype=np.float64)
    timestamps[141:] = timestamps[141]
    note_types = np.ones(n, dtype=np.int16)
    note_types[142] = 3  # held tail: canonical late-Great selector is +81 ms
    notes = _perfect_note_graph(n, timestamps)
    notes[142]["note_result"] = "Great"
    notes[142]["delta_ms"] = None

    _mark_same_time_selector_order_deltas(
        notes,
        total_notes=n,
        note_types=note_types,
    )
    assert notes[142]["delta_ms"] is None

    _materialize_remaining_selector_deltas(notes, note_types=note_types)
    _assign_exact_input_order(notes, ())

    assert notes[142]["delta_ms"] == 81.0
    assert notes[141]["input_order"] < notes[143]["input_order"] < notes[142]["input_order"]


def test_same_time_selector_cluster_crossing_head_boundary_keeps_chart_order():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_same_time_selector_order_deltas,
        _perfect_note_graph,
    )

    n = 101
    timestamps = np.arange(n, dtype=np.float64)
    timestamps[100] = timestamps[99]
    note_types = np.ones(n, dtype=np.int16)
    notes = _perfect_note_graph(n, timestamps)
    notes[99]["note_result"] = "Great"
    notes[99]["delta_ms"] = None

    _mark_same_time_selector_order_deltas(
        notes,
        total_notes=n,
        note_types=note_types,
    )

    assert notes[99]["delta_ms"] < -20.0
    assert notes[99]["delta_ms"] < notes[100]["delta_ms"]


def test_same_time_selector_cluster_shares_late_great_boundary_in_chart_order():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _assign_exact_input_order,
        _mark_same_time_selector_order_deltas,
        _perfect_note_graph,
    )

    n = 86
    timestamps = np.arange(n, dtype=np.float64)
    timestamps[82:] = timestamps[82]
    note_types = np.ones(n, dtype=np.int16)
    note_types[82:84] = 3
    notes = _perfect_note_graph(n, timestamps)
    activation_delta_ms = 189.99862670898438
    for index in range(82, 86):
        notes[index]["note_result"] = "Great"
        notes[index]["delta_ms"] = None
    notes[82]["delta_ms"] = activation_delta_ms

    _mark_same_time_selector_order_deltas(
        notes,
        total_notes=n,
        note_types=note_types,
    )
    _assign_exact_input_order(notes, ())

    assert [notes[index]["delta_ms"] for index in range(82, 86)] == [
        activation_delta_ms,
        activation_delta_ms,
        activation_delta_ms,
        activation_delta_ms,
    ]
    assert [notes[index]["input_order"] for index in range(82, 86)] == [82, 83, 84, 85]


def test_same_time_selector_cluster_projects_before_fixed_early_great():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_same_time_selector_order_deltas,
        _perfect_note_graph,
    )

    timestamps = np.zeros(2, dtype=np.float64)
    note_types = np.ones(2, dtype=np.int16)
    notes = _perfect_note_graph(2, timestamps)
    notes[0]["note_result"] = "Great"
    notes[0]["delta_ms"] = None
    notes[1]["note_result"] = "Great"
    notes[1]["delta_ms"] = -80.0

    _mark_same_time_selector_order_deltas(
        notes,
        total_notes=2,
        note_types=note_types,
    )

    assert notes[0]["delta_ms"] == -80.0
    assert notes[1]["delta_ms"] == -80.0


def test_mopemope_wasted_boundary_reconstructs_exact_cross_lane_body_order():
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_force_greats_physical_replay,
    )
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    root = Path(__file__).resolve().parents[1]
    calc_song = build_prepared_calc_song(
        fp=str(root / "Data" / "Easy" / "Mopemope (Easy) by LeaF (7eaF).txt"),
        cfg_dict={},
    ).calc_song
    song_inputs = extract_fg_song_inputs(calc_song)
    surface = FgResponseSurface(
        4278190080,
        4294967295,
        4294967295,
        15,
        0,
        0,
        0,
        0,
        172,
        1,
        0,
    )
    raw_fever_fill = 24.53966249004006
    real_fever_time = 43.218920541501035
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=25,
        target_surface=surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )

    replay = validate_force_greats_physical_replay(
        frontier_trace=trace,
        surface=surface,
        timestamps=song_inputs.timestamps,
        note_types=calc_song["song_data"]["note_types"],
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
    )

    assert trace[1]["preactivation_order"][:3] == [143, 142, 146]
    assert replay.event_order.index(141) < replay.event_order.index(143) < replay.event_order.index(142)


def test_alice_same_time_boundary_reconstructs_exact_judgments_and_order():
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_force_greats_physical_replay,
    )
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    root = Path(__file__).resolve().parents[1]
    calc_song = build_prepared_calc_song(
        fp=str(root / "Data" / "Hard" / "Alice in Misanthrope (Hard) by LeaF (7eaF).txt"),
        cfg_dict={},
    ).calc_song
    song_inputs = extract_fg_song_inputs(calc_song)
    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 1597, 1, 0)
    raw_fever_fill = 195.50747138670087
    real_fever_time = 55.122186673736564
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=196,
        target_surface=surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )

    replay = validate_force_greats_physical_replay(
        frontier_trace=trace,
        surface=surface,
        timestamps=song_inputs.timestamps,
        note_types=calc_song["song_data"]["note_types"],
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
    )

    cluster = (951, 952, 953, 954, 955)
    assert [replay.event_order.index(index) for index in cluster] == list(cluster)
    assert [replay.judgments[index] for index in cluster] == [
        "Perfect",
        "Perfect",
        "Great",
        "Perfect",
        "Perfect",
    ]
    assert [replay.fever_mask[index] for index in cluster] == [True, False, False, False, False]


def test_light_it_up_late_great_cluster_reconstructs_exact_judgments_and_order():
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_force_greats_physical_replay,
    )
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    root = Path(__file__).resolve().parents[1]
    calc_song = build_prepared_calc_song(
        fp=str(root / "Data" / "Normal" / "Light it up by Camellia.txt"),
        cfg_dict={},
    ).calc_song
    song_inputs = extract_fg_song_inputs(calc_song)
    surface = FgResponseSurface(0, 0, 4294705152, 15, 0, 0, 4063232, 0, 740, 0, 0)
    raw_fever_fill = 81.71601202940941
    real_fever_time = 59.28149701967239
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=82,
        target_surface=surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )

    replay = validate_force_greats_physical_replay(
        frontier_trace=trace,
        surface=surface,
        timestamps=song_inputs.timestamps,
        note_types=calc_song["song_data"]["note_types"],
        lanes=song_inputs.lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
    )

    cluster = (82, 83, 84, 85)
    assert [replay.event_order.index(index) for index in cluster] == list(cluster)
    assert [replay.judgments[index] for index in cluster] == ["Great"] * len(cluster)
    assert [replay.fever_mask[index] for index in cluster] == [True] * len(cluster)


def test_fg_note_graph_delays_following_perfect_to_preserve_late_activation_order():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 10.0, 10.160, 10.300, 10.500], dtype=np.float32)
    trace = [
        {
            "section": 1,
            "activation_index": 2,
            "fever_end_index": 6,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 181.0,
        }
    ]
    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=n,
        timestamps=ts,
        note_types=np.ones(n, dtype=np.int16),
    )

    activation_press = graph[2]["hit_time_ms"] + graph[2]["delta_ms"]
    next_press = graph[3]["hit_time_ms"] + graph[3]["delta_ms"]

    assert graph[2]["note_result"] == "Great"
    assert graph[3]["note_result"] == "Perfect"
    assert graph[3]["delta_ms"] == pytest.approx(21.0, abs=1e-3)
    assert next_press >= activation_press
    assert graph[4]["delta_ms"] == 0.0


def test_fg_note_graph_uses_activation_upper_edge_for_priced_fever_cutoff():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 4
    ts = np.asarray([10.000, 10.160, 10.300, 10.500], dtype=np.float32)
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 4,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 50.0,
            "activation_hit_offset_upper_ms": 190.0,
            "fever_window_end_ms": 12000.0,
        }
    ]
    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=n,
        timestamps=ts,
        note_types=np.ones(n, dtype=np.int16),
    )

    activation_press = graph[0]["hit_time_ms"] + graph[0]["delta_ms"]
    next_press = graph[1]["hit_time_ms"] + graph[1]["delta_ms"]

    assert graph[0]["delta_ms"] == pytest.approx(190.0)
    assert graph[1]["note_result"] == "Perfect"
    assert graph[1]["delta_ms"] == pytest.approx(30.0, abs=1e-3)
    assert next_press >= activation_press


def test_fg_note_graph_decodes_float32_window_on_engine_ms_lattice():
    timestamp = np.float32(104.36299896240234)
    absolute_hit_ms = float(np.float32(104.403)) * 1000.0
    raw_offset_ms = (float(np.float32(104.403)) - float(timestamp)) * 1000.0
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 1,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "perfect",
            "activation_ms": float(timestamp) * 1000.0,
            "activation_hit_ms": absolute_hit_ms,
            "activation_hit_offset_ms": raw_offset_ms,
            "activation_hit_window_lower_ms": absolute_hit_ms,
            "activation_hit_window_upper_ms": absolute_hit_ms,
            "activation_hit_offset_lower_ms": raw_offset_ms,
            "activation_hit_offset_upper_ms": raw_offset_ms,
        }
    ]

    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=1,
        timestamps=np.asarray([timestamp], dtype=np.float32),
        note_types=np.ones(1, dtype=np.int16),
    )

    assert raw_offset_ms > 40.0
    assert graph[0]["hit_time_ms"] == pytest.approx(float(timestamp) * 1000.0)
    assert graph[0]["delta_ms"] == 40.0
    assert graph[0]["note_result"] == "Perfect"


def test_fg_note_graph_hold_head_activation_uses_upper_edge_for_early_great_tail():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    timestamps = np.asarray([0.0, 1.0], dtype=np.float32)
    trace = [{
        "section": 1,
        "activation_index": 0,
        "fever_end_index": 2,
        "forced_start_index": 0,
        "forced_prefix_count": 0,
        "activation_judgment": "perfect",
        "activation_hit_offset_ms": 20.0,
        "activation_hit_offset_lower_ms": 0.0,
        "activation_hit_offset_upper_ms": 40.0,
        "fever_window_end_ms": 920.0,
        "early_great_start": 1,
        "early_great_end": 2,
    }]

    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=2,
        timestamps=timestamps,
        note_types=np.asarray([2, 1], dtype=np.int16),
    )

    assert graph[0]["delta_ms"] == pytest.approx(40.0)
    assert graph[1]["note_result"] == "Great"
    assert -94.0 <= float(graph[1]["delta_ms"]) < -20.0
    assert float(graph[1]["hit_time_ms"]) + float(graph[1]["delta_ms"]) < 920.0


def test_fg_note_graph_caps_activation_edge_to_preserve_following_perfect():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 3
    ts = np.asarray([10.000, 10.130, 10.500], dtype=np.float32)
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 3,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 120.0,
            "activation_hit_offset_lower_ms": 80.0,
            "activation_hit_offset_upper_ms": 190.0,
            "fever_window_end_ms": 11190.0,
        }
    ]
    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=n,
        timestamps=ts,
        note_types=np.ones(n, dtype=np.int16),
    )

    activation_press = graph[0]["hit_time_ms"] + graph[0]["delta_ms"]
    next_press = graph[1]["hit_time_ms"] + graph[1]["delta_ms"]

    assert graph[0]["delta_ms"] == pytest.approx(169.999, abs=1e-3)
    assert graph[1]["note_result"] == "Perfect"
    assert graph[1]["delta_ms"] == pytest.approx(39.999, abs=1e-3)
    assert next_press >= activation_press
    assert graph[2]["fever_end_ms"] == pytest.approx(11169.999, abs=1e-3)


def test_fg_note_graph_rejects_activation_edge_when_label_order_is_impossible():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 2
    ts = np.asarray([10.000, 10.000], dtype=np.float32)
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 120.0,
            "activation_hit_offset_lower_ms": 80.0,
            "activation_hit_offset_upper_ms": 190.0,
            "fever_window_end_ms": 11190.0,
        }
    ]

    with pytest.raises(ValueError, match="activation witness cannot preserve following note order"):
        _exact_force_greats_note_graph(
            frontier_trace=trace,
            total_notes=n,
            timestamps=ts,
            note_types=np.ones(n, dtype=np.int16),
        )


def test_fg_note_graph_uses_exact_later_preactivation_witness_before_activation():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 120.0,
            "activation_hit_offset_lower_ms": 80.0,
            "activation_hit_offset_upper_ms": 190.0,
            "fever_window_end_ms": 11190.0,
            "fever_duration_ms": 11000.0,
            "activation_schedule_schema_version": 1,
            "preactivation_order": [1],
            "preactivation_lane_prefixes": [
                {"lane": 1, "count": 0},
                {"lane": 2, "count": 1},
            ],
            "preactivation_fill_half_units": 2,
            "preactivation_event_count": 1,
            "preactivation_great_count": 0,
        }
    ]

    graph = force_greats_note_graph(
        frontier_trace=trace,
        total_notes=2,
        timestamps=np.asarray([10.0, 10.0], dtype=np.float32),
        note_types=np.ones(2, dtype=np.int16),
        lanes=np.asarray([1, 2], dtype=np.int32),
    )

    assert graph[1]["input_order"] < graph[0]["input_order"]
    assert graph[1]["note_result"] == "Perfect"
    assert graph[1]["fever"] is False
    assert graph[0]["note_result"] == "Great"
    assert graph[0]["fever"] is True


def test_fg_note_graph_materializes_all_section_labels_before_activation_caps():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "late_great",
            "activation_hit_offset_ms": 120.0,
            "activation_hit_offset_lower_ms": 80.0,
            "activation_hit_offset_upper_ms": 190.0,
            "fever_window_end_ms": 15000.0,
            "fever_duration_ms": 5000.0,
            "activation_schedule_schema_version": 1,
            "preactivation_order": [],
            "preactivation_lane_prefixes": [
                {"lane": 1, "count": 0},
                {"lane": 2, "count": 0},
                {"lane": 3, "count": 0},
            ],
            "preactivation_fill_half_units": 0,
            "preactivation_event_count": 0,
            "preactivation_great_count": 0,
        },
        {
            "section": 2,
            "activation_index": 2,
            "fever_end_index": 3,
            "forced_start_index": 1,
            "forced_prefix_count": 1,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 0.0,
            "fever_window_end_ms": 31000.0,
            "fever_duration_ms": 11000.0,
            "activation_schedule_schema_version": 1,
            "preactivation_order": [1],
            "preactivation_lane_prefixes": [
                {"lane": 2, "count": 1},
                {"lane": 3, "count": 0},
            ],
            "preactivation_fill_half_units": 1,
            "preactivation_event_count": 1,
            "preactivation_great_count": 1,
        },
    ]

    graph = force_greats_note_graph(
        frontier_trace=trace,
        total_notes=3,
        timestamps=np.asarray([10.0, 10.0, 20.0], dtype=np.float32),
        note_types=np.ones(3, dtype=np.int16),
        lanes=np.asarray([1, 2, 3], dtype=np.int32),
    )

    assert [note["note_result"] for note in graph] == ["Great", "Great", "Perfect"]
    assert graph[0]["input_order"] < graph[1]["input_order"] < graph[2]["input_order"]
    assert float(graph[1]["delta_ms"]) >= float(graph[0]["delta_ms"])


def test_fg_note_graph_marks_fever_end_witness():
    """FG note-graph tags the last note of each fever run with the cutoff ms, like base."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

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
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=np.ones(n, dtype=np.int16))

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
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
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
        "section": 1, "activation_index": 2, "fever_start_note_index": 2, "fever_end_index": 8,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": 1240.0,
    }]

    nt = np.ones(n, dtype=np.int16)  # all-normal notes for this case
    for g in (
        _exact_force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=np.zeros(n, bool), frontier_trace=base_trace, note_types=nt),
    ):
        # note 7 @ chart 1245ms is past the 1240ms cutoff -> in fever ONLY via an early hit.
        assert g[7]["fever"] is True
        assert g[7]["is_fever_end_witness"] is True
        # Largest cushion = center of [legal_low_hit, strict cutoff predecessor].
        # (BUG-1: legal Perfect low is -19, not -20.)
        strict_cutoff = float(np.nextafter(np.float64(1240.0), np.float64(-np.inf)))
        expected = 0.5 * (-19.0 + strict_cutoff - float(g[7]["hit_time_ms"]))
        assert g[7]["delta_ms"] == pytest.approx(expected, abs=1e-3)
        assert g[7]["delta_ms"] >= -19.0                               # still legal (>= lower bound, BUG-1)
        # its event lands inside the window -> displayed per-note timing is self-consistent.
        assert g[7]["hit_time_ms"] + g[7]["delta_ms"] < 1240.0
        # comfortably-inside fever notes untouched (delta 0); activation keeps its +40.
        assert g[6]["fever"] is True and g[6]["delta_ms"] == 0.0
        assert g[2]["is_activation_witness"] is True and g[2]["delta_ms"] == pytest.approx(40.0)


def test_endpoint_early_delta_never_below_legal_lower_bound():
    """Issue #42 reconstruction legality: the displayed endpoint-early `delta_ms` (now the
    largest-cushion center of the legal in-fever range) is never below the note's own Perfect lower
    bound (-20, or -40 for a held tail). In the tight-margin edge where the legal-early hit already
    sits at/after the strict cutoff predecessor (no in-fever room), the degenerate branch preserves the old
    clamp-to-bound. Needs `note_types` for the held-tail bound."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
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
        "section": 1, "activation_index": 0, "fever_start_note_index": 0, "fever_end_index": 4,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": 1000.0,
    }]
    mask = np.zeros(n, bool)

    # Normal note (BUG-1 legal low -19): legal_low_hit = 1019.5-19 = 1000.5 >= upper_hit (<1000)
    # -> NO in-fever room -> degenerate branch clamps shown_hit to legal_low_hit, delta = exactly -19
    # (the legal bound; the note is now genuinely unreachable in-fever, shown at its earliest legal hit).
    nt_normal = [1, 1, 1, 1, 1]
    for g in (
        _exact_force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt_normal),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt_normal),
    ):
        assert g[3]["delta_ms"] >= -19.0                  # never below the Perfect lower bound (BUG-1)
        assert g[3]["delta_ms"] == pytest.approx(-19.0)   # tight edge -> clamped to the bound

    # Held tail (note_type 3, window [-39,+80] BUG-1): legal_low_hit = 1019.5-39 = 980.5 < cutoff.
    # There is room, so the largest-cushion center uses the strict cutoff predecessor.
    nt = [1, 1, 1, 3, 1]
    for g in (
        _exact_force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=base_trace, note_types=nt),
    ):
        assert g[3]["delta_ms"] >= -39.0                   # never below the held-tail lower bound (BUG-1)
        strict_cutoff = float(np.nextafter(np.float64(1000.0), np.float64(-np.inf)))
        expected = 0.5 * (-39.0 + strict_cutoff - float(g[3]["hit_time_ms"]))
        assert g[3]["delta_ms"] == pytest.approx(expected)

    # FAIL LOUD: a clawed-in note with NO note_types must raise -- never guess a (possibly false)
    # bound. (A graph with no clawed-in note does not need note_types -- not asserted here.)
    with pytest.raises(ValueError):
        _exact_force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts)


def test_endpoint_early_delta_is_largest_cushion_center():
    """Issue #42 display convention: a clawed-in held-tail note's shown `delta_ms` is the
    LARGEST-CUSHION timing -- the center of its legal in-fever range bounded by the strict cutoff
    predecessor -- not an arbitrary fixed-gap cliff. The shown hit is LEGAL (delta >= legal_low),
    IN-FEVER (hit <= cutoff), and MONOTONIC (>= the previous note's shown hit). Both frontiers."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    # idx5 held tail @ chart 1410ms is clawed in past the 1400ms cutoff; legal_low = -40.
    # legal_low_hit < cutoff -> real in-fever room -> center fires (not the clamp).
    # Preceding fever notes sit well before 1370 so monotonicity does NOT bind here.
    n = 7
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 1.0, 1.410, 1.6], dtype=np.float32)
    cutoff = 1400.0
    legal_low = -39.0  # held tail (BUG-1: -40 edge is exclusive; earliest legal is -39)
    fg_trace = [{
        "section": 1, "activation_index": 2, "fever_end_index": 6,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 40.0,
        "fever_window_end_ms": cutoff,
    }]
    base_trace = [{
        "section": 1, "activation_index": 2, "fever_start_note_index": 2, "fever_end_index": 6,
        "activation_hit_offset_ms": 40.0, "fever_window_end_ms": cutoff,
    }]
    nt = np.asarray([1, 1, 1, 1, 1, 3, 1], dtype=np.int16)  # idx5 is the held tail
    for g in (
        _exact_force_greats_note_graph(frontier_trace=fg_trace, total_notes=n, timestamps=ts, note_types=nt),
        base_note_graph(total_notes=n, timestamps=ts, is_fever_mask=np.zeros(n, bool), frontier_trace=base_trace, note_types=nt),
    ):
        hit = g[5]["hit_time_ms"]
        shown = hit + g[5]["delta_ms"]
        # shown delta == center of [legal_low, nextafter(cutoff, -inf) - hit].
        strict_cutoff = float(np.nextafter(np.float64(cutoff), np.float64(-np.inf)))
        expected = 0.5 * (legal_low + strict_cutoff - hit)
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
    nt2 = np.ones(n2, dtype=np.int16)  # both clawed notes are normal (legal_low = -19, BUG-1)
    g = _exact_force_greats_note_graph(frontier_trace=fg_trace2, total_notes=n2, timestamps=ts2, note_types=nt2)
    shown5 = g[5]["hit_time_ms"] + g[5]["delta_ms"]
    shown6 = g[6]["hit_time_ms"] + g[6]["delta_ms"]
    for i in (5, 6):
        assert g[i]["delta_ms"] >= -19.0                         # both stay legal (BUG-1)
        assert g[i]["hit_time_ms"] + g[i]["delta_ms"] < 1400.0   # both stay strictly in-fever
    assert shown6 >= shown5                                      # monotonic shown order preserved
    strict_cutoff = float(np.nextafter(np.float64(1400.0), np.float64(-np.inf)))
    expected5 = 0.5 * (float(g[5]["hit_time_ms"]) - 19.0 + strict_cutoff)
    expected6 = 0.5 * (expected5 + strict_cutoff)
    assert shown5 == pytest.approx(expected5, abs=1e-3)
    assert shown6 == pytest.approx(expected6, abs=1e-3)


def test_endpoint_early_degenerate_clamp_is_monotonic():
    """Degenerate branch (no in-fever room) must keep the prev_hit floor so shown hits stay
    non-decreasing. A normal note clawed in at the ~1ms boundary (shown ~cutoff-0.5) followed by a
    held tail whose own legal_low_hit is lower would, under a prev_hit-blind clamp, be shown EARLIER
    -- breaking monotonicity. The fix clamps to lo_hit (>= prev_hit)."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 4
    # BUG-1: legal Perfect low is -19, so idx2 sits at 18.5ms past cutoff (was 19.5 at the -20 edge)
    # to keep the same degenerate-but-in-fever knife-edge: legal_low_hit = 1018.5-19 = 999.5 (< cutoff,
    # >= upper_hit 999 -> degenerate). idx3 held @1030 -> prev_hit floor raises it, monotonic.
    ts = np.asarray([0.0, 0.1, 1.0185, 1.030], dtype=np.float32)  # idx2 normal @1018.5, idx3 held @1030
    cutoff = 1000.0
    trace = [{
        "section": 1, "activation_index": 0, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.asarray([1, 1, 1, 3], dtype=np.int16)  # idx2 normal (-19), idx3 held tail (-39) (BUG-1)
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)
    s2 = g[2]["hit_time_ms"] + g[2]["delta_ms"]
    s3 = g[3]["hit_time_ms"] + g[3]["delta_ms"]
    assert s3 >= s2                       # MONOTONIC across the degenerate clamp (the regression guard)
    assert s2 < cutoff and s3 < cutoff    # both still land in fever
    assert g[2]["delta_ms"] >= -19.0      # normal-note legal bound (BUG-1)
    assert g[3]["delta_ms"] >= -39.0      # held-tail legal bound (BUG-1)


def test_base_note_graph_maps_fever_timeline():
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

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
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
    mask = np.zeros(n, dtype=np.bool_)
    trace = [
        {
            "section": 1,
            "activation_index": 2,
            "fever_start_note_index": 2,
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
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

    n = 6
    ts = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
    mask = np.zeros(n, dtype=np.bool_)
    trace = [
        {
            "section": 1,
            "activation_index": 2,
            "fever_start_note_index": 2,
            "activation_hit_offset_ms": 40.0,
            "fever_end_index": 5,
            "fever_window_end_ms": 440.0,
        }
    ]

    graph = base_note_graph(
        total_notes=n, timestamps=ts, is_fever_mask=mask, frontier_trace=trace,
        note_types=np.ones(n, dtype=np.int16),
    )

    # Fever run is notes [2, 5); the last fevered note (4) is the fever-end witness,
    # carrying the largest-cushion cutoff time. No score-contributing flag exists.
    assert [g["is_fever_end_witness"] for g in graph] == [False, False, False, False, True, False]
    assert graph[4]["fever_end_ms"] == pytest.approx(440.0)
    assert graph[4]["fever"] is True
    assert graph[2]["is_activation_witness"] is True
    assert graph[2]["is_fever_end_witness"] is False
    assert graph[0]["fever_end_ms"] is None
    assert all("contributes_to_max_score" not in g for g in graph)


def test_endpoint_early_frontier_includes_reattributed_activation_witness():
    """Chorded-tail witness (w < a) + tight endpoint: the endpoint-early monotonic
    frontier must start at the PHYSICAL activating hit, so no clawed-in fever note is
    displayed before it."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

    n = 6
    # note 1 = held tail (witness, hit 500+80=580); note 2 = same-ms count boundary
    # (swapped out of fever); note 4 = held-tail endpoint at chart 600 == cutoff,
    # clawed in early (its -40 legal edge reaches below the 580 witness hit).
    ts = np.asarray([0.0, 0.5, 0.5, 0.55, 0.6, 0.7], dtype=np.float32)
    nt = np.asarray([1, 3, 1, 1, 3, 1], dtype=np.int16)
    trace = [{
        "section": 1, "activation_index": 2, "fever_start_note_index": 1,
        "activation_ms": 500.0, "activation_hit_offset_ms": 80.0,
        "fever_end_index": 5, "fever_window_end_ms": 600.0,
    }]

    g = base_note_graph(
        total_notes=n, timestamps=ts, is_fever_mask=np.zeros(n, bool),
        frontier_trace=trace, note_types=nt,
    )

    assert g[1]["is_activation_witness"] is True and g[1]["delta_ms"] == pytest.approx(80.0)
    assert g[1]["fever"] is True
    assert g[2]["fever"] is False
    witness_shown = g[1]["hit_time_ms"] + g[1]["delta_ms"]  # 580
    # The clawed endpoint's displayed hit must never precede the activating hit.
    endpoint_shown = g[4]["hit_time_ms"] + g[4]["delta_ms"]
    assert endpoint_shown >= witness_shown
    # lo_hit = max(600-40, witness 580) = 580, upper is the strict predecessor of 600.
    assert endpoint_shown == pytest.approx(590.0)
    assert g[4]["delta_ms"] >= -40.0                       # legal for the held tail
    assert endpoint_shown < 600.0                          # still inside the cutoff
    # Every displayed fever hit chosen by the guidance stays at/after the witness hit.
    for note in g:
        if note["fever"] and note["delta_ms"] not in (None, 0.0):
            assert note["hit_time_ms"] + note["delta_ms"] >= witness_shown


def test_base_delayed_activation_materializes_physical_chord_order():
    """A delayed base activation cannot leave its following chord sibling at chart time.

    The server consumes inputs by physical timestamp.  Leaving note 2 at 0ms would make it land
    before note 1's +40ms activation and move fever to the wrong note.  The graph must materialize
    the frontier's priced order without changing fever membership or judgments.
    """
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

    trace = [{
        "section": 1,
        "activation_index": 1,
        "fever_start_note_index": 1,
        "activation_hit_offset_ms": 40.0,
        "fever_end_index": 4,
        "fever_window_end_ms": 500.0,
    }]
    graph = base_note_graph(
        total_notes=4,
        timestamps=np.asarray([0.0, 0.1, 0.1, 0.3], dtype=np.float32),
        is_fever_mask=np.zeros(4, bool),
        frontier_trace=trace,
        note_types=np.ones(4, dtype=np.int16),
        timing_mode="perfect_window",
    )

    assert graph[1]["delta_ms"] == pytest.approx(40.0)
    assert graph[2]["delta_ms"] == pytest.approx(40.0)
    assert graph[1]["hit_time_ms"] + graph[1]["delta_ms"] == pytest.approx(
        graph[2]["hit_time_ms"] + graph[2]["delta_ms"]
    )
    assert [note["fever"] for note in graph] == [False, True, True, True]
    assert all(note["note_result"] == "Perfect" for note in graph)


def test_base_zero_ms_activation_does_not_retime_chord():
    """The physical-order materializer is an exact no-op for canonical zero-ms replay."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

    trace = [{
        "section": 1,
        "activation_index": 1,
        "fever_start_note_index": 1,
        "activation_hit_offset_ms": 0.0,
        "fever_end_index": 4,
        "fever_window_end_ms": 500.0,
    }]
    graph = base_note_graph(
        total_notes=4,
        timestamps=np.asarray([0.0, 0.1, 0.1, 0.3], dtype=np.float32),
        is_fever_mask=np.zeros(4, bool),
        frontier_trace=trace,
        note_types=np.ones(4, dtype=np.int16),
        timing_mode="zero_ms",
    )

    assert [note["delta_ms"] for note in graph] == [0.0, 0.0, 0.0, 0.0]


def test_base_note_graph_matches_production_fever_timeline():
    """base fever mask is the production fever timeline's full per-note is_fever buffer."""
    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
    from gear_optimizer.solver.fg_response_scoring.note_graph import base_note_graph

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


def test_fever_end_cluster_rejects_impossible_plus_560_ms():
    """Comfortable cutoff: fever does not constrain Perfect upper -> keep 0 ms (not cutoff-hit)."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 5
    ts = np.asarray([0.0, 1.0, 1.2, 1.4, 1.6], dtype=np.float32)
    trace = [{
        "section": 1, "activation_index": 1, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": 1560.0,
    }]
    nt = np.ones(n, dtype=np.int16)
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)

    assert g[3]["is_fever_end_witness"] is True
    assert g[3]["delta_ms"] == 0.0
    assert -20.0 <= g[3]["delta_ms"] <= 40.0
    assert g[3]["delta_ms"] != pytest.approx(560.0)


def test_fever_end_cluster_barely_inside_decoy_delta():
    """Tight cutoff: safe upper is the strict fever boundary."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    cutoff = 61340.14382457733
    n = 4
    ts = np.asarray([0.0, 61.167, 61.339, 61.339], dtype=np.float32)
    trace = [{
        "section": 1, "activation_index": 0, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 179.43191528320312,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.ones(n, dtype=np.int16)
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)

    strict_cutoff = float(np.nextafter(np.float64(cutoff), np.float64(-np.inf)))
    expected = 0.5 * (-19.0 + strict_cutoff - float(g[2]["hit_time_ms"]))
    assert g[2]["delta_ms"] == pytest.approx(expected)
    assert g[3]["delta_ms"] == pytest.approx(g[2]["delta_ms"])
    for i in (2, 3):
        assert g[i]["delta_ms"] >= -19.0  # BUG-1: earliest legal Perfect is -19, not -20
        assert g[i]["hit_time_ms"] + g[i]["delta_ms"] < cutoff


def test_note_graph_displays_early_great_fever_end_tail():
    """Issue #68: Great-only fever-end claw-in must not collapse to Perfect-low."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 2
    # BUG-1: the earliest legal early-Great is now -94 (was -95). Widen the cutoff a couple ms from
    # the original knife-edge (which was reachable only at the now-illegal -95) so the note is a
    # genuinely-reachable early-Great -- the point of the test is that it is shown in the Great band,
    # not collapsed to the Perfect-low line.
    cutoff = 133120.0
    ts = np.asarray([0.0, 133.201996], dtype=np.float32)
    nt = np.ones(n, dtype=np.int16)
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 40.0,
            "fever_window_end_ms": cutoff,
            "early_great_start": 1,
            "early_great_end": 2,
        }
    ]

    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)
    assert g[1]["fever"] is True
    assert g[1]["note_result"] == "Great"
    assert g[1]["delta_ms"] < -20.0           # in the Great band, NOT collapsed to Perfect-low
    assert g[1]["delta_ms"] >= -94.0          # BUG-1: earliest legal early-Great is -94, not -95
    assert g[1]["hit_time_ms"] + g[1]["delta_ms"] < cutoff
    assert g[1]["delta_ms"] != pytest.approx(-20.0)


def test_early_great_tail_accepts_submillisecond_strict_cutoff_interval():
    cutoff = 906.5
    timestamps = np.asarray([0.0, 1.0], dtype=np.float32)
    trace = [{
        "section": 1,
        "activation_index": 0,
        "fever_end_index": 2,
        "forced_start_index": 0,
        "forced_prefix_count": 0,
        "activation_judgment": "perfect",
        "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": cutoff,
        "early_great_start": 1,
        "early_great_end": 2,
    }]

    graph = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=2,
        timestamps=timestamps,
        note_types=np.ones(2, dtype=np.int16),
    )

    delta = float(graph[1]["delta_ms"])
    assert graph[1]["note_result"] == "Great"
    assert -94.0 <= delta < -93.5
    assert float(graph[1]["hit_time_ms"]) + delta < cutoff


def test_note_graph_displays_early_great_fever_end_tail_held_tail():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 2
    cutoff = 133108.764
    ts = np.asarray([0.0, 133.201996], dtype=np.float32)
    nt = np.asarray([1, 3], dtype=np.int16)  # held tail doubles early-Great floor
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 40.0,
            "fever_window_end_ms": cutoff,
            "early_great_start": 1,
            "early_great_end": 2,
        }
    ]

    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)
    assert g[1]["note_result"] == "Great"
    assert g[1]["delta_ms"] >= -190.0
    assert g[1]["delta_ms"] < -40.0


def test_note_graph_early_great_fever_end_fails_loud_beyond_floor():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 2
    # Make the fever upper bound earlier than the Great floor (-95ms) so the safe interval is empty.
    # chart_ms = 133201.996 -> choose cutoff_ms so (cutoff_ms - hit_ms - 1) < -95.
    # e.g. cutoff_ms = hit_ms - 96 => upper ~= -97ms.
    cutoff = 133201.996 - 96.0
    ts = np.asarray([0.0, 133.201996], dtype=np.float32)
    nt = np.ones(n, dtype=np.int16)
    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 2,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 40.0,
            "fever_window_end_ms": float(cutoff),
            "early_great_start": 1,
            "early_great_end": 2,
        }
    ]

    with pytest.raises(ValueError, match="early-Great fever-end note"):
        _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)


def test_early_great_tail_uses_prior_perfect_endpoint_delta_for_monotonicity():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 3
    cutoff = 1240.0
    ts = np.asarray([0.0, 1.250, 1.330], dtype=np.float32)
    nt = np.ones(n, dtype=np.int16)

    trace = [
        {
            "section": 1,
            "activation_index": 0,
            "fever_end_index": 3,
            "forced_start_index": 0,
            "forced_prefix_count": 0,
            "activation_judgment": "perfect",
            "activation_hit_offset_ms": 40.0,
            "fever_window_end_ms": cutoff,
            "early_great_start": 2,
            "early_great_end": 3,
        }
    ]

    g = _exact_force_greats_note_graph(
        frontier_trace=trace,
        total_notes=n,
        timestamps=ts,
        note_types=nt,
    )

    assert g[1]["note_result"] == "Perfect"
    assert -20.0 <= g[1]["delta_ms"] <= 40.0
    assert g[1]["hit_time_ms"] + g[1]["delta_ms"] < cutoff
    assert g[1]["delta_ms"] != 0.0

    assert g[2]["note_result"] == "Great"
    assert -95.0 <= g[2]["delta_ms"] < -20.0
    assert g[2]["hit_time_ms"] + g[2]["delta_ms"] < cutoff

    assert g[1]["hit_time_ms"] + g[1]["delta_ms"] <= g[2]["hit_time_ms"] + g[2]["delta_ms"]


def test_zero_ms_note_graph_does_not_apply_fever_end_guidance():
    """zero_ms mode must not inherit Perfect-window guidance deltas (issue #66)."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        base_note_graph,
        force_greats_note_graph,
    )

    cutoff = 61340.14382457733
    n = 4
    ts = np.asarray([0.0, 61.167, 61.339, 61.339], dtype=np.float32)
    trace_with_tight_fever_end = [{
        "section": 1, "activation_index": 0, "fever_start_note_index": 0, "fever_end_index": 4,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 179.43191528320312,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.ones(n, dtype=np.int16)

    fg_graph = _exact_force_greats_note_graph(
        frontier_trace=trace_with_tight_fever_end,
        total_notes=n,
        timestamps=ts,
        note_types=nt,
        timing_mode="zero_ms",
    )
    assert all(note["delta_ms"] in (0.0, None) for note in fg_graph)
    assert fg_graph[0]["is_activation_witness"] is False

    pw_graph = _exact_force_greats_note_graph(
        frontier_trace=trace_with_tight_fever_end,
        total_notes=n,
        timestamps=ts,
        note_types=nt,
        timing_mode="perfect_window",
    )
    strict_cutoff = float(np.nextafter(np.float64(cutoff), np.float64(-np.inf)))
    expected = 0.5 * (-19.0 + strict_cutoff - float(pw_graph[2]["hit_time_ms"]))
    assert pw_graph[2]["delta_ms"] == pytest.approx(expected)

    base_graph = base_note_graph(
        total_notes=n,
        timestamps=ts,
        is_fever_mask=np.zeros(n, bool),
        frontier_trace=trace_with_tight_fever_end,
        note_types=nt,
        timing_mode="zero_ms",
    )
    assert all(note["delta_ms"] in (0.0, None) for note in base_graph)
    assert base_graph[0]["is_activation_witness"] is False


def test_fever_end_cluster_same_chart_time_shared_delta():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 8
    cutoff = 1240.0
    ts = np.asarray([0.0, 0.2, 0.4, 0.6, 1.220, 1.220, 1.4, 1.6], dtype=np.float32)
    trace = [{
        "section": 1, "activation_index": 3, "fever_end_index": 6,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.ones(n, dtype=np.int16)
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)

    assert g[5]["is_fever_end_witness"] is True
    assert g[4]["delta_ms"] == pytest.approx(g[5]["delta_ms"])
    assert g[4]["delta_ms"] != 0.0


def test_fever_end_cluster_held_tail_intersection():
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    n = 7
    cutoff = 1230.0
    ts = np.asarray([0.0, 0.2, 0.4, 0.6, 1.220, 1.220, 1.5], dtype=np.float32)
    trace = [{
        "section": 1, "activation_index": 3, "fever_end_index": 6,
        "forced_start_index": 0, "forced_prefix_count": 0,
        "activation_judgment": "perfect", "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": cutoff,
    }]
    nt = np.asarray([1, 1, 1, 1, 1, 3, 1], dtype=np.int16)
    g = _exact_force_greats_note_graph(frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt)

    shared = g[5]["delta_ms"]
    assert g[4]["delta_ms"] == pytest.approx(shared)
    assert shared >= -20.0
    assert shared <= 40.0
    assert g[5]["delta_ms"] >= -40.0
    assert g[5]["delta_ms"] <= 80.0


def test_fever_end_cluster_fail_loud_on_tight_non_perfect_same_time():
    """Tight cutoff + mixed Perfect/Great same-chart-time cluster must not silently keep 0 ms."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_fever_end_cluster_safe_delta,
        _mark_fever_end_witness,
        _perfect_note_graph,
    )

    n = 4
    ts = np.asarray([0.0, 0.5, 1.0, 1.0], dtype=np.float32)
    notes = _perfect_note_graph(n, ts)
    for i in range(n):
        notes[i]["fever"] = i >= 1
    _mark_fever_end_witness(
        notes,
        activation_index=1,
        fever_end_index=4,
        total_notes=n,
        fever_window_end_ms=1010.0,
        section=1,
    )
    notes[2]["note_result"] = "Great"
    notes[2]["delta_ms"] = None

    with pytest.raises(ValueError, match="unsupported fever-end guidance"):
        _mark_fever_end_cluster_safe_delta(
            notes,
            activation_index=1,
            fever_end_index=4,
            total_notes=n,
            fever_window_end_ms=1010.0,
            note_types=np.ones(n, dtype=np.int16),
        )


def test_fever_end_decoy_replay_at_cluster_delta_keeps_sequential_fever():
    import json
    import sqlite3

    from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF, team_buff_effect
    from gear_optimizer.data.database import get_evolution_db_path
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats
    from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs, resolve_stat_factors
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    song = "Decoy World VIP by INTERCOM feat. Park Avenue [Monstercat]"
    loadout_hash = "9466514779a185ba64c4198786581230"
    t1_opt = 7_845_087

    db_path = get_evolution_db_path()
    try:
        row = sqlite3.connect(db_path).execute(
            "SELECT force_details_json FROM team_buff_fg_loadouts WHERE loadout_hash=? AND song_name=?",
            (loadout_hash, song),
        ).fetchone()
    except Exception:
        pytest.skip("evolution DB unavailable")
    if row is None:
        pytest.skip("Decoy FG loadout not in local DB")

    fd = json.loads(row[0])
    calc = clone_calc_song(
        get_base_calc_song(
            "Data/Normal/Decoy World VIP by INTERCOM feat. Park Avenue [Monstercat].txt", {}
        )
    )
    apply_timing_envelope(calc)
    si = extract_fg_song_inputs(calc)
    nt = calc.get("song_data", {}).get("note_types")
    ts = np.asarray(si.timestamps)
    n = si.total_notes
    trace = fd["ForceGreats"]["frontier_trace"]

    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    ng = _exact_force_greats_note_graph(
        frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt
    )

    stats = read_visible_stats(fd)
    for key, val in {
        k: team_buff_effect("T1", "Rush").get(k, 0)
        - team_buff_effect(OPTIMIZER_BASELINE_TEAM_BUFF, "Rush").get(k, 0)
        for k in team_buff_effect("T1", "Rush")
    }.items():
        stats[key] = int(stats.get(key, 0)) + int(val)

    ref = get_exact_replay_ref_arrays_cached()
    f = resolve_stat_factors(stats, ref)
    real_ft = (float(si.last_note_time) * 0.15 + 0.15) * float(f.fever_time_stat)
    acts = [int(trace[0]["activation_index"]), int(trace[1]["activation_index"])]
    act_offs = [
        float(trace[0]["activation_hit_offset_ms"]),
        float(trace[1]["activation_hit_offset_ms"]),
    ]

    offsets = np.zeros(n, dtype=np.float64)
    for i, note in enumerate(ng):
        d = note.get("delta_ms")
        if d is not None:
            offsets[i] = float(d)

    static_fever = np.array([bool(x.get("fever")) for x in ng], dtype=bool)
    seq_fever = np.zeros(n, dtype=bool)
    act_ptr = 0
    window_end = -1.0
    for i in range(n):
        if act_ptr < len(acts) and i == acts[act_ptr]:
            window_end = float(ts[i]) + act_offs[act_ptr] / 1000.0 + real_ft
            act_ptr += 1
        if act_ptr > 0 and i >= acts[act_ptr - 1]:
            hit = float(ts[i]) + offsets[i] / 1000.0
            seq_fever[i] = hit < window_end

    assert np.array_equal(static_fever, seq_fever)
    # F1 tail cluster: chart notes 183/184 (zero-based indices 182/183); witness is 184.
    f1_tail = (182, 183)
    assert ng[f1_tail[1]]["is_fever_end_witness"] is True
    assert ng[f1_tail[0]]["delta_ms"] == pytest.approx(-9.93, abs=0.02)
    assert ng[f1_tail[1]]["delta_ms"] == pytest.approx(ng[f1_tail[0]]["delta_ms"])

    import sys
    from pathlib import Path

    verify_dir = Path(__file__).resolve().parents[1] / "tools" / "verify"
    if str(verify_dir) not in sys.path:
        sys.path.insert(0, str(verify_dir))
    from verify_fg_game_oracle import score_from_game_source

    great = np.array([x.get("note_result") == "Great" for x in ng], dtype=bool)
    assert score_from_game_source(
        stats=stats,
        primary_color="Rush",
        secondary_color="Vibe",
        fever_mask=seq_fever,
        great_mask=great,
    ) == t1_opt


def test_note_graph_lower_edges_are_reachable_not_the_exclusive_edge():
    """BUG-1 regression: the note-graph endpoint-early bounds must be the earliest REACHABLE hit
    (exclusive edge + 1ms), never the edge value itself. The engine judge is strict-`>`, so a hit at
    exactly the perfect-lower (-20/-40) is a Great and at the great-lower (-95/-190) is an Okay --
    replaying those through the oracle would certify illegal timings. Keep in lockstep with the
    production timing_envelope.py floor builders."""
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _perfect_bounds_ms_at,
        _early_great_bounds_ms_at,
    )

    nt = np.array([1, 3], dtype=np.int16)  # [0]=tap, [1]=held tail (x2 windows)

    # Perfect lower bound: earliest reachable Perfect is -19 (tap) / -39 (tail), NOT -20 / -40.
    p_tap_lo, p_tap_hi = _perfect_bounds_ms_at(nt, 0)
    p_tail_lo, p_tail_hi = _perfect_bounds_ms_at(nt, 1)
    assert p_tap_lo == -19 and p_tail_lo == -39, (p_tap_lo, p_tail_lo)
    assert p_tap_hi == 40 and p_tail_hi == 80, (p_tap_hi, p_tail_hi)   # upper edge inclusive, unchanged
    assert p_tap_lo > -20 and p_tail_lo > -40                          # strictly past the exclusive edge

    # Early-Great lower bound: earliest reachable early-Great is -94 (tap) / -189 (tail), NOT -95 / -190.
    g_tap_lo, g_tap_hi = _early_great_bounds_ms_at(nt, 0)
    g_tail_lo, g_tail_hi = _early_great_bounds_ms_at(nt, 1)
    assert g_tap_lo == -94 and g_tail_lo == -189, (g_tap_lo, g_tail_lo)
    assert g_tap_lo > -95 and g_tail_lo > -190                         # strictly past the exclusive edge
    # Early-Great-only region tops out at the latest legal early-Great (-20 / -40, inclusive), a full
    # ms below the Perfect-low (-19 / -39): a visible gap, and never overlapping the Perfect band.
    assert g_tap_hi == -20 and g_tail_hi == -40, (g_tap_hi, g_tail_hi)
    assert g_tap_hi < p_tap_lo and g_tail_hi < p_tail_lo


def test_preemptor_delay_reaches_partners_behind_delayed_sibling() -> None:
    """Regression (Aurora 47,502,676 witness): the forward preemptor-delay scan must not stop at
    a delayed same-time forced-Great sibling.

    Press times are not monotone over chart order once a witness is delayed: the bundle sibling
    at the activation's own late edge already satisfies the ordering requirement, but the
    still-on-time chord partners BEHIND it would press before the activation and steal the fill
    crossing (the engine activates fever on their Perfect fill, ending the window early). The
    scan must delay every window note whose press precedes the chained requirement, and stop
    only on the chart-time bound.
    """
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_activation_preemptor_order_deltas,
    )

    nt = np.asarray([1, 1, 1, 1, 1], dtype=np.int16)
    notes = [
        {"note_index": 0, "hit_time_ms": 96017.0, "note_result": "Great", "delta_ms": 189.999},
        {"note_index": 1, "hit_time_ms": 96017.0, "note_result": "Great", "delta_ms": 189.999},
        {"note_index": 2, "hit_time_ms": 96180.0, "note_result": "Perfect", "delta_ms": 0.0},
        {"note_index": 3, "hit_time_ms": 96180.0, "note_result": "Perfect", "delta_ms": 0.0},
        {"note_index": 4, "hit_time_ms": 97000.0, "note_result": "Perfect", "delta_ms": 0.0},
    ]
    _mark_activation_preemptor_order_deltas(
        notes, frontier_trace=[{"activation_index": 0}], total_notes=5, note_types=nt
    )

    required_delta = (96017.0 + 189.999) - 96180.0  # press at/after the activation hit
    assert float(notes[2]["delta_ms"]) >= required_delta, notes[2]  # was 0.0 pre-fix (break at sibling)
    assert float(notes[3]["delta_ms"]) >= required_delta, notes[3]
    assert float(notes[2]["delta_ms"]) <= 40.0  # stays a legal Perfect
    assert float(notes[3]["delta_ms"]) <= 40.0
    assert float(notes[4]["delta_ms"]) == 0.0  # beyond the 200ms chart window: untouched


def test_activation_preemptor_order_deltas_are_lane_scoped_when_lanes_are_supplied():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_activation_preemptor_order_deltas,
    )

    nt = np.asarray([1, 1], dtype=np.int16)
    notes = [
        {"note_index": 0, "hit_time_ms": 1000.0, "note_result": "Great", "delta_ms": 190.0},
        {"note_index": 1, "hit_time_ms": 1160.0, "note_result": "Perfect", "delta_ms": 0.0},
    ]

    _mark_activation_preemptor_order_deltas(
        notes,
        frontier_trace=[{"activation_index": 0}],
        total_notes=2,
        note_types=nt,
        lanes=np.asarray([1, 2], dtype=np.int32),
    )
    assert float(notes[1]["delta_ms"]) == 0.0

    _mark_activation_preemptor_order_deltas(
        notes,
        frontier_trace=[{"activation_index": 0}],
        total_notes=2,
        note_types=nt,
        lanes=np.asarray([1, 1], dtype=np.int32),
    )
    assert float(notes[1]["delta_ms"]) >= 30.0
    assert float(notes[1]["delta_ms"]) <= 40.0


def test_persisted_activation_schedule_orders_cross_lane_followers_after_activation():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _mark_activation_preemptor_order_deltas,
    )

    nt = np.asarray([1, 1], dtype=np.int16)
    notes = [
        {"note_index": 0, "hit_time_ms": 1000.0, "note_result": "Great", "delta_ms": 190.0},
        {"note_index": 1, "hit_time_ms": 1160.0, "note_result": "Perfect", "delta_ms": 0.0},
    ]
    trace = [{
        "activation_index": 0,
        "forced_start_index": 0,
        "activation_schedule_schema_version": 1,
        "preactivation_order": [],
        "preactivation_lane_prefixes": [
            {"lane": 1, "count": 0},
            {"lane": 2, "count": 0},
        ],
        "preactivation_fill_half_units": 0,
        "preactivation_event_count": 0,
        "preactivation_great_count": 0,
    }]

    _mark_activation_preemptor_order_deltas(
        notes,
        frontier_trace=trace,
        total_notes=2,
        note_types=nt,
        lanes=np.asarray([1, 2], dtype=np.int32),
        require_exact_schedule=True,
    )
    assert float(notes[1]["delta_ms"]) == pytest.approx(30.0)


def test_persisted_activation_schedule_jointly_fits_same_time_boundary_and_prefix():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _assign_exact_input_order,
        _mark_activation_preemptor_order_deltas,
    )

    nt = np.asarray([3, 1, 2, 1], dtype=np.int16)
    notes = [
        {"note_index": 0, "hit_time_ms": 1000.0, "note_result": "Perfect", "delta_ms": 0.0},
        {"note_index": 1, "hit_time_ms": 1000.0, "note_result": "Great", "delta_ms": None},
        {"note_index": 2, "hit_time_ms": 1000.0, "note_result": "Perfect", "delta_ms": 0.0},
        {"note_index": 3, "hit_time_ms": 1100.0, "note_result": "Perfect", "delta_ms": 0.0},
    ]
    trace = [{
        "activation_index": 3,
        "forced_start_index": 1,
        "activation_schedule_schema_version": 1,
        "preactivation_order": [1, 2],
        "preactivation_lane_prefixes": [
            {"lane": 1, "count": 1},
            {"lane": 2, "count": 1},
            {"lane": 3, "count": 0},
        ],
        "preactivation_fill_half_units": 3,
        "preactivation_event_count": 2,
        "preactivation_great_count": 1,
    }]

    constraints = _mark_activation_preemptor_order_deltas(
        notes,
        frontier_trace=trace,
        total_notes=4,
        note_types=nt,
        lanes=np.asarray([0, 1, 2, 3], dtype=np.int32),
        require_exact_schedule=True,
    )

    assert constraints == [(0, 1), (1, 2), (2, 3)]
    event_times = [float(note["hit_time_ms"]) + float(note["delta_ms"]) for note in notes]
    assert event_times == sorted(event_times)
    assert float(notes[0]["delta_ms"]) == -20.0
    assert float(notes[1]["delta_ms"]) == -20.0
    assert float(notes[2]["delta_ms"]) == 0.0
    _assign_exact_input_order(notes, constraints)


def test_persisted_activation_schedule_chains_postactivation_notes_per_lane():
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        _assign_exact_input_order,
        _mark_activation_preemptor_order_deltas,
    )

    nt = np.asarray([1, 1, 1], dtype=np.int16)
    notes = [
        {"note_index": 0, "hit_time_ms": 1000.0, "note_result": "Great", "delta_ms": 100.0},
        {"note_index": 1, "hit_time_ms": 1000.0, "note_result": "Great", "delta_ms": 190.0},
        {"note_index": 2, "hit_time_ms": 1137.0, "note_result": "Perfect", "delta_ms": 0.0},
    ]
    trace = [{
        "activation_index": 0,
        "forced_start_index": 0,
        "activation_schedule_schema_version": 1,
        "preactivation_order": [],
        "preactivation_lane_prefixes": [
            {"lane": 1, "count": 0},
            {"lane": 2, "count": 0},
            {"lane": 3, "count": 0},
        ],
        "preactivation_fill_half_units": 0,
        "preactivation_event_count": 0,
        "preactivation_great_count": 0,
    }]

    constraints = _mark_activation_preemptor_order_deltas(
        notes,
        frontier_trace=trace,
        total_notes=3,
        note_types=nt,
        lanes=np.asarray([1, 2, 3], dtype=np.int32),
        require_exact_schedule=True,
    )

    assert constraints == [(0, 1), (0, 2)]
    assert float(notes[2]["delta_ms"]) == 0.0
    _assign_exact_input_order(notes, constraints)
    assert [int(note["input_order"]) for note in notes] == [0, 2, 1]


def test_physical_replay_validates_exact_surface_and_event_time_fever() -> None:
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_force_greats_physical_replay,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    trace = [{
        "section": 1,
        "activation_index": 0,
        "fever_end_index": 2,
        "forced_start_index": 0,
        "forced_prefix_count": 0,
        "forced_run_start_index": 0,
        "forced_run_count": 0,
        "activation_judgment": "perfect",
        "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": 10_000.0,
        "fever_duration_ms": 10_000.0,
        "activation_schedule_schema_version": 1,
        "preactivation_order": [],
        "preactivation_lane_prefixes": [
            {"lane": 0, "count": 0},
            {"lane": 1, "count": 0},
        ],
        "preactivation_fill_half_units": 0,
        "preactivation_event_count": 0,
        "preactivation_great_count": 0,
    }]
    replay = validate_force_greats_physical_replay(
        frontier_trace=trace,
        surface=FgResponseSurface(3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        timestamps=np.asarray([0.0, 0.1], dtype=np.float32),
        note_types=np.ones(2, dtype=np.int16),
        lanes=np.asarray([0, 1], dtype=np.int32),
        raw_fever_fill=1.0,
        real_fever_time=10.0,
    )
    assert replay.event_order == (0, 1)
    assert replay.fever_mask == (True, True)
    assert replay.judgments == ("Perfect", "Perfect")


def test_physical_replay_preserves_exact_body_cross_lane_prefix_swap() -> None:
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        validate_force_greats_physical_replay,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    n = 104
    timestamps = np.concatenate(
        (np.arange(100, dtype=np.float32) * np.float32(0.001), np.full(4, 0.1, np.float32))
    )
    lanes = np.arange(10_000, 10_000 + n, dtype=np.int32)
    lanes[100:] = np.asarray([2_000, 2_001, 2_002, 2_001], dtype=np.int32)
    preactivation_order = [*range(100), 101, 103]
    lane_prefixes = [
        *({"lane": int(lanes[index]), "count": 1} for index in range(100)),
        {"lane": 2_000, "count": 0},
        {"lane": 2_001, "count": 2},
        {"lane": 2_002, "count": 0},
    ]
    trace = [{
        "section": 1,
        "activation_index": 102,
        "fever_end_index": 104,
        "forced_start_index": 0,
        "forced_prefix_count": 0,
        "forced_run_start_index": 104,
        "forced_run_count": 0,
        "activation_judgment": "perfect",
        "activation_hit_offset_ms": 20.0,
        "fever_window_end_ms": 1_140.0,
        "fever_duration_ms": 1_000.0,
        "activation_schedule_schema_version": 1,
        "preactivation_order": preactivation_order,
        "preactivation_lane_prefixes": lane_prefixes,
        "preactivation_fill_half_units": 204,
        "preactivation_event_count": 102,
        "preactivation_great_count": 0,
    }]

    replay = validate_force_greats_physical_replay(
        frontier_trace=trace,
        surface=FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0),
        timestamps=timestamps,
        note_types=np.ones(n, dtype=np.int16),
        lanes=lanes,
        raw_fever_fill=102.5,
        real_fever_time=1.0,
    )

    assert replay.event_order[-4:] == (101, 103, 102, 100)
    assert replay.fever_mask[100:] == (True, False, True, False)


def test_physical_replay_models_one_wasted_exit_hit_without_frame_extension() -> None:
    from gear_optimizer.solver.fg_response_scoring.physical_replay import (
        _event_time_fever_mask,
    )

    fever = _event_time_fever_mask(
        event_order=(0, 1, 2, 3),
        event_times_ms=np.asarray([0.0, 100.0, 1_200.0, 1_300.0]),
        judgments=("Perfect", "Perfect", "Perfect", "Perfect"),
        fever_fill_denom=2.0,
        fever_time_seconds=1.0,
    )
    assert fever == (False, True, False, False)


def test_perfect_window_fg_rejects_legacy_trace_without_exact_schedule() -> None:
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph

    with pytest.raises(ValueError, match="exact activation schedule schema v1 is required"):
        force_greats_note_graph(
            frontier_trace=[{
                "section": 1,
                "activation_index": 0,
                "fever_end_index": 2,
                "forced_start_index": 0,
                "forced_prefix_count": 0,
                "activation_judgment": "perfect",
                "activation_hit_offset_ms": 0.0,
                "fever_window_end_ms": 1_000.0,
            }],
            total_notes=2,
            timestamps=np.asarray([0.0, 0.1], dtype=np.float32),
            note_types=np.ones(2, dtype=np.int16),
            lanes=np.asarray([0, 1], dtype=np.int32),
            timing_mode="perfect_window",
        )
