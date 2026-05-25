"""
Keep the package import light; GPU dispatch is loaded only when the public
entrypoint is actually called.
"""

from __future__ import annotations

import logging

__all__ = ["process_force_greats"]


def process_force_greats(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    ga_candidates=None,
    ga_registry=None,
):
    from .response_frontier_adapter import process_force_greats_response_frontier_gpu

    total_entries = int(len(loadout_entries or {})) + int(len(ga_candidates or []))
    logger = logging.getLogger(__name__)
    logger.debug("[ForceGreats] Processing %s candidate loadouts (DB + GA)...", total_entries)
    return process_force_greats_response_frontier_gpu(
        loadout_entries,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_candidates=ga_candidates,
        ga_registry=ga_registry,
    )
