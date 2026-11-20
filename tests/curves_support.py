"""Synthetic stat curves for tests."""

from __future__ import annotations

from collections.abc import Mapping

from gear_optimizer.gamedata import StatCurves, stat_curves


def synthetic_curves(values: Mapping[str, object]) -> StatCurves:
    """The game's curves with the given curves replaced (a test sets only the curves it studies)."""
    full = dict(stat_curves().f64)
    full.update(values)
    return StatCurves.from_mapping(full)
