from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.gamedata import load_stat_curves
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface
from gear_optimizer.solver.timing_envelope import time_song


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("secondary, expected, colors", [("Chill", 1774, ["ColorBlue"]), ("Flow", 1773, ["ColorBlue", "ColorPurple"])])
def test_great_rounding_uses_chart_colors(secondary, expected, colors) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _color_flags, _fg_response_surface_score_native_f64
    from tools.verify.loadout_oracle_replay import _statsdict_for_oracle

    assert _fg_response_surface_score_native_f64(
        np.zeros((1, 8), dtype=np.uint32), 0, 0, 1, 0, 0, 1, 812, 812, 0.0, 1.0, 1.0,
        _color_flags("Chill", secondary, "Chill")[8],
    ) == expected
    assert _statsdict_for_oracle({"Chill": 812, "Flow": 812}, "Chill", secondary)[1] == colors


def test_reflections_force_greats_matches_observed_game_score() -> None:
    song = time_song(load_chart(ROOT / "Data" / "Normal" / "Reflections by Rutra.txt"))
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    stats = {
        "Perfect Points": 85,
        "Combo Multiplier": 60,
        "Fever Multiplier": 70,
        "Fever Time": 39,
        "Fever Fill Rate": 54,
        "Beat": 50,
        "Vibe": 54,
        "Rush": 34,
        "Flow": 6,
        "Chill": 767,
    }
    surface = FgResponseSurface(0, 0, 4292870144, 15, 0, 0, 0, 0, 587, 3, 3)

    assert score_force_greats_response_surface_exact(stats, song, curves, surface) == 22640729
