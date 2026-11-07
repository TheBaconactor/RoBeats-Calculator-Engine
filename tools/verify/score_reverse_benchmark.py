#!/usr/bin/env python3
"""Seeded dev/held-out benchmark of the score reverse-lookup (gear_optimizer.reverse).

Truth comes from outside the lookup: stored rows of a results database (a known set and its score) and generated plays
through tools/verify/frame_play.py, a frame-by-frame port of the decompiled game. Songs split by a seeded hash, so dev tuning
never sees held-out songs. Cases: stored rows and plays of stored builds a few gems off, what the catalog does not hold, then
generated plays: sets from uniform to climbed, simulated players at frame rates, timing noise, misses, fever shifts, Force
Greats, Casual matches and hacks. Latencies are this process's CPU time, on one thread with NUMBA_NUM_THREADS=1. Run with
EVOLUTION_DB_PATH set to anything but a live database; the database is only read.

    python tools/verify/score_reverse_benchmark.py --db scratch.db --split dev --songs 40 --out dev.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sqlite3
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gear_optimizer.chart import Chart, load_chart, read_header
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_ORDER, team_buff_effect
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import ELEMENTS, STATS, stat_curves
from gear_optimizer.reverse.fever_reach import event_times, walk_cell
from gear_optimizer.reverse.lookup import ReverseSong, ShownPlay, prepare_song, reverse_score
from gear_optimizer.score import best_timeline_score, factors
from gear_optimizer.settings import paths
from gear_optimizer.solver.fever_timeline import fixed_timeline_cell
from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, fever_axes
from gear_optimizer.stats import GEM_KINDS, apply_gems, total
from gear_optimizer.store.db import load_boards
from gear_optimizer.store.schema import connect
from tools.verify.frame_play import Played, Plan, frame_clock, play

_LINE = ("Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
_FIVE = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
_BUILDS = ("any", "colored", "climbed")
_TIERS = tuple(TEAM_BUFF_TIER_ORDER)
_SHOWN = ("score", "score+power", "full")
_DATABASE: list[str] = []


def gear_power(stats: dict[str, int], chart: Chart) -> int:
    return 5 * sum(stats[stat] for stat in _FIVE) + 4 * stats[chart.primary] + 2 * stats[chart.secondary]


@dataclass(frozen=True, slots=True)
class Build:
    stats: dict[str, int]
    gear: tuple[str, ...]
    minis: tuple[str, ...]
    perfect_time: int


def _roll_gems(rng: random.Random, element_share: float) -> dict[str, int]:
    """90 gems: `element_share` of them on the element at the most, the rest anywhere."""
    element = rng.randint(0, int(90 * element_share))
    cuts = sorted(rng.randint(0, 90 - element) for _ in range(4))
    counts = [high - low for low, high in zip([0, *cuts], [*cuts, 90 - element])]
    return dict(zip(GEM_KINDS, (*counts, element)))


def _build(rng: random.Random, kind: str, song: ReverseSong) -> Build:
    """A set from the released items: `any` is uniform over them, with gems no solver would spend; `colored` is what a
    player of the song's colors wears; `climbed` starts there and climbs the all-Perfect chart-time score."""
    chart = song.chart
    by_slot: dict[str, list] = defaultdict(list)
    for item in song.gears.values():
        by_slot[item.slot].append(item)
    minis = list(song.minis.values())

    def color_value(item) -> int:
        return 2 * item.stats[chart.primary] + item.stats[chart.secondary]

    if kind != "any":
        by_slot = {slot: sorted(items, key=color_value, reverse=True)[:6] for slot, items in by_slot.items()}
        minis = sorted(minis, key=color_value, reverse=True)[:8]
    tier = "T5" if kind == "climbed" else rng.choice(_TIERS)
    team = chart.primary if kind == "climbed" else rng.choice(ELEMENTS)
    element = chart.primary if kind != "any" else rng.choice(ELEMENTS)
    start = team_buff_effect(tier, team)
    gear = {slot: rng.choice(items) for slot, items in by_slot.items()}
    trio = rng.sample(minis, 3)
    gems = _roll_gems(rng, 0.0 if kind == "any" else 0.9)

    def stats_of(worn: dict, three: list, allocation: dict[str, int]) -> dict[str, int]:
        return apply_gems(total(start, *(item.stats for item in worn.values()), *(mini.stats for mini in three)), allocation, element)

    if kind == "climbed":
        best = _chart_time_score(song, stats_of(gear, trio, gems))
        for _ in range(600):
            worn, three, allocation = dict(gear), list(trio), dict(gems)
            move = rng.random()
            if move < 0.35:
                slot = rng.choice(tuple(worn))
                worn[slot] = rng.choice(by_slot[slot])
            elif move < 0.55:
                three[rng.randrange(3)] = rng.choice([mini for mini in minis if mini not in three])
            else:
                source = rng.choice([gem for gem, count in allocation.items() if count])
                moved = min(allocation[source], rng.choice((1, 1, 2, 3, 5)))
                allocation[source] -= moved
                allocation[rng.choice(GEM_KINDS)] += moved
            value = _chart_time_score(song, stats_of(worn, three, allocation))
            if value >= best:
                best, gear, trio, gems = value, worn, three, allocation
    return Build(stats_of(gear, trio, gems), tuple(item.name for item in gear.values()), tuple(mini.name for mini in trio), sum(item.perfect_time for item in gear.values()))


def _chart_time_score(song: ReverseSong, stats: dict[str, int]) -> int:
    chart = song.chart
    cell = _chart_cell(song, stats)
    return best_timeline_score(factors(stats, song.curves, chart.primary, chart.secondary), cell, chart.total_notes)[0]


def _chart_cell(song: ReverseSong, stats: dict[str, int]):
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    ft, ff = min(stats["Fever Time"], 160), min(stats["Fever Fill Rate"], 160)
    key = (ft, ff)
    cache = _CELLS.setdefault(chart.name, {})
    if key not in cache:
        cache[key] = fixed_timeline_cell(chart.timestamps, fill_notes=math.ceil(thresholds[ff]), fever_duration=float(durations[ft]))
    return cache[key]


_CELLS: dict[str, dict] = {}


@dataclass(frozen=True, slots=True)
class Situation:
    """A simulated player: the frame rate and its jitter, how its presses fall, whether a hacked client states every hit
    Perfect, and whether it plays a Casual match."""

    fps: float
    jitter: float
    offsets: Callable[[np.random.Generator, Chart], np.ndarray]
    cheats: bool = False
    casual: bool = False


def _inside(chart: Chart, offsets: np.ndarray, frame_ms: float) -> np.ndarray:
    """Offsets kept where a frame later still lands inside a Perfect window."""
    tail = chart.note_types == HELD_TAIL_TYPE
    return np.clip(offsets, np.where(tail, -38.0, -18.0), np.where(tail, 78.0, 38.0) - frame_ms)


def _tight(sigma: float, frame_ms: float):
    return lambda rng, chart: _inside(chart, rng.normal(frame_ms * -0.5 + 8.0, sigma, chart.total_notes), frame_ms)


def _drift(rng: np.random.Generator, chart: Chart) -> np.ndarray:
    """A hand that wanders: every press drifts together, so fever windows shift as whole windows."""
    period = rng.uniform(4.0, 30.0)
    wave = 12.0 * np.sin(2.0 * np.pi * np.asarray(chart.timestamps, dtype=np.float64) / period + rng.uniform(0.0, 6.28))
    return _inside(chart, wave + rng.normal(0.0, 3.0, chart.total_notes), 1000.0 / 60.0)


def _edges(rng: np.random.Generator, chart: Chart) -> np.ndarray:
    """Every press near an edge of the Perfect window: the most a timing can move fever."""
    late = rng.random(chart.total_notes) < 0.5
    return _inside(chart, np.where(late, 40.0, -18.0), 1000.0 / 60.0)


def _human(sigma: float, missing: float):
    def offsets(rng: np.random.Generator, chart: Chart) -> np.ndarray:
        played = np.clip(rng.normal(4.0, sigma, chart.total_notes), -150.0, 170.0)
        played[rng.random(chart.total_notes) < missing] = np.nan
        return played
    return offsets


def _force_greats(count: int):
    def offsets(rng: np.random.Generator, chart: Chart) -> np.ndarray:
        played = _tight(7.0, 1000.0 / 60.0)(rng, chart)
        played[:count] = rng.uniform(60.0, 150.0, count)
        return played
    return offsets


def _isolated(chart: Chart) -> np.ndarray:
    """Taps with no note of their lane within 200 ms: a late press there loses no note."""
    times = np.asarray(chart.timestamps, dtype=np.float64) * 1000.0
    lanes = np.asarray(chart.lanes)
    out = np.asarray(chart.note_types) == 1
    for lane in np.unique(lanes):
        rows = np.flatnonzero(lanes == lane)
        close = np.diff(times[rows]) < 200.0
        out[rows[:-1][close]] = False
        out[rows[1:][close]] = False
    return out


def _hacked(share: float, sigma: float | None = None):
    """A hacked client's real presses, every one stated Perfect: `share` of the taps that can take it land in a Great
    window, or with `sigma` a human's hand over those taps. Fever slides, no point is lost."""
    def offsets(rng: np.random.Generator, chart: Chart) -> np.ndarray:
        played = _tight(7.0, 1000.0 / 60.0)(rng, chart)
        taps = _isolated(chart)
        chosen = taps & (rng.random(chart.total_notes) < share)
        played[chosen] = rng.uniform(60.0, 150.0, int(chosen.sum())) if sigma is None else rng.normal(4.0, sigma, int(chosen.sum())).clip(-48.0, 150.0)
        return played
    return offsets


SITUATIONS: dict[str, Situation] = {
    "autoplay/60": Situation(60.0, 0.0, lambda rng, chart: np.zeros(chart.total_notes)),
    "tight/30": Situation(30.0, 0.0, _tight(5.0, 1000.0 / 30.0)),
    "tight/60": Situation(60.0, 0.0, _tight(9.0, 1000.0 / 60.0)),
    "tight/144": Situation(144.0, 0.0, _tight(9.0, 1000.0 / 144.0)),
    "tight/240-jitter": Situation(240.0, 0.3, _tight(9.0, 1000.0 / 120.0)),
    "drift/60": Situation(60.0, 0.0, _drift),
    "edges/60": Situation(60.0, 0.0, _edges),
    "human/60": Situation(60.0, 0.0, _human(18.0, 0.0)),
    "human/144": Situation(144.0, 0.1, _human(14.0, 0.0)),
    "sloppy/60": Situation(60.0, 0.0, _human(26.0, 0.01)),
    "force-greats-2": Situation(60.0, 0.0, _force_greats(2)),
    "force-greats-8": Situation(60.0, 0.0, _force_greats(8)),
    "casual/perfect-time": Situation(60.0, 0.0, _human(16.0, 0.0), casual=True),
    "hack/accuracy": Situation(60.0, 0.0, _hacked(1.0, 24.0), True),
    "hack/fever-2": Situation(60.0, 0.0, _hacked(0.02), True),
    "hack/fever-10": Situation(60.0, 0.0, _hacked(0.10), True),
    "hack/fever-30": Situation(60.0, 0.0, _hacked(0.30), True),
}


def _shown_play(played: Played, stats: dict[str, int], chart: Chart, shown: str, match_mode: str = "Compete") -> ShownPlay:
    if shown == "score":
        return ShownPlay(score=played.score, match_mode=match_mode)
    if shown == "score+power":
        return ShownPlay(score=played.score, gear_power=gear_power(stats, chart), match_mode=match_mode)
    return ShownPlay(
        score=played.score, casual_score=played.casual, accuracy=round(played.accuracy * 100.0, 2), perfect=played.perfect,
        great=played.great, okay=played.okay, miss=played.miss, gear_power=gear_power(stats, chart), match_mode=match_mode,
    )


def _reaches(song: ReverseSong, stats: dict[str, int], perfect_time: int, played: Played) -> bool:
    """Whether the walk holds a clean play's own timeline: its fever events in the head, and their count past it."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    ft, ff = min(stats["Fever Time"], 160), min(stats["Fever Fill Rate"], 160)
    scratch = (np.empty((1 << 15, 6), dtype=np.int64), np.empty((1 << 15, 6), dtype=np.int64))
    out = np.empty((1 << 15, 5), dtype=np.int64)
    written = walk_cell(event_times(chart, perfect_time), math.ceil(thresholds[ff]), float(durations[ft]) * 1000.0, scratch, out)
    head = sum(1 << position for position in played.fever_positions if position < 100)
    body = sum(position >= 100 for position in played.fever_positions)
    for low, high, lowest, highest, bits in out[:written].tolist():
        if low + (high << 62) == head and lowest <= body <= highest and (bits < 0 or (bits >> (body - lowest)) & 1):
            return True
    return False


class Tally:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = defaultdict(list)
        self.missed: list[tuple] = []
        self.prepare_ms: list[float] = []
        self.client_gaps: list[float] = []
        self.reach = [0, 0]  # clean plays, inside the walk
        self.outside: list[str] = []
        self.flagged: list[tuple] = []
        self.forged: dict[str, list[float]] = defaultdict(list)

    def note_prepare(self, ms: float) -> None:
        self.prepare_ms.append(ms)

    def note_client_gap(self, played: Played) -> None:
        self.client_gaps.append((played.client_score - played.score) / max(played.score, 1))

    def note_reach(self, inside: bool, perfect_time: int, label: str) -> None:
        self.reach[0] += 1
        self.reach[1] += inside
        if not inside:
            self.outside.append(f"{label} pt={perfect_time}")

    def add(self, case: str, song: ReverseSong, stats, gear, reply, seconds: float, expected: str = "sets") -> None:
        def line(row: dict[str, int]) -> tuple:
            chart = song.chart
            return (*(row[stat] for stat in _LINE), factors(row, song.curves, chart.primary, chart.secondary).base)

        lines = list(dict.fromkeys(line(row.stats) for row in reply.sets))
        wanted = None if stats is None else line(stats)
        rank = lines.index(wanted) if wanted in lines else -1
        self.rows[case].append({
            "rank": rank,
            "gear": bool(gear) and any(set(row.gear) == set(gear) for row in reply.sets),
            "lines": len(lines),
            "verdict": reply.verdict,
            "expected": expected,
            "ms": seconds * 1000.0,
            "finished": bool(reply.finished),
            "lines_found": reply.lines,
        })

    def report(self, songs: int) -> dict:
        gaps = np.asarray(self.client_gaps)
        prepare = np.asarray(self.prepare_ms)
        return {
            "songs": songs,
            "prepare_ms": {"p50": float(np.percentile(prepare, 50)), "p95": float(np.percentile(prepare, 95))},
            "client_over_compete": {"plays": len(gaps), "share_differing": float((gaps != 0.0).mean()), "p50": float(np.percentile(np.abs(gaps), 50)), "p95": float(np.percentile(np.abs(gaps), 95))},
            "clean_plays_in_walk": {"plays": self.reach[0], "inside": self.reach[1], "outside": self.outside[:40]},
            "honest_plays": self.honest(),
            "flagged": self.flagged[:200],
            "forged_note_share": {case: float(np.mean(shares)) for case, shares in sorted(self.forged.items())},
            "cases": self.summary(),
            "missed": self.missed[:200],
        }

    def honest(self) -> dict:
        rows = [row for table in self.rows.values() for row in table if row["expected"] in ("sets", "honest")]
        return {
            "plays": len(rows),
            "called_exploited": sum(row["verdict"] == "exploited" for row in rows),
            "called_unreleased": sum(row["verdict"] == "unreleased" for row in rows),
        }

    def summary(self) -> dict:
        out = {}
        for case, rows in sorted(self.rows.items()):
            ms = np.asarray([row["ms"] for row in rows])
            ranked = [row for row in rows if row["expected"] == "sets"]
            verdicts = defaultdict(int)
            for row in rows:
                verdicts[row["verdict"]] += 1
            out[case] = {
                "plays": len(rows),
                "top1": sum(row["rank"] == 0 for row in ranked),
                "top5": sum(0 <= row["rank"] < 5 for row in ranked),
                "any": sum(row["rank"] >= 0 for row in ranked),
                "gear": sum(row["gear"] for row in ranked),
                "right_verdict": sum(row["verdict"] == row["expected"] or (row["expected"] == "honest" and row["verdict"] in ("sets", "unresolved")) for row in rows),
                "verdicts": dict(verdicts),
                "unresolved_finished": sum(row["verdict"] == "unresolved" and row["finished"] for row in rows),
                "ms_p50": round(float(np.percentile(ms, 50)), 2),
                "ms_p95": round(float(np.percentile(ms, 95)), 2),
                "ms_max": round(float(ms.max()), 2),
                "mean_lines": round(float(np.mean([row["lines"] for row in rows])), 2),
                "lines_p50": float(np.percentile([row["lines_found"] for row in rows], 50)),
            }
        return out


def _lookup(tally: Tally, case: str, song: ReverseSong, play: ShownPlay, stats, gear, expected: str = "sets") -> None:
    started = time.process_time()
    reply = reverse_score(play, song)
    tally.add(case, song, stats, gear, reply, time.process_time() - started, expected)
    if tally.rows[case][-1]["rank"] < 0 and stats is not None and expected == "sets":
        tally.missed.append((case, song.chart.name, play.score, reply.verdict, reply.lines, reply.finished))
    if expected in ("sets", "honest") and reply.verdict in ("exploited", "unreleased"):
        tally.flagged.append((case, song.chart.name, play.score, reply.verdict, reply.evidence))


def _with_perfect_time(build: Build, song: ReverseSong, rng: random.Random) -> Build:
    """The build with one Perfect Time gear in its slot."""
    wearing = [song.gears[name] for name in build.gear]
    swap = rng.choice([item for item in song.gears.values() if item.perfect_time > 0])
    old = next(item for item in wearing if item.slot == swap.slot)
    stats = {stat: value + swap.stats.get(stat, 0) - old.stats.get(stat, 0) for stat, value in build.stats.items()}
    gear = tuple(swap.name if name == old.name else name for name in build.gear)
    return Build(stats, gear, build.minis, build.perfect_time + swap.perfect_time - old.perfect_time)


def _past_the_catalog(tally: Tally, song: ReverseSong, stats: dict[str, int], rng: random.Random) -> None:
    """Clean plays of what the catalog does not hold, from a stored top build: an unreleased item's primary points, whose
    verdict must name one; and a set no item explains."""
    chart = song.chart
    frames = frame_clock(np.random.default_rng(rng.getrandbits(63)), float(chart.timestamps[-1]) * 1000.0, 60.0, 0.0)
    for extra, expected in ((25, "unreleased"), (400, "exploited")):
        lifted = dict(stats, **{chart.primary: stats[chart.primary] + extra})
        played = play(chart, lifted, 0, Plan(np.zeros(chart.total_notes)), frames)
        _lookup(tally, f"catalog/plus-{extra}/score+power", song, ShownPlay(score=played.score, gear_power=gear_power(lifted, chart)), None, (), expected)


def _near_meta(tally: Tally, song: ReverseSong, row: tuple, rng: random.Random) -> None:
    """A clean play of a stored top build a few gems off: what a leaderboard holds."""
    chart = song.chart
    gear, minis, gems, element = row
    allocation = dict(zip(GEM_KINDS, gems))
    for _ in range(rng.randint(1, 4)):
        source = rng.choice([gem for gem, count in allocation.items() if count])
        allocation[source] -= 1
        allocation[rng.choice(GEM_KINDS)] += 1
    items = [song.gears[item].stats for item in gear] + [song.minis[mini].stats for mini in minis]
    stats = apply_gems(total(team_buff_effect("T5", chart.primary), *items), allocation, element)
    noise = np.random.default_rng(rng.getrandbits(63))
    frames = frame_clock(noise, float(chart.timestamps[-1]) * 1000.0, 60.0, 0.0)
    played = play(chart, stats, 0, Plan(_tight(9.0, 1000.0 / 60.0)(noise, chart)), frames)
    if played.great + played.okay + played.miss == 0:
        for shown in _SHOWN:
            _lookup(tally, f"near-meta/tight/{shown}", song, _shown_play(played, stats, chart, shown), stats, gear)
    for name, situation in SITUATIONS.items():
        if situation.cheats:
            hacked = play(chart, stats, 0, Plan(situation.offsets(noise, chart), states_perfect=True), frames)
            tally.forged[f"near-meta/{name}"].append(hacked.forged / chart.total_notes)
            _lookup(tally, f"near-meta/{name}/full", song, _shown_play(hacked, stats, chart, "full"), stats, gear, "exploited")


def _stored_rows(name: str, chart: Chart, song: ReverseSong, con, store, tally: Tally, rng: random.Random, rows: int) -> None:
    """Verified builds: stored rows of a results database, by score and at its Gear Power."""
    for mode in ("non-precise", "precise"):
        meta = con.execute(
            "select score, meta_result, gear, minis from loadouts where timing_mode=? and song_name=? and meta_board=1", (mode, name)
        ).fetchall()
        for score, result, gear, minis in rng.sample(meta, min(rows, len(meta))):
            record = json.loads(result)
            stats = dict(zip(STATS, record["stats"]))
            _near_meta(tally, song, (json.loads(gear), [group[0] for group in json.loads(minis)], record["gems"], record["element"]), rng)
            _lookup(tally, f"stored/meta/{mode}/score", song, ShownPlay(score=int(score)), stats, json.loads(gear))
            _lookup(tally, f"stored/meta/{mode}/score+power", song, ShownPlay(score=int(score), gear_power=gear_power(stats, chart)), stats, json.loads(gear))
            _past_the_catalog(tally, song, stats, rng)
        fg = con.execute(
            "select fg_score, fg_result, gear from loadouts where timing_mode=? and song_name=? and fg_board=1", (mode, name)
        ).fetchall()
        for score, result, gear in rng.sample(fg, min(rows, len(fg))):
            record = json.loads(result)
            stats = dict(zip(STATS, record["stats"]))
            surface = record["surface"]
            greats = surface[9] + sum(bin(word).count("1") for word in surface[4:8])
            play_row = ShownPlay(score=int(score), perfect=chart.total_notes - greats, great=greats, okay=0, miss=0, gear_power=gear_power(stats, chart))
            _lookup(tally, f"stored/fg/{mode}/no-board", song, play_row, stats, json.loads(gear), "honest")
            board = load_boards(store, mode, name, "T5").fg
            started = time.process_time()
            reply = reverse_score(play_row, song, board=board)
            tally.add(f"stored/fg/{mode}/board", song, stats, json.loads(gear), reply, time.process_time() - started)


def run_song(name: str, chart: Chart, con: sqlite3.Connection, catalog, curves, tally: Tally, seed: int, rows_per_song: int) -> None:
    store = connect(_DATABASE[0])
    started = time.process_time()
    song = prepare_song(chart, catalog, curves)
    tally.note_prepare((time.process_time() - started) * 1000.0)
    rng = random.Random(f"{seed}:{name}")
    _stored_rows(name, chart, song, con, store, tally, rng, rows_per_song)
    last_ms = float(chart.timestamps[-1]) * 1000.0
    for build_kind in _BUILDS:
        for situation_name, situation in SITUATIONS.items():
            build = _build(rng, build_kind, song)
            if situation.casual:
                build = _with_perfect_time(build, song, rng)
            noise = np.random.default_rng(rng.getrandbits(63))
            offsets = situation.offsets(noise, chart)
            frames = frame_clock(noise, last_ms, situation.fps, situation.jitter)
            plan = Plan(offsets, states_perfect=situation.cheats, casual=situation.casual)
            played = play(chart, build.stats, build.perfect_time, plan, frames)
            tally.note_client_gap(played)
            if situation.cheats:
                tally.forged[situation_name].append(played.forged / chart.total_notes)
            clean = played.great + played.okay + played.miss == 0
            if clean and not situation.cheats and not situation.casual:
                tally.note_reach(_reaches(song, build.stats, build.perfect_time, played), build.perfect_time, f"{name} {build_kind} {situation_name}")
            for shown in _SHOWN:
                if situation.cheats and shown != "full":
                    continue
                expected = "exploited" if situation.cheats else ("honest" if situation.casual or not clean else "sets")
                case = f"{build_kind}/{situation_name}/{shown}"
                match_mode = "Casual" if situation.casual else "Compete"
                _lookup(tally, case, song, _shown_play(played, build.stats, chart, shown, match_mode), build.stats, build.gear, expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--split", choices=("dev", "heldout"), required=True)
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--songs", type=int, default=40)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    _DATABASE.append(args.db)
    curves = stat_curves()
    catalog = load_catalog(paths().game_export)
    charts: dict[str, Path] = {}
    for difficulty in ("Easy", "Normal", "Hard"):
        for path in paths().chart_dir(difficulty).glob("*.txt"):
            charts[read_header(path)["Song Name"]] = path
    names = sorted(name for (name,) in con.execute("select distinct name from songs") if name in charts)

    def split_of(name: str) -> str:
        digest = hashlib.blake2b(f"{args.seed}:{name}".encode(), digest_size=2).digest()
        return "dev" if digest[0] % 2 == 0 else "heldout"

    names = [name for name in names if split_of(name) == args.split]
    random.Random(args.seed).shuffle(names)
    tally = Tally()
    started = time.perf_counter()
    for index, name in enumerate(names[: args.songs]):
        run_song(name, load_chart(charts[name]), con, catalog, curves, tally, args.seed, args.rows)
        Path(args.out).write_text(json.dumps(tally.report(index + 1), indent=1))
        print(f"{index + 1}/{args.songs} {name[:50]} {time.perf_counter() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
