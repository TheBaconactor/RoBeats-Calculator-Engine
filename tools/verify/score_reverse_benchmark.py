#!/usr/bin/env python3
"""Seeded dev/held-out benchmark of the score reverse-lookup (gear_optimizer.reverse) on fake players.

Each fake player (tools/verify/fake_players.py) wears a real set and plays through tools/verify/frame_play.py, a frame-by-frame
port of the decompiled game. The lookup gets what the Top Scores menu shows of their best play, nothing else; the set is the
answer key. Songs split by a seeded hash, so dev tuning never sees held-out songs. A results database, when given, adds
stored top builds and Force Great plans as more answer keys; the lookup never reads it. Latencies are this process's CPU time,
on one thread with NUMBA_NUM_THREADS=1.

    python tools/verify/score_reverse_benchmark.py --split dev --songs 40 --out dev.json [--db scratch.db] [--part 0/2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gear_optimizer.chart import Chart, load_chart, read_header
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import STATS, perfect_time_of, stat_curves
from gear_optimizer.reverse.lookup import PlayInfo, Reverse, ReverseSong, prepare_song, reverse_score
from gear_optimizer.score import factors
from gear_optimizer.settings import paths
from gear_optimizer.store.records import decode_trace
from gear_optimizer.trace.note_graph import force_greats_plan
from tools.verify.fake_players import SKILLS, Player, Row, fake_player, gear_power, play_info, top_scores_row
from tools.verify.frame_play import Plan, play

KINDS = ("top", "solid", "casual", "any", "starter")
BANDS = ((100.0, "100"), (99.5, "99.5+"), (98.0, "98+"), (95.0, "95+"), (90.0, "90+"), (0.0, "under 90"))


def band_of(accuracy: float) -> str:
    return next(name for floor, name in BANDS if accuracy >= floor)


def stat_line(stats: dict[str, int], chart: Chart, curves) -> tuple[int, ...]:
    """What the score can see of a final stat block."""
    cleaned = {stat: max(value, 0) for stat, value in stats.items()}
    keys = ("Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
    return (*(min(cleaned[key], 160) for key in keys), int(factors(cleaned, curves, chart.primary, chart.secondary).base))


class Tally:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.prepare_ms: list[float] = []

    def add(self, case: dict, reply: Reverse, truth: tuple[int, ...], gear: tuple[str, ...], ms: float, chart: Chart, curves) -> None:
        lines = list(dict.fromkeys(stat_line(row.stats, chart, curves) for row in reply.sets))
        self.rows.append({
            **case,
            "verdict": reply.verdict,
            "rank": lines.index(truth) if truth in lines else -1,
            "stat_lines": len(lines),
            "lines": reply.lines,
            "same_gear": any(set(row.gear) == set(gear) for row in reply.sets) if gear else False,
            "finished": bool(reply.finished),
            "ms": ms,
        })

    def report(self, songs: int) -> dict:
        def group(rows: list[dict]) -> dict:
            ms = [row["ms"] for row in rows]
            honest = [row for row in rows if not row.get("exploit")]
            return {
                "plays": len(rows),
                "listed": sum(row["rank"] >= 0 for row in rows),
                "first": sum(row["rank"] == 0 for row in rows),
                "top5": sum(0 <= row["rank"] < 5 for row in rows),
                "same_gear": sum(row["same_gear"] for row in rows),
                "verdicts": dict(Counter(row["verdict"] for row in rows)),
                "called_exploited": sum(row["verdict"] == "exploited" for row in honest),
                "called_unreleased": sum(row["verdict"] == "unreleased" for row in honest),
                "stat_lines_p50": float(np.percentile([row["stat_lines"] for row in rows], 50)),
                "ms_p50": round(float(np.percentile(ms, 50)), 2),
                "ms_p95": round(float(np.percentile(ms, 95)), 2),
                "ms_max": round(float(max(ms)), 2),
            }

        groups: dict[str, list[dict]] = defaultdict(list)
        for row in self.rows:
            for key in (
                f"shown/{row['shown']}",
                f"kind/{row['kind']}/{row['shown']}",
                f"skill/{row['skill']}/{row['shown']}",
                f"band/{row['band']}/{row['shown']}",
                f"tier/{row['tier']}/{row['shown']}",
                f"kind-band/{row['kind']}/{row['band']}/{row['shown']}",
                f"height/{int(row['height'] * 10) * 10}/{row['shown']}",
            ):
                if not row.get("exploit") and not row.get("stored"):
                    groups[key].append(row)
            if row.get("exploit"):
                groups[f"exploit/{row['exploit']}/{row['kind']}"].append(row)
                groups[f"exploit/{row['exploit']}/all"].append(row)
            if row.get("stored"):
                groups[f"stored/{row['stored']}/{row['shown']}"].append(row)
        prepare = np.asarray(self.prepare_ms)
        return {
            "songs": songs,
            "plays": len(self.rows),
            "prepare_ms": {"p50": float(np.percentile(prepare, 50)), "p95": float(np.percentile(prepare, 95))},
            "groups": {key: group(rows) for key, rows in sorted(groups.items())},
        }


def _lookup(tally: Tally, song: ReverseSong, row: Row, shown: str, case: dict) -> None:
    info = row.info
    chart = song.chart
    if shown == "score":
        info = PlayInfo(info.score, match_mode=info.match_mode)
    elif shown == "row":
        info = PlayInfo(info.score, info.accuracy, gear_multiplier=info.gear_multiplier, match_mode=info.match_mode)
    started = time.process_time()
    reply = reverse_score(info, song)
    ms = (time.process_time() - started) * 1000.0
    player = row.player
    top = float(song.surface_tops.max())
    tally.add(
        {**case, "shown": shown, "band": band_of(row.info.accuracy), "tier": player.tier, "kind": player.kind, "skill": player.skill, "height": min(row.info.score / top, 1.0), "exploit": player.exploit},
        reply, stat_line(player.stats, chart, song.curves), player.gear, ms, chart, song.curves,
    )


def _stored_rows(name: str, chart: Chart, song: ReverseSong, con, catalog, tally: Tally, seed: int, rows: int) -> None:
    """Verified builds: stored top builds and Force Great plans of a results database, played through the simulator."""
    curves = song.curves
    clock = np.arange(-1000.0, float(chart.timestamps[-1]) * 1000.0 + 2000.0, 1.0)
    top = float(song.surface_tops.max())
    for board, column, result in (("fg_board", "fg_trace", "fg_result"), ("meta_board", "meta_trace", "meta_result")):
        found = con.execute(
            f"select {result}, {column}, timing_mode, gear from loadouts where song_name=? and {board}=1", (name,)
        ).fetchall()
        for payload, trace, mode, gear in random.Random(f"{seed}:{name}:{board}").sample(found, min(rows, len(found))):
            record = json.loads(payload)
            stats = dict(zip(STATS, record["stats"]))
            worn = tuple(json.loads(gear))
            if board == "fg_board":
                time_stat = perfect_time_of(worn, catalog.gears)
                plan = force_greats_plan(frontier_trace=decode_trace(trace)["frontier_trace"], total_notes=chart.total_notes, timestamps=chart.timestamps, note_types=chart.note_types, lanes=chart.lanes, timing_mode=mode, perfect_time=time_stat)
                offsets = np.asarray([0.0 if delta is None else float(delta) for delta in plan.delta])
            else:
                time_stat, offsets = 0, np.zeros(chart.total_notes)
            played = play(chart, stats, time_stat, Plan(offsets), clock)
            info = play_info(played, gear_power(stats, chart), "Compete")
            started = time.process_time()
            reply = reverse_score(info, song)
            case = {"shown": "play-info", "band": band_of(info.accuracy), "tier": "T5", "kind": "stored", "skill": "plan", "height": min(info.score / top, 1.0), "stored": f"{board}/{mode}", "greats": played.great}
            tally.add(case, reply, stat_line(stats, chart, curves), worn, (time.process_time() - started) * 1000.0, chart, curves)


def run_song(name: str, chart: Chart, con, catalog, curves, tally: Tally, seed: int, repeats: int, rows: int) -> None:
    started = time.process_time()
    song = prepare_song(chart, catalog, curves)
    tally.prepare_ms.append((time.process_time() - started) * 1000.0)
    rng = random.Random(f"{seed}:{name}")
    minis = dict(catalog.minis)
    if con is not None:
        _stored_rows(name, chart, song, con, catalog, tally, seed, rows)
    for _ in range(repeats):
        for kind in KINDS:
            for skill in SKILLS:
                player = fake_player(rng, song, minis, kind, skill)
                row = top_scores_row(np.random.default_rng(rng.getrandbits(63)), chart, player)
                _lookup(tally, song, row, "play-info", {})
                if kind == "top":
                    _lookup(tally, song, row, "row", {})
                    _lookup(tally, song, row, "score", {})
        for kind in ("top", "solid", "casual"):
            for skill in ("pro", "good", "average", "bad"):
                for exploit in ("accuracy", "omitted-misses"):
                    player: Player = fake_player(rng, song, minis, kind, skill, exploit)
                    if player.match_mode == "Compete":
                        _lookup(tally, song, top_scores_row(np.random.default_rng(rng.getrandbits(63)), chart, player), "play-info", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--split", choices=("dev", "heldout"), required=True)
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--songs", type=int, default=40)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--part", default="0/1", help="this process's share of the songs, i/n")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True) if args.db else None
    curves = stat_curves()
    catalog = load_catalog(paths().game_export)
    charts: dict[str, Path] = {}
    for difficulty in ("Easy", "Normal", "Hard"):
        for path in paths().chart_dir(difficulty).glob("*.txt"):
            charts[read_header(path)["Song Name"]] = path

    def split_of(name: str) -> str:
        digest = hashlib.blake2b(f"{args.seed}:{name}".encode(), digest_size=2).digest()
        return "dev" if digest[0] % 2 == 0 else "heldout"

    names = sorted(name for name in charts if split_of(name) == args.split)
    random.Random(args.seed).shuffle(names)
    index, parts = (int(value) for value in args.part.split("/"))
    tally = Tally()
    started = time.perf_counter()
    for at, name in enumerate(names[: args.songs]):
        if at % parts == index:
            run_song(name, load_chart(charts[name]), con, catalog, curves, tally, args.seed, args.repeats, args.rows)
            Path(args.out).write_text(json.dumps(tally.report(at + 1), indent=1))
            print(f"{at + 1}/{args.songs} {name[:50]} {time.perf_counter() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
