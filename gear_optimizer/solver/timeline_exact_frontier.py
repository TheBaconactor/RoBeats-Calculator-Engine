"""
Exact symbolic fever-surface frontier construction.

This module builds the non-dominated symbolic fever frontier for a fixed song and
one timing cell `(fill_count, d_ms)`, then expands it to a full 161x161 payload for
GPU upload.

The frontier is loadout-independent. The canonical representative is chosen by a
deterministic structural comparator, while the full non-dominated surface set is
retained for exact scoring.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import concurrent.futures
import threading
import time
from typing import Iterable

import numpy as np
from numba import jit

from gear_optimizer.core.constants import FEVER_TIME_OFFSET, FEVER_TIME_SCALE
from gear_optimizer.core.profile_events import emit_profile_event

from .taichi_gem.fields import GRID_SIZE, MAX_TIMELINE_FRONTIER_SURFACES

_CARRY_L = -40
_CARRY_U = 80
_MAX_HEAD = 100
_GROUPED_TIMELINE_CONTEXT_CACHE_MAX = 64
_GROUPED_TIMELINE_CONTEXT_CACHE_LOCK = threading.RLock()
_GROUPED_TIMELINE_CONTEXT_CACHE: "OrderedDict[tuple[object, ...], _GroupedTimelineContext]" = OrderedDict()

_TIMELINE_PAIR_BUILD_THREADS = 1


def configure_timeline_pair_build_threads(max_threads: int) -> int:
    """Size the per-song fill-count pair-build thread pool (timeline prebuild workers)."""
    global _TIMELINE_PAIR_BUILD_THREADS
    from gear_optimizer.core.cpu_affinity import logical_core_count

    previous = int(_TIMELINE_PAIR_BUILD_THREADS)
    _TIMELINE_PAIR_BUILD_THREADS = max(1, min(int(max_threads), logical_core_count()))
    return previous


@dataclass(frozen=True)
class TimelineExactSignature:
    head_len: int
    head_bits: tuple[int, int, int, int]
    body_fever: int
    body_normal: int
    fever_activations: int
    gap: int
    total_bonus: int = 0


@dataclass(frozen=True)
class TimelineFrontierPack:
    surfaces: tuple[TimelineExactSignature, ...]
    canonical: TimelineExactSignature
    sig0: int
    sig1: int
    head_len: int
    body_fever: int
    body_normal: int
    fever_activations: int
    gap: int


@dataclass(frozen=True)
class TimelineFrontierGridPayload:
    grid_count_body_fever: np.ndarray
    grid_count_body_normal: np.ndarray
    grid_head_len: np.ndarray
    grid_fever_masks_bits: np.ndarray
    grid_frontier_count: np.ndarray
    grid_frontier_offset: np.ndarray
    grid_frontier_body_fever_pool: np.ndarray
    grid_frontier_body_normal_pool: np.ndarray
    grid_frontier_masks_bits_pool: np.ndarray
    grid_frontier_head_coeffs_pool: np.ndarray
    grid_gap: np.ndarray
    grid_fever_activations: np.ndarray
    frontier_pool_used: int


@dataclass(frozen=True)
class _GroupedTimelineContext:
    total_notes: int
    group_starts: np.ndarray
    group_base_t_ms: np.ndarray
    group_low_ms: np.ndarray
    group_high_ms: np.ndarray
    note_group_idx: np.ndarray
    head_range_masks: np.ndarray
    gcount: int
    head_len: int
    total_body: int
    max_pow: int
    jump_b: np.ndarray
    jump_a_lo: np.ndarray
    jump_a_hi: np.ndarray
    exit_lower: np.ndarray
    exit_cap: np.ndarray
    exit_delta: np.ndarray
    exit_need: np.ndarray
    exit_need_prefix_prev: np.ndarray
    exit_need_prefix_current: np.ndarray
    future_high_abs_suffix: np.ndarray
    lo0: int
    hi0: int


@dataclass(frozen=True)
class _ExitTraceEntry:
    activation_group: int
    act_lo: int
    act_hi: int
    exits: tuple[tuple[int, int, int, int], ...]


def _mix_u64(x: int) -> int:
    x &= 0xFFFFFFFFFFFFFFFF
    x ^= x >> 33
    x = (x * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 33
    x = (x * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 33
    return x & 0xFFFFFFFFFFFFFFFF


def _pack_mask_sig(m0: int, m1: int, m2: int, m3: int) -> int:
    lo = (int(m0) & 0xFFFFFFFF) | ((int(m1) & 0xFFFFFFFF) << 32)
    hi = (int(m2) & 0xFFFFFFFF) | ((int(m3) & 0xFFFFFFFF) << 32)
    return _mix_u64(lo) ^ _mix_u64((hi + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF)


def _pack_counts_sig(body_fever: int, body_normal: int, head_len: int, fever_activations: int, gap: int) -> int:
    bf = int(body_fever) & 0xFFFF
    bn = (int(body_normal) & 0xFFFF) << 16
    hl = (int(head_len) & 0xFF) << 32
    fa = (int(fever_activations) & 0xFF) << 40
    gp = (int(gap) & 0xFFFF) << 48
    return (bf | bn | hl | fa | gp) & 0xFFFFFFFFFFFFFFFF


def _surface_sort_key(surface: TimelineExactSignature) -> tuple[int, int, int, int, int, int, int]:
    return (
        int(surface.body_fever),
        int(surface.head_bits[3]) & 0xFFFFFFFF,
        int(surface.head_bits[2]) & 0xFFFFFFFF,
        int(surface.head_bits[1]) & 0xFFFFFFFF,
        int(surface.head_bits[0]) & 0xFFFFFFFF,
        int(surface.fever_activations),
        int(surface.gap),
    )


def _surface_equal(a: TimelineExactSignature, b: TimelineExactSignature) -> bool:
    return (
        int(a.head_bits[0]) == int(b.head_bits[0])
        and int(a.head_bits[1]) == int(b.head_bits[1])
        and int(a.head_bits[2]) == int(b.head_bits[2])
        and int(a.head_bits[3]) == int(b.head_bits[3])
        and int(a.body_fever) == int(b.body_fever)
        and int(a.body_normal) == int(b.body_normal)
    )


def _surface_dominates(a: TimelineExactSignature, b: TimelineExactSignature) -> bool:
    a_contains_b_head = (
        ((int(a.head_bits[0]) | int(b.head_bits[0])) == int(a.head_bits[0]))
        and ((int(a.head_bits[1]) | int(b.head_bits[1])) == int(a.head_bits[1]))
        and ((int(a.head_bits[2]) | int(b.head_bits[2])) == int(a.head_bits[2]))
        and ((int(a.head_bits[3]) | int(b.head_bits[3])) == int(a.head_bits[3]))
    )
    return a_contains_b_head and int(a.body_fever) >= int(b.body_fever) and int(a.body_normal) <= int(b.body_normal)


def _emit_frontier_phase(
    *,
    phase: str,
    start: float,
    song_key: str | None,
    song_slot: int,
    **metrics,
) -> None:
    payload = {
        "phase": str(phase),
        "ms": float((time.perf_counter() - float(start)) * 1000.0),
        "song_slot": int(song_slot),
    }
    payload.update(metrics)
    emit_profile_event(
        component="gpu_executor",
        event="timeline_frontier_phase",
        song_key=song_key,
        metrics=payload,
    )


def reduce_timeline_frontier(surfaces: Iterable[TimelineExactSignature]) -> tuple[TimelineExactSignature, ...]:
    ordered = list(surfaces)
    if not ordered:
        return ()
    if len(ordered) == 1:
        return (ordered[0],)

    retained: list[TimelineExactSignature] = []
    for idx, cand in enumerate(ordered):
        drop = False
        for other_idx, other in enumerate(ordered):
            if other_idx == idx:
                continue
            if _surface_equal(other, cand):
                if other_idx < idx:
                    drop = True
            elif _surface_dominates(other, cand):
                drop = True
            if drop:
                break
        if not drop:
            retained.append(cand)

    retained.sort(key=_surface_sort_key, reverse=True)
    return tuple(retained)


def _head_mask_coefficients_py(m0: int, m1: int, m2: int, m3: int, head_len: int) -> tuple[int, int, int, int]:
    n_hn = 0
    n_hf = 0
    sigma_hn = 0
    sigma_hf = 0
    for i in range(max(0, int(head_len))):
        pos = i + 1
        if i < 32:
            bit = (int(m0) >> i) & 1
        elif i < 64:
            bit = (int(m1) >> (i - 32)) & 1
        elif i < 96:
            bit = (int(m2) >> (i - 64)) & 1
        else:
            bit = (int(m3) >> (i - 96)) & 1
        if bit:
            n_hf += 1
            sigma_hf += pos
        else:
            n_hn += 1
            sigma_hn += pos
    return n_hn, n_hf, sigma_hn, sigma_hf


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
    Enumerate merged first-exit boundary intervals for a single activation band.

    The returned tuples are `(boundary_note, exit_group, exit_lo, exit_hi)`.
    """

    n = int(total_notes)
    group_base = group_base_t_ms
    group_low = group_low_ms
    group_high = group_high_ms
    gcount = int(group_starts.shape[0])
    s = int(activation_group)
    lo_band = int(act_lo)
    hi_band = int(act_hi)
    if lo_band > hi_band or s < 0 or s >= gcount:
        return []

    if s + 1 >= gcount:
        return [(int(n), int(gcount), int(lo_band), int(hi_band))]

    out: list[tuple[int, int, int, int]] = []
    survive_lo = int(lo_band)
    lower_const: int | None = None
    survivor_cap_const: int | None = None
    last_delta_sum = 0

    for g in range(s + 1, gcount):
        if g == s + 1:
            lower_const = max(_CARRY_L, int(group_low[g]))
            survivor_cap_const = min(_CARRY_U, int(group_high[g]))
        else:
            # True delta (no >=1 clamp): 0 for same-timestamp split groups; >=1 (bit-identical)
            # for every distinct-timestamp adjacency. Mirrors the context-build path.
            delta = int(group_base[g]) - int(group_base[g - 1])
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


@jit(nopython=True, cache=True)
def _exit_intervals_jit(
    s, lo_band, hi_band, d_ms, gcount, n, carry_u, group_base_s,
    group_starts, group_high, exit_delta_s, exit_lower_s, exit_cap_s,
    exit_need_prefix_prev_s, exit_need_prefix_current_s, future_high_s1,
    out_bnote, out_egroup, out_elo, out_ehi,
):
    """numba kernel for the first-exit boundary enumeration (main case: s+1 < gcount, lo<=hi,
    handled by the wrapper). Fills out_* scratch arrays, returns the exit count. Bit-identical
    to the prior numpy/Python path (the row enumerator is the cross-checked reference)."""
    # Early-out: no future group can be in fever.
    if future_high_s1 < group_base_s + lo_band + d_ms:
        last_idx = gcount - 1
        lds = exit_delta_s[last_idx]
        c0 = exit_need_prefix_current_s[last_idx] - d_ms
        survive_lo = lo_band if lo_band > c0 else c0
        x_hi = hi_band - lds
        el = exit_lower_s[last_idx]
        sl2 = survive_lo - lds
        end_lo = el if el > sl2 else sl2
        scc = exit_cap_s[last_idx]
        c2 = x_hi + d_ms - 1
        m = scc if scc < c2 else c2
        end_hi = x_hi if x_hi > m else m
        out_bnote[0] = n
        out_egroup[0] = gcount
        out_elo[0] = end_lo
        out_ehi[0] = end_hi
        return 1

    start = s + 1
    target = hi_band + d_ms
    # searchsorted(exit_need_prefix_current_s[start:gcount], target, side="right") (monotone row)
    loi = start
    hii = gcount
    while loi < hii:
        mid = (loi + hii) >> 1
        if exit_need_prefix_current_s[mid] <= target:
            loi = mid + 1
        else:
            hii = mid
    keep_count = loi - start
    stopped = keep_count < (gcount - start)
    process_stop = (start + keep_count + 1) if stopped else gcount

    cnt = 0
    g = start
    while g < process_stop:
        delta = exit_delta_s[g]
        gh = group_high[g]
        c_rlo = exit_need_prefix_prev_s[g] - d_ms
        r_lo = lo_band if lo_band > c_rlo else c_rlo
        c_rhi = gh + delta - d_ms
        r_hi = hi_band if hi_band < c_rhi else c_rhi
        ex_hi = carry_u if carry_u < gh else gh
        c_elo = r_lo - delta + d_ms
        lower = exit_lower_s[g]
        ex_lo = lower if lower > c_elo else c_elo
        if r_lo <= r_hi and ex_lo <= ex_hi:
            out_bnote[cnt] = group_starts[g]
            out_egroup[cnt] = g
            out_elo[cnt] = ex_lo
            out_ehi[cnt] = ex_hi
            cnt += 1
        g += 1

    if stopped:
        return cnt

    last_idx = gcount - 1
    lds = exit_delta_s[last_idx]
    c0 = exit_need_prefix_current_s[last_idx] - d_ms
    survive_lo = lo_band if lo_band > c0 else c0
    x_hi = hi_band - lds
    el = exit_lower_s[last_idx]
    sl2 = survive_lo - lds
    end_lo = el if el > sl2 else sl2
    scc = exit_cap_s[last_idx]
    c2 = x_hi + d_ms - 1
    m = scc if scc < c2 else c2
    end_hi = x_hi if x_hi > m else m
    out_bnote[cnt] = n
    out_egroup[cnt] = gcount
    out_elo[cnt] = end_lo
    out_ehi[cnt] = end_hi
    cnt += 1
    return cnt


def _enumerate_first_exit_boundary_intervals_from_context(
    ctx: _GroupedTimelineContext,
    *,
    activation_group: int,
    act_lo: int,
    act_hi: int,
    d_ms: int,
    scratch: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> list[tuple[int, int, int, int]]:
    n = int(ctx.total_notes)
    gcount = int(ctx.gcount)
    s = int(activation_group)
    lo_band = int(act_lo)
    hi_band = int(act_hi)
    if lo_band > hi_band or s < 0 or s >= gcount:
        return []
    if s + 1 >= gcount:
        return [(n, gcount, lo_band, hi_band)]
    if scratch is None:
        cap = gcount + 1
        scratch = (
            np.empty(cap, dtype=np.int64),
            np.empty(cap, dtype=np.int64),
            np.empty(cap, dtype=np.int64),
            np.empty(cap, dtype=np.int64),
        )
    out_bnote, out_egroup, out_elo, out_ehi = scratch
    count = _exit_intervals_jit(
        s, lo_band, hi_band, int(d_ms), gcount, n, int(_CARRY_U),
        int(ctx.group_base_t_ms[s]), ctx.group_starts, ctx.group_high_ms,
        ctx.exit_delta[s], ctx.exit_lower[s], ctx.exit_cap[s],
        ctx.exit_need_prefix_prev[s], ctx.exit_need_prefix_current[s],
        int(ctx.future_high_abs_suffix[s + 1]),
        out_bnote, out_egroup, out_elo, out_ehi,
    )
    return [
        (int(out_bnote[i]), int(out_egroup[i]), int(out_elo[i]), int(out_ehi[i]))
        for i in range(int(count))
    ]


def _transition_cache_key(*, activation_group: int, act_lo: int, act_hi: int, d_ms: int) -> tuple[int, int, int, int]:
    return (int(activation_group), int(act_lo), int(act_hi), int(d_ms))


def _cached_first_exit_boundary_intervals(
    ctx: _GroupedTimelineContext,
    *,
    activation_group: int,
    act_lo: int,
    act_hi: int,
    d_ms: int,
    transition_cache: dict[tuple[int, int, int, int], tuple[tuple[int, int, int, int], ...]] | None = None,
    scratch: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> tuple[tuple[int, int, int, int], ...]:
    key = _transition_cache_key(
        activation_group=int(activation_group),
        act_lo=int(act_lo),
        act_hi=int(act_hi),
        d_ms=int(d_ms),
    )
    if transition_cache is not None:
        cached = transition_cache.get(key)
        if cached is not None:
            return cached
    exits = tuple(
        _enumerate_first_exit_boundary_intervals_from_context(
            ctx,
            activation_group=int(activation_group),
            act_lo=int(act_lo),
            act_hi=int(act_hi),
            d_ms=int(d_ms),
            scratch=scratch,
        )
    )
    if transition_cache is not None:
        transition_cache[key] = exits
    return exits


def _build_grouped_timeline_context(
    total_notes: int,
    *,
    group_starts: np.ndarray,
    group_ends: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
) -> _GroupedTimelineContext:
    n = int(total_notes)
    group_starts = np.asarray(group_starts, dtype=np.int32).reshape(-1)
    group_base = np.asarray(group_base_t_ms, dtype=np.int32).reshape(-1)
    group_low = np.asarray(group_low_ms, dtype=np.int32).reshape(-1)
    group_high = np.asarray(group_high_ms, dtype=np.int32).reshape(-1)
    note_group_idx = np.asarray(note_group_idx, dtype=np.int32).reshape(-1)

    if n <= 0:
        return _GroupedTimelineContext(
            total_notes=0,
            group_starts=np.zeros((0,), dtype=np.int32),
            group_base_t_ms=np.zeros((0,), dtype=np.int32),
            group_low_ms=np.zeros((0,), dtype=np.int32),
            group_high_ms=np.zeros((0,), dtype=np.int32),
            note_group_idx=np.zeros((0,), dtype=np.int32),
            head_range_masks=np.zeros((1, 1, 4), dtype=np.uint32),
            gcount=0,
            head_len=0,
            total_body=0,
            max_pow=1,
            jump_b=np.zeros((0, 1), dtype=np.int32),
            jump_a_lo=np.zeros((0, 1), dtype=np.int32),
            jump_a_hi=np.zeros((0, 1), dtype=np.int32),
            exit_lower=np.zeros((0, 0), dtype=np.int16),
            exit_cap=np.zeros((0, 0), dtype=np.int16),
            exit_delta=np.zeros((0, 0), dtype=np.int32),
            exit_need=np.zeros((0, 0), dtype=np.int32),
            exit_need_prefix_prev=np.zeros((0, 0), dtype=np.int32),
            exit_need_prefix_current=np.zeros((0, 0), dtype=np.int32),
            future_high_abs_suffix=np.zeros((1,), dtype=np.int32),
            lo0=0,
            hi0=0,
        )

    gcount = int(group_starts.shape[0])
    if gcount <= 0:
        raise AssertionError("empty chord-group payload")
    if int(note_group_idx.shape[0]) != n:
        raise AssertionError("note_group_idx length mismatch")

    head_len = int(min(n, _MAX_HEAD))
    total_body = int(max(0, n - head_len))
    head_range_masks = np.zeros((head_len + 1, head_len + 1, 4), dtype=np.uint32)
    for start_note in range(head_len):
        m0 = 0
        m1 = 0
        m2 = 0
        m3 = 0
        for end_note in range(start_note + 1, head_len + 1):
            bit_idx = end_note - 1
            word = bit_idx >> 5
            bit = bit_idx & 31
            if word == 0:
                m0 |= 1 << bit
            elif word == 1:
                m1 |= 1 << bit
            elif word == 2:
                m2 |= 1 << bit
            else:
                m3 |= 1 << bit
            head_range_masks[start_note, end_note, 0] = np.uint32(m0)
            head_range_masks[start_note, end_note, 1] = np.uint32(m1)
            head_range_masks[start_note, end_note, 2] = np.uint32(m2)
            head_range_masks[start_note, end_note, 3] = np.uint32(m3)

    delta_from_prev = np.zeros(gcount, dtype=np.int32)
    if gcount > 1:
        # True inter-group time delta. 0 for same-timestamp groups (a held tail split into its
        # own group, sharing the chord's ms). NO clamp to >=1: clamping would model simultaneous
        # notes as 1 ms apart and make `carry_pos` (clamped) diverge from the unclamped
        # `exit_delta` below, corrupting the exit arithmetic. Group timestamps are non-decreasing,
        # so delta is always >= 0; for every distinct-timestamp adjacency (all of them on a chart
        # with no held-tail-mixed chord) delta is already >= 1, making this bit-identical there.
        delta_from_prev[1:] = group_base[1:].astype(np.int32) - group_base[:-1].astype(np.int32)

    # Binary-lifting jump tables as 2D int32 arrays (was list-of-lists): vectorized build +
    # numba-friendly random access in _propagate_band_to_group.
    max_pow = max(1, int(gcount).bit_length())
    jump_b = np.zeros((gcount, max_pow), dtype=np.int32)
    jump_a_lo = np.zeros((gcount, max_pow), dtype=np.int32)
    jump_a_hi = np.zeros((gcount, max_pow), dtype=np.int32)
    if gcount > 1:
        jump_b[: gcount - 1, 0] = delta_from_prev[1:]
        jump_a_lo[: gcount - 1, 0] = group_low[1:]
        jump_a_hi[: gcount - 1, 0] = group_high[1:]
    for p2 in range(1, max_pow):
        step = 1 << (p2 - 1)
        span = 1 << p2
        last = gcount - span  # valid g are [0, last): need g+span < gcount (=> mid=g+step < gcount)
        if last <= 0:
            continue
        g = np.arange(last)
        mid = g + step
        b2 = jump_b[mid, p2 - 1]
        jump_b[g, p2] = jump_b[g, p2 - 1] + b2
        jump_a_lo[g, p2] = np.maximum(jump_a_lo[mid, p2 - 1], jump_a_lo[g, p2 - 1] - b2)
        jump_a_hi[g, p2] = np.maximum(jump_a_hi[mid, p2 - 1], jump_a_hi[g, p2 - 1] - b2)

    exit_lower = np.zeros((gcount, gcount), dtype=np.int16)
    exit_cap = np.zeros((gcount, gcount), dtype=np.int16)
    exit_delta = np.zeros((gcount, gcount), dtype=np.int32)
    exit_need = np.zeros((gcount, gcount), dtype=np.int32)
    exit_need_prefix_prev = np.full((gcount, gcount), -1_000_000_000, dtype=np.int32)
    exit_need_prefix_current = np.full((gcount, gcount), -1_000_000_000, dtype=np.int32)
    carry_pos = np.zeros(gcount, dtype=np.int32)
    if gcount > 1:
        carry_pos[1:] = np.cumsum(delta_from_prev[1:], dtype=np.int32)
    low_source = group_low.astype(np.int32, copy=False) + carry_pos
    cap_source = np.minimum(group_high.astype(np.int32, copy=False), np.int32(_CARRY_U)) + carry_pos
    abs_high = group_base.astype(np.int32, copy=False) + group_high.astype(np.int32, copy=False)
    future_high_abs_suffix = np.full(gcount + 1, -1_000_000_000, dtype=np.int32)
    if gcount > 0:
        future_high_abs_suffix[:gcount] = np.maximum.accumulate(abs_high[::-1])[::-1]
    for s in range(0, gcount - 1):
        sl = slice(s + 1, gcount)
        row_carry = carry_pos[sl]
        lower_vals = np.maximum(
            np.int32(_CARRY_L),
            np.maximum.accumulate(low_source[sl]) - row_carry,
        ).astype(np.int32, copy=False)
        cap_vals = np.minimum(
            np.int32(_CARRY_U),
            np.maximum.accumulate(cap_source[sl]) - row_carry,
        ).astype(np.int32, copy=False)
        delta_vals = group_base[sl].astype(np.int32, copy=False) - np.int32(int(group_base[s]))
        need_vals = lower_vals + delta_vals + np.int32(1)
        need_prefix = np.maximum.accumulate(need_vals)

        exit_lower[s, sl] = lower_vals.astype(np.int16, copy=False)
        exit_cap[s, sl] = cap_vals.astype(np.int16, copy=False)
        exit_delta[s, sl] = delta_vals.astype(np.int32, copy=False)
        exit_need[s, sl] = need_vals.astype(np.int32, copy=False)
        if int(need_prefix.shape[0]) > 1:
            exit_need_prefix_prev[s, s + 2 : gcount] = need_prefix[:-1].astype(np.int32, copy=False)
        exit_need_prefix_current[s, sl] = need_prefix.astype(np.int32, copy=False)

    lo0 = max(_CARRY_L, int(group_low[0]))
    hi0 = min(_CARRY_U, int(group_high[0]))
    return _GroupedTimelineContext(
        total_notes=n,
        group_starts=group_starts,
        group_base_t_ms=group_base,
        group_low_ms=group_low,
        group_high_ms=group_high,
        note_group_idx=note_group_idx,
        head_range_masks=head_range_masks,
        gcount=gcount,
        head_len=head_len,
        total_body=total_body,
        max_pow=max_pow,
        jump_b=jump_b,
        jump_a_lo=jump_a_lo,
        jump_a_hi=jump_a_hi,
        exit_lower=exit_lower,
        exit_cap=exit_cap,
        exit_delta=exit_delta,
        exit_need=exit_need,
        exit_need_prefix_prev=exit_need_prefix_prev,
        exit_need_prefix_current=exit_need_prefix_current,
        future_high_abs_suffix=future_high_abs_suffix,
        lo0=lo0,
        hi0=hi0,
    )


def _grouped_context_cache_key(
    total_notes: int,
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> tuple[object, ...]:
    key: list[object] = [int(total_notes)]
    for arr in arrays:
        key.extend((id(arr), tuple(int(v) for v in arr.shape), str(arr.dtype)))
    return tuple(key)


def _cached_grouped_timeline_context(
    total_notes: int,
    *,
    group_starts: np.ndarray,
    group_ends: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
) -> _GroupedTimelineContext:
    arrays = (
        np.asarray(group_starts, dtype=np.int32),
        np.asarray(group_ends, dtype=np.int32),
        np.asarray(group_base_t_ms, dtype=np.int32),
        np.asarray(group_low_ms, dtype=np.int32),
        np.asarray(group_high_ms, dtype=np.int32),
        np.asarray(note_group_idx, dtype=np.int32),
    )
    cache_key = _grouped_context_cache_key(int(total_notes), arrays)
    with _GROUPED_TIMELINE_CONTEXT_CACHE_LOCK:
        cached = _GROUPED_TIMELINE_CONTEXT_CACHE.get(cache_key)
        if cached is not None:
            _GROUPED_TIMELINE_CONTEXT_CACHE.move_to_end(cache_key)
            return cached

    ctx = _build_grouped_timeline_context(
        int(total_notes),
        group_starts=arrays[0],
        group_ends=arrays[1],
        group_base_t_ms=arrays[2],
        group_low_ms=arrays[3],
        group_high_ms=arrays[4],
        note_group_idx=arrays[5],
    )
    with _GROUPED_TIMELINE_CONTEXT_CACHE_LOCK:
        _GROUPED_TIMELINE_CONTEXT_CACHE[cache_key] = ctx
        _GROUPED_TIMELINE_CONTEXT_CACHE.move_to_end(cache_key)
        while len(_GROUPED_TIMELINE_CONTEXT_CACHE) > _GROUPED_TIMELINE_CONTEXT_CACHE_MAX:
            _GROUPED_TIMELINE_CONTEXT_CACHE.popitem(last=False)
    return ctx


def _empty_frontier_pack() -> TimelineFrontierPack:
    empty = TimelineExactSignature(
        head_len=0,
        head_bits=(0, 0, 0, 0),
        body_fever=0,
        body_normal=0,
        fever_activations=0,
        gap=0,
    )
    return TimelineFrontierPack(
        surfaces=(empty,),
        canonical=empty,
        sig0=_pack_mask_sig(0, 0, 0, 0),
        sig1=_pack_counts_sig(0, 0, 0, 0, 0),
        head_len=0,
        body_fever=0,
        body_normal=0,
        fever_activations=0,
        gap=0,
    )


@jit(nopython=True, cache=True)
def _propagate_band_jit(jump_b, jump_a_lo, jump_a_hi, start_g, lo, hi, target_g):
    """Binary-lifting band carry from start_g to target_g. Returns (1, 0) for an empty band
    (out_lo > out_hi), matching the Python reference. Pure numeric -> numba nopython."""
    g = start_g
    out_lo = lo
    out_hi = hi
    dist = target_g - start_g
    p2 = 0
    while dist != 0:
        if dist & 1:
            b = jump_b[g, p2]
            tlo = out_lo - b
            vlo = jump_a_lo[g, p2]
            out_lo = vlo if vlo > tlo else tlo
            thi = out_hi - b
            vhi = jump_a_hi[g, p2]
            out_hi = vhi if vhi > thi else thi
            g += 1 << p2
            if out_lo > out_hi:
                return 1, 0
        dist >>= 1
        p2 += 1
    return out_lo, out_hi


def _propagate_band_to_group(
    ctx: _GroupedTimelineContext,
    start_g: int,
    lo: int,
    hi: int,
    target_g: int,
    propagation_cache: dict[tuple[int, int, int, int], tuple[int, int]] | None = None,
) -> tuple[int, int]:
    if int(target_g) <= int(start_g):
        return int(lo), int(hi)
    cache_key = (int(start_g), int(lo), int(hi), int(target_g))
    if propagation_cache is not None:
        cached = propagation_cache.get(cache_key)
        if cached is not None:
            return cached
    out_lo, out_hi = _propagate_band_jit(
        ctx.jump_b, ctx.jump_a_lo, ctx.jump_a_hi, int(start_g), int(lo), int(hi), int(target_g)
    )
    result = (int(out_lo), int(out_hi))
    if propagation_cache is not None:
        propagation_cache[cache_key] = result
    return result


def _reachable_act_hi(ctx, activation_group: int, act_hi: int) -> int:
    """Cap the largest-cushion activation clock to the hit-time REACHABLE value.

    CANONICAL BASE OWNER, not legacy (record 16.25/16.38): this is the base path's single-window
    activation cap, physically validated (press-during-hold + lane-blind follower semantics) and
    kept lane-blind BY PROOF -- label-window uppers bind regardless of lane because the
    fill-preemption headroom is below the smallest fill unit, the same argument that closed the
    FG cap review (16.38). Handoff language describing deleted legacy predicates refers to the FG
    reachability gates collapsed in the 2026-07-07 hygiene sweep, not to this function.

    Base is all-Perfect, so each note's only latest legal hit is ``group_base_t_ms[g] +
    group_high_ms[g]`` and the fever bar completes on the ``fill_count``-th note IN LATEST-LEGAL-HIT
    ORDER (the decompiled server processes hits in physical time order -- see
    ``robeats-fever-clock-semantics``). The running-max band carry (:func:`_propagate_band_to_group`)
    makes the clock the max window over the INDEX-prefix ``[start_g, g_act]``, which OVER-estimates
    it whenever a wider-window group inflates the max past the latest hit of a LATER-INDEXED
    overlapping sibling that is unavoidably hit first -- the chord phantom (a held tail ``+80``
    indexed before a normal ``+40`` at the same timestamp: the normal is hit at ``+40`` first and
    really completes the bar, so the ``+80`` clock over-extends the drain window and sweeps a
    preempted note). A note ``j`` (index after ``g_act``) whose LATEST hit still precedes the clock
    ``h_a`` cannot be delayed past the activation, so the reachable clock cannot exceed its hit.

    This is the single-window analog of the FG reachability owner
    :func:`gear_optimizer.solver.taichi_gem.force_greats.fill_crossing.activation_hit_is_reachable_weighted_lane_aware`
    (a full-combo hit-time reachability predicate rather than a cap). Only the LATE edge is capped; ``act_lo``
    is untouched. Off overlap the forward scan runs 0 effective iterations (the next group's chart
    time is already ``>= h_a``), so ``act_hi`` is returned unchanged -- distinct-timestamp charts are
    bit-identical.
    """
    g_act = int(activation_group)
    base = int(ctx.group_base_t_ms[g_act])
    h_a = base + int(act_hi)  # activation latest-legal-hit, absolute ms
    gb = ctx.group_base_t_ms
    gh = ctx.group_high_ms
    gcount = int(ctx.gcount)
    cap = h_a
    j = g_act + 1
    # Scan bound: once a later group's chart time reaches h_a, its latest hit (chart + positive
    # window) is >= h_a, so it cannot preempt -- nothing further can lower the cap.
    while j < gcount and int(gb[j]) < h_a:
        pc_j = int(gb[j]) + int(gh[j])  # that note's own latest legal hit
        if pc_j < cap:  # unavoidably hit before the activation -> it completes the bar first
            cap = pc_j
        j += 1
    if cap < h_a:
        return int(act_hi) - (h_a - cap)  # == cap - base; lower the clock offset to the reachable hit
    return int(act_hi)


def _build_exact_timeline_frontier_from_context(
    ctx: _GroupedTimelineContext,
    *,
    fill_count: int,
    d_ms: int,
    exit_trace: list[_ExitTraceEntry] | None = None,
    transition_cache: dict[tuple[int, int, int, int], tuple[tuple[int, int, int, int], ...]] | None = None,
    propagation_cache: dict[tuple[int, int, int, int], tuple[int, int]] | None = None,
) -> TimelineFrontierPack:
    n = int(ctx.total_notes)
    if n <= 0:
        return _empty_frontier_pack()

    group_starts = ctx.group_starts
    note_group_idx = ctx.note_group_idx
    head_range_masks = ctx.head_range_masks
    gcount = int(ctx.gcount)
    head_len = int(ctx.head_len)
    total_body = int(ctx.total_body)
    fill_count_i = max(1, int(fill_count))
    d_ms_i = max(0, int(d_ms))

    # Reused scratch for the exit-enumeration kernel (max exits = gcount+1), so the many
    # per-build enumerations don't each allocate output arrays.
    _exit_cap = int(gcount) + 1
    exit_scratch = (
        np.empty(_exit_cap, dtype=np.int64),
        np.empty(_exit_cap, dtype=np.int64),
        np.empty(_exit_cap, dtype=np.int64),
        np.empty(_exit_cap, dtype=np.int64),
    )

    all_normal_cache: dict[int, TimelineExactSignature] = {}

    def _all_normal_surface(start_note: int) -> TimelineExactSignature:
        start_note_i = int(start_note)
        cached = all_normal_cache.get(start_note_i)
        if cached is not None:
            return cached
        surface = TimelineExactSignature(
            head_len=head_len,
            head_bits=(0, 0, 0, 0),
            body_fever=0,
            body_normal=total_body,
            fever_activations=0,
            gap=int(max(0, n - start_note_i)),
        )
        all_normal_cache[start_note_i] = surface
        return surface

    solve_cache: dict[tuple[int, int, int, int], tuple[TimelineExactSignature, ...]] = {}

    def _solve_from_boundary(start_group: int, lo: int, hi: int, is_first: bool) -> tuple[TimelineExactSignature, ...]:
        start_group_i = int(start_group)
        lo_i = int(lo)
        hi_i = int(hi)
        is_first_i = 1 if bool(is_first) else 0
        solve_key = (start_group_i, lo_i, hi_i, is_first_i)
        cached = solve_cache.get(solve_key)
        if cached is not None:
            return cached

        if start_group_i >= gcount:
            start_note_i = int(n)
        else:
            start_note_i = int(group_starts[start_group_i])

        notes_to_fill = int(fill_count_i - 1 if is_first_i else fill_count_i)
        if notes_to_fill < 0:
            notes_to_fill = 0
        activation_note = int(start_note_i + int(notes_to_fill))

        if activation_note >= n or activation_note <= 0 or start_note_i >= n:
            result = (_all_normal_surface(start_note_i),)
            solve_cache[solve_key] = result
            return result

        g_act = int(note_group_idx[activation_note])
        if g_act < 0 or g_act >= gcount:
            result = (_all_normal_surface(start_note_i),)
            solve_cache[solve_key] = result
            return result

        act_lo, act_hi = _propagate_band_to_group(
            ctx,
            start_group_i,
            lo_i,
            hi_i,
            g_act,
            propagation_cache=propagation_cache,
        )
        # Hit-time reachability: cap the largest-cushion clock so a wide-window group cannot claim a
        # late activation a later-indexed overlapping sibling (hit first) actually forecloses.
        act_hi = _reachable_act_hi(ctx, int(g_act), int(act_hi))
        if act_lo > act_hi:
            result = (_all_normal_surface(start_note_i),)
            solve_cache[solve_key] = result
            return result

        exits = _cached_first_exit_boundary_intervals(
            ctx,
            activation_group=int(g_act),
            act_lo=int(act_lo),
            act_hi=int(act_hi),
            d_ms=int(d_ms_i),
            transition_cache=transition_cache,
            scratch=exit_scratch,
        )
        if exit_trace is not None:
            exit_trace.append(
                _ExitTraceEntry(
                    activation_group=int(g_act),
                    act_lo=int(act_lo),
                    act_hi=int(act_hi),
                    exits=exits,
                )
            )

        candidates: list[TimelineExactSignature] = []
        for boundary_note, exit_group, exit_lo, exit_hi in exits:
            mask_start = max(0, min(int(activation_note), head_len))
            mask_end = max(0, min(int(boundary_note), head_len))
            if int(exit_group) >= gcount:
                range_mask = head_range_masks[mask_start, mask_end]
                body_add = 0
                if boundary_note > head_len:
                    body_start = max(head_len, int(activation_note))
                    if boundary_note > body_start:
                        body_add = int(boundary_note) - int(body_start)
                candidates.append(
                    TimelineExactSignature(
                        head_len=head_len,
                        head_bits=(
                            int(range_mask[0]),
                            int(range_mask[1]),
                            int(range_mask[2]),
                            int(range_mask[3]),
                        ),
                        body_fever=int(body_add),
                        body_normal=int(total_body - int(body_add)),
                        fever_activations=1,
                        gap=0,
                    )
                )
                continue

            future_frontier = _solve_from_boundary(
                int(exit_group),
                int(exit_lo),
                int(exit_hi),
                False,
            )
            for future in future_frontier:
                range_mask = head_range_masks[mask_start, mask_end]
                body_add = 0
                if boundary_note > head_len:
                    body_start = max(head_len, int(activation_note))
                    if boundary_note > body_start:
                        body_add = int(boundary_note) - int(body_start)

                body_fever = int(future.body_fever) + int(body_add)
                candidates.append(
                    TimelineExactSignature(
                        head_len=head_len,
                        head_bits=(
                            int(future.head_bits[0]) | int(range_mask[0]),
                            int(future.head_bits[1]) | int(range_mask[1]),
                            int(future.head_bits[2]) | int(range_mask[2]),
                            int(future.head_bits[3]) | int(range_mask[3]),
                        ),
                        body_fever=int(body_fever),
                        body_normal=int(total_body - body_fever),
                        fever_activations=int(future.fever_activations + 1),
                        gap=int(future.gap),
                    )
                )

        if not candidates:
            result = (_all_normal_surface(start_note_i),)
            solve_cache[solve_key] = result
            return result

        reduced = reduce_timeline_frontier(candidates)
        if not reduced:
            result = (_all_normal_surface(start_note_i),)
            solve_cache[solve_key] = result
            return result
        solve_cache[solve_key] = reduced
        return reduced

    frontier = _solve_from_boundary(0, int(ctx.lo0), int(ctx.hi0), True)
    if not frontier:
        frontier = (_all_normal_surface(0),)

    canonical = max(frontier, key=_surface_sort_key)
    sig0 = _pack_mask_sig(*canonical.head_bits)
    sig1 = _pack_counts_sig(
        canonical.body_fever,
        canonical.body_normal,
        canonical.head_len,
        canonical.fever_activations,
        canonical.gap,
    )
    return TimelineFrontierPack(
        surfaces=frontier,
        canonical=canonical,
        sig0=sig0,
        sig1=sig1,
        head_len=canonical.head_len,
        body_fever=canonical.body_fever,
        body_normal=canonical.body_normal,
        fever_activations=canonical.fever_activations,
        gap=canonical.gap,
    )


def _activation_offset_band_for_exit(
    ctx: _GroupedTimelineContext,
    *,
    activation_group: int,
    act_lo: int,
    act_hi: int,
    exit_group: int,
    d_ms: int,
) -> tuple[int, int]:
    """Feasible activation Perfect-hit offset band that produces this first exit.

    Returns the inclusive ``(lo, hi)`` offset interval (relative to the activation
    note's chart time) for which the carry-aware fever window first leaves fever at
    ``exit_group``. ``hi`` is the latest Perfect activation that still yields this
    surface (the largest-cushion witness); ``lo`` is the earliest. Raises when the
    interval is empty, which is an impossible internal state for a surface that was
    retained on the exact frontier.
    """
    s = int(activation_group)
    g = int(exit_group)
    lo = int(act_lo)
    hi = int(act_hi)
    if lo > hi:
        raise ValueError("timeline frontier trace received an empty activation band")
    if g <= s or s + 1 >= int(ctx.gcount):
        return lo, hi
    if g >= int(ctx.gcount):
        survive_lo = max(lo, int(ctx.exit_need_prefix_current[s, int(ctx.gcount) - 1]) - int(d_ms))
        if survive_lo > hi:
            raise ValueError("timeline frontier trace could not choose a terminal activation offset")
        return int(survive_lo), hi

    delta = int(ctx.exit_delta[s, g])
    r_lo = max(lo, int(ctx.exit_need_prefix_prev[s, g]) - int(d_ms))
    r_hi = min(hi, int(ctx.group_high_ms[g]) + delta - int(d_ms))
    if r_lo > r_hi:
        raise ValueError("timeline frontier trace could not choose an activation offset")
    return int(r_lo), int(r_hi)


def _subtract_timeline_edge(
    remaining_bits: tuple[int, int, int, int],
    remaining_body_fever: int,
    edge_bits: tuple[int, int, int, int],
    edge_body_fever: int,
) -> tuple[tuple[int, int, int, int], int] | None:
    for idx in range(4):
        if int(edge_bits[idx]) & ~int(remaining_bits[idx]):
            return None
    if int(edge_body_fever) > int(remaining_body_fever):
        return None
    return (
        (
            int(remaining_bits[0]) & ~int(edge_bits[0]),
            int(remaining_bits[1]) & ~int(edge_bits[1]),
            int(remaining_bits[2]) & ~int(edge_bits[2]),
            int(remaining_bits[3]) & ~int(edge_bits[3]),
        ),
        int(remaining_body_fever) - int(edge_body_fever),
    )


def reconstruct_timeline_frontier_trace(
    *,
    total_notes: int,
    group_starts: np.ndarray,
    group_ends: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
    fill_count: int,
    d_ms: int,
    target_surface: TimelineExactSignature,
) -> tuple[dict[str, object], ...]:
    """Reconstruct one compact Perfect-window witness for a selected base surface."""

    ctx = _cached_grouped_timeline_context(
        int(total_notes),
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )
    n = int(ctx.total_notes)
    if n <= 0:
        return ()

    target_bits = (
        int(target_surface.head_bits[0]),
        int(target_surface.head_bits[1]),
        int(target_surface.head_bits[2]),
        int(target_surface.head_bits[3]),
    )
    target_body_fever = int(target_surface.body_fever)
    if target_body_fever < 0 or target_body_fever > int(ctx.total_body):
        raise ValueError("timeline frontier trace target has invalid body fever count")
    if int(target_surface.body_normal) != int(ctx.total_body) - target_body_fever:
        raise ValueError("timeline frontier trace target body counts do not match song body count")

    transition_cache: dict[tuple[int, int, int, int], tuple[tuple[int, int, int, int], ...]] = {}
    propagation_cache: dict[tuple[int, int, int, int], tuple[int, int]] = {}
    fill_count_i = max(1, int(fill_count))
    d_ms_i = max(0, int(d_ms))

    def _empty(bits: tuple[int, int, int, int], body_fever: int) -> bool:
        return int(body_fever) == 0 and not any(int(value) for value in bits)

    def _search(
        start_group: int,
        lo: int,
        hi: int,
        is_first: bool,
        remaining_bits: tuple[int, int, int, int],
        remaining_body_fever: int,
    ) -> tuple[dict[str, object], ...] | None:
        if _empty(remaining_bits, remaining_body_fever):
            return ()
        start_group_i = int(start_group)
        start_note_i = int(n) if start_group_i >= int(ctx.gcount) else int(ctx.group_starts[start_group_i])
        notes_to_fill = int(fill_count_i - 1 if bool(is_first) else fill_count_i)
        activation_note = int(start_note_i + max(0, notes_to_fill))
        if activation_note >= n or activation_note <= 0 or start_note_i >= n:
            return None

        g_act = int(ctx.note_group_idx[activation_note])
        if g_act < 0 or g_act >= int(ctx.gcount):
            return None

        act_lo, act_hi = _propagate_band_to_group(
            ctx,
            start_group_i,
            int(lo),
            int(hi),
            g_act,
            propagation_cache=propagation_cache,
        )
        # Hit-time reachability: same cap as the build site, so the reconstructed trace enumerates
        # against the same reachable clock the persisted surface was built with.
        act_hi = _reachable_act_hi(ctx, int(g_act), int(act_hi))
        if act_lo > act_hi:
            return None

        exits = _cached_first_exit_boundary_intervals(
            ctx,
            activation_group=g_act,
            act_lo=int(act_lo),
            act_hi=int(act_hi),
            d_ms=d_ms_i,
            transition_cache=transition_cache,
        )
        for boundary_note, exit_group, exit_lo, exit_hi in exits:
            mask_start = max(0, min(int(activation_note), int(ctx.head_len)))
            mask_end = max(0, min(int(boundary_note), int(ctx.head_len)))
            range_mask_arr = ctx.head_range_masks[mask_start, mask_end]
            edge_bits = (
                int(range_mask_arr[0]),
                int(range_mask_arr[1]),
                int(range_mask_arr[2]),
                int(range_mask_arr[3]),
            )
            body_add = 0
            if int(boundary_note) > int(ctx.head_len):
                body_start = max(int(ctx.head_len), int(activation_note))
                if int(boundary_note) > int(body_start):
                    body_add = int(boundary_note) - int(body_start)
            next_remaining = _subtract_timeline_edge(
                remaining_bits,
                int(remaining_body_fever),
                edge_bits,
                int(body_add),
            )
            if next_remaining is None:
                continue

            activation_ms = int(ctx.group_base_t_ms[g_act])
            offset_lo, offset_hi = _activation_offset_band_for_exit(
                ctx,
                activation_group=g_act,
                act_lo=int(act_lo),
                act_hi=int(act_hi),
                exit_group=int(exit_group),
                d_ms=d_ms_i,
            )
            # Largest-cushion witness time (issue #41): the band's upper end is
            # the latest activation clock yielding this exit; fever_window_end_ms
            # pins the displayed duration to d_ms regardless of boundary-note
            # timing.
            #
            # The band is the carry CLOCK (running max over every Perfect hit so
            # far), so its upper edge can exceed the count-boundary note's OWN
            # Perfect window when an earlier wider-window note (a chorded held
            # tail, [-40,+80], grouped separately by (timestamp, window)) delivers
            # the activating hit. The witness must name a note that can legally be
            # hit at the chosen clock time: activation_index keeps the count /
            # fever-mask boundary, while fever_start_note_index and every
            # activation_hit_* field describe the physical activating hit,
            # attributed to the LATEST already-hit group whose own Perfect window
            # contains it.
            hit_abs_ms = int(activation_ms) + int(offset_hi)
            witness_group = int(g_act)
            if not (
                int(ctx.group_low_ms[g_act]) <= int(offset_hi) <= int(ctx.group_high_ms[g_act])
            ):
                witness_group = -1
                max_group_high = int(np.max(ctx.group_high_ms))
                for g in range(int(g_act) - 1, -1, -1):
                    g_base = int(ctx.group_base_t_ms[g])
                    if g_base + max_group_high < hit_abs_ms:
                        break
                    if (
                        g_base + int(ctx.group_low_ms[g])
                        <= hit_abs_ms
                        <= g_base + int(ctx.group_high_ms[g])
                    ):
                        witness_group = g
                        break
                if witness_group < 0:
                    raise ValueError(
                        "timeline frontier trace clock witness is outside every "
                        "already-hit note's Perfect window"
                    )
            if witness_group == int(g_act):
                witness_note = int(activation_note)
            else:
                witness_note = int(ctx.group_starts[witness_group + 1]) - 1
            witness_base_ms = int(ctx.group_base_t_ms[witness_group])
            activation_offset_ms = hit_abs_ms - witness_base_ms
            # Feasible witness band for THAT note: the clock band mapped onto the
            # witness note's chart time, clamped to its own Perfect window (every
            # value still yields this same first exit, so the surface and scores
            # are unchanged).
            witness_lo = max(
                int(activation_ms) + int(offset_lo) - witness_base_ms,
                int(ctx.group_low_ms[witness_group]),
            )
            activation_hit_ms = float(hit_abs_ms)
            if int(boundary_note) >= n or int(exit_group) >= int(ctx.gcount):
                fever_end_ms: float | None = None
            else:
                fever_end_ms = float(int(ctx.group_base_t_ms[int(exit_group)]))
            section = {
                "activation_index": int(activation_note),
                "activation_ms": float(witness_base_ms),
                "activation_hit_ms": activation_hit_ms,
                "activation_hit_offset_ms": float(activation_offset_ms),
                "activation_hit_offset_lower_ms": float(witness_lo),
                "activation_hit_offset_upper_ms": float(activation_offset_ms),
                "activation_hit_window_lower_ms": float(witness_base_ms + witness_lo),
                "activation_hit_window_upper_ms": float(hit_abs_ms),
                "activation_hit_window_width_ms": float(max(0, activation_offset_ms - witness_lo)),
                "activation_hit_offset_kind": "largest_cushion",
                "activation_judgment": "perfect",
                "fever_start_source": "perfect_window",
                "fever_start_note_index": int(witness_note),
                "fever_start_hit_ms": activation_hit_ms,
                "fever_end_index": int(boundary_note),
                "fever_end_ms": fever_end_ms,
                "fever_window_end_ms": activation_hit_ms + float(d_ms_i),
                "forced_count": 0,
                "forced_start_index": int(activation_note),
                "forced_prefix_count": 0,
                "body_fever": int(body_add),
                "body_great": 0,
                "body_fever_great": 0,
            }

            rem_bits, rem_body = next_remaining
            if _empty(rem_bits, rem_body):
                return (section,)
            if int(exit_group) >= int(ctx.gcount):
                continue
            tail = _search(int(exit_group), int(exit_lo), int(exit_hi), False, rem_bits, int(rem_body))
            if tail is not None:
                return (section,) + tail
        return None

    trace = _search(0, int(ctx.lo0), int(ctx.hi0), True, target_bits, target_body_fever)
    if trace is None:
        raise ValueError("could not reconstruct timeline frontier surface trace")
    return tuple({**dict(row), "section": idx + 1} for idx, row in enumerate(trace))


def _exit_trace_certifies_d_ms(
    ctx: _GroupedTimelineContext,
    trace: list[_ExitTraceEntry],
    d_ms: int,
    *,
    transition_cache: dict[tuple[int, int, int, int], tuple[tuple[int, int, int, int], ...]] | None = None,
) -> bool:
    for entry in trace:
        exits = _cached_first_exit_boundary_intervals(
            ctx,
            activation_group=int(entry.activation_group),
            act_lo=int(entry.act_lo),
            act_hi=int(entry.act_hi),
            d_ms=int(d_ms),
            transition_cache=transition_cache,
        )
        if exits != entry.exits:
            return False
    return True


@dataclass(frozen=True)
class _TimelineFillCountPairBuild:
    pair_cache: dict[tuple[int, int], TimelineFrontierPack]
    solved_pair_count: int
    trace_equivalent_reused_pair_count: int
    pair_build_ms_total: float
    pair_build_ms_max: float
    pair_surface_total: int
    pair_surface_max: int
    pack_sig_counts: dict[tuple[int, int], int]


def _build_timeline_pair_cache_for_fill_count(
    ctx: _GroupedTimelineContext,
    fill_count_i: int,
    d_ms_list: list[int],
) -> _TimelineFillCountPairBuild:
    transition_cache: dict[tuple[int, int, int, int], tuple[tuple[int, int, int, int], ...]] = {}
    propagation_cache: dict[tuple[int, int, int, int], tuple[int, int]] = {}
    pair_cache: dict[tuple[int, int], TimelineFrontierPack] = {}
    solved_pair_count = 0
    pair_build_ms_total = 0.0
    pair_build_ms_max = 0.0
    pair_surface_total = 0
    pair_surface_max = 0
    trace_equivalent_reused_pair_count = 0
    pack_sig_counts: dict[tuple[int, int], int] = {}
    d_idx = 0
    while d_idx < len(d_ms_list):
        d_ms = int(d_ms_list[d_idx])
        key = (int(d_ms), int(fill_count_i))
        if key in pair_cache:
            d_idx += 1
            continue
        trace: list[_ExitTraceEntry] = []
        t_pair = time.perf_counter()
        pack = _build_exact_timeline_frontier_from_context(
            ctx,
            fill_count=fill_count_i,
            d_ms=int(d_ms),
            exit_trace=trace,
            transition_cache=transition_cache,
            propagation_cache=propagation_cache,
        )
        solved_pair_count += 1
        pair_ms = float((time.perf_counter() - t_pair) * 1000.0)
        pair_build_ms_total += pair_ms
        if pair_ms > pair_build_ms_max:
            pair_build_ms_max = pair_ms
        count = int(len(pack.surfaces))
        sig_key = (int(pack.sig0), int(pack.sig1))
        pack_sig_counts[sig_key] = int(pack_sig_counts.get(sig_key, 0)) + 1
        pair_surface_total += count
        if count > pair_surface_max:
            pair_surface_max = count
        pair_cache[key] = pack
        d_idx += 1
        while d_idx < len(d_ms_list):
            reuse_d_ms = int(d_ms_list[d_idx])
            reuse_key = (reuse_d_ms, fill_count_i)
            if reuse_key in pair_cache:
                d_idx += 1
                continue
            if not _exit_trace_certifies_d_ms(
                ctx,
                trace,
                int(reuse_d_ms),
                transition_cache=transition_cache,
            ):
                break
            pair_cache[reuse_key] = pack
            trace_equivalent_reused_pair_count += 1
            d_idx += 1
    return _TimelineFillCountPairBuild(
        pair_cache=pair_cache,
        solved_pair_count=int(solved_pair_count),
        pair_build_ms_total=float(pair_build_ms_total),
        pair_build_ms_max=float(pair_build_ms_max),
        pair_surface_total=int(pair_surface_total),
        pair_surface_max=int(pair_surface_max),
        trace_equivalent_reused_pair_count=int(trace_equivalent_reused_pair_count),
        pack_sig_counts=pack_sig_counts,
    )


def build_timeline_frontier_grid_payload(
    *,
    song_slot: int,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    song_key: str | None = None,
    group_starts: np.ndarray,
    group_ends: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
    ref_ft: np.ndarray,
    ref_ff: np.ndarray,
) -> TimelineFrontierGridPayload:
    song_slot_i = int(song_slot)
    if song_slot_i < 0:
        raise ValueError(f"song_slot out of range: {song_slot_i}")
    # Disk-cache payloads are slot-agnostic and always materialized at slot 0.
    # Runtime upload remaps this source slot into the active GPU song slot.
    payload_slot_i = 0
    payload_slots = 1

    ref_ft = np.asarray(ref_ft, dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_ff, dtype=np.float32).reshape(-1)
    if int(ref_ft.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Time axis must be shape ({GRID_SIZE},), got {ref_ft.shape}")
    if int(ref_ff.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Fill Rate axis must be shape ({GRID_SIZE},), got {ref_ff.shape}")

    total_notes_i = int(total_notes)
    long_notes_i = int(long_notes)
    non_fever_cas = float(max(0, total_notes_i - long_notes_i)) * 0.333
    fever_time_cas = float(last_note_time) * FEVER_TIME_SCALE + FEVER_TIME_OFFSET

    fill_counts = np.ceil(np.float32(non_fever_cas) * ref_ff).astype(np.int32)
    fill_counts = np.maximum(fill_counts, np.int32(1))
    d_ms_values = np.ceil(np.float32(fever_time_cas) * ref_ft * np.float32(1000.0)).astype(np.int32)
    d_ms_values = np.maximum(d_ms_values, np.int32(0))

    grid_count_body_fever = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_count_body_normal = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_head_len = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int8)
    grid_fever_masks_bits = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
    grid_frontier_count = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_frontier_offset = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_frontier_body_fever_pool = np.zeros((payload_slots, MAX_TIMELINE_FRONTIER_SURFACES), dtype=np.int32)
    grid_frontier_body_normal_pool = np.zeros((payload_slots, MAX_TIMELINE_FRONTIER_SURFACES), dtype=np.int32)
    grid_frontier_masks_bits_pool = np.zeros(
        (payload_slots, MAX_TIMELINE_FRONTIER_SURFACES, 4), dtype=np.uint32
    )
    # Per-VARIANT head coefficients (n_hn, n_hf, sigma_hn, sigma_hf): the eval kernel's
    # upper bound needs them for every pool row, not just the cell-canonical surface.
    # i16 is exact (n <= 100, sigma <= 5050).
    grid_frontier_head_coeffs_pool = np.zeros((payload_slots, MAX_TIMELINE_FRONTIER_SURFACES, 4), dtype=np.int16)
    grid_gap = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_fever_activations = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)

    unique_fill_counts, fill_inverse = np.unique(fill_counts, return_inverse=True)
    unique_d_ms, d_inverse = np.unique(d_ms_values, return_inverse=True)
    ctx = _build_grouped_timeline_context(
        total_notes_i,
        group_starts=group_starts,
        group_ends=group_ends,
        group_base_t_ms=group_base_t_ms,
        group_low_ms=group_low_ms,
        group_high_ms=group_high_ms,
        note_group_idx=note_group_idx,
    )
    pool_offset_by_pack_signature: dict[tuple[tuple[int, int, int, int, int, int, int], ...], int] = {}
    pool_cursor = 0
    head_coeff_cache: dict[tuple[int, int, int, int, int], tuple[int, int, int, int]] = {}

    def _store_pack(pack: TimelineFrontierPack) -> int:
        nonlocal pool_cursor
        count = int(len(pack.surfaces))
        pack_pool_key = tuple(
            (
                int(surf.body_fever),
                int(surf.body_normal),
                int(surf.head_bits[0]),
                int(surf.head_bits[1]),
                int(surf.head_bits[2]),
                int(surf.head_bits[3]),
                int(surf.fever_activations),
            )
            for surf in pack.surfaces
        )
        existing_offset = pool_offset_by_pack_signature.get(pack_pool_key)
        if existing_offset is not None:
            return int(existing_offset)
        if pool_cursor + count > int(MAX_TIMELINE_FRONTIER_SURFACES):
            raise RuntimeError(
                "timeline frontier pool overflow: "
                f"need {pool_cursor + count}, cap {MAX_TIMELINE_FRONTIER_SURFACES}"
            )
        offset = int(pool_cursor)
        pool_offset_by_pack_signature[pack_pool_key] = offset
        for local_idx, surf in enumerate(pack.surfaces):
            pool_idx = pool_cursor + local_idx
            grid_frontier_body_fever_pool[payload_slot_i, pool_idx] = int(surf.body_fever)
            grid_frontier_body_normal_pool[payload_slot_i, pool_idx] = int(surf.body_normal)
            grid_frontier_masks_bits_pool[payload_slot_i, pool_idx, 0] = np.uint32(int(surf.head_bits[0]))
            grid_frontier_masks_bits_pool[payload_slot_i, pool_idx, 1] = np.uint32(int(surf.head_bits[1]))
            grid_frontier_masks_bits_pool[payload_slot_i, pool_idx, 2] = np.uint32(int(surf.head_bits[2]))
            grid_frontier_masks_bits_pool[payload_slot_i, pool_idx, 3] = np.uint32(int(surf.head_bits[3]))
            coeff_key = (
                int(surf.head_bits[0]),
                int(surf.head_bits[1]),
                int(surf.head_bits[2]),
                int(surf.head_bits[3]),
                int(surf.head_len),
            )
            coeffs = head_coeff_cache.get(coeff_key)
            if coeffs is None:
                coeffs = _head_mask_coefficients_py(
                    surf.head_bits[0],
                    surf.head_bits[1],
                    surf.head_bits[2],
                    surf.head_bits[3],
                    head_len=surf.head_len,
                )
                head_coeff_cache[coeff_key] = coeffs
            grid_frontier_head_coeffs_pool[payload_slot_i, pool_idx, 0] = np.int16(int(coeffs[0]))
            grid_frontier_head_coeffs_pool[payload_slot_i, pool_idx, 1] = np.int16(int(coeffs[1]))
            grid_frontier_head_coeffs_pool[payload_slot_i, pool_idx, 2] = np.int16(int(coeffs[2]))
            grid_frontier_head_coeffs_pool[payload_slot_i, pool_idx, 3] = np.int16(int(coeffs[3]))
        pool_cursor += count
        return offset

    t_pairs = time.perf_counter()
    d_ms_list = [int(x) for x in unique_d_ms.tolist()]
    fill_counts_list = [int(x) for x in unique_fill_counts.tolist()]
    pair_cache: dict[tuple[int, int], tuple[TimelineFrontierPack, int]] = {}
    solved_pair_count = 0
    pair_build_ms_total = 0.0
    pair_build_ms_max = 0.0
    pair_surface_total = 0
    pair_surface_max = 0
    pack_sig_counts: dict[tuple[int, int], int] = {}
    trace_equivalent_reused_pair_count = 0
    thread_count = max(1, int(_TIMELINE_PAIR_BUILD_THREADS))
    if thread_count <= 1 or len(fill_counts_list) <= 1:
        builds = [
            _build_timeline_pair_cache_for_fill_count(ctx, int(fill_count_i), d_ms_list)
            for fill_count_i in fill_counts_list
        ]
    else:
        workers = min(thread_count, len(fill_counts_list))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            builds = list(
                executor.map(
                    lambda fill_count_i: _build_timeline_pair_cache_for_fill_count(ctx, int(fill_count_i), d_ms_list),
                    fill_counts_list,
                )
            )
    for build in builds:
        solved_pair_count += int(build.solved_pair_count)
        trace_equivalent_reused_pair_count += int(build.trace_equivalent_reused_pair_count)
        pair_build_ms_total += float(build.pair_build_ms_total)
        pair_build_ms_max = max(pair_build_ms_max, float(build.pair_build_ms_max))
        pair_surface_total += int(build.pair_surface_total)
        pair_surface_max = max(pair_surface_max, int(build.pair_surface_max))
        for sig_key, count in build.pack_sig_counts.items():
            pack_sig_counts[sig_key] = int(pack_sig_counts.get(sig_key, 0)) + int(count)
        for key in sorted(build.pair_cache.keys()):
            if key in pair_cache:
                continue
            pack = build.pair_cache[key]
            pair_cache[key] = (pack, _store_pack(pack))

    _emit_frontier_phase(
        phase="pair_builds",
        start=t_pairs,
        song_key=song_key,
        song_slot=song_slot_i,
        unique_fill_counts=int(unique_fill_counts.size),
        unique_d_ms=int(unique_d_ms.size),
        pair_count=int(len(pair_cache)),
        solved_pair_count=int(solved_pair_count),
        plateau_reused_pair_count=int(trace_equivalent_reused_pair_count),
        trace_equivalent_reused_pair_count=int(trace_equivalent_reused_pair_count),
        transition_cache_entries=0,
        propagation_cache_entries=0,
        pair_build_ms_total=float(pair_build_ms_total),
        pair_build_ms_max=float(pair_build_ms_max),
        pair_surface_total=int(pair_surface_total),
        pair_surface_max=int(pair_surface_max),
        unique_pack_signatures=int(len(pack_sig_counts)),
        duplicate_pack_pairs=int(len(pair_cache) - len(pack_sig_counts)),
        unique_pool_packs=int(len(pool_offset_by_pack_signature)),
        frontier_pool_used=int(pool_cursor),
    )

    t_cells = time.perf_counter()
    dense_shape = (int(unique_d_ms.size), int(unique_fill_counts.size))
    d_pos = {int(v): idx for idx, v in enumerate(unique_d_ms.tolist())}
    f_pos = {int(v): idx for idx, v in enumerate(unique_fill_counts.tolist())}
    dense_body_fever = np.zeros(dense_shape, dtype=np.int32)
    dense_body_normal = np.zeros(dense_shape, dtype=np.int32)
    dense_head_len = np.zeros(dense_shape, dtype=np.int8)
    dense_masks = np.zeros((*dense_shape, 4), dtype=np.uint32)
    dense_frontier_count = np.zeros(dense_shape, dtype=np.int32)
    dense_frontier_offset = np.zeros(dense_shape, dtype=np.int32)
    dense_gap = np.zeros(dense_shape, dtype=np.int32)
    dense_fever_activations = np.zeros(dense_shape, dtype=np.int32)

    for (d_key, fc_key), (pack, offset) in pair_cache.items():
        d_i = int(d_pos[int(d_key)])
        f_i = int(f_pos[int(fc_key)])
        canonical = pack.canonical
        dense_body_fever[d_i, f_i] = int(canonical.body_fever)
        dense_body_normal[d_i, f_i] = int(canonical.body_normal)
        dense_head_len[d_i, f_i] = np.int8(int(canonical.head_len))
        dense_masks[d_i, f_i, 0] = np.uint32(int(canonical.head_bits[0]))
        dense_masks[d_i, f_i, 1] = np.uint32(int(canonical.head_bits[1]))
        dense_masks[d_i, f_i, 2] = np.uint32(int(canonical.head_bits[2]))
        dense_masks[d_i, f_i, 3] = np.uint32(int(canonical.head_bits[3]))
        dense_frontier_count[d_i, f_i] = int(len(pack.surfaces))
        dense_frontier_offset[d_i, f_i] = int(offset)
        dense_gap[d_i, f_i] = int(canonical.gap)
        dense_fever_activations[d_i, f_i] = int(canonical.fever_activations)

    grid_d_idx = d_inverse.reshape(GRID_SIZE, 1)
    grid_f_idx = fill_inverse.reshape(1, GRID_SIZE)
    grid_count_body_fever[payload_slot_i] = dense_body_fever[grid_d_idx, grid_f_idx]
    grid_count_body_normal[payload_slot_i] = dense_body_normal[grid_d_idx, grid_f_idx]
    grid_head_len[payload_slot_i] = dense_head_len[grid_d_idx, grid_f_idx]
    grid_fever_masks_bits[payload_slot_i] = dense_masks[grid_d_idx, grid_f_idx]
    grid_frontier_count[payload_slot_i] = dense_frontier_count[grid_d_idx, grid_f_idx]
    grid_frontier_offset[payload_slot_i] = dense_frontier_offset[grid_d_idx, grid_f_idx]
    grid_gap[payload_slot_i] = dense_gap[grid_d_idx, grid_f_idx]
    grid_fever_activations[payload_slot_i] = dense_fever_activations[grid_d_idx, grid_f_idx]

    frontier_cells = int(np.count_nonzero(grid_frontier_count[payload_slot_i]))
    frontier_variants = int(np.sum(grid_frontier_count[payload_slot_i], dtype=np.int64))
    _emit_frontier_phase(
        phase="grid_fill",
        start=t_cells,
        song_key=song_key,
        song_slot=song_slot_i,
        cell_count=int(GRID_SIZE * GRID_SIZE),
        frontier_cells=frontier_cells,
        frontier_variants=frontier_variants,
        frontier_pool_used=int(pool_cursor),
    )

    return TimelineFrontierGridPayload(
        grid_count_body_fever=grid_count_body_fever,
        grid_count_body_normal=grid_count_body_normal,
        grid_head_len=grid_head_len,
        grid_fever_masks_bits=grid_fever_masks_bits,
        grid_frontier_count=grid_frontier_count,
        grid_frontier_offset=grid_frontier_offset,
        grid_frontier_body_fever_pool=grid_frontier_body_fever_pool,
        grid_frontier_body_normal_pool=grid_frontier_body_normal_pool,
        grid_frontier_masks_bits_pool=grid_frontier_masks_bits_pool,
        grid_frontier_head_coeffs_pool=grid_frontier_head_coeffs_pool,
        grid_gap=grid_gap,
        grid_fever_activations=grid_fever_activations,
        frontier_pool_used=int(pool_cursor),
    )
