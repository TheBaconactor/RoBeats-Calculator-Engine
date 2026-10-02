from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.rules import MAX_STAT
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint

from .response_types import FgResponseFrontierResult

# The FG response-frontier cache version: a hand-kept base version plus a fingerprint (an AST digest, see
# logic_fingerprint.py) of every module that co-determines the cached bundles (_FG_DP_SOURCES), so a logic change there
# rotates it by itself. Bump the base version when bundle output changes in a way the fingerprint cannot see (e.g. a
# dependency's behavior); any change of the bundle key's inputs needs a new version, because the version is the only
# key-derivation input the prebuild manifest sees. A new version reads an older version's files only when
# response_cache_store._EXACT_COMPATIBLE_PREDECESSOR_VERSIONS lists it, after a byte gate proved them identical. The
# version history is in git.
_FG_RESPONSE_CACHE_BASE_VERSION = "fg-response-frontier-visible-first-v31"
_HERE = Path(__file__).resolve().parent
_SOLVER_DIR = _HERE.parents[1]
_CORE_DIR = _SOLVER_DIR.parent / "core"
_RULES = _SOLVER_DIR.parent / "rules.py"
# Canonical game-engine inputs to the cached transition producer. Keep this ownership explicit:
# cache compaction may reuse exact producer output, but it must never make timing, input-order,
# lane-reachability, fever, or witness semantics invisible to cache compatibility.
_FG_GAME_ENGINE_SOURCES = (
    _RULES,
    _CORE_DIR / "time_quantize.py",
    _SOLVER_DIR / "input_engine_breakpoints.py",
    _SOLVER_DIR / "timing_envelope.py",
    _SOLVER_DIR / "scoring" / "fg_policy.py",
    _SOLVER_DIR / "fg_response_scoring" / "note_graph.py",
)
# Shared exact frontier producer used by both Base (Perfect-only actions) and FG. Base cache
# identity imports this tuple directly so a producer edit can never leave one product surface on
# stale bytes while the other rotates correctly.
_FG_SHARED_FRONTIER_PRODUCER_SOURCES = (
    _RULES,
    _CORE_DIR / "time_quantize.py",
    _SOLVER_DIR / "input_engine_breakpoints.py",
    _SOLVER_DIR / "timing_envelope.py",
    _SOLVER_DIR / "scoring" / "fg_policy.py",
    _HERE / "fill_crossing.py",
    _HERE / "response_builder.py",
    _HERE / "response_types.py",
    _HERE / "response_build_gpu_batch.py",
    _HERE / "response_build_gpu_scheduler.py",
    _HERE / "response_build_gpu_precompute.py",
    _HERE / "response_build_gpu_reducer.py",
    _HERE / "response_build_gpu_numba.py",
    _HERE / "response_build_gpu_surfaces.py",
)
# Modules whose logic co-determines the cached frontier bundle output. If a NEW module joins the FG
# build/search/pack path, add it here (the base version stays the human backstop).
_FG_DP_SOURCES = (
    *_FG_SHARED_FRONTIER_PRODUCER_SOURCES,
    _SOLVER_DIR / "fg_response_scoring" / "note_graph.py",
    _HERE / "response_cache_keys.py",
    _HERE / "response_cache_patterns.py",
    _HERE / "response_cache_serde.py",
    _HERE / "response_inner_host.py",
)
_FG_RESPONSE_CACHE_VERSION = (
    f"{_FG_RESPONSE_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_FG_DP_SOURCES)}"
)
_BUNDLE_KEY_MARKER = "all-stat-keys"
_SURFACE_GENERATION_ARRAY_NAME = "surface_generation"
_SURFACE_BUNDLE_PATH_ARRAY_NAME = "_surface_bundle_path"
_SCORING_BUNDLE_ARRAY_NAMES = frozenset(
    (
        _SURFACE_GENERATION_ARRAY_NAME,
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
        "first_surface_row_count",
        "first_surface_pattern_count",
    )
)


@lru_cache(maxsize=1)
def all_response_stat_keys() -> tuple[tuple[int, int], ...]:
    return tuple((int(ft), int(ff)) for ft in range(MAX_STAT + 1) for ff in range(MAX_STAT + 1))


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


class _FrontierIdxByStatView:
    """Read-only ``(ft, ff) -> frontier index`` lookup over a ``frontier_idx_by_stat`` grid
    (``-1`` = stat key not loaded)."""

    __slots__ = ("_grid",)

    def __init__(self, grid: np.ndarray) -> None:
        self._grid = grid

    def get(self, key: tuple[int, int], default: int | None = None) -> int | None:
        ft_stat, ff_stat = int(key[0]), int(key[1])
        if not (0 <= ft_stat < int(self._grid.shape[0]) and 0 <= ff_stat < int(self._grid.shape[1])):
            return default
        frontier_idx = int(self._grid[ft_stat, ff_stat])
        return frontier_idx if frontier_idx >= 0 else default


@dataclass(frozen=True, slots=True)
class FgResponseFrontierScoringBundle:
    cache_key: tuple
    frontier_idx_by_stat: np.ndarray
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    frontier_meta: np.ndarray
    surface_pattern_ids: np.ndarray
    surface_pattern_words: np.ndarray
    surface_counts: np.ndarray
    surface_pattern_head_coeffs: np.ndarray
    frontier_offsets: np.ndarray
    frontier_lengths: np.ndarray
    surface_row_count: int
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool
    surface_generation: str | None = None
    bundle_path: Path | None = None

    @property
    def frontier_idx_by_key(self) -> _FrontierIdxByStatView:
        # The grid is the bundle's only key map (a per-key dict duplicated it at ~135 B/key). This
        # view keeps the fingerprinted serde reader's ``frontier_idx_by_key.get`` unchanged.
        return _FrontierIdxByStatView(self.frontier_idx_by_stat)


def _normalize_stat_key(stat_key: tuple[int, int] | list[int]) -> tuple[int, int]:
    if len(stat_key) != 2:
        raise ValueError("FG response frontier stat keys must be (ft_stat, ff_stat)")
    ft_stat = max(0, min(MAX_STAT, int(stat_key[0])))
    ff_stat = max(0, min(MAX_STAT, int(stat_key[1])))
    return int(ft_stat), int(ff_stat)


def normalize_fg_response_stat_keys(stat_keys: Iterable[tuple[int, int]] | None) -> tuple[tuple[int, int], ...]:
    keys = tuple(sorted({_normalize_stat_key(key) for key in (stat_keys or ())}))
    if not keys:
        raise ValueError("FG response frontier cache requires at least one FT/FF stat key")
    return keys
