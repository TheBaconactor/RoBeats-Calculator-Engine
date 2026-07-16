"""Process-isolated host materialization for the fused GA -> FG handoff."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_entry_names
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
    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    scoring_bundle: Any


@dataclass(frozen=True, slots=True)
class FgMaterializationRequest:
    song_key: str
    plan: FgResponseFrontierPreparedPlan
    owner_score_map: dict[tuple[int, ...], Any]


@dataclass(frozen=True, slots=True)
class FgMaterializationResult:
    variants: tuple[dict[str, Any], ...]
    wall_seconds: float
    cpu_seconds: float


def initialize_fg_materialization_worker() -> None:
    """Keep spawned workers from concurrently writing the parent's JSONL trace."""

    for name in (
        "METAFINDER_PROFILE_EVENTS",
        "METAFINDER_PROFILE_EVENTS_PATH",
        "PROFILE_EVENTS",
        "PROFILE_EVENTS_PATH",
    ):
        os.environ.pop(name, None)


def _compact_materialized_variant(variant: dict[str, Any]) -> dict[str, Any]:
    """Keep the canonical persistence/progress surface and drop reducer internals."""

    return {
        "data": variant.get("data") or {},
        "gear": list(variant.get("gear") or []),
        "minis": list(variant.get("minis") or []),
        "score": int(variant.get("score", 0) or 0),
        "base_score": int(variant.get("base_score", variant.get("score", 0)) or 0),
        "fg_score": int(variant.get("fg_score", 0) or 0),
        "_is_ga": bool(variant.get("_is_ga")),
    }


def _compact_entry(entry: dict[str, Any], eval_data: dict[str, Any]) -> dict[str, Any]:
    """Remove driver-only object graphs after resolving the persisted identity."""

    gear_names, mini_names = materialize_entry_names(entry, mutate=False)
    compact = {
        key: value
        for key, value in entry.items()
        if key not in {"_candidate_ref", "_ga_registry", "eval_data", "gear", "minis"}
    }
    compact["gear"] = list(gear_names)
    compact["minis"] = list(mini_names)
    compact["eval_data"] = eval_data
    return compact


def build_fg_materialization_request(song: Any) -> FgMaterializationRequest:
    """Project a prepared song onto the picklable host-materialization contract."""

    runtime = getattr(song, "runtime", song)
    plan = getattr(runtime.fg, "fg_response_frontier_plan", None)
    if plan is None:
        raise RuntimeError("FG process materialization requires a prepared exact scoring plan")
    owner_score_map = getattr(runtime.fg, "fg_owner_score_map", None)
    if owner_score_map is None:
        raise RuntimeError("FG process materialization requires the fused owner FG score map")

    calc_song = plan.calc_song
    ref_arrays = plan.ref_arrays
    pending_jobs = []
    for entry, eval_data, selected, base_stats, paired_base_score, cache_key in plan.pending_jobs:
        if not isinstance(entry, dict) or not isinstance(eval_data, dict) or not isinstance(base_stats, dict):
            raise ValueError("FG process materialization received an invalid prepared job")
        eval_data_copy = dict(eval_data)
        pending_jobs.append(
            (
                _compact_entry(entry, eval_data_copy),
                eval_data_copy,
                str(selected or ""),
                dict(base_stats),
                int(paired_base_score),
                tuple(cache_key),
            )
        )

    prepared_batches = []
    for prepared in plan.prepared_batches:
        batch = prepared.batch
        compact_batch = FgMaterializationBatch(
            started=float(batch.started),
            base_components=np.ascontiguousarray(batch.base_components, dtype=np.int32),
            selected_color=str(batch.selected_color or ""),
            calc_song=calc_song,
            ref_arrays=ref_arrays,
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
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        pending_jobs=tuple(pending_jobs),
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

    wall_t0 = time.perf_counter()
    cpu_t0 = time.process_time()
    try:
        variants = FgResponseScoringService.materialize_from_owner_score_map(
            request.plan,
            request.owner_score_map,
            include_forced_counts=False,
        )
        return FgMaterializationResult(
            variants=tuple(
                _compact_materialized_variant(variant)
                for variant in (variants or ())
                if isinstance(variant, dict)
            ),
            wall_seconds=max(0.0, time.perf_counter() - wall_t0),
            cpu_seconds=max(0.0, time.process_time() - cpu_t0),
        )
    finally:
        # Geometry/frontier memo entries are useful only inside this song's materialization.
        # Drop them before the worker accepts another song so a long live run stays bounded.
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            release_fg_response_song_memory,
        )

        released: set[tuple[Any, ...]] = set()
        for prepared in request.plan.prepared_batches:
            cache_key = tuple(getattr(prepared.batch.scoring_bundle, "cache_key", ()) or ())
            if cache_key and cache_key not in released:
                released.add(cache_key)
                release_fg_response_song_memory(cache_key)
