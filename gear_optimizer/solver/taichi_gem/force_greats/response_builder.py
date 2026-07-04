from __future__ import annotations

from typing import Any

import numpy as np

from .fill_crossing import (
    late_great_activation_is_reachable,
    late_great_activation_prefix,
    perfect_fill_crossing_offset,
)
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE


def _action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    last_fill: int | None = None
    for k in range(max(0, int(non_fever_base)) + 1):
        fill = perfect_fill_crossing_offset(float(raw_fever_fill), int(k), first=False)
        if bool(use_forced_great_timing) or last_fill is None or fill != last_fill:
            fill_first = perfect_fill_crossing_offset(float(raw_fever_fill), int(k), first=True)
            actions.append(int(k))
            later_fill.append(int(fill))
            first_fill.append(int(fill_first))
            later_forced.append(min(int(k), int(fill)))
            first_forced.append(min(int(k), int(fill_first)))
        last_fill = int(fill)
    if not actions:
        actions.append(0)
        later_fill.append(0)
        first_fill.append(0)
        later_forced.append(0)
        first_forced.append(0)
    return actions, later_fill, first_fill, later_forced, first_forced


def _lower_bound_from(timestamps: np.ndarray, value: float) -> int:
    return int(np.searchsorted(timestamps, np.float32(value), side="left", sorter=None))


def _edge_end(
    *,
    n: int,
    a: int,
    activation_great: bool,
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray | None = None,
    great_candidate_timestamps: np.ndarray | None = None,
    perfect_floor_timestamps: np.ndarray,
) -> tuple[int, float, int]:
    perfect_ts = timestamps if perfect_candidate_timestamps is None else perfect_candidate_timestamps
    great_ts = timestamps if great_candidate_timestamps is None else great_candidate_timestamps
    # Endpoint-early fever inclusion (issue #42): the boundary searches the earliest-Perfect
    # floor envelope, not chart, so a boundary note within early-hit reach of the cutoff is
    # counted in fever. The cutoff VALUE (start_time = latest Perfect / late Great) is unchanged.
    floor_ts = perfect_floor_timestamps
    start_time = float(perfect_ts[int(a)])
    carry_idx = -1
    if bool(use_forced_great_timing) and bool(activation_great) and int(a) < int(n):
        activation_t = float(great_ts[int(a)])
        if activation_t > start_time:
            start_time = activation_t
            carry_idx = int(a)
    e = _lower_bound_from(floor_ts, start_time + float(real_fever_time))
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
        source = "perfect_window"
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
    timestamps: np.ndarray, n: int, activation_idx: int, chart_time: float,
    legal_lo: float, legal_hi: float, real_fever_time: float, target_end_idx: int,
    perfect_floor_timestamps: np.ndarray,
) -> tuple[float, float, float]:
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

    def _last_order_with_exit_at_most(first_order: int, last_order: int, expected: int) -> int | None:
        lo_order = int(first_order)
        hi_order = int(last_order)
        found: int | None = None
        while lo_order <= hi_order:
            mid = (lo_order + hi_order) // 2
            if _exit_idx(_hit_from_order(mid)) <= int(expected):
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
    if _exit_idx(midpoint_hit) == int(target):
        return float(midpoint_hit), float(first_hit), float(last_hit)

    candidate_order = (int(first_order) + int(last_order)) // 2
    candidate = _hit_from_order(int(candidate_order))
    if _exit_idx(candidate) == int(target):
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


def _edge_surface_options(
    *,
    i: int,
    first: bool,
    n: int,
    actions: list[int],
    later_fill: list[int],
    first_fill: list[int],
    later_forced: list[int],
    first_forced: list[int],
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray | None = None,
    great_candidate_timestamps: np.ndarray | None = None,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    raw_fever_fill: float,
) -> list[dict[str, Any]]:
    """Enumerate candidate fever sections with their response-surface edges.

    Witness timing fields are intentionally absent here: computing the centered
    activation witness (`_centered_hit_window_for_exit`) is the expensive part
    and only sections accepted into the final trace need it. Callers attach it
    with `_option_with_witness` once an option is accepted.
    """
    out: list[dict[str, Any]] = []
    fills = first_fill if first else later_fill
    forced_values = first_forced if first else later_forced
    prev_fill = -1
    prev_start_time = -1.0
    prev_e = -1
    perfect_ts = timestamps if perfect_candidate_timestamps is None else perfect_candidate_timestamps
    great_ts = timestamps if great_candidate_timestamps is None else great_candidate_timestamps

    def _great_floor_end(start_time: float, a: int) -> int:
        # Issue #44: the early-Great extended fever end -- searchsorted of the earliest-Great
        # floor at the SAME cutoff `start_time + rft`, clamped to (a, n]. Always >= the Perfect/
        # late end (Great reaches earlier).
        ee = _lower_bound_from(great_floor_timestamps, float(start_time) + float(real_fever_time))
        if int(ee) <= int(a):
            ee = int(a) + 1
        if int(ee) > int(n):
            ee = int(n)
        return int(ee)

    def _early_great_options(base: dict[str, Any], base_e: int, eg_e: int, *, a: int,
                             forced_start: int, forced_great_end: int, activation_great_idx: int) -> None:
        # One Pareto surface per end ee in (base_e, eg_e]; the tail [base_e, ee) is fever-great.
        # The activation witness is unchanged (it still reproduces the Perfect/late extent
        # base_e), so reuse the base witness (its target_end is already base_e).
        for ee in range(int(base_e) + 1, int(eg_e) + 1):
            opt = dict(base)
            opt["next_state"] = int(ee)
            opt["fever_end_index"] = int(ee)
            opt["fever_end_ms"] = None if int(ee) >= int(n) else float(timestamps[int(ee)]) * 1000.0
            opt["early_great_start"] = int(base_e)
            opt["early_great_end"] = int(ee)
            opt["surface"] = _edge_surface(
                n=int(n),
                fever_start=int(a),
                fever_end=int(ee),
                great_start=int(forced_start),
                great_end=int(forced_great_end),
                activation_great_idx=int(activation_great_idx),
                early_great_start=int(base_e),
                early_great_end=int(ee),
            )
            opt["_witness"] = dict(base["_witness"])
            out.append(opt)

    for action_idx, k in enumerate(actions):
        fill = int(fills[action_idx])
        a = int(fill if first else int(i) + fill)
        if a >= n:
            break
        forced_start = 0 if first else int(i) + 1
        forced_applied = int(forced_values[action_idx])
        e, start_time, carry_idx = _edge_end(
            n=int(n),
            a=int(a),
            activation_great=False,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
        )
        if fill != prev_fill or (start_time != prev_start_time and e != prev_e):
            chart_time = float(timestamps[int(a)])
            great_end = min(int(n), int(forced_start) + int(forced_applied))
            out.append(
                {
                    "k": int(k),
                    "next_state": int(e),
                    "activation_index": int(a),
                    "activation_ms": float(chart_time) * 1000.0,
                    "activation_judgment": "perfect",
                    "forced_start_index": int(forced_start),
                    "forced_prefix_count": int(forced_applied),
                    "fever_end_index": int(e),
                    "fever_end_ms": None if int(e) >= int(n) else float(timestamps[int(e)]) * 1000.0,
                    "surface": _edge_surface(
                        n=int(n),
                        fever_start=int(a),
                        fever_end=int(e),
                        great_start=int(forced_start),
                        great_end=int(great_end),
                    ),
                    "_witness": {
                        "activation_idx": int(a),
                        "chart_time": float(chart_time),
                        "lo": min(float(chart_time), float(perfect_ts[int(a)])),
                        "hi": max(float(chart_time), float(perfect_ts[int(a)])),
                        "target_end": int(e),
                        "carry_idx": int(carry_idx),
                        "activation_great": False,
                    },
                }
            )
            # Issue #44: early-Great extension of the Perfect-activation section.
            _early_great_options(
                out[-1], int(e), _great_floor_end(float(start_time), int(a)),
                a=int(a), forced_start=int(forced_start), forced_great_end=int(great_end),
                activation_great_idx=-1,
            )
        # Late-Great activation, single-sourced with the search's `_compact_first_frontier_action_arrays`
        # via `late_great_activation_prefix`: the forced-Great prefix when the activation Great IS the
        # server fill-crossing, or None when a Perfect crosses first (a phantom over-report). Same O(1)
        # owner both paths call, so the placement math lives in exactly one place.
        lg_prefix = late_great_activation_prefix(int(fill), int(k), first=bool(first), fever_fill_denom=float(raw_fever_fill))
        # Hit-time reachability: the index gate above can bless a late-Great activation whose bar is
        # actually completed first by an earlier-hit same-timestamp sibling (the chord phantom). Drop
        # it here so the reconstruct emits only reachable surfaces; off overlap this is a bit-exact
        # no-op (the correction is 0) so non-chord charts are unchanged.
        if lg_prefix is not None and not late_great_activation_is_reachable(
            int(a), timestamps, perfect_ts, great_ts, int(n)
        ):
            lg_prefix = None
        if (
            bool(use_forced_great_timing)
            and int(action_idx) > 0
            and int(fills[action_idx - 1]) == int(fill)
            and lg_prefix is not None
        ):
            prefix_forced = int(lg_prefix)
            activation_e, _activation_start_time, activation_carry_idx = _edge_end(
                n=int(n),
                a=int(a),
                activation_great=True,
                real_fever_time=float(real_fever_time),
                use_forced_great_timing=bool(use_forced_great_timing),
                timestamps=timestamps,
                perfect_candidate_timestamps=perfect_candidate_timestamps,
                great_candidate_timestamps=great_candidate_timestamps,
                perfect_floor_timestamps=perfect_floor_timestamps,
            )
            if int(activation_e) > int(e):
                chart_time = float(timestamps[int(a)])
                great_hi = float(great_ts[int(a)])
                late_lo = float(np.float32(np.float32(perfect_ts[int(a)]) + np.float32(0.001)))
                activation_surface = _edge_surface(
                    n=int(n),
                    fever_start=int(a),
                    fever_end=int(activation_e),
                    great_start=int(forced_start),
                    great_end=min(int(n), int(forced_start) + int(prefix_forced)),
                    activation_great_idx=int(a),
                )
                out.append(
                    {
                        "k": int(k),
                        "next_state": int(activation_e),
                        "activation_index": int(a),
                        "activation_ms": float(chart_time) * 1000.0,
                        "activation_judgment": "late_great",
                        "forced_start_index": int(forced_start),
                        "forced_prefix_count": int(prefix_forced),
                        "fever_end_index": int(activation_e),
                        "fever_end_ms": None
                        if int(activation_e) >= int(n)
                        else float(timestamps[int(activation_e)]) * 1000.0,
                        "surface": activation_surface,
                        "_witness": {
                            "activation_idx": int(a),
                            "chart_time": float(chart_time),
                            "lo": float(late_lo),
                            "hi": float(great_hi),
                            "target_end": int(activation_e),
                            "carry_idx": int(activation_carry_idx),
                            "activation_great": True,
                        },
                    }
                )
                # Issue #44: early-Great extension of the late-Great-activation section.
                _early_great_options(
                    out[-1], int(activation_e),
                    _great_floor_end(float(_activation_start_time), int(a)),
                    a=int(a), forced_start=int(forced_start),
                    forced_great_end=min(int(n), int(forced_start) + int(prefix_forced)),
                    activation_great_idx=int(a),
                )
        prev_fill = fill
        prev_start_time = start_time
        prev_e = e
    return out


def _option_with_witness(
    option: dict[str, Any],
    *,
    timestamps: np.ndarray,
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
        timestamps, int(n), int(w["activation_idx"]), float(w["chart_time"]),
        float(w["lo"]), float(w["hi"]),
        float(real_fever_time), int(w["target_end"]),
        perfect_floor_timestamps,
    )
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
        "forced_prefix_count": option["forced_prefix_count"],
        "fever_end_index": option["fever_end_index"],
        "fever_end_ms": option["fever_end_ms"],
        # Largest-cushion fever cutoff: the LATEST legal activation hit (`hit_hi`) plus the
        # fever duration -- this is the boundary `_edge_end` actually used to compute
        # `fever_end_index`, and it matches the base trace's `fever_window_end_ms`. It must NOT
        # use the centered display hit (which is earlier), or `_mark_endpoint_early_hits` would
        # flag notes reachable at delta 0 by hitting the activation late. Stats-free /
        # tier-invariant (start time + FT-derived duration).
        "fever_window_end_ms": (float(hit_hi) + float(real_fever_time)) * 1000.0,
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
        "surface": option["surface"],
    }


def _edge_surface_option_details(
    *,
    i: int,
    first: bool,
    n: int,
    actions: list[int],
    later_fill: list[int],
    first_fill: list[int],
    later_forced: list[int],
    first_forced: list[int],
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray | None = None,
    great_candidate_timestamps: np.ndarray | None = None,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    raw_fever_fill: float,
) -> list[dict[str, Any]]:
    """Full option details (surface edge + witness fields) for every option."""
    return [
        _option_with_witness(
            option,
            timestamps=timestamps,
            n=int(n),
            real_fever_time=float(real_fever_time),
            perfect_floor_timestamps=perfect_floor_timestamps,
        )
        for option in _edge_surface_options(
            i=int(i),
            first=bool(first),
            n=int(n),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
            great_floor_timestamps=great_floor_timestamps,
            raw_fever_fill=float(raw_fever_fill),
        )
    ]


def reconstruct_force_greats_response_counts(
    *,
    frontier: FgResponseFrontierResult,
    target_surface: FgResponseSurface,
    timestamps: Any,
    perfect_candidate_timestamps: Any | None = None,
    great_candidate_timestamps: Any | None = None,
    perfect_floor_timestamps: Any,
    great_floor_timestamps: Any,
    raw_fever_fill: float,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> tuple[int, ...]:
    # Thin adapter for the solve path, which has the full frontier in hand; forward only
    # the one field the reconstruction primitive consumes (its `non_fever_base`).
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(frontier.non_fever_base),
        target_surface=target_surface,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        raw_fever_fill=float(raw_fever_fill),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    return tuple(int(row["forced_count"]) for row in trace)


def reconstruct_force_greats_response_trace(
    *,
    non_fever_base: int,
    target_surface: FgResponseSurface,
    timestamps: Any,
    perfect_candidate_timestamps: Any | None = None,
    great_candidate_timestamps: Any | None = None,
    perfect_floor_timestamps: Any,
    great_floor_timestamps: Any,
    raw_fever_fill: float,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> tuple[dict[str, Any], ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0 or target_surface == _EMPTY_SURFACE:
        return ()
    perfect_ts = ts if perfect_candidate_timestamps is None else np.ascontiguousarray(
        np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    if int(perfect_ts.shape[0]) != n:
        raise ValueError("perfect_candidate_timestamps length must match timestamps")
    great_ts = ts if great_candidate_timestamps is None else np.ascontiguousarray(
        np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    if int(great_ts.shape[0]) != n:
        raise ValueError("great_candidate_timestamps length must match timestamps")
    # perfect_floor is the issue-#42 fever-boundary basis and is REQUIRED (no chart fallback):
    # silently searching chart would under-count endpoint-early fever -- a wrong best_fg_score.
    floor_ts = np.ascontiguousarray(np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(floor_ts.shape[0]) != n:
        raise ValueError("perfect_floor_timestamps length must match timestamps")
    # great_floor is the issue-#44 greats-side fever-boundary basis, REQUIRED for the same reason:
    # the early-Great extended surfaces cannot be reconstructed without it.
    great_floor_ts = np.ascontiguousarray(np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(great_floor_ts.shape[0]) != n:
        raise ValueError("great_floor_timestamps length must match timestamps")

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=int(non_fever_base),
        use_forced_great_timing=bool(use_forced_great_timing),
    )

    target_words = (
        int(target_surface.fever0),
        int(target_surface.fever1),
        int(target_surface.fever2),
        int(target_surface.fever3),
        int(target_surface.great0),
        int(target_surface.great1),
        int(target_surface.great2),
        int(target_surface.great3),
        int(target_surface.body_fever),
        int(target_surface.body_great),
        int(target_surface.body_fever_great),
    )

    def _empty(words: tuple[int, ...]) -> bool:
        return not any(int(value) for value in words)

    def _edge_words(edge: FgResponseSurface) -> tuple[int, ...]:
        return (
            int(edge.fever0),
            int(edge.fever1),
            int(edge.fever2),
            int(edge.fever3),
            int(edge.great0),
            int(edge.great1),
            int(edge.great2),
            int(edge.great3),
            int(edge.body_fever),
            int(edge.body_great),
            int(edge.body_fever_great),
        )

    def _subtract_edge(words: tuple[int, ...], edge: FgResponseSurface) -> tuple[int, ...] | None:
        edge_values = _edge_words(edge)
        for idx in range(8):
            if int(edge_values[idx]) & ~int(words[idx]):
                return None
        if (
            int(edge_values[8]) > int(words[8])
            or int(edge_values[9]) > int(words[9])
            or int(edge_values[10]) > int(words[10])
        ):
            return None
        return (
            int(words[0]) & ~int(edge_values[0]),
            int(words[1]) & ~int(edge_values[1]),
            int(words[2]) & ~int(edge_values[2]),
            int(words[3]) & ~int(edge_values[3]),
            int(words[4]) & ~int(edge_values[4]),
            int(words[5]) & ~int(edge_values[5]),
            int(words[6]) & ~int(edge_values[6]),
            int(words[7]) & ~int(edge_values[7]),
            int(words[8]) - int(edge_values[8]),
            int(words[9]) - int(edge_values[9]),
            int(words[10]) - int(edge_values[10]),
        )

    memo: set[tuple[int, bool, tuple[int, ...]]] = set()

    def _accepted_section(option: dict[str, Any], edge: FgResponseSurface) -> dict[str, Any]:
        # The centered witness is computed only here — for sections accepted
        # into the final trace — not for every option the DFS explores.
        section = dict(
            _option_with_witness(
                option,
                timestamps=ts,
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
        for option in _edge_surface_options(
            i=int(state),
            first=bool(first),
            n=int(n),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=ts,
            perfect_candidate_timestamps=perfect_ts,
            great_candidate_timestamps=great_ts,
            perfect_floor_timestamps=floor_ts,
            great_floor_timestamps=great_floor_ts,
            raw_fever_fill=float(raw_fever_fill),
        ):
            edge = option["surface"]
            next_remaining = _subtract_edge(remaining, edge)
            if next_remaining is None:
                continue
            if _empty(next_remaining):
                return (_accepted_section(option, edge),)
            if int(option["next_state"]) >= int(n):
                continue
            tail = _search(int(option["next_state"]), False, next_remaining)
            if tail is not None:
                return (_accepted_section(option, edge),) + tail
        memo.add(key)
        return None

    trace = _search(0, True, target_words)
    if trace is None:
        raise ValueError("could not reconstruct FG response surface trace")
    return tuple({**dict(row), "section": idx + 1} for idx, row in enumerate(trace))
