#!/usr/bin/env python3
"""A simulated player through a port of the decompiled game, for the reverse-lookup benchmark and its tests.

game_sim.py judges at the exact input time; the game does not. This port follows the game frame by frame (ReplicatedStorage
of the decompile, `file:line` below) and needs no player:

* Clock: one Heartbeat, one clock value; inputs carry no time (InputUtil.lua:297-383), so a press is judged at the first
  frame at or after it (GameLocal.lua:539-664).
* Inside a frame: notes update first, last spawned first: time-misses past 200 ms (Note.lua:240-263, HeldNote.lua:316-342,
  TrackSystem.lua:512-520); then each control, press before release (GameLocal.lua:589-611). Two presses of a key in one
  frame are one press (InputUtil.lua:598-617). A press takes the lane's first note it can hit, else it is a whiff, at most
  one between hits and none at chain 0 (TrackSystem.lua:227-268, ScoreManager.lua:271-285).
* Holds: head x1, tail x2 windows, late head recovery on the tail at x1, early release, tail time-miss (HeldNote.lua:262-405).
* The saved score is the server's replay of the events in time order: each event's fill or drain from the result its time
  offset computes, then its elapsed time, then points, chain and counts from the result it states
  (ServerPlayerNoteSequenceInfo.lua:262-309), event time = floor(frame clock) (ScoreManager.lua:316-318).
* The client's own score runs beside it, with no resync, to size the client vs Compete gap (ScoreManager.lua:286-291, 454-486).

Stat curves and each note's points come from game_sim. At a 1 ms clock an autoplay equals the engine's chart-time score.

Where it differs from the game: the order of controls inside a frame is track 2, 3, 4, 1, what Luau's pairs() probably gives
(not verified in game); the fill of Perfect and Great is the reference port's, get_powerbar_noteresult_fill failed to decompile and Okay and Miss are taken to add
none; there are no tap releases, and no audio sync of the clock (a force sync moves it by up to 0.5 s, AudioManager.lua:609-621).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.time_quantize import quantize_to_int_ms
from tools.verify.game_sim import (
    _DRAIN_WEIGHT,
    _chain_after_break,
    _color_point_bonus,
    _continuous_combo_multiplier,
    _fever_decay_rate,
    _fever_fill_scales,
    _fever_miss_drain_pct,
    _fever_multiplier,
    _great_points,
    _judge_with_edges,
    _note_times,
    _okay_points,
    _perfect_points,
    _statsdict_from,
)

ORACLE_STATS = {
    "Perfect Points": "PerfectPoints", "Combo Multiplier": "ComboMultiplier", "Fever Multiplier": "FeverMultiplier",
    "Fever Time": "FeverTime", "Fever Fill Rate": "FeverFillRate", "Chill": "ColorBlue", "Flow": "ColorPurple",
    "Rush": "ColorRed", "Beat": "ColorOrange", "Vibe": "ColorGreen",
}
_CONTROL_ORDER = (2, 3, 4, 1)
_NOTE_REMOVE_MS = 200.0
_PRE, _HOLDING, _MISSED, _PASSED, _GONE = range(5)
_TICK = 0.016666666666666666
# Note hit modes: those whose Miss counts at chain 0, and those that add to the accuracy denominator (PlayerScore.lua:231-232).
_TIME_MISSES = frozenset(("note_time", "head_time", "tail_time"))
_WHIFFS = frozenset(("whiff", "release_early"))


class PlayerScore:
    """PlayerScore.lua at one stat table: the powerbar and the hit register."""

    def __init__(self, stats: dict, colors: list[str], hit_objects: int, approx_ms: float):
        self.stats = stats
        self.colors = colors
        self.hit_objects = hit_objects
        fill = _fever_fill_scales(stats)
        self.fill = {"perfect": fill["perfect"], "great": fill["great"]}
        self.decay_seconds = approx_ms / 1000 * _fever_decay_rate(stats)
        self.fever_mult = _fever_multiplier(stats)
        self.drain = _fever_miss_drain_pct(stats)
        self.points = {"perfect": _perfect_points(stats), "great": _great_points(stats), "okay": _okay_points(stats), "miss": 0}
        self.score = self.chain = self.max_chain = self.whiffs = 0
        self.bar = 0.0
        self.active = False
        self.counts = {"perfect": 0, "great": 0, "okay": 0, "miss": 0}

    def apply(self, result: str) -> None:
        if self.active:
            self.bar += -self.drain * _DRAIN_WEIGHT[result]
        elif result in self.fill:
            self.bar += 1.0 / (self.hit_objects * self.fill[result])
        self.bar = min(max(self.bar, 0.0), 1.0)

    def update(self, timescale: float) -> None:
        if self.active:
            self.bar -= _TICK / self.decay_seconds * timescale
            if self.bar <= 0.0:
                self.bar = 0.0
                self.active = False
        elif self.bar >= 1.0:
            self.active = True

    def register(self, result: str, mode: str) -> None:
        self.max_chain = max(self.max_chain, self.chain)
        counted = True
        if result in ("perfect", "great"):
            self.chain += 1
        elif result == "miss":
            if self.chain > 0:
                self.chain = _chain_after_break(self.stats, self.chain)
            elif mode not in _TIME_MISSES:
                counted = False
            self.whiffs += counted and mode in _WHIFFS
        if counted:
            self.counts[result] += 1
            first, second = _color_point_bonus(self.stats, result, self.colors)
            combo = _continuous_combo_multiplier(self.stats, self.chain)
            self.score += math.floor((self.points[result] + first + second) * combo * (self.fever_mult if self.active else 1.0))


@dataclass(slots=True)
class _Note:
    row: int
    tail_row: int | None
    lane: int
    hit: float
    end: float | None
    state: int = _PRE


@dataclass(frozen=True, slots=True)
class Plan:
    """What a player does: the planned press offset of each chart row in ms (NaN: no input), and how to state a result."""

    offsets: np.ndarray
    states_perfect: bool = False  # an accuracy hack: every hit claims Perfect, its time offset stays the real one
    casual: bool = False  # the client judges at Perfect Time 0 (ScoreManager.lua:112-116), the server at the gear's
    strays: tuple[tuple[float, int], ...] = ()  # presses at no note: (song ms, lane)
    lost: tuple[tuple[float, float], ...] = ()  # song ms spans of frames the lag sync skipped: a press there never lands
    omits_misses: bool = False  # a hacked client never sends its Miss events: nothing on the server asks for them


@dataclass(slots=True)
class Played:
    score: int
    casual: int
    client_score: int
    perfect: int
    great: int
    okay: int
    miss: int
    accuracy: float
    max_combo: int
    fever_positions: list[int] = field(default_factory=list)
    forged: int = 0  # events whose stated result is not the one their time offset computes


def frame_clock(rng: np.random.Generator, last_ms: float, fps: float, jitter: float, gaps: tuple[tuple[float, float], ...] = ()) -> np.ndarray:
    """The song clock of every frame: a dt accumulator from a random phase (AudioManager.lua:569-587). gaps: (song ms, ms)
    frames that took that much longer and the lag sync let through (GameLagDelaySync.lua:36-79)."""
    step = 1000.0 / fps
    count = int((last_ms + 2000.0) / step * 1.3) + 16
    steps = step * (1.0 + jitter * rng.standard_normal(count)) if jitter else np.full(count, step)
    clock = -1000.0 + rng.uniform(0.0, step) + np.cumsum(np.maximum(steps, 1000.0 / 480.0))
    for at, extra in gaps:
        clock[np.searchsorted(clock, at):] += extra
    return clock


def shown_accuracy(accuracy: float) -> float:
    """The accuracy a row shows: saved to 5 decimals (PlayerSongPlay.lua:251, SPUtil.lua:2249-2253), printed to 2."""
    return float(f"{math.floor(accuracy * 100000.0 + 0.5) / 100000.0 * 100.0:.2f}")


def _notes_of(chart: Chart, hit: np.ndarray) -> list[_Note]:
    """Taps and holds in hit order: a head and the next tail of its lane are one note."""
    notes: list[_Note] = []
    open_holds: dict[int, _Note] = {}
    for row in range(chart.total_notes):
        kind, lane = int(chart.note_types[row]), int(chart.lanes[row])
        if kind == 3:
            hold = open_holds.pop(lane)
            hold.tail_row, hold.end = row, float(hit[row])
        else:
            notes.append(_Note(row, None, lane, float(hit[row]), None))
            if kind == 2:
                open_holds[lane] = notes[-1]
    return notes


def play(chart: Chart, stats: dict[str, int], perfect_time: int, plan: Plan, frames: np.ndarray) -> Played:
    hit = quantize_to_int_ms(chart.timestamps).astype(np.float64)
    gear = _statsdict_from({ORACLE_STATS[stat]: value for stat, value in stats.items()} | {"PerfectTime": perfect_time})
    base = _statsdict_from({})
    colors = [ORACLE_STATS[color] for color in dict.fromkeys((chart.primary, chart.secondary))]
    approx_ms = (round(chart.last_note_time * 1000.0) + 1000) / 1000 * 1000
    hit_objects = chart.total_notes - chart.long_notes
    server_edges = _note_times(gear)
    client_edges = _note_times(_statsdict_from({ORACLE_STATS[stat]: value for stat, value in stats.items()})) if plan.casual else server_edges
    client = PlayerScore(gear, colors, hit_objects, approx_ms)
    notes = _notes_of(chart, hit)
    presses: dict[int, set[int]] = {}
    releases: dict[int, list[_Note]] = {}
    pressed_at = [(note.hit + plan.offsets[note.row], note.lane) for note in notes if not math.isnan(plan.offsets[note.row])]
    for when, lane in [*pressed_at, *plan.strays]:
        if not any(start < when <= end for start, end in plan.lost):
            presses.setdefault(int(np.searchsorted(frames, when)), set()).add(lane)
    for note in notes:
        if note.tail_row is not None and not math.isnan(plan.offsets[note.row]) and not math.isnan(plan.offsets[note.tail_row]):
            releases.setdefault(int(np.searchsorted(frames, note.end + plan.offsets[note.tail_row])), []).append(note)
    events: list[tuple[int, int, str, float, str]] = []
    last_whiff = True

    def register(when: float, row: int, result: str, delta: float, mode: str) -> None:
        nonlocal last_whiff
        if mode == "whiff":
            if client.chain == 0:
                return
            last_whiff = True
        elif result != "miss":
            last_whiff = False
        client.apply(result)
        client.update(0.0)
        client.register(result, mode)
        stated = "perfect" if plan.states_perfect and result != "miss" else result
        if result != "miss" or not plan.omits_misses:
            events.append((math.floor(when), row, stated, delta, mode))

    first_live = 0
    previous = frames[0]
    expiries = [note.hit if note.end is None else note.end for note in notes] + [note.hit for note in notes if note.end is not None]
    due = np.searchsorted(frames, np.asarray(expiries) + _NOTE_REMOVE_MS, side="right").tolist()
    for index in sorted({*presses, *releases, *due}):
        now = float(frames[index])
        while first_live < len(notes) and notes[first_live].state == _GONE:
            first_live += 1
        live = [note for note in notes[first_live : first_live + 48] if note.hit - now < 3000.0 and note.state != _GONE]
        for note in reversed(live):
            if note.end is None:
                if note.state == _PRE and now - note.hit > _NOTE_REMOVE_MS:
                    register(now, note.row, "miss", 0.0, "note_time")
                    note.state = _GONE
            elif note.state == _PRE:
                if now - note.hit > _NOTE_REMOVE_MS:
                    register(now, note.row, "miss", 0.0, "head_time")
                    note.state = _MISSED
            elif now - note.end > _NOTE_REMOVE_MS:
                if note.state in (_HOLDING, _MISSED):
                    register(now, note.tail_row, "miss", 0.0, "tail_time")
                note.state = _GONE
        pressed_lanes = presses.get(index, ())
        released = releases.get(index, ())
        for lane in _CONTROL_ORDER:
            if lane in pressed_lanes:
                taken = False
                for note in live:
                    if note.lane != lane or note.state not in (_PRE, _MISSED):
                        continue
                    anchor = note.hit if note.state == _PRE else note.end
                    if note.state == _MISSED and note.end is None:
                        continue
                    delta = now - anchor
                    result = _judge_with_edges(delta, client_edges)
                    if result == "miss":
                        continue
                    if note.state == _PRE:
                        register(now, note.row, result, delta, "hit" if note.end is None else "head")
                        note.state = _GONE if note.end is None else _HOLDING
                    else:
                        register(now, note.tail_row, result, delta, "tail_late")
                        note.state = _PASSED
                    taken = True
                    break
                if not taken and not last_whiff:
                    register(now, -1, "miss", 0.0, "whiff")
            for note in released:
                if note.lane == lane and note.state in (_HOLDING, _MISSED):
                    delta = now - note.end
                    result = _judge_with_edges(delta, tuple(edge * 2 for edge in client_edges))
                    if result != "miss":
                        register(now, note.tail_row, result, delta, "tail")
                        note.state = _PASSED
                    elif note.state == _HOLDING:
                        register(now, note.tail_row, "miss", 0.0, "release_early")
                        note.state = _MISSED
        client.update((now - previous) / 1000.0 / _TICK)
        previous = now
    return _server_replay(chart, gear, base, colors, (hit_objects, approx_ms), server_edges, events, client.score)


def _server_replay(chart: Chart, gear: dict, base: dict, colors: list[str], song: tuple[int, float], edges: tuple, events: list, client_score: int) -> Played:
    """push_note_sequence over a play's events in time order."""
    hit_objects, approx_ms = song
    score = PlayerScore(gear, colors, hit_objects, approx_ms)
    naked = PlayerScore(base, [], hit_objects, approx_ms)
    fever_positions: list[int] = []
    previous = 0
    position = forged = 0
    for when, _row, stated, delta, mode in sorted(events, key=lambda event: event[0]):
        computed = "miss" if stated == "miss" else _judge_with_edges(delta, tuple(edge * 2 for edge in edges) if mode == "tail" else edges)
        forged += computed != stated
        score.apply(computed)
        naked.apply(computed)
        scale = max(0, when - previous) / 1000.0 / _TICK
        previous = when
        score.update(scale)
        naked.update(scale)
        if score.active:
            fever_positions.append(position)
        score.register(stated, mode)
        naked.register(stated, mode)
        position += 1
    counts = score.counts
    accuracy = (counts["perfect"] + 0.75 * counts["great"] + 0.25 * counts["okay"]) / (chart.total_notes + score.whiffs)
    return Played(score.score, naked.score, client_score, counts["perfect"], counts["great"], counts["okay"], counts["miss"], accuracy, score.max_chain, fever_positions, forged)
