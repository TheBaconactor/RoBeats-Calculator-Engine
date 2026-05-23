import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _ref_arrays():
    size = 1001
    return {
        "Perfect Points": np.linspace(0.0, 2.0, size, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
    }


def test_response_frontier_gpu_inner_matches_reference_inner_with_overlap():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseSurface,
        optimize_response_frontier_inner_exact,
        optimize_response_frontier_inner_exact_gpu,
    )

    surfaces = (
        FgResponseSurface(0b111, 0, 0, 0, 0b001, 0, 0, 0, 2, 1),
        FgResponseSurface(0b011, 0, 0, 0, 0b000, 0, 0, 0, 1, 0),
    )
    kwargs = {
        "total_notes": 105,
        "residual_budget": 3,
        "stats_after_ftff": {
            "Perfect Points": 10,
            "Combo Multiplier": 20,
            "Fever Multiplier": 30,
            "Power": 40,
            "Rush": 50,
        },
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }

    reference = optimize_response_frontier_inner_exact(surfaces, **kwargs)
    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert gpu == reference


def test_response_frontier_gpu_batch_pack_matches_reference_groups():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseSurface,
        optimize_response_frontier_inner_exact,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner import _optimize_response_surfaces_gpu

    surfaces_a = (
        FgResponseSurface(0b1111, 0, 0, 0, 0b0010, 0, 0, 0, 4, 1),
        FgResponseSurface(0b0111, 0, 0, 0, 0b0000, 0, 0, 0, 2, 0),
        FgResponseSurface(0b1110, 0, 0, 0, 0b0100, 0, 0, 0, 5, 2),
    )
    surfaces_b = (
        FgResponseSurface(0b101, 0, 0, 0, 0b001, 0, 0, 0, 1, 1),
        FgResponseSurface(0b111, 0, 0, 0, 0b011, 0, 0, 0, 3, 2),
    )
    shared = {
        "total_notes": 108,
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }
    stats_a = {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Power": 40,
        "Rush": 50,
    }
    stats_b = {
        "Perfect Points": 30,
        "Combo Multiplier": 15,
        "Fever Multiplier": 25,
        "Power": 20,
        "Rush": 80,
    }

    rows, surface_rows = _optimize_response_surfaces_gpu(
        [(5, stats_a, surfaces_a), (4, stats_b, surfaces_b)],
        **shared,
    )

    ref_a = optimize_response_frontier_inner_exact(
        surfaces_a,
        residual_budget=5,
        stats_after_ftff=stats_a,
        **shared,
    )
    ref_b = optimize_response_frontier_inner_exact(
        surfaces_b,
        residual_budget=4,
        stats_after_ftff=stats_b,
        **shared,
    )

    assert surface_rows == len(surfaces_a) + len(surfaces_b)
    assert rows == [
        (
            ref_a.best_score,
            ref_a.surface_index,
            ref_a.g_pp,
            ref_a.g_cm,
            ref_a.g_fm,
            ref_a.g_ov,
            ref_a.final_pp,
            ref_a.final_cm,
            ref_a.final_fm,
            ref_a.final_primary,
            ref_a.final_secondary,
        ),
        (
            ref_b.best_score,
            ref_b.surface_index,
            ref_b.g_pp,
            ref_b.g_cm,
            ref_b.g_fm,
            ref_b.g_ov,
            ref_b.final_pp,
            ref_b.final_cm,
            ref_b.final_fm,
            ref_b.final_primary,
            ref_b.final_secondary,
        ),
    ]
