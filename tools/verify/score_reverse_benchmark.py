#!/usr/bin/env python3
"""Seeded dev/held-out benchmark of the score reverse-lookup (gear_optimizer.reverse).

Truth comes from outside the lookup: stored rows of a results database (a known set and its score) and plays simulated
through tools/verify/game_sim.GameScoreEngine, driven the way the game's server replays events: frames, floored event
times, the fill of the event's offset and the points of its stated result. Songs split by a seeded hash, so dev tuning
never sees held-out songs. Cases: meta rows, FG rows, plays with timing noise, random builds, exploited plays, and
unreleased stats. Run with EVOLUTION_DB_PATH set to anything but a live database; the database is only read.

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
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gear_optimizer.chart import Chart, load_chart, read_header
from gear_optimizer.core.time_quantize import quantize_to_int_ms
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import STATS, stat_curves
from gear_optimizer.reverse.lookup import ReverseSong, ShownPlay, prepare_song, reverse_score
from gear_optimizer.settings import paths
from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, judgment_edges
from gear_optimizer.stats import GEM_KINDS, apply_gems, total
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.gamedata import song_minis
from tools.verify.game_sim import GameScoreEngine, _judge_with_edges, _statsdict_from

_FRAME_MS = 1000.0 / 60.0
_LINE = ("Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
_ORACLE_STATS = {
    "Perfect Points": "PerfectPoints", "Combo Multiplier": "ComboMultiplier", "Fever Multiplier": "FeverMultiplier",
    "Fever Time": "FeverTime", "Fever Fill Rate": "FeverFillRate", "Chill": "ColorBlue", "Flow": "ColorPurple",
    "Rush": "ColorRed", "Beat": "ColorOrange", "Vibe": "ColorGreen",
}
_FIVE = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")


def gear_power(stats: dict[str, int], chart: Chart) -> int:
    return 5 * sum(stats[stat] for stat in _FIVE) + 4 * stats[chart.primary] + 2 * stats[chart.secondary]


class _ServerEngine(GameScoreEngine):
    """The game server's two readings of an event: its points from the stated result, its fill from `fill_as`."""

    fill_as: str | None = None

    def _fever_fill(self, result):
        return super()._fever_fill(self.fill_as or result)


def _engine(stats: dict[str, int] | None, chart: Chart) -> _ServerEngine:
    raw = {} if stats is None else {_ORACLE_STATS[stat]: value for stat, value in stats.items()}
    colors = [_ORACLE_STATS[color] for color in dict.fromkeys((chart.primary, chart.secondary))]
    config = {
        "hitObjectsCount": chart.total_notes - chart.long_notes,
        "lastNoteTimeSec": (round(chart.last_note_time * 1000.0) + 1000) / 1000,
    }
    return _ServerEngine(config, _statsdict_from(raw), colors)


def simulate(chart: Chart, stats: dict[str, int], offsets: np.ndarray, phase: float, fill_as: dict[int, str] | None = None) -> dict:
    """A play through the server's rule: judged at the frame after each press, event times floored, events in time order."""
    hit = quantize_to_int_ms(chart.timestamps).astype(np.float64)
    press = hit + offsets
    frames = np.ceil((press - phase) / _FRAME_MS) * _FRAME_MS + phase
    tap = judgment_edges(0)
    tail = tuple(edge * 2 for edge in tap)
    results = [
        _judge_with_edges(float(frames[i] - hit[i]), tail if chart.note_types[i] == HELD_TAIL_TYPE else tap)
        for i in range(chart.total_notes)
    ]
    times = np.floor(frames).astype(np.int64)
    gear, naked = _engine(stats, chart), _engine(None, chart)
    previous = 0
    for i in np.lexsort((np.arange(chart.total_notes), times)).tolist():
        for engine in (gear, naked):
            engine.fever_tick((int(times[i]) - previous) / 1000.0)
            engine.fill_as = None if fill_as is None else fill_as.get(i)
            engine.register_hit(results[i])
        previous = int(times[i])
    tally = gear.tally
    notes = chart.total_notes
    return {
        "score": gear.score,
        "casual": naked.score,
        "perfect": tally["perfect"],
        "great": tally["great"],
        "okay": tally["okay"],
        "miss": tally["miss"],
        "accuracy": round(100.0 * (tally["perfect"] + 0.75 * tally["great"] + 0.25 * tally["okay"]) / notes, 2),
    }


class Tally:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = defaultdict(list)

    def add(self, case: str, stats, gear, reply, seconds: float, expected: str = "sets") -> None:
        lines = list(dict.fromkeys(tuple(row.stats[stat] for stat in _LINE) for row in reply.sets))
        wanted = None if stats is None else tuple(stats[stat] for stat in _LINE)
        rank = lines.index(wanted) if wanted in lines else -1
        self.rows[case].append({
            "rank": rank,
            "gear": bool(gear) and any(set(row.gear) == set(gear) for row in reply.sets),
            "lines": len(lines),
            "verdict": reply.verdict,
            "expected": expected,
            "ms": seconds * 1000.0,
            "finished": bool(reply.finished),
        })

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
                "right_verdict": sum(row["verdict"] == row["expected"] for row in rows),
                "verdicts": dict(verdicts),
                "ms_p50": round(float(np.percentile(ms, 50)), 2),
                "ms_p95": round(float(np.percentile(ms, 95)), 2),
                "ms_max": round(float(ms.max()), 2),
                "mean_lines": round(float(np.mean([row["lines"] for row in rows])), 2),
            }
        return out


def _lookup(tally: Tally, case: str, song: ReverseSong, play: ShownPlay, stats, gear, expected: str = "sets") -> None:
    started = time.perf_counter()
    reply = reverse_score(play, song)
    tally.add(case, stats, gear, reply, time.perf_counter() - started, expected)


def _random_loadout(rng: random.Random, catalog, chart: Chart) -> dict[str, int]:
    """Any released items, any gems: a player the optimizer never looked at."""
    by_slot: dict[str, list] = defaultdict(list)
    for item in catalog.gears.values():
        by_slot[item.slot].append(item)
    minis = song_minis(catalog.minis.values(), chart.name, chart.primary, chart.secondary)
    parts = [team_buff_effect("T5", chart.primary)]
    parts += [rng.choice(items).stats for items in by_slot.values()]
    parts += [mini.stats for mini in rng.sample(minis, 3)]
    cuts = sorted(rng.randrange(91) for _ in range(5))
    counts = [b - a for a, b in zip([0, *cuts], [*cuts, 90])]
    return apply_gems(total(*parts), dict(zip(GEM_KINDS, counts)), chart.primary)


def _noise(rng: np.random.Generator, chart: Chart, sigma: float, center: float, perfect_only: bool) -> np.ndarray:
    offsets = rng.normal(center, sigma, chart.total_notes)
    if perfect_only:
        tail = chart.note_types == HELD_TAIL_TYPE
        # A frame later than the press still has to land inside the window.
        offsets = np.clip(offsets, np.where(tail, -38.0, -18.0), np.where(tail, 62.0, 22.0))
    return np.clip(offsets, -90.0, 170.0)


def run_song(name: str, chart: Chart, con: sqlite3.Connection, catalog, curves, tally: Tally, seed: int, rows_per_song: int) -> None:
    song = prepare_song(chart, catalog, curves)
    rng = random.Random(f"{seed}:{name}")
    noise = np.random.default_rng(int(hashlib.blake2b(f"{seed}:{name}".encode(), digest_size=8).hexdigest(), 16) % (1 << 63))
    for mode in ("non-precise", "precise"):
        meta = con.execute(
            "select score, meta_result, gear from loadouts where timing_mode=? and song_name=? and meta_board=1", (mode, name)
        ).fetchall()
        for score, result, gear in rng.sample(meta, min(rows_per_song, len(meta))):
            record = json.loads(result)
            stats = dict(zip(STATS, record["stats"]))
            items = json.loads(gear)
            _lookup(tally, f"meta/{mode}/score", song, ShownPlay(score=int(score)), stats, items)
            _lookup(tally, f"meta/{mode}/score+power", song, ShownPlay(score=int(score), gear_power=gear_power(stats, chart)), stats, items)
        fg = con.execute(
            "select fg_score, fg_result, gear from loadouts where timing_mode=? and song_name=? and fg_board=1", (mode, name)
        ).fetchall()
        for score, result, gear in rng.sample(fg, min(max(1, rows_per_song // 2), len(fg))):
            record = json.loads(result)
            stats = dict(zip(STATS, record["stats"]))
            surface = record["surface"]
            greats = surface[9] + sum(bin(word).count("1") for word in surface[4:8])
            play = ShownPlay(score=int(score), perfect=chart.total_notes - greats, great=greats, okay=0, miss=0, gear_power=gear_power(stats, chart))
            _lookup(tally, f"fg/{mode}/counts+power", song, play, stats, json.loads(gear))
    rows = con.execute(
        "select meta_result, gear from loadouts where song_name=? and meta_board=1 order by score desc limit 40", (name,)
    ).fetchall()
    for _ in range(rows_per_song):
        result, gear = rng.choice(rows)
        stats = dict(zip(STATS, json.loads(result)["stats"]))
        items = json.loads(gear)
        phase = rng.random() * _FRAME_MS
        honest = simulate(chart, stats, _noise(noise, chart, 9.0, 2.0, True), phase)
        if honest["great"] + honest["okay"] + honest["miss"] == 0:
            shown = ShownPlay(score=honest["score"], casual_score=honest["casual"], accuracy=honest["accuracy"], perfect=honest["perfect"], great=0, okay=0, miss=0)
            _lookup(tally, "noise/perfect/score+casual", song, shown, stats, items)
        human = simulate(chart, stats, _noise(noise, chart, 16.0, 6.0, False), phase)
        shown = ShownPlay(score=human["score"], casual_score=human["casual"], accuracy=human["accuracy"], perfect=human["perfect"], great=human["great"], okay=human["okay"], miss=human["miss"], gear_power=gear_power(stats, chart))
        _lookup(tally, "noise/human/counts+power", song, shown, stats, items)
        # Accuracy hacking: every note claims Perfect; the share that really was a Great fills as one.
        share = rng.choice((0.02, 0.1, 0.3))
        faked = {note: "great" for note in range(chart.total_notes) if rng.random() < share}
        cheat = simulate(chart, stats, np.zeros(chart.total_notes), phase, faked)
        shown = ShownPlay(score=cheat["score"], casual_score=cheat["casual"], accuracy=100.0, perfect=chart.total_notes, great=0, okay=0, miss=0)
        _lookup(tally, f"exploited/fill{int(share * 100)}", song, shown, None, None, "exploited")
        random_stats = _random_loadout(rng, catalog, chart)
        clean = simulate(chart, random_stats, np.zeros(chart.total_notes), phase)
        if clean["great"] + clean["okay"] + clean["miss"] == 0:
            _lookup(tally, "random/score", song, ShownPlay(score=clean["score"]), random_stats, None)
            _lookup(tally, "random/score+power", song, ShownPlay(score=clean["score"], gear_power=gear_power(random_stats, chart)), random_stats, None)
        boosted = dict(stats)
        boosted[chart.primary] += 25
        over = simulate(chart, boosted, np.zeros(chart.total_notes), phase)
        shown = ShownPlay(score=over["score"], casual_score=over["casual"], accuracy=100.0, perfect=chart.total_notes, great=0, okay=0, miss=0)
        if over["great"] + over["okay"] + over["miss"] == 0:
            _lookup(tally, "unreleased/plus25", song, shown, None, None, "unreleased")


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
        Path(args.out).write_text(json.dumps({"songs": index + 1, "cases": tally.summary()}, indent=1))
        print(f"{index + 1}/{args.songs} {name[:50]} {time.perf_counter() - started:.0f}s", flush=True)
    print(json.dumps(tally.summary(), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
