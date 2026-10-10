"""The startup frontier caches: before scoring, each queued chart's timeline and FG response frontier caches in each
timing mode it is solved in are verified and the missing ones built (timeline first: the FG build reads it)."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Mapping
from typing import TextIO

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.fg_response_frontier_cache_prebuild import FG_RESPONSE_FRONTIER_PREBUILD
from gear_optimizer.solver.frontier_cache import prebuild_frontier_cache
from gear_optimizer.solver.timeline_frontier_cache_prebuild import TIMELINE_FRONTIER_PREBUILD


def run_startup_cpu_work(
    *,
    charts_by_mode: Mapping[str, Iterable[str]],
    curves: StatCurves,
    announce_stream: TextIO | None = None,
    build_missing: bool = True,
    authorize_destructive_rotation: bool = False,
) -> None:
    """Verify (and with `build_missing`, build) both caches of every chart in each of its modes; the summary lines go to
    `announce_stream` (default stdout). Raises when a cache could not be verified or built."""
    stream = announce_stream or sys.stdout
    charts_by_mode = {mode: list(charts) for mode, charts in charts_by_mode.items()}
    songs = len({os.path.abspath(chart).casefold() for charts in charts_by_mode.values() for chart in charts})
    stream.write(f"[Startup][Cache] Verifying exact timeline + FG response frontier caches for {songs} queued song(s)\n")
    failures = {}
    for label, prebuild in (("Timeline frontier cache", TIMELINE_FRONTIER_PREBUILD),
                            ("FG response-frontier cache", FG_RESPONSE_FRONTIER_PREBUILD)):
        summary = prebuild_frontier_cache(prebuild, charts_by_mode=charts_by_mode, curves=curves,
                                          build_missing=build_missing,
                                          authorize_destructive_rotation=authorize_destructive_rotation)
        stream.write(
            f"[Startup][Cache] {label} ready: total={summary.total} built={summary.built} disk={summary.disk} "
            f"memory={summary.memory} failures={summary.failures} elapsed={summary.elapsed_ms / 1000.0:.1f}s\n"
        )
        stream.flush()
        failures[label] = summary.failures
    if any(failures.values()):
        raise RuntimeError(f"Startup frontier cache prebuild failed: {failures}")
