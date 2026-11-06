from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from math import ceil
from typing import Any, NamedTuple

import numpy as np

from gear_optimizer.solver.scoring.fg_policy import FGSongInputs
from .activation_witness import activation_schedule_witnesses, exact_label_hit_intervals
from gear_optimizer.frontier.fill_crossing import server_fill_crossing_run
from gear_optimizer.frontier import producer_kernels as _rb_numba
from gear_optimizer.frontier.producer_batch import action_table, early_exit_min_fill, song_arrays
from gear_optimizer.frontier.types import FgResponseSurface


_EMPTY_SURFACE = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
_TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS = 8192
_TRACE_EDGE_OPTIONS_CACHE_MAX_STATES = 256


class UnplayableTrace(ValueError):
    """A trace whose judgments no legal hit timing realizes in the exact input order."""


@dataclass(slots=True)
class _SectionOptionStream:
    """A section start's options in emission order, built only as far as a trace search reads them (the search stops at
    the first option that completes its trace) and shared by every search of the song that reaches the state."""

    source: Iterator[dict[str, Any]] | None
    built: list[dict[str, Any]] = field(default_factory=list)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        index = 0
        while True:
            if index == len(self.built):
                option = None if self.source is None else next(self.source, None)
                if option is None:
                    self.source = None
                    return
                self.built.append(option)
            yield self.built[index]
            index += 1


@dataclass(slots=True)
class FgTraceEdgeOptionsCache:
    """One song's section options per state, bounded (eviction only rebuilds an identical stream). A cache belongs to
    the one song it was made for: its keys do not name the song."""

    _entries: dict[Any, _SectionOptionStream] = field(default_factory=dict)

    def get(self, key: tuple[Any, ...]) -> _SectionOptionStream | None:
        return self._entries.get(key)

    def put(self, key: tuple[Any, ...], options: _SectionOptionStream) -> None:
        while self._entries and (
            len(self._entries) >= _TRACE_EDGE_OPTIONS_CACHE_MAX_STATES
            or self.option_count + len(options.built) > _TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS
        ):
            self._entries.pop(next(iter(self._entries)))
        self._entries[key] = options

    @property
    def option_count(self) -> int:
        """The options the retained states have built (bounded at each insert, oldest state evicted first)."""
        return sum(len(entry.built) for entry in self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)


@dataclass(frozen=True, slots=True)
class _ActivationReachabilityContext:
    timestamps: np.ndarray
    perfect_floor_timestamps: np.ndarray
    perfect_candidate_timestamps: np.ndarray
    great_floor_timestamps: np.ndarray
    great_candidate_timestamps: np.ndarray
    late_great_floor_timestamps: np.ndarray
    exit_ceiling_timestamps: np.ndarray
    lanes: np.ndarray
    fever_fill_denom: float


def _lower_bound_from(timestamps: np.ndarray, value: float) -> int:
    # Same left-bisect as np.searchsorted(side="left") over the float32 axis, via the
    # frontier build's numba twin: identical float32 needle rounding and comparisons,
    # without the per-call numpy dispatch (this sits under the trace-DFS hot loops).
    return int(_rb_numba._numba_lower_bound_from(timestamps, float(value)))


def _fever_end(hit: float, a: int, floor_timestamps: np.ndarray, real_fever_time: float, n: int) -> int:
    """The first note past the fever of activation `a` hit at `hit`, by the notes' earliest hits: in (a, n]."""
    return min(max(_lower_bound_from(floor_timestamps, hit + real_fever_time), a + 1), n)


def _head_mask(start: int, end: int, n: int) -> int:
    """Bit i for each head note i in [start, end)."""
    lo, hi = max(0, min(start, n, 100)), max(0, min(end, n, 100))
    return ((1 << (hi - lo)) - 1) << lo if hi > lo else 0


def _body_count(start: int, end: int, n: int) -> int:
    return max(0, min(end, n) - max(start, 100))


def _body_overlap(first_start: int, first_end: int, second_start: int, second_end: int, n: int) -> int:
    return max(0, min(first_end, second_end, n) - max(first_start, second_start, 100))


class _Edge(NamedTuple):
    """A section's response surface: its head's fever and Great notes as bit masks, and its body counts."""

    fever: int
    great: int
    body_fever: int
    body_great: int
    body_fever_great: int


def _edge_of_surface(surface: FgResponseSurface) -> _Edge:
    fever = great = 0
    for word in range(4):
        fever |= surface[word] << (32 * word)
        great |= surface[4 + word] << (32 * word)
    return _Edge(fever, great, surface.body_fever, surface.body_great, surface.body_fever_great)


def _subtract_edge(remaining: _Edge, edge: _Edge) -> _Edge | None:
    """The surface left after an edge; None when the edge does not fit."""
    if (
        edge.fever & ~remaining.fever
        or edge.great & ~remaining.great
        or edge.body_fever > remaining.body_fever
        or edge.body_great > remaining.body_great
        or edge.body_fever_great > remaining.body_fever_great
    ):
        return None
    return _Edge(
        remaining.fever & ~edge.fever,
        remaining.great & ~edge.great,
        remaining.body_fever - edge.body_fever,
        remaining.body_great - edge.body_great,
        remaining.body_fever_great - edge.body_fever_great,
    )


def _edge_surface(
    *,
    n: int,
    fever_start: int,
    fever_end: int,
    great_start: int,
    great_end: int,
    activation_great_idx: int = -1,
    early_great_start: int = -1,
    early_great_end: int = -1,
) -> _Edge:
    great = _head_mask(great_start, great_end, n)
    if 0 <= activation_great_idx < min(n, 100):
        great |= 1 << activation_great_idx
    body_great = _body_count(great_start, great_end, n)
    body_fever_great = _body_overlap(fever_start, fever_end, great_start, great_end, n)
    if max(100, fever_start) <= activation_great_idx < min(fever_end, n) and not great_start <= activation_great_idx < great_end:
        body_great += 1
        body_fever_great += 1
    # Issue #44 early-Great tail [early_great_start, early_great_end): boundary notes pulled into fever only as Greats:
    # in fever and Great, disjoint from the forced-Great prefix.
    if early_great_end > early_great_start:
        great |= _head_mask(early_great_start, early_great_end, n)
        body_great += _body_count(early_great_start, early_great_end, n)
        body_fever_great += _body_overlap(fever_start, fever_end, early_great_start, early_great_end, n)
    return _Edge(_head_mask(fever_start, fever_end, n), great, _body_count(fever_start, fever_end, n), body_great,
                 body_fever_great)


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
        return _fever_end(hit, activation_idx, perfect_floor_timestamps, real_fever_time, n)

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


def _activation_reachable(
    *,
    context: _ActivationReachabilityContext,
    a: int,
    hit: float,
    section_start: int,
    great_start: int,
    great_count: int,
    activation_great: bool,
    n: int,
) -> bool:
    return bool(
        _rb_numba._numba_activation_reachable_contiguous_run(
            a, hit, context.timestamps,
            _rb_numba.HitTimes(
                context.perfect_floor_timestamps, context.perfect_candidate_timestamps, context.great_floor_timestamps,
                context.great_candidate_timestamps, context.late_great_floor_timestamps,
            ),
            context.lanes, context.fever_fill_denom, section_start, n, great_start, great_count, int(activation_great),
        )
    )


def _latest_hit(
    context: _ActivationReachabilityContext, a: int, hit_lo: float, hit_hi: float, great_start: int, great_count: int
) -> float | None:
    """The latest hit of `a` in [hit_lo, hit_hi] that the contiguous Great run keeps in chart order, if any."""
    cap, valid, _token = _rb_numba._numba_latest_activation_hit_for_contiguous_great_run(
        a, hit_lo, hit_hi, context.timestamps, context.perfect_candidate_timestamps, context.great_candidate_timestamps,
        great_start, great_count, context.timestamps.shape[0], -1,
    )
    return float(cap) if valid else None


def _perfect_window(context: _ActivationReachabilityContext, a: int) -> tuple[float, float]:
    """The hits of note `a` that judge it Perfect at the time the chart can place it."""
    chart_time, candidate = float(context.timestamps[a]), float(context.perfect_candidate_timestamps[a])
    return min(chart_time, candidate), max(chart_time, candidate)


def _region_run_offsets(*, section_start: int, k: int, n: int, raw_fever_fill: float) -> tuple[int, ...]:
    if k <= 0 or section_start >= n:
        return ()
    offsets: set[int] = set()

    # Region 2: if `k` is the actual number of Greats up to and including the crossing,
    # x = run_start-section_start must satisfy
    #   x + 0.5*(k-1) < denom <= x + 0.5*k.
    # The interval is only half a unit wide, so there is at most one integer start.
    lo = ceil(raw_fever_fill - 0.5 * k)
    hi = ceil(raw_fever_fill - 0.5 * (k - 1)) - 1
    if lo == hi and lo >= 1 and section_start + lo + k - 1 < n:
        offsets.add(lo)

    # Region-3 shifted-head runs share activation/end for a fixed k. The earliest shifted
    # head run is the score-dominant representative; later starts only move the same Great
    # count onto later ramp notes. Keep reconstruction aligned with the Numba producer.
    if section_start < 99 and ceil(raw_fever_fill) > 1 and section_start + 1 < n:
        offsets.add(1)
    return tuple(sorted(offsets))


def _minimal_reachable_region_great_end(
    context: _ActivationReachabilityContext, a: int, section_start: int, run_start: int, n: int
) -> tuple[int, float] | None:
    hit_hi = float(context.great_candidate_timestamps[a])
    hit_lo = float(context.late_great_floor_timestamps[a])
    max_great_end = a + 1
    while max_great_end < n and float(context.perfect_candidate_timestamps[max_great_end]) < hit_hi:
        max_great_end += 1
    for great_end in range(a + 1, max_great_end + 1):
        great_count = great_end - run_start
        hit = _latest_hit(context, a, hit_lo, hit_hi, run_start, great_count)
        if hit is not None and _activation_reachable(
            context=context, a=a, hit=hit, section_start=section_start, great_start=run_start,
            great_count=great_count, activation_great=True, n=n,
        ):
            return great_end, hit
    return None


class _ActionRow(NamedTuple):
    """One action of a section start (_numba_trace_edge_action_arrays): its forced Greats k, fill and forced count; its
    activation note a; its Perfect activation (hit window low end, latest hit, reachable, end e, the start time of its
    fever, the end of its early-Great tail); its late-Great activation (floor, hit, the forced prefix it needs (< 0: none
    schedulable), its end and early-Great tail end)."""

    k: int
    fill: int
    forced: int
    a: int
    hit_lo: float
    perfect_hit: float
    perfect_reachable: bool
    e: int
    start_time: float
    eg_e: int
    late_lo: float
    late_hit: float
    lg_prefix: int
    late_e: int
    late_eg_e: int


class _Witness(NamedTuple):
    """How a section's activation is hit: its legal window, the fever end priced for it, and whether it exits early."""

    lo: float
    hi: float
    target_end: int
    early_exit: bool = False


@dataclass(slots=True)
class _SectionOptions:
    """A section start's distinct options, in emission order."""

    context: _ActivationReachabilityContext
    real_fever_time: float
    n: int
    out: list[dict[str, Any]] = field(default_factory=list)
    seen: set[tuple[Any, ...]] = field(default_factory=set)

    def emit(self, option: dict[str, Any]) -> None:
        key = (
            option["surface"],
            option["next_state"],
            option["activation_index"],
            option["activation_judgment"],
            option["forced_run_start_index"],
            option["forced_run_count"],
            option["early_great_start"],
            option["early_great_end"],
        )
        if key not in self.seen:
            self.seen.add(key)
            self.out.append(option)

    def section(
        self, *, k: int, a: int, late_great: bool, section_start: int, run_start: int, run_end: int, end: int,
        early_great_end: int, hit_lo: float, hit_hi: float,
    ) -> None:
        """The sections activating at `a` (by a late Great when `late_great`) with the forced Greats [run_start, run_end):
        the section to `end`; then one per later end up to `early_great_end` whose tail past `end` is fever-great (issue
        #44: the same witness still reproduces `end`); then the activation ending its fever early: hit from its earliest
        legal hit (a Perfect's floor, a late Great's late-Great floor), at every end from which the later notes can still
        be hit past its cutoff."""
        context, n = self.context, self.n
        timestamps = context.timestamps
        edge = dict(
            n=n, fever_start=a, great_start=run_start, great_end=run_end, activation_great_idx=a if late_great else -1
        )

        def ending_at(index: int) -> dict[str, Any]:
            return {
                "next_state": index,
                "fever_end_index": index,
                "fever_end_ms": None if index >= n else float(timestamps[index]) * 1000.0,
            }

        base = {
            "k": k,
            **ending_at(end),
            "activation_index": a,
            "activation_ms": float(timestamps[a]) * 1000.0,
            "activation_judgment": "late_great" if late_great else "perfect",
            "forced_start_index": section_start,
            "forced_run_start_index": run_start,
            "forced_run_count": run_end - run_start,
            "early_great_start": -1,
            "early_great_end": -1,
            "surface": _edge_surface(**edge, fever_end=end),
            "_witness": _Witness(hit_lo, hit_hi, end),
        }
        self.emit(base)
        for tail_end in range(end + 1, early_great_end + 1):
            self.emit({
                **base,
                **ending_at(tail_end),
                "early_great_start": end,
                "early_great_end": tail_end,
                "surface": _edge_surface(**edge, fever_end=tail_end, early_great_start=end, early_great_end=tail_end),
            })
        floor = context.late_great_floor_timestamps if late_great else context.perfect_floor_timestamps
        lo = float(floor[a])
        exit_lo = _lower_bound_from(context.exit_ceiling_timestamps, lo + self.real_fever_time)
        for early_end in range(min(max(exit_lo, a + 1), end), end):
            self.emit({
                **base,
                **ending_at(early_end),
                "surface": _edge_surface(**edge, fever_end=early_end),
                "_witness": _Witness(lo, hit_hi, early_end, True),
            })


def _edge_surface_options(
    *,
    context: _ActivationReachabilityContext,
    i: int,
    first: bool,
    actions: list[int],
    fills: list[int],
    forced: list[int],
    real_fever_time: float,
    use_forced_great_timing: bool,
) -> Iterator[dict[str, Any]]:
    """Enumerate the candidate fever sections of the section start after state `i` (the first section when `first`)
    with their response-surface edges: per action of the frontier's action table (its `fills` and `forced` counts for
    this kind of section), its Perfect activation, its late-Great activation and its region runs. Yields each action's
    options as they are built, so a consumer that stops early builds no later action's.

    Witness timing fields are intentionally absent here: computing the centered activation witness
    (`_centered_hit_window_for_exit`) is the expensive part and only sections accepted into the final trace need it.
    Callers attach it with `_option_with_witness` once an option is accepted.
    """
    n = context.timestamps.shape[0]
    section_start = 0 if first else i + 1
    # One batched numba pass over the action loop's per-action scalar precompute (the prefix + late-Great families);
    # every emit/dedup/dict decision and the region-run family stay below, driven by these arrays.
    (
        act_err, act_a, _act_chart, act_hit_lo, act_perfect_hit, _act_perfect_hit_ok, act_perfect_reachable, act_e,
        act_start_time, act_eg_e, act_late_lo, act_late_hit, act_lg_prefix, act_late_e, _act_late_start, act_late_eg_e,
    ) = _rb_numba._numba_trace_edge_action_arrays(
        np.asarray(actions, dtype=np.int64),
        np.asarray(fills, dtype=np.int64),
        np.asarray(forced, dtype=np.int64),
        int(first),
        i,
        n,
        context.timestamps,
        context.perfect_candidate_timestamps,
        context.great_candidate_timestamps,
        context.perfect_floor_timestamps,
        context.great_floor_timestamps,
        context.late_great_floor_timestamps,
        context.lanes,
        context.fever_fill_denom,
        real_fever_time,
    )
    if np.any(act_err):
        raise ValueError("FG activation reachability received invalid section bounds")
    options = _SectionOptions(context, real_fever_time, n)
    prev_fill, prev_start_time, prev_e = -1, -1.0, -1
    rows = zip(actions, fills, forced, *(column.tolist() for column in (
        act_a, act_hit_lo, act_perfect_hit, act_perfect_reachable, act_e, act_start_time, act_eg_e, act_late_lo,
        act_late_hit, act_lg_prefix, act_late_e, act_late_eg_e,
    )))
    for action in map(_ActionRow._make, rows):
        emitted = len(options.out)
        if action.perfect_reachable and (
            action.fill != prev_fill or (action.start_time != prev_start_time and action.e != prev_e)
        ):
            options.section(
                k=action.k, a=action.a, late_great=False, section_start=section_start, run_start=section_start,
                run_end=min(n, section_start + action.forced), end=action.e, early_great_end=action.eg_e,
                hit_lo=action.hit_lo, hit_hi=action.perfect_hit,
            )
        # lg_prefix < 0 encodes both "no late-Great placement" and "placement not scheduleable". A late Great activation
        # needs to reach past the Perfect activation's end or early-Great tail.
        if (
            use_forced_great_timing and prev_fill == action.fill and action.lg_prefix >= 0
            and (action.late_e > action.e or action.late_eg_e > action.eg_e)
        ):
            options.section(
                k=action.k, a=action.a, late_great=True, section_start=section_start, run_start=section_start,
                run_end=min(n, section_start + action.lg_prefix), end=action.late_e, early_great_end=action.late_eg_e,
                hit_lo=action.late_lo, hit_hi=action.late_hit,
            )
        if use_forced_great_timing and action.k > 0:
            _region_runs(options, action, section_start)
        yield from options.out[emitted:]
        prev_fill, prev_start_time, prev_e = action.fill, action.start_time, action.e


def _region_runs(options: _SectionOptions, action: _ActionRow, section_start: int) -> None:
    """The action's sections whose k forced Greats run from later in the section: each run's fill crossing activates
    by a Great or a Perfect (the run from the section start crossing at the action's own activation is that action)."""
    n = options.n
    raw_fever_fill = options.context.fever_fill_denom
    for offset in _region_run_offsets(section_start=section_start, k=action.k, n=n, raw_fever_fill=raw_fever_fill):
        run_start = section_start + offset
        a, crossing_is_great = server_fill_crossing_run(section_start, run_start, action.k, raw_fever_fill, n)
        if a is None or a >= n or (a == action.a and run_start == section_start):
            continue
        if crossing_is_great:
            _great_region_run(options, a, section_start, run_start)
        else:
            _perfect_region_run(options, action.k, a, section_start, run_start)


def _great_region_run(options: _SectionOptions, a: int, section_start: int, run_start: int) -> None:
    """A region run crossing by a late Great at `a`: its minimal reachable Great run, kept when it ends later than the
    Perfect activation of the same run (or its early-Great tail reaches further)."""
    context, n, real_fever_time = options.context, options.n, options.real_fever_time
    found = _minimal_reachable_region_great_end(context, a, section_start, run_start, n)
    if found is None:
        return
    great_end, activation_hit = found
    floor, great_floor = context.perfect_floor_timestamps, context.great_floor_timestamps
    end = _fever_end(activation_hit, a, floor, real_fever_time, n)
    tail_end = _fever_end(activation_hit, a, great_floor, real_fever_time, n)
    perfect_hit = _latest_hit(context, a, *_perfect_window(context, a), run_start, great_end - run_start)
    if (
        perfect_hit is not None
        and end <= _fever_end(perfect_hit, a, floor, real_fever_time, n)
        and tail_end <= _fever_end(perfect_hit, a, great_floor, real_fever_time, n)
    ):
        return
    options.section(
        k=great_end - run_start, a=a, late_great=True, section_start=section_start, run_start=run_start,
        run_end=great_end, end=end, early_great_end=tail_end, hit_lo=float(context.late_great_floor_timestamps[a]),
        hit_hi=activation_hit,
    )


def _perfect_region_run(options: _SectionOptions, k: int, a: int, section_start: int, run_start: int) -> None:
    """A region run of k forced Greats crossing by a Perfect at `a`, when the input engine can reach its latest hit."""
    context, n, real_fever_time = options.context, options.n, options.real_fever_time
    great_end = min(n, run_start + k)
    if great_end <= run_start:
        return
    great_count = great_end - run_start
    hit_lo, hit_hi = _perfect_window(context, a)
    hit = _latest_hit(context, a, hit_lo, hit_hi, run_start, great_count)
    if hit is None or not _activation_reachable(
        context=context, a=a, hit=hit, section_start=section_start, great_start=run_start, great_count=great_count,
        activation_great=False, n=n,
    ):
        return
    options.section(
        k=great_count, a=a, late_great=False, section_start=section_start, run_start=run_start, run_end=great_end,
        end=_fever_end(hit, a, context.perfect_floor_timestamps, real_fever_time, n),
        early_great_end=_fever_end(hit, a, context.great_floor_timestamps, real_fever_time, n),
        hit_lo=hit_lo, hit_hi=hit,
    )


def _option_with_witness(
    option: dict[str, Any], context: _ActivationReachabilityContext, real_fever_time: float
) -> dict[str, Any]:
    """An accepted option as a stored trace section: with its centered activation witness and exact schedule."""
    n = context.timestamps.shape[0]
    witness = option["_witness"]
    activation_idx = option["activation_index"]
    late_great = option["activation_judgment"] == "late_great"
    hit, hit_lo, hit_hi = _centered_hit_window_for_exit(
        n, activation_idx, witness.lo, witness.hi, real_fever_time, witness.target_end,
        context.perfect_floor_timestamps, context.exit_ceiling_timestamps if witness.early_exit else None,
    )
    section_start = option["forced_start_index"]
    run_start = option["forced_run_start_index"]
    run_end = min(n, run_start + option["forced_run_count"])
    is_great = np.zeros(n, dtype=np.bool_)
    is_great[run_start:run_end] = True
    if late_great:
        is_great[activation_idx] = True
    labels = exact_label_hit_intervals(
        is_great=is_great,
        timestamps=context.timestamps,
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
    chart_time = float(context.timestamps[activation_idx])
    return {
        "k": option["k"],
        "next_state": option["next_state"],
        "activation_index": activation_idx,
        "activation_ms": option["activation_ms"],
        "activation_judgment": option["activation_judgment"],
        "activation_hit_ms": hit * 1000.0,
        "activation_hit_offset_ms": (hit - chart_time) * 1000.0,
        "activation_hit_window_lower_ms": hit_lo * 1000.0,
        "activation_hit_window_upper_ms": hit_hi * 1000.0,
        "activation_hit_offset_lower_ms": (hit_lo - chart_time) * 1000.0,
        "activation_hit_offset_upper_ms": (hit_hi - chart_time) * 1000.0,
        "activation_hit_window_width_ms": max(0.0, (hit_hi - hit_lo) * 1000.0),
        "forced_start_index": section_start,
        "forced_run_start_index": run_start,
        "forced_run_count": option["forced_run_count"],
        "fever_end_index": option["fever_end_index"],
        "fever_end_ms": option["fever_end_ms"],
        "fever_duration_ms": real_fever_time * 1000.0,
        # The cutoff belongs to the materialized activation witness, not another legal point in
        # its interval. Endpoint guidance may move boundary notes earlier to realize the selected
        # surface, but activation and cutoff must describe one physical play.
        "fever_window_end_ms": (hit + real_fever_time) * 1000.0,
        **_fever_start_fields(
            start_time=hit, chart_time=chart_time, activation_idx=activation_idx, late_great=late_great
        ),
        # Issue #44: the early-Great tail [early_great_start, early_great_end) -- boundary notes
        # this section pulls into fever as Greats (default -1/-1 = none). The per-note early-Great
        # hit offsets are stamped by the note-graph layer (like #42's endpoint-early Perfect hits).
        "early_great_start": option["early_great_start"],
        "early_great_end": option["early_great_end"],
        "activation_schedule_schema_version": 1,
        "preactivation_order": [int(index) for index in schedule.preactivation_order],
        "preactivation_lane_prefixes": [
            {"lane": int(row.lane), "count": len(row.note_indices)} for row in schedule.lane_prefixes
        ],
        "preactivation_fill_half_units": schedule.preactivation_fill_half_units,
        "preactivation_event_count": schedule.preactivation_event_count,
        "preactivation_great_count": schedule.preactivation_great_count,
        "surface": option["surface"],
    }


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
    use_forced_great_timing = inputs.use_forced_great_timing
    ts, perfect_ts, great_ts, floor_ts, great_floor_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr = song_arrays(
        inputs.timestamps, inputs.perfect_candidates, inputs.great_candidates, inputs.perfect_floor,
        inputs.great_floor, inputs.late_great_floor, inputs.exit_ceiling, inputs.lanes,
    )
    if max(1, ceil(raw_fever_fill)) < early_exit_min_fill(floor_ts, perfect_ts):
        exit_ceiling_ts = np.full_like(exit_ceiling_ts, -np.inf)  # as the search: no early exits at this fill
    context = _ActivationReachabilityContext(
        ts, floor_ts, perfect_ts, great_floor_ts, great_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr,
        raw_fever_fill,
    )

    actions, later_fill, first_fill, later_forced, first_forced = action_table(
        raw_fever_fill=raw_fever_fill, non_fever_base=non_fever_base, use_forced_great_timing=use_forced_great_timing
    )

    # The ordered edge list is independent of the target surface, so the up-to-51 surfaces of one song reuse it.
    shared_edge_options = edge_options_cache if edge_options_cache is not None else FgTraceEdgeOptionsCache()
    edge_cache_prefix = (non_fever_base, raw_fever_fill, real_fever_time, use_forced_great_timing)

    memo: set[tuple[int, bool, _Edge]] = set()
    unplayable: list[UnplayableTrace] = []

    def _section_options(state: int, first: bool) -> _SectionOptionStream:
        key = (*edge_cache_prefix, state, first)
        options = shared_edge_options.get(key)
        if options is None:
            options = _SectionOptionStream(
                _edge_surface_options(
                    context=context,
                    i=state,
                    first=first,
                    actions=actions,
                    fills=first_fill if first else later_fill,
                    forced=first_forced if first else later_forced,
                    real_fever_time=real_fever_time,
                    use_forced_great_timing=use_forced_great_timing,
                )
            )
            shared_edge_options.put(key, options)
        return options

    def _accepted_section(option: dict[str, Any], edge: _Edge) -> dict[str, Any]:
        # The centered witness is computed only here, for sections accepted into the final trace.
        section = _option_with_witness(option, context, real_fever_time)
        del section["surface"]
        section["forced_count"] = section.pop("k")
        section["body_fever"] = edge.body_fever
        section["body_great"] = edge.body_great
        section["body_fever_great"] = edge.body_fever_great
        return section

    def _search(state: int, first: bool, remaining: _Edge) -> tuple[dict[str, Any], ...] | None:
        key = (state, first, remaining)
        if key in memo:
            return None
        for option in _section_options(state, first):
            edge = option["surface"]
            left = _subtract_edge(remaining, edge)
            if left is None:
                continue
            next_state = option["next_state"]
            if not any(left):
                tail = ()
            elif next_state >= n or (left.fever | left.great) & ((2 << next_state) - 1):
                continue  # the next section starts past next_state: no section can take a head note before it
            else:
                tail = _search(next_state, False, left)
                if tail is None:
                    continue
            try:
                return (_accepted_section(option, edge), *tail)
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
