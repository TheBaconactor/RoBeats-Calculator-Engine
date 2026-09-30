"""Synthetic stat curves for tests."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from gear_optimizer.gamedata import StatCurves, load_stat_curves

_STATS_TXT = Path(__file__).resolve().parents[1] / "Data" / "Gear" / "Stats.txt"


def synthetic_curves(values: Mapping[str, object]) -> StatCurves:
    """The repo's Stats.txt curves with the given curves replaced (a test sets only the curves it studies)."""
    full = dict(load_stat_curves(_STATS_TXT).f64)
    full.update(values)
    return StatCurves.from_mapping(full)
