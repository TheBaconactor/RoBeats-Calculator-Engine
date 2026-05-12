"""Compatibility wrapper for the pure FT/FF combo enumeration helpers."""

from __future__ import annotations

from gear_optimizer.solver.ftff_combos import (
    collect_ftff_pairs_from_centers,
    ftff_combo_arrays,
    ftff_combo_pairs_array,
    ftff_combo_pairs_list,
)

__all__ = [
    "collect_ftff_pairs_from_centers",
    "ftff_combo_arrays",
    "ftff_combo_pairs_array",
    "ftff_combo_pairs_list",
]
