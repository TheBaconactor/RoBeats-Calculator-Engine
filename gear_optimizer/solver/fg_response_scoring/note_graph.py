"""Per-loadout note-graph reconstruction data (Deliverable B).

Produces, per note, exactly the fields the game's client `NoteTimeGraph`
(`ReplicatedStorage/Lobby/UI/NoteTimeGraph.lua`) renders for a registered hit:

    HitTime    -> hit_time_ms   (note position on the song timeline, ms)
    Delta      -> delta_ms       (hit timing offset, ms; +late / -early). Carries the exact
                                  offset for every note whose timing is load-bearing: the
                                  activation witness (fever-start, hit late) and any
                                  endpoint-early fever note (issue #42 -- a note at/after the
                                  fever cutoff that is in fever only because it is hit early).
                                  Notes whose timing does not matter stay at 0.
    NoteResult -> note_result    ("Perfect" | "Great"; never "Miss" -- the
                                  optimizer's solution assumes every note is hit)
    Fever      -> fever           (bool; the game draws the fever bar across the
                                  contiguous fevered notes)

This is RECONSTRUCTION DATA, not a frontend. The candidate-INDEPENDENT cache + the
per-loadout persisted witness data (`evolution.db`) are mapped onto the runtime song
note times (the frontend feeds the game's Rojo `HitObjects`, which share ordering and
ms with the optimizer's `timestamps`). The gear-stat window lines (`get_note_times`)
are derived frontend-side from the persisted stats.

Two graphs per loadout, matching the intended software behavior:
  * BASE = timeline frontier            -> base_note_graph(..., timing_mode=...)
        all notes Perfect; selected activation witnesses carry exact `delta_ms`
        when a compact timeline trace is available. The last note of each fever
        run is also a witness (`is_fever_end_witness`) carrying `fever_end_ms`,
        the largest-cushion fever cutoff time -- symmetric to the activation
        witness that anchors where fever starts.
  * FG   = fg frontier + timeline       -> force_greats_note_graph(..., timing_mode=...)
        per-note Perfect/Great + fever; optimized activation hits are timing
        WITNESSES (Perfect-window or Late-Great, carrying exact `delta_ms`);
        prefix/forced Greats are pure v3 selectors unless a same-chart-time cluster
        needs an explicit early/late Great witness to preserve the scored head-ramp
        order.

``timing_mode`` selects the timing semantic (issue #66):
  * ``"perfect_window"`` (default): apply activation witness offsets, endpoint-early
    guidance, and fever-end safe-target guidance.
  * ``"zero_ms"``: every playable hit at chart time (`delta_ms=0.0`; Great selectors
    stay ``None``). Fever/great sets and witness metadata are unchanged.

Both are reconstructable losslessly from already-persisted data (FG: `frontier_trace`
+ `response_surface`; BASE: the packed stats, replayed through the fever timeline),
so there is no candidate-dependent re-solve and no bulky per-note persistence.
"""

from __future__ import annotations

import heapq
from typing import Any, Mapping, Sequence

import numpy as np

from gear_optimizer.core.time_quantize import snap_near_int_ms

from gear_optimizer.solver.input_engine_breakpoints import latest_activation_hit_from_label_highs

__all__ = [
    "base_note_graph",
    "timeline_frontier_note_graph",
    "force_greats_note_graph",
    "reconcile_force_greats_note_graph",
]

# RAW judgment early edges (ms), matching the scoring envelope (timing_envelope.py). The engine
# judge is strict-`>` at the early edge (SPUtil.timedelta_to_result / WebPort judgeWithEdges: a band
# is `lower < delta <= upper`), so the edge value itself is NOT in that band -- `-20` is judged
# Great, `-95` Okay. The earliest REACHABLE hit is therefore `edge*mult + 1` ms (the +1 is applied
# AFTER the held-tail x2, so a tail is `-40 -> -39`, not `-38`). Consumers below add the +1; the
# constants stay the raw edges so the x2 scaling is correct. (BUG-1: keep in lockstep with
# timing_envelope.py, else the oracle harness replays illegal hit timings.)
_PERFECT_LOWER_MS = -20
_PERFECT_UPPER_MS = 40
_GREAT_UPPER_MS = 190
_HELD_TAIL_TYPE = 3
_HELD_TAIL_TIME_MULT = 2
_FEVER_END_SAME_CHART_TIME_MS = 0.01
_TIMING_MODES = frozenset({"perfect_window", "zero_ms"})
_EARLY_GREAT_LOWER_EXTRA_MS = -75.0
_EARLY_GREAT_FLOOR_MS = float(_PERFECT_LOWER_MS) + float(_EARLY_GREAT_LOWER_EXTRA_MS)  # -95
_EARLY_GREAT_ONLY_UPPER_GAP_MS = 1.0


def _normalize_timing_mode(timing_mode: str) -> str:
    mode = str(timing_mode or "perfect_window").strip().lower()
    if mode not in _TIMING_MODES:
        raise ValueError(f"note_graph: unknown timing_mode {timing_mode!r}")
    return mode


def _strictly_before_cutoff_ms(cutoff_ms: float) -> float:
    """Return the greatest float64 event time that remains strictly before a finite cutoff."""
    cutoff = np.float64(cutoff_ms)
    if not np.isfinite(cutoff):
        raise ValueError("note_graph: fever cutoff must be finite")
    upper = np.nextafter(cutoff, np.float64(-np.inf))
    if not np.isfinite(upper) or not upper < cutoff:
        raise ValueError("note_graph: fever cutoff has no finite strict predecessor")
    return float(upper)


def _perfect_bounds_ms_at(note_types: np.ndarray, j: int) -> tuple[float, float]:
    if int(note_types.shape[0]) <= j:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "fever-end cluster timing at the note's legal judgment bounds -- it is never guessed"
        )
    mult = _HELD_TAIL_TIME_MULT if int(note_types[j]) == _HELD_TAIL_TYPE else 1
    # +1 after the x2: earliest REACHABLE Perfect is the exclusive edge + 1ms (-19 / tail -39).
    return float(_PERFECT_LOWER_MS * mult + 1), float(_PERFECT_UPPER_MS * mult)


def _early_great_bounds_ms_at(note_types: np.ndarray, j: int) -> tuple[float, float]:
    """Return early-Great-only guidance bounds for note j (issue #68).

    Great-only endpoint claw-in is a different semantic than Perfect-window claw-in:
    a note that is fevered only via an early Great hit should be shown inside the
    early-Great band, not collapsed to the Perfect-low line.
    """
    if int(note_types.shape[0]) <= j:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "early-Great fever-end timing at judgment bounds -- it is never guessed"
        )
    mult = _HELD_TAIL_TIME_MULT if int(note_types[j]) == _HELD_TAIL_TYPE else 1
    # +1 after the x2: earliest REACHABLE early-Great is the exclusive edge + 1ms (-94 / tail -189).
    great_low = float(_EARLY_GREAT_FLOOR_MS * mult + 1)
    # Great-only region ends at the latest early-Great (inclusive `-20` edge; the Perfect band opens
    # at the exclusive `-19`), i.e. perfect_low - gap. The +1 on perfect_low provides the visible gap.
    great_high = float((_PERFECT_LOWER_MS * mult + 1) - _EARLY_GREAT_ONLY_UPPER_GAP_MS)
    return great_low, great_high


def _late_great_bounds_ms_at(note_types: np.ndarray, j: int) -> tuple[float, float]:
    if int(note_types.shape[0]) <= j:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "same-time forced-Great selector timing at judgment bounds -- it is never guessed"
        )
    mult = _HELD_TAIL_TIME_MULT if int(note_types[j]) == _HELD_TAIL_TYPE else 1
    return float(_PERFECT_UPPER_MS * mult + 1), float(_GREAT_UPPER_MS * mult)


def _selector_default_delta_ms(note_types: np.ndarray, j: int, result: str, delta: Any) -> float:
    if delta is not None:
        return float(delta)
    if result == "Perfect":
        return 0.0
    if result == "Great":
        late_lo, _late_hi = _late_great_bounds_ms_at(note_types, j)
        return float(late_lo)
    raise ValueError(f"note_graph: cannot infer timing for result {result!r} at note {j}")


def _activation_materialized_delta_ms(
    sec: Mapping[str, Any],
    *,
    notes: Sequence[Mapping[str, Any]] | None = None,
    total_notes: int | None = None,
    note_types: Sequence[int] | np.ndarray | None,
    lanes: Sequence[int] | np.ndarray | None = None,
    note_index: int,
    judgment: str,
) -> float:
    """Return the latest activation hit that preserves the scored input order."""
    nt = None if note_types is None else np.asarray(note_types).reshape(-1)
    lane_arr = None if lanes is None else np.asarray(lanes, dtype=np.int32).reshape(-1)
    a = int(note_index)
    raw_center = float(sec["activation_hit_offset_ms"])
    if nt is None:
        return float(raw_center)
    raw_center = _snap_engine_time_ms(float(raw_center))
    if judgment == "late_great":
        judge_lo, judge_hi = _late_great_bounds_ms_at(nt, a)
    elif judgment == "perfect":
        judge_lo, judge_hi = _perfect_bounds_ms_at(nt, a)
    else:
        return float(raw_center)

    if notes is not None and 0 <= a < len(notes):
        chart_ms = float(notes[a]["hit_time_ms"])
    else:
        chart_ms = float(sec.get("activation_ms", 0.0) or 0.0)
    absolute_center = sec.get("activation_hit_ms")
    center = (
        _snap_engine_time_ms(float(absolute_center) - float(chart_ms))
        if absolute_center is not None
        else float(raw_center)
    )

    has_hit_window = any(
        sec.get(key) is not None
        for key in (
            "activation_hit_offset_lower_ms",
            "activation_hit_offset_upper_ms",
            "activation_hit_window_lower_ms",
            "activation_hit_window_upper_ms",
        )
    )
    if not has_hit_window:
        return float(center)

    def _offset_field(name: str, fallback: float) -> float:
        window_key = f"activation_hit_window_{name}_ms"
        value = sec.get(window_key)
        if value is not None:
            return _snap_engine_time_ms(float(value) - float(chart_ms))
        offset_key = f"activation_hit_offset_{name}_ms"
        value = sec.get(offset_key)
        if value is not None:
            return _snap_engine_time_ms(float(value))
        return float(fallback)

    lo = max(float(judge_lo), _offset_field("lower", center))
    hi = min(float(judge_hi), _offset_field("upper", center))
    if lo > hi:
        raise ValueError(
            f"note_graph: activation witness interval is empty at note {a} "
            f"({lo:.3f}ms > {hi:.3f}ms)"
        )

    label_high_ms: np.ndarray | None = None
    if notes is not None and total_notes is not None:
        n = min(int(total_notes), len(notes), int(nt.shape[0]))
        if lane_arr is not None:
            n = min(n, int(lane_arr.shape[0]))
        chart_timestamps_ms = np.empty((n,), dtype=np.float64)
        label_high_ms = np.empty((n,), dtype=np.float64)
        for j in range(n):
            note = notes[j]
            chart_timestamps_ms[j] = float(note["hit_time_ms"])
            result = str(note.get("note_result", "Perfect"))
            if result == "Perfect":
                _label_lo, label_hi = _perfect_bounds_ms_at(nt, j)
            elif result == "Great":
                _early_lo, early_hi = _early_great_bounds_ms_at(nt, j)
                _late_lo, late_hi = _late_great_bounds_ms_at(nt, j)
                label_hi = max(float(early_hi), float(late_hi))
            else:
                raise ValueError(f"note_graph: cannot order unsupported result {result!r} at note {j}")
            label_high_ms[j] = float(note["hit_time_ms"]) + float(label_hi)
        hit_ms = latest_activation_hit_from_label_highs(
            activation_index=a,
            hit_lo=float(chart_ms) + float(lo),
            hit_hi=float(chart_ms) + float(hi),
            chart_timestamps=chart_timestamps_ms,
            label_high_timestamps=label_high_ms,
            section_end=n,
            lanes=(
                None
                if int(sec.get("activation_schedule_schema_version", 0) or 0) == 1
                else lane_arr
            ),
            epsilon=0.001,
        )
    else:
        hit_ms = float(chart_ms) + float(hi)

    if hit_ms is None:
        raise ValueError(
            "note_graph: activation witness cannot preserve following note order without "
            f"changing note {a}'s {judgment} judgment"
        )

    delta = min(float(hi), float(hit_ms) - float(chart_ms))
    if delta < lo:
        raise ValueError(
            "note_graph: activation witness cannot preserve following note order without "
            f"changing note {a}'s {judgment} judgment"
        )
    return float(delta)


def _materialized_fever_window_end_ms(
    sec: Mapping[str, Any],
    *,
    activation_delta_ms: float | None,
    activation_chart_ms: float | None = None,
) -> float | None:
    fever_end = sec.get("fever_window_end_ms")
    if fever_end is None or activation_delta_ms is None:
        return None if fever_end is None else float(fever_end)
    chart_ms = (
        float(activation_chart_ms)
        if activation_chart_ms is not None
        else float(sec.get("activation_ms", 0.0) or 0.0)
    )
    priced_hit_ms = sec.get("activation_hit_window_upper_ms")
    if priced_hit_ms is None:
        priced_delta = sec.get("activation_hit_offset_upper_ms", sec.get("activation_hit_offset_ms"))
        if priced_delta is not None:
            priced_hit_ms = float(chart_ms) + _snap_engine_time_ms(float(priced_delta))
    if priced_hit_ms is None:
        return float(fever_end)
    duration_ms = float(fever_end) - float(priced_hit_ms)
    if duration_ms <= 0.0:
        return float(fever_end)
    return float(chart_ms) + float(activation_delta_ms) + float(duration_ms)


def _bounded_judgment_delta_ms(
    note_types: np.ndarray,
    j: int,
    result: str,
    *,
    preferred_delta_ms: float,
    min_delta_ms: float = -np.inf,
    max_delta_ms: float = np.inf,
) -> float:
    if result == "Perfect":
        intervals = (_perfect_bounds_ms_at(note_types, j),)
    elif result == "Great":
        early_lo, early_hi = _early_great_bounds_ms_at(note_types, j)
        late_lo, late_hi = _late_great_bounds_ms_at(note_types, j)
        intervals = ((early_lo, early_hi), (late_lo, late_hi))
    else:
        raise ValueError(f"note_graph: unsupported result {result!r} at note {j}")

    candidates: list[float] = []
    for lo, hi in intervals:
        feasible_lo = max(float(lo), float(min_delta_ms))
        feasible_hi = min(float(hi), float(max_delta_ms))
        if feasible_lo <= feasible_hi:
            candidates.append(min(max(float(preferred_delta_ms), feasible_lo), feasible_hi))
    if not candidates:
        raise ValueError(
            "note_graph: exact input order has no legal bounded hit "
            f"for note {j}'s {result} judgment"
        )
    if np.isposinf(preferred_delta_ms):
        return max(candidates)
    if np.isneginf(preferred_delta_ms):
        return min(candidates)
    return min(candidates, key=lambda delta: (abs(delta - float(preferred_delta_ms)), delta))


def _delta_at_or_after_ms(note_types: np.ndarray, j: int, result: str, min_delta_ms: float) -> float:
    return _bounded_judgment_delta_ms(
        note_types,
        j,
        result,
        preferred_delta_ms=float(min_delta_ms),
        min_delta_ms=float(min_delta_ms),
    )


def _delta_at_or_before_ms(note_types: np.ndarray, j: int, result: str, max_delta_ms: float) -> float:
    return _bounded_judgment_delta_ms(
        note_types,
        j,
        result,
        preferred_delta_ms=float(max_delta_ms),
        max_delta_ms=float(max_delta_ms),
    )


def _center_safe_delta(*, low_ms: float, high_ms: float) -> float:
    return 0.5 * (float(low_ms) + float(high_ms))


def _same_chart_time_ms(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= _FEVER_END_SAME_CHART_TIME_MS


def _snap_engine_time_ms(value: float) -> float:
    return float(snap_near_int_ms(np.asarray(float(value), dtype=np.float32)))


def _hit_time_ms(timestamps: np.ndarray, idx: int) -> float:
    return float(timestamps[int(idx)]) * 1000.0


def _perfect_note_graph(total_notes: int, timestamps: Sequence[float] | np.ndarray) -> list[dict[str, Any]]:
    n = int(total_notes)
    ts = np.asarray(timestamps).reshape(-1)
    if int(ts.shape[0]) < n:
        raise ValueError("note graph timestamps shorter than total_notes")
    return [
        {
            "note_index": int(i),
            "hit_time_ms": _hit_time_ms(ts, i),
            "note_result": "Perfect",
            "delta_ms": 0.0,
            "input_order": int(i),
            "fever": False,
            "is_activation_witness": False,
            "is_fever_end_witness": False,
            "fever_end_ms": None,
            "section": 0,
        }
        for i in range(n)
    ]


def _mark_same_time_selector_order_deltas(
    notes: list[dict[str, Any]],
    *,
    total_notes: int,
    note_types: Sequence[int] | np.ndarray | None,
) -> None:
    """Give same-time forced-Great selectors concrete offsets when combo order matters.

    A selector Great (`delta_ms is None`) is not a fever-boundary witness, but in the first
    100-note ramp its physical order still changes score. The scored surface indexes head
    bits in chart order, so the replay/display witness must keep same-chart-time clusters in
    that order. Great-before-Perfect therefore uses the early-Great band; Perfect-before-Great
    uses the late-Great band. If a mixed cluster cannot be ordered without changing a judgment,
    fail loudly: that surface is not a legal witness for the scored ramp.
    """
    graph_n = min(int(total_notes), len(notes))
    if graph_n <= 1:
        return

    # Chart-index ordering is score-bearing only while the combo multiplier ramps. Include the
    # complete same-time cluster crossing the head/body boundary, but leave body-only clusters to
    # their physical event times and the exact activation constraints below.
    n = min(graph_n, 100)
    while n < graph_n and _same_chart_time_ms(notes[n - 1]["hit_time_ms"], notes[n]["hit_time_ms"]):
        n += 1

    clusters: list[list[int]] = []
    current: list[int] = [0]
    for idx in range(1, n):
        if _same_chart_time_ms(notes[idx - 1]["hit_time_ms"], notes[idx]["hit_time_ms"]):
            current.append(idx)
            continue
        if len(current) > 1:
            clusters.append(current)
        current = [idx]
    if len(current) > 1:
        clusters.append(current)
    if not clusters:
        return

    nt: np.ndarray | None = None
    for cluster in clusters:
        has_selector = any(
            str(notes[j].get("note_result", "Perfect")) == "Great" and notes[j].get("delta_ms") is None
            for j in cluster
        )
        if not has_selector:
            continue
        if nt is None:
            if note_types is None:
                raise ValueError(
                    "note_graph: note_types (length == total_notes) is required to display "
                    "same-time forced-Great selector timing at judgment bounds -- it is never guessed"
                )
            nt = np.asarray(note_types).reshape(-1)

        latest_deltas = [np.inf] * len(cluster)
        latest_delta = np.inf
        for position in range(len(cluster) - 1, -1, -1):
            j = int(cluster[position])
            note = notes[j]
            result = str(note.get("note_result", "Perfect"))
            delta = note.get("delta_ms")
            if result == "Great" and delta is None:
                latest_delta = _delta_at_or_before_ms(nt, j, result, float(latest_delta))
                latest_deltas[position] = float(latest_delta)
                continue
            if delta is None:
                # Only Great selectors are allowed to omit a timing witness.
                raise ValueError(
                    f"note_graph: same-time cluster note {j} has no timing witness for result {result!r}"
                )
            fixed_delta = float(delta)
            if fixed_delta > latest_delta:
                next_index = int(cluster[position + 1])
                raise ValueError(
                    "note_graph: same-time cluster witness order contradicts chart-index score order "
                    f"at note {j} ({fixed_delta}ms > note {next_index}'s latest {latest_delta}ms)"
                )
            latest_delta = fixed_delta
            latest_deltas[position] = fixed_delta

        previous_delta = -np.inf
        for position, j in enumerate(cluster):
            note = notes[j]
            result = str(note.get("note_result", "Perfect"))
            delta = note.get("delta_ms")
            if result == "Great" and delta is None:
                early_lo, early_hi = _early_great_bounds_ms_at(nt, j)
                chosen = _bounded_judgment_delta_ms(
                    nt,
                    j,
                    result,
                    preferred_delta_ms=_center_safe_delta(low_ms=early_lo, high_ms=early_hi),
                    min_delta_ms=float(previous_delta),
                    max_delta_ms=float(latest_deltas[position]),
                )
                note["delta_ms"] = float(chosen)
                previous_delta = float(chosen)
                continue

            fixed_delta = float(delta)
            if fixed_delta < previous_delta:
                raise ValueError(
                    "note_graph: same-time cluster witness order contradicts chart-index score order "
                    f"at note {j} ({fixed_delta}ms < {previous_delta}ms)"
                )
            previous_delta = fixed_delta


def _materialize_preactivation_schedule(
    notes: list[dict[str, Any]],
    *,
    note_types: np.ndarray,
    exact_order: Sequence[int],
    activation_index: int,
    boundary_index: int | None,
) -> None:
    """Project preferred witness times into one exact monotone interval schedule."""
    activation = notes[int(activation_index)]
    activation_press = float(activation["hit_time_ms"]) + float(activation["delta_ms"])

    latest_presses = [0.0] * len(exact_order)
    latest_press = float(activation_press)
    for position in range(len(exact_order) - 1, -1, -1):
        index = int(exact_order[position])
        note = notes[index]
        result = str(note.get("note_result", "Perfect"))
        latest_delta = _delta_at_or_before_ms(
            note_types,
            index,
            result,
            latest_press - float(note["hit_time_ms"]),
        )
        latest_press = float(note["hit_time_ms"]) + float(latest_delta)
        latest_presses[position] = float(latest_press)

    required_press = -np.inf
    if boundary_index is not None:
        boundary = notes[int(boundary_index)]
        result = str(boundary.get("note_result", "Perfect"))
        boundary_upper = (
            latest_presses[0]
            if exact_order
            else float(activation_press)
        )
        boundary_delta = _bounded_judgment_delta_ms(
            note_types,
            int(boundary_index),
            result,
            preferred_delta_ms=_selector_default_delta_ms(
                note_types,
                int(boundary_index),
                result,
                boundary.get("delta_ms"),
            ),
            min_delta_ms=-np.inf,
            max_delta_ms=float(boundary_upper) - float(boundary["hit_time_ms"]),
        )
        boundary["delta_ms"] = float(boundary_delta)
        required_press = float(boundary["hit_time_ms"]) + float(boundary_delta)

    for note_index, latest_note_press in zip(exact_order, latest_presses, strict=True):
        index = int(note_index)
        note = notes[index]
        result = str(note.get("note_result", "Perfect"))
        chosen_delta = _bounded_judgment_delta_ms(
            note_types,
            index,
            result,
            preferred_delta_ms=_selector_default_delta_ms(
                note_types,
                index,
                result,
                note.get("delta_ms"),
            ),
            min_delta_ms=float(required_press) - float(note["hit_time_ms"]),
            max_delta_ms=float(latest_note_press) - float(note["hit_time_ms"]),
        )
        note["delta_ms"] = float(chosen_delta)
        required_press = float(note["hit_time_ms"]) + float(chosen_delta)


def _mark_activation_preemptor_order_deltas(
    notes: list[dict[str, Any]],
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    note_types: Sequence[int] | np.ndarray | None,
    lanes: Sequence[int] | np.ndarray | None = None,
    require_exact_schedule: bool = False,
) -> list[tuple[int, int]]:
    """Delay following notes that would otherwise preempt a delayed activation witness.

    A response surface can legally activate on a late-Great witness only if nearby following notes
    that could be hit first are held until after that activation hit. This pass materializes that
    existing input order locally; it never changes a Perfect/Great label or fever membership.
    """
    n = min(int(total_notes), len(notes))
    if n <= 1:
        return []
    input_order_constraints: list[tuple[int, int]] = []
    if require_exact_schedule and (note_types is None or lanes is None):
        raise ValueError(
            "note_graph: note_types and lanes are required for exact activation schedule replay"
        )
    nt = None if note_types is None else np.asarray(note_types).reshape(-1)
    lane_arr = None if lanes is None else np.asarray(lanes, dtype=np.int32).reshape(-1)
    if require_exact_schedule and (
        nt is None
        or lane_arr is None
        or int(nt.shape[0]) != n
        or int(lane_arr.shape[0]) != n
    ):
        raise ValueError("note_graph: note_types and lanes must match total_notes")
    if lane_arr is not None and not require_exact_schedule:
        n = min(n, int(lane_arr.shape[0]))

    for sec in frontier_trace:
        a = int(sec.get("activation_index", -1))
        if not (0 <= a < n):
            if require_exact_schedule:
                raise ValueError("note_graph: activation schedule has an invalid activation index")
            continue
        activation_delta = notes[a].get("delta_ms")
        if activation_delta is None:
            if require_exact_schedule:
                raise ValueError("note_graph: activation schedule requires a concrete activation hit")
            continue

        activation_press = float(notes[a]["hit_time_ms"]) + float(activation_delta)
        activation_lane = None if lane_arr is None else int(lane_arr[a])
        selected_preactivation: set[int] = set()
        if require_exact_schedule:
            schedule_version = sec.get("activation_schedule_schema_version")
            exact_order_raw = sec.get("preactivation_order")
            if schedule_version != 1 or not isinstance(exact_order_raw, (list, tuple)):
                raise ValueError("note_graph: exact activation schedule schema v1 is required")
            exact_order = tuple(int(index) for index in exact_order_raw)
            if len(exact_order) != int(sec.get("preactivation_event_count", -1)):
                raise ValueError("note_graph: preactivation order length does not match its signature")
            if len(set(exact_order)) != len(exact_order) or any(
                index < 0 or index >= n or index == a for index in exact_order
            ):
                raise ValueError("note_graph: preactivation order contains an invalid note identity")
            section_start = int(sec.get("forced_start_index", -1))
            if not (0 <= int(section_start) <= int(a) < n):
                raise ValueError("note_graph: activation schedule has invalid section bounds")
            great_count = sum(
                1
                for index in exact_order
                if str(notes[int(index)].get("note_result", "Perfect")) == "Great"
            )
            if great_count != int(sec.get("preactivation_great_count", -1)) or (
                2 * len(exact_order) - int(great_count)
                != int(sec.get("preactivation_fill_half_units", -1))
            ):
                raise ValueError("note_graph: preactivation fill signature does not match note labels")
            lane_prefixes_raw = sec.get("preactivation_lane_prefixes")
            if not isinstance(lane_prefixes_raw, (list, tuple)):
                raise ValueError("note_graph: per-lane prefixes are required by activation schedule v1")
            lane_notes: dict[int, list[int]] = {}
            lane_order: list[int] = []
            for index in range(int(section_start), n):
                lane_id = int(lane_arr[int(index)])
                if lane_id not in lane_notes:
                    lane_notes[lane_id] = []
                    lane_order.append(lane_id)
                lane_notes[lane_id].append(int(index))
            if any(not isinstance(row, Mapping) for row in lane_prefixes_raw):
                raise ValueError("note_graph: per-lane prefix rows must be mappings")
            persisted_lane_counts = tuple(
                (int(row["lane"]), int(row["count"])) for row in lane_prefixes_raw
            )
            if tuple(lane for lane, _count in persisted_lane_counts) != tuple(lane_order):
                raise ValueError("note_graph: persisted per-lane prefix identities are not canonical")
            selected_rows: list[int] = []
            for lane_id, prefix_count in persisted_lane_counts:
                rows = lane_notes[int(lane_id)]
                if not (0 <= int(prefix_count) <= len(rows)):
                    raise ValueError("note_graph: persisted per-lane prefix count is out of range")
                if int(lane_id) == int(activation_lane):
                    activation_position = rows.index(int(a))
                    if int(prefix_count) != int(activation_position):
                        raise ValueError(
                            "note_graph: activation-lane prefix must end immediately before activation"
                        )
                selected_rows.extend(rows[: int(prefix_count)])
            selected_preactivation = set(int(index) for index in selected_rows)
            if set(exact_order) != selected_preactivation:
                raise ValueError("note_graph: preactivation order does not match its per-lane prefixes")
            for lane_id, prefix_count in persisted_lane_counts:
                expected_lane_order = tuple(lane_notes[int(lane_id)][: int(prefix_count)])
                actual_lane_order = tuple(
                    index for index in exact_order if int(lane_arr[int(index)]) == int(lane_id)
                )
                if actual_lane_order != expected_lane_order:
                    raise ValueError("note_graph: preactivation order violates lane-local matcher order")
            exact_sequence = (*exact_order, int(a))
            boundary_index = int(section_start) - 1 if int(section_start) > 0 else None
            _materialize_preactivation_schedule(
                notes,
                note_types=nt,
                exact_order=exact_order,
                activation_index=int(a),
                boundary_index=boundary_index,
            )
            if boundary_index is not None:
                input_order_constraints.append(
                    (boundary_index, int(exact_sequence[0]))
                )
            input_order_constraints.extend(
                (int(before), int(after))
                for before, after in zip(exact_sequence, exact_sequence[1:])
            )
        required_press_by_lane: dict[int, float] = {}
        previous_order_index_by_lane: dict[int, int] = {}
        global_required_press = float(activation_press)

        scan_start = int(sec.get("forced_start_index", a + 1)) if require_exact_schedule else a + 1
        for j in range(int(scan_start), n):
            if int(j) == int(a) or int(j) in selected_preactivation:
                continue
            note = notes[j]
            chart_j = float(note["hit_time_ms"])
            lane_key = -1 if lane_arr is None else int(lane_arr[j])
            required_press = float(required_press_by_lane.get(lane_key, activation_press))
            previous_order_index = int(previous_order_index_by_lane.get(lane_key, a))
            # Chart times are monotone and every legal Perfect/Great press lies within 200ms of
            # chart, so once chart_j - 200 clears every lane-local requirement nothing later can
            # press before it. Do NOT stop at the first note whose press already satisfies the
            # requirement: press times are not monotone over chart order once a witness is
            # delayed -- a forced-Great bundle sibling at the activation's own late edge satisfies
            # the requirement while still-on-time chord partners behind it would preempt the
            # activation's fill (the Aurora 47,502,676 witness shape).
            if int(j) > int(a) and chart_j - 200.0 > global_required_press:
                break
            if (
                not require_exact_schedule
                and activation_lane is not None
                and int(lane_arr[j]) != activation_lane
            ):
                continue
            result = str(note.get("note_result", "Perfect"))
            raw_delta = note.get("delta_ms")
            if raw_delta is not None:
                current_delta = float(raw_delta)
            else:
                if nt is None:
                    raise ValueError(
                        "note_graph: note_types (length == total_notes) is required to display "
                        "delayed activation ordering at judgment bounds -- it is never guessed"
                    )
                current_delta = _selector_default_delta_ms(nt, j, result, raw_delta)
            current_press = chart_j + float(current_delta)
            if current_press >= required_press:
                # Already after the activation and the prior note in this lane. It becomes only
                # this lane's ordering floor: cross-lane notes may be pressed in either order.
                required_press_by_lane[lane_key] = float(current_press)
                previous_order_index_by_lane[lane_key] = int(j)
                global_required_press = max(float(global_required_press), float(current_press))
                input_order_constraints.append((int(previous_order_index), int(j)))
                continue

            needed_delta = required_press - chart_j
            if nt is None:
                raise ValueError(
                    "note_graph: note_types (length == total_notes) is required to display "
                    "delayed activation ordering at judgment bounds -- it is never guessed"
                )
            note["delta_ms"] = _delta_at_or_after_ms(nt, j, result, needed_delta)
            required_press_by_lane[lane_key] = chart_j + float(note["delta_ms"])
            previous_order_index_by_lane[lane_key] = int(j)
            global_required_press = max(
                float(global_required_press),
                float(required_press_by_lane[lane_key]),
            )
            input_order_constraints.append((int(previous_order_index), int(j)))

    return input_order_constraints


def _materialize_remaining_selector_deltas(
    notes: list[dict[str, Any]],
    *,
    note_types: Sequence[int] | np.ndarray,
) -> None:
    """Give every remaining Perfect-window selector one canonical physical hit.

    Schedule-sensitive selectors were already moved by the exact order passes. The rows left with
    no delta are order-neutral Great selectors; materialize the first legal late-Great millisecond
    here so every consumer receives the same event stream instead of inventing a frontend default.
    """
    nt = np.asarray(note_types).reshape(-1)
    if int(nt.shape[0]) != len(notes):
        raise ValueError("note_graph: note_types must match the graph before selector materialization")
    for index, note in enumerate(notes):
        if note.get("delta_ms") is not None:
            continue
        result = str(note.get("note_result", "Perfect"))
        if result != "Great":
            raise ValueError(
                f"note_graph: only a Great selector may omit its timing witness (note {index})"
            )
        note["delta_ms"] = float(_selector_default_delta_ms(nt, index, result, None))


def _assign_exact_input_order(
    notes: list[dict[str, Any]],
    constraints: Sequence[tuple[int, int]],
) -> None:
    """Topologically order equal-time inputs while keeping physical time authoritative."""
    n = len(notes)
    event_times: list[float] = []
    for index, note in enumerate(notes):
        delta = note.get("delta_ms")
        if delta is None:
            raise ValueError(f"note_graph: note {index} lacks a canonical input timing")
        event_time = float(note["hit_time_ms"]) + float(delta)
        if not np.isfinite(event_time):
            raise ValueError(f"note_graph: note {index} has a non-finite input timing")
        event_times.append(float(event_time))

    successors: list[set[int]] = [set() for _ in range(n)]
    indegree = [0] * n
    for before_raw, after_raw in constraints:
        before = int(before_raw)
        after = int(after_raw)
        if not (0 <= before < n and 0 <= after < n) or before == after:
            raise ValueError("note_graph: exact input-order constraint has an invalid endpoint")
        if event_times[before] > event_times[after]:
            raise ValueError(
                "note_graph: exact input-order constraint moves backward in physical time "
                f"({before} -> {after})"
            )
        if after not in successors[before]:
            successors[before].add(after)
            indegree[after] += 1

    ready = [
        (float(event_times[index]), int(index))
        for index in range(n)
        if int(indegree[index]) == 0
    ]
    heapq.heapify(ready)
    ordered: list[int] = []
    while ready:
        _event_time, index = heapq.heappop(ready)
        ordered.append(int(index))
        for after in successors[int(index)]:
            indegree[int(after)] -= 1
            if int(indegree[int(after)]) == 0:
                heapq.heappush(ready, (float(event_times[int(after)]), int(after)))
    if len(ordered) != n:
        raise ValueError("note_graph: exact input-order constraints contain a cycle")
    if any(
        event_times[int(after)] < event_times[int(before)]
        for before, after in zip(ordered, ordered[1:])
    ):
        raise ValueError("note_graph: exact input order is not monotone in physical event time")
    for input_order, note_index in enumerate(ordered):
        notes[int(note_index)]["input_order"] = int(input_order)


def _apply_exact_schedule_fever(
    notes: list[dict[str, Any]],
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
) -> None:
    """Materialize fever membership from exact event order and trace-owned durations."""
    activation_rows: list[tuple[int, float]] = []
    seen_activations: set[int] = set()
    for sec in frontier_trace:
        if int(sec.get("activation_schedule_schema_version", 0) or 0) != 1:
            raise ValueError("note_graph: exact schedule fever requires trace schema v1")
        activation = int(sec.get("activation_index", -1))
        if not (0 <= activation < len(notes)) or activation in seen_activations:
            raise ValueError("note_graph: exact schedule fever has an invalid activation identity")
        seen_activations.add(int(activation))
        duration_ms = float(sec.get("fever_duration_ms", float("nan")))
        if not np.isfinite(duration_ms) or duration_ms <= 0.0:
            raise ValueError("note_graph: exact schedule fever duration is missing or invalid")
        activation_rows.append((int(activation), float(duration_ms)))

    ordered_indices = tuple(
        int(index) for index in sorted(range(len(notes)), key=lambda index: int(notes[index]["input_order"]))
    )
    activation_cursor = 0
    active_until_ms: float | None = None
    for note_index in ordered_indices:
        note = notes[int(note_index)]
        event_ms = float(note["hit_time_ms"]) + float(note["delta_ms"])
        if active_until_ms is not None and event_ms >= float(active_until_ms):
            active_until_ms = None
        is_next_activation = bool(
            int(activation_cursor) < len(activation_rows)
            and int(activation_rows[int(activation_cursor)][0]) == int(note_index)
        )
        if is_next_activation:
            if active_until_ms is not None:
                raise ValueError("note_graph: a persisted activation occurs while fever is still active")
            duration_ms = float(activation_rows[int(activation_cursor)][1])
            active_until_ms = float(event_ms) + float(duration_ms)
            activation_cursor += 1
        note["fever"] = bool(active_until_ms is not None)
    if int(activation_cursor) != len(activation_rows):
        raise ValueError("note_graph: exact input order did not consume every persisted activation")


def _mark_endpoint_early_hits(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
    skip_range: tuple[int, int] | None = None,
) -> None:
    """Issue #42 endpoint-early inclusion, shown as the LARGEST-CUSHION legal hit per note.

    A fever note whose chart time is at/after the fever cutoff is in fever ONLY because it is hit
    EARLY (its corrected event time slips before the cutoff). The shown offset is the timing with
    the MOST error margin: the CENTER of the note's legal in-fever hit range, in hit-time space.
    (This center sense of "largest cushion" is DISTINCT from the edge-anchored ``largest_cushion``
    activation_hit_offset_kind elsewhere, which denotes the LATEST legal hit / band edge -- here the
    endpoint note is shown at the range's center, not its edge.)
    For a clawed note with chart time ``hit``:

      * ``legal_low_hit = hit + legal_low``        earliest legal Perfect hit (held-tail-aware
        lower bound: -19 normal, -39 held tail -- the exclusive edge + 1ms, BUG-1)
      * ``upper_hit = nextafter(cutoff, -inf)``    latest float64 hit strictly inside the cutoff
      * ``lo_hit = max(legal_low_hit, prev_hit)``  also >= the previous shown hit (monotonic order)
      * if ``lo_hit >= upper_hit`` (degenerate / no in-fever room): ``shown_hit = lo_hit`` -- the
        legal + monotonic floor; for a valid trace ``lo_hit < cutoff``, so the note still lands in
        fever, within ~1ms of the cutoff.
      * else: ``shown_hit = 0.5 * (lo_hit + upper_hit)`` -- the largest-cushion center.

    ``delta_ms = shown_hit - hit``. This is DISPLAY-ONLY: it changes only the per-note timing
    offset shown, never the fever/great set or any score (the note graph is not on the scoring
    path; ``reconcile_*`` checks fever/great positions + counts, not deltas). The shown hit stays
    LEGAL (``delta >= legal_low``), IN-FEVER (``shown_hit < cutoff``; the center case is
    ``< cutoff``), and MONOTONIC (``>= prev shown hit``, including the degenerate clamp).

    Monotonicity is tracked across ALL notes of the section left-to-right: each note's shown hit is
    ``hit_time_ms + delta_ms`` (treating ``None``/unset delta as 0; the activation witness
    contributes its nominal time + its load-bearing delta). The clawed note's shown hit must be
    ``>= prev_hit``.

    ``note_types`` is REQUIRED runtime song data, but only load-bearing when a note is actually
    clawed in (chart >= cutoff): the lower bound is never guessed. If a clawed-in note is found and
    ``note_types`` is missing or shorter than ``total_notes``, this FAILS LOUD rather than display
    a possibly-false hit. Notes comfortably inside the cutoff keep ``delta_ms = 0``; Great
    selectors (``delta_ms is None``) and the activation witness are left untouched.
    """
    if fever_window_end_ms is None:
        return
    cutoff = float(fever_window_end_ms)
    upper_hit = _strictly_before_cutoff_ms(cutoff)
    nt = None if note_types is None else np.asarray(note_types).reshape(-1)
    prev_hit = -np.inf  # running largest shown hit across the section (monotonic order)
    for j in range(max(0, int(activation_index)), min(int(fever_end_index), int(total_notes))):
        if skip_range is not None and int(skip_range[0]) <= j < int(skip_range[1]):
            # Great-only endpoint notes are handled by the early-Great helper; do not overwrite
            # them with Perfect-only endpoint logic (which would collapse to Perfect-low).
            continue
        note = notes[j]
        delta = note["delta_ms"]
        hit = float(note["hit_time_ms"])
        if delta is None:
            # Great selector: no timing witness; does not move the monotonic frontier.
            continue
        if note["is_activation_witness"] or hit < cutoff:
            # Not re-centered: a score-determining activation witness (left untouched) or a note
            # comfortably inside the cutoff (no claw). Its shown hit advances the monotonic frontier.
            prev_hit = max(prev_hit, hit + float(delta))
            continue
        # Clawed-in note: shown with the largest-cushion legal in-fever hit.
        if nt is None or int(nt.shape[0]) <= j:
            raise ValueError(
                "note_graph: note_types (length == total_notes) is required to display an "
                "endpoint-early hit at the note's legal lower bound -- it is never guessed"
            )
        # +1 after the x2: earliest REACHABLE Perfect hit (exclusive edge + 1ms), matching BUG-1.
        legal_low = _PERFECT_LOWER_MS * (_HELD_TAIL_TIME_MULT if int(nt[j]) == _HELD_TAIL_TYPE else 1) + 1
        legal_low_hit = hit + float(legal_low)
        lo_hit = max(legal_low_hit, prev_hit)
        if lo_hit >= upper_hit:
            shown_hit = lo_hit  # no in-fever room: keep the legal + monotonic floor (>= prev_hit, < cutoff)
        else:
            shown_hit = 0.5 * (lo_hit + upper_hit)  # largest cushion = center of the legal range
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit


def _mark_endpoint_early_great_hits(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
    early_great_range: tuple[int, int] | None,
) -> None:
    """Issue #68: early-Great fever extension tail, shown in the Great-only band."""
    if fever_window_end_ms is None:
        return
    if early_great_range is None:
        return
    start, end = (int(early_great_range[0]), int(early_great_range[1]))
    if end <= start:
        return
    if note_types is None:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display early-Great "
            "fever-end timing at judgment bounds -- it is never guessed"
        )

    cutoff = float(fever_window_end_ms)
    strict_cutoff = _strictly_before_cutoff_ms(cutoff)
    nt = np.asarray(note_types).reshape(-1)
    prev_hit = -np.inf

    # Reconstruct the monotonic frontier up to the early-Great start from already-set deltas.
    for j in range(max(0, int(activation_index)), min(end, int(total_notes))):
        note = notes[j]
        hit = float(note["hit_time_ms"])
        delta = note.get("delta_ms")
        if j < start:
            if delta is not None:
                prev_hit = max(prev_hit, hit + float(delta))
            continue

        if not bool(note.get("fever")):
            continue
        if note.get("is_activation_witness"):
            continue

        great_low, great_high = _early_great_bounds_ms_at(nt, j)
        fever_high = strict_cutoff - hit
        safe_low = float(great_low)
        safe_high = min(float(great_high), float(fever_high))
        if safe_low > safe_high:
            raise ValueError(
                f"note_graph: early-Great fever-end note {j} has empty safe interval "
                f"[{safe_low}, {safe_high}] ms"
            )

        lo_hit = max(hit + safe_low, prev_hit)
        hi_hit = hit + safe_high
        if lo_hit > hi_hit:
            raise ValueError(
                f"note_graph: early-Great fever-end note {j} has empty safe interval after "
                f"monotonic/cutoff constraints (lo_hit={lo_hit}, hi_hit={hi_hit})"
            )

        shown_hit = 0.5 * (lo_hit + hi_hit)
        note["note_result"] = "Great"
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit

    return


def _mark_fever_end_witness(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    section: int,
) -> None:
    """Mark the last note of the fever run as the fever-end witness.

    Anchors where fever ends with the largest-cushion cutoff (``fever_window_end_ms``) -- the
    same latest-legal convention the activation witness uses for where fever starts. Shared by
    the base and FG note graphs so the two stay symmetric. ``last_fever`` is ``min(e, n) - 1``,
    always ``< n``, so only the lower bound is checked.
    """
    last_fever = min(int(fever_end_index), int(total_notes)) - 1
    if int(activation_index) <= last_fever:
        notes[last_fever]["is_fever_end_witness"] = True
        if fever_window_end_ms is not None:
            notes[last_fever]["fever_end_ms"] = float(fever_window_end_ms)
        notes[last_fever]["section"] = int(section)


def _mark_fever_end_cluster_safe_delta(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
) -> None:
    """Fever-end cluster: judgment-safe ∩ in-fever display delta (issue #64).

    ``fever_window_end_ms`` is a continuous fever **cutoff**, not a playable hit target.
    A guidance ``delta_ms`` must stay inside the note's required judgment window (Perfect
    first) **and** land before the cutoff (``hit + delta < cutoff``).

    For each same-chart-time fever cluster at the section tail:

      * ``judgment_safe = [perfect_lower, perfect_upper]`` (held-tail-aware)
      * ``fever_safe_upper = nextafter(cutoff, -inf) - hit``
      * ``safe = judgment_safe ∩ (-inf, fever_safe_upper]``
      * ``cluster_safe = intersection of every cluster note's safe interval``

    Display only when the cutoff **constrains** the upper bound below Perfect upper
    (comfortable ends keep ``delta_ms = 0``). Otherwise ``+560 ms``-style values are
    impossible. Great-interval fever-end guidance is not implemented; a tight cutoff
    with a non-Perfect same-chart-time cluster **fails loud** rather than silently
    leaving ``0 ms``.

    Display-only; fever/great sets and scores are unchanged.
    """
    if fever_window_end_ms is None:
        return
    cutoff = float(fever_window_end_ms)
    a = int(activation_index)
    last_fever = min(int(fever_end_index), int(total_notes)) - 1
    if last_fever < a:
        return
    witness = notes[last_fever]
    if not witness.get("is_fever_end_witness"):
        return
    if witness.get("is_activation_witness"):
        return
    hit = float(witness["hit_time_ms"])
    if hit >= cutoff:
        return
    strict_cutoff = _strictly_before_cutoff_ms(cutoff)
    fever_upper_witness = strict_cutoff - hit
    if fever_upper_witness >= _PERFECT_UPPER_MS:
        return
    witness_result = str(witness.get("note_result", "Perfect"))
    if witness_result != "Perfect":
        raise ValueError(
            "note_graph: unsupported fever-end guidance at tight cutoff: "
            f"witness note {last_fever} is {witness_result!r}, not Perfect"
        )
    if note_types is None:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "fever-end cluster timing at judgment bounds -- it is never guessed"
        )
    nt = np.asarray(note_types).reshape(-1)

    cluster: list[int] = []
    for j in range(max(0, a), last_fever + 1):
        note = notes[j]
        if not note.get("fever"):
            continue
        if note.get("is_activation_witness"):
            continue
        if not _same_chart_time_ms(note["hit_time_ms"], hit):
            continue
        note_result = str(note.get("note_result", "Perfect"))
        if note.get("delta_ms") is None or note_result != "Perfect":
            raise ValueError(
                "note_graph: unsupported fever-end guidance at tight cutoff: "
                f"same-chart-time cluster note {j} is {note_result!r} "
                "(Perfect-only guidance not implemented)"
            )
        cluster.append(j)
    if not cluster:
        return

    cluster_lo = -np.inf
    cluster_hi = np.inf
    min_judgment_hi = np.inf
    for j in cluster:
        j_lo, j_hi = _perfect_bounds_ms_at(nt, j)
        min_judgment_hi = min(min_judgment_hi, j_hi)
        fever_upper_delta = strict_cutoff - float(notes[j]["hit_time_ms"])
        safe_hi = min(j_hi, fever_upper_delta)
        safe_lo = j_lo
        if safe_lo > safe_hi:
            raise ValueError(
                f"note_graph: fever-end cluster note {j} has empty safe interval "
                f"[{safe_lo}, {safe_hi}] ms"
            )
        cluster_lo = max(cluster_lo, safe_lo)
        cluster_hi = min(cluster_hi, safe_hi)

    if cluster_lo > cluster_hi:
        raise ValueError(
            "note_graph: fever-end cluster has empty shared safe interval after intersection"
        )
    if cluster_hi >= float(min_judgment_hi):
        return

    display_delta = _center_safe_delta(low_ms=cluster_lo, high_ms=cluster_hi)
    for j in cluster:
        notes[j]["delta_ms"] = display_delta


def _mark_fever_exit_push_delta(
    notes: list[dict[str, Any]],
    *,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
) -> None:
    """Push the first-excluded note(s) at a fever-end boundary LATE so the replay drain excludes them.

    The MIRROR of the claw-IN-early endpoint logic. ``_mark_endpoint_early_hits`` /
    ``_mark_fever_end_cluster_safe_delta`` pull late fever notes EARLY to keep them inside the
    cutoff; this pushes the FIRST NON-FEVER note (``fever_end_index``) LATE to keep it OUT.

    Why it is needed: the served surface excludes note ``e`` -- the frontier proved that exclusion
    using the note's LATEST legal Perfect hit (``group_high``) landing at/after the cutoff
    (``timeline_exact_frontier._exit_intervals_jit``). But the note is serialized at ``delta_ms = 0``
    (chart time), and the replay RE-DERIVES fever from the shipped hit times. If the note's chart
    time is still before the cutoff, the replay's drain reclaims it into fever, so the replayed fever
    set no longer matches the served surface and the replay score diverges from the card
    (``delta != 0``; e.g. Raining Tacos (Easy) T1: card 2,833,029 vs replay 2,831,430). Shipping the
    note at its latest legal Perfect hit -- the same ``group_high`` the frontier's exclusion assumed
    -- restores ``hit >= cutoff`` so the drain excludes it exactly as the surface does.

    Display/replay-only: the scored surface and the card score are unchanged; this only makes the
    replay reproduce them. Acts only on a plain Perfect note actually reclaimed at chart time
    (``chart < cutoff``); a note already past the cutoff, a Great selector, an activation witness, or
    an already-fever note is left untouched. It pushes to the note's LATEST legal Perfect hit -- the
    same ``group_high`` the frontier's exclusion assumed, so it is the best legal effort and can only
    move the note further out (never worse than the current ``d = 0``). It does NOT fail loud on the
    frontier's ``fever_window_end_ms``: that cutoff is a floored-integer-derived float, so a note's
    float latest hit can sit a sub-ms below it yet still land past the REPLAY's own (lower) fever end
    -- as Raining Tacos note 85 does (latest 41388.999ms vs cutoff 41389.000ms, replay-excluded). The
    authoritative reproducibility gate is the delta=0 replay sweep, not a serializer inequality that
    cannot see the replay's exact drain.
    """
    if fever_window_end_ms is None:
        return
    cutoff = float(fever_window_end_ms)
    n = int(total_notes)
    nt: np.ndarray | None = None
    j = int(fever_end_index)
    while 0 <= j < n:
        note = notes[j]
        hit = float(note["hit_time_ms"])
        if hit >= cutoff:
            break  # already excluded at chart time; every later note is later still -> done
        # Only a plain Perfect exit note is pushed. A Great selector (delta_ms None), an activation
        # witness, or an already-fever note is owned by other logic and left untouched.
        if note.get("is_activation_witness") or note.get("fever"):
            break
        if note.get("delta_ms") is None or str(note.get("note_result", "Perfect")) != "Perfect":
            break
        if nt is None:
            if note_types is None:
                raise ValueError(
                    "note_graph: note_types (length == total_notes) is required to push a fever-exit "
                    "note past the cutoff at its held-tail-aware Perfect bound -- it is never guessed"
                )
            nt = np.asarray(note_types).reshape(-1)
        _perfect_lo, perfect_hi = _perfect_bounds_ms_at(nt, j)
        note["delta_ms"] = float(perfect_hi)  # latest legal Perfect hit: largest cushion OUT
        j += 1


def timeline_frontier_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """BASE note-graph from the selected timeline-frontier witness trace.

    ``note_types`` is runtime song data (like ``timestamps``) needed to show a clawed-in
    endpoint-early note's held-tail-aware LEGAL early hit; it is required (fails loud) only when a
    note is actually clawed in -- never guessed.
    """

    n = int(total_notes)
    apply_guidance = _normalize_timing_mode(timing_mode) == "perfect_window"
    notes = _perfect_note_graph(n, timestamps)
    for sec in frontier_trace:
        section = int(sec.get("section", 0))
        a = int(sec["activation_index"])
        e = int(sec["fever_end_index"])
        w = int(sec["fever_start_note_index"])
        for j in range(max(0, a), min(e, n)):
            notes[j]["fever"] = True
            if notes[j]["section"] == 0:
                notes[j]["section"] = section
        if w != a and 0 <= w < n:
            # The activating hit is physically delivered by an earlier
            # wider-window note (chorded held tail): fever starts at ITS hit, so
            # the count-boundary note (hit before the activation clock) is outside
            # fever and the witness note is inside. Same fever count -> the scored
            # surface is unchanged; the graph stays replay-consistent per note.
            notes[w]["fever"] = True
            if notes[w]["section"] == 0:
                notes[w]["section"] = section
            if 0 <= a < n:
                notes[a]["fever"] = False
        if apply_guidance and 0 <= w < n:
            notes[w]["delta_ms"] = float(sec["activation_hit_offset_ms"])
            notes[w]["is_activation_witness"] = True
            notes[w]["section"] = section
        # The last note of the fever run is the fever-end witness (largest-cushion cutoff);
        # any fever note at/after that cutoff is shown with its LARGEST-CUSHION legal early hit --
        # the center of its legal in-fever range, the timing with the most error margin (issue #42).
        # Display-only: the per-note timing keeps the scored fever set unchanged.
        fever_end_ms = sec.get("fever_window_end_ms")
        _mark_fever_end_witness(
            notes, activation_index=a, fever_end_index=e, total_notes=n,
            fever_window_end_ms=fever_end_ms, section=section,
        )
        if apply_guidance:
            # Endpoint guidance must see the PHYSICAL fever start: when the
            # witness precedes the count boundary (chorded held tail), the
            # monotonic display frontier starts at the witness so no clawed-in
            # endpoint hit is ever shown before the activating hit.
            guidance_start = min(a, w)
            _mark_endpoint_early_hits(
                notes, activation_index=guidance_start, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )
            _mark_fever_end_cluster_safe_delta(
                notes, activation_index=guidance_start, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )
            # Mirror of the claw-in: push the first NON-fever note past the cutoff so the replay's
            # drain excludes it exactly as the served surface does (keeps replay == card).
            _mark_fever_exit_push_delta(
                notes, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )

    if apply_guidance:
        # The base frontier prices a delayed activation clock, but the replay wire is a stream of
        # physical inputs sorted by ``chart time + delta``. Materialize the already-priced order:
        # every following input that would otherwise land before the activation must be delayed to
        # the activation clock. Without this pass, a same-time chord sibling left at 0ms can fill
        # the bar first in game even though the frontier scored the activation witness at +40ms.
        # FG has always applied this same canonical materialization below.
        _mark_activation_preemptor_order_deltas(
            notes,
            frontier_trace=frontier_trace,
            total_notes=n,
            note_types=note_types,
        )

    return notes


def base_note_graph(
    *,
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    is_fever_mask: Sequence[bool] | np.ndarray,
    frontier_trace: Sequence[Mapping[str, Any]] | None = None,
    note_types: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """BASE note-graph (timeline frontier): every note Perfect, with fever windows.

    The mask path (no ``frontier_trace``) needs no ``note_types`` (no endpoint-early offsets); the
    trace path delegates to ``timeline_frontier_note_graph``, which REQUIRES ``note_types`` and
    fails loud if it is absent -- the held-tail-aware lower bound is never guessed.

    `is_fever_mask` is the full per-note fever mask produced deterministically by
    `gear_optimizer.solver.fever_timeline.calculate_fever_timeline_indices` from the
    loadout's persisted Fever Fill Rate / Fever Time stats + the song notes (its
    `fever_mask_buffer` argument is written for ALL notes, not just the head slice).
    """
    if frontier_trace is not None:
        return timeline_frontier_note_graph(
            frontier_trace=frontier_trace,
            total_notes=int(total_notes),
            timestamps=timestamps,
            note_types=note_types,
            timing_mode=timing_mode,
        )
    n = int(total_notes)
    fev = np.asarray(is_fever_mask).reshape(-1)
    if int(fev.shape[0]) < n:
        raise ValueError("base_note_graph: timestamps/is_fever_mask shorter than total_notes")
    notes = _perfect_note_graph(n, timestamps)
    for i in range(n):
        notes[i]["fever"] = bool(fev[int(i)])
    return notes


def force_greats_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray | None = None,
    lanes: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """FG note-graph (fg frontier + timeline frontier) from the persisted witness trace.

    ``note_types`` is runtime song data (like ``timestamps``) needed to show a clawed-in
    endpoint-early note's held-tail-aware LEGAL early hit; required (fails loud) only when a note
    is actually clawed in -- never guessed.

    `frontier_trace` is the per-loadout `ForceGreats.frontier_trace` (list of section
    dicts emitted by `reconstruct_force_greats_response_trace`). Each section carries a
    sequential, non-overlapping region of the timeline:
      - fever window  [activation_index, fever_end_index)            -> fever
      - forced greats [forced_run_start_index, forced_run_start_index+forced_run_count) -> Great (selector)
        (older prefix-only traces map this to forced_start_index/forced_prefix_count)
      - the activation note is a timing WITNESS when activation_hit_offset_ms is nonzero.
        If activation_judgment == "late_great", that witness is also a Great; otherwise
        it remains Perfect.
    All other notes are Perfect (delta 0). A note may be both fever and Great.
    """
    n = int(total_notes)
    apply_guidance = _normalize_timing_mode(timing_mode) == "perfect_window"
    if apply_guidance:
        if note_types is None or lanes is None:
            raise ValueError(
                "note_graph: perfect-window FG replay requires chart note_types and lanes"
            )
        if int(np.asarray(note_types).reshape(-1).shape[0]) != n or int(
            np.asarray(lanes).reshape(-1).shape[0]
        ) != n:
            raise ValueError("note_graph: note_types and lanes must match total_notes")
    notes = _perfect_note_graph(n, timestamps)

    for sec in frontier_trace:
        section = int(sec.get("section", 0))
        a = int(sec["activation_index"])
        e = int(sec["fever_end_index"])
        fs = int(sec.get("forced_run_start_index", sec["forced_start_index"]))
        fc = int(sec.get("forced_run_count", sec["forced_prefix_count"]))

        for j in range(max(0, fs), min(fs + fc, n)):     # forced (selector) Greats
            notes[j]["note_result"] = "Great"
            notes[j]["delta_ms"] = None                   # selectors have NO timing witness (v3)
            if notes[j]["section"] == 0:
                notes[j]["section"] = section

        for j in range(max(0, a), min(e, n)):             # fever window
            notes[j]["fever"] = True
            if notes[j]["section"] == 0:
                notes[j]["section"] = section

        # Fever-end witness: last note of the fever run, carrying the largest-cushion
        # cutoff (`fever_window_end_ms`). Symmetric to the base note-graph.
        fever_end_ms = sec.get("fever_window_end_ms")
        materialized_activation_delta_ms: float | None = None

        if apply_guidance:
            activation_judgment = str(sec.get("activation_judgment", ""))
            if activation_judgment == "late_great" and 0 <= a < n:
                notes[a]["note_result"] = "Great"             # activation Late Great = the WITNESS
                materialized_activation_delta_ms = _activation_materialized_delta_ms(
                    sec,
                    notes=notes,
                    total_notes=n,
                    note_types=note_types,
                    lanes=lanes,
                    note_index=a,
                    judgment=activation_judgment,
                )
                notes[a]["delta_ms"] = float(materialized_activation_delta_ms)
                notes[a]["is_activation_witness"] = True
                notes[a]["section"] = section
            elif (
                activation_judgment == "perfect"
                and 0 <= a < n
                and float(sec.get("activation_hit_offset_ms", 0.0) or 0.0) != 0.0
            ):
                materialized_activation_delta_ms = _activation_materialized_delta_ms(
                    sec,
                    notes=notes,
                    total_notes=n,
                    note_types=note_types,
                    lanes=lanes,
                    note_index=a,
                    judgment=activation_judgment,
                )
                notes[a]["delta_ms"] = float(materialized_activation_delta_ms)
                notes[a]["is_activation_witness"] = True
                notes[a]["section"] = section

            fever_end_ms = _materialized_fever_window_end_ms(
                sec,
                activation_delta_ms=materialized_activation_delta_ms,
                activation_chart_ms=float(notes[a]["hit_time_ms"]) if 0 <= a < n else None,
            )

        _mark_fever_end_witness(
            notes, activation_index=a, fever_end_index=e, total_notes=n,
            fever_window_end_ms=fever_end_ms, section=section,
        )

        if apply_guidance:
            # Endpoint-early (issue #42): any Perfect fever note at/after the cutoff is shown with its
            # LARGEST-CUSHION legal early hit -- the center of its legal in-fever range (most error
            # margin), display-only so the scored fever set is unchanged. Great selectors (delta_ms
            # None) are skipped.
            early_great_start = int(sec.get("early_great_start", -1))
            early_great_end = int(sec.get("early_great_end", -1))
            early_great_range = None
            if early_great_start >= 0 and early_great_end >= 0:
                start = max(int(a), int(early_great_start), 0)
                end = min(int(early_great_end), int(e), int(n))
                if end > start:
                    early_great_range = (start, end)
            _mark_endpoint_early_hits(
                notes,
                activation_index=a,
                fever_end_index=e,
                total_notes=n,
                fever_window_end_ms=fever_end_ms,
                note_types=note_types,
                skip_range=early_great_range,
            )
            _mark_endpoint_early_great_hits(
                notes,
                activation_index=a,
                fever_end_index=e,
                total_notes=n,
                fever_window_end_ms=fever_end_ms,
                note_types=note_types,
                early_great_range=early_great_range,
            )
            _mark_fever_end_cluster_safe_delta(
                notes, activation_index=a, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )
            # Mirror of the claw-in: push the first NON-fever note past the cutoff so the replay's
            # drain excludes it exactly as the served surface does (keeps replay == card).
            _mark_fever_exit_push_delta(
                notes, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )

    if apply_guidance:
        _mark_same_time_selector_order_deltas(
            notes,
            total_notes=n,
            note_types=note_types,
        )
        input_order_constraints = _mark_activation_preemptor_order_deltas(
            notes,
            frontier_trace=frontier_trace,
            total_notes=n,
            note_types=note_types,
            lanes=lanes,
            require_exact_schedule=True,
        )
        _materialize_remaining_selector_deltas(notes, note_types=note_types)
        _assign_exact_input_order(notes, input_order_constraints)
        _apply_exact_schedule_fever(notes, frontier_trace=frontier_trace)

    return notes


def _head_set_from_words(words: Sequence[int], head_limit: int) -> set[int]:
    """Return the set of note indices in [0, head_limit) set in a 4x32-bit head mask."""
    w = tuple(int(x) for x in tuple(words)[:4]) + (0,) * max(0, 4 - len(words))
    idxs: set[int] = set()
    for i in range(int(head_limit)):
        if (int(w[i // 32]) >> (i % 32)) & 1:
            idxs.add(i)
    return idxs


def reconcile_force_greats_note_graph(
    note_graph: Sequence[Mapping[str, Any]],
    *,
    total_notes: int,
    fever_words: Sequence[int],
    great_words: Sequence[int],
    body_fever: int,
    body_great: int,
    body_fever_great: int,
) -> None:
    """Fail-loud proof that the FG note-graph reconciles EXACTLY with the chosen surface.

    Head notes (0..min(n,100)) must match the surface's fever/great bitmasks bit-for-bit;
    body notes (>=100) must match the surface's fever/great/fever_great counts. This is
    the sufficiency guarantee: the persisted trace + surface fully determine the graph.
    Raises ValueError on any mismatch.
    """
    n = int(total_notes)
    head_limit = min(n, 100)

    g_fever_idx = {int(x["note_index"]) for x in note_graph if bool(x["fever"])}
    g_great_idx = {int(x["note_index"]) for x in note_graph if str(x["note_result"]) == "Great"}

    surf_fever_head_idx = _head_set_from_words(fever_words, head_limit)
    surf_great_head_idx = _head_set_from_words(great_words, head_limit)

    g_fever_head = {i for i in g_fever_idx if i < head_limit}
    g_great_head = {i for i in g_great_idx if i < head_limit}
    if g_fever_head != surf_fever_head_idx:
        raise ValueError(f"FG note-graph head fever positions != surface mask: {g_fever_head ^ surf_fever_head_idx}")
    if g_great_head != surf_great_head_idx:
        raise ValueError(f"FG note-graph head great positions != surface mask: {g_great_head ^ surf_great_head_idx}")

    g_body_fever = sum(1 for i in g_fever_idx if i >= 100)
    g_body_great = sum(1 for i in g_great_idx if i >= 100)
    g_body_fg = sum(1 for i in (g_fever_idx & g_great_idx) if i >= 100)
    if g_body_fever != int(body_fever):
        raise ValueError(f"FG note-graph body_fever {g_body_fever} != surface {int(body_fever)}")
    if g_body_great != int(body_great):
        raise ValueError(f"FG note-graph body_great {g_body_great} != surface {int(body_great)}")
    if g_body_fg != int(body_fever_great):
        raise ValueError(f"FG note-graph body_fever_great {g_body_fg} != surface {int(body_fever_great)}")
