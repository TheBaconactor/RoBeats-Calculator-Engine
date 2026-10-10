from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.gamedata import CURVE_STATS, StatCurves, stat_curves
from gear_optimizer.rules import MAX_STAT
from tools.verify import game_sim

# GearStats.lua: each curve passes through its knots at stat 0, 40 and 80 and reaches a80 + (a80 - a40) x 0.35 at 160.
_KNOTS = {
    "Perfect Points": (200, 350, 450, 485),
    "Combo Multiplier": (2.0, 2.4, 2.6, 2.67),
    "Fever Multiplier": (3.0, 4.75, 5.25, 5.425),
    "Fever Fill Rate": (0.333, 0.166, 0.1, 0.0769),
    "Fever Time": (0.15, 0.35, 0.4, 0.4175),
}
# The reference ScoreEngine port of the same curves (tools/verify/game_sim), stat by stat.
_REFERENCE = {
    "Perfect Points": lambda v: game_sim._perfect_points(game_sim._statsdict_from({"PerfectPoints": v})),
    "Combo Multiplier": lambda v: game_sim._combo_multipliers(game_sim._statsdict_from({"ComboMultiplier": v}))[2],
    "Fever Multiplier": lambda v: game_sim._fever_multiplier(game_sim._statsdict_from({"FeverMultiplier": v})),
    "Fever Fill Rate": lambda v: game_sim._fever_fill_scales(game_sim._statsdict_from({"FeverFillRate": v}))["perfect"],
    "Fever Time": lambda v: game_sim._fever_decay_rate(game_sim._statsdict_from({"FeverTime": v})),
}


def test_stat_curves_pass_through_the_games_knots() -> None:
    curves = stat_curves()
    for stat, (at0, at40, at80, at160) in _KNOTS.items():
        values = curves.f64[stat][[0, 40, 80, MAX_STAT]]
        assert values == pytest.approx([at0, at40, at80, at160], rel=1e-12), stat
        assert np.all(np.diff(curves.f64[stat]) * np.sign(at80 - at0) >= 0), f"{stat} is monotone"


def test_stat_curves_match_the_reference_port_at_every_stat_value() -> None:
    # The port measures BezierDist chords with math.hypot, the game with sqrt(x*x + y*y): equal to the last ulp or two.
    curves = stat_curves()
    for stat, reference in _REFERENCE.items():
        expected = np.array([reference(v) for v in range(MAX_STAT + 1)], dtype=np.float64)
        assert curves.f64[stat] == pytest.approx(expected, rel=1e-15, abs=0), stat


def test_float32_view_is_the_float64_values_rounded() -> None:
    curves = StatCurves.from_mapping({stat: np.linspace(0.1, 3.7, MAX_STAT + 1) for stat in CURVE_STATS})
    for stat in CURVE_STATS:
        assert curves.f64[stat].dtype == np.float64
        assert curves.f32[stat].dtype == np.float32
        assert curves.f32[stat].tobytes() == curves.f64[stat].astype(np.float32).tobytes()
    assert curves.factor("Combo Multiplier", 999) == float(curves.f64["Combo Multiplier"][MAX_STAT])
    assert curves.factor("Combo Multiplier", -3) == float(curves.f64["Combo Multiplier"][0])


def test_from_mapping_requires_every_curve_at_full_length() -> None:
    values = {stat: np.ones(MAX_STAT + 1) for stat in CURVE_STATS}
    del values["Fever Time"]
    with pytest.raises(KeyError):
        StatCurves.from_mapping(values)
    values["Fever Time"] = np.ones(MAX_STAT)
    with pytest.raises(ValueError, match="Fever Time curve needs 161 values"):
        StatCurves.from_mapping(values)
