from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import lru_cache
from math import ceil
from typing import Any, NamedTuple

import numpy as np

from gear_optimizer.solver.scoring.fg_policy import FGSongInputs
from gear_optimizer.frontier.producer_batch import action_table, early_exit_min_fill, song_arrays
from gear_optimizer.frontier.types import FgResponseSurface
from .activation_witness import activation_schedule_witnesses, exact_label_hit_intervals
from .section_kernels import SectionContext, fever_end, section_rows


_EMPTY_SURFACE = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
_action_table = lru_cache(maxsize=64)(action_table)
_TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS = 262_144


class UnplayableTrace(ValueError):
    """A trace whose judgments no legal hit timing realizes in the exact input order."""


class _SectionTable(NamedTuple):
    """A section start's options in emission order (section_kernels.section_rows): their response-surface edges, each
    its head's fever and Great masks in two 64-bit words each, then its body counts, and the rows and witness hit windows
    an accepted one reads."""

    section_start: int
    edges: np.ndarray
    rows: np.ndarray
    hits: np.ndarray


@dataclass(slots=True)
class FgTraceEdgeOptionsCache:
    """One song's section tables per state, bounded (a full cache starts over: a rebuild is identical). A cache belongs
    to the one song it was made for: its keys do not name the song."""

    tables: dict[Any, _SectionTable] = field(default_factory=dict)
    options: int = 0

    def add(self, key: tuple[Any, ...], table: _SectionTable) -> None:
        if self.options + len(table.rows) > _TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS:
            self.tables.clear()
            self.options = 0
        self.tables[key] = table
        self.options += len(table.rows)


def _edge_of_surface(surface: FgResponseSurface) -> tuple[int, ...]:
    """A surface as the columns of _SectionTable.edges."""
    head = [surface[word] | surface[word + 1] << 32 for word in (0, 2, 4, 6)]
    return (*head, surface.body_fever, surface.body_great, surface.body_fever_great)


def _fitting_edges(edges: np.ndarray, remaining: tuple[int, ...]) -> np.ndarray:
    """The rows of `edges` that fit in the surface `remaining`: their notes in it and their counts within it."""
    left = np.array(remaining, dtype=np.uint64)
    return np.flatnonzero(
        (np.bitwise_or.reduce(edges[:, :4] & ~left[:4], axis=1) == 0) & (edges[:, 4:] <= left[4:]).all(axis=1)
    )


def _subtract_edge(remaining: tuple[int, ...], edge: list[int]) -> tuple[int, ...]:
    return (
        remaining[0] & ~edge[0], remaining[1] & ~edge[1], remaining[2] & ~edge[2], remaining[3] & ~edge[3],
        remaining[4] - edge[4], remaining[5] - edge[5], remaining[6] - edge[6],
    )


def _fever_start_fields(*, start_time: float, chart_time: float, activation_idx: int, late_great: bool) -> dict[str, Any]:
    if late_great:
        source, note_idx = "activation_late_great", activation_idx
    elif start_time != chart_time:
        source, note_idx = "precise", activation_idx
    else:
        source, note_idx = "chart_perfect", None
    return {"fever_start_source": source, "fever_start_note_index": note_idx, "fever_start_hit_ms": start_time * 1000.0}


def _float32_order(value: float) -> int:
    """A float32's place on the number line: neighbouring float32 values are neighbouring orders."""
    bits = int(np.asarray(np.float32(value), dtype=np.float32).view(np.uint32))
    return 0x80000000 - bits if bits & 0x80000000 else bits + 0x80000000


def _hit_from_order(order: int) -> float:
    bits = order - 0x80000000 if order >= 0x80000000 else 0x80000000 - order
    return float(np.asarray(np.uint32(bits), dtype=np.uint32).view(np.float32))


def _first_order(first: int, last: int, holds: Callable[[float], bool]) -> int:
    """The first order in [first, last] whose hit satisfies the monotone `holds`; last + 1 if none does."""
    while first <= last:
        middle = (first + last) // 2
        if holds(_hit_from_order(middle)):
            last = middle - 1
        else:
            first = middle + 1
    return first


def _centered_hit_window_for_exit(
    n: int, activation_idx: int, legal_lo: float, legal_hi: float, real_fever_time: float, target_end_idx: int,
    perfect_floor_timestamps: np.ndarray, exit_ceiling_timestamps: np.ndarray | None = None,
) -> tuple[float, float, float]:
    """The activation hit, centered in [legal_lo, legal_hi], whose fever ends at `target_end_idx`: by default the end
    the notes reach at their earliest hits (the floor). With `exit_ceiling_timestamps` (an early exit) the notes before
    the target still reach inside the cutoff at their earliest hits, and the cutoff stays at or before the exit ceiling
    of the target, so the target and every later note can be hit past it."""
    target = max(0, min(target_end_idx, n))

    def exit_index(hit: float) -> int:
        # The same earliest-Perfect floor the surface boundary used (issue #42), so the witness reproduces the end.
        return fever_end(hit, activation_idx, perfect_floor_timestamps, real_fever_time, n)

    def reaches_target(hit: float) -> bool:
        return exit_index(hit) >= target

    def within_target(hit: float) -> bool:
        if exit_ceiling_timestamps is None:
            return exit_index(hit) <= target
        return float(np.float32(hit + real_fever_time)) <= float(exit_ceiling_timestamps[target])

    lowest, highest = float(np.float32(legal_lo)), float(np.float32(legal_hi))
    if lowest < legal_lo:
        lowest = float(np.nextafter(np.float32(lowest), np.float32(np.inf)))
    if highest > legal_hi:
        highest = float(np.nextafter(np.float32(highest), np.float32(-np.inf)))
    min_order, max_order = _float32_order(lowest), _float32_order(highest)
    first_order = _first_order(min_order, max_order, reaches_target)
    last_order = _first_order(min_order, max_order, lambda hit: not within_target(hit)) - 1
    if first_order > last_order:
        # The producer prices a section's end at its latest hit in float64, which can lie between two float32 hits.
        raise UnplayableTrace(
            f"no float32 hit of note {activation_idx} in [{legal_lo:.9f}, {legal_hi:.9f}] s ends its fever at note {target}"
        )

    first_hit, last_hit = _hit_from_order(first_order), _hit_from_order(last_order)
    midpoint = _float32_order(float(np.float32((first_hit + last_hit) * 0.5)))
    for order in (min(max(midpoint, first_order), last_order), (first_order + last_order) // 2):
        hit = _hit_from_order(order)
        if reaches_target(hit) and within_target(hit):
            return hit, first_hit, last_hit
    raise ValueError("centered FG trace witness changed the response surface")


def _stored_section(table: _SectionTable, index: int, context: SectionContext) -> dict[str, Any]:
    """An accepted option as a stored trace section: with its centered activation witness and exact schedule."""
    k, next_state, activation_idx, late_great, run_start, run_count, early_great_start, early_great_end, target_end, \
        early_exit = table.rows[index].tolist()
    section_start = table.section_start
    timestamps, real_fever_time = context.timestamps, context.real_fever_time
    n = timestamps.shape[0]
    legal_lo, legal_hi = table.hits[index].tolist()
    hit, hit_lo, hit_hi = _centered_hit_window_for_exit(
        n, activation_idx, legal_lo, legal_hi, real_fever_time, target_end, context.perfect_floor_timestamps,
        context.exit_ceiling_timestamps if early_exit else None,
    )
    run_end = min(n, run_start + run_count)
    is_great = np.zeros(n, dtype=np.bool_)
    is_great[run_start:run_end] = True
    if late_great:
        is_great[activation_idx] = True
    labels = exact_label_hit_intervals(
        is_great=is_great,
        timestamps=timestamps,
        perfect_floor_timestamps=context.perfect_floor_timestamps,
        perfect_candidate_timestamps=context.perfect_candidate_timestamps,
        great_floor_timestamps=context.great_floor_timestamps,
        great_candidate_timestamps=context.great_candidate_timestamps,
    )
    preactivation_event_count = activation_idx - section_start
    preactivation_great_count = max(0, min(activation_idx, run_end) - max(section_start, run_start))
    schedule_rows = activation_schedule_witnesses(
        labels=labels,
        lanes=context.lanes,
        activation_index=activation_idx,
        activation_hit_timestamp=hit,
        fever_fill_denom=context.fever_fill_denom,
        section_start=section_start,
        predecessor_hit_timestamp=None if section_start == 0 else float(context.perfect_floor_timestamps[section_start - 1]),
        required_signature=(2 * preactivation_event_count - preactivation_great_count, preactivation_event_count),
    )
    if len(schedule_rows) != 1:
        raise ValueError("FG accepted edge has no unique exact lane-prefix witness for its scored surface")
    schedule = schedule_rows[0]
    chart_time = float(timestamps[activation_idx])
    body_fever, body_great, body_fever_great = table.edges[index, 4:].tolist()
    return {
        "next_state": next_state,
        "activation_index": activation_idx,
        "activation_ms": chart_time * 1000.0,
        "activation_judgment": "late_great" if late_great else "perfect",
        "activation_hit_ms": hit * 1000.0,
        "activation_hit_offset_ms": (hit - chart_time) * 1000.0,
        "activation_hit_window_lower_ms": hit_lo * 1000.0,
        "activation_hit_window_upper_ms": hit_hi * 1000.0,
        "activation_hit_offset_lower_ms": (hit_lo - chart_time) * 1000.0,
        "activation_hit_offset_upper_ms": (hit_hi - chart_time) * 1000.0,
        "activation_hit_window_width_ms": max(0.0, (hit_hi - hit_lo) * 1000.0),
        "forced_start_index": section_start,
        "forced_run_start_index": run_start,
        "forced_run_count": run_count,
        "fever_end_index": next_state,
        "fever_end_ms": None if next_state >= n else float(timestamps[next_state]) * 1000.0,
        "fever_duration_ms": real_fever_time * 1000.0,
        # The cutoff belongs to the materialized activation witness, not another legal point in
        # its interval. Endpoint guidance may move boundary notes earlier to realize the selected
        # surface, but activation and cutoff must describe one physical play.
        "fever_window_end_ms": (hit + real_fever_time) * 1000.0,
        **_fever_start_fields(
            start_time=hit, chart_time=chart_time, activation_idx=activation_idx, late_great=bool(late_great)
        ),
        # Issue #44: the early-Great tail [early_great_start, early_great_end) -- boundary notes
        # this section pulls into fever as Greats (default -1/-1 = none). The per-note early-Great
        # hit offsets are stamped by the note-graph layer (like #42's endpoint-early Perfect hits).
        "early_great_start": early_great_start,
        "early_great_end": early_great_end,
        "activation_schedule_schema_version": 1,
        "preactivation_order": [int(index) for index in schedule.preactivation_order],
        "preactivation_lane_prefixes": [
            {"lane": int(row.lane), "count": len(row.note_indices)} for row in schedule.lane_prefixes
        ],
        "preactivation_fill_half_units": schedule.preactivation_fill_half_units,
        "preactivation_event_count": schedule.preactivation_event_count,
        "preactivation_great_count": schedule.preactivation_great_count,
        "forced_count": k,
        "body_fever": body_fever,
        "body_great": body_great,
        "body_fever_great": body_fever_great,
    }


def section_table(
    context: SectionContext, actions: list[int], fills: list[int], forced: list[int], state: int, first: bool
) -> _SectionTable:
    """The candidate fever sections after state `state` (the first section when `first`), per action of the frontier's
    action table (its `fills` and `forced` counts for this kind of section)."""
    rows, edges, hits = section_rows(
        context, np.asarray(actions, dtype=np.int64), np.asarray(fills, dtype=np.int64),
        np.asarray(forced, dtype=np.int64), first, state,
    )
    return _SectionTable(0 if first else state + 1, edges, rows, hits)


def reconstruct_force_greats_response_trace(
    *,
    inputs: FGSongInputs,
    non_fever_base: int,
    target_surface: FgResponseSurface,
    raw_fever_fill: float,
    real_fever_time: float,
    edge_options_cache: FgTraceEdgeOptionsCache | None = None,
) -> tuple[dict[str, Any], ...]:
    """The section trace whose edges add up to ``target_surface``: per fever section its activation, forced Greats,
    exact witness and fever end, as the producer priced them for the song's FG ``inputs``."""
    n = len(inputs.timestamps)
    if n <= 0 or target_surface == _EMPTY_SURFACE:
        return ()
    raw_fever_fill, real_fever_time = float(raw_fever_fill), float(real_fever_time)
    use_forced_great_timing = bool(inputs.use_forced_great_timing)
    ts, perfect_ts, great_ts, floor_ts, great_floor_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr = song_arrays(
        inputs.timestamps, inputs.perfect_candidates, inputs.great_candidates, inputs.perfect_floor,
        inputs.great_floor, inputs.late_great_floor, inputs.exit_ceiling, inputs.lanes,
    )
    if max(1, ceil(raw_fever_fill)) < early_exit_min_fill(floor_ts, perfect_ts):
        exit_ceiling_ts = np.full_like(exit_ceiling_ts, -np.inf)  # as the search: no early exits at this fill
    context = SectionContext(
        ts, floor_ts, perfect_ts, great_floor_ts, great_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr,
        raw_fever_fill, real_fever_time, use_forced_great_timing,
    )

    # The ordered edge list is independent of the target surface, so the up-to-51 surfaces of one song reuse it.
    shared_tables = edge_options_cache if edge_options_cache is not None else FgTraceEdgeOptionsCache()
    table_prefix = (non_fever_base, raw_fever_fill, real_fever_time, use_forced_great_timing)
    memo: set[tuple[int, bool, tuple[int, ...]]] = set()
    unplayable: list[UnplayableTrace] = []

    def _section_table_at(state: int, first: bool) -> _SectionTable:
        key = (*table_prefix, state, first)
        table = shared_tables.tables.get(key)
        if table is None:
            actions, later_fill, first_fill, later_forced, first_forced = _action_table(
                raw_fever_fill=raw_fever_fill, non_fever_base=non_fever_base, use_forced_great_timing=use_forced_great_timing
            )
            fills, forced = (first_fill, first_forced) if first else (later_fill, later_forced)
            table = section_table(context, actions, fills, forced, state, first)
            shared_tables.add(key, table)
        return table

    def _search(state: int, first: bool, remaining: tuple[int, ...]) -> tuple[dict[str, Any], ...] | None:
        key = (state, first, remaining)
        if key in memo:
            return None
        table = _section_table_at(state, first)
        for index in _fitting_edges(table.edges, remaining).tolist():
            left = _subtract_edge(remaining, table.edges[index].tolist())
            next_state = int(table.rows[index, 1])
            if not any(left):
                tail = ()
            elif next_state >= n or ((left[0] | left[2]) | (left[1] | left[3]) << 64) & ((2 << next_state) - 1):
                continue  # the next section starts past next_state: no section can take a head note before it
            else:
                tail = _search(next_state, False, left)
                if tail is None:
                    continue
            try:
                # The centered witness is computed only here, for sections accepted into the final trace.
                return (_stored_section(table, index, context), *tail)
            except UnplayableTrace as exc:  # no hit plays this section: the next option may price the same surface
                unplayable.append(exc)
        memo.add(key)
        return None

    trace = _search(0, True, _edge_of_surface(target_surface))
    if trace is None and unplayable:
        raise unplayable[0]
    if trace is None:
        raise ValueError("could not reconstruct FG response surface trace")
    return tuple({**row, "section": idx + 1} for idx, row in enumerate(trace))


def reconstruct_base_trace(
    inputs: FGSongInputs,
    *,
    head_words: tuple[int, int, int, int],
    body_fever: int,
    raw_fever_fill: float,
    real_fever_time: float,
) -> tuple[dict, ...]:
    """The physical trace of a Base surface: the FG reconstruction of the same surface without Greats, so without
    forced-Great timing (and its late-Great floor)."""
    return reconstruct_force_greats_response_trace(
        inputs=replace(inputs, late_great_floor=None, use_forced_great_timing=False),
        non_fever_base=0,
        target_surface=FgResponseSurface(*head_words, 0, 0, 0, 0, body_fever, 0, 0),
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
    )
