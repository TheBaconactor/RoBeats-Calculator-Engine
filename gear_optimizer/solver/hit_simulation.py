"""
Synthetic human hit-time simulation for server-parity fever modeling.

The real (server-authoritative) fever timeline depends on the *times* notes are
validated at (integer milliseconds), not just the chart timestamps. For the
optimizer, we can optionally generate a deterministic, human-like hit-time
sequence by sampling offsets within the judgement windows.

This module currently targets Perfect-only simulation (i.e., all notes hit as
Perfect), with support for held tail notes having a wider window (x2), matching
the game code (GearStats.note_hit_mode_get_time_multiplier).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HumanHitSimConfig:
    enabled: bool
    apply_to: str  # "FG" | "ALL"
    seed: int  # 0 => derive per-song
    distribution: str  # "uniform"
    perfect_lower_ms: int
    perfect_upper_ms: int
    held_tail_type: int
    held_tail_time_multiplier: int
    quantize_ms: bool


def stable_seed_from_text(text: str) -> int:
    """
    Convert a string into a deterministic 32-bit seed.

    Uses BLAKE2b to avoid Python's randomized hash() salt.
    """
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, byteorder="little", signed=False)


def _floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    ts = np.asarray(timestamps_sec, dtype=np.float64)
    # Server/client event time uses floor(audio_time_ms). Song dumps store timestamps
    # with ~3 decimals; adding a tiny epsilon avoids float -> int off-by-1 near integers.
    return np.floor(ts * 1000.0 + 1e-6).astype(np.int32)


def _build_per_note_perfect_window_ms(
    note_types: np.ndarray,
    *,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
) -> tuple[np.ndarray, np.ndarray]:
    note_types = np.asarray(note_types, dtype=np.int16)
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)
    lower = (int(perfect_lower_ms) * mult).astype(np.int16)
    upper = (int(perfect_upper_ms) * mult).astype(np.int16)
    return lower, upper


def simulate_perfect_hit_timestamps(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    seed: int,
    distribution: str = "uniform",
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> tuple[np.ndarray, dict]:
    """
    Generate a deterministic, human-like hit-time sequence for Perfect hits.

    - Offsets are sampled within the Perfect window (ms).
    - Held tail notes use a wider time window (multiplier) when note_types is provided.
    - Events with identical chart timestamps (chords) share the same sampled offset.
    - Group offsets are sampled with a monotonic constraint (non-decreasing event times),
      which approximates sequential processing and keeps the output suitable for
      searchsorted-based fever logic.

    Returns:
        (hit_timestamps_sec, debug_info)
    """
    if distribution != "uniform":
        raise ValueError(f"Unsupported HumanHitSim distribution: {distribution!r}")

    ts_sec = np.asarray(timestamps_sec, dtype=np.float64)
    n = int(ts_sec.shape[0])
    if n == 0:
        return ts_sec.astype(np.float64), {"notes": 0, "groups": 0, "forced_monotonic": 0}

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * 1000.0).astype(np.int32)

    if note_types is None or len(note_types) != n:
        note_types = np.ones(n, dtype=np.int16)
    else:
        note_types = np.asarray(note_types, dtype=np.int16)

    lower_ms, upper_ms = _build_per_note_perfect_window_ms(
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    # Build chord groups by identical timestamp_ms runs (song data is already sorted).
    # For each group, use the intersection of windows so one offset works for all notes.
    group_starts = np.empty(n, dtype=np.int32)
    group_ends = np.empty(n, dtype=np.int32)
    group_count = 0
    i = 0
    while i < n:
        j = i + 1
        t = ts_ms[i]
        while j < n and ts_ms[j] == t:
            j += 1
        group_starts[group_count] = i
        group_ends[group_count] = j
        group_count += 1
        i = j

    group_starts = group_starts[:group_count]
    group_ends = group_ends[:group_count]

    hit_ms = np.empty(n, dtype=np.int32)
    prev_event_ms: int | None = None
    forced_monotonic = 0

    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(ts_ms[s])

        # Intersection window across the group.
        g_low = int(np.max(lower_ms[s:e]))
        g_high = int(np.min(upper_ms[s:e]))

        if g_low > g_high:
            # Should never happen (tail windows are wider), but guard anyway.
            g_low, g_high = g_high, g_low

        # Monotonic constraint: ensure event times do not go backwards.
        if prev_event_ms is None:
            eff_low = g_low
        else:
            required_off = int(prev_event_ms) - base_t
            eff_low = max(g_low, required_off)

        if eff_low <= g_high:
            off = int(rng.integers(eff_low, g_high + 1, endpoint=False))
        else:
            # Constraint is infeasible within the window; fall back to the latest
            # legal time, then clamp to monotonic (rare in practice).
            off = g_high
            if prev_event_ms is not None and base_t + off < int(prev_event_ms):
                off = int(prev_event_ms) - base_t
                forced_monotonic += 1

        event_ms = base_t + off
        hit_ms[s:e] = event_ms
        prev_event_ms = event_ms

    hit_sec = hit_ms.astype(np.float64) / 1000.0
    debug = {"notes": n, "groups": int(group_count), "forced_monotonic": int(forced_monotonic)}
    return hit_sec, debug


def simulate_perfect_hit_timestamps_with_great_candidates(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    seed: int,
    distribution: str = "uniform",
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    great_upper_ms: int = 150,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Generate:
    - Perfect event times (monotonic, chord-grouped)
    - Great-candidate times (chart_time + sampled late-only Great offset, chord-grouped)

    "Great-candidate" is intentionally *not* monotonic by itself; monotonicity is
    handled in FG timeline simulation via a carry (prefix-max) rule:
      effective_time[i] = max(perfect_event_time[i], max(great_candidate_time[j] for forced j<=i))

    Great offsets are sampled from the late-only band:
      [perfect_upper+1, great_upper]
    with held tails using x2 window multiplier.
    """
    if distribution != "uniform":
        raise ValueError(f"Unsupported HumanHitSim distribution: {distribution!r}")
    if int(great_upper_ms) < int(perfect_upper_ms):
        raise ValueError("great_upper_ms must be >= perfect_upper_ms")

    ts_sec = np.asarray(timestamps_sec, dtype=np.float64)
    n = int(ts_sec.shape[0])
    if n == 0:
        empty = ts_sec.astype(np.float64)
        return empty, empty, {"notes": 0, "groups": 0, "forced_monotonic": 0}

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * 1000.0).astype(np.int32)

    if note_types is None or len(note_types) != n:
        note_types = np.ones(n, dtype=np.int16)
    else:
        note_types = np.asarray(note_types, dtype=np.int16)

    # Perfect windows per note (ms, with tail multiplier).
    perfect_low_ms, perfect_high_ms = _build_per_note_perfect_window_ms(
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )

    # Great late-only band per note (ms, with tail multiplier).
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)
    great_low_ms = (int(perfect_upper_ms) * mult + 1).astype(np.int32)
    great_high_ms = (int(great_upper_ms) * mult).astype(np.int32)

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    # Chord grouping by identical timestamp_ms runs.
    group_starts = np.empty(n, dtype=np.int32)
    group_ends = np.empty(n, dtype=np.int32)
    group_count = 0
    i = 0
    while i < n:
        j = i + 1
        t = ts_ms[i]
        while j < n and ts_ms[j] == t:
            j += 1
        group_starts[group_count] = i
        group_ends[group_count] = j
        group_count += 1
        i = j

    group_starts = group_starts[:group_count]
    group_ends = group_ends[:group_count]

    # Perfect event times (monotonic per chord group).
    perfect_event_ms = np.empty(n, dtype=np.int32)
    prev_event_ms: int | None = None
    forced_monotonic = 0

    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(ts_ms[s])

        g_low = int(np.max(perfect_low_ms[s:e]))
        g_high = int(np.min(perfect_high_ms[s:e]))
        if g_low > g_high:
            g_low, g_high = g_high, g_low

        if prev_event_ms is None:
            eff_low = g_low
        else:
            required_off = int(prev_event_ms) - base_t
            eff_low = max(g_low, required_off)

        if eff_low <= g_high:
            off = int(rng.integers(eff_low, g_high + 1, endpoint=False))
        else:
            off = g_high
            if prev_event_ms is not None and base_t + off < int(prev_event_ms):
                off = int(prev_event_ms) - base_t
                forced_monotonic += 1

        event_ms = base_t + off
        perfect_event_ms[s:e] = event_ms
        prev_event_ms = event_ms

    # Great-candidate times (late-only band, chord-grouped, no monotonic clamp).
    great_candidate_ms = np.empty(n, dtype=np.int32)
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(ts_ms[s])

        g_low = int(np.max(great_low_ms[s:e]))
        g_high = int(np.min(great_high_ms[s:e]))
        if g_low > g_high:
            # No late-only Great band available (shouldn't happen for stat=0),
            # fall back to "latest perfect" to avoid invalid output.
            g_low = int(np.min(perfect_high_ms[s:e]))
            g_high = g_low

        off = int(rng.integers(g_low, g_high + 1, endpoint=False))
        great_candidate_ms[s:e] = base_t + off

    perfect_sec = perfect_event_ms.astype(np.float64) / 1000.0
    great_sec = great_candidate_ms.astype(np.float64) / 1000.0
    debug = {"notes": n, "groups": int(group_count), "forced_monotonic": int(forced_monotonic)}
    return perfect_sec, great_sec, debug
