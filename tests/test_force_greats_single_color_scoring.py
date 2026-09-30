from pathlib import Path

import numpy as np

from gear_optimizer.chart import load_chart
from gear_optimizer.gamedata import load_stat_curves
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface
from gear_optimizer.solver.timing_envelope import time_song


ROOT = Path(__file__).resolve().parents[1]


def test_same_color_force_greats_formula_preserves_component_floor_order() -> None:
    from tests.parity.force_greats.fg_atom_champion import compute_great_penalty_base

    assert compute_great_penalty_base(812, 812) == 1773


def test_dark_sheep_force_greats_matches_observed_game_score() -> None:
    song = time_song(load_chart(ROOT / "Data" / "Hard" / "Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt"))
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    stats = {
        "Perfect Points": 85,
        "Combo Multiplier": 66,
        "Fever Multiplier": 68,
        "Fever Time": 74,
        "Fever Fill Rate": 65,
        "Beat": 769,
        "Vibe": 55,
        "Rush": 180,
        "Flow": 72,
        "Chill": 35,
    }
    surface = FgResponseSurface(0, 0, 0, 0, 131071, 0, 0, 0, 3420, 4, 3)

    assert score_force_greats_response_surface_exact(stats, song, curves, surface) == 129185709
