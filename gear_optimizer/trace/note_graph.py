"""A stored build's note plan: per note, what the timing graph draws and the replay plays.

Each note of a graph is a dict: note_index, hit_time_ms (its chart time), note_result ("Perfect" or "Great"), delta_ms
(its planned hit offset, + late), input_order (its place in the input stream), fever, is_activation_witness,
is_fever_end_witness, fever_end_ms (the fever cutoff, on a section's last fever note) and section.

Two graphs per loadout, rebuilt from the persisted frontier trace, so nothing per note is stored:
  * timeline_frontier_note_graph, Base: every note Perfect, each activation at its witnessed hit.
  * force_greats_note_graph, Force Greats: per-note Perfect or Great. A forced Great is a selector without a timing of its
    own until the passes below give it one; a late-Great or offset Perfect activation is hit inside the interval
    the producer proved keeps its surface.
base_note_graph draws a fever mask with every hit on its chart time, for a Base row that has no trace.

The timing mode decides the hits:
  * "precise": activation witnesses, endpoint hits that keep a section's last notes inside its fever cutoff and its
    first note past it outside, and every other hit no later than its band's frame-safe offset when that keeps its input
    order and fever (_plan_frame_safe_hits).
  * "non-precise": Perfects stay on time. Leading Greats in a tie are early to precede its first Perfect, at the latest
    offset every frame timing still judges an early Great; other Greats use their canonical late hit, or that early
    offset when the late hit would come within a frame margin of an input that must follow it
    (_plan_blocked_late_greats_early).

A plan uses the hit windows of the build's Perfect Time; the frontier behind it used the base ones. A surface no hit plays
at the build's windows raises UnplayableTrace.
"""

from __future__ import annotations

import math
from bisect import insort
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np

from gear_optimizer.core.time_quantize import snap_near_int_ms
from gear_optimizer.trace.reconstruct import UnplayableTrace
from gear_optimizer.solver.timing_envelope import (
    FRAME_MARGIN_MS,
    HELD_TAIL_TYPE,
    HELD_TAIL_WINDOW_SCALE,
    TIMING_MODES,
    judgment_bounds,
)

__all__ = [
    "base_note_graph",
    "timeline_frontier_note_graph",
    "force_greats_note_graph",
    "reconcile_base_note_graph",
    "reconcile_force_greats_note_graph",
]

_FEVER_END_SAME_CHART_TIME_MS = 0.01
# The combo ramp: the score surface keeps the judgment and fever of each of these first notes.
_HEAD_NOTES = 100
# Wider than any planned hit offset (a held tail's late Great ends at the 200 ms note removal): notes further apart in
# chart time never swap inputs.
_PLANNED_OFFSET_SPAN_MS = 200.0
# Every legal Perfect or Great press lies within this of its chart time.
_LATEST_PRESS_MS = 200.0


class _Section(NamedTuple):
    """The fields of a stored trace section that a plan reads."""

    number: int
    activation: int
    fever_end: int
    judgment: str  # how the activation note is hit: "perfect" or "late_great"
    hit_offset_ms: float
    window_lower_ms: float  # the activation hits that keep the section's surface
    window_upper_ms: float
    cutoff_ms: float
    fever_duration_ms: float
    forced_start: int  # the section's first note
    forced_run_start: int
    forced_run_count: int
    early_great_start: int
    early_great_end: int
    preactivation_order: tuple[int, ...]  # the notes planned before the activation, in input order


def _sections(frontier_trace: Sequence[Mapping[str, Any]]) -> list[_Section]:
    return [
        _Section(
            number=row["section"],
            activation=row["activation_index"],
            fever_end=row["fever_end_index"],
            judgment=row["activation_judgment"],
            hit_offset_ms=row["activation_hit_offset_ms"],
            window_lower_ms=row["activation_hit_window_lower_ms"],
            window_upper_ms=row["activation_hit_window_upper_ms"],
            cutoff_ms=row["fever_window_end_ms"],
            fever_duration_ms=row["fever_duration_ms"],
            forced_start=row["forced_start_index"],
            forced_run_start=row["forced_run_start_index"],
            forced_run_count=row["forced_run_count"],
            early_great_start=row["early_great_start"],
            early_great_end=row["early_great_end"],
            preactivation_order=tuple(row["preactivation_order"]),
        )
        for row in frontier_trace
    ]


class _Bands(NamedTuple):
    """A note's reachable planned offsets (lowest, highest) per judgment."""

    perfect: tuple[float, float]
    early_great: tuple[float, float]
    late_great: tuple[float, float]


@lru_cache(maxsize=None)
def _tap_and_tail_bands(perfect_time: int) -> tuple[_Bands, _Bands]:
    return tuple(
        _Bands(*((float(band.earliest), float(band.latest)) for band in judgment_bounds(scale, perfect_time)))
        for scale in (1, HELD_TAIL_WINDOW_SCALE)
    )


@dataclass(slots=True)
class _Plan:
    """A graph being built: its notes, each note's bands at the build's Perfect Time, and the chart."""

    notes: list[dict[str, Any]]
    bands: list[_Bands]
    is_tail: list[bool]
    lanes: list[int]
    precise: bool
    tap_latest_perfect: float

    def __len__(self) -> int:
        return len(self.notes)


def _perfect_notes(total_notes: int, timestamps: Sequence[float] | np.ndarray) -> list[dict[str, Any]]:
    return [
        {
            "note_index": index,
            "hit_time_ms": seconds * 1000.0,
            "note_result": "Perfect",
            "delta_ms": 0.0,
            "input_order": index,
            "fever": False,
            "is_activation_witness": False,
            "is_fever_end_witness": False,
            "fever_end_ms": None,
            "section": 0,
        }
        for index, seconds in enumerate(np.asarray(timestamps, dtype=np.float64).reshape(-1)[:total_notes].tolist())
    ]


def _new_plan(
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> _Plan:
    if timing_mode not in TIMING_MODES:
        raise ValueError(f"note_graph: unknown timing_mode {timing_mode!r}")
    notes = _perfect_notes(total_notes, timestamps)
    is_tail = (np.asarray(note_types).reshape(-1) == HELD_TAIL_TYPE).tolist()
    lane_ids = np.asarray(lanes).reshape(-1).tolist()
    if not len(notes) == len(is_tail) == len(lane_ids) == total_notes:
        raise ValueError("note_graph: timestamps, note_types and lanes must match total_notes")
    tap, tail = _tap_and_tail_bands(perfect_time)
    return _Plan(
        notes=notes,
        bands=[tail if held else tap for held in is_tail],
        is_tail=is_tail,
        lanes=lane_ids,
        precise=timing_mode != "non-precise",
        tap_latest_perfect=tap.perfect[1],
    )


def _frame_safe_latest_ms(latest_ms: float) -> float:
    """The latest planned offset every frame timing still judges at or before `latest_ms`: the game judges a press up
    to one frame margin after it is planned (any rate >= 60 fps)."""
    return float(math.floor(latest_ms - FRAME_MARGIN_MS))


def _guaranteed_early_great_ms(plan: _Plan, j: int) -> float:
    """The latest planned offset every frame timing judges an early Great."""
    return _frame_safe_latest_ms(plan.bands[j].early_great[1])


def _default_delta_ms(plan: _Plan, j: int, result: str, delta: float | None) -> float:
    """A hit's planned offset: its own, or on time for a Perfect and the first late-Great offset for a selector."""
    if delta is not None:
        return delta
    return 0.0 if result == "Perfect" else plan.bands[j].late_great[0]


def _strictly_before(cutoff_ms: float) -> float:
    """The greatest float64 event time strictly before a cutoff."""
    return math.nextafter(cutoff_ms, -math.inf)


def _center(low_ms: float, high_ms: float) -> float:
    return 0.5 * (low_ms + high_ms)


def _same_chart_time(a: float, b: float) -> bool:
    return abs(a - b) <= _FEVER_END_SAME_CHART_TIME_MS


def _snap_engine_time_ms(value: float) -> float:
    return float(snap_near_int_ms(np.asarray(value, dtype=np.float64)))


def _bounded_delta_ms(
    plan: _Plan,
    j: int,
    result: str,
    *,
    preferred_ms: float,
    min_delta_ms: float = -math.inf,
    max_delta_ms: float = math.inf,
) -> float:
    """The offset nearest `preferred_ms` that keeps note j's `result` inside [min_delta_ms, max_delta_ms]."""
    bands = plan.bands[j]
    candidates: list[float] = []
    for lo, hi in (bands.perfect,) if result == "Perfect" else (bands.early_great, bands.late_great):
        feasible_lo, feasible_hi = max(lo, min_delta_ms), min(hi, max_delta_ms)
        if feasible_lo <= feasible_hi:
            candidates.append(min(max(preferred_ms, feasible_lo), feasible_hi))
    if not candidates:
        raise UnplayableTrace(f"note_graph: exact input order has no legal bounded hit for note {j}'s {result} judgment")
    if preferred_ms == math.inf:
        return max(candidates)
    if preferred_ms == -math.inf:
        return min(candidates)
    return min(candidates, key=lambda delta: (abs(delta - preferred_ms), delta))


def _delta_at_or_after_ms(plan: _Plan, j: int, result: str, min_delta_ms: float) -> float:
    return _bounded_delta_ms(plan, j, result, preferred_ms=min_delta_ms, min_delta_ms=min_delta_ms)


def _delta_at_or_before_ms(plan: _Plan, j: int, result: str, max_delta_ms: float) -> float:
    return _bounded_delta_ms(plan, j, result, preferred_ms=max_delta_ms, max_delta_ms=max_delta_ms)


def _activation_delta_ms(plan: _Plan, sec: _Section) -> float:
    """The max-margin hit of a late-Great or offset Perfect activation that keeps the scored input order."""
    notes, bands, a = plan.notes, plan.bands, sec.activation
    judge_lo, judge_hi = bands[a].late_great if sec.judgment == "late_great" else bands[a].perfect
    chart_ms = notes[a]["hit_time_ms"]
    window_lo, window_hi = sec.window_lower_ms - chart_ms, sec.window_upper_ms - chart_ms
    lo, hi = max(judge_lo, window_lo), min(judge_hi, window_hi)
    if lo > hi:
        if window_lo > judge_hi and _snap_engine_time_ms(window_lo) == judge_hi:
            lo = hi = judge_hi
        elif window_hi < judge_lo and _snap_engine_time_ms(window_hi) == judge_lo:
            lo = hi = judge_lo
        else:
            raise UnplayableTrace(f"note_graph: activation witness interval is empty at note {a} ({lo:.3f}ms > {hi:.3f}ms)")

    # Early-Great endpoint rows sit before the ordinary Perfect-floor exit, so the producer's exit band does not include
    # their strict event < fever_end constraint: raise the activation's lower bound just enough that each keeps a legal
    # hit inside fever.
    if sec.early_great_start >= 0 and sec.early_great_end > sec.early_great_start:
        for j in range(max(0, sec.early_great_start), min(sec.early_great_end, len(plan))):
            earliest_hit_ms = notes[j]["hit_time_ms"] + bands[j].early_great[0]
            lo = max(lo, math.nextafter(earliest_hit_ms - sec.fever_duration_ms, math.inf) - chart_ms)
        if lo > hi:
            raise UnplayableTrace(
                f"note_graph: activation witness has no score-parity room for an early-Great fever-end note at "
                f"activation {a} ({lo:.3f}ms > {hi:.3f}ms)"
            )

    # A following note that the schedule does not plan before the activation caps it at that note's latest legal hit.
    # Equal event times are legal: the activation -> follower constraint orders them.
    hit_lo_ms, hit_ms = chart_ms + lo, chart_ms + hi
    planned_first = frozenset(sec.preactivation_order)
    for j in range(a + 1, len(plan)):
        if j in planned_first:
            continue
        note = notes[j]
        if note["hit_time_ms"] >= hit_ms:
            break
        latest = bands[j].perfect[1] if note["note_result"] == "Perfect" else bands[j].late_great[1]
        hit_ms = min(hit_ms, note["hit_time_ms"] + latest)
        if hit_ms < hit_lo_ms:
            raise UnplayableTrace(
                f"note_graph: activation witness cannot preserve following note order without changing note {a}'s "
                f"{sec.judgment} judgment"
            )
    feasible_hi = min(hi, hit_ms - chart_ms)
    if feasible_hi < lo:
        raise UnplayableTrace(
            f"note_graph: activation witness cannot preserve following note order without changing note {a}'s "
            f"{sec.judgment} judgment"
        )
    # The midpoint maximizes the input error the hit tolerates in both directions.
    return _center(lo, feasible_hi)


def _mark_same_time_selector_deltas(plan: _Plan) -> None:
    """Keep selector order inside score-bearing ties: chart order through the combo ramp (non-precise: the whole
    chart, where only the Greats leading a tie can go early, the Perfects staying on time)."""
    notes, graph_n = plan.notes, len(plan)
    if graph_n <= 1:
        return
    # Include the complete cluster crossing the combo ramp.
    n = min(graph_n, _HEAD_NOTES) if plan.precise else graph_n
    while n < graph_n and _same_chart_time(notes[n - 1]["hit_time_ms"], notes[n]["hit_time_ms"]):
        n += 1

    clusters: list[list[int]] = []
    current = [0]
    for index in range(1, n):
        if _same_chart_time(notes[index - 1]["hit_time_ms"], notes[index]["hit_time_ms"]):
            current.append(index)
            continue
        if len(current) > 1:
            clusters.append(current)
        current = [index]
    if len(current) > 1:
        clusters.append(current)

    for cluster in clusters:
        if not any(notes[j]["note_result"] == "Great" and notes[j]["delta_ms"] is None for j in cluster):
            continue
        if not plan.precise:
            stop = min((j for j in cluster if notes[j]["note_result"] == "Perfect"), default=cluster[0])
            for j in range(cluster[0], stop):
                notes[j]["delta_ms"] = _guaranteed_early_great_ms(plan, j)
            continue

        latest_deltas = [math.inf] * len(cluster)
        latest_delta = math.inf
        for position in range(len(cluster) - 1, -1, -1):
            j = cluster[position]
            delta = notes[j]["delta_ms"]
            if notes[j]["note_result"] == "Great" and delta is None:
                latest_delta = _delta_at_or_before_ms(plan, j, "Great", latest_delta)
            else:
                if delta > latest_delta:
                    raise UnplayableTrace(f"note_graph: same-time cluster witness at note {j} contradicts chart order")
                latest_delta = delta
            latest_deltas[position] = latest_delta

        previous_delta = -math.inf
        for position, j in enumerate(cluster):
            note = notes[j]
            if note["note_result"] == "Great" and note["delta_ms"] is None:
                early_lo, early_hi = plan.bands[j].early_great
                note["delta_ms"] = _bounded_delta_ms(
                    plan, j, "Great", preferred_ms=_center(early_lo, early_hi), min_delta_ms=previous_delta,
                    max_delta_ms=latest_deltas[position],
                )
            elif note["delta_ms"] < previous_delta:
                raise UnplayableTrace(f"note_graph: same-time cluster witness at note {j} contradicts chart order")
            previous_delta = note["delta_ms"]


def _plan_preactivation_schedule(
    plan: _Plan, exact_order: Sequence[int], activation_index: int, boundary_index: int | None
) -> None:
    """Project preferred witness times into one exact monotone interval schedule."""
    notes, is_tail = plan.notes, plan.is_tail
    activation_press = notes[activation_index]["hit_time_ms"] + notes[activation_index]["delta_ms"]

    latest_presses = [0.0] * len(exact_order)
    latest_press = activation_press
    successor = activation_index
    for position in range(len(exact_order) - 1, -1, -1):
        index = exact_order[position]
        note = notes[index]
        # The input engine processes presses before releases at the same timestamp, so a release that must precede a
        # later press needs a strictly earlier event time.
        ordered_latest = _strictly_before(latest_press) if is_tail[index] and not is_tail[successor] else latest_press
        latest_delta = _delta_at_or_before_ms(plan, index, note["note_result"], ordered_latest - note["hit_time_ms"])
        latest_press = note["hit_time_ms"] + latest_delta
        latest_presses[position] = latest_press
        successor = index

    required_press = -math.inf
    if boundary_index is not None:
        boundary = notes[boundary_index]
        next_index = exact_order[0] if exact_order else activation_index
        boundary_upper = latest_presses[0] if exact_order else activation_press
        if is_tail[boundary_index] and not is_tail[next_index]:
            boundary_upper = _strictly_before(boundary_upper)
        result = boundary["note_result"]
        boundary["delta_ms"] = _bounded_delta_ms(
            plan, boundary_index, result,
            preferred_ms=_default_delta_ms(plan, boundary_index, result, boundary["delta_ms"]),
            max_delta_ms=boundary_upper - boundary["hit_time_ms"],
        )
        required_press = boundary["hit_time_ms"] + boundary["delta_ms"]

    for index, latest_note_press in zip(exact_order, latest_presses, strict=True):
        note = notes[index]
        result = note["note_result"]
        note["delta_ms"] = _bounded_delta_ms(
            plan, index, result,
            preferred_ms=_default_delta_ms(plan, index, result, note["delta_ms"]),
            min_delta_ms=required_press - note["hit_time_ms"],
            max_delta_ms=latest_note_press - note["hit_time_ms"],
        )
        required_press = note["hit_time_ms"] + note["delta_ms"]


def _plan_fg_section_schedule(plan: _Plan, sec: _Section) -> list[tuple[int, int]]:
    """Plan the hits a Force Greats section schedules before its activation; returns their input-order constraints."""
    sequence = (*sec.preactivation_order, sec.activation)
    boundary = sec.forced_start - 1 if sec.forced_start > 0 else None
    _plan_preactivation_schedule(plan, sec.preactivation_order, sec.activation, boundary)
    constraints = [] if boundary is None else [(boundary, sequence[0])]
    constraints.extend(zip(sequence, sequence[1:]))
    return constraints


def _hold_followers_after_activation(
    plan: _Plan, sections: Sequence[_Section], *, fg_schedule: bool
) -> list[tuple[int, int]]:
    """Delay the following notes that would preempt a delayed activation; returns the input-order constraints.

    A surface can activate on a late hit only if nearby following notes are held until after it. This materializes that
    input order; it never changes a judgment or fever membership. Force Greats schedules each section's preactivation
    hits and scans lane by lane: a following note only waits for its own lane. A Base note waits for the activation
    whatever its lane (one lane key): other-lane followers there must not pass a delayed activation.
    """
    notes, n = plan.notes, len(plan)
    constraints: list[tuple[int, int]] = []
    if n <= 1:
        return constraints
    for sec in sections:
        a = sec.activation
        activation_press = notes[a]["hit_time_ms"] + notes[a]["delta_ms"]
        planned_first: frozenset[int] = frozenset()
        scan_start = a + 1
        if fg_schedule:
            constraints.extend(_plan_fg_section_schedule(plan, sec))
            planned_first = frozenset(sec.preactivation_order)
            scan_start = sec.forced_start
        required_press_by_lane: dict[int, float] = {}
        previous_by_lane: dict[int, int] = {}
        global_required_press = activation_press

        for j in range(scan_start, n):
            if j == a or j in planned_first:
                continue
            note = notes[j]
            chart_j = note["hit_time_ms"]
            # Chart times are monotone and every legal press lies within 200 ms of chart, so once chart_j - 200 clears
            # every lane's requirement nothing later can press before it. Press times are not monotone over chart order
            # once a witness is delayed: a forced-Great sibling at the activation's own late edge satisfies the
            # requirement while on-time chord partners behind it would preempt the activation's fill.
            if j > a and chart_j - _LATEST_PRESS_MS > global_required_press:
                break
            lane = plan.lanes[j] if fg_schedule else -1
            previous = previous_by_lane.get(lane, a)
            required_press = required_press_by_lane.get(lane, activation_press)
            result = note["note_result"]
            press = chart_j + _default_delta_ms(plan, j, result, note["delta_ms"])
            if press < required_press:
                note["delta_ms"] = _delta_at_or_after_ms(plan, j, result, required_press - chart_j)
                press = chart_j + note["delta_ms"]
            # This note becomes only its lane's ordering floor: cross-lane notes may be pressed in either order.
            required_press_by_lane[lane] = press
            previous_by_lane[lane] = j
            global_required_press = max(global_required_press, press)
            constraints.append((previous, j))
    return constraints


def _plan_base_preactivation_schedules(plan: _Plan, sections: Sequence[_Section]) -> list[tuple[int, int]]:
    """Plan the chart-order fill events that precede each Base activation; returns their input-order constraints."""
    constraints: list[tuple[int, int]] = []
    previous_exit: int | None = None
    for sec in sections:
        a = sec.activation
        exact_order = tuple(range(0 if previous_exit is None else previous_exit + 1, a))
        _plan_preactivation_schedule(plan, exact_order, a, previous_exit)
        sequence = (*exact_order, a)
        if previous_exit is not None:
            constraints.append((previous_exit, sequence[0]))
        constraints.extend(zip(sequence, sequence[1:]))
        previous_exit = sec.fever_end
    return constraints


def _plan_remaining_selectors(plan: _Plan) -> None:
    """Give every remaining Great selector its canonical physical hit."""
    for index, note in enumerate(plan.notes):
        if note["delta_ms"] is None:
            note["delta_ms"] = plan.bands[index].late_great[0]


def _plan_blocked_late_greats_early(plan: _Plan, sections: Sequence[_Section]) -> None:
    """Non-Precise: a late Great whose input is not one frame margin before an input that must follow it is planned
    early (_guaranteed_early_great_ms), with the late Greats that must then precede it, when every input that must
    precede a moved one stays one margin earlier, every input that must follow it one margin later, and no fever window
    ends within a margin of its move. An input must precede another one of a later note in its lane, or of a later note
    scored in another order: a different judgment or fever in the combo ramp, an activation or a wasted note. Inputs
    a move passes are scored in either order, so the plan keeps its score and fever. A plan with an input it cannot
    move stays as it is (the physical replay rejects an order no player can play)."""
    notes, n, lane = plan.notes, len(plan), plan.lanes
    times = [note["hit_time_ms"] for note in notes]
    events = [time + note["delta_ms"] for time, note in zip(times, notes)]
    scored = [(note["note_result"], note["fever"]) for note in notes]
    special = {index for sec in sections for index in (sec.activation, sec.fever_end)}
    fever_ends = [sec.cutoff_ms for sec in sections]

    def ordered(a: int, b: int) -> bool:
        """Whether note a's input must precede note b's (a < b)."""
        return lane[a] == lane[b] or a in special or b in special or (a < _HEAD_NOTES and scored[a] != scored[b])

    def late_great(i: int) -> bool:
        return notes[i]["note_result"] == "Great" and events[i] > times[i]

    def too_close_after(i: int, at: float, planned: Mapping[int, float]) -> list[int]:
        """The later notes whose input must follow i's input at `at` but is not one margin after it."""
        out, b = [], i + 1
        while b < n and times[b] < at + _PLANNED_OFFSET_SPAN_MS:
            if ordered(i, b) and planned.get(b, events[b]) < at + FRAME_MARGIN_MS:
                out.append(b)
            b += 1
        return out

    def too_close_before(i: int, at: float, planned: Mapping[int, float]) -> list[int]:
        """The earlier notes whose input must precede i's input at `at` but is not one margin before it."""
        out, a = [], i - 1
        while a >= 0 and times[a] > at - _PLANNED_OFFSET_SPAN_MS:
            if ordered(a, i) and planned.get(a, events[a]) > at - FRAME_MARGIN_MS:
                out.append(a)
            a -= 1
        return out

    def early_group(k: int) -> dict[int, float] | None:
        """k and the late Greats that must move with it, at their early inputs; None when they cannot move."""
        planned = {k: times[k] + _guaranteed_early_great_ms(plan, k)}
        pending = [k]
        while pending:
            i = pending.pop()
            for a in too_close_before(i, planned[i], planned):
                if a in planned or not late_great(a):
                    return None
                planned[a] = times[a] + _guaranteed_early_great_ms(plan, a)
                pending.append(a)
        for i, at in planned.items():
            if too_close_after(i, at, planned) or any(
                at - FRAME_MARGIN_MS <= end <= events[i] + FRAME_MARGIN_MS for end in fever_ends
            ):
                return None
        return planned

    moved = True
    while moved:
        moved = False
        for k in range(n - 1, -1, -1):
            if not late_great(k) or not too_close_after(k, events[k], {}):
                continue
            group = early_group(k)
            if group is None:
                continue
            for i, at in group.items():
                notes[i]["delta_ms"] = _guaranteed_early_great_ms(plan, i)
                events[i] = at
            moved = True


def _assign_input_order(notes: list[dict[str, Any]], constraints: Sequence[tuple[int, int]]) -> list[int]:
    """Topologically order equal-time inputs while keeping physical time authoritative; returns the note indices in
    input order."""
    n = len(notes)
    event_times = [note["hit_time_ms"] + note["delta_ms"] for note in notes]
    successors: dict[int, set[int]] = {}
    indegree = [0] * n
    for before, after in constraints:
        if event_times[before] > event_times[after]:
            raise UnplayableTrace(f"note_graph: exact input-order constraint moves backward in time ({before} -> {after})")
        targets = successors.setdefault(before, set())
        if after not in targets:
            targets.add(after)
            indegree[after] += 1

    # No constraint runs backward in time, so walking the ready inputs by time yields a time-monotone order: an input
    # released by the walk joins the part still ahead of it. Constraints are few, so nearly every note starts ready.
    ready = sorted([(event_times[index], index) for index in range(n) if indegree[index] == 0])
    for position, (_event_time, index) in enumerate(ready, 1):
        if index in successors:
            for after in successors[index]:
                indegree[after] -= 1
                if indegree[after] == 0:
                    insort(ready, (event_times[after], after), lo=position)
    if len(ready) != n:
        raise UnplayableTrace("note_graph: exact input-order constraints contain a cycle")
    ordered = [index for _event_time, index in ready]
    for input_order, note_index in enumerate(ordered):
        notes[note_index]["input_order"] = input_order
    return ordered


def _plan_frame_safe_hits(plan: _Plan, ordered: Sequence[int], sections: Sequence[_Section]) -> None:
    """Plan each hit no later than the latest offset every frame timing judges in its band.

    A later hit moves back to that offset when it stays a frame margin after the previous input and keeps its fever
    state: a fever hit stays after the previous fever input, and a hit out of fever stays a frame margin past the
    cutoff of the last window an input was in. Its judgment, the input order and fever membership, and so the score,
    stay as planned. Activations (in fever after an input out of it) never move. A hit on its chart time is safe in
    every band, so only offset hits are visited (`ordered`: note indices in input order).
    """
    notes = plan.notes
    witnesses = (notes[min(sec.fever_end, len(notes)) - 1] for sec in sections)
    cutoffs = {w["section"]: w["fever_end_ms"] for w in witnesses if w["is_fever_end_witness"]}
    offset_hits = sorted((note["input_order"], index) for index, note in enumerate(notes) if note["delta_ms"] != 0.0)
    last_fever, scanned = None, 0
    for position, index in offset_hits:
        while scanned < position:  # the last fever input before this one
            if notes[ordered[scanned]]["fever"]:
                last_fever = notes[ordered[scanned]]
            scanned += 1
        note = notes[index]
        bands = plan.bands[index]
        delta = note["delta_ms"]
        if note["note_result"] == "Perfect":
            low, high = bands.perfect
        else:
            low, high = bands.early_great if delta <= bands.early_great[1] else bands.late_great
        safe = _frame_safe_latest_ms(high)
        if not delta > safe >= low:
            continue
        previous = notes[ordered[position - 1]] if position else None
        if note["fever"] and not (previous and previous["fever"]):
            continue
        earliest_ms = -math.inf
        if previous is not None:
            earliest_ms = previous["hit_time_ms"] + previous["delta_ms"] + FRAME_MARGIN_MS
        if not note["fever"] and last_fever is not None:
            earliest_ms = max(earliest_ms, cutoffs.get(last_fever["section"], math.inf) + FRAME_MARGIN_MS)
        if note["hit_time_ms"] + safe >= earliest_ms:
            note["delta_ms"] = safe


def _apply_schedule_fever(plan: _Plan, ordered: Sequence[int], sections: Sequence[_Section]) -> None:
    """Fever membership from the input order (note indices) and each section's duration."""
    cursor = 0
    active_until_ms: float | None = None
    for index in ordered:
        note = plan.notes[index]
        event_ms = note["hit_time_ms"] + note["delta_ms"]
        if active_until_ms is not None and event_ms >= active_until_ms:
            active_until_ms = None
        if cursor < len(sections) and sections[cursor].activation == index:
            if active_until_ms is not None:
                raise UnplayableTrace("note_graph: a planned activation lands while fever is still active")
            active_until_ms = event_ms + sections[cursor].fever_duration_ms
            cursor += 1
        note["fever"] = active_until_ms is not None
    if cursor != len(sections):
        raise UnplayableTrace("note_graph: the input order does not reach every planned activation")


def _plan_endpoint_early_perfects(
    plan: _Plan, sec: _Section, cutoff_ms: float, skip_range: tuple[int, int] | None
) -> None:
    """Issue #42: a fever note at or after the cutoff is in fever only because it is hit early. It is planned at the
    center of its legal in-fever hits, at or after the previous planned hit, or at that floor when no room is left.
    Great selectors have no timing yet and early-Great tail notes (`skip_range`) get theirs below."""
    notes = plan.notes
    upper_hit = _strictly_before(cutoff_ms)
    prev_hit = -math.inf
    for j in range(max(0, sec.activation), min(sec.fever_end, len(plan))):
        if skip_range is not None and skip_range[0] <= j < skip_range[1]:
            continue
        note = notes[j]
        delta, hit = note["delta_ms"], note["hit_time_ms"]
        if delta is None:
            continue
        if note["is_activation_witness"] or hit < cutoff_ms:
            prev_hit = max(prev_hit, hit + delta)
            continue
        lo_hit = max(hit + plan.bands[j].perfect[0], prev_hit)
        shown_hit = lo_hit if lo_hit >= upper_hit else _center(lo_hit, upper_hit)
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit


def _plan_early_great_tail(plan: _Plan, sec: _Section, cutoff_ms: float, early_range: tuple[int, int]) -> None:
    """Issue #68: the early-Great notes that extend a fever window, at the center of their in-fever early-Great hits."""
    notes = plan.notes
    start, end = early_range
    strict_cutoff = _strictly_before(cutoff_ms)
    prev_hit = -math.inf
    for j in range(max(0, sec.activation), min(end, len(plan))):
        note = notes[j]
        hit, delta = note["hit_time_ms"], note["delta_ms"]
        if j < start:
            if delta is not None:
                prev_hit = max(prev_hit, hit + delta)
            continue
        if not note["fever"] or note["is_activation_witness"]:
            continue
        great_low, great_high = plan.bands[j].early_great
        lo_hit = max(hit + great_low, prev_hit)
        hi_hit = hit + min(great_high, strict_cutoff - hit)
        if lo_hit > hi_hit:
            raise UnplayableTrace(f"note_graph: early-Great fever-end note {j} has no hit left in fever")
        shown_hit = _center(lo_hit, hi_hit)
        note["note_result"] = "Great"
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit


def _plan_tight_cutoff_cluster(plan: _Plan, sec: _Section, cutoff_ms: float) -> None:
    """Issue #64: when a section's last chart-time cluster has a cutoff tighter than its Perfect band, all of it is
    planned at one offset inside both. Comfortable ends keep their chart time."""
    notes = plan.notes
    a = sec.activation
    last_fever = min(sec.fever_end, len(plan)) - 1
    if last_fever < a:
        return
    witness = notes[last_fever]
    if not witness["is_fever_end_witness"] or witness["is_activation_witness"]:
        return
    hit = witness["hit_time_ms"]
    if hit >= cutoff_ms:
        return
    strict_cutoff = _strictly_before(cutoff_ms)
    if strict_cutoff - hit >= plan.tap_latest_perfect:
        return
    if witness["note_result"] != "Perfect":
        raise UnplayableTrace(f"note_graph: no hit plays fever-end note {last_fever}, a Great at a tight cutoff")

    cluster: list[int] = []
    for j in range(max(0, a), last_fever + 1):
        note = notes[j]
        if not note["fever"] or note["is_activation_witness"] or not _same_chart_time(note["hit_time_ms"], hit):
            continue
        if note["delta_ms"] is None or note["note_result"] != "Perfect":
            raise UnplayableTrace(f"note_graph: no hit plays fever-end note {j}, a Great at a tight cutoff")
        cluster.append(j)
    if not cluster:
        return

    cluster_lo, cluster_hi, latest_perfect = -math.inf, math.inf, math.inf
    for j in cluster:
        lo, hi = plan.bands[j].perfect
        latest_perfect = min(latest_perfect, hi)
        safe_hi = min(hi, strict_cutoff - notes[j]["hit_time_ms"])
        if lo > safe_hi:
            raise UnplayableTrace(f"note_graph: fever-end note {j} has no Perfect hit in fever")
        cluster_lo, cluster_hi = max(cluster_lo, lo), min(cluster_hi, safe_hi)
    if cluster_lo > cluster_hi:
        raise UnplayableTrace("note_graph: a fever-end cluster has no shared Perfect hit in fever")
    if cluster_hi >= latest_perfect:
        return
    shared = _center(cluster_lo, cluster_hi)
    for j in cluster:
        notes[j]["delta_ms"] = shared


def _push_fever_exit_notes(plan: _Plan, sec: _Section, cutoff_ms: float) -> None:
    """The mirror of the early endpoint: a plain Perfect the frontier excluded from fever by its latest legal hit, but
    whose chart time is still before the cutoff, is planned at that latest hit so the drain excludes it as the surface
    does (e.g. Raining Tacos (Easy) T1, where a note on its chart time scored 1,599 more than the card). Its float
    latest hit can sit a fraction of a millisecond before the cutoff and still land past the replay's own fever end, so
    the physical replay, not this pass, is the check."""
    notes = plan.notes
    j = sec.fever_end
    while 0 <= j < len(plan):
        note = notes[j]
        if note["hit_time_ms"] >= cutoff_ms:
            break
        if note["is_activation_witness"] or note["fever"] or note["delta_ms"] is None or note["note_result"] != "Perfect":
            break
        note["delta_ms"] = plan.bands[j].perfect[1]
        j += 1


def _mark_fever_end(plan: _Plan, sec: _Section, cutoff_ms: float, early_range: tuple[int, int] | None) -> None:
    """A section's fever-end witness (its last fever note, carrying the cutoff) and, on precise, the endpoint hits that
    keep its last fever notes inside the cutoff and push the first note past it out."""
    last_fever = min(sec.fever_end, len(plan)) - 1
    if sec.activation <= last_fever:
        witness = plan.notes[last_fever]
        witness["is_fever_end_witness"] = True
        witness["fever_end_ms"] = cutoff_ms
        witness["section"] = sec.number
    if not plan.precise:
        return
    _plan_endpoint_early_perfects(plan, sec, cutoff_ms, early_range)
    if early_range is not None:
        _plan_early_great_tail(plan, sec, cutoff_ms, early_range)
    _plan_tight_cutoff_cluster(plan, sec, cutoff_ms)
    _push_fever_exit_notes(plan, sec, cutoff_ms)


def _mark_section_fever(plan: _Plan, sec: _Section) -> None:
    for j in range(max(0, sec.activation), min(sec.fever_end, len(plan))):
        note = plan.notes[j]
        note["fever"] = True
        if note["section"] == 0:
            note["section"] = sec.number


def timeline_frontier_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> list[dict[str, Any]]:
    """BASE graph from a selected timeline-frontier witness trace."""
    plan = _new_plan(total_notes, timestamps, note_types, lanes, timing_mode, perfect_time)
    sections = _sections(frontier_trace)
    for sec in sections:
        _mark_section_fever(plan, sec)
        if plan.precise:
            activation = plan.notes[sec.activation]
            activation["delta_ms"] = sec.hit_offset_ms
            activation["is_activation_witness"] = True
            activation["section"] = sec.number
        _mark_fever_end(plan, sec, sec.cutoff_ms, None)
    if plan.precise:
        # The frontier prices a delayed activation clock, but the replay plays physical inputs in time order: every
        # following input that would land before the activation is delayed to it, or a chord sibling on its chart time
        # would fill the bar first.
        constraints = _plan_base_preactivation_schedules(plan, sections)
        constraints.extend(_hold_followers_after_activation(plan, sections, fg_schedule=False))
        ordered = _assign_input_order(plan.notes, constraints)
        _plan_frame_safe_hits(plan, ordered, sections)
    return plan.notes


def base_note_graph(
    *,
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    is_fever_mask: Sequence[bool] | np.ndarray,
) -> list[dict[str, Any]]:
    """BASE graph of a row without a trace: every note Perfect on its chart time, with the fever of `is_fever_mask`
    (solver.fever_timeline.calculate_fever_timeline_indices from the row's stats)."""
    notes = _perfect_notes(total_notes, timestamps)
    if len(notes) < total_notes or len(is_fever_mask) < total_notes:
        raise ValueError("base_note_graph: timestamps/is_fever_mask shorter than total_notes")
    for note, fever in zip(notes, np.asarray(is_fever_mask).tolist()):
        note["fever"] = bool(fever)
    return notes


def force_greats_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> list[dict[str, Any]]:
    """FG graph from the persisted witness trace (the per-loadout ForceGreats.frontier_trace). Each section carries a
    sequential region of the chart: a fever window [activation, fever_end), a forced run of Great selectors, and the
    activation note, a Great when its judgment is late_great. Every other note is a Perfect; a note may be both fever
    and Great."""
    plan = _new_plan(total_notes, timestamps, note_types, lanes, timing_mode, perfect_time)
    sections = _sections(frontier_trace)
    notes, n = plan.notes, len(plan)

    # Labels are global inputs to every activation cap: materialize the whole map before planning any witness, or an
    # earlier section could read a Great owned by a later section as Perfect and reject the producer's schedule.
    for sec in sections:
        for j in range(max(0, sec.forced_run_start), min(sec.forced_run_start + sec.forced_run_count, n)):
            note = notes[j]
            note["note_result"] = "Great"
            note["delta_ms"] = None
            if note["section"] == 0:
                note["section"] = sec.number
        _mark_section_fever(plan, sec)
        if sec.judgment == "late_great":
            notes[sec.activation]["note_result"] = "Great"

    for sec in sections:
        a = sec.activation
        cutoff_ms = sec.cutoff_ms
        if plan.precise and (sec.judgment == "late_great" or sec.hit_offset_ms != 0.0):
            activation = notes[a]
            activation["delta_ms"] = _activation_delta_ms(plan, sec)
            activation["is_activation_witness"] = True
            activation["section"] = sec.number
            cutoff_ms = activation["hit_time_ms"] + activation["delta_ms"] + sec.fever_duration_ms
        # The section's early-Great tail notes inside its fever window.
        early_range = None
        if sec.early_great_start >= 0 and sec.early_great_end >= 0:
            start, end = max(a, sec.early_great_start, 0), min(sec.early_great_end, sec.fever_end, n)
            if end > start:
                early_range = (start, end)
        _mark_fever_end(plan, sec, cutoff_ms, early_range)

    _mark_same_time_selector_deltas(plan)
    constraints = _hold_followers_after_activation(plan, sections, fg_schedule=True) if plan.precise else []
    _plan_remaining_selectors(plan)
    if not plan.precise:
        _plan_blocked_late_greats_early(plan, sections)
    ordered = _assign_input_order(notes, constraints)
    if plan.precise:
        _apply_schedule_fever(plan, ordered, sections)
        _plan_frame_safe_hits(plan, ordered, sections)
    return notes


def _head_set_from_words(words: Sequence[int], head_limit: int) -> set[int]:
    """The note indices in [0, head_limit) set in a 4x32-bit head mask."""
    return {i for i in range(head_limit) if (int(words[i // 32]) >> (i % 32)) & 1}


def reconcile_base_note_graph(
    note_graph: Sequence[Mapping[str, Any]],
    *,
    total_notes: int,
    response_surface: Sequence[int],
) -> None:
    """Fail loudly unless a Base graph exactly matches its selected score surface."""
    n = int(total_notes)
    surface = tuple(int(value) for value in response_surface)
    if len(surface) != 6:
        raise ValueError("Base response surface must contain four head words and two body counts")
    head_limit = min(n, _HEAD_NOTES)
    graph_fever = {int(note["note_index"]) for note in note_graph if bool(note["fever"])}
    graph_head = {index for index in graph_fever if index < head_limit}
    surface_head = _head_set_from_words(surface[:4], head_limit)
    if graph_head != surface_head:
        raise ValueError(
            "Base note-graph head fever positions differ from the selected response surface: "
            f"{graph_head ^ surface_head}"
        )
    graph_body_fever = sum(1 for index in graph_fever if index >= _HEAD_NOTES)
    body_total = max(0, n - _HEAD_NOTES)
    if graph_body_fever != surface[4] or body_total - graph_body_fever != surface[5]:
        raise ValueError(
            "Base note-graph body counts differ from the selected response surface: "
            f"graph=({graph_body_fever}, {body_total - graph_body_fever}) surface=({surface[4]}, {surface[5]})"
        )


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
    """Fail loudly unless an FG graph exactly matches its surface: the head notes' fever and Great bitmasks, the body
    notes' fever, Great and fever-Great counts."""
    head_limit = min(int(total_notes), _HEAD_NOTES)
    g_fever_idx = {int(x["note_index"]) for x in note_graph if bool(x["fever"])}
    g_great_idx = {int(x["note_index"]) for x in note_graph if str(x["note_result"]) == "Great"}

    surface_fever_head = _head_set_from_words(fever_words, head_limit)
    surface_great_head = _head_set_from_words(great_words, head_limit)
    g_fever_head = {i for i in g_fever_idx if i < head_limit}
    g_great_head = {i for i in g_great_idx if i < head_limit}
    if g_fever_head != surface_fever_head:
        raise ValueError(f"FG note-graph head fever positions != surface mask: {g_fever_head ^ surface_fever_head}")
    if g_great_head != surface_great_head:
        raise ValueError(f"FG note-graph head great positions != surface mask: {g_great_head ^ surface_great_head}")

    g_body_fever = sum(1 for i in g_fever_idx if i >= _HEAD_NOTES)
    g_body_great = sum(1 for i in g_great_idx if i >= _HEAD_NOTES)
    g_body_fg = sum(1 for i in (g_fever_idx & g_great_idx) if i >= _HEAD_NOTES)
    if g_body_fever != int(body_fever):
        raise ValueError(f"FG note-graph body_fever {g_body_fever} != surface {int(body_fever)}")
    if g_body_great != int(body_great):
        raise ValueError(f"FG note-graph body_great {g_body_great} != surface {int(body_great)}")
    if g_body_fg != int(body_fever_great):
        raise ValueError(f"FG note-graph body_fever_great {g_body_fg} != surface {int(body_fever_great)}")
