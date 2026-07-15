"""Native FG scoring for an exact Base candidate surface on the GPU owner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from gear_optimizer.core.constants import TOTAL_GEM_BUDGET

if TYPE_CHECKING:
    from gear_optimizer.solver.exact_base_search import ExactBasePipelineResult
    from gear_optimizer.solver.solver_common import SolverContext
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgFusedOwnerScoreRow,
    )


@dataclass(frozen=True, slots=True)
class ExactBaseOwnerResult:
    """One owner-turn result: exact Base surface plus native FG scores."""

    base_result: ExactBasePipelineResult
    fg_owner_score: dict[tuple[int, ...], FgFusedOwnerScoreRow]


def score_native_fg_candidate_surface(
    *,
    base_stats7: np.ndarray,
    context: SolverContext,
    scoring_bundle: Any,
    calc_song: dict[str, Any],
) -> dict[tuple[int, ...], FgFusedOwnerScoreRow]:
    """Score the typed Base surface directly, without a packed handoff ABI."""

    if scoring_bundle is None:
        raise ValueError(
            "native FG scoring requires the startup-built song scoring bundle"
        )
    if not isinstance(calc_song, dict):
        raise ValueError("native FG scoring requires a resolved FG calculation song")
    if not isinstance(context.ref_arrays, dict):
        raise ValueError("native FG scoring requires reference arrays")

    base_components = np.asarray(base_stats7)
    if not np.issubdtype(base_components.dtype, np.integer):
        raise TypeError("native FG base_stats7 must contain integers")
    if base_components.ndim != 2 or base_components.shape[1] != 7:
        raise ValueError(
            f"native FG base_stats7 must have shape (N,7); got {base_components.shape}"
        )
    if int(base_components.shape[0]) <= 0:
        raise ValueError("native FG scoring requires at least one Base candidate")
    i32 = np.iinfo(np.int32)
    if np.any(base_components < i32.min) or np.any(base_components > i32.max):
        raise OverflowError("native FG base_stats7 exceeds the int32 scoring contract")

    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        score_fused_owner_base_components_on_gpu_owner,
    )

    scores = score_fused_owner_base_components_on_gpu_owner(
        base_components=np.ascontiguousarray(base_components, dtype=np.int32),
        calc_song=calc_song,
        ref_arrays=context.ref_arrays,
        selected_color=str(context.selected_color or ""),
        scoring_bundle=scoring_bundle,
        total_budget=int(TOTAL_GEM_BUDGET),
    )
    expected_keys = {tuple(int(value) for value in row) for row in base_components}
    if not isinstance(scores, dict) or set(scores) != expected_keys:
        raise RuntimeError(
            "native FG owner result does not cover the typed Base candidate surface"
        )
    return scores


__all__ = ["ExactBaseOwnerResult", "score_native_fg_candidate_surface"]
