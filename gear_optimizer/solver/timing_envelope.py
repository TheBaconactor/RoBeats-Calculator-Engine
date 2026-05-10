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

from dataclasses import dataclass, field
from math import ceil
from typing import Literal
import threading
import logging

import numpy as np

from ..core.constants import (
    FEVER_FILL_BASE_RATE,
    FEVER_TIME_OFFSET,
    FEVER_TIME_SCALE,
    TOTAL_ROWS,
)
from ..core.time_quantize import quantize_to_int_ms
from ..core.utils import safe_float, safe_int
from .scoring_core import lookup_reference_py



logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class TimelineAnalysisInputs:
    """Fixed-stat timeline inputs shared by base analysis and FG exact DP."""

    mode: Literal["base", "fg"]
    timestamps: np.ndarray
    great_candidates: np.ndarray | None
    total_notes: int
    long_notes: int
    last_note_time: float
    raw_fill: float
    non_fever_base: int
    fever_duration: float
    ft_idx: int
    base_value: float
    combo_mul: float
    fever_mul: float
    primary_val: int
    secondary_val: int


@dataclass
class TimelineWindowCounter:
    """Reusable all-normal window counter for resolved timeline stat cells."""

    timestamps: np.ndarray
    long_notes: int
    last_note_time: float
    ref_ft: np.ndarray
    ref_ff: np.ndarray
    _fever_end_cache: dict[int, np.ndarray] = field(default_factory=dict)
    _window_count_cache: dict[tuple[int, int], int] = field(default_factory=dict)

    def total_notes(self) -> int:
        return int(self.timestamps.shape[0])

    def fill_count(self, ff_idx: int) -> int:
        ff_i = max(0, min(TOTAL_ROWS, safe_int(ff_idx, 0)))
        total_notes = int(self.timestamps.shape[0])
        non_fever_cas = (total_notes - int(self.long_notes)) * float(FEVER_FILL_BASE_RATE)
        if non_fever_cas < 0.0:
            non_fever_cas = 0.0
        raw_fill = float(non_fever_cas) * float(self.ref_ff[ff_i])
        return max(1, int(ceil(raw_fill)))

    def count(self, ft_idx: int, ff_idx: int) -> int:
        ft_i = max(0, min(TOTAL_ROWS, safe_int(ft_idx, 0)))
        ff_i = max(0, min(TOTAL_ROWS, safe_int(ff_idx, 0)))
        cache_key = (int(ft_i), int(ff_i))
        cached = self._window_count_cache.get(cache_key)
        if cached is not None:
            return int(cached)

        total_notes = int(self.timestamps.shape[0])
        if total_notes <= 0:
            self._window_count_cache[cache_key] = 0
            return 0

        non_fever_base = int(self.fill_count(ff_i))

        fever_end_song = self._fever_end_cache.get(ft_i)
        if fever_end_song is None:
            fever_time_cas = float(self.last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
            fever_duration = float(fever_time_cas) * float(self.ref_ft[ft_i])
            end_times_song = self.timestamps.astype(np.float64, copy=False) + float(fever_duration)
            fever_end_song = np.searchsorted(self.timestamps, end_times_song, side="left").astype(
                np.int32, copy=False
            )
            self._fever_end_cache[ft_i] = fever_end_song

        count = _count_timeline_windows_from_end_table(
            total_notes=total_notes,
            non_fever_base=int(non_fever_base),
            fever_end_song=fever_end_song,
        )
        self._window_count_cache[cache_key] = int(count)
        return int(count)


def _count_timeline_windows_from_end_table(
    *,
    total_notes: int,
    non_fever_base: int,
    fever_end_song: np.ndarray,
) -> int:
    windows = 0
    i = 0
    is_first = True
    while i < int(total_notes):
        notes_to_fill = int(non_fever_base - 1 if is_first else non_fever_base)
        if notes_to_fill < 0:
            notes_to_fill = 0
        end_normal = int(i + notes_to_fill)
        if end_normal >= int(total_notes):
            break

        fever_end_idx = int(fever_end_song[end_normal])
        if fever_end_idx <= end_normal:
            fever_end_idx = min(int(total_notes), end_normal + 1)

        windows += 1
        i = int(fever_end_idx)
        is_first = False

    return int(windows)


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
    late-carry envelope and avoids historical seeded sampling.
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


def _extract_timestamps_for_mode(calc_song: dict, mode: Literal["base", "fg"]) -> tuple[np.ndarray, np.ndarray | None]:
    song_data = calc_song.get("song_data", {}) or {}
    if mode == "fg":
        ts = song_data.get("fg_timestamps", song_data.get("chart_timestamps", song_data.get("timestamps")))
        gc = song_data.get("fg_great_candidate_timestamps")
    else:
        ts = song_data.get("chart_timestamps", song_data.get("timestamps"))
        gc = None
    if ts is None:
        return np.empty((0,), dtype=np.float32), None
    ts_f32 = np.asarray(ts, dtype=np.float32)
    if gc is None:
        return ts_f32, None
    gc_f32 = np.asarray(gc, dtype=np.float32)
    if int(gc_f32.shape[0]) != int(ts_f32.shape[0]):
        return ts_f32, None
    return ts_f32, gc_f32


def prepare_timeline_analysis_inputs(
    *,
    stats: dict,
    calc_song: dict,
    ref_arrays: dict,
    mode: Literal["base", "fg"] = "base",
) -> TimelineAnalysisInputs | None:
    if not isinstance(stats, dict) or not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return None

    mode = "fg" if mode == "fg" else "base"
    timestamps, great_candidates = _extract_timestamps_for_mode(calc_song, mode)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return None

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes", 0), 0)

    song_data = calc_song.get("song_data", {}) or {}
    base_ts = song_data.get("chart_timestamps", song_data.get("timestamps", timestamps))
    try:
        default_last_note = float(np.asarray(base_ts, dtype=np.float32)[-1]) if len(base_ts) else 0.0
    except Exception as e:
        logger.debug(f"timing_envelope:prepare_timeline_analysis_inputs: {e}")
        default_last_note = 0.0
    last_note_time = safe_float(metadata.get("Last Note Time", default_last_note), default=default_last_note)

    try:
        ref_pp = ref_arrays["Perfect Points"]
        ref_cm = ref_arrays["Combo Multiplier"]
        ref_fm = ref_arrays["Fever Multiplier"]
        ref_ff = ref_arrays["Fever Fill Rate"]
        ref_ft = ref_arrays["Fever Time"]
    except Exception as e:
        logger.debug(f"timing_envelope:prepare_timeline_analysis_inputs: {e}")
        return None

    pp_factor = float(lookup_reference_py(stats.get("Perfect Points", 0), ref_pp, TOTAL_ROWS))
    combo_mul = float(lookup_reference_py(stats.get("Combo Multiplier", 0), ref_cm, TOTAL_ROWS))
    fever_mul = float(lookup_reference_py(stats.get("Fever Multiplier", 0), ref_fm, TOTAL_ROWS))
    fever_fill_rate = float(lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_ff, TOTAL_ROWS))
    fever_time_stat = float(lookup_reference_py(stats.get("Fever Time", 0), ref_ft, TOTAL_ROWS))

    p_color = str(metadata.get("Primary Color", "") or "")
    s_color = str(metadata.get("Secondary Color", "") or "")
    primary_val = safe_int(stats.get(p_color, 0), 0)
    secondary_val = safe_int(stats.get(s_color, 0), 0)
    base_value = float((primary_val * 2) + secondary_val) + float(pp_factor)

    non_fever_cas = (total_notes - long_notes) * float(FEVER_FILL_BASE_RATE)
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0
    raw_fill = float(non_fever_cas) * float(fever_fill_rate)
    non_fever_base = int(ceil(raw_fill))

    fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    fever_duration = float(fever_time_cas) * float(fever_time_stat)

    return TimelineAnalysisInputs(
        mode=mode,
        timestamps=timestamps,
        great_candidates=great_candidates,
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        raw_fill=float(raw_fill),
        non_fever_base=int(non_fever_base),
        fever_duration=float(fever_duration),
        ft_idx=max(0, min(TOTAL_ROWS, safe_int(stats.get("Fever Time", 0), 0))),
        base_value=float(base_value),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
    )


def prepare_timeline_window_counter(
    *,
    calc_song: dict,
    ref_arrays: dict,
    mode: Literal["base", "fg"] = "base",
) -> TimelineWindowCounter | None:
    """Prepare a cheap reusable counter for resolved all-normal window counts."""

    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return None

    mode = "fg" if mode == "fg" else "base"
    timestamps, _great_candidates = _extract_timestamps_for_mode(calc_song, mode)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return None

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes", 0), 0)

    song_data = calc_song.get("song_data", {}) or {}
    base_ts = song_data.get("chart_timestamps", song_data.get("timestamps", timestamps))
    try:
        default_last_note = float(np.asarray(base_ts, dtype=np.float32)[-1]) if len(base_ts) else 0.0
    except Exception as e:
        logger.debug(f"timing_envelope:prepare_timeline_window_counter: {e}")
        default_last_note = 0.0
    last_note_time = safe_float(metadata.get("Last Note Time", default_last_note), default=default_last_note)

    try:
        ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32)
        ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32)
    except Exception as e:
        logger.debug(f"timing_envelope:prepare_timeline_window_counter: {e}")
        return None
    if int(ref_ff.shape[0]) <= TOTAL_ROWS or int(ref_ft.shape[0]) <= TOTAL_ROWS:
        return None

    return TimelineWindowCounter(
        timestamps=np.asarray(timestamps, dtype=np.float64),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        ref_ft=ref_ft,
        ref_ff=ref_ff,
    )


def count_timeline_analysis_windows(prepared: TimelineAnalysisInputs | None) -> int:
    """
    Count all-normal fever activations for a fixed stat point.

    This is the shared exact frontier bound: forced Greats can only delay fill,
    and carry can only extend fever, so no forced path can exceed this count.
    """

    if not isinstance(prepared, TimelineAnalysisInputs):
        return 0

    timestamps = prepared.timestamps
    total_notes = int(prepared.total_notes)
    if total_notes <= 0:
        return 0

    non_fever_base = int(prepared.non_fever_base)
    fever_duration = float(prepared.fever_duration)
    end_times_song = timestamps.astype(np.float64) + float(fever_duration)
    fever_end_song = np.searchsorted(timestamps, end_times_song, side="left").astype(np.int32, copy=False)

    return _count_timeline_windows_from_end_table(
        total_notes=int(total_notes),
        non_fever_base=int(non_fever_base),
        fever_end_song=fever_end_song,
    )
