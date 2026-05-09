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
def test_combined_skyline_gpu_matches_cpu_reference_with_duplicates():
    from gear_optimizer.solver.exact_skyline import (
        _combined_global_skyline_pairs_6d_lane_base_with_indices,
        _combined_global_skyline_pairs_6d_lane_base_with_indices_cpu_reference,
    )

    gear_points = np.asarray(
        [
            [0, 15, 1, 2, 3, 100],
            [0, 15, 1, 2, 3, 105],
            [1, 5, 6, 7, 8, 200],
            [1, 5, 6, 8, 8, 190],
            [2, 3, 4, 5, 6, 20],
            [2, 4, 4, 5, 6, 19],
            [3, 1, 2, 3, 4, 50],
        ],
        dtype=np.int32,
    )
    mini_points = np.asarray(
        [
            [2, 2, 3, 4, 7],
            [2, 2, 3, 4, 7],
            [5, 7, 1, 2, 30],
            [1, 1, 9, 2, 40],
            [0, 0, 0, 10, 60],
        ],
        dtype=np.int32,
    )

    cpu_g, cpu_m = _combined_global_skyline_pairs_6d_lane_base_with_indices_cpu_reference(gear_points, mini_points)
    gpu_g, gpu_m = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, mini_points)

    def stats(g_idx: np.ndarray, m_idx: np.ndarray) -> list[tuple[int, int, int, int, int, int]]:
        return sorted(
            map(
                tuple,
                np.column_stack(
                    (
                        gear_points[g_idx, 0],
                        np.minimum(160, gear_points[g_idx, 1] + mini_points[m_idx, 0]),
                        np.minimum(160, gear_points[g_idx, 2] + mini_points[m_idx, 1]),
                        np.minimum(160, gear_points[g_idx, 3] + mini_points[m_idx, 2]),
                        np.minimum(160, gear_points[g_idx, 4] + mini_points[m_idx, 3]),
                        gear_points[g_idx, 5] + mini_points[m_idx, 4],
                    )
                ),
            )
        )

    assert stats(gpu_g, gpu_m) == stats(cpu_g, cpu_m)
