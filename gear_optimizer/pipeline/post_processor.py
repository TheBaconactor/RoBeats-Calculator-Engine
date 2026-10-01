"""The post-processor: canonicalizes each solved song, stores its results and prints what the database holds.

Runs as its own process beside the run's solve queue (pipeline.solve.run_queue), so the canonical gem re-solve and
exact replays stay off the queue's threads; PostSender feeds it from the run. Messages: a SongSolve, an error payload of
a failed song, or None (shutdown). The process exits 1 when any song failed.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import traceback
from typing import Any, cast

from gear_optimizer import settings
from gear_optimizer.core.output import suppress_stderr, suppress_stdout
from gear_optimizer.gamedata import Gear, Mini, load_gears, load_minis
from gear_optimizer.pipeline.canonical import canonical_rows
from gear_optimizer.pipeline.results import SongSolve
from gear_optimizer.settings import paths
from gear_optimizer.stats import GEM_KINDS
from gear_optimizer.store import schema
from gear_optimizer.store.db import Boards, load_boards, store_results
from gear_optimizer.store.records import Loadout

logger = logging.getLogger(__name__)


def run_post_processor(result_queue, total_tasks: int | None = None) -> None:
    # Spawned children may block-buffer stdout; results should print as songs finish.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            cast(Any, stream).reconfigure(line_buffering=True)
    if not settings.output_enabled():
        suppress_stdout(True)
        suppress_stderr(True)
    # A spawned child has no logging handlers: configure them (after the stderr swap, so quiet mode stays quiet on
    # the console) or per-song failures reach neither the console nor bin/error.log.
    from gear_optimizer.core.logging_config import configure_default_logging

    configure_default_logging()
    gears, minis = load_gears(paths().gears_csv), load_minis(paths().minis_csv)
    conn = schema.connect(paths().database, write=True)
    failed = 0
    try:
        while True:
            try:
                item = result_queue.get()
            except KeyboardInterrupt:
                # Ctrl+C can land here while blocked in get(); the parent drives shutdown with the None sentinel.
                continue
            except (EOFError, BrokenPipeError, OSError):
                break
            if item is None:
                break
            if isinstance(item, dict) and "_error" in item:
                failed += 1
                song = item.get("_song_name") or item.get("song") or "Unknown"
                msg = f"[POST] FAILED: {song} - {item.get('_error_type') or 'Error'}: {item.get('_error')}"
                print(msg, file=sys.stderr)
                logging.error(msg)
                if item.get("_trace"):
                    logging.error(item["_trace"])
                continue
            try:
                store_solve(conn, item, gears, minis)
            except Exception as exc:
                failed += 1
                msg = f"[POST] FAILED: {getattr(item, 'song', 'Unknown')} - {type(exc).__name__}: {exc}"
                print(msg, file=sys.stderr)
                logging.error(msg + "\n" + traceback.format_exc())
    finally:
        conn.close()
    if failed:
        print(f"[POST][SUMMARY] {failed}/{max(1, int(total_tasks or 0))} task(s) failed.")
        raise SystemExit(1)


def store_solve(conn, solve: SongSolve, gears: dict[str, Gear], minis: dict[str, Mini]) -> None:
    """Canonicalize a solved song, merge it into its boards (one transaction) and print the stored bests."""
    if not isinstance(solve, SongSolve):
        raise TypeError(f"the post-processor takes SongSolve results, got {type(solve).__name__}")
    rows = canonical_rows(solve, gears, minis)
    before = _best_overall(load_boards(conn, solve.song, solve.tier))
    store_results(conn, solve.song, solve.tier, rows)
    _print_stored(solve, load_boards(conn, solve.song, solve.tier), before, gears)


def _best_overall(boards: Boards) -> int:
    return max([x.score for x in boards.meta[:1]] + [x.fg_score for x in boards.fg[:1]] + [0])


def _print_stored(solve: SongSolve, boards: Boards, before: int, gears: dict[str, Gear]) -> None:
    meta = boards.meta[0] if boards.meta else None
    fg = boards.fg[0] if boards.fg else None
    best = _best_overall(boards)
    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {solve.song}")
    print(f"Best Base Score Found: {meta.score if meta else 0}")
    print(f"Best FG Score Found: {fg.fg_score if fg else 0}")
    if best > before:
        print(f" >> NEW RECORD! Previous: {before} | New: {best}")
    else:
        print(f" >> No improvement over the stored record ({before})")
    if meta is not None:
        _print_loadout("Best Gear Loadout (Base)", meta, meta.meta, gears)
    if fg is not None:
        _print_loadout("Best Gear Loadout (ForceGreats)", fg, fg.fg, gears)


def _print_loadout(title: str, loadout: Loadout, result, gears: dict[str, Gear]) -> None:
    print(f"\n[{title}]")
    for name in loadout.gear:
        slot = gears[name].slot if name in gears else "Item"
        print(f"{slot}: {name}")
    print(f"\n[{title} - Mini Team]")
    for group in loadout.minis:
        print(group[0])
    allocation = dict(zip(GEM_KINDS, result.gems))
    print(f"\nGem Allocation -> Fever Time: {allocation['Fever Time']}")
    print(f"Gem Allocation -> Fever Fill: {allocation['Fever Fill Rate']}")
    print(f"Gem Allocation -> Fever Multiplier: {allocation['Fever Multiplier']}")
    print(f"Gem Allocation -> Combo Multiplier: {allocation['Combo Multiplier']}")
    print(f"Gem Allocation -> Perfect Points: {allocation['Perfect Points']}")
    print(f"Gem Allocation -> {result.element} (Overflow): {allocation['Element']}")


class PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        backlog = 0
        self._q: queue.Queue[Any] = queue.Queue(maxsize=backlog)
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except queue.Full:
            return
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            while True:
                if self._stop_requested is not None and self._stop_requested():
                    return
                try:
                    self._post_queue.put(item, block=True, timeout=0.5)
                    break
                except queue.Full:
                    continue
