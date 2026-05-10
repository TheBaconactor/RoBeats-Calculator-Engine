import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu]


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_global_gear_skyline_gpu_matches_cpu_reference():
    from gear_optimizer.solver.exact_skyline import (
        _global_gear_skyline_points_6d_lane_base_with_codes,
        _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference,
    )

    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]] = {
        (0, 0, 0, 0): [(0, 10, 101), (2, 15, 102)],
        (0, 1, 0, 0): [(0, 12, 103)],
        (0, 1, 1, 0): [(1, 13, 104)],
        (1, 0, 0, 0): [(0, 11, 201), (1, 25, 202)],
        (1, 1, 1, 1): [(0, 20, 203)],
        (2, 0, 0, 0): [(0, 8, 301)],
        (2, 2, 1, 0): [(1, 18, 302)],
    }

    cpu_stats, cpu_points, cpu_codes = _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference(states)
    gpu_stats, gpu_points, gpu_codes = _global_gear_skyline_points_6d_lane_base_with_codes(states)

    assert gpu_stats.points_in == cpu_stats.points_in
    assert gpu_stats.points_out == cpu_stats.points_out
    np.testing.assert_array_equal(gpu_points, cpu_points)
    np.testing.assert_array_equal(gpu_codes, cpu_codes)
