from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint

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
#             v18->v19: canonical late-Great gate (late_great_prefix_is_legal) added to the search
#             (_compact_first_frontier_action_arrays) + reconstruct mirror -- illegal (phantom)
#             late-Great activations whose fill-crossing is an earlier Perfect are no longer emitted,
#             so produced surfaces change for any song where the old model scheduled one. Rebuild.
# v19 -> v20: the manual string above is now the BACKSTOP + history; a DP-LOGIC FINGERPRINT of the FG
#             builder modules is appended as `+logic-<fp>` (Fix 1, 2026-07-04). The manifest fast-path
#             admits that "the version string is the only key-derivation fingerprint [it] sees" -- so
#             any change to the FG search/build/pack/kernel logic below now moves the version
#             automatically, and the manifest can no longer false-hit bundles built by superseded
#             logic (the failure mode that stranded songs at built=0 while runtime fail-louded). The
#             fingerprint is ast-level: comment/docstring/whitespace edits do NOT rebuild (see
#             logic_fingerprint.py); only real logic/literal changes do. Over-invalidation is safe.
# v20 -> v21: hit-time chord-reachability -- the frontier now forbids UNREACHABLE late-Great
#             activations (an earlier-hit same-timestamp sibling or on-time note-ahead completes the
#             fever bar first), so stale bundles carry phantom late-Great over-reports and MUST
#             rebuild. The DP fingerprint over fill_crossing.py + response_build_gpu_precompute.py
#             already moves the version automatically; this backstop bump records the behaviour change.
# v21 -> v22: the PERFECT activation clock is now capped to the reachable value too (a held-tail +80
#             perfect activation whose narrower later-indexed sibling is hit first over-extended the
#             drain window). perfect_end_idx is built from the capped clock, so stale bundles carry the
#             phantom perfect-activation window and MUST rebuild.
# v22->v23: BUG-1 judgment-edge inclusivity fix (timing_envelope.py perfect/great FLOOR early edges
# shifted +1ms to the engine's exclusive-early boundary: -20/-40 -> -19/-39, -95/-190 -> -94/-189).
# The floor envelopes are frontier-build INPUTS but timing_envelope.py is NOT in _FG_DP_SOURCES, so
# the logic fingerprint does not cover it -- this explicit base-version bump is what invalidates the
# stale (over-generous) fever-membership floors. Re-solve to re-persist best_fg_score.
# v23->v24: input-engine-aware reachability. The frontier now carries lanes in the cache key, keeps
# raw timing edges in precompute, and filters reconstructed surfaces through the weighted lane-aware
# owner. Stale v23 bundles can either keep phantoms the input engine cannot play or miss legal
# region-delay surfaces the lane-blind clamp removed.
# v24->v25: region-delay producer. The numba first-frontier graph now emits late-Great activations
# from non-prefix contiguous Great runs, and traces persist forced_run_start/count so the note graph
# and audits render the same run the surface scored. v24 bundles are prefix-only after filtering.
# v25->v26: input-engine-aware same-time sibling bundles. A region-delay late-Great activation may
# require following same-time/early-hit siblings to also be forced Great so their Perfect hits do not
# fill the bar first; stale v25 bundles miss legal higher-scoring surfaces such as ART Hard 835/3/3.
# v26->v27: shared input-order breakpoint owner. Delayed activation hits are capped by following
# notes' scored label upper edges, and capped hits own the fever end / early-Great extension. Stale
# v26 bundles can miss legal capped-breakpoint surfaces or price them from the wrong activation edge.
# v27->v28: shifted-head region representative. The numba first-frontier producer now emits the
# earliest shifted-head run representative (plus the normal crossing offset) and both Perfect /
# late-Great crossing branches. Stale v27 bundles can miss score-equivalent timing witnesses and
# shifted-head breakpoint surfaces.
_FG_RESPONSE_CACHE_BASE_VERSION = "fg-response-frontier-visible-first-v28"
_HERE = Path(__file__).resolve().parent
_SOLVER_DIR = _HERE.parents[1]
# Modules whose logic co-determines the cached frontier bundle output. If a NEW module joins the FG
# build/search/pack path, add it here (the base version stays the human backstop).
_FG_DP_SOURCES = (
    _SOLVER_DIR / "input_engine_breakpoints.py",
    _HERE / "fill_crossing.py",
    _HERE / "response_builder.py",
    _HERE / "response_types.py",
    _HERE / "response_build_gpu_batch.py",
    _HERE / "response_build_gpu_precompute.py",
    _HERE / "response_build_gpu_reducer.py",
    _HERE / "response_build_gpu_numba.py",
    _HERE / "response_build_gpu_surfaces.py",
)
_FG_RESPONSE_CACHE_VERSION = (
    f"{_FG_RESPONSE_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_FG_DP_SOURCES)}"
)
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
