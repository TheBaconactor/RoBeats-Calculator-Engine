"""Exact-scored Base candidates and the bounded Base-to-FG funnel surface.

The outer exact search reconstructs loadouts as nine registry item IDs.  This
module owns the remainder of their Base lifecycle:

* exact GPU scoring with the canonical skyline inner solver,
* deterministic effective-loadout deduplication and Base ranking,
* exact result-row materialization for the retained funnel, and
* the pre-gem ``base_stats7`` carried into the FG owner scorer.

The typed arrays below are the canonical in-process contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags, normalize_color_flags
from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET
from gear_optimizer.solver.fg_effective_dedup import (
    effective_tables_for_context,
    select_top_base_fg_candidates_reference,
)
from gear_optimizer.solver.solver_common import SolverContext


N_LOADOUT_SLOTS = 9
N_GEAR_SLOTS = 6
N_MINI_SLOTS = 3
N_RESULT_STATS = 7
N_BASE_STATS = 7


def _i32_copy(value: Any, *, name: str, ndim: int, readonly: bool) -> np.ndarray:
    source = np.asarray(value)
    if not np.issubdtype(source.dtype, np.integer):
        raise TypeError(f"{name} must contain integers; got dtype {source.dtype}")
    if source.size:
        i32 = np.iinfo(np.int32)
        if np.any(source < i32.min) or np.any(source > i32.max):
            raise OverflowError(f"{name} contains a value outside the int32 contract")
    array = np.array(source, dtype=np.int32, copy=True, order="C")
    if array.ndim != int(ndim):
        raise ValueError(f"{name} must be {ndim}-D; got shape {array.shape}")
    if readonly:
        array.setflags(write=False)
    return array


def _readonly_i32(value: Any, *, name: str, ndim: int) -> np.ndarray:
    return _i32_copy(value, name=name, ndim=ndim, readonly=True)


@dataclass(frozen=True, slots=True)
class ExactScoredBaseCandidates:
    """Every reconstructed candidate and its exact Base score."""

    candidate_ids: np.ndarray
    base_scores: np.ndarray

    def __post_init__(self) -> None:
        ids = _readonly_i32(self.candidate_ids, name="candidate_ids", ndim=2)
        scores = _readonly_i32(self.base_scores, name="base_scores", ndim=1)
        n = int(ids.shape[0])
        if ids.shape != (n, N_LOADOUT_SLOTS):
            raise ValueError(
                f"candidate_ids must have shape (N,{N_LOADOUT_SLOTS}); got {ids.shape}"
            )
        if scores.shape != (n,):
            raise ValueError(f"base_scores must have shape ({n},); got {scores.shape}")
        if n <= 0:
            raise ValueError("exact Base candidate set must not be empty")
        if np.any(ids <= 0):
            raise ValueError("exact Base candidate IDs must all be positive registry IDs")
        if np.any(scores <= 0):
            bad = int(np.flatnonzero(scores <= 0)[0])
            raise RuntimeError(
                "exact Base scoring produced a non-positive score at candidate "
                f"{bad}: {int(scores[bad])}"
            )
        object.__setattr__(self, "candidate_ids", ids)
        object.__setattr__(self, "base_scores", scores)

    @property
    def count(self) -> int:
        return int(self.candidate_ids.shape[0])

    def take(self, indices: np.ndarray) -> "ExactScoredBaseCandidates":
        selected = np.asarray(indices, dtype=np.int64).reshape(-1)
        if selected.size <= 0:
            raise ValueError("exact Base candidate selection must not be empty")
        if np.any(selected < 0) or np.any(selected >= self.count):
            raise IndexError("exact Base candidate selection index is out of range")
        return ExactScoredBaseCandidates(
            candidate_ids=self.candidate_ids[selected],
            base_scores=self.base_scores[selected],
        )


@dataclass(frozen=True, slots=True)
class ExactBaseCandidateSurface:
    """Effective-unique Base-ranked candidates ready for the FG funnel."""

    candidate_ids: np.ndarray
    base_scores: np.ndarray
    result_rows: np.ndarray
    base_stats7: np.ndarray

    def __post_init__(self) -> None:
        ids = _readonly_i32(self.candidate_ids, name="candidate_ids", ndim=2)
        scores = _readonly_i32(self.base_scores, name="base_scores", ndim=1)
        results = _readonly_i32(self.result_rows, name="result_rows", ndim=2)
        base_stats = _readonly_i32(self.base_stats7, name="base_stats7", ndim=2)
        n = int(ids.shape[0])
        if ids.shape != (n, N_LOADOUT_SLOTS):
            raise ValueError(
                f"candidate_ids must have shape (N,{N_LOADOUT_SLOTS}); got {ids.shape}"
            )
        if n <= 0:
            raise ValueError("exact Base candidate surface must not be empty")
        expected_vectors = {
            "base_scores": (scores.shape, (n,)),
            "result_rows": (results.shape, (n, N_RESULT_STATS)),
            "base_stats7": (base_stats.shape, (n, N_BASE_STATS)),
        }
        for name, (actual, expected) in expected_vectors.items():
            if actual != expected:
                raise ValueError(f"{name} must have shape {expected}; got {actual}")
        if np.any(ids <= 0) or np.any(scores <= 0):
            raise ValueError("exact Base surface requires positive IDs and scores")
        if not np.array_equal(results[:, 0], scores):
            raise RuntimeError(
                "exact Base score scan and retained result materialization disagree"
            )
        if np.any(scores[:-1] < scores[1:]):
            raise RuntimeError("exact Base candidate surface is not Base-score descending")
        object.__setattr__(self, "candidate_ids", ids)
        object.__setattr__(self, "base_scores", scores)
        object.__setattr__(self, "result_rows", results)
        object.__setattr__(self, "base_stats7", base_stats)

    @property
    def count(self) -> int:
        return int(self.candidate_ids.shape[0])

    @property
    def best_score(self) -> int:
        return int(self.base_scores[0])

    @property
    def best_ids(self) -> np.ndarray:
        return self.candidate_ids[0]

    @property
    def best_result(self) -> np.ndarray:
        return self.result_rows[0]


def _canonical_candidate_ids(context: SolverContext, value: Any) -> np.ndarray:
    ids = _i32_copy(value, name="candidate batch", ndim=2, readonly=False)
    if ids.ndim != 2 or ids.shape[1:] != (N_LOADOUT_SLOTS,):
        raise ValueError(
            f"candidate batch must have shape (N,{N_LOADOUT_SLOTS}); got {ids.shape}"
        )
    if int(ids.shape[0]) <= 0:
        raise ValueError("candidate batch must not be empty")
    if np.any(ids <= 0):
        raise ValueError("candidate batch contains an empty or negative registry ID")

    slot_start = np.asarray(context.registry.slot_start, dtype=np.int64).reshape(-1)
    slot_count = np.asarray(context.registry.slot_count, dtype=np.int64).reshape(-1)
    if slot_start.shape != (N_LOADOUT_SLOTS,) or slot_count.shape != (N_LOADOUT_SLOTS,):
        raise ValueError(
            "solver registry must expose nine slot boundaries; "
            f"got starts={slot_start.shape}, counts={slot_count.shape}"
        )
    if np.any(slot_count <= 0):
        raise ValueError("solver registry contains an empty candidate slot")
    for slot in range(N_LOADOUT_SLOTS):
        low = int(slot_start[slot])
        high = low + int(slot_count[slot])
        invalid = (ids[:, slot] < low) | (ids[:, slot] >= high)
        if np.any(invalid):
            row = int(np.flatnonzero(invalid)[0])
            raise ValueError(
                f"candidate row {row} slot {slot} references item ID "
                f"{int(ids[row, slot])}, outside [{low}, {high})"
            )

    # Mini positions are semantically interchangeable.  Canonicalizing them at
    # ingestion makes exact duplicate handling and all downstream tie-breaks
    # deterministic without changing scoring.
    ids[:, N_GEAR_SLOTS:] = np.sort(ids[:, N_GEAR_SLOTS:], axis=1)
    return np.ascontiguousarray(ids, dtype=np.int32)


def _color_evaluation_kwargs(context: SolverContext) -> dict[str, int]:
    flags = normalize_color_flags(context.color_flags).as_dict()
    if any(int(value) not in (0, 1) for value in flags.values()):
        raise ValueError("solver color flags must be binary")
    expected = build_color_flags(
        str(context.p_color or ""),
        str(context.s_color or ""),
        str(context.selected_color or ""),
    )
    if flags != expected:
        raise ValueError(
            "solver color flags disagree with the song color context: "
            f"actual={flags}, expected={expected}"
        )
    return {name: int(value) for name, value in flags.items()}


def _evaluate_ids(
    context: SolverContext,
    candidate_ids: np.ndarray,
    *,
    materialize_mode: str,
) -> np.ndarray:
    from gear_optimizer.solver.taichi_gem.api import skyline_operations

    n = int(candidate_ids.shape[0])
    uploaded = skyline_operations.skyline_upload_loadout_indices(
        candidate_ids,
        n_slots=N_LOADOUT_SLOTS,
    )
    if int(uploaded) != n:
        raise RuntimeError(f"exact Base GPU upload truncated candidates: {uploaded} != {n}")
    skyline_operations.skyline_evaluate_loadouts(
        n,
        N_LOADOUT_SLOTS,
        total_budget=int(TOTAL_GEM_BUDGET),
        gem_scale_fever=int(GEM_SCALE_FEVER),
        song_slot=int(context.song_slot),
        materialize_mode=str(materialize_mode),
        **_color_evaluation_kwargs(context),
    )
    if materialize_mode == "scores":
        return np.asarray(skyline_operations.skyline_download_scores(n), dtype=np.int32)
    if materialize_mode == "results":
        return np.asarray(skyline_operations.skyline_download_results(n), dtype=np.int32)
    raise AssertionError(f"unsupported exact Base materialization mode {materialize_mode!r}")


def rank_exact_base_candidates(
    scored: ExactScoredBaseCandidates,
    *,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
    limit: int,
) -> ExactScoredBaseCandidates:
    """Effective-deduplicate and deterministically rank exact-scored rows."""

    limit_i = int(limit)
    if limit_i <= 0:
        raise ValueError(f"exact Base funnel limit must be positive; got {limit_i}")
    gear_rank = np.asarray(gear_name_rank, dtype=np.int32).reshape(-1)
    mini_sig = np.asarray(mini_sig_id, dtype=np.int32).reshape(-1)
    max_id = int(np.max(scored.candidate_ids))
    if gear_rank.shape[0] <= max_id or mini_sig.shape[0] <= max_id:
        raise ValueError(
            "effective-equivalence tables do not cover the candidate registry IDs: "
            f"max_id={max_id}, gear={gear_rank.shape[0]}, minis={mini_sig.shape[0]}"
        )
    gear_ids = scored.candidate_ids[:, :N_GEAR_SLOTS]
    mini_ids = scored.candidate_ids[:, N_GEAR_SLOTS:]
    if np.any(gear_rank[gear_ids] <= 0):
        raise ValueError("gear effective-equivalence table has an unbound candidate ID")
    if np.any(mini_sig[mini_ids] <= 0):
        raise ValueError("mini effective-equivalence table has an unbound candidate ID")
    selected = select_top_base_fg_candidates_reference(
        base_scores=scored.base_scores,
        gear_ids=gear_ids,
        mini_ids=mini_ids,
        gear_name_rank=gear_rank,
        mini_sig_id=mini_sig,
        limit=limit_i,
    )
    if selected.size <= 0:
        raise RuntimeError("exact Base ranking produced an empty candidate funnel")
    return scored.take(selected)


def rank_exact_base_candidates_for_context(
    context: SolverContext,
    scored: ExactScoredBaseCandidates,
    *,
    limit: int,
) -> ExactScoredBaseCandidates:
    gear_name_rank, mini_sig_id = effective_tables_for_context(
        context.registry,
        primary_color=str(context.p_color or ""),
        secondary_color=str(context.s_color or ""),
        selected_color=str(context.selected_color or ""),
    )
    return rank_exact_base_candidates(
        scored,
        gear_name_rank=gear_name_rank,
        mini_sig_id=mini_sig_id,
        limit=int(limit),
    )


def compute_base_stats7(context: SolverContext, candidate_ids: np.ndarray) -> np.ndarray:
    """Compute authoritative pre-gem FG inputs for registry loadouts.

    No clipping occurs here.  Signed catalog contributions are valid and must
    survive into the complete pre-gem sum; the inner scoring kernels own stat
    caps at the points where those caps are semantically required.
    """

    ids = _canonical_candidate_ids(context, candidate_ids)
    if "item_stats" not in context.gpu_arrays:
        raise ValueError("solver GPU item arrays are missing item_stats")
    item_stats = np.asarray(context.gpu_arrays["item_stats"], dtype=np.int64)
    if item_stats.ndim != 2 or item_stats.shape[1] != 10:
        raise ValueError(f"item_stats must have shape (N,10); got {item_stats.shape}")
    if int(np.max(ids)) >= int(item_stats.shape[0]):
        raise ValueError("candidate IDs exceed the uploaded item stat table")
    fixed = np.asarray(context.base_fixed_stats_arr, dtype=np.int64).reshape(-1)
    if fixed.shape != (10,):
        raise ValueError(f"base_fixed_stats_arr must have shape (10,); got {fixed.shape}")
    totals = item_stats[ids].sum(axis=1, dtype=np.int64) + fixed

    color_index = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    primary = str(context.p_color or "")
    secondary = str(context.s_color or "")
    if primary not in color_index:
        raise ValueError(f"invalid primary color for Base stats: {primary!r}")
    if secondary and secondary not in color_index:
        raise ValueError(f"invalid secondary color for Base stats: {secondary!r}")
    p_val = totals[:, color_index[primary]]
    s_val = totals[:, color_index[secondary]] if secondary else np.zeros(ids.shape[0], dtype=np.int64)
    out64 = np.column_stack(
        (
            totals[:, 0],
            totals[:, 1],
            totals[:, 2],
            p_val,
            s_val,
            totals[:, 3],
            totals[:, 4],
        )
    )
    i32 = np.iinfo(np.int32)
    if np.any(out64 < i32.min) or np.any(out64 > i32.max):
        raise OverflowError("pre-gem Base stats exceed the int32 scoring contract")
    return np.ascontiguousarray(out64, dtype=np.int32)


def materialize_exact_base_candidate_surface(
    context: SolverContext,
    ranked: ExactScoredBaseCandidates,
) -> ExactBaseCandidateSurface:
    """Materialize exact inner-solver rows for an already ranked funnel."""

    results = np.asarray(
        _evaluate_ids(context, ranked.candidate_ids, materialize_mode="results"),
        dtype=np.int32,
    )
    expected = (ranked.count, N_RESULT_STATS)
    if results.shape != expected:
        raise RuntimeError(
            f"exact Base result download returned {results.shape}, expected {expected}"
        )
    if not np.array_equal(results[:, 0], ranked.base_scores):
        mismatches = np.flatnonzero(results[:, 0] != ranked.base_scores)
        row = int(mismatches[0])
        raise RuntimeError(
            "exact Base score scan and retained result materialization disagree at "
            f"row {row}: {int(ranked.base_scores[row])} != {int(results[row, 0])}"
        )
    return ExactBaseCandidateSurface(
        candidate_ids=ranked.candidate_ids,
        base_scores=ranked.base_scores,
        result_rows=results,
        base_stats7=compute_base_stats7(context, ranked.candidate_ids),
    )


__all__ = [
    "ExactBaseCandidateSurface",
    "ExactScoredBaseCandidates",
    "compute_base_stats7",
    "materialize_exact_base_candidate_surface",
    "rank_exact_base_candidates",
    "rank_exact_base_candidates_for_context",
]
