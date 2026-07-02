from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS

from .response_types import FgResponseFrontierResult

# Bump whenever the FG response-frontier bundle OUTPUT changes via code (not the chart file).
# The per-song disk digest captures perfect_floor / candidate timestamps, but the prebuild's
# coarse manifest (frontier_cache_manifest._manifest_key) keys ONLY on cache_version + chart
# path/mtime/size + ref/stat sigs -- it never parses the chart. So an FG-output code change with
# an unchanged chart file and an unbumped version makes the prebuild false-hit stale bundles
# (built=0) while runtime computes the new perfect_floor-keyed digest and fail-louds on a missing
# scoring bundle. This is the FG analog of timeline._FRONTIER_DISK_CACHE_VERSION.
# v12 -> v13: issue #42 endpoint-early fever -> perfect_floor envelope (build_perfect_floor_envelope_sec)
#             changed the bundle output; the v12 bundles predate it.
# v13 -> v14: issue #44 greats-side endpoint-early fever -> early-Great floor (build_great_floor_envelope_sec)
#             adds early-Great extended surfaces to the bundle; the v13 bundles predate them.
# v14 -> v15: issue #44 Route A head upper-envelope prune (_numba_head_envelope_filter) shrinks the
#             cached frontier to the parametric envelope (same best_fg_score, far fewer surfaces); the
#             v14 bundles carry the un-pruned early-Great cascade, so rebuild to gain the perf win.
# v15 -> v16: issue #44 early-Great FLOOR corrected -75 -> cumulative -95 (held -190) to match the
#             game's get_note_times/timedelta_to_result (great_lower = perfect_lower + great_extra).
#             Captures legal early-Great fever for notes 75-95ms past a cutoff; v15 under-included it.
# v16 -> v17: body-pair radix correctness. The build packs (normal_great, body_fever_great) as
#             normal_great*pair_mod + body_fever_great; pair_mod was sized to the SECTION COUNT, but
#             the issue-#44 early-Great band makes body_fever_great exceed that, so the pack aliased
#             onto a phantom (normal_great+1, ...) surface -- silently OVER-scoring some cells and
#             crashing trace reconstruction. pair_mod now sizes to the geometry's true max
#             body_fever_great (= section_bound*(1+early_Great_band)); best_fg_score drops to the
#             correct value on aliased cells, so v16 bundles are wrong and must rebuild. (Latent
#             since #44 at -75; -95's wider band made it reproduce.)
# v17 -> v18: PR #89 late-Great deliverability cap (build_per_note_great_window_ms clamps the late
#             edge at NOTE_REMOVE_LATE_CAP_MS = +200) changed great_candidates for most charts.
#             That changed the content-addressed bundle key for those songs, but WITHOUT a version
#             bump the manifest fast-path (identity: version + chart mtime/size + ref sig, none of
#             which moved) kept reporting the pre-#89 bundles as valid and skipped the rebuild --
#             every affected song then failed prep loudly ("scoring bundle is missing") while the
#             startup banner said the cache was ready. v17 bundles for affected songs schedule
#             non-deliverable +200..+380ms late-Great activations, so they are semantically stale
#             and must rebuild. Invariant: ANY change that alters fg_response_frontier_song_cache_key
#             inputs (extract_fg_song_inputs / timing envelopes) MUST bump this version -- the
#             version string is the only key-derivation fingerprint the manifest fast-path sees.
_FG_RESPONSE_CACHE_VERSION = "fg-response-frontier-visible-first-v18"
_MEMORY_CACHE_MAX = 4096
_PAYLOAD_CACHE_MAX = 8
# Sized to cover the native in-flight prep window (prep_limit tops out around 36): a
# bundle's slim metadata arrays are hydrated at prep and re-read at the fused GA turn
# 10-30 songs later; a 2-entry LRU thrashed and forced an owner-thread npz re-open per
# song. Entries are ~0.2-1MB (metadata members only, never the surface pools).
_BUNDLE_ARRAY_CACHE_MAX = 40
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
        "first_surface_head_len",
        "frontier_meta",
        "first_offsets",
        "first_counts",
        "first_surface_row_count",
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
    surface_row_count: int
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
