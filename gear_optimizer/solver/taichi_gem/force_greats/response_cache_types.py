from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.parsing import env_get

from .response_types import FgResponseFrontierResult

_FG_RESPONSE_CACHE_VERSION = "fg-response-frontier-visible-first-v8"
_MEMORY_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_MEMORY_CACHE_MAX", "4096") or "4096"))
_PAYLOAD_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_PAYLOAD_CACHE_MAX", "8") or "8"))
_BUNDLE_ARRAY_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_BUNDLE_ARRAY_CACHE_MAX", "2") or "2"))
_BUNDLE_KEY_MARKER = "all-stat-keys"
_SCORING_BUNDLE_ARRAY_NAMES = frozenset(
    (
        "stat_keys",
        "frontier_ids",
        "raw_fill_by_ff",
        "non_fever_base_by_ff",
        "real_time_by_ft",
        "total_notes",
        "long_notes",
        "use_forced_great_timing",
        "frontier_meta",
        "first_surface_pool",
        "first_offsets",
        "first_counts",
    )
)


@lru_cache(maxsize=1)
def all_response_stat_keys() -> tuple[tuple[int, int], ...]:
    return tuple((int(ft), int(ff)) for ft in range(TOTAL_ROWS + 1) for ff in range(TOTAL_ROWS + 1))


@dataclass(frozen=True, slots=True)
class FgResponseFrontierCachePayload:
    frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult]
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool

    def stats_key(self, *, ft_stat: int, ff_stat: int) -> tuple[int, int]:
        return _normalize_stat_key((ft_stat, ff_stat))

    def frontier_for_stats(self, *, ft_stat: int, ff_stat: int) -> FgResponseFrontierResult:
        key = self.stats_key(ft_stat=ft_stat, ff_stat=ff_stat)
        frontier = self.frontier_by_key.get(key)
        if frontier is None:
            raise ValueError(f"FG response frontier stat key was not loaded: {key}")
        return frontier

    @property
    def frontiers(self) -> tuple[FgResponseFrontierResult, ...]:
        out: list[FgResponseFrontierResult] = []
        seen: set[int] = set()
        for frontier in self.frontier_by_key.values():
            marker = id(frontier)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(frontier)
        return tuple(out)


@dataclass(frozen=True, slots=True)
class FgResponseFrontierCacheInfo:
    cache_key: tuple
    disk_path: Path
    cache_source: str
    total_notes: int
    long_notes: int
    frontier_count: int = 0


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPrewarmResult:
    payload: FgResponseFrontierCachePayload
    cache_key: tuple
    disk_path: Path
    cache_source: str
    elapsed_ms: float
    total_notes: int
    long_notes: int
    frontier_count: int


@dataclass(frozen=True, slots=True)
class FgResponseFrontierScoringBundle:
    cache_key: tuple
    frontier_idx_by_key: dict[tuple[int, int], int]
    frontier_idx_by_stat: np.ndarray
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    frontier_meta: np.ndarray
    surface_words: np.ndarray
    surface_counts: np.ndarray
    surface_head_coeffs: np.ndarray
    frontier_offsets: np.ndarray
    frontier_lengths: np.ndarray
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool


def _normalize_stat_key(stat_key: tuple[int, int] | list[int]) -> tuple[int, int]:
    if len(stat_key) != 2:
        raise ValueError("FG response frontier stat keys must be (ft_stat, ff_stat)")
    ft_stat = max(0, min(TOTAL_ROWS, int(stat_key[0])))
    ff_stat = max(0, min(TOTAL_ROWS, int(stat_key[1])))
    return int(ft_stat), int(ff_stat)


def normalize_fg_response_stat_keys(stat_keys: Iterable[tuple[int, int]] | None) -> tuple[tuple[int, int], ...]:
    keys = tuple(sorted({_normalize_stat_key(key) for key in (stat_keys or ())}))
    if not keys:
        raise ValueError("FG response frontier cache requires at least one FT/FF stat key")
    return keys
