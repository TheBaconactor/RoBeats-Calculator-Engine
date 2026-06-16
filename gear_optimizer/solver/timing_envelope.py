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
        # Group consecutive notes that share BOTH a quantized timestamp AND a Perfect window.
        # A held tail (wider [-40,+80] window) chorded with a narrower note thus lands in its
        # OWN group, keeping its full reach instead of being capped to the chord intersection
        # (the game registers each lane's hit independently). For chords whose members share one
        # window (the common case) this is identical to grouping by timestamp alone, so non-
        # held-tail charts are bit-unchanged.
        boundaries = np.nonzero(
            (ts_ms[1:] != ts_ms[:-1])
            | (note_low_ms[1:] != note_low_ms[:-1])
            | (note_high_ms[1:] != note_high_ms[:-1])
        )[0].astype(np.int32) + 1
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
            # Contiguous fever run: the first note at/after fever_start whose event reaches the
            # cutoff. Independent per-lane sampling can leave `ev` non-monotone, so this must be a
            # contiguous first-exit (a global searchsorted assumes a sorted stream); for a monotone
            # stream -- the deterministic ceiling envelope -- the two coincide exactly.
            exits = ev[fever_start:] >= end_ms
            fever_end_idx = fever_start + int(np.argmax(exits)) if bool(exits.any()) else total_notes

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
    Sample one legal Perfect-window hit offset per chord-group and return the resulting
    per-note event times in integer ms.

    Same-timestamp lanes are sampled INDEPENDENTLY -- the decompiled server clamps each event
    to its OWN note window and floors only the inter-event meter delta at 0 (no forced-monotone
    event coupling; see ServerPlayerNoteSequenceInfo:push_note_sequence), so the returned stream
    may be non-monotone and ``compute_fever_timeline_signature`` walks it with a contiguous
    first-exit. Used by tests/benchmarks as a sampled reference against the deterministic ceiling
    envelope; production scoring uses the deterministic envelope directly.
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

    # Each chord-group is an INDEPENDENT lane hit: the game clamps every event to its own note
    # window and never forces a later note's event forward (it floors only the inter-event meter
    # delta at 0), so sample each group's offset independently within its OWN [g_low, g_high].
    # Carrying a previous group's offset (the old monotone chain) would, for same-timestamp split
    # groups sharing base_t, force an offset past this note's g_high -- an illegal out-of-window hit.
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(group_base_t[g])
        g_low = int(group_low[g])
        g_high = int(group_high[g])
        off = int(rng.integers(g_low, g_high + 1, endpoint=False))
        event_ms[s:e] = base_t + off

    return event_ms


def _perfect_window_edges_ms(
    ts_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-note Perfect (low, high) window edges in ms, held-tail-aware.

    Shared by the latest-candidate (high) and earliest-floor (low) FG envelopes so both see the
    SAME per-note windows. A held tail keeps its full [-40,+80] reach -- NOT collapsed to a chord
    intersection. Assumes ``ts_sec`` non-empty (callers guard ``n <= 0``).
    """
    n = int(ts_sec.shape[0])
    if note_types is None or len(note_types) != n:
        nt = np.ones(n, dtype=np.int16)
    else:
        nt = np.asarray(note_types, dtype=np.int16)
    low, high = build_per_note_perfect_window_ms(
        nt,
        perfect_lower_ms=int(perfect_lower_ms),
        perfect_upper_ms=int(perfect_upper_ms),
        held_tail_type=int(held_tail_type),
        held_tail_time_multiplier=int(held_tail_time_multiplier),
    )
    return np.asarray(low, dtype=np.int32), np.asarray(high, dtype=np.int32)


def _emit_pernote_edge_envelope_sec(
    ts_sec: np.ndarray, edge_ms: np.ndarray, *, prefix_max: bool = False, quantize_ms: bool = True
) -> np.ndarray:
    """Per-note envelope (seconds): each note takes its OWN quantized chart ms + its OWN window
    edge, with NO chord-group collapse.

    The game registers every note's hit independently (per lane/track, confirmed against the
    decompiled server), so a held tail (Perfect window [-40,+80]) that shares a timestamp with a
    narrower note keeps its individual reach. The previous chord-intersection collapse
    (`prepare_grouped_timing_windows`: group_low=max(lows), group_high=min(highs)) lost the held
    tail's wider early/late reach and UNDER-counted fever when a chord-tied held tail was the
    activation (its +80 latest hit capped to the chord's +40) or a boundary note (its -40
    earliest capped to -20). For solo notes and chords WITHOUT a held tail this is bit-identical
    to the old grouped emit (each member's quantized ms equals the group base, and the group edge
    equals every member's edge). ``prefix_max`` keeps the floor monotone (searchsortable); it is
    pointwise <= chart, so the boundary only ever moves later -> never a regression.
    """
    if quantize_ms:
        q_ms = floor_to_int_ms(ts_sec)
    else:
        q_ms = (np.asarray(ts_sec, dtype=np.float32) * np.float32(1000.0)).astype(np.int32)
    event_ms = (np.asarray(q_ms, dtype=np.int32) + np.asarray(edge_ms, dtype=np.int32)).astype(np.int32)
    if prefix_max:
        np.maximum.accumulate(event_ms, out=event_ms)
    out = event_ms.astype(np.float32)
    out *= np.float32(0.001)
    return out


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
    _great_low_ms, great_high_ms = build_per_note_great_window_ms(
        nt,
        perfect_low_ms=perfect_low_ms,
        perfect_upper_ms=int(perfect_upper_ms),
        great_lower_ms=int(great_lower_ms),
        great_extra_upper_ms=int(great_extra_upper_ms),
        great_mode=str(great_mode or "late").strip().lower(),
        held_tail_type=int(held_tail_type),
        held_tail_time_multiplier=int(held_tail_time_multiplier),
    )
    # Per-note (NOT chord-collapsed): a held tail's widened late-Great reach is its own, so a
    # chord-tied held-tail late-Great activation is not capped to the chord intersection.
    return _emit_pernote_edge_envelope_sec(
        ts_sec, np.asarray(great_high_ms, dtype=np.int32), prefix_max=False, quantize_ms=quantize_ms
    )


def build_perfect_candidate_envelope_sec(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> np.ndarray:
    """Build the latest valid Perfect-candidate envelope (per-note `chart + Perfect upper`).

    Per-note, NOT chord-collapsed: a held-tail activation keeps its own +80 latest-hit reach
    (the chord intersection would cap it to a tighter chord member's +40 and under-count fever).
    """

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return ts_sec.astype(np.float32, copy=False)
    _low, high = _perfect_window_edges_ms(
        ts_sec,
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )
    return _emit_pernote_edge_envelope_sec(ts_sec, high, prefix_max=False, quantize_ms=quantize_ms)


def build_perfect_floor_envelope_sec(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> np.ndarray:
    """Earliest legal Perfect-hit envelope (per-note `chart + Perfect lower`), monotone via a
    prefix-max.

    Issue #42 fever-boundary search basis for FG. `floor[i] = chart[i] + per-note Perfect LOWER
    bound` (held-tail-aware: a held tail keeps its own -40, NOT the chord intersection's -20),
    then `maximum.accumulate` so a single `searchsorted` is exact even when a held tail's wider
    early edge makes the raw floor dip below an earlier note. With the FG activation fixed at its
    latest Perfect (optimal), a later note is in fever iff its earliest legal hit precedes the
    cutoff, so the fever extent is `searchsorted(this_envelope, perfect_candidate[a] +
    real_fever_time)`.

    Per-note (NOT chord-collapsed) and bit-consistent with the candidate: both share the SAME
    quantized int-ms chart (`floor_to_int_ms`) and the SAME `* float32(0.001)` conversion, and
    the floor is pointwise <= the candidate, so searchsorted never spuriously off-by-ones.
    """

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return ts_sec.astype(np.float32, copy=False)
    low, _high = _perfect_window_edges_ms(
        ts_sec,
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )
    return _emit_pernote_edge_envelope_sec(ts_sec, low, prefix_max=True, quantize_ms=quantize_ms)


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
    # Candidate (latest Perfect) + floor (earliest Perfect, issue #42 fever-boundary basis), both
    # per-note (not chord-collapsed, so a chord-tied held tail keeps its [-40,+80] reach). Route
    # through the canonical builders so production scores the exact path the tests validate.
    song_data["fg_perfect_candidate_timestamps"] = build_perfect_candidate_envelope_sec(chart_ts, note_types)
    song_data["fg_perfect_floor_timestamps"] = build_perfect_floor_envelope_sec(chart_ts, note_types)
    song_data["fg_great_candidate_timestamps"] = build_great_candidate_envelope_sec(
        chart_ts,
        note_types,
        great_mode="late",
    )

    meta = dict(calc_song.get("metadata", {}) or {})
    meta["TimingEnvelopeApplied"] = True
    meta["TimingEnvelopeMode"] = "perfect_window"
    meta["TimingEnvelopeFGPerfect"] = "perfect_upper"
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
