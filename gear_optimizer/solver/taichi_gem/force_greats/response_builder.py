from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any, NamedTuple

import numpy as np

from ...scoring.fg_policy import FGSongInputs
from .activation_witness import activation_schedule_witnesses, exact_label_hit_intervals
from .fill_crossing import server_fill_crossing_run
from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_batch import action_table, early_exit_min_fill, song_arrays
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE
from ...timing_envelope import FRAME_MARGIN_MS


_TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS = 8192
_TRACE_EDGE_OPTIONS_CACHE_MAX_STATES = 256


@dataclass(slots=True)
class FgTraceEdgeOptionsCache:
    """One-song ordered edge cache with enforced owner identity and bounded option count."""

    _entries: dict[Any, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    _owner_inputs: tuple[Any, ...] | None = None
    _owner_note_count: int = -1
    _explicit_owner: bool = False
    _option_count: int = 0

    def bind_owner(self, owner: Any, *, note_count: int) -> None:
        if self._owner_inputs is None:
            self._owner_inputs = (owner,)
            self._owner_note_count = int(note_count)
            self._explicit_owner = True
        elif (
            not self._explicit_owner
            or self._owner_note_count != int(note_count)
            or self._owner_inputs[0] is not owner
        ):
            raise ValueError("FG trace edge cache cannot be reused across song timing owners")

    def bind_inputs(self, *, owner_inputs: tuple[Any, ...], note_count: int) -> None:
        if self._explicit_owner:
            if self._owner_note_count != int(note_count):
                raise ValueError("FG trace edge cache note count changed for its bound song owner")
            return
        if self._owner_inputs is None:
            self._owner_inputs = tuple(owner_inputs)
            self._owner_note_count = int(note_count)
        elif self._owner_note_count != int(note_count) or any(
            current is not stored for current, stored in zip(owner_inputs, self._owner_inputs, strict=True)
        ):
            raise ValueError("FG trace edge cache cannot be reused across song timing owners")

    def get(self, key: tuple[Any, ...]) -> tuple[dict[str, Any], ...] | None:
        return self._entries.get(key)

    def put(self, key: tuple[Any, ...], options: tuple[dict[str, Any], ...]) -> None:
        if key in self._entries:
            raise RuntimeError("FG trace edge cache key was published twice")
        option_count = len(options)
        if option_count > _TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS:
            return
        while self._entries and (
            len(self._entries) >= _TRACE_EDGE_OPTIONS_CACHE_MAX_STATES
            or self._option_count + option_count > _TRACE_EDGE_OPTIONS_CACHE_MAX_OPTIONS
        ):
            oldest_key = next(iter(self._entries))
            old_options = self._entries.pop(oldest_key)
            self._option_count -= len(old_options)
        self._entries[key] = options
        self._option_count += option_count

    @property
    def option_count(self) -> int:
        return int(self._option_count)

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


def _build_activation_reachability_context(
    *,
    timestamps: Any,
    perfect_floor_timestamps: Any,
    perfect_candidate_timestamps: Any,
    great_floor_timestamps: Any,
    great_candidate_timestamps: Any,
    lanes: Any,
    fever_fill_denom: float,
    late_great_floor_timestamps: Any | None = None,
    exit_ceiling_timestamps: Any | None = None,
) -> _ActivationReachabilityContext:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    perfect_floor = np.ascontiguousarray(np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1))
    perfect_candidates = np.ascontiguousarray(
        np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    great_floor = np.ascontiguousarray(np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1))
    great_candidates = np.ascontiguousarray(
        np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    late_great_floor = (
        perfect_candidates + np.float32(0.001)
        if late_great_floor_timestamps is None
        else np.ascontiguousarray(np.asarray(late_great_floor_timestamps, dtype=np.float32).reshape(-1))
    )
    exit_ceiling = (
        np.ascontiguousarray(np.minimum.accumulate(perfect_candidates[::-1])[::-1])
        if exit_ceiling_timestamps is None
        else np.ascontiguousarray(np.asarray(exit_ceiling_timestamps, dtype=np.float32).reshape(-1))
    )
    lane_arr = np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0:
        raise ValueError("FG activation reachability requires at least one note")
    if any(
        int(values.shape[0]) != n
        for values in (
            perfect_floor, perfect_candidates, great_floor, great_candidates, late_great_floor, exit_ceiling, lane_arr
        )
    ):
        raise ValueError("FG activation reachability arrays must match timestamps")
    return _ActivationReachabilityContext(
        timestamps=ts,
        perfect_floor_timestamps=perfect_floor,
        perfect_candidate_timestamps=perfect_candidates,
        great_floor_timestamps=great_floor,
        great_candidate_timestamps=great_candidates,
        late_great_floor_timestamps=late_great_floor,
        exit_ceiling_timestamps=exit_ceiling,
        lanes=lane_arr,
        fever_fill_denom=float(fever_fill_denom),
    )


def _lower_bound_from(timestamps: np.ndarray, value: float) -> int:
    # Same left-bisect as np.searchsorted(side="left") over the float32 axis, via the
    # frontier build's numba twin: identical float32 needle rounding and comparisons,
    # without the per-call numpy dispatch (this sits under the trace-DFS hot loops).
    return int(_rb_numba._numba_lower_bound_from(timestamps, float(value)))


def _edge_end_at_hit(
    *,
    n: int,
    a: int,
    hit: float,
    activation_great: bool,
    real_fever_time: float,
    perfect_floor_timestamps: np.ndarray,
) -> tuple[int, float, int]:
    start_time = float(hit)
    carry_idx = int(a) if bool(activation_great) else -1
    e = _lower_bound_from(perfect_floor_timestamps, float(start_time) + float(real_fever_time))
    if e <= int(a):
        e = int(a) + 1
    if e > int(n):
        e = int(n)
    return int(e), float(start_time), int(carry_idx)


def _range_head_mask(start: int, end: int, *, n: int) -> tuple[int, int, int, int]:
    start_i = max(0, min(int(start), int(n), 100))
    end_i = max(0, min(int(end), int(n), 100))
    words = [0, 0, 0, 0]
    if end_i <= start_i:
        return 0, 0, 0, 0
    for word_idx in range(4):
        lo = word_idx * 32
        hi = min(lo + 32, 100)
        a = max(start_i, lo)
        b = min(end_i, hi)
        if b <= a:
            continue
        width = b - a
        words[word_idx] = ((1 << width) - 1) << (a - lo)
    return int(words[0]), int(words[1]), int(words[2]), int(words[3])


def _range_body_count(start: int, end: int, *, n: int) -> int:
    return max(0, min(int(end), int(n)) - max(int(start), 100))


def _range_body_overlap_count(first_start: int, first_end: int, second_start: int, second_end: int, *, n: int) -> int:
    start = max(int(first_start), int(second_start), 100)
    end = min(int(first_end), int(second_end), int(n))
    return max(0, int(end) - int(start))


def _single_head_mask(idx: int, *, n: int) -> tuple[int, int, int, int]:
    idx_i = int(idx)
    if idx_i < 0 or idx_i >= min(int(n), 100):
        return 0, 0, 0, 0
    words = [0, 0, 0, 0]
    word_idx = idx_i // 32
    words[word_idx] = 1 << (idx_i % 32)
    return int(words[0]), int(words[1]), int(words[2]), int(words[3])


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
) -> FgResponseSurface:
    f0, f1, f2, f3 = _range_head_mask(fever_start, fever_end, n=int(n))
    g0, g1, g2, g3 = _range_head_mask(great_start, great_end, n=int(n))
    if int(activation_great_idx) >= 0:
        a0, a1, a2, a3 = _single_head_mask(int(activation_great_idx), n=int(n))
        g0 |= a0
        g1 |= a1
        g2 |= a2
        g3 |= a3
    body_great = _range_body_count(great_start, great_end, n=int(n))
    body_fever_great = _range_body_overlap_count(fever_start, fever_end, great_start, great_end, n=int(n))
    if int(activation_great_idx) >= max(100, int(fever_start)) and int(activation_great_idx) < min(int(fever_end), int(n)):
        if int(activation_great_idx) < int(great_start) or int(activation_great_idx) >= int(great_end):
            body_great += 1
            body_fever_great += 1
    # Issue #44 early-Great tail [early_great_start, early_great_end): boundary notes pulled into
    # fever ONLY as Greats. In-fever-and-Great, disjoint from the forced-Great prefix, so OR into
    # the Great mask and add to both body_great and body_fever_great.
    if int(early_great_end) > int(early_great_start):
        e0, e1, e2, e3 = _range_head_mask(int(early_great_start), int(early_great_end), n=int(n))
        g0 |= e0
        g1 |= e1
        g2 |= e2
        g3 |= e3
        body_great += _range_body_count(int(early_great_start), int(early_great_end), n=int(n))
        body_fever_great += _range_body_overlap_count(
            fever_start, fever_end, int(early_great_start), int(early_great_end), n=int(n)
        )
    return FgResponseSurface(
        f0,
        f1,
        f2,
        f3,
        g0,
        g1,
        g2,
        g3,
        _range_body_count(fever_start, fever_end, n=int(n)),
        int(body_great),
        int(body_fever_great),
    )


def _trace_timing_fields(
    *,
    carry_idx: int,
    start_time: float,
    chart_time: float,
    activation_idx: int,
    activation_great: bool,
) -> dict[str, Any]:
    if bool(activation_great) and int(carry_idx) == int(activation_idx):
        source = "activation_late_great"
        note_idx = int(carry_idx)
    elif float(start_time) != float(chart_time):
        source = "precise"
        note_idx = int(activation_idx)
    else:
        source = "chart_perfect"
        note_idx: int | None = None
    return {
        "fever_start_source": source,
        "fever_start_note_index": note_idx,
        "fever_start_hit_ms": float(start_time) * 1000.0,
    }


def _centered_hit_window_for_exit(
    n: int, activation_idx: int,
    legal_lo: float, legal_hi: float, real_fever_time: float, target_end_idx: int,
    perfect_floor_timestamps: np.ndarray,
    exit_ceiling_timestamps: np.ndarray | None = None,
) -> tuple[float, float, float]:
    """The activation hit, centered in [legal_lo, legal_hi], whose fever ends at `target_end_idx`: by default the end
    the notes reach at their earliest hits (the floor). With `exit_ceiling_timestamps` (an early exit) the notes before
    the target still reach inside the cutoff at their earliest hits, and the cutoff stays at or before the exit ceiling
    of the target, so the target and every later note can be hit past it."""
    target = max(0, min(int(target_end_idx), int(n)))
    lo = float(legal_lo)
    hi = float(legal_hi)
    if lo > hi:
        raise ValueError("FG response trace received an empty activation witness interval")
    # The exit must search the same earliest-Perfect floor envelope the surface boundary
    # used (issue #42), so the centered witness reproduces the (floor-based) target_end.
    floor_ts = perfect_floor_timestamps

    def _exit_idx(hit: float) -> int:
        end_idx = _lower_bound_from(floor_ts, hit + float(real_fever_time))
        if end_idx <= int(activation_idx):
            end_idx = min(int(n), int(activation_idx) + 1)
        return int(end_idx)

    def _next_hit(hit: float, direction: float) -> float:
        return float(np.nextafter(np.float32(hit), np.float32(direction)))

    def _ceil_hit(value: float) -> float:
        hit = float(np.float32(value))
        if hit < float(value):
            hit = _next_hit(hit, np.float32(np.inf))
        return float(hit)

    def _floor_hit(value: float) -> float:
        hit = float(np.float32(value))
        if hit > float(value):
            hit = _next_hit(hit, np.float32(-np.inf))
        return float(hit)

    def _float32_order(value: float) -> int:
        bits = int(np.asarray(np.float32(value), dtype=np.float32).view(np.uint32))
        if bits & 0x80000000:
            return int(0x80000000 - bits)
        return int(bits + 0x80000000)

    def _hit_from_order(order: int) -> float:
        if int(order) >= 0x80000000:
            bits = int(order) - 0x80000000
        else:
            bits = 0x80000000 - int(order)
        return float(np.asarray(np.uint32(bits), dtype=np.uint32).view(np.float32))

    def _first_order_with_exit_at_least(first_order: int, last_order: int, expected: int) -> int | None:
        lo_order = int(first_order)
        hi_order = int(last_order)
        found: int | None = None
        while lo_order <= hi_order:
            mid = (lo_order + hi_order) // 2
            if _exit_idx(_hit_from_order(mid)) >= int(expected):
                found = int(mid)
                hi_order = int(mid) - 1
            else:
                lo_order = int(mid) + 1
        return found

    def _ends_at_target(hit: float) -> bool:
        if exit_ceiling_timestamps is None:
            return _exit_idx(hit) == int(target)
        cutoff = float(np.float32(float(hit) + float(real_fever_time)))
        return _exit_idx(hit) >= int(target) and cutoff <= float(exit_ceiling_timestamps[int(target)])

    def _last_order_with_exit_at_most(first_order: int, last_order: int, expected: int) -> int | None:
        lo_order = int(first_order)
        hi_order = int(last_order)
        found: int | None = None
        while lo_order <= hi_order:
            mid = (lo_order + hi_order) // 2
            hit = _hit_from_order(mid)
            if exit_ceiling_timestamps is None:
                fits = _exit_idx(hit) <= int(expected)
            else:
                cutoff = float(np.float32(float(hit) + float(real_fever_time)))
                fits = cutoff <= float(exit_ceiling_timestamps[int(expected)])
            if fits:
                found = int(mid)
                lo_order = int(mid) + 1
            else:
                hi_order = int(mid) - 1
        return found

    min_order = _float32_order(_ceil_hit(lo))
    max_order = _float32_order(_floor_hit(hi))
    if min_order > max_order:
        raise ValueError("could not choose a centered FG trace witness without changing the response surface")

    first_order = _first_order_with_exit_at_least(min_order, max_order, int(target))
    last_order = _last_order_with_exit_at_most(min_order, max_order, int(target))
    if first_order is None or last_order is None or int(first_order) > int(last_order):
        raise ValueError("could not choose a centered FG trace witness without changing the response surface")

    first_hit = _hit_from_order(int(first_order))
    last_hit = _hit_from_order(int(last_order))
    midpoint = float(np.float32((float(first_hit) + float(last_hit)) * 0.5))
    midpoint_order = min(max(_float32_order(midpoint), int(first_order)), int(last_order))
    midpoint_hit = _hit_from_order(int(midpoint_order))
    if _ends_at_target(midpoint_hit):
        return float(midpoint_hit), float(first_hit), float(last_hit)

    candidate_order = (int(first_order) + int(last_order)) // 2
    candidate = _hit_from_order(int(candidate_order))
    if _ends_at_target(candidate):
        return float(candidate), float(first_hit), float(last_hit)
    raise ValueError("centered FG trace witness changed the response surface")


def _hit_window_fields(*, hit: float, lo: float, hi: float, chart_time: float) -> dict[str, float]:
    return {
        "activation_hit_ms": float(hit) * 1000.0,
        "activation_hit_offset_ms": (float(hit) - float(chart_time)) * 1000.0,
        "activation_hit_window_lower_ms": float(lo) * 1000.0,
        "activation_hit_window_upper_ms": float(hi) * 1000.0,
        "activation_hit_offset_lower_ms": (float(lo) - float(chart_time)) * 1000.0,
        "activation_hit_offset_upper_ms": (float(hi) - float(chart_time)) * 1000.0,
        "activation_hit_window_width_ms": max(0.0, (float(hi) - float(lo)) * 1000.0),
    }


def _forced_fields(*, section_start: int, great_start: int, great_count: int, n: int) -> dict[str, int]:
    """Forced-Great fields for one response-surface option.

    Two genuinely distinct concepts are recorded:

    * ``forced_run_start_index`` / ``forced_run_count`` -- the canonical Great RUN (start index +
      length). This is the one true encoding every freshly reconstructed reader consumes.
    * ``forced_start_index`` -- the fever SECTION start. NOT an old name for the run start: readers
      use it distinctly as the reachability section boundary (``reducer._assert_trace_hit_time_
      reachable``, ``tools/dev/audit_loadout_legality.py``). It coincides with the run start only
      when the run is a section-start prefix.
    """
    great_start_i = max(0, min(int(great_start), int(n)))
    great_count_i = max(0, min(int(great_count), int(n) - int(great_start_i)))
    return {
        "forced_start_index": int(section_start),
        "forced_run_start_index": int(great_start_i),
        "forced_run_count": int(great_count_i),
    }


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
    if int(n) != int(context.timestamps.shape[0]):
        raise ValueError("FG activation reachability context length does not match the chart")
    if not (0 <= int(section_start) <= int(a) < int(n)):
        raise ValueError("FG activation reachability received invalid section bounds")
    if not (int(section_start) <= int(great_start) <= int(n)) or int(great_count) < 0:
        raise ValueError("FG activation reachability received an invalid Great run")
    return bool(
        _rb_numba._numba_activation_reachable_contiguous_run(
            int(a),
            float(hit),
            context.timestamps,
            _rb_numba.HitTimes(
                context.perfect_floor_timestamps,
                context.perfect_candidate_timestamps,
                context.great_floor_timestamps,
                context.great_candidate_timestamps,
                context.late_great_floor_timestamps,
            ),
            context.lanes,
            float(context.fever_fill_denom),
            int(section_start),
            int(n),
            int(great_start),
            int(great_count),
            int(bool(activation_great)),
        )
    )


def _latest_activation_hit_for_labels(
    *,
    a: int,
    hit_lo: float,
    hit_hi: float,
    great_start: int,
    great_count: int,
    n: int,
    timestamps: np.ndarray,
    perfect_ts: np.ndarray,
    great_ts: np.ndarray,
) -> float | None:
    great_start_i = max(0, min(int(great_start), int(n)))
    great_count_i = max(0, int(great_count))
    # Numba twin of the reference latest_activation_hit_for_contiguous_great_run
    # (tests/fg_response_frontier_oracles.py) for the lanes=None,
    # epsilon=INPUT_ORDER_EPS_SEC(=1e-6) form this DFS always uses: same walk, same
    # per-note cap arithmetic, minus ~150k Python/numpy dispatches per heavy song.
    n_eff = min(
        int(n), int(timestamps.shape[0]), int(perfect_ts.shape[0]), int(great_ts.shape[0])
    )
    if not (0 <= int(a) < int(n_eff)):
        raise ValueError("activation_index must be inside the section")
    cap, valid, _token = _rb_numba._numba_latest_activation_hit_for_contiguous_great_run(
        int(a),
        float(hit_lo),
        float(hit_hi),
        timestamps,
        perfect_ts,
        great_ts,
        int(great_start_i),
        int(great_count_i),
        int(n_eff),
        -1,
    )
    return float(cap) if int(valid) else None


def _region_run_offsets(*, section_start: int, k: int, n: int, raw_fever_fill: float) -> tuple[int, ...]:
    if int(k) <= 0:
        return ()
    s = int(section_start)
    if s >= int(n):
        return ()
    denom = float(raw_fever_fill)
    offsets: set[int] = set()

    # Region 2: if `k` is the actual number of Greats up to and including the crossing,
    # x = run_start-section_start must satisfy
    #   x + 0.5*(k-1) < denom <= x + 0.5*k.
    # The interval is only half a unit wide, so there is at most one integer start.
    lo = int(ceil(denom - 0.5 * float(k)))
    hi = int(ceil(denom - 0.5 * float(k - 1))) - 1
    if lo == hi and lo >= 1 and s + lo + int(k) - 1 < int(n):
        offsets.add(int(lo))

    # Region-3 shifted-head runs share activation/end for a fixed k. The earliest shifted
    # head run is the score-dominant representative; later starts only move the same Great
    # count onto later ramp notes. Keep reconstruction aligned with the Numba producer.
    if s < 99 and int(ceil(denom)) > 1 and s + 1 < int(n):
        offsets.add(1)
    return tuple(sorted(offsets))


def _minimal_reachable_region_great_end(
    *,
    reachability_context: _ActivationReachabilityContext,
    a: int,
    section_start: int,
    run_start: int,
    n: int,
    timestamps: np.ndarray,
    perfect_ts: np.ndarray,
    great_ts: np.ndarray,
) -> tuple[int, float] | None:
    hit_hi = float(great_ts[int(a)])
    hit_lo = float(reachability_context.late_great_floor_timestamps[int(a)])
    max_great_end = int(a) + 1
    while max_great_end < int(n) and float(perfect_ts[int(max_great_end)]) < hit_hi:
        max_great_end += 1
    for great_end in range(int(a) + 1, int(max_great_end) + 1):
        hit = _latest_activation_hit_for_labels(
            a=int(a),
            hit_lo=float(hit_lo),
            hit_hi=float(hit_hi),
            great_start=int(run_start),
            great_count=int(great_end) - int(run_start),
            n=int(n),
            timestamps=timestamps,
            perfect_ts=perfect_ts,
            great_ts=great_ts,
        )
        if hit is None:
            continue
        if _activation_reachable(
            context=reachability_context,
            a=int(a),
            hit=float(hit),
            section_start=int(section_start),
            great_start=int(run_start),
            great_count=int(great_end) - int(run_start),
            activation_great=True,
            n=int(n),
        ):
            return int(great_end), float(hit)
    return None


def _great_floor_end(
    start_time: float, a: int, *, great_floor_timestamps: np.ndarray, real_fever_time: float, n: int
) -> int:
    # Issue #44: the early-Great extended fever end -- searchsorted of the earliest-Great
    # floor at the SAME cutoff `start_time + rft`, clamped to (a, n]. Always >= the Perfect/
    # late end (Great reaches earlier).
    ee = _lower_bound_from(great_floor_timestamps, float(start_time) + float(real_fever_time))
    if int(ee) <= int(a):
        ee = int(a) + 1
    if int(ee) > int(n):
        ee = int(n)
    return int(ee)


def _section_option(
    *, k: int, judgment: str, forced: dict[str, int], surface: Any, witness: dict[str, Any], timestamps: np.ndarray,
    n: int,
) -> dict[str, Any]:
    """One candidate fever section: activation `witness["activation_idx"]`, end `witness["target_end"]`."""
    a = int(witness["activation_idx"])
    e = int(witness["target_end"])
    return {
        "k": int(k),
        "next_state": e,
        "activation_index": a,
        "activation_ms": float(witness["chart_time"]) * 1000.0,
        "activation_judgment": judgment,
        **forced,
        "fever_end_index": e,
        "fever_end_ms": None if e >= int(n) else float(timestamps[e]) * 1000.0,
        "surface": surface,
        "_witness": witness,
    }


class _ActionRow(NamedTuple):
    """One action of a section start (_numba_trace_edge_action_arrays): its forced Greats k, fill and forced count; its
    activation note a and chart time; its Perfect activation (hit window low end, latest hit if any, reachable, end e,
    the start time of its fever, the end of its early-Great tail); its late-Great activation (floor, hit, the forced
    prefix it needs (< 0: none schedulable), its end and early-Great tail end)."""

    k: int
    fill: int
    forced: int
    a: int
    chart_time: float
    hit_lo: float
    perfect_hit: float | None
    perfect_reachable: bool
    e: int
    start_time: float
    eg_e: int
    late_lo: float
    late_hit: float
    lg_prefix: int
    late_e: int
    late_eg_e: int


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
            int(option["next_state"]),
            int(option["activation_index"]),
            str(option["activation_judgment"]),
            int(option["forced_run_start_index"]),
            int(option["forced_run_count"]),
            int(option.get("early_great_start", -1)),
            int(option.get("early_great_end", -1)),
        )
        if key not in self.seen:
            self.seen.add(key)
            self.out.append(option)

    def family(
        self, base: dict[str, Any], *, early_great_end: int, great_start: int, great_end: int, activation_great_idx: int
    ) -> None:
        """`base`, a section from its activation to its end; then one option per later end up to `early_great_end`
        whose tail past the end is fever-great (issue #44: the base witness still reproduces the end); then the
        activation ending its fever early: hit from its earliest legal hit (a Perfect's floor, a late Great's late-Great
        floor), at every end from which the later notes can still be hit past its cutoff."""
        a, end = int(base["activation_index"]), int(base["next_state"])
        timestamps = self.context.timestamps
        self.emit(base)
        for ee in range(end + 1, int(early_great_end) + 1):
            option = dict(base)
            option.update(
                next_state=ee,
                fever_end_index=ee,
                fever_end_ms=None if ee >= self.n else float(timestamps[ee]) * 1000.0,
                early_great_start=end,
                early_great_end=ee,
                surface=_edge_surface(
                    n=self.n, fever_start=a, fever_end=ee, great_start=int(great_start), great_end=int(great_end),
                    activation_great_idx=int(activation_great_idx), early_great_start=end, early_great_end=ee,
                ),
                _witness=dict(base["_witness"]),
            )
            self.emit(option)
        lo = float(
            self.context.perfect_floor_timestamps[a]
            if int(activation_great_idx) < 0
            else self.context.late_great_floor_timestamps[a]
        )
        exit_lo = _lower_bound_from(self.context.exit_ceiling_timestamps, lo + float(self.real_fever_time))
        for ee in range(min(max(int(exit_lo), a + 1), end), end):
            option = dict(base)
            option.update(
                next_state=ee,
                fever_end_index=ee,
                fever_end_ms=float(timestamps[ee]) * 1000.0,
                surface=_edge_surface(
                    n=self.n, fever_start=a, fever_end=ee, great_start=int(great_start), great_end=int(great_end),
                    activation_great_idx=int(activation_great_idx),
                ),
                _witness={**base["_witness"], "lo": lo, "target_end": ee, "early_exit": True},
            )
            self.emit(option)


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
) -> list[dict[str, Any]]:
    """Enumerate the candidate fever sections of the section start after state `i` (the first section when `first`)
    with their response-surface edges: per action of the frontier's action table (its `fills` and `forced` counts for
    this kind of section), its Perfect activation, its late-Great activation and its region runs.

    Witness timing fields are intentionally absent here: computing the centered activation witness
    (`_centered_hit_window_for_exit`) is the expensive part and only sections accepted into the final trace need it.
    Callers attach it with `_option_with_witness` once an option is accepted.
    """
    n = int(context.timestamps.shape[0])
    section_start = 0 if first else int(i) + 1
    # One batched numba pass over the action loop's per-action scalar precompute (the prefix + late-Great families);
    # every emit/dedup/dict decision and the region-run family stay below, driven by these arrays.
    (
        act_err, act_a, act_chart, act_hit_lo, act_perfect_hit, act_perfect_hit_ok, act_perfect_reachable, act_e,
        act_start_time, act_eg_e, act_late_lo, act_late_hit, act_lg_prefix, act_late_e, _act_late_start, act_late_eg_e,
    ) = _rb_numba._numba_trace_edge_action_arrays(
        np.asarray(actions, dtype=np.int64),
        np.asarray(fills, dtype=np.int64),
        np.asarray(forced, dtype=np.int64),
        int(bool(first)),
        int(i),
        n,
        context.timestamps,
        context.perfect_candidate_timestamps,
        context.great_candidate_timestamps,
        context.perfect_floor_timestamps,
        context.great_floor_timestamps,
        context.late_great_floor_timestamps,
        context.lanes,
        float(context.fever_fill_denom),
        float(real_fever_time),
    )
    if bool(np.any(act_err)):
        raise ValueError("FG activation reachability received invalid section bounds")
    options = _SectionOptions(context, float(real_fever_time), n)
    prev_fill, prev_start_time, prev_e = -1, -1.0, -1
    for idx in range(int(act_a.shape[0])):
        action = _ActionRow(
            k=int(actions[idx]), fill=int(fills[idx]), forced=int(forced[idx]), a=int(act_a[idx]),
            chart_time=float(act_chart[idx]), hit_lo=float(act_hit_lo[idx]),
            perfect_hit=float(act_perfect_hit[idx]) if int(act_perfect_hit_ok[idx]) else None,
            perfect_reachable=bool(act_perfect_reachable[idx]), e=int(act_e[idx]),
            start_time=float(act_start_time[idx]), eg_e=int(act_eg_e[idx]), late_lo=float(act_late_lo[idx]),
            late_hit=float(act_late_hit[idx]), lg_prefix=int(act_lg_prefix[idx]), late_e=int(act_late_e[idx]),
            late_eg_e=int(act_late_eg_e[idx]),
        )
        if action.perfect_reachable and (
            action.fill != prev_fill or (action.start_time != prev_start_time and action.e != prev_e)
        ):
            _perfect_activation(options, action, section_start)
        # Late-Great activation, single-sourced with the search's `_compact_first_frontier_action_arrays` via
        # `late_great_activation_prefix`: lg_prefix < 0 encodes both "no late-Great placement" and "placement not
        # scheduleable".
        if use_forced_great_timing and idx > 0 and int(fills[idx - 1]) == action.fill and action.lg_prefix >= 0:
            _late_great_activation(options, action, section_start)
        if use_forced_great_timing and action.k > 0:
            _region_runs(options, action, section_start)
        prev_fill, prev_start_time, prev_e = action.fill, action.start_time, action.e
    return options.out


def _perfect_activation(options: _SectionOptions, action: _ActionRow, section_start: int) -> None:
    """The action's section activated by a Perfect, its forced Greats from the section start."""
    n = options.n
    great_end = min(n, int(section_start) + action.forced)
    options.family(
        _section_option(
            k=action.k,
            judgment="perfect",
            forced=_forced_fields(
                section_start=int(section_start), great_start=int(section_start), great_count=action.forced, n=n
            ),
            surface=_edge_surface(
                n=n, fever_start=action.a, fever_end=action.e, great_start=int(section_start), great_end=great_end
            ),
            witness={
                "activation_idx": action.a,
                "chart_time": action.chart_time,
                "lo": action.hit_lo,
                "hi": float(action.perfect_hit),
                "target_end": action.e,
                "carry_idx": -1,
                "activation_great": False,
            },
            timestamps=options.context.timestamps,
            n=n,
        ),
        early_great_end=action.eg_e,
        great_start=int(section_start),
        great_end=great_end,
        activation_great_idx=-1,
    )


def _late_great_activation(options: _SectionOptions, action: _ActionRow, section_start: int) -> None:
    """The action's section activated by a late Great after its forced-Great prefix, when it reaches past the Perfect
    activation's end or early-Great tail."""
    if action.late_e <= action.e and action.late_eg_e <= action.eg_e:
        return
    n = options.n
    great_end = min(n, int(section_start) + action.lg_prefix)
    options.family(
        _section_option(
            k=action.k,
            judgment="late_great",
            forced=_forced_fields(
                section_start=int(section_start), great_start=int(section_start), great_count=action.lg_prefix, n=n
            ),
            surface=_edge_surface(
                n=n, fever_start=action.a, fever_end=action.late_e, great_start=int(section_start),
                great_end=great_end, activation_great_idx=action.a,
            ),
            witness={
                "activation_idx": action.a,
                "chart_time": action.chart_time,
                "lo": action.late_lo,
                "hi": action.late_hit,
                "target_end": action.late_e,
                "carry_idx": action.a,
                "activation_great": True,
            },
            timestamps=options.context.timestamps,
            n=n,
        ),
        early_great_end=action.late_eg_e,
        great_start=int(section_start),
        great_end=great_end,
        activation_great_idx=action.a,
    )


def _region_runs(options: _SectionOptions, action: _ActionRow, section_start: int) -> None:
    """The action's sections whose k forced Greats run from later in the section: each run's fill crossing activates
    by a Great or a Perfect (the run from the section start crossing at the action's own activation is that action)."""
    n = options.n
    raw_fever_fill = float(options.context.fever_fill_denom)
    for offset in _region_run_offsets(
        section_start=int(section_start), k=action.k, n=n, raw_fever_fill=raw_fever_fill
    ):
        run_start = int(section_start) + int(offset)
        crossing, crossing_is_great = server_fill_crossing_run(
            int(section_start), int(run_start), action.k, raw_fever_fill, n
        )
        if crossing is None:
            continue
        a = int(crossing)
        if a >= n or (a == action.a and run_start == int(section_start)):
            continue
        if bool(crossing_is_great):
            _great_region_run(options, a, int(section_start), run_start)
        else:
            _perfect_region_run(options, action.k, a, int(section_start), run_start)


def _great_region_run(options: _SectionOptions, a: int, section_start: int, run_start: int) -> None:
    """A region run crossing by a late Great at `a`: its minimal reachable Great run, kept when it ends later than the
    Perfect activation of the same run (or its early-Great tail reaches further)."""
    context, n, real_fever_time = options.context, options.n, float(options.real_fever_time)
    ts, perfect_ts = context.timestamps, context.perfect_candidate_timestamps
    found = _minimal_reachable_region_great_end(
        reachability_context=context, a=a, section_start=section_start, run_start=run_start, n=n, timestamps=ts,
        perfect_ts=perfect_ts, great_ts=context.great_candidate_timestamps,
    )
    if found is None:
        return
    great_end, activation_hit = found
    activation_e, activation_start_time, carry_idx = _edge_end_at_hit(
        n=n, a=a, hit=float(activation_hit), activation_great=True, real_fever_time=real_fever_time,
        perfect_floor_timestamps=context.perfect_floor_timestamps,
    )
    perfect_hit = _latest_activation_hit_for_labels(
        a=a,
        hit_lo=min(float(ts[a]), float(perfect_ts[a])),
        hit_hi=max(float(ts[a]), float(perfect_ts[a])),
        great_start=run_start,
        great_count=int(great_end) - run_start,
        n=n,
        timestamps=ts,
        perfect_ts=perfect_ts,
        great_ts=context.great_candidate_timestamps,
    )
    perfect_e = -1 if perfect_hit is None else _edge_end_at_hit(
        n=n, a=a, hit=float(perfect_hit), activation_great=False, real_fever_time=real_fever_time,
        perfect_floor_timestamps=context.perfect_floor_timestamps,
    )[0]
    tail_end = _great_floor_end(
        float(activation_start_time), a, great_floor_timestamps=context.great_floor_timestamps,
        real_fever_time=real_fever_time, n=n,
    )
    if int(activation_e) <= int(perfect_e) and not (
        perfect_hit is not None
        and tail_end > _great_floor_end(
            float(perfect_hit), a, great_floor_timestamps=context.great_floor_timestamps,
            real_fever_time=real_fever_time, n=n,
        )
    ):
        return
    great_count = int(great_end) - run_start
    options.family(
        _section_option(
            k=great_count,
            judgment="late_great",
            forced=_forced_fields(section_start=section_start, great_start=run_start, great_count=great_count, n=n),
            surface=_edge_surface(
                n=n, fever_start=a, fever_end=int(activation_e), great_start=run_start, great_end=int(great_end),
                activation_great_idx=a,
            ),
            witness={
                "activation_idx": a,
                "chart_time": float(ts[a]),
                "lo": float(context.late_great_floor_timestamps[a]),
                "hi": float(activation_hit),
                "target_end": int(activation_e),
                "carry_idx": int(carry_idx),
                "activation_great": True,
            },
            timestamps=ts,
            n=n,
        ),
        early_great_end=tail_end,
        great_start=run_start,
        great_end=int(great_end),
        activation_great_idx=a,
    )


def _perfect_region_run(options: _SectionOptions, k: int, a: int, section_start: int, run_start: int) -> None:
    """A region run of k forced Greats crossing by a Perfect at `a`, when the input engine can reach its latest hit."""
    context, n, real_fever_time = options.context, options.n, float(options.real_fever_time)
    ts, perfect_ts = context.timestamps, context.perfect_candidate_timestamps
    great_end = min(n, run_start + int(k))
    if great_end <= run_start:
        return
    great_count = great_end - run_start
    hit = _latest_activation_hit_for_labels(
        a=a,
        hit_lo=min(float(ts[a]), float(perfect_ts[a])),
        hit_hi=max(float(ts[a]), float(perfect_ts[a])),
        great_start=run_start,
        great_count=great_count,
        n=n,
        timestamps=ts,
        perfect_ts=perfect_ts,
        great_ts=context.great_candidate_timestamps,
    )
    if hit is None or not _activation_reachable(
        context=context, a=a, hit=float(hit), section_start=section_start, great_start=run_start,
        great_count=great_count, activation_great=False, n=n,
    ):
        return
    e, start_time, carry_idx = _edge_end_at_hit(
        n=n, a=a, hit=float(hit), activation_great=False, real_fever_time=real_fever_time,
        perfect_floor_timestamps=context.perfect_floor_timestamps,
    )
    chart_time = float(ts[a])
    options.family(
        _section_option(
            k=great_count,
            judgment="perfect",
            forced=_forced_fields(section_start=section_start, great_start=run_start, great_count=great_count, n=n),
            surface=_edge_surface(n=n, fever_start=a, fever_end=int(e), great_start=run_start, great_end=great_end),
            witness={
                "activation_idx": a,
                "chart_time": chart_time,
                "lo": min(chart_time, float(perfect_ts[a])),
                "hi": float(hit),
                "target_end": int(e),
                "carry_idx": int(carry_idx),
                "activation_great": False,
            },
            timestamps=ts,
            n=n,
        ),
        early_great_end=_great_floor_end(
            float(start_time), a, great_floor_timestamps=context.great_floor_timestamps,
            real_fever_time=real_fever_time, n=n,
        ),
        great_start=run_start,
        great_end=great_end,
        activation_great_idx=-1,
    )


def _option_with_witness(
    option: dict[str, Any],
    *,
    reachability_context: _ActivationReachabilityContext,
    n: int,
    real_fever_time: float,
    perfect_floor_timestamps: np.ndarray,
) -> dict[str, Any]:
    """Attach the centered activation-witness fields to one accepted option.

    Produces the historical field layout (witness hit-window fields after the
    judgment, timing fields after fever_end_ms) so persisted trace rows are
    unchanged.
    """
    w = option["_witness"]
    centered_start_time, hit_lo, hit_hi = _centered_hit_window_for_exit(
        int(n), int(w["activation_idx"]),
        float(w["lo"]), float(w["hi"]),
        float(real_fever_time), int(w["target_end"]),
        perfect_floor_timestamps,
        reachability_context.exit_ceiling_timestamps if w.get("early_exit") else None,
    )
    activation_idx = int(option["activation_index"])
    section_start = int(option["forced_start_index"])
    run_start = int(option["forced_run_start_index"])
    run_end = min(int(n), int(run_start) + int(option["forced_run_count"]))
    is_great = np.zeros(int(n), dtype=np.bool_)
    is_great[max(0, int(run_start)) : max(0, int(run_end))] = True
    if str(option["activation_judgment"]) == "late_great":
        is_great[int(activation_idx)] = True
    labels = exact_label_hit_intervals(
        is_great=is_great,
        timestamps=reachability_context.timestamps,
        perfect_floor_timestamps=reachability_context.perfect_floor_timestamps,
        perfect_candidate_timestamps=reachability_context.perfect_candidate_timestamps,
        great_floor_timestamps=reachability_context.great_floor_timestamps,
        great_candidate_timestamps=reachability_context.great_candidate_timestamps,
    )
    preactivation_event_count = int(activation_idx) - int(section_start)
    preactivation_great_count = max(
        0,
        min(int(activation_idx), int(run_end)) - max(int(section_start), int(run_start)),
    )
    preactivation_fill_half = (
        2 * int(preactivation_event_count) - int(preactivation_great_count)
    )
    schedule_rows = activation_schedule_witnesses(
        labels=labels,
        lanes=reachability_context.lanes,
        activation_index=int(activation_idx),
        activation_hit_timestamp=float(centered_start_time),
        fever_fill_denom=float(reachability_context.fever_fill_denom),
        section_start=int(section_start),
        predecessor_hit_timestamp=(
            None
            if int(section_start) == 0
            else float(reachability_context.perfect_floor_timestamps[int(section_start) - 1])
        ),
        required_signature=(int(preactivation_fill_half), int(preactivation_event_count)),
    )
    if len(schedule_rows) != 1:
        raise ValueError(
            "FG accepted edge has no unique exact lane-prefix witness for its scored surface"
        )
    schedule = schedule_rows[0]
    return {
        "k": option["k"],
        "next_state": option["next_state"],
        "activation_index": option["activation_index"],
        "activation_ms": option["activation_ms"],
        "activation_judgment": option["activation_judgment"],
        **_hit_window_fields(
            hit=float(centered_start_time),
            lo=float(hit_lo),
            hi=float(hit_hi),
            chart_time=float(w["chart_time"]),
        ),
        "forced_start_index": option["forced_start_index"],
        "forced_run_start_index": option["forced_run_start_index"],
        "forced_run_count": option["forced_run_count"],
        "fever_end_index": option["fever_end_index"],
        "fever_end_ms": option["fever_end_ms"],
        "fever_duration_ms": float(real_fever_time) * 1000.0,
        # The cutoff belongs to the materialized activation witness, not another legal point in
        # its interval. Endpoint guidance may move boundary notes earlier to realize the selected
        # surface, but activation and cutoff must describe one physical play.
        "fever_window_end_ms": (float(centered_start_time) + float(real_fever_time)) * 1000.0,
        **_trace_timing_fields(
            carry_idx=int(w["carry_idx"]),
            start_time=float(centered_start_time),
            chart_time=float(w["chart_time"]),
            activation_idx=int(w["activation_idx"]),
            activation_great=bool(w["activation_great"]),
        ),
        # Issue #44: the early-Great tail [early_great_start, early_great_end) -- boundary notes
        # this section pulls into fever as Greats (default -1/-1 = none). The per-note early-Great
        # hit offsets are stamped by the note-graph layer (like #42's endpoint-early Perfect hits).
        "early_great_start": int(option.get("early_great_start", -1)),
        "early_great_end": int(option.get("early_great_end", -1)),
        "activation_schedule_schema_version": 1,
        "preactivation_order": [int(index) for index in schedule.preactivation_order],
        "preactivation_lane_prefixes": [
            {"lane": int(row.lane), "count": len(row.note_indices)}
            for row in schedule.lane_prefixes
        ],
        "preactivation_fill_half_units": int(schedule.preactivation_fill_half_units),
        "preactivation_event_count": int(schedule.preactivation_event_count),
        "preactivation_great_count": int(schedule.preactivation_great_count),
        "surface": option["surface"],
    }


def _empty(words: tuple[int, ...]) -> bool:
    return not any(int(value) for value in words)


def _subtract_edge(words: tuple[int, ...], edge: FgResponseSurface) -> tuple[int, ...] | None:
    """The surface words left after an edge's (head bits and body counts); None when the edge does not fit."""
    edge_values = tuple(int(value) for value in edge)
    if any(edge_values[idx] & ~words[idx] for idx in range(8)) or any(
        edge_values[idx] > words[idx] for idx in range(8, 11)
    ):
        return None
    return tuple(words[idx] & ~edge_values[idx] for idx in range(8)) + tuple(
        words[idx] - edge_values[idx] for idx in range(8, 11)
    )


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
    n = int(np.asarray(inputs.timestamps).reshape(-1).shape[0])
    if n <= 0 or target_surface == _EMPTY_SURFACE:
        return ()
    use_forced_great_timing = bool(inputs.use_forced_great_timing)
    ts, perfect_ts, great_ts, floor_ts, great_floor_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr = song_arrays(
        inputs.timestamps, inputs.perfect_candidates, inputs.great_candidates, inputs.perfect_floor,
        inputs.great_floor, inputs.late_great_floor, inputs.exit_ceiling, inputs.lanes,
    )
    if max(1, ceil(float(raw_fever_fill))) < early_exit_min_fill(floor_ts, perfect_ts):
        exit_ceiling_ts = np.full_like(exit_ceiling_ts, -np.inf)  # as the search: no early exits at this fill
    reachability_context: _ActivationReachabilityContext | None = None

    def _reachability_context() -> _ActivationReachabilityContext:
        nonlocal reachability_context
        if reachability_context is None:
            reachability_context = _build_activation_reachability_context(
                timestamps=ts,
                perfect_floor_timestamps=floor_ts,
                perfect_candidate_timestamps=perfect_ts,
                great_floor_timestamps=great_floor_ts,
                great_candidate_timestamps=great_ts,
                late_great_floor_timestamps=late_great_floor_ts,
                exit_ceiling_timestamps=exit_ceiling_ts,
                lanes=lane_arr,
                fever_fill_denom=float(raw_fever_fill),
            )
        return reachability_context

    actions, later_fill, first_fill, later_forced, first_forced = action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=int(non_fever_base),
        use_forced_great_timing=bool(use_forced_great_timing),
    )

    target_words = tuple(int(value) for value in target_surface)
    # The ordered edge list is independent of the target surface. A materialization batch can
    # therefore reuse it across the up-to-51 exact surfaces for one song/stat geometry. Keep the
    # cache song-local and bounded: eviction only regenerates an identical ordered tuple.
    shared_edge_options = edge_options_cache if edge_options_cache is not None else FgTraceEdgeOptionsCache()
    shared_edge_options.bind_inputs(
        owner_inputs=(
            inputs.timestamps,
            inputs.perfect_candidates,
            inputs.great_candidates,
            inputs.perfect_floor,
            inputs.great_floor,
            inputs.late_great_floor,
            inputs.exit_ceiling,
            inputs.lanes,
        ),
        note_count=n,
    )
    edge_cache_prefix = (
        int(non_fever_base),
        float(raw_fever_fill),
        float(real_fever_time),
        bool(use_forced_great_timing),
    )

    memo: set[tuple[int, bool, tuple[int, ...]]] = set()

    def _accepted_section(option: dict[str, Any], edge: FgResponseSurface) -> dict[str, Any]:
        # The centered witness is computed only here — for sections accepted
        # into the final trace — not for every option the DFS explores.
        section = dict(
            _option_with_witness(
                option,
                reachability_context=_reachability_context(),
                n=int(n),
                real_fever_time=float(real_fever_time),
                perfect_floor_timestamps=floor_ts,
            )
        )
        section.pop("surface", None)
        section["forced_count"] = int(section.pop("k"))
        section["body_fever"] = int(edge.body_fever)
        section["body_great"] = int(edge.body_great)
        section["body_fever_great"] = int(edge.body_fever_great)
        return section

    def _search(state: int, first: bool, remaining: tuple[int, ...]) -> tuple[dict[str, Any], ...] | None:
        if _empty(remaining):
            return ()
        key = (int(state), bool(first), remaining)
        if key in memo:
            return None
        found: tuple[dict[str, Any], ...] | None = None

        def _visit(option: dict[str, Any]) -> bool:
            nonlocal found
            edge = option["surface"]
            next_remaining = _subtract_edge(remaining, edge)
            if next_remaining is None:
                return False
            if _empty(next_remaining):
                found = (_accepted_section(option, edge),)
                return True
            if int(option["next_state"]) >= int(n):
                return False
            tail = _search(int(option["next_state"]), False, next_remaining)
            if tail is not None:
                found = (_accepted_section(option, edge),) + tail
                return True
            return False

        edge_cache_key = (*edge_cache_prefix, int(state), bool(first))
        options = shared_edge_options.get(edge_cache_key)
        if options is None:
            options = tuple(
                _edge_surface_options(
                    context=_reachability_context(),
                    i=int(state),
                    first=bool(first),
                    actions=actions,
                    fills=first_fill if first else later_fill,
                    forced=first_forced if first else later_forced,
                    real_fever_time=float(real_fever_time),
                    use_forced_great_timing=bool(use_forced_great_timing),
                )
            )
            shared_edge_options.put(edge_cache_key, options)
        for option in options:
            if _visit(option):
                break
        if found is not None:
            return found
        memo.add(key)
        return None

    trace = _search(0, True, target_words)
    if trace is None:
        raise ValueError("could not reconstruct FG response surface trace")
    return tuple({**dict(row), "section": idx + 1} for idx, row in enumerate(trace))
