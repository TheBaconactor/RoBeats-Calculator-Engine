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
