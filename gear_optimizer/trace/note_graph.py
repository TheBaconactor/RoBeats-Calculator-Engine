"""A stored build's note plan: per note, what the timing graph draws and the replay plays.

A plan keeps its notes as columns (NotePlan); NotePlan.graph() writes each note as the dict the timing graph reads:
note_index, hit_time_ms (its chart time), note_result ("Perfect" or "Great"), delta_ms (its planned hit offset, + late),
input_order (its place in the input stream), fever, is_activation_witness, is_fever_end_witness, fever_end_ms (the fever
cutoff, on a section's last fever note) and section.

Two plans per loadout, rebuilt from the persisted frontier trace, so nothing per note is stored:
  * timeline_frontier_plan, Base: every note Perfect, each activation at its witnessed hit.
  * force_greats_plan, Force Greats: per-note Perfect or Great. A forced Great is a selector without a timing of its own
    until the passes below give it one; a late-Great or offset Perfect activation is hit inside the interval the
    producer proved keeps its surface.
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
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import chain
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
    "NotePlan",
    "base_note_graph",
    "timeline_frontier_note_graph",
    "timeline_frontier_plan",
    "force_greats_note_graph",
    "force_greats_plan",
    "reconcile_base_plan",
    "reconcile_force_greats_plan",
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
class NotePlan:
    """A plan's notes as columns: chart time, planned offset (None: a Great selector with no timing yet), Great, fever,
    activation witness, section and place in the input stream; `fever_ends`, the fever-end witnesses and their cutoffs.
    A plan being built also reads each note's bands at the build's Perfect Time and the chart."""

    hit_ms: list[float]
    delta: list[float | None]
    great: list[bool]
    fever: list[bool]
    activation_witness: list[bool]
    section: list[int]
    input_order: list[int]
    fever_ends: dict[int, float]
    bands: list[_Bands] = field(default_factory=list)
    is_tail: list[bool] = field(default_factory=list)
    lanes: list[int] = field(default_factory=list)
    precise: bool = False
    tap_latest_perfect: float = 0.0

    def __len__(self) -> int:
        return len(self.hit_ms)

    def graph(self) -> list[dict[str, Any]]:
        """The plan as the timing graph reads it, a dict per note."""
        return [
            {
                "note_index": index,
                "hit_time_ms": hit,
                "note_result": "Great" if great else "Perfect",
                "delta_ms": delta,
                "input_order": order,
                "fever": fever,
                "is_activation_witness": witness,
                "is_fever_end_witness": index in self.fever_ends,
                "fever_end_ms": self.fever_ends.get(index),
                "section": section,
            }
            for index, (hit, delta, great, fever, witness, section, order) in enumerate(
                zip(self.hit_ms, self.delta, self.great, self.fever, self.activation_witness, self.section, self.input_order)
            )
        ]


def _chart_times_ms(total_notes: int, timestamps: Sequence[float] | np.ndarray) -> list[float]:
    return (np.asarray(timestamps, dtype=np.float64).reshape(-1)[:total_notes] * 1000.0).tolist()


def _new_plan(
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> NotePlan:
    if timing_mode not in TIMING_MODES:
        raise ValueError(f"note_graph: unknown timing_mode {timing_mode!r}")
    hit_ms = _chart_times_ms(total_notes, timestamps)
    is_tail = (np.asarray(note_types).reshape(-1) == HELD_TAIL_TYPE).tolist()
    lane_ids = np.asarray(lanes).reshape(-1).tolist()
    if not len(hit_ms) == len(is_tail) == len(lane_ids) == total_notes:
        raise ValueError("note_graph: timestamps, note_types and lanes must match total_notes")
    tap, tail = _tap_and_tail_bands(perfect_time)
    n = total_notes
    return NotePlan(
        hit_ms, [0.0] * n, [False] * n, [False] * n, [False] * n, [0] * n, list(range(n)), {},
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


def _guaranteed_early_great_ms(plan: NotePlan, j: int) -> float:
    """The latest planned offset every frame timing judges an early Great."""
    return _frame_safe_latest_ms(plan.bands[j].early_great[1])


def _default_delta_ms(plan: NotePlan, j: int) -> float:
    """A hit's planned offset: its own, or the first late-Great offset for a selector."""
    delta = plan.delta[j]
    return plan.bands[j].late_great[0] if delta is None else delta


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
    plan: NotePlan,
    j: int,
    *,
    preferred_ms: float,
    min_delta_ms: float = -math.inf,
    max_delta_ms: float = math.inf,
) -> float:
    """The offset nearest `preferred_ms` that keeps note j's judgment inside [min_delta_ms, max_delta_ms]."""
    bands = plan.bands[j]
    candidates: list[float] = []
    for lo, hi in (bands.early_great, bands.late_great) if plan.great[j] else (bands.perfect,):
        feasible_lo, feasible_hi = max(lo, min_delta_ms), min(hi, max_delta_ms)
        if feasible_lo <= feasible_hi:
            candidates.append(min(max(preferred_ms, feasible_lo), feasible_hi))
    if not candidates:
        judgment = "Great" if plan.great[j] else "Perfect"
        raise UnplayableTrace(f"note_graph: exact input order has no legal bounded hit for note {j}'s {judgment} judgment")
    if len(candidates) == 1:
        return candidates[0]
    if preferred_ms == math.inf:
        return max(candidates)
    if preferred_ms == -math.inf:
        return min(candidates)
    return min(candidates, key=lambda delta: (abs(delta - preferred_ms), delta))


def _delta_at_or_after_ms(plan: NotePlan, j: int, min_delta_ms: float) -> float:
    return _bounded_delta_ms(plan, j, preferred_ms=min_delta_ms, min_delta_ms=min_delta_ms)


def _delta_at_or_before_ms(plan: NotePlan, j: int, max_delta_ms: float) -> float:
    return _bounded_delta_ms(plan, j, preferred_ms=max_delta_ms, max_delta_ms=max_delta_ms)


def _activation_delta_ms(plan: NotePlan, sec: _Section) -> float:
    """The max-margin hit of a late-Great or offset Perfect activation that keeps the scored input order."""
    hit_ms, bands, a = plan.hit_ms, plan.bands, sec.activation
    judge_lo, judge_hi = bands[a].late_great if sec.judgment == "late_great" else bands[a].perfect
    chart_ms = hit_ms[a]
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
            earliest_hit_ms = hit_ms[j] + bands[j].early_great[0]
            lo = max(lo, math.nextafter(earliest_hit_ms - sec.fever_duration_ms, math.inf) - chart_ms)
        if lo > hi:
            raise UnplayableTrace(
                f"note_graph: activation witness has no score-parity room for an early-Great fever-end note at "
                f"activation {a} ({lo:.3f}ms > {hi:.3f}ms)"
            )

    # A following note that the schedule does not plan before the activation caps it at that note's latest legal hit.
    # Equal event times are legal: the activation -> follower constraint orders them.
    earliest, latest_hit = chart_ms + lo, chart_ms + hi
    planned_first = frozenset(sec.preactivation_order)
    for j in range(a + 1, len(plan)):
        if j in planned_first:
            continue
        if hit_ms[j] >= latest_hit:
            break
        latest_hit = min(latest_hit, hit_ms[j] + (bands[j].late_great[1] if plan.great[j] else bands[j].perfect[1]))
        if latest_hit < earliest:
            raise UnplayableTrace(
                f"note_graph: activation witness cannot preserve following note order without changing note {a}'s "
                f"{sec.judgment} judgment"
            )
    feasible_hi = min(hi, latest_hit - chart_ms)
    if feasible_hi < lo:
        raise UnplayableTrace(
            f"note_graph: activation witness cannot preserve following note order without changing note {a}'s "
            f"{sec.judgment} judgment"
        )
    # The midpoint maximizes the input error the hit tolerates in both directions.
    return _center(lo, feasible_hi)


def _same_time_clusters(hit_ms: Sequence[float]) -> list[list[int]]:
    """The notes that share a chart time with the next or the previous one, chord by chord."""
    clusters: list[list[int]] = []
    for link in np.flatnonzero(np.abs(np.diff(hit_ms)) <= _FEVER_END_SAME_CHART_TIME_MS).tolist():
        if clusters and clusters[-1][-1] == link:
            clusters[-1].append(link + 1)
        else:
            clusters.append([link, link + 1])
    return clusters


def _mark_same_time_selector_deltas(plan: NotePlan) -> None:
    """Keep selector order inside score-bearing ties: chart order through the combo ramp (non-precise: the whole
    chart, where only the Greats leading a tie can go early, the Perfects staying on time)."""
    hit_ms, delta, graph_n = plan.hit_ms, plan.delta, len(plan)
    if graph_n <= 1:
        return
    # Include the complete cluster crossing the combo ramp.
    n = min(graph_n, _HEAD_NOTES) if plan.precise else graph_n
    while n < graph_n and _same_chart_time(hit_ms[n - 1], hit_ms[n]):
        n += 1

    for cluster in _same_time_clusters(hit_ms[:n]):
        if not any(delta[j] is None for j in cluster):
            continue
        if not plan.precise:
            stop = min((j for j in cluster if not plan.great[j]), default=cluster[0])
            for j in range(cluster[0], stop):
                delta[j] = _guaranteed_early_great_ms(plan, j)
            continue

        latest_deltas = [math.inf] * len(cluster)
        latest_delta = math.inf
        for position in range(len(cluster) - 1, -1, -1):
            j = cluster[position]
            if delta[j] is None:
                latest_delta = _delta_at_or_before_ms(plan, j, latest_delta)
            else:
                if delta[j] > latest_delta:
                    raise UnplayableTrace(f"note_graph: same-time cluster witness at note {j} contradicts chart order")
                latest_delta = delta[j]
            latest_deltas[position] = latest_delta

        previous_delta = -math.inf
        for position, j in enumerate(cluster):
            if delta[j] is None:
                early_lo, early_hi = plan.bands[j].early_great
                delta[j] = _bounded_delta_ms(
                    plan, j, preferred_ms=_center(early_lo, early_hi), min_delta_ms=previous_delta,
                    max_delta_ms=latest_deltas[position],
                )
            elif delta[j] < previous_delta:
                raise UnplayableTrace(f"note_graph: same-time cluster witness at note {j} contradicts chart order")
            previous_delta = delta[j]


def _plan_preactivation_schedule(
    plan: NotePlan, exact_order: Sequence[int], activation_index: int, boundary_index: int | None
) -> None:
    """Project preferred witness times into one exact monotone interval schedule."""
    hit_ms, delta, is_tail = plan.hit_ms, plan.delta, plan.is_tail
    activation_press = hit_ms[activation_index] + delta[activation_index]

    latest_presses = [0.0] * len(exact_order)
    latest_press = activation_press
    successor = activation_index
    for position in range(len(exact_order) - 1, -1, -1):
        index = exact_order[position]
        # The input engine processes presses before releases at the same timestamp, so a release that must precede a
        # later press needs a strictly earlier event time.
        ordered_latest = _strictly_before(latest_press) if is_tail[index] and not is_tail[successor] else latest_press
        latest_press = hit_ms[index] + _delta_at_or_before_ms(plan, index, ordered_latest - hit_ms[index])
        latest_presses[position] = latest_press
        successor = index

    required_press = -math.inf
    if boundary_index is not None:
        next_index = exact_order[0] if exact_order else activation_index
        boundary_upper = latest_presses[0] if exact_order else activation_press
        if is_tail[boundary_index] and not is_tail[next_index]:
            boundary_upper = _strictly_before(boundary_upper)
        delta[boundary_index] = _bounded_delta_ms(
            plan, boundary_index, preferred_ms=_default_delta_ms(plan, boundary_index),
            max_delta_ms=boundary_upper - hit_ms[boundary_index],
        )
        required_press = hit_ms[boundary_index] + delta[boundary_index]

    for index, latest_note_press in zip(exact_order, latest_presses, strict=True):
        delta[index] = _bounded_delta_ms(
            plan, index, preferred_ms=_default_delta_ms(plan, index), min_delta_ms=required_press - hit_ms[index],
            max_delta_ms=latest_note_press - hit_ms[index],
        )
        required_press = hit_ms[index] + delta[index]


def _plan_fg_section_schedule(plan: NotePlan, sec: _Section) -> list[tuple[int, int]]:
    """Plan the hits a Force Greats section schedules before its activation; returns their input-order constraints."""
    sequence = (*sec.preactivation_order, sec.activation)
    boundary = sec.forced_start - 1 if sec.forced_start > 0 else None
    _plan_preactivation_schedule(plan, sec.preactivation_order, sec.activation, boundary)
    constraints = [] if boundary is None else [(boundary, sequence[0])]
    constraints.extend(zip(sequence, sequence[1:]))
    return constraints


def _hold_followers_after_activation(
    plan: NotePlan, sections: Sequence[_Section], *, fg_schedule: bool
) -> list[tuple[int, int]]:
    """Delay the following notes that would preempt a delayed activation; returns the input-order constraints.

    A surface can activate on a late hit only if nearby following notes are held until after it. This materializes that
    input order; it never changes a judgment or fever membership. Force Greats schedules each section's preactivation
    hits and scans lane by lane: a following note only waits for its own lane. A Base note waits for the activation
    whatever its lane (one lane key): other-lane followers there must not pass a delayed activation.
    """
    hit_ms, delta, n = plan.hit_ms, plan.delta, len(plan)
    constraints: list[tuple[int, int]] = []
    if n <= 1:
        return constraints
    for sec in sections:
        a = sec.activation
        activation_press = hit_ms[a] + delta[a]
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
            chart_j = hit_ms[j]
            # Chart times are monotone and every legal press lies within 200 ms of chart, so once chart_j - 200 clears
            # every lane's requirement nothing later can press before it. Press times are not monotone over chart order
            # once a witness is delayed: a forced-Great sibling at the activation's own late edge satisfies the
            # requirement while on-time chord partners behind it would preempt the activation's fill.
            if j > a and chart_j - _LATEST_PRESS_MS > global_required_press:
                break
            lane = plan.lanes[j] if fg_schedule else -1
            previous = previous_by_lane.get(lane, a)
            required_press = required_press_by_lane.get(lane, activation_press)
            press = chart_j + _default_delta_ms(plan, j)
            if press < required_press:
                delta[j] = _delta_at_or_after_ms(plan, j, required_press - chart_j)
                press = chart_j + delta[j]
            # This note becomes only its lane's ordering floor: cross-lane notes may be pressed in either order.
            required_press_by_lane[lane] = press
            previous_by_lane[lane] = j
            global_required_press = max(global_required_press, press)
            constraints.append((previous, j))
    return constraints


def _plan_base_preactivation_schedules(plan: NotePlan, sections: Sequence[_Section]) -> list[tuple[int, int]]:
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


def _plan_remaining_selectors(plan: NotePlan) -> None:
    """Give every remaining Great selector its canonical physical hit."""
    for index, delta in enumerate(plan.delta):
        if delta is None:
            plan.delta[index] = plan.bands[index].late_great[0]


def _plan_blocked_late_greats_early(plan: NotePlan, sections: Sequence[_Section]) -> None:
    """Non-Precise: a late Great whose input is not one frame margin before an input that must follow it is planned
    early (_guaranteed_early_great_ms), with the late Greats that must then precede it, when every input that must
    precede a moved one stays one margin earlier, every input that must follow it one margin later, and no fever window
    ends within a margin of its move. An input must precede another one of a later note in its lane, or of a later note
    scored in another order: a different judgment or fever in the combo ramp, an activation or a wasted note. Inputs
    a move passes are scored in either order, so the plan keeps its score and fever. A plan with an input it cannot
    move stays as it is (the physical replay rejects an order no player can play)."""
    n, lane, times = len(plan), plan.lanes, plan.hit_ms
    events = (np.array(times) + np.array(plan.delta)).tolist()
    scored = list(zip(plan.great, plan.fever))
    special = {index for sec in sections for index in (sec.activation, sec.fever_end)}
    fever_ends = [sec.cutoff_ms for sec in sections]

    def ordered(a: int, b: int) -> bool:
        """Whether note a's input must precede note b's (a < b)."""
        return lane[a] == lane[b] or a in special or b in special or (a < _HEAD_NOTES and scored[a] != scored[b])

    def late_great(i: int) -> bool:
        return plan.great[i] and events[i] > times[i]

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
        for k in np.flatnonzero(plan.great)[::-1].tolist():
            if not late_great(k) or not too_close_after(k, events[k], {}):
                continue
            group = early_group(k)
            if group is None:
                continue
            for i, at in group.items():
                plan.delta[i] = _guaranteed_early_great_ms(plan, i)
                events[i] = at
            moved = True


def _assign_input_order(plan: NotePlan, constraints: Sequence[tuple[int, int]]) -> list[int]:
    """Topologically order equal-time inputs while keeping physical time authoritative; returns the note indices in
    input order."""
    event_times = np.array(plan.hit_ms) + np.array(plan.delta)
    pairs = np.fromiter(chain.from_iterable(constraints), dtype=np.int64, count=2 * len(constraints)).reshape(-1, 2)
    gaps = event_times[pairs[:, 1]] - event_times[pairs[:, 0]]
    if (gaps < 0.0).any():
        before, after = pairs[np.argmax(gaps < 0.0)].tolist()
        raise UnplayableTrace(f"note_graph: exact input-order constraint moves backward in time ({before} -> {after})")
    successors: dict[int, set[int]] = {}
    waiting: dict[int, int] = {}
    # No constraint runs backward in time, so time orders all but the inputs of one time: only those need a constraint.
    for before, after in pairs[gaps == 0.0].tolist():
        targets = successors.setdefault(before, set())
        if after not in targets:
            targets.add(after)
            waiting[after] = waiting.get(after, 0) + 1

    # Walking the ready inputs by time, an input released by the walk joins the part still ahead of it.
    ready = [index for index in np.argsort(event_times, kind="stable").tolist() if index not in waiting]
    for position, index in enumerate(ready, 1):
        if index in successors:
            for after in successors[index]:
                waiting[after] -= 1
                if waiting[after] == 0:
                    insort(ready, after, lo=position, key=lambda note: (event_times[note], note))
    if len(ready) != len(event_times):
        raise UnplayableTrace("note_graph: exact input-order constraints contain a cycle")
    for input_order, note_index in enumerate(ready):
        plan.input_order[note_index] = input_order
    return ready


def _plan_frame_safe_hits(plan: NotePlan, ordered: Sequence[int], sections: Sequence[_Section]) -> None:
    """Plan each hit no later than the latest offset every frame timing judges in its band.

    A later hit moves back to that offset when it stays a frame margin after the previous input and keeps its fever
    state: a fever hit stays after the previous fever input, and a hit out of fever stays a frame margin past the
    cutoff of the last window an input was in. Its judgment, the input order and fever membership, and so the score,
    stay as planned. Activations (in fever after an input out of it) never move. A hit on its chart time is safe in
    every band, so only offset hits are visited (`ordered`: note indices in input order).
    """
    hit_ms, deltas, fever, section = plan.hit_ms, plan.delta, plan.fever, plan.section
    witnesses = (min(sec.fever_end, len(plan)) - 1 for sec in sections)
    cutoffs = {section[w]: plan.fever_ends[w] for w in witnesses if w in plan.fever_ends}
    offset_hits = sorted((plan.input_order[index], index) for index in np.flatnonzero(deltas).tolist())
    last_fever, scanned = None, 0
    for position, index in offset_hits:
        while scanned < position:  # the last fever input before this one
            if fever[ordered[scanned]]:
                last_fever = ordered[scanned]
            scanned += 1
        bands = plan.bands[index]
        delta = deltas[index]
        if not plan.great[index]:
            low, high = bands.perfect
        else:
            low, high = bands.early_great if delta <= bands.early_great[1] else bands.late_great
        safe = _frame_safe_latest_ms(high)
        if not delta > safe >= low:
            continue
        previous = ordered[position - 1] if position else None
        if fever[index] and not (previous is not None and fever[previous]):
            continue
        earliest_ms = -math.inf
        if previous is not None:
            earliest_ms = hit_ms[previous] + deltas[previous] + FRAME_MARGIN_MS
        if not fever[index] and last_fever is not None:
            earliest_ms = max(earliest_ms, cutoffs.get(section[last_fever], math.inf) + FRAME_MARGIN_MS)
        if hit_ms[index] + safe >= earliest_ms:
            deltas[index] = safe


def _apply_schedule_fever(plan: NotePlan, ordered: Sequence[int], sections: Sequence[_Section]) -> None:
    """Fever membership from the input order (note indices) and each section's duration."""
    cursor = 0
    active_until_ms: float | None = None
    for index in ordered:
        event_ms = plan.hit_ms[index] + plan.delta[index]
        if active_until_ms is not None and event_ms >= active_until_ms:
            active_until_ms = None
        if cursor < len(sections) and sections[cursor].activation == index:
            if active_until_ms is not None:
                raise UnplayableTrace("note_graph: a planned activation lands while fever is still active")
            active_until_ms = event_ms + sections[cursor].fever_duration_ms
            cursor += 1
        plan.fever[index] = active_until_ms is not None
    if cursor != len(sections):
        raise UnplayableTrace("note_graph: the input order does not reach every planned activation")


def _plan_endpoint_early_perfects(
    plan: NotePlan, sec: _Section, cutoff_ms: float, skip_range: tuple[int, int] | None
) -> None:
    """Issue #42: a fever note at or after the cutoff is in fever only because it is hit early. It is planned at the
    center of its legal in-fever hits, at or after the previous planned hit, or at that floor when no room is left.
    Great selectors have no timing yet and early-Great tail notes (`skip_range`) get theirs below."""
    upper_hit = _strictly_before(cutoff_ms)
    prev_hit = -math.inf
    for j in range(max(0, sec.activation), min(sec.fever_end, len(plan))):
        if skip_range is not None and skip_range[0] <= j < skip_range[1]:
            continue
        delta, hit = plan.delta[j], plan.hit_ms[j]
        if delta is None:
            continue
        if plan.activation_witness[j] or hit < cutoff_ms:
            prev_hit = max(prev_hit, hit + delta)
            continue
        lo_hit = max(hit + plan.bands[j].perfect[0], prev_hit)
        shown_hit = lo_hit if lo_hit >= upper_hit else _center(lo_hit, upper_hit)
        plan.delta[j] = shown_hit - hit
        prev_hit = shown_hit


def _plan_early_great_tail(plan: NotePlan, sec: _Section, cutoff_ms: float, early_range: tuple[int, int]) -> None:
    """Issue #68: the early-Great notes that extend a fever window, at the center of their in-fever early-Great hits."""
    start, end = early_range
    strict_cutoff = _strictly_before(cutoff_ms)
    prev_hit = -math.inf
    for j in range(max(0, sec.activation), min(end, len(plan))):
        hit, delta = plan.hit_ms[j], plan.delta[j]
        if j < start:
            if delta is not None:
                prev_hit = max(prev_hit, hit + delta)
            continue
        if not plan.fever[j] or plan.activation_witness[j]:
            continue
        great_low, great_high = plan.bands[j].early_great
        lo_hit = max(hit + great_low, prev_hit)
        hi_hit = hit + min(great_high, strict_cutoff - hit)
        if lo_hit > hi_hit:
            raise UnplayableTrace(f"note_graph: early-Great fever-end note {j} has no hit left in fever")
        shown_hit = _center(lo_hit, hi_hit)
        plan.great[j] = True
        plan.delta[j] = shown_hit - hit
        prev_hit = shown_hit


def _plan_tight_cutoff_cluster(plan: NotePlan, sec: _Section, cutoff_ms: float) -> None:
    """Issue #64: when a section's last chart-time cluster has a cutoff tighter than its Perfect band, all of it is
    planned at one offset inside both. Comfortable ends keep their chart time."""
    a = sec.activation
    last_fever = min(sec.fever_end, len(plan)) - 1
    if last_fever < a:
        return
    if last_fever not in plan.fever_ends or plan.activation_witness[last_fever]:
        return
    hit = plan.hit_ms[last_fever]
    if hit >= cutoff_ms:
        return
    strict_cutoff = _strictly_before(cutoff_ms)
    if strict_cutoff - hit >= plan.tap_latest_perfect:
        return
    if plan.great[last_fever]:
        raise UnplayableTrace(f"note_graph: no hit plays fever-end note {last_fever}, a Great at a tight cutoff")

    cluster: list[int] = []
    for j in range(max(0, a), last_fever + 1):
        if not plan.fever[j] or plan.activation_witness[j] or not _same_chart_time(plan.hit_ms[j], hit):
            continue
        if plan.delta[j] is None or plan.great[j]:
            raise UnplayableTrace(f"note_graph: no hit plays fever-end note {j}, a Great at a tight cutoff")
        cluster.append(j)
    if not cluster:
        return

    cluster_lo, cluster_hi, latest_perfect = -math.inf, math.inf, math.inf
    for j in cluster:
        lo, hi = plan.bands[j].perfect
        latest_perfect = min(latest_perfect, hi)
        safe_hi = min(hi, strict_cutoff - plan.hit_ms[j])
        if lo > safe_hi:
            raise UnplayableTrace(f"note_graph: fever-end note {j} has no Perfect hit in fever")
        cluster_lo, cluster_hi = max(cluster_lo, lo), min(cluster_hi, safe_hi)
    if cluster_lo > cluster_hi:
        raise UnplayableTrace("note_graph: a fever-end cluster has no shared Perfect hit in fever")
    if cluster_hi >= latest_perfect:
        return
    shared = _center(cluster_lo, cluster_hi)
    for j in cluster:
        plan.delta[j] = shared


def _push_fever_exit_notes(plan: NotePlan, sec: _Section, cutoff_ms: float) -> None:
    """The mirror of the early endpoint: a plain Perfect the frontier excluded from fever by its latest legal hit, but
    whose chart time is still before the cutoff, is planned at that latest hit so the drain excludes it as the surface
    does (e.g. Raining Tacos (Easy) T1, where a note on its chart time scored 1,599 more than the card). Its float
    latest hit can sit a fraction of a millisecond before the cutoff and still land past the replay's own fever end, so
    the physical replay, not this pass, is the check."""
    j = sec.fever_end
    while 0 <= j < len(plan):
        if plan.hit_ms[j] >= cutoff_ms:
            break
        if plan.activation_witness[j] or plan.fever[j] or plan.delta[j] is None or plan.great[j]:
            break
        plan.delta[j] = plan.bands[j].perfect[1]
        j += 1


def _mark_fever_end(plan: NotePlan, sec: _Section, cutoff_ms: float, early_range: tuple[int, int] | None) -> None:
    """A section's fever-end witness (its last fever note, carrying the cutoff) and, on precise, the endpoint hits that
    keep its last fever notes inside the cutoff and push the first note past it out."""
    last_fever = min(sec.fever_end, len(plan)) - 1
    if sec.activation <= last_fever:
        plan.fever_ends[last_fever] = cutoff_ms
        plan.section[last_fever] = sec.number
    if not plan.precise:
        return
    _plan_endpoint_early_perfects(plan, sec, cutoff_ms, early_range)
    if early_range is not None:
        _plan_early_great_tail(plan, sec, cutoff_ms, early_range)
    _plan_tight_cutoff_cluster(plan, sec, cutoff_ms)
    _push_fever_exit_notes(plan, sec, cutoff_ms)


def _mark_section_fever(plan: NotePlan, sec: _Section) -> None:
    for j in range(max(0, sec.activation), min(sec.fever_end, len(plan))):
        plan.fever[j] = True
        if plan.section[j] == 0:
            plan.section[j] = sec.number


def timeline_frontier_plan(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> NotePlan:
    """BASE plan from a selected timeline-frontier witness trace."""
    plan = _new_plan(total_notes, timestamps, note_types, lanes, timing_mode, perfect_time)
    sections = _sections(frontier_trace)
    for sec in sections:
        _mark_section_fever(plan, sec)
        if plan.precise:
            plan.delta[sec.activation] = sec.hit_offset_ms
            plan.activation_witness[sec.activation] = True
            plan.section[sec.activation] = sec.number
        _mark_fever_end(plan, sec, sec.cutoff_ms, None)
    if plan.precise:
        # The frontier prices a delayed activation clock, but the replay plays physical inputs in time order: every
        # following input that would land before the activation is delayed to it, or a chord sibling on its chart time
        # would fill the bar first.
        constraints = _plan_base_preactivation_schedules(plan, sections)
        constraints.extend(_hold_followers_after_activation(plan, sections, fg_schedule=False))
        ordered = _assign_input_order(plan, constraints)
        _plan_frame_safe_hits(plan, ordered, sections)
    return plan


def timeline_frontier_note_graph(**trace: Any) -> list[dict[str, Any]]:
    return timeline_frontier_plan(**trace).graph()


def base_note_graph(
    *,
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    is_fever_mask: Sequence[bool] | np.ndarray,
) -> list[dict[str, Any]]:
    """BASE graph of a row without a trace: every note Perfect on its chart time, with the fever of `is_fever_mask`
    (solver.fever_timeline.calculate_fever_timeline_indices from the row's stats)."""
    hit_ms = _chart_times_ms(total_notes, timestamps)
    if len(hit_ms) < total_notes or len(is_fever_mask) < total_notes:
        raise ValueError("base_note_graph: timestamps/is_fever_mask shorter than total_notes")
    n = total_notes
    fever = np.asarray(is_fever_mask).astype(bool)[:n].tolist()
    return NotePlan(hit_ms, [0.0] * n, [False] * n, fever, [False] * n, [0] * n, list(range(n)), {}).graph()


def force_greats_plan(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    timing_mode: str,
    perfect_time: int,
) -> NotePlan:
    """FG plan from the persisted witness trace (the per-loadout ForceGreats.frontier_trace). Each section carries a
    sequential region of the chart: a fever window [activation, fever_end), a forced run of Great selectors, and the
    activation note, a Great when its judgment is late_great. Every other note is a Perfect; a note may be both fever
    and Great."""
    plan = _new_plan(total_notes, timestamps, note_types, lanes, timing_mode, perfect_time)
    sections = _sections(frontier_trace)
    n = len(plan)

    # Labels are global inputs to every activation cap: materialize the whole map before planning any witness, or an
    # earlier section could read a Great owned by a later section as Perfect and reject the producer's schedule.
    for sec in sections:
        for j in range(max(0, sec.forced_run_start), min(sec.forced_run_start + sec.forced_run_count, n)):
            plan.great[j] = True
            plan.delta[j] = None
            if plan.section[j] == 0:
                plan.section[j] = sec.number
        _mark_section_fever(plan, sec)
        if sec.judgment == "late_great":
            plan.great[sec.activation] = True

    for sec in sections:
        a = sec.activation
        cutoff_ms = sec.cutoff_ms
        if plan.precise and (sec.judgment == "late_great" or sec.hit_offset_ms != 0.0):
            plan.delta[a] = _activation_delta_ms(plan, sec)
            plan.activation_witness[a] = True
            plan.section[a] = sec.number
            cutoff_ms = plan.hit_ms[a] + plan.delta[a] + sec.fever_duration_ms
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
    ordered = _assign_input_order(plan, constraints)
    if plan.precise:
        _apply_schedule_fever(plan, ordered, sections)
        _plan_frame_safe_hits(plan, ordered, sections)
    return plan


def force_greats_note_graph(**trace: Any) -> list[dict[str, Any]]:
    return force_greats_plan(**trace).graph()


def _head_bits(words: Sequence[int], head_limit: int) -> np.ndarray:
    """Whether each of the first head_limit notes is set in a 4x32-bit head mask."""
    return np.unpackbits(np.asarray(words, dtype="<u4").view(np.uint8), bitorder="little")[:head_limit].astype(bool)


def reconcile_base_plan(plan: NotePlan, response_surface: Sequence[int]) -> None:
    """Fail loudly unless a Base plan exactly matches its selected score surface."""
    surface = tuple(int(value) for value in response_surface)
    if len(surface) != 6:
        raise ValueError("Base response surface must contain four head words and two body counts")
    head_limit = min(len(plan), _HEAD_NOTES)
    fever = np.array(plan.fever, dtype=bool)
    surface_head = _head_bits(surface[:4], head_limit)
    if not np.array_equal(fever[:head_limit], surface_head):
        raise ValueError(
            "Base note-graph head fever positions differ from the selected response surface: "
            f"{set(np.flatnonzero(fever[:head_limit] != surface_head).tolist())}"
        )
    graph_body_fever = int(np.count_nonzero(fever[_HEAD_NOTES:]))
    body_total = max(0, len(plan) - _HEAD_NOTES)
    if graph_body_fever != surface[4] or body_total - graph_body_fever != surface[5]:
        raise ValueError(
            "Base note-graph body counts differ from the selected response surface: "
            f"graph=({graph_body_fever}, {body_total - graph_body_fever}) surface=({surface[4]}, {surface[5]})"
        )


def reconcile_force_greats_plan(
    plan: NotePlan,
    *,
    fever_words: Sequence[int],
    great_words: Sequence[int],
    body_fever: int,
    body_great: int,
    body_fever_great: int,
) -> None:
    """Fail loudly unless an FG plan exactly matches its surface: the head notes' fever and Great bitmasks, the body
    notes' fever, Great and fever-Great counts."""
    head_limit = min(len(plan), _HEAD_NOTES)
    fever, great = np.array(plan.fever, dtype=bool), np.array(plan.great, dtype=bool)
    for name, notes, words in (("fever", fever, fever_words), ("great", great, great_words)):
        surface_head = _head_bits(words, head_limit)
        if not np.array_equal(notes[:head_limit], surface_head):
            positions = set(np.flatnonzero(notes[:head_limit] != surface_head).tolist())
            raise ValueError(f"FG note-graph head {name} positions != surface mask: {positions}")

    g_body_fever = int(np.count_nonzero(fever[_HEAD_NOTES:]))
    g_body_great = int(np.count_nonzero(great[_HEAD_NOTES:]))
    g_body_fg = int(np.count_nonzero(fever[_HEAD_NOTES:] & great[_HEAD_NOTES:]))
    if g_body_fever != int(body_fever):
        raise ValueError(f"FG note-graph body_fever {g_body_fever} != surface {int(body_fever)}")
    if g_body_great != int(body_great):
        raise ValueError(f"FG note-graph body_great {g_body_great} != surface {int(body_great)}")
    if g_body_fg != int(body_fever_great):
        raise ValueError(f"FG note-graph body_fever_great {g_body_fg} != surface {int(body_fever_great)}")
