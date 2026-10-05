"""The timing models a chart is prepared for (TimedSong) and the per-note hit envelopes of the windowed models.

perfect_window: every note may be hit anywhere inside its judgment window, so FG reads four per-note envelopes
(float32 seconds): the latest Perfect hit (fever activations), the earliest Perfect and earliest early-Great hits (fever
boundaries; prefix maxima, so one searchsorted finds a boundary exactly) and the latest late-Great hit. frame_robust:
the same windows, claiming fever only for notes in fever at every frame timing (fever_window_times). zero_ms: every
note is hit at its chart time (or the chart plus a custom per-note offset) and has no envelopes.

The judge's bands are `lower < delta <= upper` (SPUtil.timedelta_to_result, WebPort judgeWithEdges): the early edge is
exclusive, so the earliest reachable hit is the edge + 1 ms (after the held-tail x2) and the latest is the edge itself.
The windows are cumulative (the early-Great edge is the Perfect lower edge plus the Great extra, -95; GearStats
get_note_times) and per note, never collapsed over a chord: the game registers each lane's hit independently, so a
held tail keeps its own x2 reach.
"""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import NamedTuple

import numpy as np
from cachetools import LRUCache

from ..chart import Chart
from ..core.array_signature import array_sig16
from ..core.time_quantize import quantize_to_int_ms
from ..rules import FEVER_FILL_PER_NOTE, FEVER_TIME_OFFSET, FEVER_TIME_PER_SECOND

# The game removes an unhit note once `now - hit > 200` ms (decompiled Constants.lua:19 NOTE_REMOVE_TIME = -200; the
# same edge for taps (Note.lua:191), hold heads and the hold despawn (HeldNote.lua:219/231)). A held tail's late-Great
# classification edge reaches +380, but an input scheduled past +200 races the per-frame sweep and lands only if no
# frame ticks inside the gap, which no frame rate guarantees: no hit is ever planned later than this.
NOTE_REMOVE_LATE_CAP_MS = 200
TIMING_MODES = ("perfect_window", "zero_ms", "frame_robust")
# The modes whose frontier caches the service prebuilds for every catalog chart; frame_robust builds a song's caches on
# its first use.
PREBUILT_TIMING_MODES = ("perfect_window", "zero_ms")
PERFECT_LOWER_MS, PERFECT_UPPER_MS = -20, 40
GREAT_LOWER_EXTRA_MS, GREAT_UPPER_EXTRA_MS = -75, 150
HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE = 3, 2
# frame_robust plans for every frame timing (frame_mode/FRAME_TIMING_SPEC.md). The game reads inputs once per frame and
# judges them, fills and drains fever at that frame's song clock, and its server re-scores the event times floored to
# whole ms. So a planned press is judged up to one frame (1/60 s at >= 60 fps; the web port's clock steps up to
# 17.27 ms) plus the 1 ms floor late, never early. This margin covers both: a band's latest planned offset is its late
# edge minus the margin, a note is planned in fever only when it follows the activation press by at most the fever
# time minus the margin and out of it only from the fever time plus the margin, and two presses whose order matters
# are planned at least the margin apart.
FRAME_MARGIN_MS = 1000.0 / 60.0 + 1.0
# The windowed modes' cache revisions, bumped with every change to a mode's frontier payloads or bundles. A version that
# ratifies its predecessors serves their files to every mode whose key is unchanged, so only the byte-gated modes may
# keep their keys (perfect_window 2: fevers may end early; frame_robust 4: same-lane spacing).
CACHE_REVISIONS = {"perfect_window": 2, "frame_robust": 4}


class Band(NamedTuple):
    earliest: int
    latest: int


class JudgmentBounds(NamedTuple):
    perfect: Band
    early_great: Band
    late_great: Band


@lru_cache(maxsize=None)
def judgment_bounds(scale: int, mode: str) -> JudgmentBounds:
    """A note's reachable planned hit offsets (ms) per judgment; `scale` is its window scale (2 for a held tail). The
    late-Great band ends at the note removal; frame_robust ends every band FRAME_MARGIN_MS earlier (whole ms)."""
    margin = FRAME_MARGIN_MS if mode == "frame_robust" else 0.0

    def latest(edge_ms: int) -> int:
        return int(np.floor(edge_ms - margin))

    return JudgmentBounds(
        perfect=Band(PERFECT_LOWER_MS * scale + 1, latest(PERFECT_UPPER_MS * scale)),
        early_great=Band((PERFECT_LOWER_MS + GREAT_LOWER_EXTRA_MS) * scale + 1, latest(PERFECT_LOWER_MS * scale)),
        late_great=Band(
            PERFECT_UPPER_MS * scale + 1,
            latest(min((PERFECT_UPPER_MS + GREAT_UPPER_EXTRA_MS) * scale, NOTE_REMOVE_LATE_CAP_MS)),
        ),
    )


def judgment_windows_ms(
    note_types: np.ndarray, mode: str = "perfect_window"
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-note reachable hit offsets (int32 ms, see judgment_bounds): earliest Perfect, latest Perfect, earliest
    early-Great, latest late-Great and earliest late-Great."""
    tap, tail = judgment_bounds(1, mode), judgment_bounds(HELD_TAIL_WINDOW_SCALE, mode)
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
    lane_bounds: np.ndarray


def _envelope_sec(timestamps: np.ndarray, offset_ms: np.ndarray, *, prefix_max: bool = False) -> np.ndarray:
    """Each note's chart time in integer ms (the repo parity rule) plus its own offset, as float32 seconds."""
    event_ms = (quantize_to_int_ms(timestamps).astype(np.int32) + offset_ms).astype(np.int32)
    if prefix_max:
        np.maximum.accumulate(event_ms, out=event_ms)
    return event_ms.astype(np.float32) * np.float32(0.001)


def _lane_order_bounds(
    earliest: np.ndarray, latest: np.ndarray, note_types: np.ndarray, lanes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Tight bounds for chart order and lane-local input spacing (a hold release needs no press gap)."""
    low, high = earliest.astype(np.float64), latest.astype(np.float64)
    nt, lane_arr = np.asarray(note_types).reshape(-1), np.asarray(lanes).reshape(-1)
    n = len(low)
    gap = (FRAME_MARGIN_MS + 0.001) / 1000.0
    previous: dict[int, int] = {}
    for j in range(n):
        if j:
            low[j] = max(low[j], low[j - 1])
        lane = int(lane_arr[j])
        if lane in previous:
            low[j] = max(low[j], low[previous[lane]] + (0.0 if nt[j] == HELD_TAIL_TYPE else gap))
        previous[lane] = j
    following: dict[int, int] = {}
    for j in range(n - 1, -1, -1):
        if j + 1 < n:
            high[j] = min(high[j], high[j + 1])
        lane = int(lane_arr[j])
        if lane in following:
            successor = following[lane]
            high[j] = min(high[j], high[successor] - (0.0 if nt[successor] == HELD_TAIL_TYPE else gap))
        following[lane] = j
    # Round toward the feasible interval, preserving the producer's float32 contract.
    low32, high32 = low.astype(np.float32), high.astype(np.float32)
    below = low32.astype(np.float64) < low
    above = high32.astype(np.float64) > high
    low32[below] = np.nextafter(low32[below], np.float32(np.inf))
    high32[above] = np.nextafter(high32[above], np.float32(-np.inf))
    if np.any(low32 > high32):
        raise ValueError("frame_robust lane spacing cannot realize full combo inside the judgment bounds")
    return low32, high32


def perfect_window_envelopes(
    timestamps: np.ndarray, note_types: np.ndarray, mode: str = "perfect_window", *, lanes: np.ndarray | None = None
) -> Envelopes:
    """The six hit envelopes of a chart in a windowed mode (timestamps in float32 seconds, chart order)."""
    ts = np.asarray(timestamps, dtype=np.float32)
    perfect_low, perfect_high, great_low, great_high, late_great_low = judgment_windows_ms(note_types, mode)
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
    latest_perfect_schedule = perfect_candidates
    lane_bounds = np.empty((0, 5), dtype=np.float64)
    if mode == "frame_robust":
        if lanes is None:
            raise ValueError("frame_robust envelopes require chart lanes")
        perfect_floor, latest_perfect_schedule = _lane_order_bounds(perfect_floor, perfect_candidates, note_types, lanes)
        great_floor, _ = _lane_order_bounds(great_floor, great_candidates, note_types, lanes)
        # Successor, incoming press gap, latest Perfect, predecessor, earliest Perfect.
        lane_bounds = np.column_stack((
            np.full(len(ts), len(ts)), np.where(note_types == HELD_TAIL_TYPE, 0.0, (FRAME_MARGIN_MS + 0.001) / 1000.0),
            latest_perfect_schedule, np.full(len(ts), -1), perfect_floor,
        ))
        previous: dict[int, int] = {}
        for j, lane in enumerate(lanes):
            lane = int(lane)
            predecessor = previous.get(lane, -1)
            lane_bounds[j, 3] = predecessor
            if predecessor >= 0:
                lane_bounds[predecessor, 0] = j
            previous[lane] = j
    # The earliest planned late-Great hit. perfect_window plans it 1 ms past the latest Perfect (in float32, one step
    # under the band's own encoding on most notes; kept as built). frame_robust's latest Perfect ends a margin early and
    # the hits between are judged by the frame, so its late Greats start at the band itself, encoded as the
    # materializer reads it (fill_crossing.exact_label_hit_intervals).
    if mode == "frame_robust":
        late_great_floor = _envelope_sec(ts, late_great_low)
    else:
        late_great_floor = perfect_candidates + np.float32(0.001)
    # The latest fever cutoff that note j and every later note can still be hit at or past (a fever ending early):
    # their latest Perfect hits, under frame_robust a full exit gap earlier (a note is out at every frame timing only
    # from the fever's end + the margin), rounded down to float32.
    exit_ceiling = latest_perfect_schedule.astype(np.float64)
    if mode == "frame_robust":
        exit_ceiling = exit_ceiling - 2.0 * FRAME_MARGIN_MS / 1000.0
    exit_ceiling32 = exit_ceiling.astype(np.float32)
    overshot = exit_ceiling32.astype(np.float64) > exit_ceiling
    exit_ceiling32[overshot] = np.nextafter(exit_ceiling32[overshot], np.float32(-np.inf))
    return Envelopes(
        perfect_candidates=perfect_candidates,
        perfect_floor=perfect_floor,
        great_floor=great_floor,
        great_candidates=great_candidates,
        late_great_floor=late_great_floor,
        exit_ceiling=np.ascontiguousarray(np.minimum.accumulate(exit_ceiling32[::-1])[::-1]),
        lane_bounds=lane_bounds,
    )


def fever_window_times(last_note_time: float, time_factors: np.ndarray, mode: str) -> np.ndarray:
    """Per Fever Time factor (the float32 curve values), how long a planned fever window extends past its activation
    press, in float64 seconds: the game's fever time, (last note time x 0.15 + 0.15) x the factor; under frame_robust
    FRAME_MARGIN_MS shorter, the longest offset at which a note is in fever at every frame timing."""
    real = np.maximum(
        (float(last_note_time) * FEVER_TIME_PER_SECOND + FEVER_TIME_OFFSET)
        * np.asarray(time_factors, dtype=np.float32).astype(np.float64),
        0.0,
    )
    return np.maximum(real - FRAME_MARGIN_MS / 1000.0, 0.0) if mode == "frame_robust" else real


def _bezier(a: float, b: float, c: float, d: float, t: float) -> float:
    u = 1.0 - t
    return u * u * u * a + 3 * t * u * u * b + 3 * t * t * u * c + t * t * t * d


def _eased(x2: float, y2: float, x3: float, y3: float, pct: float) -> float:
    """CurveUtil BezierDist (BezierDist.lua): the Bezier (0,0) (x2,y2) (x3,y3) (1,1) at `pct` of its arc length, measured
    over 10 segments (the same arithmetic as tools/verify/game_sim.py)."""
    ts, dists = [0.0], [0.0]
    t = dist = px = py = 0.0
    for _ in range(10):
        t += 1.0 / 10
        cx, cy = _bezier(0, x2, x3, 1, t), _bezier(0, y2, y3, 1, t)
        dist += math.hypot(cx - px, cy - py)
        ts.append(t)
        dists.append(dist)
        px, py = cx, cy
    v = min(max(dist * pct, 0.0), dist)
    if v == dist:
        return _bezier(0, y2, y3, 1, 1.0)
    lo, hi = 0, 10
    while hi - lo > 1:
        mid = lo + (hi - lo) // 2
        lo, hi = (mid, hi) if dists[mid] < v else (lo, mid)
    return _bezier(0, y2, y3, 1, ts[lo] + (ts[lo + 1] - ts[lo]) * ((v - dists[lo]) / (dists[lo + 1] - dists[lo])))


@lru_cache(maxsize=None)
def _game_fever_fill_factor(points: int) -> float:
    """The game's fill curve at `points` (0..MAX_STAT) gear points: GearStats f_N(0.6, 0.5, 0.333, 0.166, 0.1, points),
    the exact double the exported Stats.txt factor truncates."""

    def pct(x1: int, x2: int) -> float:
        slope = (0 - 1) / (x1 - x2)
        return slope * points + (0 - slope * x1)

    def lerp(a: float, b: float, t: float) -> float:
        return (b - a) * t + a

    if points == 0:
        return 0.333
    if points < 40:
        return lerp(0.333, 0.166, _eased(0, 0.4, 0.7, 0.9, pct(0, 40)))
    if points > 80:
        return lerp(0.1, 0.1 + (0.1 - 0.166) * 0.35, _eased(0, 0.5, 0.6, 1, pct(80, 160)))
    return lerp(0.166, 0.1, _eased(0.2, 0.1, 0.4, 1, pct(40, 80)))


# A fill this close to a whole (or, for Great half-fills, half) number of Perfects is decided by the game's double sum.
_FILL_BOUNDARY = 1e-6


@lru_cache(maxsize=4096)
def _frame_robust_fever_fills(hit_objects: int, points: int) -> tuple[float, ...]:
    fills = []
    for ff in range(points):
        fill = float(hit_objects) * _game_fever_fill_factor(ff)
        whole = round(fill)
        if fill > 0.0 and abs(fill - whole) < _FILL_BOUNDARY:
            bar, step = 0.0, 1.0 / fill
            for _ in range(whole):
                bar = min(bar + step, 1.0)
            fill = whole - 0.5 if bar >= 1.0 else whole + 0.5
        fills.append(fill)
    return tuple(fills)


def fever_fill_raw(hit_objects: int, fill_factors: np.ndarray, mode: str) -> np.ndarray:
    """Per Fever Fill Rate point, the fever fill in Perfects (float64; its ceil is the Perfects that fill the bar): hit
    objects (notes - long notes) x FEVER_FILL_PER_NOTE x the exported float32 factor. frame_robust fills as the game does
    (T6): its double bar adds 1 / (hit objects x the curve value) per Perfect and activates at >= 1, so at a whole
    denominator the sum can end one ulp short and the game needs one more Perfect; there the fill is the game's count
    less half a Perfect (fever_fill_is_order_sensitive)."""
    factors = np.asarray(fill_factors, dtype=np.float32).astype(np.float64)
    if mode != "frame_robust":
        return float(hit_objects) * FEVER_FILL_PER_NOTE * factors
    game = [_game_fever_fill_factor(ff) for ff in range(len(factors))]
    if not np.allclose(FEVER_FILL_PER_NOTE * factors, game, rtol=1e-6, atol=0.0):
        raise ValueError("timing_envelope: Stats.txt's Fever Fill Rate no longer matches the game curve frame_robust ports")
    return np.asarray(_frame_robust_fever_fills(int(hit_objects), len(factors)), dtype=np.float64)


def fever_fill_is_order_sensitive(fill: float) -> bool:
    """Whether a fill sits on a half-Perfect boundary: Great half-fills can reach it exactly, and whether the game's double
    sum then activates depends on the order of the adds, so frame_robust plans no Force Greats there."""
    return abs(2.0 * fill - round(2.0 * fill)) < _FILL_BOUNDARY


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
    under zero_ms. perfect_window and frame_robust add the per-note Perfect/Great candidate and floor envelopes that
    make FG carry-aware; zero_ms has none (every hit lands at its hit time).
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
    lane_bounds: np.ndarray | None = None

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
            self.cache_mode,
            self.baseline_hash,
            0,
        )

    @property
    def cache_mode(self) -> str:
        """The timing mode as the frontier cache keys name it, with its revision (CACHE_REVISIONS)."""
        revision = CACHE_REVISIONS.get(self.mode)
        return self.mode if revision is None else f"{self.mode}@{revision}"


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
            mode=timing_mode,
            baseline_hash="",
            hit_timestamps=chart_ts,
            **perfect_window_envelopes(chart_ts, chart.note_types, timing_mode, lanes=chart.lanes)._asdict(),
        )
    with _TIMED_SONG_CACHE_LOCK:
        _TIMED_SONG_CACHE[cache_key] = song
    return song
