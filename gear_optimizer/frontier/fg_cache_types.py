from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from gear_optimizer.rules import MAX_STAT
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint

from .types import FgResponseFrontierResult, SurfacePool

# The FG response-frontier cache version: a hand-kept base version plus a fingerprint (an AST digest, see
# logic_fingerprint.py) of every module that co-determines the cached bundles (_FG_DP_SOURCES), so a logic change there
# rotates it by itself. Bump the base version when bundle output changes in a way the fingerprint cannot see (e.g. a
# dependency's behavior); any change of the bundle key's inputs needs a new version, because the version is the only
# key-derivation input the prebuild manifest sees. A new version reads an older version's files only when
# fg_cache_store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS lists it, after a byte gate proved them identical. The
# version history is in git.
_FG_RESPONSE_CACHE_BASE_VERSION = "fg-response-frontier-visible-first-v32"
_HERE = Path(__file__).resolve().parent
_ENGINE = _HERE.parent
_SCORING_POLICY_SOURCE = _ENGINE / "solver" / "scoring" / "fg_policy.py"
# Shared exact frontier producer used by both Base (Perfect-only actions) and FG. Base cache
# identity imports this tuple directly so a producer edit can never leave one product surface on
# stale bytes while the other rotates correctly.
_FG_SHARED_FRONTIER_PRODUCER_SOURCES = (
    _ENGINE / "rules.py",
    _ENGINE / "core" / "time_quantize.py",
    _ENGINE / "solver" / "timing_envelope.py",
    _SCORING_POLICY_SOURCE,
    _HERE / "fill_crossing.py",
    _HERE / "types.py",
    _HERE / "producer_batch.py",
    _HERE / "producer_scheduler.py",
    _HERE / "producer_precompute.py",
    _HERE / "producer_reducer.py",
    _HERE / "producer_kernels.py",
    _HERE / "producer_surfaces.py",
)
# Modules whose logic co-determines the cached frontier bundle output. If a NEW module joins the FG
# build/search/pack path, add it here (the base version stays the human backstop).
_FG_DP_SOURCES = (
    *_FG_SHARED_FRONTIER_PRODUCER_SOURCES,
    _HERE / "fg_cache_keys.py",
    _HERE / "fg_cache_patterns.py",
    _HERE / "fg_cache_serde.py",
)
_FG_RESPONSE_CACHE_VERSION = (
    f"{_FG_RESPONSE_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_FG_DP_SOURCES)}"
)
_BUNDLE_KEY_MARKER = "all-stat-keys"
# The members of a bundle file (fg_cache_store).
_BUNDLE_ARRAY_NAMES = frozenset(
    (
        "version",
        "stat_keys",
        "frontier_ids",
        "raw_fill_by_ff",
        "non_fever_base_by_ff",
        "real_time_by_ft",
        "total_notes",
        "long_notes",
        "use_forced_great_timing",
        "first_surface_head_len",
        "frontier_meta",
        "first_offsets",
        "first_counts",
        "surface_rows",
        "surface_patterns",
    )
)


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
