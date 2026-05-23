import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu]


def _points_and_codes_from_states(
    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]],
) -> tuple[np.ndarray, np.ndarray]:
    points: list[tuple[int, int, int, int, int, int]] = []
    codes: list[int] = []
    for (pp, cm, fm, ft), frontier in states.items():
        for ff, base, code in frontier:
            points.append((int(pp), int(cm), int(fm), int(ft), int(ff), int(base)))
            codes.append(int(code))
    return np.asarray(points, dtype=np.int32), np.asarray(codes, dtype=np.uint64)


def _point_code_rows(points: np.ndarray, codes: np.ndarray) -> list[tuple[int, ...]]:
    return sorted(
        tuple(int(x) for x in row.tolist()) + (int(code),)
        for row, code in zip(points, codes, strict=True)
    )


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
    gear_points, gear_codes = _points_and_codes_from_states(states)
    gpu_stats, gpu_points, gpu_codes = _global_gear_skyline_points_6d_lane_base_with_codes(gear_points, gear_codes)

    assert gpu_stats.points_in == cpu_stats.points_in
    assert gpu_stats.points_out == cpu_stats.points_out
    assert _point_code_rows(gpu_points, gpu_codes) == _point_code_rows(cpu_points, cpu_codes)
