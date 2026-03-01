"""
In-code placement guide for avoiding duplicated logic.

This module is intentionally lightweight and import-safe so developers can inspect
canonical ownership from REPL/tests/scripts without touching markdown docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class PlacementHint:
    """Describes where a concern should live in the repository."""

    concern: str
    owner: str
    paths: tuple[str, ...]
    why: str


PLACEMENT_HINTS: tuple[PlacementHint, ...] = (
    PlacementHint(
        concern="config, env vars, shared constants, path discovery",
        owner="gear_optimizer.core",
        paths=(
            "gear_optimizer/core/config.py",
            "gear_optimizer/core/env_config.py",
            "gear_optimizer/core/constants.py",
        ),
        why="Single source of truth for runtime knobs and foundational settings.",
    ),
    PlacementHint(
        concern="database schema, persistence, loadout storage",
        owner="gear_optimizer.data",
        paths=("gear_optimizer/data/database.py", "gear_optimizer/helpers/song_helpers/persistence.py"),
        why="Keeps DB contracts centralized and prevents drift between save paths.",
    ),
    PlacementHint(
        concern="song pipeline orchestration and per-song flow",
        owner="gear_optimizer.pipeline",
        paths=("gear_optimizer/pipeline/song_processor.py", "gear_optimizer/pipeline/post_processor.py"),
        why="Orchestration belongs in pipeline, not in scoring/math helpers.",
    ),
    PlacementHint(
        concern="GA loop, scoring orchestration, GPU execution and Taichi kernels",
        owner="gear_optimizer.solver",
        paths=(
            "gear_optimizer/solver/genetic.py",
            "gear_optimizer/solver/scoring/",
            "gear_optimizer/solver/taichi_gem/",
        ),
        why="Algorithm hot paths are grouped for parity and performance tuning.",
    ),
    PlacementHint(
        concern="reusable helper logic for song/GA glue code",
        owner="gear_optimizer.helpers",
        paths=("gear_optimizer/helpers/ga_helpers/", "gear_optimizer/helpers/song_helpers/"),
        why="Avoids copy-pasting pipeline/solver glue into multiple call sites.",
    ),
    PlacementHint(
        concern="maintained utilities (bench, verify, db maintenance, profiling)",
        owner="tools",
        paths=("tools/bench/", "tools/db/", "tools/profile/", "tools/verify/", "tools/dev/"),
        why="Production runtime code stays clean while dev utilities remain discoverable.",
    ),
    PlacementHint(
        concern="ad-hoc one-off probes and temporary investigations",
        owner="scripts",
        paths=("scripts/",),
        why="Keeps experimental workflows out of maintained utility surfaces.",
    ),
)


def iter_placement_hints() -> Iterable[PlacementHint]:
    """Return all placement hints in canonical order."""
    return PLACEMENT_HINTS


def find_hints(query: str) -> list[PlacementHint]:
    """
    Find placement hints by keyword.

    Matching is case-insensitive and checks concern, owner, path fragments, and rationale text.
    """
    needle = str(query or "").strip().lower()
    if not needle:
        return list(PLACEMENT_HINTS)

    matches: list[PlacementHint] = []
    for hint in PLACEMENT_HINTS:
        haystack = " ".join((hint.concern, hint.owner, hint.why, " ".join(hint.paths))).lower()
        if needle in haystack:
            matches.append(hint)
    return matches


def owner_for_path(path: str) -> Optional[str]:
    """Return the owning module surface for a path fragment, if one matches."""
    path_norm = str(path or "").replace("\\", "/").lower()
    for hint in PLACEMENT_HINTS:
        for known in hint.paths:
            normalized_known = known.replace("\\", "/").lower()
            if normalized_known in path_norm or path_norm.startswith(normalized_known):
                return hint.owner
    return None
