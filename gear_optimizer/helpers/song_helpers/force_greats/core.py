"""
Song Helpers - Force Greats - Force greats processing and optimization.

Public entrypoint:
- `process_force_greats(...)`
"""

from __future__ import annotations

import logging

from .bellman_fixed_adapter import process_force_greats_bellman_fixed_gpu

logger = logging.getLogger(__name__)


def process_force_greats(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    ga_candidates=None,
    ga_registry=None,
):
    total_entries = int(len(loadout_entries or {})) + int(len(ga_candidates or []))
    logger.debug("[ForceGreats] Processing %s candidate loadouts (DB + GA)...", total_entries)
    return process_force_greats_bellman_fixed_gpu(
        loadout_entries,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_candidates=ga_candidates,
        ga_registry=ga_registry,
    )
