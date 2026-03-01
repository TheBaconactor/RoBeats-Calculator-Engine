"""
In-code placement map for the scoring package.

This is a code-native guide to reduce duplication when extending scoring behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ScoringPlacementHint:
    """Describes the canonical location for a scoring concern."""

    concern: str
    owner: str
    paths: tuple[str, ...]
    entrypoints: tuple[str, ...]
    why: str


SCORING_PLACEMENT_HINTS: tuple[ScoringPlacementHint, ...] = (
    ScoringPlacementHint(
        concern="single stats snapshot scoring without gem search",
        owner="stats_scoring",
        paths=("gear_optimizer/solver/scoring/stats_scoring.py",),
        entrypoints=("evaluate_stats_score",),
        why="Keeps direct score math in one place for CPU/GPU parity checks.",
    ),
    ScoringPlacementHint(
        concern="full gem allocation search (FT/FF + PP/CM/FM/OV)",
        owner="fever_solver",
        paths=("gear_optimizer/solver/scoring/fever_solver.py",),
        entrypoints=("solve_best_fever_combination", "precompute_fever_timelines"),
        why="Centralizes allocation logic and avoids re-implementing search loops elsewhere.",
    ),
    ScoringPlacementHint(
        concern="force-greats scoring, hill climb, and hit-sim delta summaries",
        owner="force_greats",
        paths=("gear_optimizer/solver/scoring/force_greats.py",),
        entrypoints=(
            "evaluate_force_greats",
            "evaluate_fg_with_gem_iteration",
            "run_force_greats_hill_climb",
            "apply_force_greats_to_result",
        ),
        why="FG behavior is a separate contract; keep it unified to prevent drift in DB/console outputs.",
    ),
    ScoringPlacementHint(
        concern="population-level genome evaluation and GPU dispatch routing",
        owner="genome_evaluation",
        paths=("gear_optimizer/solver/scoring/genome_evaluation.py",),
        entrypoints=("batch_evaluate_genomes", "prepare_gpu_batch_eval_plan", "finalize_gpu_batch_eval_plan"),
        why="Ensures one canonical path for cache partitioning and worker/executor GPU routing.",
    ),
    ScoringPlacementHint(
        concern="shared GPU solver singleton/caches and synchronization lock",
        owner="gpu_solver",
        paths=("gear_optimizer/solver/scoring/gpu_solver.py",),
        entrypoints=("_get_gpu_solver", "_GPU_LOCK", "GEM_SOLVER_CACHE"),
        why="Avoids fragmented cache/lock ownership across modules.",
    ),
    ScoringPlacementHint(
        concern="pure stat recomposition from base stats + gem counts",
        owner="stats_ops",
        paths=("gear_optimizer/solver/scoring/stats_ops.py",),
        entrypoints=("apply_gems_to_base_stats",),
        why="Reusable pure helper for rebuilding final stats payloads.",
    ),
)


def iter_scoring_hints() -> Iterable[ScoringPlacementHint]:
    """Return all scoring placement hints in canonical order."""
    return SCORING_PLACEMENT_HINTS


def find_scoring_hints(query: str) -> list[ScoringPlacementHint]:
    """
    Find scoring placement hints by keyword.

    Matching checks concern text, owner, path fragments, entrypoints, and rationale.
    """

    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    needle = _norm(query or "")
    if not needle:
        return list(SCORING_PLACEMENT_HINTS)

    matches: list[ScoringPlacementHint] = []
    for hint in SCORING_PLACEMENT_HINTS:
        haystack = _norm(
            " ".join((hint.concern, hint.owner, hint.why, " ".join(hint.paths), " ".join(hint.entrypoints)))
        )
        if needle in haystack:
            matches.append(hint)
    return matches
