from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from gear_optimizer.rules import MAX_STAT

from .cache import FRONTIER_PRODUCER_SOURCES, cache_version
from .types import FgResponseFrontierResult, SurfacePool

# The FG response-frontier cache version: a hand-kept base version plus a fingerprint of every module that co-determines
# the cached bundles (_FG_DP_SOURCES), so a logic change there rotates it by itself. Bump the base version when bundle
# output changes in a way the fingerprint cannot see (e.g. a dependency's behavior); any change of the bundle key's
# inputs needs a new version, because the version is the only key-derivation input the prebuild manifest sees. A new
# version reads an older version's files only when fg_cache_store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS lists it, after
# a byte gate proved them identical. The version history is in git.
_FG_RESPONSE_CACHE_BASE_VERSION = "fg-response-frontier-visible-first-v32"
_HERE = Path(__file__).resolve().parent
# Modules whose logic co-determines the cached frontier bundle output. If a NEW module joins the FG
# build/search/pack path, add it here (the base version stays the human backstop).
_FG_DP_SOURCES = (
    *FRONTIER_PRODUCER_SOURCES,
    _HERE.parent / "solver" / "scoring" / "fg_policy.py",
    _HERE / "fg_cache_keys.py",
    _HERE / "fg_cache_patterns.py",
    _HERE / "fg_cache_serde.py",
)
_FG_RESPONSE_CACHE_VERSION = cache_version(_FG_RESPONSE_CACHE_BASE_VERSION, _FG_DP_SOURCES)
_BUNDLE_KEY_MARKER = "all-stat-keys"


@lru_cache(maxsize=1)
def all_response_stat_keys() -> np.ndarray:
    """Every (FT, FF) stat key, sorted, as an (n, 2) int32 array."""
    axis = np.arange(MAX_STAT + 1, dtype=np.int32)
    return np.stack((np.repeat(axis, axis.size), np.tile(axis, axis.size)), axis=1)


@dataclass(frozen=True, slots=True)
class FgResponseFrontierCachePayload:
    frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult]
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool

    @property
    def frontiers(self) -> tuple[FgResponseFrontierResult, ...]:
        """The distinct frontier objects, in the order their first stat key holds them."""
        return tuple({id(frontier): frontier for frontier in self.frontier_by_key.values()}.values())


@dataclass(frozen=True, slots=True)
class FgResponseFrontierScoringBundle:
    """A bundle file as the gem search reads it: `frontier_idx_by_stat` is -1 at a stat key the file does not hold, and
    `pool` holds its surfaces."""

    cache_key: tuple
    frontier_idx_by_stat: np.ndarray
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    pool: SurfacePool
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool
