"""
Timing-envelope preparation and reduced exact timeline analysis.

This module owns the deterministic Perfect-window model used by both:

- base GPU timeline ceiling precompute, and
- FG exact-DP frontier analysis.

The contract is intentionally narrower than full timing exactness: for fixed
stats, we compute exact properties of the retained timeline frontier. FG uses
the same counter to derive admissible score bounds for pruning, instead of a
hard activation-window cap.
"""

from __future__ import annotations

import threading
import logging

import numpy as np

from ..core.time_quantize import quantize_to_int_ms



logger = logging.getLogger(__name__)


def floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    """Quantize seconds to integer milliseconds using the repo parity rule."""

    return quantize_to_int_ms(timestamps_sec)


def build_per_note_perfect_window_ms(
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


def build_per_note_great_window_ms(
    note_types: np.ndarray,
    *,
    perfect_low_ms: np.ndarray,
    perfect_upper_ms: int,
    great_lower_ms: int,
    great_extra_upper_ms: int,
    great_mode: str,
    held_tail_type: int,
    held_tail_time_multiplier: int,
) -> tuple[np.ndarray, np.ndarray]:
    note_types = np.asarray(note_types, dtype=np.int16)
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)

    great_upper_abs_ms = ((int(perfect_upper_ms) + int(great_extra_upper_ms)) * mult).astype(np.int32)
    perfect_low_abs_ms = np.asarray(perfect_low_ms, dtype=np.int32)
    mode = str(great_mode or "late").strip().lower()

    if mode == "late":
        great_low_abs_ms = (int(perfect_upper_ms) * mult + 1).astype(np.int32)
        great_high_abs_ms = great_upper_abs_ms
    elif mode == "early":
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_high_abs_ms = perfect_low_abs_ms - 1
    elif mode == "full":
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_high_abs_ms = great_upper_abs_ms
    else:
        raise ValueError(f"Invalid great_mode: {great_mode}")

    return great_low_abs_ms, great_high_abs_ms


def prepare_grouped_timing_windows(
    timestamps_sec: np.ndarray,
    *,
    note_low_ms: np.ndarray,
    note_high_ms: np.ndarray,
    quantize_ms: bool,
) -> dict:
    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return {
            "n": 0,
            "ts_ms": np.zeros((0,), dtype=np.int32),
            "group_starts": np.zeros((0,), dtype=np.int32),
            "group_ends": np.zeros((0,), dtype=np.int32),
            "group_base_t": np.zeros((0,), dtype=np.int32),
            "group_low": np.zeros((0,), dtype=np.int32),
            "group_high": np.zeros((0,), dtype=np.int32),
        }

    if quantize_ms:
        ts_ms = floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * np.float32(1000.0)).astype(np.int32)

    note_low_ms = np.asarray(note_low_ms, dtype=np.int32)
    note_high_ms = np.asarray(note_high_ms, dtype=np.int32)

    if n == 1:
        group_starts = np.asarray([0], dtype=np.int32)
        group_ends = np.asarray([1], dtype=np.int32)
    else:
        boundaries = np.nonzero(ts_ms[1:] != ts_ms[:-1])[0].astype(np.int32) + 1
        group_count = int(boundaries.shape[0]) + 1
        group_starts = np.empty(group_count, dtype=np.int32)
        group_ends = np.empty(group_count, dtype=np.int32)
        group_starts[0] = 0
        if group_count > 1:
            group_starts[1:group_count] = boundaries
            group_ends[: group_count - 1] = boundaries
        group_ends[group_count - 1] = int(n)

    group_base_t = ts_ms[group_starts].astype(np.int32, copy=False)
    raw_low = np.maximum.reduceat(note_low_ms, group_starts)
    raw_high = np.minimum.reduceat(note_high_ms, group_starts)
    group_low = np.minimum(raw_low, raw_high).astype(np.int32, copy=False)
    group_high = np.maximum(raw_low, raw_high).astype(np.int32, copy=False)

    return {
        "n": int(n),
        "ts_ms": ts_ms.astype(np.int32, copy=False),
        "group_starts": group_starts,
        "group_ends": group_ends,
        "group_base_t": group_base_t,
        "group_low": group_low,
        "group_high": group_high,
    }


def prepare_perfect_timing_envelope(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
    quantize_ms: bool,
) -> dict:
    """Prepare chord-group Perfect timing windows for envelope kernels."""

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return prepare_grouped_timing_windows(
            ts_sec,
            note_low_ms=np.zeros((0,), dtype=np.int32),
            note_high_ms=np.zeros((0,), dtype=np.int32),
            quantize_ms=quantize_ms,
        )

    if note_types is None or len(note_types) != n:
        nt = np.ones(n, dtype=np.int16)
    else:
        nt = np.asarray(note_types, dtype=np.int16)

    perfect_low_ms, perfect_high_ms = build_per_note_perfect_window_ms(
        nt,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )
    return prepare_grouped_timing_windows(
        ts_sec,
        note_low_ms=np.asarray(perfect_low_ms, dtype=np.int32),
        note_high_ms=np.asarray(perfect_high_ms, dtype=np.int32),
        quantize_ms=quantize_ms,
    )


def compute_fever_timeline_signature(
    event_ms: np.ndarray,
    *,
    non_fever_base: int,
    real_fever_time_ms: int,
) -> tuple[tuple[int, int, int, bytes], np.ndarray, int, int]:
    """
    Build a compact score-relevant signature for fixed stats on one event-time stream.
    """

    ev = np.asarray(event_ms, dtype=np.int32)
    total_notes = int(ev.shape[0])
    head_limit = min(total_notes, 100)
    fever_mask_head = np.zeros(head_limit, dtype=np.bool_)

    current_note_idx = 0
    fever_section = 0
    count_body_fever = 0
    while current_note_idx < total_notes:
        fever_section += 1
        notes_to_fill = int(non_fever_base) - 1 if fever_section == 1 else int(non_fever_base)
        end_normal_idx = current_note_idx + notes_to_fill
        if end_normal_idx > total_notes:
            end_normal_idx = total_notes
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_start = int(current_note_idx)
            end_ms = int(ev[fever_start]) + int(real_fever_time_ms)
            fever_end_idx = int(np.searchsorted(ev, end_ms, side="left"))

            if fever_start < head_limit:
                head_s = max(0, fever_start)
                head_e = min(head_limit, fever_end_idx)
                if head_e > head_s:
                    fever_mask_head[head_s:head_e] = True

            if fever_end_idx > 100:
                body_start = max(100, fever_start)
                if fever_end_idx > body_start:
                    count_body_fever += int(fever_end_idx - body_start)

            current_note_idx = fever_end_idx
        else:
            break

    count_body_normal = max(0, int(total_notes - head_limit - int(count_body_fever)))
    head_u8 = np.asarray(fever_mask_head, dtype=np.uint8)
    packed_head = np.packbits(head_u8, bitorder="little")
    signature = (
        int(head_u8.shape[0]),
        int(count_body_fever),
        int(count_body_normal),
        bytes(packed_head.tobytes()),
    )
    return signature, fever_mask_head, int(count_body_fever), int(count_body_normal)


def generate_perfect_timing_events_ms(prepared: dict, *, seed: int) -> np.ndarray:
    """
    Generate monotone Perfect event times in integer ms for a prepared envelope.

    This is used by tests/benchmarks as a sampled reference against the deterministic
    ceiling envelope. Production scoring uses the deterministic envelope directly.
    """

    n = int(prepared.get("n", 0) or 0)
    if n <= 0:
        return np.zeros((0,), dtype=np.int32)

    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base_t = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_low = np.asarray(prepared["group_low"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)
    group_count = int(group_starts.shape[0])

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    tls = getattr(generate_perfect_timing_events_ms, "_tls", None)
    if tls is None:
        tls = threading.local()
        setattr(generate_perfect_timing_events_ms, "_tls", tls)

    event_ms = getattr(tls, "event_ms", None)
    if event_ms is None or int(getattr(event_ms, "shape", (0,))[0]) < int(n):
        event_ms = np.empty(int(n), dtype=np.int32)
        setattr(tls, "event_ms", event_ms)
    event_ms = event_ms[:n]

    prev_event_ms: int | None = None
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(group_base_t[g])
        g_low = int(group_low[g])
        g_high = int(group_high[g])

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

        event = base_t + off
        event_ms[s:e] = event
        prev_event_ms = event

    return event_ms


def build_great_candidate_envelope_sec(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    great_lower_ms: int = -75,
    great_extra_upper_ms: int = 150,
    great_mode: str = "late",
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> np.ndarray:
    """
    Build deterministic per-note Great-candidate envelope timestamps.

    FG only needs the carry-extending side of Great timing. We therefore choose
    the latest valid candidate per chord group, which is exact for the retained
    late-carry envelope and avoids legacy seeded sampling.
    """

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return ts_sec.astype(np.float32, copy=False)
    if int(great_extra_upper_ms) < 0:
        raise ValueError("great_extra_upper_ms must be >= 0")

    if note_types is None or len(note_types) != n:
        nt = np.ones(n, dtype=np.int16)
    else:
        nt = np.asarray(note_types, dtype=np.int16)

    perfect_low_ms, perfect_high_ms = build_per_note_perfect_window_ms(
        nt,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )
    great_low_ms, great_high_ms = build_per_note_great_window_ms(
        nt,
        perfect_low_ms=perfect_low_ms,
        perfect_upper_ms=int(perfect_upper_ms),
        great_lower_ms=int(great_lower_ms),
        great_extra_upper_ms=int(great_extra_upper_ms),
        great_mode=str(great_mode or "late").strip().lower(),
        held_tail_type=int(held_tail_type),
        held_tail_time_multiplier=int(held_tail_time_multiplier),
    )
    prepared = prepare_grouped_timing_windows(
        ts_sec,
        note_low_ms=np.asarray(great_low_ms, dtype=np.int32),
        note_high_ms=np.asarray(great_high_ms, dtype=np.int32),
        quantize_ms=bool(quantize_ms),
    )

    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base_t = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)

    event_ms = np.empty(int(n), dtype=np.int32)
    for g in range(int(group_starts.shape[0])):
        s = int(group_starts[g])
        e = int(group_ends[g])
        event_ms[s:e] = int(group_base_t[g]) + int(group_high[g])

    out = event_ms.astype(np.float32)
    out *= np.float32(0.001)
    return out


def apply_timing_envelope(calc_song: dict, *, attach_fg: bool = True) -> dict | None:
    """
    Attach deterministic timing-envelope streams to a calc_song.

    This replaces production HumanHitSim usage. Base scoring keeps chart
    timestamps; FG receives chart timestamps plus a deterministic late Great
    candidate envelope for carry-aware exact DP.
    """

    if not isinstance(calc_song, dict):
        return None
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        return None

    chart_ts = np.asarray(timestamps, dtype=np.float32)
    song_data["chart_timestamps"] = chart_ts
    try:
        from ..core.array_signature import array_sig16

        song_data["_chart_timestamps_sig"] = array_sig16(chart_ts)
    except Exception as e:
        logger.debug(f"timing_envelope:apply_timing_envelope: {e}")
        song_data.pop("_chart_timestamps_sig", None)
    if not attach_fg:
        calc_song["song_data"] = song_data
        return {"mode": "base", "notes": int(chart_ts.shape[0])}

    note_types = song_data.get("note_types")
    if note_types is None or len(note_types) != int(chart_ts.shape[0]):
        note_types = np.ones(int(chart_ts.shape[0]), dtype=np.int16)
    else:
        note_types = np.asarray(note_types, dtype=np.int16)
    try:
        from ..core.array_signature import array_sig16

        song_data["_note_types_sig"] = array_sig16(note_types)
    except Exception as e:
        logger.debug(f"timing_envelope:apply_timing_envelope: {e}")
        song_data.pop("_note_types_sig", None)

    song_data["fg_timestamps"] = chart_ts
    song_data["fg_great_candidate_timestamps"] = build_great_candidate_envelope_sec(
        chart_ts,
        note_types,
        great_mode="late",
    )

    meta = dict(calc_song.get("metadata", {}) or {})
    meta["TimingEnvelopeApplied"] = True
    meta["TimingEnvelopeMode"] = "perfect_window"
    meta["TimingEnvelopeFGCarry"] = "late_upper"
    for key in (
        "HumanHitSimApplied",
        "HumanHitSimPlanned",
        "HumanHitSimSeed",
        "HumanHitSimApplyTo",
        "HumanHitSimDistribution",
        "HumanHitSimGreatMode",
        "HumanHitSimSeedIsRandom",
        "HumanHitSimDebug",
    ):
        meta.pop(key, None)
    calc_song["metadata"] = meta
    calc_song["song_data"] = song_data
    return {"mode": "fg", "notes": int(chart_ts.shape[0]), "great_mode": "late_upper"}
