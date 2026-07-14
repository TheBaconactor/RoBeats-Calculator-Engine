from pathlib import Path

import numpy as np

from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.scoring.fg_policy import build_penalty_table_and_body, compute_great_penalty_base
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface


ROOT = Path(__file__).resolve().parents[1]


def test_same_color_force_greats_formula_preserves_component_floor_order() -> None:
    assert compute_great_penalty_base(812, 812) == 1773

    penalty_table, body_penalty, combo_value = build_penalty_table_and_body(
        base_value=2436.0,
        combo_mul=1.0,
        primary_val=812,
        secondary_val=812,
        head_limit=4,
    )

    assert combo_value == 2436
    assert body_penalty == 663
    assert penalty_table == [663, 663, 663, 663]


def test_destiny_normal_t1_chill_force_greats_preserves_component_floors() -> None:
    calc_song = get_base_calc_song(
        str(ROOT / "Data" / "Normal" / "Destiny by Jim Yosef, Electro-Light, Anna Yvette, Deaf Kev & Tobu.txt"),
        {},
    )
    ref_arrays = build_ref_arrays_from_stats(read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")), dtype=np.float64)
    stats = {
        "Perfect Points": 29,
        "Combo Multiplier": 51,
        "Fever Multiplier": 69,
        "Fever Fill Rate": 51,
        "Fever Time": 33,
        "Chill": 812,
        "Flow": 6,
        "Rush": 28,
        "Beat": 38,
        "Vibe": 39,
    }

    replay = evaluate_force_greats_exact(stats, calc_song, ref_arrays, [4, 0])

    assert replay is not None
    assert replay["base_score"] == 24548685
    assert replay["score_penalty"] == 4082
    assert replay["final_score"] == 24544603


def test_dark_sheep_force_greats_matches_observed_game_score() -> None:
    calc_song = get_base_calc_song(
        str(ROOT / "Data" / "Hard" / "Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt"),
        {},
    )
    ref_arrays = build_ref_arrays_from_stats(
        read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")),
        dtype=np.float64,
    )
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

    assert score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, surface) == 129185709
