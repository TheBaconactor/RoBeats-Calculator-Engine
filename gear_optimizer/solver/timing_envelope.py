"""
Timing-envelope preparation and reduced exact timeline analysis.

This module owns the deterministic Perfect-window model used by both:

- base GPU exact timeline-frontier construction, and
- FG exact-DP frontier analysis.

The contract is intentionally narrower than full timing exactness: for fixed
stats, we compute exact properties of the retained timeline frontier. FG uses
the same counter to derive admissible score bounds for pruning, instead of a
hard activation-window cap.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np

from ..core.time_quantize import quantize_to_int_ms



logger = logging.getLogger(__name__)

# The game engine removes an unhit note once ``now - hit > 200`` ms (decompiled
# Constants.lua:19 ``NOTE_REMOVE_TIME = -200``; the SAME edge for taps
# (Note.lua:191), hold heads, and the hold despawn (HeldNote.lua:219/231)).
# Judgement windows wider than this — a held tail's late-Great classification
# edge reaches +380 — are scoring ranges only: an input scheduled past +200
# races the per-frame sweep and lands only if no frame ticks inside the gap,
# which no frame rate guarantees. The planner must never claim a hit later
# than this cap.
NOTE_REMOVE_LATE_CAP_MS = 200


def floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    """Quantize seconds to integer milliseconds using the repo parity rule."""

    return quantize_to_int_ms(timestamps_sec)


def baseline_hit_timeline(
    chart_timestamps_sec: np.ndarray,
    baseline_offset_sec: np.ndarray | None,
) -> tuple[np.ndarray, str]:
    """Apply a per-note baseline timing offset ``T`` to the chart timeline.

    Returns ``(hit_timestamps, baseline_hash)`` where ``hit_timestamps = chart + T`` (float32
    seconds) and ``baseline_hash`` is a stable digest of ``T`` for cache separation. A ``None`` or
    all-zero offset returns the chart unchanged and an empty hash -- the ``zero_ms`` (``T == 0``)
    preset, bit-identical to the chart-only path. Fails loud if ``T`` reorders notes: the fever
    timeline searchsorts the hit times, so they must stay non-decreasing.
    """
    chart = np.asarray(chart_timestamps_sec, dtype=np.float32)
    if baseline_offset_sec is None:
        return chart, ""
    offset = np.asarray(baseline_offset_sec, dtype=np.float32)
    if int(offset.shape[0]) != int(chart.shape[0]):
        raise ValueError(
            f"baseline timing offset length {int(offset.shape[0])} != song note count "
            f"{int(chart.shape[0])}"
        )
    if not bool(np.any(offset)):
        return chart, ""
    hit = (chart + offset).astype(np.float32)
    if int(hit.shape[0]) > 1 and bool(np.any(np.diff(hit) < np.float32(0.0))):
        raise ValueError("baseline timing offset reorders notes (hit timeline must be non-decreasing)")
    quantized_ms = np.round(np.asarray(offset, dtype=np.float64) * 1000.0).astype(np.int64)
    baseline_hash = hashlib.blake2b(quantized_ms.tobytes(), digest_size=8).hexdigest()
    return hit, baseline_hash


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
    # Early edge is EXCLUSIVE in the engine judge (score_bundle.mjs judgeWithEdges is strict `>`:
    # a hit at exactly `perfect_lower` is judged Great, not Perfect). So the earliest REACHABLE
    # Perfect hit is `perfect_lower + 1` ms (tail: `-40 -> -39`), not the edge value itself. The +1
    # is a flat ms after the held-tail x2 (the edge scales, the 1ms strict-boundary does not). The
    # late edge (`upper`) is inclusive in the engine, so it stays at the value. (BUG-1 fix.)
    lower = (int(perfect_lower_ms) * mult + 1).astype(np.int16)
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
    late_removal_cap_ms: int = NOTE_REMOVE_LATE_CAP_MS,
) -> tuple[np.ndarray, np.ndarray]:
    note_types = np.asarray(note_types, dtype=np.int16)
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)

    # The late edge is deliverability-capped by the engine's note removal, NOT
    # by the (wider) classification window: a held tail's +380 late-Great edge
    # is unreachable past +200 (see NOTE_REMOVE_LATE_CAP_MS).
    great_upper_abs_ms = np.minimum(
        ((int(perfect_upper_ms) + int(great_extra_upper_ms)) * mult).astype(np.int32),
        np.int32(int(late_removal_cap_ms)),
    )
    perfect_low_abs_ms = np.asarray(perfect_low_ms, dtype=np.int32)
    mode = str(great_mode or "late").strip().lower()

    if mode == "late":
        great_low_abs_ms = (int(perfect_upper_ms) * mult + 1).astype(np.int32)
        great_high_abs_ms = great_upper_abs_ms
        if bool(np.any(great_low_abs_ms > great_high_abs_ms)):
            raise ValueError(
                "late-Great window empty: removal cap "
                f"{int(late_removal_cap_ms)}ms is below a note's earliest late-Great "
                f"({int(np.max(great_low_abs_ms))}ms)"
            )
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
    late_removal_cap_ms: int = NOTE_REMOVE_LATE_CAP_MS,
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
        late_removal_cap_ms=int(late_removal_cap_ms),
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


def build_great_floor_envelope_sec(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int = -20,
    great_lower_ms: int = -75,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> np.ndarray:
    """Earliest legal GREAT-hit envelope (per-note `chart + cumulative Great-lower`), monotone via a
    prefix-max.

    Issue #44 greats-side fever-boundary basis. VERIFIED against the decompiled game (place
    706824758): the judgment windows are CUMULATIVE. `GearStats.get_note_times` builds the Great
    lower boundary by ADDING the per-tier Great extra to the Perfect lower boundary
    (`great_lower = perfect_lower + great_lower_extra = -20 + (-75) = -95`), and both
    `SPUtil.timedelta_to_result` (the scorer) and `NoteTimeGraph` (renders "-95ms (Great)") put the
    early-Great edge at **-95** (held tail ×2 = -190), NOT -75. This matches the candidate's own
    `build_per_note_great_window_ms`, which already cumulates (`perfect_low + great_lower`).

    So the earliest a boundary note can be hit as a Great is `chart - 95`; a note sitting 20-95ms
    past a fever cutoff is out of Perfect reach (`chart-20 >= cutoff`) but still reachable INTO fever
    as a Great (`chart-95 < cutoff`). The maximal early-Great fever extent is
    `searchsorted(this_envelope, perfect_candidate[a] + real_fever_time)`, mirroring the
    earliest-Perfect `build_perfect_floor_envelope_sec` with the cumulative Great lower edge.

    Per-note (NOT chord-collapsed: a held tail keeps its own -190) and bit-consistent with the
    Perfect floor/candidate -- same quantized int-ms chart (`floor_to_int_ms`) and same
    `* float32(0.001)` conversion. Pointwise `<= perfect_floor` (Great reaches earlier), so the
    fever boundary it produces is always `>= e_perfect`: a pure additional reachable surface,
    never a regression of the #42 Perfect boundary.
    """

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return ts_sec.astype(np.float32, copy=False)
    if note_types is None or len(note_types) != n:
        nt = np.ones(n, dtype=np.int16)
    else:
        nt = np.asarray(note_types, dtype=np.int16)
    is_tail = nt == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int32)
    # Cumulative early-Great edge = perfect_lower + great_lower_extra (game get_note_times), ×2 on
    # held tails -> -95 / -190. (Was raw -75: it dropped the Perfect-lower offset and under-included
    # legal early-Great fever for notes 75-95ms past a cutoff.)
    # Early edge is EXCLUSIVE in the engine judge (strict `>`): a hit at exactly the cumulative
    # `perfect_lower + great_lower` edge is judged Okay, not Great. So the earliest REACHABLE
    # early-Great hit is that edge `+ 1` ms (tap `-95 -> -94`, tail `-190 -> -189`); the +1 is a
    # flat ms after the held-tail x2. Independent of the Perfect-floor +1 (this path uses the raw
    # constants, not the Perfect-window array), so no double-count. (BUG-1 fix.)
    great_low_ms = ((int(perfect_lower_ms) + int(great_lower_ms)) * mult + 1).astype(np.int32)
    return _emit_pernote_edge_envelope_sec(ts_sec, great_low_ms, prefix_max=True, quantize_ms=quantize_ms)


def apply_timing_envelope(
    calc_song: dict,
    *,
    attach_fg: bool = True,
    mode: str | None = None,
    baseline_offset: np.ndarray | None = None,
) -> dict | None:
    """
    Attach deterministic timing-envelope streams to a calc_song.

    ``mode`` selects the timing model this calc_song is prepared for. When omitted, the chart's
    optional ``Timing Mode`` metadata is authoritative, then defaults to ``perfect_window``. It is a
    semantic input (each mode is one canonical preparation), not a perf flag:

    - ``"perfect_window"`` (default): base scoring keeps chart timestamps; FG
      receives chart timestamps plus the deterministic Perfect/Great candidate +
      floor envelopes for carry-aware exact DP.
    - ``"zero_ms"`` (issue #51 fixed timing): every hit lands at chart time. Base
      keeps chart timestamps; FG is prepared WITHOUT the Perfect-window envelope
      streams, so ``extract_fg_song_inputs`` falls back to chart timestamps for
      every activation/boundary decision and disables forced-great carry -- the
      canonical chart-only FG path. ``TimingEnvelopeMode="zero_ms"`` is stamped so
      cache signatures stay disjoint from the envelope path.
    """

    if not isinstance(calc_song, dict):
        return None
    metadata = calc_song.get("metadata", {}) or {}
    timing_mode = str(mode if mode is not None else metadata.get("Timing Mode") or "perfect_window").strip().lower()
    if timing_mode not in {"perfect_window", "zero_ms"}:
        raise ValueError(f"apply_timing_envelope: unknown timing mode {mode!r}")
    if (
        baseline_offset is not None
        and timing_mode != "zero_ms"
        and bool(np.any(np.asarray(baseline_offset)))
    ):
        raise ValueError(
            "apply_timing_envelope: baseline_offset (custom per-note timing) is only valid for "
            f"fixed timing (mode='zero_ms'), not {timing_mode!r}"
        )

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        return None

    if timing_mode == "perfect_window" and attach_fg:
        # Idempotent fast path: the four envelope streams are pure functions of
        # (chart_timestamps, note_types), so re-applying rebuilds identical arrays.
        # The identity check pins fg_timestamps to the SAME chart array object --
        # a replaced chart (new object) still rebuilds. note_types is load-fixed song
        # metadata written once alongside chart_timestamps and never mutated in place,
        # so the chart-identity check also covers it (no separate note_types signature
        # is needed on this hot path).
        meta_existing = calc_song.get("metadata", {}) or {}
        chart_existing = song_data.get("chart_timestamps")
        if (
            meta_existing.get("TimingEnvelopeMode") == "perfect_window"
            and chart_existing is not None
            and song_data.get("fg_timestamps") is chart_existing
            and all(
                song_data.get(stream) is not None
                for stream in (
                    "fg_perfect_candidate_timestamps",
                    "fg_perfect_floor_timestamps",
                    "fg_great_floor_timestamps",
                    "fg_great_candidate_timestamps",
                )
            )
        ):
            return {"mode": "fg", "notes": int(len(chart_existing)), "great_mode": "late_upper"}

    chart_ts = np.asarray(timestamps, dtype=np.float32)
    song_data["chart_timestamps"] = chart_ts

    if timing_mode == "zero_ms":
        # Fixed/explicit timing: no Perfect-window envelope. The played timeline is
        # ``chart + baseline_offset`` (T); the four FG candidate/floor streams are dropped so
        # extract_fg_song_inputs uses this single hit timeline for every activation/boundary
        # decision and disables forced-great carry. ``baseline_offset is None`` (or all-zero) is
        # the canonical ``zero_ms`` (T == 0) preset, bit-identical to the chart-only build.
        hit_ts, baseline_hash = baseline_hit_timeline(chart_ts, baseline_offset)
        for _stream in (
            "fg_perfect_candidate_timestamps",
            "fg_perfect_floor_timestamps",
            "fg_great_floor_timestamps",
            "fg_great_candidate_timestamps",
        ):
            song_data.pop(_stream, None)
        song_data["fg_timestamps"] = hit_ts
        meta = dict(calc_song.get("metadata", {}) or {})
        meta["TimingEnvelopeApplied"] = True
        meta["TimingEnvelopeMode"] = "zero_ms"
        meta["TimingEnvelopeBaselineHash"] = baseline_hash
        meta["TimingEnvelopeFGPerfect"] = "chart"
        meta["TimingEnvelopeFGCarry"] = "none"
        calc_song["metadata"] = meta
        calc_song["song_data"] = song_data
        return {
            "mode": "fg" if attach_fg else "base",
            "notes": int(chart_ts.shape[0]),
            "timing_mode": "zero_ms",
            "baseline_hash": baseline_hash,
        }

    if not attach_fg:
        calc_song["song_data"] = song_data
        return {"mode": "base", "notes": int(chart_ts.shape[0])}

    note_types = song_data.get("note_types")
    if note_types is None or len(note_types) != int(chart_ts.shape[0]):
        note_types = np.ones(int(chart_ts.shape[0]), dtype=np.int16)
    else:
        note_types = np.asarray(note_types, dtype=np.int16)

    song_data["fg_timestamps"] = chart_ts
    # Candidate (latest Perfect) + floor (earliest Perfect, issue #42 fever-boundary basis), both
    # per-note (not chord-collapsed, so a chord-tied held tail keeps its [-40,+80] reach). Route
    # through the canonical builders so production scores the exact path the tests validate.
    song_data["fg_perfect_candidate_timestamps"] = build_perfect_candidate_envelope_sec(chart_ts, note_types)
    song_data["fg_perfect_floor_timestamps"] = build_perfect_floor_envelope_sec(chart_ts, note_types)
    # Earliest-Great floor (issue #44): the greats-side fever-boundary basis. A boundary note
    # 20-95ms past a cutoff is reachable into fever only as a Great; this envelope (chart - 95,
    # held tail -190 = cumulative perfect_lower + great_lower_extra, prefix-max) is searched for the
    # extended fever end. Pointwise <= the Perfect floor, so it only ever ADDS surfaces on top of #42.
    song_data["fg_great_floor_timestamps"] = build_great_floor_envelope_sec(chart_ts, note_types)
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
    calc_song["metadata"] = meta
    calc_song["song_data"] = song_data
    return {"mode": "fg", "notes": int(chart_ts.shape[0]), "great_mode": "late_upper"}
