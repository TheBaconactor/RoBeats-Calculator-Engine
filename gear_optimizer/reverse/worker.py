"""The :8765 service's lookup process: one JSON request per stdin line, one JSON answer per stdout line, in arrival order.

A process of its own has its own GPU context and so its own command queue. A lookup waits for the command buffer the GPU is
running, never for a turn on the solve worker's executor, and it runs at normal priority where the solve worker runs in the
background. Its main thread is its GPU owner, as macOS asks. Prepared songs stay warm, the most recently used first.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections import OrderedDict
from dataclasses import asdict
from typing import Any

from gear_optimizer.chart import load_chart
from gear_optimizer.data.game_export import Catalog, load_catalog
from gear_optimizer.gamedata import StatCurves, stat_curves
from gear_optimizer.settings import paths

from .lookup import PlayInfo, ReverseSong, prepare_song, reverse_score

_SONGS_KEPT = 8


def _song(path: str, songs: OrderedDict[str, ReverseSong], catalog: Catalog, curves: StatCurves) -> ReverseSong:
    if path not in songs:
        songs[path] = prepare_song(load_chart(path), catalog, curves)
        while len(songs) > _SONGS_KEPT:
            songs.popitem(last=False)
    songs.move_to_end(path)
    return songs[path]


def lookup(request: dict[str, Any], songs: OrderedDict[str, ReverseSong], catalog: Catalog, curves: StatCurves) -> dict[str, Any]:
    play = PlayInfo(request["score"], request.get("accuracy"), request.get("casualScore"), request.get("gearMultiplier"), request.get("gearPower"), request.get("matchMode", "Compete"))
    reply = reverse_score(play, _song(request["chartPath"], songs, catalog, curves), limit=request.get("limit", 8))
    return asdict(reply)


def main() -> int:
    from gear_optimizer.core.logging_config import configure_default_logging

    answers = sys.stdout
    with open(os.devnull, "w", encoding="utf-8") as devnull, contextlib.redirect_stdout(devnull):
        sys.__stdout__ = devnull
        configure_default_logging()
        os.environ.setdefault("TI_ENABLE_PYBUF", "0")
        from gear_optimizer.gpu.executor import is_fatal_gpu_error

        catalog, curves = load_catalog(paths().game_export), stat_curves()
        songs: OrderedDict[str, ReverseSong] = OrderedDict()
        for line in sys.stdin:
            try:
                answer = {"ok": True, "reverse": lookup(json.loads(line), songs, catalog, curves)}
            except Exception as exc:
                # A failed request leaves nothing behind; the process keeps serving unless its GPU is gone.
                answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": is_fatal_gpu_error(exc)}
            except BaseException as exc:
                answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": True}
            answers.write(json.dumps(answer, separators=(",", ":"), default=str) + "\n")
            answers.flush()
            if answer.get("restart"):
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
