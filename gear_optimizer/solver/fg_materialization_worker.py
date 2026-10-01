"""Process-isolated host materialization for the fused GA -> FG handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.pipeline.results import SolvedFg, SolvedLoadout
from gear_optimizer.solver.fg_response_scoring.planner import (
    FgResponseFrontierPreparedBatch,
    FgResponseFrontierPreparedPlan,
)


@dataclass(frozen=True, slots=True)
class FgMaterializationBatch:
    """The exact subset of a prepared GPU batch read by host materialization."""

    started: float
    base_components: np.ndarray
    selected_color: str
    song: TimedSong
    curves: StatCurves
    scoring_bundle: Any


@dataclass(frozen=True, slots=True)
class FgMaterializationRequest:
    song_key: str
    plan: FgResponseFrontierPreparedPlan
    owner_score_map: dict[tuple[int, ...], Any]


@dataclass(frozen=True, slots=True)
class FgMaterializationResult:
    results: tuple[tuple[SolvedLoadout, SolvedFg], ...]  # every evaluated FG result, best FG score first


def build_fg_materialization_request(song: Any) -> FgMaterializationRequest:
    """Project a prepared song onto the picklable host-materialization contract."""

    runtime = getattr(song, "runtime", song)
    plan = getattr(runtime.fg, "fg_response_frontier_plan", None)
    if plan is None:
        raise RuntimeError("FG process materialization requires a prepared exact scoring plan")
    owner_score_map = getattr(runtime.fg, "fg_owner_score_map", None)
    if owner_score_map is None:
        raise RuntimeError("FG process materialization requires the fused owner FG score map")

    timed_song = plan.song
    curves = plan.curves
    prepared_batches = []
    for prepared in plan.prepared_batches:
        batch = prepared.batch
        compact_batch = FgMaterializationBatch(
            started=float(batch.started),
            base_components=np.ascontiguousarray(batch.base_components, dtype=np.int32),
            selected_color=str(batch.selected_color or ""),
            song=timed_song,
            curves=curves,
            scoring_bundle=batch.scoring_bundle,
        )
        compact_rows = tuple((tuple(cache_key), dict(base_stats)) for cache_key, base_stats in prepared.rows)
        prepared_batches.append(
            FgResponseFrontierPreparedBatch(
                rows=compact_rows,
                batch=compact_batch,
            )
        )

    compact_plan = FgResponseFrontierPreparedPlan(
        song=timed_song,
        curves=curves,
        jobs=plan.jobs,
        prepared_batches=tuple(prepared_batches),
    )
    song_key = str(
        getattr(getattr(song, "config", None), "task_key", "")
        or getattr(getattr(song, "config", None), "song_name", "")
        or ""
    )
    return FgMaterializationRequest(
        song_key=song_key,
        plan=compact_plan,
        owner_score_map=dict(owner_score_map),
    )


def materialize_fg_request(request: FgMaterializationRequest) -> FgMaterializationResult:
    """Run exact host FG materialization without sharing the GPU owner's GIL."""

    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

    try:
        results = FgResponseScoringService.materialize_from_owner_score_map(request.plan, request.owner_score_map)
        return FgMaterializationResult(results=tuple(results))
    finally:
        # Geometry/frontier memo entries are useful only inside this song's materialization.
        # Drop them before the worker accepts another song so a long live run stays bounded.
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
            release_fg_response_song_memory,
        )

        released: set[tuple[Any, ...]] = set()
        for prepared in request.plan.prepared_batches:
            cache_key = tuple(getattr(prepared.batch.scoring_bundle, "cache_key", ()) or ())
            if cache_key and cache_key not in released:
                released.add(cache_key)
                release_fg_response_song_memory(cache_key)
