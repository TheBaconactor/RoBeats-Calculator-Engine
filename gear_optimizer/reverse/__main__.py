"""python -m gear_optimizer.reverse --song "<Song Name>" --score N [what the game shows]: the sets behind a shown score."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from gear_optimizer.chart import load_chart, read_header
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.settings import DIFFICULTIES, paths

from .lookup import PlayInfo, prepare_song, reverse_score


def _chart_path(song: str) -> Path:
    for difficulty in DIFFICULTIES:
        for path in paths().chart_dir(difficulty).glob("*.txt"):
            if read_header(path)["Song Name"] == song:
                return path
    raise SystemExit(f"no chart has the Song Name {song!r}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m gear_optimizer.reverse", description=__doc__)
    parser.add_argument("--song", required=True, help="the chart's Song Name")
    parser.add_argument("--score", type=int, required=True, help="the Compete score")
    parser.add_argument("--accuracy", type=float, help="the row's accuracy, in percent")
    parser.add_argument("--multiplier", type=float, help="the row's Gear Multiplier")
    parser.add_argument("--mode", default="Compete", choices=("Compete", "Casual"), help="the row's mode")
    parser.add_argument("--casual", type=int, help="View's Casual Mode Score")
    parser.add_argument("--gear-power", type=int, help="View's Gear Power")
    parser.add_argument("--limit", type=int, default=8, help="the most stat lines to list")
    args = parser.parse_args()
    play = PlayInfo(args.score, args.accuracy, args.casual, args.multiplier, args.gear_power, args.mode)
    song = prepare_song(load_chart(_chart_path(args.song)), load_catalog(paths().game_export), stat_curves())
    reply = reverse_score(play, song, limit=args.limit)
    print(json.dumps(asdict(reply), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
