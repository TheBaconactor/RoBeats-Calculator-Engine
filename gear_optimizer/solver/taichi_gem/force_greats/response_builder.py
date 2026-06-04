from __future__ import annotations

from math import ceil
from typing import Any

import numpy as np

from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE


def _action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    last_fill: int | None = None
    for k in range(max(0, int(non_fever_base)) + 1):
        fill = int(ceil(float(raw_fever_fill) + (float(k) * 0.5)))
        if bool(use_forced_great_timing) or last_fill is None or fill != last_fill:
            fill_first = max(0, fill - 1)
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
    great_candidate_timestamps: np.ndarray,
) -> tuple[int, float, int]:
    start_time = float(timestamps[int(a)])
    carry_idx = -1
    if bool(use_forced_great_timing) and bool(activation_great) and int(a) < int(n):
        activation_t = float(great_candidate_timestamps[int(a)])
        if activation_t > start_time:
            start_time = activation_t
            carry_idx = int(a)
    e = _lower_bound_from(timestamps, start_time + float(real_fever_time))
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
    activation_idx: int,
    activation_great: bool,
) -> dict[str, Any]:
    if bool(activation_great) and int(carry_idx) == int(activation_idx):
        source = "activation_late_great"
        note_idx = int(carry_idx)
    else:
        source = "chart_perfect"
        note_idx: int | None = None
    return {
        "fever_start_source": source,
        "fever_start_note_index": note_idx,
        "fever_start_hit_ms": float(start_time) * 1000.0,
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
    great_candidate_timestamps: np.ndarray,
) -> list[tuple[int, int, FgResponseSurface]]:
    out: list[tuple[int, int, FgResponseSurface]] = []
    fills = first_fill if first else later_fill
    forced_values = first_forced if first else later_forced
    prev_fill = -1
    prev_start_time = -1.0
    prev_e = -1
    for action_idx, k in enumerate(actions):
        fill = int(fills[action_idx])
        a = int(fill if first else int(i) + fill)
        if a >= n:
            break
        forced_start = 0 if first else int(i) + 1
        forced_applied = int(forced_values[action_idx])
        e, start_time, _ = _edge_end(
            n=int(n),
            a=int(a),
            activation_great=False,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
        )
        skip_contiguous = fill == prev_fill and (start_time == prev_start_time or e == prev_e)
        if skip_contiguous:
            prev_fill = fill
            prev_start_time = start_time
            prev_e = e
        else:
            great_end = min(int(n), int(forced_start) + int(forced_applied))
            out.append(
                (
                    int(k),
                    int(e),
                    _edge_surface(
                        n=int(n),
                        fever_start=int(a),
                        fever_end=int(e),
                        great_start=int(forced_start),
                        great_end=int(great_end),
                    ),
                )
            )
        if bool(use_forced_great_timing) and int(k) > 0 and int(action_idx) > 0 and int(fills[action_idx - 1]) == int(fill):
            prefix_forced = min(max(0, int(k) - 1), max(0, int(a) - int(forced_start)))
            activation_e, _activation_start_time, _ = _edge_end(
                n=int(n),
                a=int(a),
                activation_great=True,
                real_fever_time=float(real_fever_time),
                use_forced_great_timing=bool(use_forced_great_timing),
                timestamps=timestamps,
                great_candidate_timestamps=great_candidate_timestamps,
            )
            if int(activation_e) > int(e):
                activation_surface = _edge_surface(
                    n=int(n),
                    fever_start=int(a),
                    fever_end=int(activation_e),
                    great_start=int(forced_start),
                    great_end=min(int(n), int(forced_start) + int(prefix_forced)),
                    activation_great_idx=int(a),
                )
                candidate = (int(k), int(activation_e), activation_surface)
                if candidate not in out:
                    out.append(candidate)
        prev_fill = fill
        prev_start_time = start_time
        prev_e = e
    return out


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
    great_candidate_timestamps: np.ndarray,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    fills = first_fill if first else later_fill
    forced_values = first_forced if first else later_forced
    prev_fill = -1
    prev_start_time = -1.0
    prev_e = -1
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
            great_candidate_timestamps=great_candidate_timestamps,
        )
        if fill != prev_fill or (start_time != prev_start_time and e != prev_e):
            great_end = min(int(n), int(forced_start) + int(forced_applied))
            out.append(
                {
                    "k": int(k),
                    "next_state": int(e),
                    "activation_index": int(a),
                    "activation_ms": float(timestamps[int(a)]) * 1000.0,
                    "activation_hit_ms": float(start_time) * 1000.0,
                    "activation_hit_offset_ms": (float(start_time) - float(timestamps[int(a)])) * 1000.0,
                    "activation_judgment": "perfect",
                    "forced_start_index": int(forced_start),
                    "forced_prefix_count": int(forced_applied),
                    "fever_end_index": int(e),
                    "fever_end_ms": None if int(e) >= int(n) else float(timestamps[int(e)]) * 1000.0,
                    **_trace_timing_fields(
                        carry_idx=int(carry_idx),
                        start_time=float(start_time),
                        activation_idx=int(a),
                        activation_great=False,
                    ),
                    "surface": _edge_surface(
                        n=int(n),
                        fever_start=int(a),
                        fever_end=int(e),
                        great_start=int(forced_start),
                        great_end=int(great_end),
                    ),
                }
            )
        if bool(use_forced_great_timing) and int(k) > 0 and int(action_idx) > 0 and int(fills[action_idx - 1]) == int(fill):
            prefix_forced = min(max(0, int(k) - 1), max(0, int(a) - int(forced_start)))
            activation_e, activation_start_time, activation_carry_idx = _edge_end(
                n=int(n),
                a=int(a),
                activation_great=True,
                real_fever_time=float(real_fever_time),
                use_forced_great_timing=bool(use_forced_great_timing),
                timestamps=timestamps,
                great_candidate_timestamps=great_candidate_timestamps,
            )
            if int(activation_e) > int(e):
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
                        "activation_ms": float(timestamps[int(a)]) * 1000.0,
                        "activation_hit_ms": float(activation_start_time) * 1000.0,
                        "activation_hit_offset_ms": (
                            float(activation_start_time) - float(timestamps[int(a)])
                        )
                        * 1000.0,
                        "activation_judgment": "late_great",
                        "forced_start_index": int(forced_start),
                        "forced_prefix_count": int(prefix_forced),
                        "fever_end_index": int(activation_e),
                        "fever_end_ms": None
                        if int(activation_e) >= int(n)
                        else float(timestamps[int(activation_e)]) * 1000.0,
                        **_trace_timing_fields(
                            carry_idx=int(activation_carry_idx),
                            start_time=float(activation_start_time),
                            activation_idx=int(a),
                            activation_great=True,
                        ),
                        "surface": activation_surface,
                    }
                )
        prev_fill = fill
        prev_start_time = start_time
        prev_e = e
    return out


def reconstruct_force_greats_response_counts(
    *,
    frontier: FgResponseFrontierResult,
    target_surface: FgResponseSurface,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> tuple[int, ...]:
    trace = reconstruct_force_greats_response_trace(
        frontier=frontier,
        target_surface=target_surface,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        raw_fever_fill=float(raw_fever_fill),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    return tuple(int(row["forced_count"]) for row in trace)


def reconstruct_force_greats_response_trace(
    *,
    frontier: FgResponseFrontierResult,
    target_surface: FgResponseSurface,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> tuple[dict[str, Any], ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0 or target_surface == _EMPTY_SURFACE:
        return ()
    great_ts = ts if great_candidate_timestamps is None else np.ascontiguousarray(
        np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    if int(great_ts.shape[0]) != n:
        raise ValueError("great_candidate_timestamps length must match timestamps")

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=int(frontier.non_fever_base),
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

    def _search(state: int, first: bool, remaining: tuple[int, ...]) -> tuple[dict[str, Any], ...] | None:
        if _empty(remaining):
            return ()
        key = (int(state), bool(first), remaining)
        if key in memo:
            return None
        for option in _edge_surface_option_details(
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
            great_candidate_timestamps=great_ts,
        ):
            edge = option["surface"]
            next_remaining = _subtract_edge(remaining, edge)
            if next_remaining is None:
                continue
            section = dict(option)
            section.pop("surface", None)
            section["forced_count"] = int(section.pop("k"))
            section["body_fever"] = int(edge.body_fever)
            section["body_great"] = int(edge.body_great)
            section["body_fever_great"] = int(edge.body_fever_great)
            if _empty(next_remaining):
                return (section,)
            if int(option["next_state"]) >= int(n):
                continue
            tail = _search(int(option["next_state"]), False, next_remaining)
            if tail is not None:
                return (section,) + tail
        memo.add(key)
        return None

    trace = _search(0, True, target_words)
    if trace is None:
        raise ValueError("could not reconstruct FG response surface trace")
    return tuple({**dict(row), "section": idx + 1} for idx, row in enumerate(trace))
