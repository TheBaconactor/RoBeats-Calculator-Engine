"""python -m gear_optimizer.reverse --song "<Song Name>" --score N [what the game shows]: the sets behind a shown score."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from gear_optimizer.chart import load_chart, read_header
from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.core.timing_modes import TIMING_MODES
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.settings import DIFFICULTIES, paths
from gear_optimizer.store.db import load_boards
from gear_optimizer.store.records import Loadout
from gear_optimizer.store.schema import connect

from .lookup import ShownPlay, prepare_song, reverse_score


def _chart_path(song: str) -> Path:
    for difficulty in DIFFICULTIES:
        for path in paths().chart_dir(difficulty).glob("*.txt"):
            if read_header(path)["Song Name"] == song:
                return path
    raise SystemExit(f"no chart has the Song Name {song!r}")


def _stored_plans(database: str | None, song: str) -> list[Loadout]:
    if database is None:
        return []
    conn = connect(database)
    try:
        return [row for mode in TIMING_MODES for row in load_boards(conn, mode, song, OPTIMIZER_BASELINE_TEAM_BUFF).fg]
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m gear_optimizer.reverse", description=__doc__)
    parser.add_argument("--song", required=True, help="the chart's Song Name")
    parser.add_argument("--score", type=int, required=True, help="the Compete score")
    parser.add_argument("--casual", type=int, help="Play Info's Casual Mode Score")
    parser.add_argument("--accuracy", type=float, help="the accuracy shown, in percent")
    for count in ("perfect", "great", "okay", "miss"):
        parser.add_argument(f"--{count}", type=int, help="the results screen's count")
    parser.add_argument("--gear-power", type=int, help="Play Info's Gear Power")
    parser.add_argument("--mode", default="Compete", choices=("Compete", "Casual"), help="Play Info's Mode")
    parser.add_argument("--limit", type=int, default=8, help="the most sets to list")
    parser.add_argument("--db", help="a results database whose Force Great plans a play may have copied")
    args = parser.parse_args()
    play = ShownPlay(
        args.score, args.casual, args.accuracy, args.perfect, args.great, args.okay, args.miss, args.gear_power, args.mode
    )
    song = prepare_song(load_chart(_chart_path(args.song)), load_catalog(paths().game_export), stat_curves())
    reply = reverse_score(play, song, limit=args.limit, board=_stored_plans(args.db, args.song))
    print(json.dumps(asdict(reply), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
