"""
Shared helpers for constructing base fixed stats vectors used by GPU paths.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging

import numpy as np

from ..core.gem_defs import BASE_STAT_KEYS
from ..core.utils import safe_int



logger = logging.getLogger(__name__)
STAT_NAMES: tuple[str, ...] = BASE_STAT_KEYS

COLOR_TO_STAT_INDEX: dict[str, int] = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}


def build_stats_list(stats: Mapping[str, Any] | None) -> list[int]:
    src = stats or {}
    return [safe_int(src.get(name, 0), 0) for name in STAT_NAMES]


def build_stats_array(stats: Mapping[str, Any] | None) -> np.ndarray:
    return np.asarray(build_stats_list(stats), dtype=np.int32)


def build_stats_dict(values: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for idx, name in enumerate(STAT_NAMES):
        try:
            out[name] = int(values[idx])
        except Exception as e:
            logger.debug(f"base_stats:build_stats_dict: {e}")
            out[name] = 0
    return out
