"""game_sim.py -- ONE faithful full-pipeline RoBeats simulator (pure Python, no Babylon).

This is the game-truth harness: unlike ``reference_oracle`` (which replays a PRE-RESOLVED
one-event-per-note stream), this tool implements BOTH halves of the real client and runs them
frame-by-frame like ``game.ts``:

  * MODEL A -- INPUT / NOTE MATCHING (``NoteSim``): the per-lane earliest-hittable-first press/
    release consumption loop (NoteSystem.pressLane/releaseLane/update), the +200ms time-miss/despawn
    removal, and the judge-window comparator (late edge INCLUSIVE, early edge EXCLUSIVE). A press is
    RESOLVED against the live active-note list -- it is NOT pre-mapped to a note.

  * MODEL B -- FILL / FEVER / SCORE (``GameScoreEngine``): a faithful port of the reference
    ``ScoreEngine`` (``tools/verify/reference_oracle/score_bundle.mjs``): the gear ``fN`` stat curves, per-note points,
    two-color colorPointBonus, continuous combo multiplier, fever fill/drain/decay, the AUTO
    activation gate, and the ``wastedFillPending`` "wasted note" after a fever window closes.

  * FRAME DRIVER (``simulate``): steps ``chartMs`` in fixed ``dt`` frames and, each frame, runs
    ``feverTick`` -> note ``update`` (time-misses) -> lane presses -> lane releases, exactly in the
    ``game.ts`` tick order. Fever activation and time-drain are therefore FRAME-granular (not
    input-granular like the oracle) -- this is what makes the score game-exact rather than
    oracle-approximate.

INPUT (two equivalent front-ends, both resolved through Model A):
  (1) a raw PRESS SEQUENCE  -- list of Press(lane, press_time_ms, is_release), or
  (2) an intended per-note TRACE -- list of IntendedNote(hit_time_ms, result, note_type, lane,
      delta_ms); the tool converts each to a physical press (head/tap at hit+delta) and, for holds,
      a release at tail_hit+delta, then resolves them through the SAME Model-A matcher.

Chart: NoteChart(timestamps_ms, lanes, note_types) with note_type 1=tap, 2=hold head, 3=hold tail.
Loadout: a WebPort raw-point statsdict + 0..2 color-stat keys (as ``loadout_oracle_replay`` builds).

RETURNS SimResult: game score, per-note (registered result, hit time, fever flag), fever sections,
tally, maxCombo.

VALIDATION GATE (``--validate``):
  * 4x-perfect trivial case reproduces the WebPort oracle's 2056.
  * Driving it with the note_graph intended timing for the Aurora served loadout
    (.calc/aurora_fix.db #1) reproduces the user's gameplay-engine 47,317,114 (+-0.05%).
"""
from __future__ import annotations

import argparse
import bisect
import glob
import json
import math
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ============================================================================================
# MODEL B -- gear stat curves (faithful port of the reference score bundle)
# ============================================================================================


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def _y_for_2pt_line(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    slope = (y1 - y2) / (x1 - x2)
    return slope * x + (y1 - slope * x1)


def _bezier1d(a: float, b: float, c: float, d: float, t: float) -> float:
    u = 1.0 - t
    return u * u * u * a + 3 * t * u * u * b + 3 * t * t * u * c + t * t * t * d


class _BezierDist:
    """CurveUtil BezierDist: arc-length reparametrised 1-D Bezier (BezierDist.lua)."""

    def __init__(self, x1, y1, x2, y2, x3, y3, x4, y4, segments: int = 10):
        self._y1, self._y2, self._y3, self._y4 = y1, y2, y3, y4
        self.ts = [0.0]
        self.dists = [0.0]
        t = 0.0
        dist = 0.0
        px, py = x1, y1
        for _ in range(1, segments + 1):
            t += 1.0 / segments
            cx = _bezier1d(x1, x2, x3, x4, t)
            cy = _bezier1d(y1, y2, y3, y4, t)
            dist += math.hypot(cx - px, cy - py)
            self.ts.append(t)
            self.dists.append(dist)
            px, py = cx, cy
        self.total = dist

    def _bracket(self, target: float) -> int:
        lo, hi = 0, len(self.dists) - 1
        while hi - lo > 1:
            mid = lo + (hi - lo) // 2
            if self.dists[mid] < target:
                lo = mid
            else:
                hi = mid
        return lo

    def _t_for_distance(self, d: float) -> float:
        v = _clamp(d, 0.0, self.total)
        if v == self.total:
            return 1.0
        i = self._bracket(v)
        d0 = self.dists[i]
        return self.ts[i] + (self.ts[i + 1] - self.ts[i]) * ((v - d0) / (self.dists[i + 1] - d0))

    def y_for_distance_pct(self, pct: float) -> float:
        return _bezier1d(self._y1, self._y2, self._y3, self._y4, self._t_for_distance(self.total * pct))


_EASE_NEG_40_0 = _BezierDist(0, 0, 0.4, 0.1, 1, 0.8, 1, 1)
_EASE_NEG_80_40 = _BezierDist(0, 0, 0.8, 0, 0.9, 0.8, 1, 1)
_EASE_0_40 = _BezierDist(0, 0, 0, 0.4, 0.7, 0.9, 1, 1)
_EASE_40_80 = _BezierDist(0, 0, 0.2, 0.1, 0.4, 1, 1, 1)
_EASE_80_160 = _BezierDist(0, 0, 0, 0.5, 0.6, 1, 1, 1)


def _lerp(a: float, b: float, t: float) -> float:
    return (b - a) * t + a


def _fN(aN80, aN40, a0, a40, a80, stat) -> float:
    """GearStats.f_N -- the 5-knot eased stat curve over gear points clamped to [-80,160]."""
    s = _clamp(stat, -80, 160)
    if s > 0:
        if s < 40:
            v = _lerp(a0, a40, _EASE_0_40.y_for_distance_pct(_y_for_2pt_line(0, 0, 40, 1, s)))
        elif s > 80:
            v = _lerp(a80, a80 + (a80 - a40) * 0.35, _EASE_80_160.y_for_distance_pct(_y_for_2pt_line(80, 0, 160, 1, s)))
        else:
            v = _lerp(a40, a80, _EASE_40_80.y_for_distance_pct(_y_for_2pt_line(40, 0, 80, 1, s)))
    elif s < 0:
        if s > -40:
            v = _lerp(aN40, a0, _EASE_NEG_40_0.y_for_distance_pct(_y_for_2pt_line(-40, 0, 0, 1, s)))
        else:
            v = _lerp(aN80, aN40, _EASE_NEG_80_40.y_for_distance_pct(_y_for_2pt_line(-80, 0, -40, 1, s)))
    else:
        v = a0
    return v if math.isfinite(v) else a0


_GEAR_STAT_TYPES = (
    "ColorBlue", "ColorGreen", "ColorPurple", "ColorRed", "ColorOrange",
    "NoteSpeed", "PerfectTime", "PerfectPoints", "GreatTime", "GreatPoints",
    "OkayTime", "OkayPoints", "ComboThreshold", "ComboMultiplier", "ComboBreakMultiplier",
    "FeverFillRate", "FeverMultiplier", "FeverTime", "FeverDrainRate",
)


def _statsdict_from(partial: dict) -> dict:
    out = {k: 0 for k in _GEAR_STAT_TYPES}
    for k, v in (partial or {}).items():
        if k not in out:
            raise ValueError(f"gearStats: unknown stat {k!r} (valid: {', '.join(_GEAR_STAT_TYPES)})")
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"gearStats: stat {k!r} is not a finite number ({v})")
        out[k] = v
    return out


def _perfect_points(s):  # noqa: ANN001
    return math.floor(_fN(50, 100, 200, 350, 450, s["PerfectPoints"]))


def _great_points(s):
    return math.floor(_fN(35, 75, 150, 225, 300, s["GreatPoints"]))


def _okay_points(s):
    return math.floor(_fN(25, 50, 100, 150, 200, s["OkayPoints"]))


def _combo_thresholds(s):
    v = _fN(600, 450, 100, 20, 10, s["ComboThreshold"])
    return [math.floor(v * 0.25), math.floor(v * 0.5), v]


def _combo_multipliers(s):
    v = _fN(0, 0.25, 1, 1.4, 1.6, s["ComboMultiplier"])
    return [1 + v * 0.25, 1 + v * 0.5, 1 + v]


def _continuous_combo_multiplier(s, combo):
    t1, t2, t3 = _combo_thresholds(s)
    m1, m2, m3 = _combo_multipliers(s)
    if combo <= t1:
        return _y_for_2pt_line(0, 1, t1, m1, combo)
    if combo <= t2:
        return _y_for_2pt_line(t1, m1, t2, m2, combo)
    if combo <= t3:
        return _y_for_2pt_line(t2, m2, t3, m3, combo)
    return m3


def _fever_decay_rate(s):
    return _fN(0, 0.05, 0.15, 0.35, 0.4, s["FeverTime"])


def _fever_miss_drain_pct(s):
    return _fN(0.5, 0.25, 0.1, 0.01, 0, s["FeverDrainRate"])


def _fever_fill_scales(s):
    v = _fN(0.6, 0.5, 0.333, 0.166, 0.1, s["FeverFillRate"])
    return {"perfect": v, "great": v * 2}


def _fever_multiplier(s):
    return _fN(1, 1.25, 3, 4.75, 5.25, s["FeverMultiplier"])


def _combo_break_multiplier(s):
    return _fN(0, 0.1, 0.5, 0.9, 1, s["ComboBreakMultiplier"])


def _chain_after_break(s, chain):
    return math.floor(_combo_break_multiplier(s) * chain)


def _color_point_bonus(s, result, colors):
    if not colors:
        return (0, 0)
    if len(colors) == 1:
        f = 3 if result == "perfect" else 2 if result == "great" else 1 if result == "okay" else 0
        return (math.floor(f * s[colors[0]]), 0)
    if result == "perfect":
        f1, f2 = 2.0, 1.0
    elif result == "great":
        f1, f2 = 4.0 / 3.0, 2.0 / 3.0
    elif result == "okay":
        f1, f2 = 2.0 / 3.0, 1.0 / 3.0
    else:
        f1 = f2 = 0.0
    return (math.floor(f1 * s[colors[0]]), math.floor(f2 * s[colors[1]]))


_DRAIN_WEIGHT = {"perfect": 0.0, "great": 0.0, "okay": 0.25, "miss": 1.0}
_FEVER_ACTIVATE_AT = 1.0


class GameScoreEngine:
    """Faithful port of the reference score bundle's ScoreEngine.

    ``manualFever`` defaults False (AUTO) to match the replay/meta-sim path -- fever fires the frame
    the bar fills. Frame granularity is supplied by the driver via ``feverTick(dt)``.
    """

    def __init__(self, cfg: dict, stats: dict, colors: list[str]):
        self.cfg = cfg
        self.stats = stats
        self.colors = colors
        self.score = 0
        self.chain = 0
        self.maxChain = 0
        self.feverBar = 0.0
        self.feverActive = False
        self.manualFever = False
        self.tally = {"perfect": 0, "great": 0, "okay": 0, "miss": 0}
        self.whiffPenalties = 0
        self.localNoteCount = 0
        self.feverHits = 0
        self.powerbarNotes = 0
        self.wastedFillPending = False
        fill = _fever_fill_scales(stats)
        self.feverFillDenom = cfg["hitObjectsCount"] * fill["perfect"]
        self.greatFillDenom = cfg["hitObjectsCount"] * fill["great"]
        # The engine tick cancels in event-time drain math; it is not extra fever duration.
        self.feverTimeSec = cfg["lastNoteTimeSec"] * 0.15 * (_fever_decay_rate(stats) / 0.15)
        self.feverMult = _fever_multiplier(stats)
        self.missDrainPct = _fever_miss_drain_pct(stats)
        self.basePoints = {
            "perfect": _perfect_points(stats),
            "great": _great_points(stats),
            "okay": _okay_points(stats),
            "miss": 0,
        }

    def _fever_fill(self, result):
        if self.feverFillDenom <= 0:
            return 0.0
        if result == "perfect":
            return 1.0 / self.feverFillDenom
        if result == "great":
            return 1.0 / self.greatFillDenom
        return 0.0

    def register_hit(self, result, kind="note"):
        """score_bundle.mjs ScoreEngine.registerHit -- returns (points, counted)."""
        if self.feverActive:
            self.feverBar = _clamp(self.feverBar - self.missDrainPct * _DRAIN_WEIGHT[result])
        elif self.wastedFillPending:
            self.wastedFillPending = False
        else:
            self.feverBar = _clamp(self.feverBar + self._fever_fill(result))
            if (not self.manualFever) and self.feverBar >= _FEVER_ACTIVATE_AT:
                self.feverActive = True
                self.powerbarNotes = 0
        self.maxChain = max(self.chain, self.maxChain)
        counted = True
        if result in ("perfect", "great"):
            self.chain += 1
            self.tally[result] += 1
            self.localNoteCount += 1
        elif result == "okay":
            self.tally["okay"] += 1
            self.localNoteCount += 1
        else:  # miss
            if self.chain > 0:
                self.chain = _chain_after_break(self.stats, self.chain)
            elif kind != "note":
                counted = False
            if counted:
                self.tally["miss"] += 1
                if kind != "note":
                    self.whiffPenalties += 1
                else:
                    self.localNoteCount += 1
        c1, c2 = _color_point_bonus(self.stats, result, self.colors)
        base = self.basePoints[result] + c1 + c2
        chain_mult = _continuous_combo_multiplier(self.stats, self.chain)
        fever_mult = self.feverMult if self.feverActive else 1.0
        points = math.floor(base * chain_mult * fever_mult)
        if not counted:
            return (points, counted)
        self.score += points
        if result != "miss":
            self.powerbarNotes += 1
            if self.feverActive:
                self.feverHits += 1
        return (points, counted)

    def fever_tick(self, dt_seconds, trigger_pressed=False):
        """Per-frame power-bar integration + AUTO activation gate (score_bundle.mjs:328)."""
        if self.feverActive:
            self.feverBar -= dt_seconds / self.feverTimeSec
            if self.feverBar <= 0:
                self.feverBar = 0.0
                self.feverActive = False
                self.wastedFillPending = True
            return
        self.powerbarNotes = 0
        if self.feverBar >= _FEVER_ACTIVATE_AT and ((not self.manualFever) or trigger_pressed):
            self.feverActive = True
            self.powerbarNotes = 1

    def combo_multiplier(self):
        return _continuous_combo_multiplier(self.stats, self.chain)

    def max_combo(self):
        return max(self.maxChain, self.chain)

    def fever_percentage(self):
        return self.feverHits / self.localNoteCount if self.localNoteCount > 0 else 0.0


# ============================================================================================
# MODEL A -- input / note matching from the independent reference model
# ============================================================================================

_JUDGE_EDGES_TAP = (430, 190, 40, -20, -95, -235)
_JUDGE_EDGES_TAIL = tuple(e * 2 for e in _JUDGE_EDGES_TAP)
_NOTE_REMOVE_MS = 200  # a note time-misses at now - hit > 200 (Constants.lua NOTE_REMOVE_TIME=-200)


def _judge_with_edges(delta, edges):
    okay_late, great_late, perfect_late, perfect_early, great_early, okay_early = edges
    if delta > okay_late:
        return "miss"
    if delta > great_late:
        return "okay"
    if delta > perfect_late:
        return "great"
    if delta > perfect_early:
        return "perfect"
    if delta > great_early:
        return "great"
    if delta > okay_early:
        return "okay"
    return "miss"


def _judge_tap(delta):
    return _judge_with_edges(delta, _JUDGE_EDGES_TAP)


def _judge_tail(delta):
    return _judge_with_edges(delta, _JUDGE_EDGES_TAIL)


# HeldNoteState (noteSystem.ts HState): Pre=0, Holding=1, HoldMissed=2, Passed=3.
_PRE, _HOLDING, _HOLD_MISSED, _PASSED = 0, 1, 2, 3


@dataclass
class NoteChart:
    """A resolved chart: parallel arrays over note_index. note_type 1=tap, 2=head, 3=tail.

    Holds are represented in the source chart as a (head, tail) pair of consecutive note_types
    2 then 3 in the SAME lane. ``build_holds`` folds each (2,3) pair into one active hold whose
    head hit = head timestamp and tail hit = tail timestamp, exactly as NoteSystem.spawn does
    (note.endMs). The tail index is kept as its own scored event (the note_graph indexes it).
    """

    timestamps_ms: list[float]
    lanes: list[int]
    note_types: list[int]


@dataclass
class _ActiveNote:
    note_index: int  # head/tap index
    lane: int
    hit_ms: float
    is_hold: bool
    tail_hit_ms: float
    tail_index: int  # for holds: the note_index of the tail event (for graph attribution)
    state: int = _PRE
    consumed: bool = False  # tap head registered
    did_trigger_head: bool = False
    did_trigger_tail: bool = False


@dataclass
class RegisteredHit:
    note_index: int
    result: str
    hit_time_ms: float  # the IDEAL note time recorded for the graph (head time or tail time)
    press_ms: float
    fever: bool
    is_tail: bool
    kind: str = "note"  # note | whiff | earlyRelease


class NoteSim:
    """Model A: per-lane earliest-hittable-first press/release consumption + time-miss removal.

    Mirrors NoteSystem: an ascending-index (== chart/spawn order) active list; a press takes the
    FIRST hittable note in that lane and stops; a release finalises the first Holding/HoldMissed
    note in that lane. Notes leave the list at hit/tail + 200ms (time-miss).
    """

    def __init__(self, chart: NoteChart, prebuffer_ms: float = 1500.0):
        self.chart = chart
        self.prebuffer_ms = prebuffer_ms
        self.active: list[_ActiveNote] = []
        # Build spawn schedule: one _ActiveNote per tap and per hold (head), tails folded in.
        # A hold head (type 2) pairs with the NEXT type-3 tail in the SAME lane (heads/tails
        # interleave with other notes in note-index order; they are not adjacent). We consume each
        # tail exactly once so nested/parallel holds in a lane pair FIFO (head order == tail order).
        self._spawn_plan: list[tuple[float, _ActiveNote]] = []  # (spawn_ms, note) sorted by spawn
        n = len(chart.note_types)
        pending_tail_by_lane: dict[int, list[int]] = {}
        for j in range(n):
            if chart.note_types[j] == 3:
                pending_tail_by_lane.setdefault(chart.lanes[j], []).append(j)
        tail_ptr: dict[int, int] = {lane: 0 for lane in pending_tail_by_lane}
        claimed_tails: set[int] = set()
        for i in range(n):
            nt = chart.note_types[i]
            if nt == 1:  # tap
                an = _ActiveNote(
                    note_index=i, lane=chart.lanes[i], hit_ms=float(chart.timestamps_ms[i]),
                    is_hold=False, tail_hit_ms=float(chart.timestamps_ms[i]), tail_index=i,
                )
                self._spawn_plan.append((an.hit_ms - prebuffer_ms, an))
            elif nt == 2:  # hold head -> next unclaimed type-3 tail in the same lane
                lane = chart.lanes[i]
                tails = pending_tail_by_lane.get(lane, [])
                ptr = tail_ptr.get(lane, 0)
                while ptr < len(tails) and (tails[ptr] in claimed_tails or tails[ptr] < i):
                    ptr += 1
                if ptr >= len(tails):
                    raise ValueError(f"hold head at index {i} (lane {lane}) has no following type-3 tail")
                tail_index = tails[ptr]
                claimed_tails.add(tail_index)
                tail_ptr[lane] = ptr + 1
                head_ms = float(chart.timestamps_ms[i])
                tail_ms = float(chart.timestamps_ms[tail_index])
                an = _ActiveNote(
                    note_index=i, lane=lane, hit_ms=head_ms,
                    is_hold=True, tail_hit_ms=tail_ms, tail_index=tail_index,
                )
                self._spawn_plan.append((head_ms - prebuffer_ms, an))
            elif nt == 3:  # tail: folded into its head above
                continue
            else:
                raise ValueError(f"unknown note_type {nt} at index {i}")
        self._spawn_plan.sort(key=lambda p: (p[0], p[1].note_index))
        self._spawn_cursor = 0

    def update(self, chart_ms: float) -> list[RegisteredHit]:
        """Spawn due notes; return time-miss events (head/tap and tail misses) this frame."""
        # spawn
        while (
            self._spawn_cursor < len(self._spawn_plan)
            and self._spawn_plan[self._spawn_cursor][0] <= chart_ms
        ):
            self.active.append(self._spawn_plan[self._spawn_cursor][1])
            self._spawn_cursor += 1

        missed: list[RegisteredHit] = []
        # iterate a copy of indices high->low so removal is safe (NoteSystem walks i high->low)
        for idx in range(len(self.active) - 1, -1, -1):
            a = self.active[idx]
            if not a.is_hold:
                if not a.consumed and chart_ms - a.hit_ms > _NOTE_REMOVE_MS:
                    missed.append(RegisteredHit(a.note_index, "miss", a.hit_ms, chart_ms, False, False))
                    self.active.pop(idx)
                continue
            # hold: head time-miss Pre -> HoldMissed at hit+200 (head miss scored)
            if a.state == _PRE and chart_ms - a.hit_ms > _NOTE_REMOVE_MS:
                a.state = _HOLD_MISSED
                missed.append(RegisteredHit(a.note_index, "miss", a.hit_ms, chart_ms, False, False))
            # despawn at tail+200; unhit tail scores a tail miss
            if chart_ms - a.tail_hit_ms > _NOTE_REMOVE_MS:
                if not a.did_trigger_tail:
                    missed.append(RegisteredHit(a.tail_index, "miss", a.tail_hit_ms, chart_ms, False, True))
                self.active.pop(idx)
        return missed

    def press_lane(self, lane: int, chart_ms: float) -> RegisteredHit | None:
        """The EARLIEST hittable note in this lane, chart order (NoteSystem.pressLane)."""
        for idx in range(len(self.active)):
            a = self.active[idx]
            if a.lane != lane:
                continue
            if not a.is_hold:
                if a.consumed:
                    continue
                result = _judge_tap(chart_ms - a.hit_ms)
                if result == "miss":
                    continue
                self.active.pop(idx)
                return RegisteredHit(a.note_index, result, a.hit_ms, chart_ms, False, False)
            if a.state == _PRE:
                result = _judge_tap(chart_ms - a.hit_ms)
                if result == "miss":
                    continue
                a.state = _HOLDING
                a.did_trigger_head = True
                return RegisteredHit(a.note_index, result, a.hit_ms, chart_ms, False, False)
            if a.state == _HOLD_MISSED:
                result = _judge_tail(chart_ms - a.tail_hit_ms)
                if result == "miss":
                    continue
                a.state = _PASSED
                a.did_trigger_tail = True
                return RegisteredHit(a.tail_index, result, a.tail_hit_ms, chart_ms, False, True)
        return None

    def release_lane(self, lane: int, chart_ms: float) -> RegisteredHit | None:
        """Finalise the first Holding/HoldMissed note in this lane (NoteSystem.releaseLane)."""
        for a in self.active:
            if not a.is_hold or a.lane != lane:
                continue
            if a.state not in (_HOLDING, _HOLD_MISSED):
                continue
            result = _judge_tail(chart_ms - a.tail_hit_ms)
            if result == "miss":
                if a.state == _HOLD_MISSED:
                    continue
                a.state = _HOLD_MISSED  # early release -> recoverable
                return RegisteredHit(a.tail_index, "miss", chart_ms, chart_ms, False, False, kind="earlyRelease")
            a.state = _PASSED
            a.did_trigger_tail = True
            return RegisteredHit(a.tail_index, result, a.tail_hit_ms, chart_ms, False, True)
        return None

    @property
    def active_count(self) -> int:
        return len(self.active)

    @property
    def spawned_all(self) -> bool:
        return self._spawn_cursor >= len(self._spawn_plan)


# ============================================================================================
# FRAME DRIVER -- game.ts tick order
# ============================================================================================


@dataclass
class Press:
    """One physical input edge. is_release=False => a lane press; True => a lane release."""

    lane: int
    time_ms: float
    is_release: bool = False


@dataclass
class SimResult:
    score: int
    tally: dict
    max_combo: int
    fever_hits: int
    fever_percentage: float
    fever_mult: float
    fever_time_sec: float
    fever_fill_denom: float
    registered: list[RegisteredHit] = field(default_factory=list)
    fever_sections: list[dict] = field(default_factory=list)


def simulate(
    chart: NoteChart,
    statsdict: dict,
    colors: list[str],
    presses: list[Press],
    config: dict,
    frame_dt_ms: float = 1000.0 / 60.0,
    manual_fever: bool = False,
) -> SimResult:
    """Full-pipeline sim: FRAME-integrated fever + EXACT-time input matching (game.ts semantics).

    RESOLUTION MODEL. The RoBeats client polls input each render frame, but a lane edge carries the
    UserInputService sub-frame timestamp; the judge sees that exact input time (Note.get_delta_time
    reads the audio clock at the input, not the frame boundary), while the power bar DECAYS
    continuously (integrated per render frame). We reproduce both:

      * fever activation + time-drain integrate over FRAMES of ``frame_dt_ms`` (feverTick), so
        which notes fall inside an active window is frame-granular -- and, crucially, a sub-frame
        ``feverTick`` is also applied right up to each input's exact time before it is judged, so
        the bar value at the hit is exact (this is what fixes the wasted-fill / activation-note
        edge cases without frame-snapping the JUDGMENT).
      * note MATCHING + JUDGMENT run at the input's EXACT time (press_lane/release_lane receive the
        exact press ms), so a witness Perfect at +36.6ms is not snapped past the +40 Perfect edge
        into a Great. Time-miss removal (notes.update) runs on the frame clock (a note times out on
        a frame, matching the client's per-frame HeldNote/Note update).

    ``presses`` is the resolved physical input edge list; each is matched earliest-hittable-first.
    """
    stats = _statsdict_from(statsdict)
    engine = GameScoreEngine(config, stats, colors)
    engine.manualFever = manual_fever
    notes = NoteSim(chart)

    ordered = sorted(enumerate(presses), key=lambda kv: (kv[1].time_ms, kv[1].is_release, kv[0]))
    press_times = [p.time_ms for _, p in ordered]
    pcursor = 0

    registered: list[RegisteredHit] = []
    fever_sections: list[dict] = []
    cur_section: dict | None = None
    was_fever = False

    last_ts = max(chart.timestamps_ms) if chart.timestamps_ms else 0.0
    last_press = press_times[-1] if press_times else 0.0
    end_ms = max(last_ts, last_press) + _NOTE_REMOVE_MS + 3 * frame_dt_ms
    start_ms = min((sp for sp, _ in notes._spawn_plan), default=0.0)

    # Continuous fever clock, advanced by frame ticks AND sub-frame right up to each input.
    fever_clock_ms = start_ms

    def advance_fever_to(target_ms: float):
        nonlocal fever_clock_ms
        dt = (target_ms - fever_clock_ms) / 1000.0
        if dt > 0:
            engine.fever_tick(dt, False)
            fever_clock_ms = target_ms

    def record_section_edge(now_ms: float):
        nonlocal cur_section, was_fever
        if engine.feverActive and not was_fever:
            cur_section = {"activationMs": now_ms, "endMs": None, "noteCount": 0}
        if (not engine.feverActive) and was_fever and cur_section is not None:
            cur_section["endMs"] = now_ms
            fever_sections.append(cur_section)
            cur_section = None
        was_fever = engine.feverActive

    def count_fever_note(result: str, counted: bool):
        if engine.feverActive and cur_section is not None and result != "miss" and counted:
            cur_section["noteCount"] += 1

    def do_press(p: Press, now_ms: float):
        # sub-frame fever advance to the exact input time (bar decay is continuous), THEN judge.
        advance_fever_to(now_ms)
        record_section_edge(now_ms)
        if not p.is_release:
            hit = notes.press_lane(p.lane, now_ms)
            if hit is not None:
                _pts, counted = engine.register_hit(hit.result, "note")
                hit.fever = engine.feverActive  # fever AFTER the hit (fill may have activated it)
                registered.append(hit)
                record_section_edge(now_ms)
                count_fever_note(hit.result, counted)
            elif engine.chain > 0:
                engine.register_hit("miss", "whiff")
                record_section_edge(now_ms)
        else:
            tail = notes.release_lane(p.lane, now_ms)
            if tail is not None:
                if tail.kind == "earlyRelease" and engine.chain <= 0:
                    return  # idle early release: complete no-op (recoverable later)
                _pts, counted = engine.register_hit(tail.result, tail.kind)
                tail.fever = engine.feverActive
                registered.append(tail)
                record_section_edge(now_ms)
                count_fever_note(tail.result, counted)

    chart_ms = start_ms
    while chart_ms <= end_ms:
        # 1) frame fever tick (activation gate + time drain) up to this frame boundary.
        advance_fever_to(chart_ms)
        record_section_edge(chart_ms)

        # 2) time-miss registrations on the frame clock
        for m in notes.update(chart_ms):
            advance_fever_to(m.press_ms)
            m.fever = engine.feverActive
            engine.register_hit("miss", "note")
            registered.append(m)
            record_section_edge(m.press_ms)

        # 3) all inputs whose exact time is within this frame [prev, chart_ms], in input order,
        #    each judged at its EXACT time (sub-frame fever advance handled inside do_press).
        while pcursor < len(ordered) and press_times[pcursor] <= chart_ms:
            _, p = ordered[pcursor]
            pcursor += 1
            do_press(p, p.time_ms)

        if notes.spawned_all and notes.active_count == 0 and pcursor >= len(ordered) and chart_ms > last_ts:
            break
        chart_ms += frame_dt_ms

    if cur_section is not None:
        cur_section["endMs"] = fever_clock_ms
        cur_section["stillActiveAtSongEnd"] = engine.feverActive
        fever_sections.append(cur_section)

    return SimResult(
        score=engine.score,
        tally=dict(engine.tally),
        max_combo=engine.max_combo(),
        fever_hits=engine.feverHits,
        fever_percentage=engine.fever_percentage(),
        fever_mult=engine.feverMult,
        fever_time_sec=engine.feverTimeSec,
        fever_fill_denom=engine.feverFillDenom,
        registered=registered,
        fever_sections=fever_sections,
    )


# ============================================================================================
# INTENDED-TRACE FRONT-END: resolve an intended per-note (result, hit_time) trace into presses
# ============================================================================================


# A note_graph "Great selector" (delta_ms is None) declares the note IS a Great but carries no
# timing witness. Order-sensitive same-time selectors are expected to be materialized by
# note_graph.py with an explicit early/late offset; only the remaining order-neutral selectors reach
# this fallback. To make the Model-A matcher re-judge those presses to "great", synthesize the
# smallest-cushion late-Great edge (perfect_late + 1ms), staying strictly inside
# (perfect_late, great_late].
_CANONICAL_GREAT_OFFSET_TAP_MS = _JUDGE_EDGES_TAP[2] + 1.0   # 41 ms  (perfect_late 40 + 1)
_CANONICAL_GREAT_OFFSET_TAIL_MS = _JUDGE_EDGES_TAIL[2] + 1.0  # 81 ms  (tail perfect_late 80 + 1)


@dataclass
class IntendedNote:
    """An intended play of one note: press it so that it judges to ``result`` at ``hit_time_ms``.

    ``delta_ms`` is the intended timing offset (physical press = hit_time_ms + delta) for a WITNESS
    note; ``None`` means the note_graph gave no timing witness (a Great selector or a comfortable
    Perfect) -- ``presses_from_intended`` then synthesizes an offset that reproduces ``result`` under
    the real judge windows. For holds the head is pressed at head+delta and released at tail+(its own
    delta). ``note_type``: 1=tap, 2=head, 3=tail. ``result`` is the AUTHORITATIVE note_graph
    judgment ("perfect"/"great").
    """

    note_index: int
    hit_time_ms: float
    result: str
    note_type: int
    lane: int
    delta_ms: float | None = 0.0


def _synth_offset(result: str, is_tail: bool, delta: float | None) -> float:
    """Physical offset (ms) that makes Model-A re-judge the press to ``result``.

    A witness (explicit ``delta``) is trusted verbatim -- it was constructed to yield ``result``. A
    remaining order-neutral selector (``delta is None``): Perfect -> 0 (on-time, judges Perfect);
    Great -> the canonical in-Great edge. Fail loud on any other unlabelled result (the optimizer
    only emits P/G).
    """
    if delta is not None:
        return float(delta)
    if result == "perfect":
        return 0.0
    if result == "great":
        return _CANONICAL_GREAT_OFFSET_TAIL_MS if is_tail else _CANONICAL_GREAT_OFFSET_TAP_MS
    raise ValueError(f"cannot synthesize an offset for result {result!r} without an explicit delta")


def presses_from_intended(chart: NoteChart, intended: list[IntendedNote]) -> list[Press]:
    """Convert an intended per-note trace into physical press/release edges.

    A tap (type 1) or hold head (type 2) => a press at hit_time+offset on its lane. A hold tail
    (type 3) => a RELEASE at tail_time+offset on its lane. ``offset`` is the witness delta verbatim,
    or a synthesized in-window offset for a selector, so the Model-A matcher re-judges each press to
    the note_graph's authoritative ``result``. The matcher resolves each edge against the live active
    list (earliest-hittable-first), so a well-formed full-combo trace reproduces its own stream.
    """
    edges: list[Press] = []
    for it in intended:
        is_tail = it.note_type == 3
        off = _synth_offset(it.result, is_tail, it.delta_ms)
        t = float(it.hit_time_ms) + off
        edges.append(Press(lane=it.lane, time_ms=t, is_release=is_tail))
    return edges


# ============================================================================================
# VALIDATION GATE
# ============================================================================================


def _build_aurora_intended():
    """Load the Aurora #1 loadout: (NoteChart, statsdict, colors, intended-trace, config)."""
    import numpy as np

    from gear_optimizer.core.gem_defs import element_gem_count
    from gear_optimizer.data.database_codecs import _unpack_stats_after_load
    from gear_optimizer.data.song_io import get_base_calc_song, scan_song_header
    from gear_optimizer.solver.fg_response_scoring.note_graph import force_greats_note_graph
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    db = str(ROOT / ".calc" / "aurora_fix.db")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT song_name, score, fg_score, force_details_json, details_json FROM team_buff_fg_loadouts "
        "WHERE force_details_json IS NOT NULL AND song_name LIKE 'Aurora%' ORDER BY fg_score DESC"
    ).fetchone()
    fd = _unpack_stats_after_load(json.loads(row["force_details_json"]))
    det = json.loads(row["details_json"]) if row["details_json"] else {}
    primary = str(det.get("pc") or fd.get("Selected Element") or "")
    secondary = str(det.get("sc") or primary)

    # chart
    fp = None
    for diff in ("Easy", "Normal", "Hard"):
        for f in glob.glob(str(ROOT / "Data" / diff / "*.txt")):
            if (scan_song_header(f) or {}).get("Song Name", "") == row["song_name"]:
                fp = f
    if fp is None:
        raise SystemExit(f"chart not found for {row['song_name']!r}")
    cs = get_base_calc_song(fp, {})
    apply_timing_envelope(cs, mode="perfect_window")
    sd = cs["song_data"]
    meta = cs["metadata"]
    ts = np.asarray(sd["timestamps"])
    nt = np.asarray(sd["note_types"])
    lanes = np.asarray(sd["lanes"])
    n = int(len(ts))

    chart = NoteChart(
        timestamps_ms=[float(x) * 1000.0 for x in ts.tolist()],
        lanes=[int(x) for x in lanes.tolist()],
        note_types=[int(x) for x in nt.tolist()],
    )

    ng = force_greats_note_graph(
        frontier_trace=fd["ForceGreats"]["frontier_trace"],
        total_notes=n, timestamps=ts, note_types=nt, lanes=lanes, timing_mode="perfect_window",
    )
    intended: list[IntendedNote] = []
    for node in ng:
        result = "great" if node["note_result"] == "Great" else "perfect"
        intended.append(
            IntendedNote(
                note_index=int(node["note_index"]),
                hit_time_ms=float(node["hit_time_ms"]),
                result=result,
                note_type=int(nt[int(node["note_index"])]),
                lane=int(lanes[int(node["note_index"])]),
                # Preserve None (a Great/Perfect SELECTOR with no timing witness) -- collapsing it to
                # 0.0 would make _synth_offset trust it verbatim and mis-judge a Great as Perfect.
                delta_ms=(float(node["delta_ms"]) if node.get("delta_ms") is not None else None),
            )
        )

    # final base+gem stats -> WebPort statsdict (same mapping loadout_oracle_replay uses)
    base = fd.get("BaseStats")
    gc = fd.get("GemCounts") or {}
    sel = str(fd.get("Selected Element") or "")
    final = apply_gems_to_base_stats(
        dict(base), sel, int(fd.get("FT", 0) or 0), int(fd.get("FF", 0) or 0),
        int(gc.get("Perfect Points", 0) or 0), int(gc.get("Combo Multiplier", 0) or 0),
        int(gc.get("Fever Multiplier", 0) or 0), element_gem_count(gc),
    )
    stat_to_wp = {
        "Perfect Points": "PerfectPoints", "Combo Multiplier": "ComboMultiplier",
        "Fever Multiplier": "FeverMultiplier", "Fever Time": "FeverTime",
        "Fever Fill Rate": "FeverFillRate",
    }
    color_to_wp = {"Chill": "ColorBlue", "Vibe": "ColorGreen", "Flow": "ColorPurple",
                   "Rush": "ColorRed", "Beat": "ColorOrange"}
    statsdict = {wp: int(final.get(opt, 0) or 0) for opt, wp in stat_to_wp.items()}
    colors: list[str] = []
    for col in (primary, secondary):
        if not col:
            continue
        wp = color_to_wp[col]
        statsdict[wp] = int(final.get(col, 0) or 0)
        colors.append(wp)

    taps = int((nt == 1).sum())
    heads = int((nt == 2).sum())
    last_note_time_ms = float(meta.get("Last Note Time", ts[-1] * 1000.0))
    if last_note_time_ms < 1000.0:
        last_note_time_ms = float(meta["Last Note Time"]) * 1000.0
    config = {
        "hitCount": n,
        "hitObjectsCount": taps + heads,
        "lastNoteTimeSec": (last_note_time_ms + 1000.0) / 1000.0,
    }
    return chart, statsdict, colors, intended, config, int(row["fg_score"]), int(row["score"])


def _validate(frame_dt_ms: float) -> int:
    lines: list[str] = []
    ok = True

    # ---- (1) trivial 4x-perfect -> oracle 2056 ----
    trivial_chart = NoteChart(
        timestamps_ms=[0.0, 1.0, 2.0, 3.0], lanes=[1, 1, 1, 1], note_types=[1, 1, 1, 1]
    )
    trivial_intended = [
        IntendedNote(i, float(i), "perfect", 1, 1, 0.0) for i in range(4)
    ]
    trivial_cfg = {"hitCount": 4, "hitObjectsCount": 4, "lastNoteTimeSec": 100.0}
    tp = presses_from_intended(trivial_chart, trivial_intended)
    tr = simulate(trivial_chart, {}, [], tp, trivial_cfg, frame_dt_ms=frame_dt_ms)
    lines.append(f"[trivial 4x-perfect] score={tr.score} (target 2056)  tally={tr.tally}")
    if tr.score != 2056:
        ok = False
        lines.append("  FAIL: 4x-perfect did not reproduce the oracle's 2056")

    # ---- (2) Aurora #1 -> game engine 47,317,114 ----
    chart, statsdict, colors, intended, config, surface_fg, surface_base = _build_aurora_intended()
    presses = presses_from_intended(chart, intended)
    r = simulate(chart, statsdict, colors, presses, config, frame_dt_ms=frame_dt_ms)
    target = 47_317_114
    delta = r.score - target
    pct = 100.0 * delta / target
    lines.append("")
    lines.append(f"[Aurora #1] GAME SCORE = {r.score:,}   target {target:,}   delta {delta:+,} ({pct:+.5f}%)")
    lines.append(
        f"           tally={r.tally}  maxCombo={r.max_combo}  feverHits={r.fever_hits} "
        f"feverPct={r.fever_percentage:.4f}"
    )
    lines.append(
        f"           feverMult={r.fever_mult:.4f} feverTimeSec={r.fever_time_sec:.4f} "
        f"feverFillDenom={r.fever_fill_denom:.4f}  surface_fg={surface_fg:,} (base {surface_base:,})"
    )
    lines.append("           fever sections:")
    for i, s in enumerate(r.fever_sections):
        lines.append(
            f"             sec{i+1}: activationMs={s['activationMs']:.1f} endMs={s['endMs']:.1f} "
            f"noteCount={s['noteCount']}"
        )
    within = abs(pct) <= 0.05
    if not within:
        ok = False
        lines.append("  FAIL: Aurora #1 outside +-0.05% of the gameplay-engine score")
    exact = delta == 0
    lines.append("")
    lines.append(f"RESOLUTION RULE: earliest-hittable-first, chart order; late edge inclusive / early exclusive;")
    lines.append(f"                 +200ms time-miss removal; frame-driven feverTick BEFORE the note pass;")
    lines.append(f"                 frame_dt_ms={frame_dt_ms:.6f}")
    lines.append("")
    lines.append(f"GATE: trivial={'PASS' if tr.score==2056 else 'FAIL'}  "
                 f"aurora_within_0.05%={'PASS' if within else 'FAIL'}  aurora_exact={exact}")
    print("\n".join(lines))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate", action="store_true", help="run the 2056 + Aurora 47,317,114 gates")
    ap.add_argument("--frame-dt-ms", type=float, default=1000.0 / 60.0, help="frame step (default 1/60 s)")
    args = ap.parse_args(argv)
    if args.validate:
        return _validate(args.frame_dt_ms)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
