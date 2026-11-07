"""A stored build's note plan: per note, what the timing graph draws and the replay plays.

A plan keeps its notes as columns (NotePlan); NotePlan.graph() writes each note as the dict the timing graph reads:
note_index, hit_time_ms (its chart time), note_result ("Perfect" or "Great"), delta_ms (its planned hit offset, + late),
input_order (its place in the input stream), fever, is_activation_witness, is_fever_end_witness, fever_end_ms (the fever
cutoff, on a section's last fever note) and section.

Two plans per loadout, rebuilt from the persisted frontier trace, so nothing per note is stored:
  * timeline_frontier_plan, Base: every note Perfect, in chart order.
  * force_greats_plan, Force Greats: per-note Perfect or Great, in the order the trace schedules each section.
base_note_graph draws a fever mask with every hit on its chart time, for a Base row that has no trace.

The trace decides each note's judgment and the order that matters; hit_schedule times the inputs, at the hit windows of
the build's Perfect Time (the frontier behind them used the base ones). The timing mode decides how far: on "precise" every
hit may move, on "non-precise" Perfects stay on time. A plan no frame timing plays raises UnplayableTrace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np

from gear_optimizer.trace.hit_schedule import Inputs, input_order, schedule_hits
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

# The combo ramp: the score surface keeps the judgment and fever of each of these first notes.
_HEAD_NOTES = 100
# Every legal hit lies within this of its chart time: a note this far past an activation cannot go first.
_LATEST_PRESS_MS = 200.0


class _Section(NamedTuple):
    """The fields of a stored trace section that a plan reads."""

    number: int
    activation: int
    fever_end: int
    judgment: str  # how the activation note is hit: "perfect" or "late_great"
    hit_offset_ms: float
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
def _tap_and_tail_bands(perfect_time: int) -> np.ndarray:
    """(tap or tail, Perfect, early Great or late Great, first or last) offsets."""
    return np.array([
        _Bands(*((float(band.earliest), float(band.latest)) for band in judgment_bounds(scale, perfect_time)))
        for scale in (1, HELD_TAIL_WINDOW_SCALE)
    ])


@dataclass(slots=True)
class NotePlan:
    """A plan's notes as columns: chart time, planned offset, Great, fever, activation witness, section and place in the
    input stream; `fever_ends`, the fever-end witnesses and their cutoffs. A plan being built also reads the notes' lanes and
    their bands (note, Perfect or early or late Great, first or last) at the build's Perfect Time."""

    hit_ms: np.ndarray
    delta: np.ndarray
    great: np.ndarray
    fever: np.ndarray
    activation_witness: np.ndarray
    section: np.ndarray
    input_order: np.ndarray
    fever_ends: dict[int, float]
    is_tail: np.ndarray | None = None
    lanes: np.ndarray | None = None
    band_ms: np.ndarray | None = None
    precise: bool = False

    def __len__(self) -> int:
        return len(self.hit_ms)

    def graph(self) -> list[dict[str, Any]]:
        """The plan as the timing graph reads it, a dict per note."""
        columns = (self.hit_ms, self.delta, self.great, self.fever, self.activation_witness, self.section, self.input_order)
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
                zip(*(column.tolist() for column in columns))
            )
        ]


def _chart_times_ms(total_notes: int, timestamps: Sequence[float] | np.ndarray) -> np.ndarray:
    """Chart times in the game's whole ms: float32 seconds carry noise that could invert a tie."""
    return np.floor(np.asarray(timestamps, dtype=np.float64).reshape(-1)[:total_notes] * 1000.0 + 0.5)


def _empty_plan(hit_ms: np.ndarray, **chart: Any) -> NotePlan:
    """A plan of these chart times: every note a Perfect on time, outside fever, in chart order."""
    n = len(hit_ms)
    return NotePlan(
        hit_ms, np.zeros(n), np.zeros(n, dtype=bool), np.zeros(n, dtype=bool), np.zeros(n, dtype=bool),
        np.zeros(n, dtype=np.int64), np.arange(n), {}, **chart,
    )


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
    is_tail = np.asarray(note_types).reshape(-1) == HELD_TAIL_TYPE
    lane_ids = np.asarray(lanes, dtype=np.int64).reshape(-1)
    if not len(hit_ms) == len(is_tail) == len(lane_ids) == total_notes:
        raise ValueError("note_graph: timestamps, note_types and lanes must match total_notes")
    return _empty_plan(
        hit_ms,
        is_tail=is_tail,
        lanes=lane_ids,
        band_ms=_tap_and_tail_bands(perfect_time)[is_tail.astype(np.int64)],
        precise=timing_mode != "non-precise",
    )


def _early_greats(plan: NotePlan, sections: Sequence[_Section]) -> np.ndarray:
    """Non-Precise, where Perfects stay on time: the Greats that go early before the input order is known, as they go ahead
    of notes before them in the chart. They are the Greats ahead of a chord's first Perfect, and a Great a late hit would
    take within a frame margin of its lane's next note, when its lane's last note leaves it more room early. No early hit
    crosses an activation or a wasted note (_anchor_links)."""
    n = len(plan)
    if plan.precise or not n:
        return np.zeros(n, dtype=bool)
    hit_ms, great, lanes, band_ms = plan.hit_ms, plan.great, plan.lanes, plan.band_ms
    late_ms = hit_ms + np.where(great, band_ms[:, 2, 0], 0.0)
    next_late_ms, from_last = np.full(n, np.inf), np.full(n, np.inf)
    for lane in np.unique(lanes):
        notes = np.flatnonzero(lanes == lane)
        next_late_ms[notes[:-1]] = late_ms[notes[1:]]
        from_last[notes[1:]] = np.diff(hit_ms[notes])
    chord = np.cumsum(np.r_[0, np.diff(hit_ms) != 0.0])
    first_perfect = np.full(chord[-1] + 1, n, dtype=np.int64)
    np.minimum.at(first_perfect, chord[~great], np.flatnonzero(~great))
    room_late, room_early = next_late_ms - late_ms, from_last + band_ms[:, 1, 1]
    early = (room_late < FRAME_MARGIN_MS) & (room_early > room_late)
    early |= (np.arange(n) < first_perfect[chord]) & (first_perfect[chord] < n)
    early &= great
    early[[sec.activation for sec in sections]] = False
    for sec in sections:
        for anchor in (sec.activation, min(sec.fever_end, n - 1)):
            early[anchor + 1 :] &= (hit_ms + band_ms[:, 1, 1] - FRAME_MARGIN_MS)[anchor + 1 :] >= hit_ms[anchor]
    return early


def _ranked_times_ms(plan: NotePlan, early: np.ndarray) -> np.ndarray:
    """Each note's place among the inputs free to go in either order: its chart time, a Great past the ramp its first late
    hit and an early one its last early hit a frame margin clear."""
    hit_ms, band_ms = plan.hit_ms, plan.band_ms
    moved = plan.great.copy()
    moved[: _HEAD_NOTES] = False
    # The chord crossing the ramp is one tie.
    ramp_end = min(_HEAD_NOTES, len(plan))
    while 0 < ramp_end < len(plan) and hit_ms[ramp_end] == hit_ms[ramp_end - 1]:
        moved[ramp_end] = False
        ramp_end += 1
    times = hit_ms + np.where(moved, band_ms[:, 2, 0], 0.0)
    times[early] = (hit_ms + band_ms[:, 1, 1] - FRAME_MARGIN_MS)[early]
    return times


def _merged_order(plan: NotePlan, links: Sequence[tuple[int, int]], early: np.ndarray) -> np.ndarray:
    """The input order (hit_schedule.input_order), written into the plan; returns the note indices in input order."""
    pairs = np.array(links, dtype=np.int64).reshape(-1, 2)
    ranks = np.empty(len(plan), dtype=np.int64)
    ranks[np.argsort(_ranked_times_ms(plan, early), kind="stable")] = np.arange(len(plan))
    ordered = input_order(plan.lanes, ranks, pairs[:, 0], pairs[:, 1])
    if ordered.shape[0] != len(plan):
        raise UnplayableTrace("note_graph: exact input-order constraints contain a cycle")
    plan.input_order[ordered] = np.arange(len(plan))
    return ordered


def _schedule_hits(plan: NotePlan, order: np.ndarray, sections: Sequence[_Section], early: np.ndarray) -> None:
    """Give every input its time (hit_schedule): the plan keeps its judgments, input order and fever, so its score, and each
    input gets the room its frame needs. Non-Precise Perfects stay on their chart times."""
    hit_ms, great, band_ms = plan.hit_ms[order], plan.great[order], plan.band_ms[order]
    perfect_ms, early_ms, late_ms = band_ms[:, 0], band_ms[:, 1], band_ms[:, 2]
    fixed_early = early[order]
    activations = np.array([sec.activation for sec in sections], dtype=np.int64)
    activation = np.zeros(len(plan), dtype=bool)
    activation[plan.input_order[activations]] = True
    offsets_ms = np.where(great[:, None], late_ms, perfect_ms if plan.precise else 0.0)
    offsets_ms[fixed_early] = early_ms[fixed_early]
    may_go_early = great & ~fixed_early & ~activation
    positions = plan.input_order[activations].tolist()
    stopped, hits = schedule_hits(
        Inputs(
            hit_ms,
            hit_ms + offsets_ms[:, 0],
            hit_ms + offsets_ms[:, 1],
            (perfect_ms[:, 1] - offsets_ms[:, 1]) * ~great,
            np.where(may_go_early, hit_ms + early_ms[:, 0], np.inf),
            np.where(may_go_early, hit_ms + early_ms[:, 1], -np.inf),
            plan.lanes[order],
            plan.is_tail[order],
            great,
            plan.fever[order],
        ),
        np.array(
            [(at, stop, sec.fever_duration_ms) for at, stop, sec in zip(positions, [*positions[1:], len(plan)], sections)],
            dtype=np.float64,
        ).reshape(-1, 3),
        np.array([plan.precise and (sec.judgment == "late_great" or sec.hit_offset_ms != 0.0) for sec in sections], dtype=bool),
    )
    if stopped >= 0:
        raise UnplayableTrace(f"note_graph: note {order[stopped]}'s input has no frame of its own at any rate")
    plan.delta[order] = hits - hit_ms
    if plan.precise:
        for sec in sections:
            last_fever = min(sec.fever_end, len(plan)) - 1
            if last_fever in plan.fever_ends:
                plan.fever_ends[last_fever] = float(plan.hit_ms[sec.activation] + plan.delta[sec.activation]) + sec.fever_duration_ms


def _apply_schedule_fever(plan: NotePlan, ordered: np.ndarray, sections: Sequence[_Section]) -> None:
    """Fever membership from the input order: a window opens on its activation and closes on the first input of a note
    past it."""
    positions = plan.input_order[[sec.activation for sec in sections]].tolist()
    if positions != sorted(positions):
        raise UnplayableTrace("note_graph: the input order does not reach every planned activation")
    plan.fever[:] = False
    for sec, at, stop in zip(sections, positions, [*positions[1:], len(plan)]):
        past = np.flatnonzero(ordered[at + 1 : stop] >= sec.fever_end)
        plan.fever[ordered[at : at + 1 + past[0] if past.size else stop]] = True


def _mark_fever_end(plan: NotePlan, sec: _Section) -> None:
    """A section's fever-end witness: its last fever note, carrying the cutoff."""
    last_fever = min(sec.fever_end, len(plan)) - 1
    if sec.activation <= last_fever:
        plan.fever_ends[last_fever] = sec.cutoff_ms
        plan.section[last_fever] = sec.number


def _claim_notes(plan: NotePlan, notes: slice, sec: _Section) -> None:
    """The section takes these notes, those no section holds yet."""
    plan.section[notes] = np.where(plan.section[notes] == 0, sec.number, plan.section[notes])


def _mark_section_fever(plan: NotePlan, sec: _Section) -> None:
    window = slice(sec.activation, sec.fever_end)
    plan.fever[window] = True
    _claim_notes(plan, window, sec)


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
    """BASE plan from a selected timeline-frontier witness trace: every input in chart order."""
    plan = _new_plan(total_notes, timestamps, note_types, lanes, timing_mode, perfect_time)
    sections = _sections(frontier_trace)
    for sec in sections:
        _mark_section_fever(plan, sec)
        if plan.precise:
            plan.activation_witness[sec.activation] = True
            plan.section[sec.activation] = sec.number
        _mark_fever_end(plan, sec)
    if plan.precise:
        _schedule_hits(plan, np.arange(len(plan)), sections, np.zeros(len(plan), dtype=bool))
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
    plan = _empty_plan(hit_ms)
    plan.fever[:] = np.asarray(is_fever_mask).astype(bool)[:total_notes]
    return plan.graph()


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
    for sec in sections:
        run = slice(sec.forced_run_start, sec.forced_run_start + sec.forced_run_count)
        plan.great[run] = True
        _claim_notes(plan, run, sec)
        _mark_section_fever(plan, sec)
        if sec.judgment == "late_great":
            plan.great[sec.activation] = True

    early = _early_greats(plan, sections)
    links: list[tuple[int, int]] = []
    for sec in sections:
        a = sec.activation
        _mark_fever_end(plan, sec)
        if not plan.precise:
            links.extend(_anchor_links(plan, sec))
            continue
        if sec.judgment == "late_great" or sec.hit_offset_ms != 0.0:
            plan.activation_witness[a] = True
            plan.section[a] = sec.number
        # The section's early-Great tail notes: the Greats that extend its fever window.
        if sec.early_great_start >= 0 and sec.early_great_end >= 0:
            tail = slice(max(a, sec.early_great_start), min(sec.early_great_end, sec.fever_end))
            extending = plan.fever[tail] & ~plan.activation_witness[tail]
            plan.great[tail] |= extending
            early[tail] |= extending
        links.extend(_section_links(plan, sec))

    ordered = _merged_order(plan, links, early)
    if plan.precise:
        _apply_schedule_fever(plan, ordered, sections)
    _schedule_hits(plan, ordered, sections, early)
    return plan


def _anchor_links(plan: NotePlan, sec: _Section) -> list[tuple[int, int]]:
    """Non-Precise: the Greats near a section's activation and its wasted note stay on their side of them, as the bar fills
    in chart order."""
    hit_ms = plan.hit_ms
    links: list[tuple[int, int]] = []
    for anchor in (sec.activation, sec.fever_end):
        if anchor < len(plan):
            first, last = np.searchsorted(hit_ms, [hit_ms[anchor] - 2.0 * _LATEST_PRESS_MS, hit_ms[anchor] + 2.0 * _LATEST_PRESS_MS])
            for j in (first + np.flatnonzero(plan.great[first:last])).tolist():
                if j != anchor:
                    links.append((j, anchor) if j < anchor else (anchor, j))
    return links


def _section_links(plan: NotePlan, sec: _Section) -> list[tuple[int, int]]:
    """The input order a section schedules: the note before it, then its notes planned before the activation, in order,
    the activation, and each lane's next note after it."""
    a = sec.activation
    sequence = (*sec.preactivation_order, a)
    links = [] if sec.forced_start <= 0 else [(sec.forced_start - 1, sequence[0])]
    links.extend(zip(sequence, sequence[1:]))
    planned_first = frozenset(sequence)
    held_lanes: set[int] = set()
    stop = np.searchsorted(plan.hit_ms, plan.hit_ms[a] + 2.0 * _LATEST_PRESS_MS, side="right")
    for j, lane in enumerate(plan.lanes[sec.forced_start : stop].tolist(), sec.forced_start):
        if j not in planned_first and lane not in held_lanes:
            held_lanes.add(lane)
            links.append((a, j))
    return links


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
    surface_head = _head_bits(surface[:4], head_limit)
    if not np.array_equal(plan.fever[:head_limit], surface_head):
        raise ValueError(
            "Base note-graph head fever positions differ from the selected response surface: "
            f"{set(np.flatnonzero(plan.fever[:head_limit] != surface_head).tolist())}"
        )
    graph_body_fever = int(np.count_nonzero(plan.fever[_HEAD_NOTES:]))
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
    fever, great = plan.fever, plan.great
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
