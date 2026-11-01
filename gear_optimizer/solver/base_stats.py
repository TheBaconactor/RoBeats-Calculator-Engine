"""The solver's stat-vector layout (STAT_NAMES order) and its conversions to and from Stats rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from ..core.gem_defs import BASE_STAT_KEYS

STAT_NAMES: tuple[str, ...] = BASE_STAT_KEYS

COLOR_TO_STAT_INDEX: dict[str, int] = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}


def build_stats_array(stats: Mapping[str, int]) -> np.ndarray:
    """A Stats row as an int32 vector in STAT_NAMES order."""
    return np.asarray([stats[name] for name in STAT_NAMES], dtype=np.int32)


def build_stats_dict(values: Sequence[int] | np.ndarray) -> dict[str, int]:
    """A STAT_NAMES-order vector as a Stats row."""
    return {name: int(values[idx]) for idx, name in enumerate(STAT_NAMES)}
