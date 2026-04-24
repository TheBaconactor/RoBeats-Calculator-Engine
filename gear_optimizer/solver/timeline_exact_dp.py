"""
Bounded exact DP for shared timing-envelope timelines.

This module owns the score-proxy exact signature search used by the production
base timing-envelope path on the retained small-window frontier. FG reuses the
same per-note fever-bonus prefix builder and keeps its own mode-specific action
layer for forced Great penalties/carry.

The result is exact for the cached proxy objective on the retained frontier,
not globally exact for every possible base stat triple across the full grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import ceil

import numpy as np

from .timing_envelope import prepare_perfect_timing_envelope

_CARRY_L = -40
_CARRY_U = 80
_MAX_HEAD = 100


@dataclass
class TimelineExactDPProfile:
    states: int = 0
    transitions: int = 0
    max_cached_states: int = 0


@dataclass(frozen=True)
class TimelineExactSignature:
    head_len: int
    head_bits: tuple[int, int, int, int]
    body_fever: int
    body_normal: int
    fever_activations: int
    gap: int
    total_bonus: int


@dataclass(frozen=True)
class _DpScoreResult:
    total_bonus: int
    m0: int
    m1: int
    m2: int
    m3: int
    body_fever: int
    fever_activations: int
    last_fever_end_idx: int

    @property
    def mask_tuple(self) -> tuple[int, int, int, int]:
        return (
            int(self.m0) & 0xFFFFFFFF,
            int(self.m1) & 0xFFFFFFFF,
            int(self.m2) & 0xFFFFFFFF,
            int(self.m3) & 0xFFFFFFFF,
        )


def build_score_bonus_prefix(
    *,
    total_notes: int,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    head_len: int = _MAX_HEAD,
) -> np.ndarray:
    """Build prefix sums of per-note fever bonus for a fixed scoring triple."""

    n = int(max(0, int(total_notes)))
    out = np.zeros(n + 1, dtype=np.int64)
    if n <= 0:
        return out

    head_len_i = int(min(max(0, int(head_len)), n))
    base_f = np.float32(float(base_value))
    combo_f = np.float32(float(combo_mul))
    fever_f = np.float32(float(fever_mul))
    factor = np.float32((combo_f - np.float32(1.0)) * base_f / np.float32(100.0))

    body_normal = int(np.float32(base_f * combo_f))
    body_fever = int(np.float32(np.float32(base_f * combo_f) * fever_f))
    body_bonus = int(body_fever - body_normal)

    running = 0
    for i in range(n):
        if i < head_len_i:
            current_ramp = np.float32(base_f + np.float32(i + 1) * factor)
            bonus = int(np.float32(current_ramp * fever_f)) - int(current_ramp)
        else:
            bonus = int(body_bonus)
        running += int(bonus)
        out[i + 1] = int(running)
    return out


def count_activation_upper_bound(*, total_notes: int, fill_count: int) -> int:
    """
    Exact-safe upper bound on possible fever activations for a fixed fill count.

    Every activation consumes at least:
    - `fill_count - 1` normal notes then 1 fever note for the first section
    - `fill_count` normal notes then 1 fever note for later sections
    """

    n = int(max(0, int(total_notes)))
    fc = max(1, int(fill_count))
    if n <= 0:
        return 0

    windows = 0
    i = 0
    is_first = True
    while i < n:
        notes_to_fill = int(fc - 1 if is_first else fc)
        if notes_to_fill < 0:
            notes_to_fill = 0
        activation_note = int(i + notes_to_fill)
        if activation_note >= n:
            break
        windows += 1
        i = int(activation_note + 1)
        is_first = False
    return int(windows)


def _better_score(a: _DpScoreResult, b: _DpScoreResult) -> bool:
    if int(a.total_bonus) != int(b.total_bonus):
        return int(a.total_bonus) > int(b.total_bonus)
    if int(a.body_fever) != int(b.body_fever):
        return int(a.body_fever) > int(b.body_fever)
    if int(a.m3) != int(b.m3):
        return int(a.m3) > int(b.m3)
    if int(a.m2) != int(b.m2):
        return int(a.m2) > int(b.m2)
    if int(a.m1) != int(b.m1):
        return int(a.m1) > int(b.m1)
    if int(a.m0) != int(b.m0):
        return int(a.m0) > int(b.m0)
    if int(a.last_fever_end_idx) != int(b.last_fever_end_idx):
        return int(a.last_fever_end_idx) > int(b.last_fever_end_idx)
    return int(a.fever_activations) > int(b.fever_activations)


def _or_head_mask_range(
    m0: int,
    m1: int,
    m2: int,
    m3: int,
    *,
    start: int,
    end: int,
    head_len: int,
) -> tuple[int, int, int, int]:
    s = max(0, int(start))
    e = min(int(end), int(head_len))
    if e <= s:
        return m0, m1, m2, m3
    for i in range(s, e):
        w = i >> 5
        b = i & 31
        if w == 0:
            m0 |= 1 << b
        elif w == 1:
            m1 |= 1 << b
        elif w == 2:
            m2 |= 1 << b
        else:
            m3 |= 1 << b
    return m0, m1, m2, m3


def _merge_int_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    ordered = sorted((int(lo), int(hi)) for lo, hi in intervals if int(lo) <= int(hi))
    if not ordered:
        return []

    out: list[tuple[int, int]] = []
    cur_lo, cur_hi = ordered[0]
    for lo, hi in ordered[1:]:
        if int(lo) <= int(cur_hi) + 1:
            if int(hi) > int(cur_hi):
                cur_hi = int(hi)
            continue
        out.append((int(cur_lo), int(cur_hi)))
        cur_lo, cur_hi = int(lo), int(hi)
    out.append((int(cur_lo), int(cur_hi)))
    return out


def _enumerate_first_exit_boundary_intervals_from_activation_band(
    *,
    total_notes: int,
    group_starts: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    activation_group: int,
    act_lo: int,
    act_hi: int,
    d_ms: int,
) -> list[tuple[int, int, int, int]]:
    """
    Exact merged boundary enumeration for an activation-carry interval.

    For `d_ms > 0`, the feasible carries that first-exit at a given boundary
    group form a single interval, so we can enumerate merged boundary intervals
    directly without iterating every activation carry.
    """

    n = int(total_notes)
    group_starts = np.asarray(group_starts, dtype=np.int32).reshape(-1)
    group_base = np.asarray(group_base_t_ms, dtype=np.int32).reshape(-1)
    group_low = np.asarray(group_low_ms, dtype=np.int32).reshape(-1)
    group_high = np.asarray(group_high_ms, dtype=np.int32).reshape(-1)

    gcount = int(group_starts.shape[0])
    s = int(activation_group)
    lo_band = int(act_lo)
    hi_band = int(act_hi)
    if lo_band > hi_band or s < 0 or s >= gcount:
        return []

    if int(s) + 1 >= gcount:
        return [(int(n), int(gcount), int(lo_band), int(hi_band))]

    out: list[tuple[int, int, int, int]] = []
    survive_lo = int(lo_band)
    lower_const: int | None = None
    survivor_cap_const: int | None = None
    last_delta_sum = 0

    for g in range(int(s) + 1, gcount):
        if g == int(s) + 1:
            lower_const = max(_CARRY_L, int(group_low[g]))
            survivor_cap_const = min(_CARRY_U, int(group_high[g]))
        else:
            delta = int(group_base[g]) - int(group_base[g - 1])
            if delta < 1:
                delta = 1
            lower_const = max(_CARRY_L, max(int(group_low[g]), int(lower_const) - int(delta)))
            survivor_cap_const = min(_CARRY_U, max(int(group_high[g]), int(survivor_cap_const) - int(delta)))

        delta_sum = int(group_base[g]) - int(group_base[s])
        last_delta_sum = int(delta_sum)

        r_lo = max(int(lo_band), int(survive_lo))
        r_hi = min(int(hi_band), int(group_high[g]) + int(delta_sum) - int(d_ms))
        if r_lo <= r_hi:
            exit_lo = max(int(lower_const), int(r_lo) - int(delta_sum) + int(d_ms))
            exit_hi = min(_CARRY_U, int(group_high[g]))
            if exit_lo <= exit_hi:
                out.append((int(group_starts[g]), int(g), int(exit_lo), int(exit_hi)))

        survive_needed = int(lower_const) + int(delta_sum) - int(d_ms) + 1
        if survive_needed > int(survive_lo):
            survive_lo = int(survive_needed)
        if int(survive_lo) > int(hi_band):
            return out

    x_hi = int(hi_band) - int(last_delta_sum)
    end_lo = max(int(lower_const), int(survive_lo) - int(last_delta_sum))
    end_hi = max(int(x_hi), min(int(survivor_cap_const), int(x_hi) + int(d_ms) - 1))
    out.append((int(n), int(gcount), int(end_lo), int(end_hi)))
    return out


def solve_timeline_signature_exact_scoremax_from_grouped_windows(
    total_notes: int,
    *,
    group_starts: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
    fill_count: int,
    d_ms: int,
    bonus_prefix: np.ndarray,
) -> TimelineExactSignature:
    """
    Score-weighted exact DP for one timing-envelope cell from grouped windows.

    The caller is expected to apply a small-window gate before using this on
    production paths.
    """

    n = int(total_notes)
    if n <= 0:
        return TimelineExactSignature(
            head_len=0,
            head_bits=(0, 0, 0, 0),
            body_fever=0,
            body_normal=0,
            fever_activations=0,
            gap=0,
            total_bonus=0,
        )

    group_starts = np.asarray(group_starts, dtype=np.int32).reshape(-1)
    group_base = np.asarray(group_base_t_ms, dtype=np.int32).reshape(-1)
    group_low = np.asarray(group_low_ms, dtype=np.int32).reshape(-1)
    group_high = np.asarray(group_high_ms, dtype=np.int32).reshape(-1)
    note_group_idx = np.asarray(note_group_idx, dtype=np.int32).reshape(-1)
    bonus_prefix = np.asarray(bonus_prefix, dtype=np.int64).reshape(-1)

    gcount = int(group_starts.shape[0])
    if n > 0 and gcount <= 0:
        raise AssertionError("empty chord-group payload")
    if int(note_group_idx.shape[0]) != n:
        raise AssertionError("note_group_idx length mismatch")
    if int(bonus_prefix.shape[0]) != int(n + 1):
        raise AssertionError("bonus_prefix length mismatch")

    head_len = int(min(n, _MAX_HEAD))
    total_body = int(max(0, n - head_len))
    fill_count_i = max(1, int(fill_count))
    d_ms_i = max(0, int(d_ms))
    profile = TimelineExactDPProfile()

    delta_from_prev = np.zeros(gcount, dtype=np.int32)
    for g in range(1, gcount):
        delta = int(group_base[g]) - int(group_base[g - 1])
        if delta < 1:
            delta = 1
        delta_from_prev[g] = int(delta)

    max_pow = max(1, int(gcount).bit_length())
    jump_b = [[0] * max_pow for _ in range(gcount)]
    jump_a_lo = [[0] * max_pow for _ in range(gcount)]
    jump_a_hi = [[0] * max_pow for _ in range(gcount)]

    for g in range(0, gcount - 1):
        delta = int(delta_from_prev[g + 1])
        jump_b[g][0] = int(delta)
        jump_a_lo[g][0] = int(group_low[g + 1])
        jump_a_hi[g][0] = int(group_high[g + 1])

    for p2 in range(1, max_pow):
        step = 1 << (p2 - 1)
        span = 1 << p2
        for g in range(0, gcount):
            end = g + span
            mid = g + step
            if end >= gcount or mid >= gcount:
                continue
            b2 = int(jump_b[mid][p2 - 1])
            jump_b[g][p2] = int(jump_b[g][p2 - 1]) + int(b2)
            jump_a_lo[g][p2] = max(int(jump_a_lo[mid][p2 - 1]), int(jump_a_lo[g][p2 - 1]) - int(b2))
            jump_a_hi[g][p2] = max(int(jump_a_hi[mid][p2 - 1]), int(jump_a_hi[g][p2 - 1]) - int(b2))

    def _propagate_to_group(start_g: int, lo: int, hi: int, target_g: int) -> tuple[int, int]:
        if target_g <= start_g:
            return int(lo), int(hi)
        g = int(start_g)
        out_lo = int(lo)
        out_hi = int(hi)
        dist = int(target_g - start_g)
        p2 = 0
        while dist:
            if dist & 1:
                b = int(jump_b[g][p2])
                out_lo = max(int(jump_a_lo[g][p2]), int(out_lo) - int(b))
                out_hi = max(int(jump_a_hi[g][p2]), int(out_hi) - int(b))
                g += 1 << p2
                if out_lo > out_hi:
                    return 1, 0
            dist >>= 1
            p2 += 1
        return int(out_lo), int(out_hi)

    @lru_cache(maxsize=None)
    def _solve_from_boundary(start_group: int, lo: int, hi: int, is_first: bool) -> _DpScoreResult:
        profile.states += 1
        profile.max_cached_states = max(profile.max_cached_states, profile.states)

        start_group_i = int(start_group)
        lo_i = int(lo)
        hi_i = int(hi)

        if start_group_i >= gcount:
            start_note_i = int(n)
        else:
            start_note_i = int(group_starts[start_group_i])

        notes_to_fill = int(fill_count_i - 1 if bool(is_first) else fill_count_i)
        if notes_to_fill < 0:
            notes_to_fill = 0
        activation_note = int(start_note_i + int(notes_to_fill))

        if activation_note >= n or activation_note <= 0 or start_note_i >= n:
            return _DpScoreResult(
                total_bonus=0,
                m0=0,
                m1=0,
                m2=0,
                m3=0,
                body_fever=0,
                fever_activations=0,
                last_fever_end_idx=start_note_i,
            )

        g_act = int(note_group_idx[activation_note])
        if g_act < 0 or g_act >= gcount:
            return _DpScoreResult(
                total_bonus=0,
                m0=0,
                m1=0,
                m2=0,
                m3=0,
                body_fever=0,
                fever_activations=0,
                last_fever_end_idx=start_note_i,
            )

        act_lo, act_hi = _propagate_to_group(start_group_i, lo_i, hi_i, g_act)
        if act_lo > act_hi:
            return _DpScoreResult(
                total_bonus=0,
                m0=0,
                m1=0,
                m2=0,
                m3=0,
                body_fever=0,
                fever_activations=0,
                last_fever_end_idx=start_note_i,
            )

        best: _DpScoreResult | None = None
        for boundary_note, exit_group, exit_lo, exit_hi in _enumerate_first_exit_boundary_intervals_from_activation_band(
            total_notes=n,
            group_starts=group_starts,
            group_base_t_ms=group_base,
            group_low_ms=group_low,
            group_high_ms=group_high,
            activation_group=int(g_act),
            act_lo=int(act_lo),
            act_hi=int(act_hi),
            d_ms=int(d_ms_i),
        ):
            profile.transitions += 1
            future = _solve_from_boundary(
                int(exit_group),
                int(exit_lo),
                int(exit_hi),
                False,
            )
            m0, m1, m2, m3 = _or_head_mask_range(
                future.m0,
                future.m1,
                future.m2,
                future.m3,
                start=int(activation_note),
                end=int(boundary_note),
                head_len=head_len,
            )

            body_add = 0
            if boundary_note > 100:
                body_start = max(100, int(activation_note))
                if boundary_note > body_start:
                    body_add = int(boundary_note) - int(body_start)

            total_bonus = int(future.total_bonus) + int(
                bonus_prefix[int(boundary_note)] - bonus_prefix[int(activation_note)]
            )
            cand = _DpScoreResult(
                total_bonus=int(total_bonus),
                m0=int(m0),
                m1=int(m1),
                m2=int(m2),
                m3=int(m3),
                body_fever=int(future.body_fever + body_add),
                fever_activations=int(future.fever_activations + 1),
                last_fever_end_idx=int(future.last_fever_end_idx),
            )
            if best is None or _better_score(cand, best):
                best = cand

        if best is None:
            return _DpScoreResult(
                total_bonus=0,
                m0=0,
                m1=0,
                m2=0,
                m3=0,
                body_fever=0,
                fever_activations=0,
                last_fever_end_idx=start_note_i,
            )
        return best

    lo0 = max(_CARRY_L, int(group_low[0]))
    hi0 = min(_CARRY_U, int(group_high[0]))
    best0 = _solve_from_boundary(0, lo0, hi0, True)

    gap = int(n - int(best0.last_fever_end_idx))
    body_fever = int(best0.body_fever)
    body_normal = int(max(0, total_body - body_fever))
    return TimelineExactSignature(
        head_len=int(head_len),
        head_bits=best0.mask_tuple,
        body_fever=int(body_fever),
        body_normal=int(body_normal),
        fever_activations=int(best0.fever_activations),
        gap=int(gap),
        total_bonus=int(best0.total_bonus),
    )


def solve_timeline_signature_exact_scoremax(
    chart_timestamps: np.ndarray,
    note_types: np.ndarray,
    *,
    long_notes: int,
    last_note_time: float,
    ff_factor: float,
    ft_factor: float,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
) -> TimelineExactSignature:
    """Convenience wrapper that prepares grouped Perfect windows from chart data."""

    ts = np.asarray(chart_timestamps, dtype=np.float32).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0:
        return TimelineExactSignature(
            head_len=0,
            head_bits=(0, 0, 0, 0),
            body_fever=0,
            body_normal=0,
            fever_activations=0,
            gap=0,
            total_bonus=0,
        )

    non_fever_cas = float(max(0, n - int(long_notes))) * 0.333
    fill_count = int(ceil(non_fever_cas * float(ff_factor)))
    fill_count = max(1, int(fill_count))

    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    d_ms = int(ceil(float(fever_time_cas * float(ft_factor) * 1000.0)))
    d_ms = max(0, int(d_ms))

    prepared = prepare_perfect_timing_envelope(
        ts,
        nt,
        perfect_lower_ms=int(perfect_lower_ms),
        perfect_upper_ms=int(perfect_upper_ms),
        held_tail_type=int(held_tail_type),
        held_tail_time_multiplier=int(held_tail_time_multiplier),
        quantize_ms=True,
    )
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32).reshape(-1)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32).reshape(-1)
    group_base = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32).reshape(-1)
    group_low = np.asarray(prepared.get("group_low", ()), dtype=np.int32).reshape(-1)
    group_high = np.asarray(prepared.get("group_high", ()), dtype=np.int32).reshape(-1)
    note_group_idx = np.full(n, -1, dtype=np.int32)
    for g in range(int(group_starts.shape[0])):
        s = int(group_starts[g])
        e = int(group_ends[g])
        if e > s:
            note_group_idx[s:e] = int(g)

    bonus_prefix = build_score_bonus_prefix(
        total_notes=n,
        base_value=float(base_value),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
    )
    return solve_timeline_signature_exact_scoremax_from_grouped_windows(
        n,
        group_starts=group_starts,
        group_base_t_ms=group_base,
        group_low_ms=group_low,
        group_high_ms=group_high,
        note_group_idx=note_group_idx,
        fill_count=int(fill_count),
        d_ms=int(d_ms),
        bonus_prefix=bonus_prefix,
    )

