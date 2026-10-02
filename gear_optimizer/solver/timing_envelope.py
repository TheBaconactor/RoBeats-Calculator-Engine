"""The timing models a chart is prepared for (TimedSong) and the per-note hit envelopes of perfect_window.

perfect_window: every note may be hit anywhere inside its judgment window, so FG reads four per-note envelopes
(float32 seconds): the latest Perfect hit (fever activations), the earliest Perfect and earliest early-Great hits (fever
boundaries; prefix maxima, so one searchsorted finds a boundary exactly) and the latest late-Great hit. zero_ms: every
note is hit at its chart time (or the chart plus a custom per-note offset) and has no envelopes.

The judge's bands are `lower < delta <= upper` (SPUtil.timedelta_to_result, WebPort judgeWithEdges): the early edge is
exclusive, so the earliest reachable hit is the edge + 1 ms (after the held-tail x2) and the latest is the edge itself.
The windows are cumulative (the early-Great edge is the Perfect lower edge plus the Great extra, -95; GearStats
get_note_times) and per note, never collapsed over a chord: the game registers each lane's hit independently, so a
held tail keeps its own x2 reach.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import cached_property
from typing import NamedTuple

import numpy as np
from cachetools import LRUCache

from ..chart import Chart
from ..core.array_signature import array_sig16
from ..core.time_quantize import quantize_to_int_ms

# The game removes an unhit note once `now - hit > 200` ms (decompiled Constants.lua:19 NOTE_REMOVE_TIME = -200; the
# same edge for taps (Note.lua:191), hold heads and the hold despawn (HeldNote.lua:219/231)). A held tail's late-Great
# classification edge reaches +380, but an input scheduled past +200 races the per-frame sweep and lands only if no
# frame ticks inside the gap, which no frame rate guarantees: no hit is ever planned later than this.
NOTE_REMOVE_LATE_CAP_MS = 200
TIMING_MODES = ("perfect_window", "zero_ms")
PERFECT_LOWER_MS, PERFECT_UPPER_MS = -20, 40
GREAT_LOWER_EXTRA_MS, GREAT_UPPER_EXTRA_MS = -75, 150
HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE = 3, 2


def judgment_windows_ms(note_types: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-note reachable hit offsets (int32 ms): earliest Perfect, latest Perfect, earliest early-Great and latest
    late-Great (capped at the note removal)."""
    scale = np.where(np.asarray(note_types) == HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE, 1).astype(np.int32)
    return (
        PERFECT_LOWER_MS * scale + 1,
        PERFECT_UPPER_MS * scale,
        (PERFECT_LOWER_MS + GREAT_LOWER_EXTRA_MS) * scale + 1,
        np.minimum((PERFECT_UPPER_MS + GREAT_UPPER_EXTRA_MS) * scale, np.int32(NOTE_REMOVE_LATE_CAP_MS)),
    )


class Envelopes(NamedTuple):
    perfect_candidates: np.ndarray
    perfect_floor: np.ndarray
    great_floor: np.ndarray
    great_candidates: np.ndarray


def _envelope_sec(timestamps: np.ndarray, offset_ms: np.ndarray, *, prefix_max: bool = False) -> np.ndarray:
    """Each note's chart time in integer ms (the repo parity rule) plus its own offset, as float32 seconds."""
    event_ms = (quantize_to_int_ms(timestamps).astype(np.int32) + offset_ms).astype(np.int32)
    if prefix_max:
        np.maximum.accumulate(event_ms, out=event_ms)
    return event_ms.astype(np.float32) * np.float32(0.001)


def perfect_window_envelopes(timestamps: np.ndarray, note_types: np.ndarray) -> Envelopes:
    """The four perfect_window hit envelopes of a chart (timestamps in float32 seconds, chart order)."""
    ts = np.asarray(timestamps, dtype=np.float32)
    perfect_low, perfect_high, great_low, great_high = judgment_windows_ms(note_types)
    # The judge compares the decoded hit with the float32 chart time in float64, so the integer-ms edge encoded as
    # float32 seconds can round one step past Perfect (#161): cap each latest Perfect hit at the latest float32 still
    # inside its hard edge.
    hard_high = ts.astype(np.float64) + perfect_high.astype(np.float64) * 0.001
    safe_high = hard_high.astype(np.float32)
    overshot = safe_high.astype(np.float64) > hard_high
    safe_high[overshot] = np.nextafter(safe_high[overshot], np.float32(-np.inf))
    return Envelopes(
        perfect_candidates=np.minimum(_envelope_sec(ts, perfect_high), safe_high),
        perfect_floor=_envelope_sec(ts, perfect_low, prefix_max=True),
        great_floor=_envelope_sec(ts, great_low, prefix_max=True),
        great_candidates=_envelope_sec(ts, great_high),
    )


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


@dataclass(frozen=True, eq=False)
class TimedSong:
    """A chart prepared for one timing model.

    hit_timestamps is the timeline FG scores against: the chart itself, or the chart plus a custom per-note offset
    under zero_ms. perfect_window adds the per-note Perfect/Great candidate and floor envelopes that make FG
    carry-aware; zero_ms has none (every hit lands at its hit time).
    """

    chart: Chart
    mode: str
    baseline_hash: str
    hit_timestamps: np.ndarray
    perfect_candidates: np.ndarray | None = None
    perfect_floor: np.ndarray | None = None
    great_floor: np.ndarray | None = None
    great_candidates: np.ndarray | None = None

    @cached_property
    def fg_inputs(self):
        from .scoring.fg_policy import fg_song_inputs

        return fg_song_inputs(self)

    @cached_property
    def timeline_key(self) -> tuple:
        """The timeline frontier cache key: chart identity, note arrays and the timing model.

        The physical input engine consumes chart order and lane-local matcher order, so the aligned
        arrays are hashed in producer order. zero_ms fever membership depends only on timestamps, long
        notes and the FT/FF axes, so note types and lanes are not part of its key.
        """
        chart = self.chart
        ts_sig = array_sig16(np.ascontiguousarray(chart.timestamps))
        if self.mode == "zero_ms":
            nt_sig = lane_sig = b"zero_ms"
        else:
            nt_sig = array_sig16(np.ascontiguousarray(chart.note_types))
            lane_sig = array_sig16(np.ascontiguousarray(chart.lanes))
        return (
            chart.name,
            chart.difficulty,
            chart.total_notes,
            chart.last_note_time,
            chart.long_notes,
            bytes(ts_sig),
            bytes(nt_sig),
            bytes(lane_sig),
            "TIMING_ENVELOPE",
            self.mode,
            self.baseline_hash,
            0,
        )


_TIMED_SONG_CACHE: LRUCache = LRUCache(maxsize=128)
_TIMED_SONG_CACHE_LOCK = threading.Lock()


def time_song(chart: Chart, mode: str | None = None, baseline_offset: np.ndarray | None = None) -> TimedSong:
    """Prepare a chart for a timing model (default: the chart's Timing Mode header, else perfect_window).

    ``baseline_offset`` (seconds per note) is a custom played timeline and is only valid for zero_ms; an
    absent or all-zero offset is the canonical chart-time preset.
    """
    timing_mode = str(mode if mode is not None else chart.header.get("Timing Mode") or "perfect_window").strip().lower()
    if timing_mode not in TIMING_MODES:
        raise ValueError(f"time_song: unknown timing mode {mode!r}")
    custom = baseline_offset is not None and bool(np.any(np.asarray(baseline_offset)))
    if custom and timing_mode != "zero_ms":
        raise ValueError(
            "time_song: baseline_offset (custom per-note timing) is only valid for fixed timing "
            f"(mode='zero_ms'), not {timing_mode!r}"
        )
    if custom:
        hit_ts, baseline_hash = baseline_hit_timeline(chart.timestamps, baseline_offset)
        return TimedSong(chart=chart, mode="zero_ms", baseline_hash=baseline_hash, hit_timestamps=hit_ts)

    cache_key = (id(chart), timing_mode)
    with _TIMED_SONG_CACHE_LOCK:
        cached = _TIMED_SONG_CACHE.get(cache_key)
        if cached is not None and cached.chart is chart:
            return cached
    chart_ts = chart.timestamps
    if timing_mode == "zero_ms":
        song = TimedSong(chart=chart, mode="zero_ms", baseline_hash="", hit_timestamps=chart_ts)
    else:
        song = TimedSong(
            chart=chart,
            mode="perfect_window",
            baseline_hash="",
            hit_timestamps=chart_ts,
            **perfect_window_envelopes(chart_ts, chart.note_types)._asdict(),
        )
    with _TIMED_SONG_CACHE_LOCK:
        _TIMED_SONG_CACHE[cache_key] = song
    return song
