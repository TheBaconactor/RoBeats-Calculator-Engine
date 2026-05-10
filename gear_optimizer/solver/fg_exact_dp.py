"""
Exact ForceGreats DP.

This module implements an exact dynamic program for ForceGreats that matches the repo's
timeline semantics:
  - fill-delay via notes_to_fill(k) = ceil(raw_fill + 0.5*k) with the section-1 offset
  - optional timing-aware carry via great-candidate timestamps (prefix-max carry_time)

Usage:
  - Kept as a fixed-stat proof/reference solver for timing semantics.
  - Production FG exploration uses the finder surface with exact-inner BnB per generated
    FG timeline instead of this fixed-stat refinement pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import ceil, floor
from typing import Literal

import numpy as np

from ..core.constants import TOTAL_ROWS
from ..core.utils import safe_int
from .timing_envelope import (
    TimelineAnalysisInputs,
    count_timeline_analysis_windows,
    prepare_timeline_analysis_inputs,
)
from .scoring.stats_scoring import build_great_penalty_table

_MAX_HEAD = 100


@dataclass
class FGExactDPProfile:
    states: int = 0
    transitions: int = 0
    max_cached_states: int = 0


@dataclass(frozen=True)
class FGExactDPSolution:
    best_delta: int
    section_counts: list[int]
    profile: FGExactDPProfile


@dataclass(frozen=True)
class FGExactDPPreparedInputs:
    timestamps: np.ndarray
    great_candidates: np.ndarray | None
    total_notes: int
    last_note_time: float
    raw_fill: float
    non_fever_base: int
    fever_duration: float
    ft_idx: int
    w_prefix: np.ndarray
    c_prefix: np.ndarray
    timeline_analysis: TimelineAnalysisInputs | None = None


def _build_fever_bonus_prefix(
    *,
    total_notes: int,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
) -> np.ndarray:
    n = int(max(0, int(total_notes)))
    out = np.zeros(n + 1, dtype=np.int64)
    if n <= 0:
        return out

    head_len = min(_MAX_HEAD, n)
    base_f = np.float32(float(base_value))
    combo_f = np.float32(float(combo_mul))
    fever_f = np.float32(float(fever_mul))
    factor = np.float32((combo_f - np.float32(1.0)) * base_f / np.float32(100.0))

    body_normal = int(np.float32(base_f * combo_f))
    body_fever = int(np.float32(np.float32(base_f * combo_f) * fever_f))
    body_bonus = int(body_fever - body_normal)

    running = 0
    for i in range(n):
        if i < head_len:
            current_ramp = np.float32(base_f + np.float32(i + 1) * factor)
            bonus = int(np.float32(current_ramp * fever_f)) - int(current_ramp)
        else:
            bonus = int(body_bonus)
        running += int(bonus)
        out[i + 1] = int(running)
    return out


def _build_forced_great_penalty_prefix(
    *,
    total_notes: int,
    base_value: float,
    combo_mul: float,
    primary_val: int,
    secondary_val: int,
) -> np.ndarray:
    """
    Build prefix sums of per-note forced-Great penalties c_i >= 0.

    Mirrors the shared ForceGreats timeline semantics used by exact replay.
    """
    n = int(total_notes)
    if n <= 0:
        return np.zeros((1,), dtype=np.int64)

    combo_value = floor(float(base_value) * float(combo_mul))

    great_penalty_base_head = floor((primary_val * 2) * (2.0 / 3.0)) + floor(secondary_val * (2.0 / 3.0)) + 150
    great_penalty_base_raw = ((primary_val * 2) * (2.0 / 3.0)) + (secondary_val * (2.0 / 3.0)) + 150.0
    great_combo_value = floor(float(great_penalty_base_raw) * float(combo_mul))
    body_penalty = max(0, int(combo_value - great_combo_value))

    penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base_head, head_limit=100)
    if penalty_table:
        penalty_table[-1] = body_penalty

    c = np.empty((n,), dtype=np.int32)
    head_len = min(100, n)
    if head_len > 0:
        c[:head_len] = np.asarray(penalty_table[:head_len], dtype=np.int32)
    if n > 100:
        c[100:n] = int(body_penalty)

    out = np.empty((n + 1,), dtype=np.int64)
    out[0] = 0
    out[1:] = np.cumsum(c, dtype=np.int64)
    return out


def _build_fp_actions(raw_fill: float, non_fever_base: int) -> list[tuple[int, ...]]:
    """
    Return action set in FP-target space.

    For each fill-delay level p (0..p_max), return a tuple of k candidates (forced counts)
    that satisfy fp(k)=p, ordered ascending. In this model fp(k) is a staircase with
    plateau length at most 2, so each tuple has length 1 or 2.
    """
    m = int(non_fever_base)
    if m <= 0:
        return [(0,)]

    p_to_ks: list[list[int]] = []
    for k in range(m + 1):
        p = int(ceil(float(raw_fill) + 0.5 * float(k)) - float(m))
        if p < 0:
            p = 0
        while p >= len(p_to_ks):
            p_to_ks.append([])
        if len(p_to_ks[p]) < 2:
            p_to_ks[p].append(int(k))

    # Ensure dense p=0..p_max with at least one representative each.
    out: list[tuple[int, ...]] = []
    for ks in p_to_ks:
        if not ks:
            out.append((0,))
        else:
            out.append(tuple(ks))
    return out


def prepare_force_greats_exact_dp_inputs(
    *,
    stats: dict,
    calc_song: dict,
    ref_arrays: dict,
) -> FGExactDPPreparedInputs | None:
    if not isinstance(stats, dict) or not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return None

    timeline = prepare_timeline_analysis_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="fg")
    if timeline is None:
        return None

    w_prefix = _build_fever_bonus_prefix(
        total_notes=timeline.total_notes,
        base_value=timeline.base_value,
        combo_mul=timeline.combo_mul,
        fever_mul=timeline.fever_mul,
    )
    c_prefix = _build_forced_great_penalty_prefix(
        total_notes=timeline.total_notes,
        base_value=timeline.base_value,
        combo_mul=timeline.combo_mul,
        primary_val=int(timeline.primary_val),
        secondary_val=int(timeline.secondary_val),
    )

    return FGExactDPPreparedInputs(
        timestamps=timeline.timestamps,
        great_candidates=timeline.great_candidates,
        total_notes=int(timeline.total_notes),
        last_note_time=float(timeline.last_note_time),
        raw_fill=float(timeline.raw_fill),
        non_fever_base=int(timeline.non_fever_base),
        fever_duration=float(timeline.fever_duration),
        ft_idx=max(0, min(TOTAL_ROWS, safe_int(stats.get("Fever Time", timeline.ft_idx), timeline.ft_idx))),
        w_prefix=w_prefix,
        c_prefix=c_prefix,
        timeline_analysis=timeline,
    )


def score_force_greats_exact_dp_bonus_from_prepared(
    *,
    prepared: FGExactDPPreparedInputs,
    section_counts: list[int] | tuple[int, ...] | None,
) -> int:
    """
    Return the exact DP objective value for an explicit forced-count path.

    This is the fixed-stat bonus relative to the all-normal timeline:
      (fever bonus gained) - (forced Great penalties paid)

    The production FG path uses this to convert exact-DP `best_delta` against the
    correct zero-force baseline for the same resolved stat point.
    """

    if not isinstance(prepared, FGExactDPPreparedInputs):
        return 0

    timestamps = prepared.timestamps
    great_candidates = prepared.great_candidates
    total_notes = int(prepared.total_notes)
    raw_fill = float(prepared.raw_fill)
    non_fever_base = int(prepared.non_fever_base)
    fever_duration = float(prepared.fever_duration)
    w_prefix = prepared.w_prefix
    c_prefix = prepared.c_prefix
    if total_notes <= 0:
        return 0

    counts = [int(x) for x in list(section_counts or [])]
    use_timing_carry = great_candidates is not None

    end_times_song = timestamps.astype(np.float64) + float(fever_duration)
    fever_end_song = np.searchsorted(timestamps, end_times_song, side="left").astype(np.int32, copy=False)
    if use_timing_carry:
        assert great_candidates is not None
        end_times_gc = great_candidates.astype(np.float64) + float(fever_duration)
        fever_end_gc = np.searchsorted(timestamps, end_times_gc, side="left").astype(np.int32, copy=False)
    else:
        fever_end_gc = None

    def _canon_carry(i: int, carry_idx: int) -> int:
        if (not use_timing_carry) or int(carry_idx) < 0:
            return -1
        if int(i) >= int(total_notes):
            return -1
        assert great_candidates is not None
        cidx = int(carry_idx)
        return -1 if float(great_candidates[cidx]) <= float(timestamps[int(i)]) else cidx

    total_bonus = 0
    i = 0
    is_first = True
    carry_idx = -1
    section_idx = 0

    while i < total_notes:
        carry_idx = _canon_carry(int(i), int(carry_idx))

        min_notes_to_fill = int(non_fever_base - 1 if is_first else non_fever_base)
        if min_notes_to_fill < 0:
            min_notes_to_fill = 0
        if int(i) + int(min_notes_to_fill) >= int(total_notes):
            break

        forced_val = int(counts[section_idx]) if section_idx < len(counts) else 0
        if forced_val < 0:
            forced_val = 0
        if forced_val > non_fever_base:
            forced_val = int(non_fever_base)

        notes_to_fill = int(ceil(float(raw_fill) + 0.5 * float(forced_val)))
        if is_first:
            notes_to_fill -= 1
        if notes_to_fill < 0:
            notes_to_fill = 0

        end_normal = int(i + notes_to_fill)
        if end_normal >= total_notes:
            break

        forced_start = int(i if is_first else (i + 1))
        if forced_start < 0:
            forced_start = 0

        actual_notes = max(0, int(end_normal - i))
        forced_applied = min(int(forced_val), int(actual_notes))

        penalty = 0
        if forced_applied > 0 and forced_start < total_notes:
            end_excl = min(int(total_notes), int(forced_start + forced_applied))
            penalty = int(c_prefix[end_excl] - c_prefix[forced_start])

            if use_timing_carry:
                assert great_candidates is not None
                forced_end = forced_start + forced_applied - 1
                if forced_end >= forced_start and forced_end < end_normal and forced_end < total_notes:
                    cand_t = float(great_candidates[forced_end])
                    if carry_idx < 0 or cand_t > float(great_candidates[carry_idx]):
                        carry_idx = int(forced_end)

        fever_end_idx = int(fever_end_song[end_normal])
        if use_timing_carry and carry_idx >= 0:
            assert great_candidates is not None and fever_end_gc is not None
            if float(great_candidates[carry_idx]) > float(timestamps[end_normal]):
                fever_end_idx = int(fever_end_gc[carry_idx])
        if fever_end_idx <= end_normal:
            fever_end_idx = min(total_notes, end_normal + 1)

        total_bonus += int(w_prefix[fever_end_idx] - w_prefix[end_normal]) - int(penalty)

        carry_idx = _canon_carry(int(fever_end_idx), int(carry_idx))
        i = int(fever_end_idx)
        is_first = False
        section_idx += 1

    return int(total_bonus)


def count_force_greats_baseline_windows_from_prepared(prepared: FGExactDPPreparedInputs) -> int:
    """
    Count fever activations for the zero-force FG baseline at a fixed stat point.

    This is an exact upper bound on the number of activations any forced-Great
    path can realize at the same stat point: forced Greats only increase the
    fill requirement, and timing-aware carry only affects the fever end when
    the carried Great timestamp survives past the activation timestamp.
    """
    if not isinstance(prepared, FGExactDPPreparedInputs):
        return 0
    timeline = prepared.timeline_analysis
    if timeline is None:
        timeline = TimelineAnalysisInputs(
            mode="fg",
            timestamps=prepared.timestamps,
            great_candidates=prepared.great_candidates,
            total_notes=int(prepared.total_notes),
            long_notes=0,
            last_note_time=float(prepared.last_note_time),
            raw_fill=float(prepared.raw_fill),
            non_fever_base=int(prepared.non_fever_base),
            fever_duration=float(prepared.fever_duration),
            ft_idx=int(prepared.ft_idx),
            base_value=0.0,
            combo_mul=0.0,
            fever_mul=0.0,
            primary_val=0,
            secondary_val=0,
        )
    return count_timeline_analysis_windows(timeline)


def solve_force_greats_exact_dp(
    *,
    stats: dict,
    calc_song: dict,
    ref_arrays: dict,
    mode: Literal["count_only", "timing_aware"] = "timing_aware",
    prune: bool = False,
) -> FGExactDPSolution:
    """
    Exact DP for a fixed (FT,FF,...) stat point.

    Returns:
      - best_delta: max (sum fever bonuses - forced great penalties) over all configs
      - section_counts: chosen forced counts per non-fever section along the optimal path
      - profile: state/transition counters
    """
    profile = FGExactDPProfile()

    prepared = prepare_force_greats_exact_dp_inputs(stats=stats, calc_song=calc_song, ref_arrays=ref_arrays)
    if prepared is None:
        return FGExactDPSolution(best_delta=0, section_counts=[], profile=profile)
    timestamps = prepared.timestamps
    great_candidates = prepared.great_candidates
    total_notes = int(prepared.total_notes)
    raw_fill = float(prepared.raw_fill)
    non_fever_base = int(prepared.non_fever_base)
    fever_duration = float(prepared.fever_duration)

    # If we don't have great-candidate timestamps, timing-aware mode collapses to count-only.
    use_timing_carry = bool(mode == "timing_aware" and great_candidates is not None)

    # Precompute reward ingredients.
    w_prefix = prepared.w_prefix
    # Upper bound: total remaining (fever - normal) bonus if every remaining note were fever.
    # With fever_mul>=1, per-note deltas are non-negative in practice, so this is a safe bound.
    suffix_bonus = w_prefix[-1] - w_prefix
    c_prefix = prepared.c_prefix

    # Fever end lookup tables (match Taichi FG tables: end idx depends on start-time source).
    end_times_song = timestamps.astype(np.float64) + float(fever_duration)
    fever_end_song = np.searchsorted(timestamps, end_times_song, side="left").astype(np.int32, copy=False)
    if use_timing_carry:
        assert great_candidates is not None
        end_times_gc = great_candidates.astype(np.float64) + float(fever_duration)
        fever_end_gc = np.searchsorted(timestamps, end_times_gc, side="left").astype(np.int32, copy=False)
    else:
        fever_end_gc = None

    # Action set in FP-target space (p -> candidate k values).
    p_to_ks = _build_fp_actions(raw_fill, non_fever_base)
    p_max = int(len(p_to_ks) - 1)

    NO_CARRY = -1

    # Policy for path reconstruction (state -> (p, k)).
    policy: dict[tuple[int, int, int], tuple[int, int]] = {}

    def _canon_carry(i: int, carry_idx: int) -> int:
        if (not use_timing_carry) or int(carry_idx) < 0:
            return NO_CARRY
        if int(i) >= int(total_notes):
            return NO_CARRY
        assert great_candidates is not None
        cidx = int(carry_idx)
        return NO_CARRY if float(great_candidates[cidx]) <= float(timestamps[int(i)]) else cidx

    @lru_cache(maxsize=None)
    def _solve(i: int, is_first: int, carry_idx_canon: int) -> int:
        profile.states += 1
        profile.max_cached_states = max(profile.max_cached_states, profile.states)

        i = int(i)
        if i >= total_notes:
            return 0

        first = bool(int(is_first) != 0)
        cidx = int(carry_idx_canon)

        # If even p=0 can't reach an activation note, forcing greats is pure loss -> choose 0.
        min_notes_to_fill = int(non_fever_base - 1 if first else non_fever_base)
        if min_notes_to_fill < 0:
            min_notes_to_fill = 0
        if i + min_notes_to_fill >= total_notes:
            policy[(i, int(first), cidx)] = (0, 0)
            return 0

        best_val = 0
        best_p = 0
        best_k = 0

        forced_start_base = i if first else (i + 1)
        if forced_start_base < 0:
            forced_start_base = 0

        # Iterate p in increasing order so we can break once end_normal runs past song end.
        for p in range(p_max + 1):
            notes_to_fill = int(non_fever_base + p)
            if first:
                notes_to_fill -= 1
            if notes_to_fill < 0:
                notes_to_fill = 0

            end_normal = i + notes_to_fill
            if end_normal >= total_notes:
                break

            if prune and best_val > 0:
                # Monotone safe stopping rule: for later activations, the remaining suffix_bonus decreases
                # while the minimum forced-great penalty needed to reach that activation increases.
                ks = p_to_ks[p] if p < len(p_to_ks) else (0,)
                k_min = int(ks[0]) if ks else 0
                if k_min < 0:
                    k_min = 0
                if k_min > non_fever_base:
                    k_min = int(non_fever_base)

                actual_notes = int(end_normal - i)
                if actual_notes < 0:
                    actual_notes = 0

                forced_applied_min = int(k_min)
                if forced_applied_min > actual_notes:
                    forced_applied_min = actual_notes

                penalty_min = 0
                if forced_applied_min > 0 and forced_start_base < total_notes:
                    end_excl_min = forced_start_base + forced_applied_min
                    if end_excl_min > total_notes:
                        end_excl_min = total_notes
                    penalty_min = int(c_prefix[end_excl_min] - c_prefix[forced_start_base])

                ub = int(suffix_bonus[end_normal]) - int(penalty_min)
                if ub <= best_val:
                    break

            # Fever bonus for this window depends on fever_end (carry may extend it).
            # Penalty/carry update depends on which k we choose inside this plateau.
            ks = p_to_ks[p] if p < len(p_to_ks) else (0,)
            for k in ks:
                profile.transitions += 1

                forced_val = int(k)
                if forced_val < 0:
                    forced_val = 0
                if forced_val > non_fever_base:
                    forced_val = int(non_fever_base)

                actual_notes = int(end_normal - i)
                if actual_notes < 0:
                    actual_notes = 0

                forced_applied = forced_val
                if forced_applied > actual_notes:
                    forced_applied = actual_notes

                forced_start = forced_start_base

                # Forced Great penalty uses the clamped `forced_applied` count and the repo's placement rule.
                penalty = 0
                if forced_applied > 0 and forced_start < total_notes:
                    end_excl = forced_start + forced_applied
                    if end_excl > total_notes:
                        end_excl = total_notes
                    penalty = int(c_prefix[end_excl] - c_prefix[forced_start])

                # Carry update: prefix-max of great-candidate timestamps for the last forced note.
                next_cidx = cidx
                if use_timing_carry and forced_applied > 0:
                    assert great_candidates is not None
                    forced_end = forced_start + forced_applied - 1
                    if forced_end >= forced_start and forced_end < end_normal and forced_end < total_notes:
                        cand_t = float(great_candidates[forced_end])
                        if next_cidx < 0:
                            next_cidx = int(forced_end)
                        else:
                            if cand_t > float(great_candidates[next_cidx]):
                                next_cidx = int(forced_end)

                # Fever end index depends on whether carry is active beyond the activation note.
                fever_end_idx = int(fever_end_song[end_normal])
                if use_timing_carry and next_cidx >= 0:
                    assert great_candidates is not None and fever_end_gc is not None
                    if float(great_candidates[next_cidx]) > float(timestamps[end_normal]):
                        fever_end_idx = int(fever_end_gc[next_cidx])
                if fever_end_idx <= end_normal:
                    fever_end_idx = min(total_notes, end_normal + 1)

                # Canonicalize carry for the next state (depends on next state's start idx).
                carry_next = _canon_carry(int(fever_end_idx), int(next_cidx))

                fever_bonus = int(w_prefix[fever_end_idx] - w_prefix[end_normal])
                future = _solve(int(fever_end_idx), 0, int(carry_next))
                total = int(fever_bonus - penalty + future)
                if total > best_val:
                    best_val = total
                    best_p = int(p)
                    best_k = int(forced_val)

        policy[(i, int(first), cidx)] = (best_p, best_k)
        return int(best_val)

    best = int(_solve(0, 1, NO_CARRY))

    # Reconstruct the chosen forced counts along the optimal path (until we can't activate fever).
    counts: list[int] = []
    i = 0
    is_first = 1
    carry_idx = NO_CARRY
    while i < total_notes:
        carry_idx = _canon_carry(int(i), int(carry_idx))
        key = (int(i), int(bool(is_first)), int(carry_idx))
        act = policy.get(key)
        if act is None:
            break
        p, k = act
        counts.append(int(k))

        notes_to_fill = int(non_fever_base + int(p))
        if is_first:
            notes_to_fill -= 1
        if notes_to_fill < 0:
            notes_to_fill = 0
        end_normal = int(i + notes_to_fill)
        if end_normal >= total_notes:
            break

        # Apply the same transition logic to advance.
        forced_val = int(k)
        if forced_val > non_fever_base:
            forced_val = int(non_fever_base)
        if forced_val < 0:
            forced_val = 0
        actual_notes = max(0, int(end_normal - i))
        forced_applied = min(int(forced_val), int(actual_notes))
        forced_start = int(i if is_first else (i + 1))
        if forced_start < 0:
            forced_start = 0

        if use_timing_carry and forced_applied > 0 and great_candidates is not None:
            forced_end = forced_start + forced_applied - 1
            if forced_end >= forced_start and forced_end < end_normal and forced_end < total_notes:
                cand_t = float(great_candidates[forced_end])
                if carry_idx < 0:
                    carry_idx = int(forced_end)
                else:
                    if cand_t > float(great_candidates[carry_idx]):
                        carry_idx = int(forced_end)

        fever_end_idx = int(fever_end_song[end_normal])
        if use_timing_carry and carry_idx >= 0 and great_candidates is not None and fever_end_gc is not None:
            if float(great_candidates[carry_idx]) > float(timestamps[end_normal]):
                fever_end_idx = int(fever_end_gc[carry_idx])
        if fever_end_idx <= end_normal:
            fever_end_idx = min(total_notes, end_normal + 1)

        carry_idx = _canon_carry(int(fever_end_idx), int(carry_idx))

        i = int(fever_end_idx)
        is_first = 0

    return FGExactDPSolution(best_delta=int(best), section_counts=counts, profile=profile)
