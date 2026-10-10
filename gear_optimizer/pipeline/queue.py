"""A run's queue: the solves (one chart in one timing mode) of its charts, unsolved first, then least recently solved.

Charts: Data/<Difficulty>/*.txt for config.ini's Difficulty, kept when their Song Name contains Song_Name and their
colors are among TargetPrimary / TargetSecondary (comma, pipe or slash lists; All, Any or * for every color). A chart is
solved in its Timing Mode header's mode, else in both, Precise first. The results database orders the solves: the
ones it has not stored (by chart), then the stored ones by when they were last solved, so a stopped run continues
where it stopped. Each solve runs SongRepeats times; SongQueueLimit keeps the first N runs (0: all). Every run has its
own GA seed: with GA_SEED stable per song, mode and run (a mode solves the same alone or beside the other), else
random.
"""

from __future__ import annotations

import logging
import re
import secrets
import zlib
from pathlib import Path

from gear_optimizer import settings
from gear_optimizer.chart import read_header
from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.settings import DIFFICULTIES, RunSettings
from gear_optimizer.store import db, schema

logger = logging.getLogger(__name__)

_SOLVE_ORDER = (PRECISE, NON_PRECISE)


def build_queue(run: RunSettings, context: SharedRunContext, *, solved_before: float | None = None) -> list[SongTask]:
    """The run's solves in queue order, each SongRepeats run a task. `solved_before` (a pass relaunched after a
    memory-guard restart) leaves out the solves the database stored at or after it."""
    charts = [chart for difficulty in _difficulties(run) for chart in _charts(difficulty, run)]
    last_solved = _last_solved(charts)
    solves = [
        (chart, mode)
        for chart in charts
        for mode in _modes(chart)
        if solved_before is None or last_solved.get((mode, chart.name), 0.0) < solved_before
    ]
    solves.sort(key=lambda solve: _queue_key(solve, last_solved))
    tasks = _seeded_tasks(solves, run, context)
    if run.song_queue_limit:
        tasks = tasks[: run.song_queue_limit]
    unsolved = sum(1 for chart, mode in solves if (mode, chart.name) not in last_solved)
    logger.info(f"[Queue] {len(tasks)} run(s) of {len(solves)} solve(s) ({unsolved} never stored) from {len(charts)} "
                f"chart(s) (Difficulty={run.difficulty}, SongQueueLimit={run.song_queue_limit})")
    return tasks


class _Chart:
    __slots__ = ("path", "name", "difficulty", "header")

    def __init__(self, path: Path, difficulty: str, header: dict[str, str]):
        name = header.get("Song Name", "")
        if not name:
            raise ValueError(f"{path}: chart has no Song Name header")
        self.path, self.name, self.difficulty, self.header = str(path), name, difficulty, header


def _difficulties(run: RunSettings) -> tuple[str, ...]:
    wanted = run.difficulty.strip().capitalize()
    return (wanted,) if wanted in DIFFICULTIES else DIFFICULTIES


def _color_filter(raw: str) -> set[str] | None:
    """The colors a target allows, lowercased; None when it allows every color."""
    colors = {token.strip().lower() for token in re.split(r"[,|/]", raw or "") if token.strip()}
    return None if not colors or colors & {"all", "any", "*"} else colors


def _charts(difficulty: str, run: RunSettings) -> list[_Chart]:
    name_filter = run.song_name.strip().lower()
    primary, secondary = _color_filter(run.target_primary), _color_filter(run.target_secondary)
    folder = settings.paths().chart_dir(difficulty)
    out = []
    for path in sorted(folder.glob("*.txt")) if folder.is_dir() else ():
        chart = _Chart(path, difficulty, read_header(path))
        colors = (chart.header.get("Primary Color", "").strip().lower(),
                  chart.header.get("Secondary Color", "").strip().lower())
        if name_filter in chart.name.lower() and (primary is None or colors[0] in primary) and (
            secondary is None or colors[1] in secondary
        ):
            out.append(chart)
    return out


def _modes(chart: _Chart) -> tuple[str, ...]:
    """The timing modes a chart is solved in: its Timing Mode header's (a custom solve's), else both."""
    mode = chart.header.get("Timing Mode", "").strip().lower()
    return (mode,) if mode else _SOLVE_ORDER


def _last_solved(charts: list[_Chart]) -> dict[tuple[str, str], float]:
    """(mode, song) -> when the results database last stored a solve of it."""
    names = {chart.name for chart in charts}
    conn = schema.connect(settings.paths().database)
    try:
        return {(mode, name): when for mode in _SOLVE_ORDER for name, when in db.last_updated(conn, mode, names).items()}
    finally:
        conn.close()


def _queue_key(solve: tuple[_Chart, str], last_solved: dict[tuple[str, str], float]) -> tuple:
    chart, mode = solve
    when = last_solved.get((mode, chart.name))
    return (when is not None, when or 0.0, chart.name.casefold(), DIFFICULTIES.index(chart.difficulty), chart.path,
            _SOLVE_ORDER.index(mode))


def _seeded_tasks(solves: list[tuple[_Chart, str]], run: RunSettings, context: SharedRunContext) -> list[SongTask]:
    seed_base = settings.ga_seed()
    used: set[int] = set()
    tasks = []
    for chart, mode in solves:
        for repeat in range(1, run.song_repeats + 1):
            if seed_base is not None:
                crc = zlib.crc32(f"{chart.name}\0{mode}".encode("utf-8", errors="replace"))
                seed = ((seed_base & 0xFFFFFFFF) + crc + repeat * 0x9E3779B1) & 0xFFFFFFFF
                while seed in used:
                    seed = (seed + 1) & 0xFFFFFFFF
            else:
                seed = secrets.randbits(32)
                while seed in used:
                    seed = secrets.randbits(32)
            used.add(seed)
            tasks.append(SongTask(chart.path, chart.name, mode, context, seed, repeat, run.song_repeats))
    return tasks
