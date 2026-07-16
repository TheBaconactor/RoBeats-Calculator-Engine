"""CPU micro-benchmark: new numba FG physical replay vs the original Python-loop body.

No GPU. Uses the real Alice (Hard) trace (n=1597) built on CPU. Reports warm per-call wall time
and, separately, the GIL-held portion (Python gather + tuple build) vs the nogil numba pass, so we
can judge how much owner-launch-loop GIL contention this actually removes.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from gear_optimizer.solver.fg_response_scoring.note_graph import (
    force_greats_note_graph,
    reconcile_force_greats_note_graph,
)
from gear_optimizer.solver.fg_response_scoring.physical_replay import (
    _HELD_TAIL_TYPE,
    _RESULT_CODE,
    _event_time_fever_mask,
    _force_greats_replay_kernel,
    _judgment_at,
    validate_force_greats_physical_replay,
)
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.song_preparation import build_prepared_calc_song
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    reconstruct_force_greats_response_trace,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

ROOT = Path(__file__).resolve().parents[2]


def _old_body(graph, nt, lane_arr, raw_fever_fill, real_fever_time):
    """Faithful copy of the pre-numba wrapper body (per-note loops in pure Python)."""
    n = len(graph)
    event_times_ms = np.empty(n, dtype=np.float64)
    judgments: list[str] = []
    for index, note in enumerate(graph):
        delta = note.get("delta_ms")
        expected = str(note.get("note_result", ""))
        actual = _judgment_at(float(delta), held_tail=int(nt[index]) == _HELD_TAIL_TYPE)
        if actual != expected:
            raise ValueError("mismatch")
        event_times_ms[index] = float(note["hit_time_ms"]) + float(delta)
        judgments.append(expected)
    input_orders = tuple(int(note.get("input_order", -1)) for note in graph)
    if tuple(sorted(input_orders)) != tuple(range(n)):
        raise ValueError("bad order")
    event_order = tuple(int(i) for i in sorted(range(n), key=input_orders.__getitem__))
    expected_by_lane: dict[int, list[int]] = {}
    for index, lane_value in enumerate(lane_arr):
        expected_by_lane.setdefault(int(lane_value), []).append(int(index))
    lane_cursors = {lane: 0 for lane in expected_by_lane}
    for index in event_order:
        lane = int(lane_arr[index])
        cursor = int(lane_cursors[lane])
        if int(index) != int(expected_by_lane[lane][cursor]):
            raise ValueError("lane")
        lane_cursors[lane] = cursor + 1
    replay_fever = _event_time_fever_mask(
        event_order=event_order,
        event_times_ms=event_times_ms,
        judgments=judgments,
        fever_fill_denom=float(raw_fever_fill),
        fever_time_seconds=float(real_fever_time),
    )
    return event_order, replay_fever, tuple(judgments)


def _new_split(graph, nt, lane_arr, raw_fever_fill, real_fever_time):
    """Same as the shipped wrapper, but times the GIL-held gather vs the nogil kernel separately."""
    n = len(graph)
    t0 = time.perf_counter()
    delta_ms = np.empty(n, dtype=np.float64)
    hit_time_ms = np.empty(n, dtype=np.float64)
    input_order = np.empty(n, dtype=np.int64)
    expected_result_code = np.empty(n, dtype=np.int8)
    expected_fever = np.empty(n, dtype=np.int8)
    judgments: list[str] = []
    for index, note in enumerate(graph):
        expected = str(note.get("note_result", ""))
        judgments.append(expected)
        delta_ms[index] = float(note["delta_ms"])
        hit_time_ms[index] = float(note["hit_time_ms"])
        input_order[index] = int(note.get("input_order", -1))
        expected_result_code[index] = _RESULT_CODE.get(expected, -1)
        expected_fever[index] = 1 if note.get("fever") else 0
    t1 = time.perf_counter()
    event_order_arr = np.empty(n, dtype=np.int64)
    replay_fever_arr = np.empty(n, dtype=np.int8)
    _force_greats_replay_kernel(
        delta_ms, hit_time_ms, input_order, expected_result_code, expected_fever,
        nt, lane_arr, float(raw_fever_fill), float(real_fever_time), event_order_arr, replay_fever_arr,
    )
    t2 = time.perf_counter()
    _ = tuple(int(x) for x in event_order_arr)
    _ = tuple(bool(x) for x in replay_fever_arr)
    _ = tuple(judgments)
    t3 = time.perf_counter()
    return (t1 - t0) + (t3 - t2), (t2 - t1)  # (gil_held_s, nogil_s)


def main() -> None:
    calc_song = build_prepared_calc_song(
        fp=str(ROOT / "Data" / "Hard" / "Alice in Misanthrope (Hard) by LeaF (7eaF).txt"),
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
    ts = np.asarray(song_inputs.timestamps, dtype=np.float64).reshape(-1)
    nt = np.asarray(calc_song["song_data"]["note_types"], dtype=np.int32).reshape(-1)
    lane_arr = np.asarray(song_inputs.lanes, dtype=np.int32).reshape(-1)
    n = int(ts.shape[0])
    graph = force_greats_note_graph(
        frontier_trace=trace, total_notes=n, timestamps=ts, note_types=nt, lanes=lane_arr,
        timing_mode="perfect_window",
    )
    reconcile_force_greats_note_graph(
        graph, total_notes=n,
        fever_words=(surface.fever0, surface.fever1, surface.fever2, surface.fever3),
        great_words=(surface.great0, surface.great1, surface.great2, surface.great3),
        body_fever=surface.body_fever, body_great=surface.body_great, body_fever_great=surface.body_fever_great,
    )
    print(f"n notes = {n}")

    # Warm both paths (numba compile).
    _old_body(graph, nt, lane_arr, raw_fever_fill, real_fever_time)
    _new_split(graph, nt, lane_arr, raw_fever_fill, real_fever_time)
    validate_force_greats_physical_replay(
        frontier_trace=trace, surface=surface, timestamps=ts, note_types=nt, lanes=lane_arr,
        raw_fever_fill=raw_fever_fill, real_fever_time=real_fever_time,
    )

    iters = 200
    t = time.perf_counter()
    for _ in range(iters):
        _old_body(graph, nt, lane_arr, raw_fever_fill, real_fever_time)
    old_ms = (time.perf_counter() - t) / iters * 1000.0

    t = time.perf_counter()
    for _ in range(iters):
        validate_force_greats_physical_replay(
            frontier_trace=trace, surface=surface, timestamps=ts, note_types=nt, lanes=lane_arr,
            raw_fever_fill=raw_fever_fill, real_fever_time=real_fever_time,
        )
    new_full_ms = (time.perf_counter() - t) / iters * 1000.0

    gil_tot = 0.0
    nogil_tot = 0.0
    for _ in range(iters):
        g, ng = _new_split(graph, nt, lane_arr, raw_fever_fill, real_fever_time)
        gil_tot += g
        nogil_tot += ng
    gil_ms = gil_tot / iters * 1000.0
    nogil_ms = nogil_tot / iters * 1000.0

    print(f"OLD body (all-Python, GIL-held whole time): {old_ms:.4f} ms/call")
    print(f"NEW validate_force_greats_physical_replay:   {new_full_ms:.4f} ms/call")
    print(f"NEW gather+return (GIL-held):                {gil_ms:.4f} ms/call")
    print(f"NEW numba kernel (nogil, GIL released):      {nogil_ms:.4f} ms/call")
    print(f"speedup (old/new-full): {old_ms / new_full_ms:.2f}x")
    print(f"GIL-held reduction (old -> new gil): {old_ms:.4f} -> {gil_ms:.4f} ms "
          f"({old_ms / gil_ms:.2f}x less GIL time per call)")


if __name__ == "__main__":
    main()
