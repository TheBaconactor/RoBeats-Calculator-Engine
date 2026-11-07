"""Synthetic stat curves for tests."""

from __future__ import annotations

from collections.abc import Mapping

from gear_optimizer.gamedata import StatCurves, stat_curves


def synthetic_curves(values: Mapping[str, object]) -> StatCurves:
    """The game's curves with the given curves replaced (a test sets only the curves it studies)."""
    full = dict(stat_curves().f64)
    full.update(values)
    return StatCurves.from_mapping(full)


def no_ftff_gems(_budget):
    """ftff_combo_arrays with nothing to split, for already allocated stats. Patch this, not gem_search.GEM_BUDGET: numba
    freezes that constant into the kernels it saves to its disk cache."""
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays

    return ftff_combo_arrays(0)
