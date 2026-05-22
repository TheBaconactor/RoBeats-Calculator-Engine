"""
Song Helpers - Force Greats - Force greats processing and optimization.

Public entrypoint:
- `process_force_greats(...)`
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from . import cache_validation
from .bellman_fixed_adapter import process_force_greats_bellman_fixed_gpu
from .entry_resolution import entry_base_score
from .entry_utils import eval_data_from_entry, expected_selected_element
from ..ga_entry_utils import materialize_entry_names
from ..loadout_builder import refresh_ga_candidate_entries
from ....core.utils import stats_signature
from ....solver.scoring import apply_force_greats_to_result

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


logger = logging.getLogger(__name__)


def _process_force_greats_cpu(
    *,
    loadout_entries,
    manual_counts,
    use_finder: bool,
    calc_song,
    ref_arrays,
    meta_primary_color,
    use_gpu: bool,
    gpu_client: Optional["GpuServiceClient"],
):
    fg_variants = []
    unique_stats_seen = set()
    computed = 0

    for entry in loadout_entries.values():
        cached_force = entry.get("force")
        expected_sel = expected_selected_element(entry, meta_primary_color)

        if (
            cached_force
            and (entry.get("fg_score") or cached_force.get("Score"))
            and cache_validation.is_cached_force_valid(cached_force, expected_sel)
        ):
            base_score = entry_base_score(entry)
            cached_fg_score = entry.get("fg_score", 0) or cached_force.get("Score", 0)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_variants.append(
                {
                    "data": cached_force,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": base_score,
                    "fg_score": cached_fg_score,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            continue

        eval_data = eval_data_from_entry(entry, meta_primary_color)
        if not eval_data:
            continue

        stats = eval_data.get("Stats", {})
        sel_color = eval_data.get("Selected Element", meta_primary_color)
        sig = stats_signature(stats, calc_song, sel_color)
        unique_stats_seen.add(sig)

        fg_variant = apply_force_greats_to_result(
            eval_data,
            calc_song,
            ref_arrays,
            manual_counts=manual_counts,
            use_finder=bool(use_finder),
            use_gpu=bool(use_gpu) and (gpu_client is None),
        )
        computed += 1
        if fg_variant:
            base_score = entry_base_score(entry)
            fg_score = fg_variant.get("Score", 0)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_variants.append(
                {
                    "data": fg_variant,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": base_score,
                    "fg_score": fg_score,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            entry["force"] = fg_variant
            entry["fg_score"] = fg_score

    logger.debug(
        "[ForceGreats] %s unique stat signatures, %s FG variants generated (computed %s)",
        len(unique_stats_seen),
        len(fg_variants),
        computed,
    )
    return fg_variants


def process_force_greats(
    loadout_entries,
    manual_force_greats,
    force_greats_config,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    use_gpu: bool = True,
    fg_search_radius: int | None = None,
    perf_timing: bool = False,
    gpu_client: Optional["GpuServiceClient"] = None,
    ga_candidates=None,
    ga_registry=None,
):
    def _ensure_ga_entries_for_cpu(loadout_entries_map):
        if not ga_candidates:
            return loadout_entries_map
        loadout_entries_map = loadout_entries_map if isinstance(loadout_entries_map, dict) else {}
        refresh_ga_candidate_entries(
            loadout_entries_map,
            list(ga_candidates or []),
            build_details_fn,
            materialize_details=False,
            ga_registry=ga_registry,
        )
        return loadout_entries_map

    manual_counts = force_greats_config if manual_force_greats else []
    try:
        total_entries = int(len(loadout_entries or {})) + int(len(ga_candidates or []))
    except Exception as e:
        logger.debug(f"core:_ensure_ga_entries_for_cpu: {e}")
        total_entries = len(loadout_entries or {})
    logger.debug("[ForceGreats] Processing %s candidate loadouts (DB + GA)...", total_entries)

    if use_gpu and not manual_force_greats:
        return process_force_greats_bellman_fixed_gpu(
            loadout_entries,
            calc_song,
            ref_arrays,
            meta_primary_color,
            ga_candidates=ga_candidates,
            ga_registry=ga_registry,
        )

    loadout_entries = _ensure_ga_entries_for_cpu(loadout_entries)
    return _process_force_greats_cpu(
        loadout_entries=loadout_entries,
        manual_counts=manual_counts,
        use_finder=not bool(manual_force_greats),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        meta_primary_color=meta_primary_color,
        use_gpu=use_gpu,
        gpu_client=gpu_client,
    )
