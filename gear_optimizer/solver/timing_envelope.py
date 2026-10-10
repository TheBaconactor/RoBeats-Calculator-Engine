"""Prepare charts for Precise judgment-window timing or fixed Non-Precise timing.

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
from functools import cached_property, lru_cache
from typing import NamedTuple

import numpy as np
from cachetools import LRUCache

from ..core.timing_modes import TIMING_MODES
from ..chart import Chart
from ..core.array_signature import array_sig16
from ..core.time_quantize import quantize_to_int_ms
from ..gamedata import StatCurves

# The game removes an unhit note once `now - hit > 200` ms (decompiled Constants.lua:19 NOTE_REMOVE_TIME = -200; the
# same edge for taps (Note.lua:191), hold heads and the hold despawn (HeldNote.lua:219/231)). A held tail's late-Great
# classification edge reaches +380, but an input scheduled past +200 races the per-frame sweep and lands only if no
# frame ticks inside the gap, which no frame rate guarantees: no hit is ever planned later than this.
NOTE_REMOVE_LATE_CAP_MS = 200
PERFECT_LOWER_MS, PERFECT_UPPER_MS = -20, 40
GREAT_LOWER_EXTRA_MS, GREAT_UPPER_EXTRA_MS = -75, 150
HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE = 3, 2
FRAME_MARGIN_MS = 1000.0 / 60.0 + 1.0


class Band(NamedTuple):
    earliest: int
    latest: int


class JudgmentBounds(NamedTuple):
    perfect: Band
    early_great: Band
    late_great: Band


@lru_cache(maxsize=None)
def judgment_bounds(scale: int) -> JudgmentBounds:
    """A note's reachable planned hit offsets (ms) per judgment; `scale` is its window scale (2 for a held tail). The
    late-Great band ends at the note removal."""
    return JudgmentBounds(
        perfect=Band(PERFECT_LOWER_MS * scale + 1, PERFECT_UPPER_MS * scale),
        early_great=Band((PERFECT_LOWER_MS + GREAT_LOWER_EXTRA_MS) * scale + 1, PERFECT_LOWER_MS * scale),
        late_great=Band(
            PERFECT_UPPER_MS * scale + 1,
            min((PERFECT_UPPER_MS + GREAT_UPPER_EXTRA_MS) * scale, NOTE_REMOVE_LATE_CAP_MS),
        ),
    )


def judgment_windows_ms(
    note_types: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-note reachable hit offsets (int32 ms, see judgment_bounds): earliest Perfect, latest Perfect, earliest
    early-Great, latest late-Great and earliest late-Great."""
    tap, tail = judgment_bounds(1), judgment_bounds(HELD_TAIL_WINDOW_SCALE)
    is_tail = np.asarray(note_types) == HELD_TAIL_TYPE
    return tuple(
        np.where(is_tail, tail_value, tap_value).astype(np.int32)
        for tap_value, tail_value in (
            (tap.perfect.earliest, tail.perfect.earliest),
            (tap.perfect.latest, tail.perfect.latest),
            (tap.early_great.earliest, tail.early_great.earliest),
            (tap.late_great.latest, tail.late_great.latest),
            (tap.late_great.earliest, tail.late_great.earliest),
        )
    )


class Envelopes(NamedTuple):
    perfect_candidates: np.ndarray
    perfect_floor: np.ndarray
    great_floor: np.ndarray
    great_candidates: np.ndarray
    late_great_floor: np.ndarray
    exit_ceiling: np.ndarray


def _envelope_sec(timestamps: np.ndarray, offset_ms: np.ndarray, *, prefix_max: bool = False) -> np.ndarray:
    """Each note's chart time in integer ms (the repo parity rule) plus its own offset, as float32 seconds."""
    event_ms = (quantize_to_int_ms(timestamps).astype(np.int32) + offset_ms).astype(np.int32)
    if prefix_max:
        np.maximum.accumulate(event_ms, out=event_ms)
    return event_ms.astype(np.float32) * np.float32(0.001)


def precise_envelopes(
    timestamps: np.ndarray, note_types: np.ndarray
) -> Envelopes:
    """The six hit envelopes of a chart in a windowed mode (timestamps in float32 seconds, chart order)."""
    ts = np.asarray(timestamps, dtype=np.float32)
    perfect_low, perfect_high, great_low, great_high, _ = judgment_windows_ms(note_types)
    # The judge compares the decoded hit with the float32 chart time in float64, so the integer-ms edge encoded as
    # float32 seconds can round one step past Perfect (#161): cap each latest Perfect hit at the latest float32 still
    # inside its hard edge.
    hard_high = ts.astype(np.float64) + perfect_high.astype(np.float64) * 0.001
    safe_high = hard_high.astype(np.float32)
    overshot = safe_high.astype(np.float64) > hard_high
    safe_high[overshot] = np.nextafter(safe_high[overshot], np.float32(-np.inf))
    perfect_candidates = np.minimum(_envelope_sec(ts, perfect_high), safe_high)
    perfect_floor = _envelope_sec(ts, perfect_low, prefix_max=True)
    great_floor = _envelope_sec(ts, great_low, prefix_max=True)
    great_candidates = _envelope_sec(ts, great_high)
    late_great_floor = perfect_candidates + np.float32(0.001)
    return Envelopes(
        perfect_candidates=perfect_candidates,
        perfect_floor=perfect_floor,
        great_floor=great_floor,
        great_candidates=great_candidates,
        late_great_floor=late_great_floor,
        exit_ceiling=np.ascontiguousarray(np.minimum.accumulate(perfect_candidates[::-1])[::-1]),
    )


def fever_durations(last_note_time: float, decay_rates: np.ndarray) -> np.ndarray:
    """Per Fever Time value, the fever's duration in seconds as the game computes it in float64: the song's approximate
    length ((LastNoteTime ms + 1000) / 1000, SongDatabase songkey_get_approx_length_sec) kept in ms by PlayerScore and
    turned back into seconds by GearStats get_powerbar_base_decay_time_seconds, times the base decay rate."""
    approx_length_ms = (round(float(last_note_time) * 1000.0) + 1000) / 1000 * 1000
    return approx_length_ms / 1000 * np.asarray(decay_rates, dtype=np.float64)


def fever_fill_denominators(hit_objects: int, fill_bases: np.ndarray) -> np.ndarray:
    """Per Fever Fill Rate value, the game's fever fill denominator, hit objects x the fill base (GearStats
    get_fever_fill_base): a Perfect adds 1 / denominator to the fever bar, a Great 1 / (2 x denominator); the bar is
    clamped to 1 and fever starts when it reaches 1 (PlayerScore)."""
    return float(hit_objects) * np.asarray(fill_bases, dtype=np.float64)


def fever_fill_thresholds(denominators: np.ndarray) -> np.ndarray:
    """Per denominator, the fill in Perfects (a Great counts half) at which the frontier's closed forms start fever.

    They compare whole half-notes with it, so it is ceil(2 x denominator) / 2, except where the game's float64 bar
    disagrees with that count. That needs a denominator that is a multiple of one half up to float64 rounding: there
    the bar after the matching run of Perfects can read 0.9999999999999999 (Back Out (Easy) at Fever Fill Rate 80:
    denominator 28, the 28th Perfect leaves the bar short and the game starts fever on the 29th). The threshold
    follows the game's all-Perfect run; a run mixing Greats that lands exactly on such a denominator sums just below
    or just above 1 depending on its order, so the physical replay walks the game's bar for every stored plan.
    """
    d = np.asarray(denominators, dtype=np.float64)
    thresholds = np.ceil(2.0 * d) / 2.0
    for i in np.flatnonzero(np.abs(2.0 * d - np.round(2.0 * d)) < 1e-6):
        perfects = _perfects_to_fill(float(d[i]))
        thresholds[i] = min(max(thresholds[i], perfects - 0.5), perfects)
    return thresholds


def fever_axes(total_notes: int, long_notes: int, last_note_time: float, curves: StatCurves) -> tuple[np.ndarray, np.ndarray]:
    """The axes every (Fever Time, Fever Fill Rate) cell of a chart is built from: per Fever Time value the fever's
    duration in seconds, per Fever Fill Rate value its fill threshold in Perfects (hit objects = notes - long notes)."""
    durations = fever_durations(last_note_time, curves.f64["Fever Time"])
    denominators = fever_fill_denominators(int(total_notes) - int(long_notes), curves.f64["Fever Fill Rate"])
    return durations, fever_fill_thresholds(denominators)


def _perfects_to_fill(denominator: float) -> int:
    """How many Perfects in a row fill the game's fever bar (PlayerScore es_playerscore_apply_hit_to_powerbar)."""
    fill, bar, perfects = 1.0 / denominator, 0.0, 0
    while bar < 1.0:
        bar = min(bar + fill, 1.0)
        perfects += 1
    return perfects


def baseline_hit_timeline(
    chart_timestamps_sec: np.ndarray,
    baseline_offset_sec: np.ndarray | None,
) -> tuple[np.ndarray, str]:
    """Apply a per-note baseline timing offset ``T`` to the chart timeline.

    Returns ``(hit_timestamps, baseline_hash)`` where ``hit_timestamps = chart + T`` (float32
    seconds) and ``baseline_hash`` is a stable digest of ``T`` for cache separation. A ``None`` or
    all-zero offset returns the chart unchanged and an empty hash -- the ``non-precise`` (``T == 0``)
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
    under Non-Precise. Precise adds the per-note Perfect/Great candidate and floor envelopes that make FG carry-aware;
    Non-Precise has none (every hit lands at its hit time).
    """

    chart: Chart
    mode: str
    baseline_hash: str
    hit_timestamps: np.ndarray
    perfect_candidates: np.ndarray | None = None
    perfect_floor: np.ndarray | None = None
    great_floor: np.ndarray | None = None
    great_candidates: np.ndarray | None = None
    late_great_floor: np.ndarray | None = None
    exit_ceiling: np.ndarray | None = None

    @cached_property
    def fg_inputs(self):
        from .scoring.fg_policy import fg_song_inputs

        return fg_song_inputs(self)

    @cached_property
    def timeline_key(self) -> tuple:
        """The timeline frontier cache key: chart identity, note arrays and the timing model.

        The physical input engine consumes chart order and lane-local matcher order, so the aligned
        arrays are hashed in producer order. non-precise fever membership depends only on timestamps, long
        notes and the FT/FF axes, so note types and lanes are not part of its key.
        """
        chart = self.chart
        ts_sig = array_sig16(np.ascontiguousarray(chart.timestamps))
        if self.mode == "non-precise":
            nt_sig = lane_sig = b""
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


def time_song(chart: Chart, mode: str, baseline_offset: np.ndarray | None = None) -> TimedSong:
    """Prepare a chart for a timing mode (core.timing_modes).

    ``baseline_offset`` (seconds per note) is a custom played timeline and is only valid for non-precise; an
    absent or all-zero offset is the canonical chart-time preset.
    """
    if mode not in TIMING_MODES:
        raise ValueError(f"time_song: unknown timing mode {mode!r}")
    custom = baseline_offset is not None and bool(np.any(np.asarray(baseline_offset)))
    if custom and mode != "non-precise":
        raise ValueError(
            "time_song: baseline_offset (custom per-note timing) is only valid for fixed timing "
            f"(mode='non-precise'), not {mode!r}"
        )
    if custom:
        hit_ts, baseline_hash = baseline_hit_timeline(chart.timestamps, baseline_offset)
        return TimedSong(chart=chart, mode="non-precise", baseline_hash=baseline_hash, hit_timestamps=hit_ts)

    cache_key = (id(chart), mode)
    with _TIMED_SONG_CACHE_LOCK:
        cached = _TIMED_SONG_CACHE.get(cache_key)
        if cached is not None and cached.chart is chart:
            return cached
    chart_ts = chart.timestamps
    if mode == "non-precise":
        song = TimedSong(chart=chart, mode="non-precise", baseline_hash="", hit_timestamps=chart_ts)
    else:
        song = TimedSong(
            chart=chart,
            mode=mode,
            baseline_hash="",
            hit_timestamps=chart_ts,
            **precise_envelopes(chart_ts, chart.note_types)._asdict(),
        )
    with _TIMED_SONG_CACHE_LOCK:
        _TIMED_SONG_CACHE[cache_key] = song
    return song
