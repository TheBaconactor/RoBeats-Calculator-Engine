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


def loadout_totals(stats: Mapping[str, int], primary_color: str, secondary_color: str) -> tuple[int, ...]:
    """A Stats row as the gem searches read a loadout: (PP, CM, FM, primary, secondary, FT, FF)."""
    return (
        stats["Perfect Points"],
        stats["Combo Multiplier"],
        stats["Fever Multiplier"],
        stats.get(primary_color, 0),
        stats.get(secondary_color, 0),
        stats["Fever Time"],
        stats["Fever Fill Rate"],
    )


def build_stats_dict(values: Sequence[int] | np.ndarray) -> dict[str, int]:
    """A STAT_NAMES-order vector as a Stats row."""
    return {name: int(values[idx]) for idx, name in enumerate(STAT_NAMES)}
