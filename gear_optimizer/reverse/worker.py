"""The :8765 service's lookup process: one JSON request per stdin line, one JSON answer per stdout line, in arrival order.

A process of its own has its own GPU context and so its own command queue. A lookup waits for the command buffer the GPU is
running, never for a turn on the solve worker's executor, and it runs at normal priority where the solve worker runs in the
background. Its main thread is its GPU owner, as macOS asks. Prepared songs stay warm, the most recently used first.

A request with "prepare" readies its song, and with an accuracy the walk a lookup at that accuracy starts with: the website
sends it while the player types the row. The process compiles its kernels on lookups of its own before it reads a request.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections import OrderedDict
from dataclasses import asdict, replace
from typing import Any

import numpy as np

from gear_optimizer.chart import load_chart
from gear_optimizer.data.game_export import Catalog, load_catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import StatCurves, stat_curves
from gear_optimizer.score import factors, fg_surface_score
from gear_optimizer.settings import paths

from .loadouts import PRICED
from .lookup import PlayInfo, ReverseSong, prepare_song, reverse_score, warm_song
from .partial_sets import guess_set

_SONGS_KEPT = 8
# The share of a song's top the start-up lookup asks about: a bare score there was some released set's on 24 of 24 charts
# spread over the catalog's sizes (21 at 0.97, 12 at 0.98, 1 at 0.99).
_WARM_HEIGHT = 0.95


def _song(path: str, songs: OrderedDict[str, ReverseSong], catalog: Catalog, curves: StatCurves) -> ReverseSong:
    if path not in songs:
        songs[path] = prepare_song(load_chart(path), catalog, curves)
        while len(songs) > _SONGS_KEPT:
            songs.popitem(last=False)
    songs.move_to_end(path)
    return songs[path]


def answer(request: dict[str, Any], songs: OrderedDict[str, ReverseSong], catalog: Catalog, curves: StatCurves) -> dict[str, Any]:
    song = _song(request["chartPath"], songs, catalog, curves)
    if request.get("prepare"):
        warm_song(song, request.get("accuracy"))
        return {"prepared": True}
    play = PlayInfo(request["score"], request.get("accuracy"), request.get("casualScore"), request.get("gearMultiplier"), request.get("gearPower"), request.get("matchMode", "Compete"))
    return asdict(reverse_score(play, song))


def _compile_kernels(catalog: Catalog, curves: StatCurves) -> None:
    """Lookups on the first Easy chart that reach the lookup's kernels, so no player's lookup compiles one (the GPU's take ~1 s,
    numba's of the files a deploy changed half a minute): a bare score a little under the chart's top, where released sets
    play; the first set it names played with Greats on its first four head notes, placed by its Casual score and then by its
    Gear Multiplier, which leaves the hundreds of places the narrow rows pass takes; and a guess below max level. Left for a
    player's lookup: the hit order of a Force Great plan (trace.hit_schedule.input_order), which no made-up play reaches."""
    chart = load_chart(min(paths().chart_dir("Easy").glob("*.txt")))
    song = prepare_song(chart, catalog, curves)
    for found in reverse_score(PlayInfo(int(_WARM_HEIGHT * song.top)), song).sets[:1]:
        power = 5 * sum(found.stats[stat] for stat in PRICED) + 4 * found.stats[chart.primary] + 2 * found.stats[chart.secondary]
        score = fg_surface_score(factors(found.stats, curves, chart.primary, chart.secondary), found.surface._replace(great0=15), chart.total_notes)
        casual = fg_surface_score(song.naked, FgResponseSurface(*song.chart_head[0].tolist(), 15, 0, 0, 0, int(song.chart_fever[0]), 0), chart.total_notes)
        played = PlayInfo(score, 100.0 - 100.0 / chart.total_notes, casual, None, power)
        reverse_score(played, song)
        reverse_score(replace(played, casual_score=None, gear_multiplier=round(score / casual, 2)), song)
    guess_set(song.partial, np.zeros(6, dtype=np.int64), 1)


def main() -> int:
    from gear_optimizer.core.logging_config import configure_default_logging

    answers = sys.stdout
    with open(os.devnull, "w", encoding="utf-8") as devnull, contextlib.redirect_stdout(devnull):
        sys.__stdout__ = devnull
        configure_default_logging()
        os.environ.setdefault("TI_ENABLE_PYBUF", "0")
        from gear_optimizer.gpu.executor import is_fatal_gpu_error

        catalog, curves = load_catalog(paths().game_export), stat_curves()
        _compile_kernels(catalog, curves)
        songs: OrderedDict[str, ReverseSong] = OrderedDict()
        for line in sys.stdin:
            try:
                reply = {"ok": True, "reverse": answer(json.loads(line), songs, catalog, curves)}
            except Exception as exc:
                # A failed request leaves nothing behind; the process keeps serving unless its GPU is gone.
                reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": is_fatal_gpu_error(exc)}
            except BaseException as exc:
                reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": True}
            answers.write(json.dumps(reply, separators=(",", ":"), default=str) + "\n")
            answers.flush()
            if reply.get("restart"):
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
