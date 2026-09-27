"""Golden parity: GPU FG group-row builder == prune-composition reference."""
from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.gpu

from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_ROWS
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.taichi_gem.force_greats.response_group_build_kernels import (
    build_response_group_rows_gpu,
)
from tests.fg_group_build_reference import build_response_group_rows_reference


def _frontier_idx_per_pos(ft_values, ff_values):
    grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for pos in range(int(ft_values.shape[0])):
        ft_stat = min(TOTAL_ROWS, int(ft_values[pos]) * GEM_SCALE_FEVER)
        ff_stat = min(TOTAL_ROWS, int(ff_values[pos]) * GEM_SCALE_FEVER)
        grid[ft_stat, ff_stat] = int(pos)
    return grid


def _frontier_idx_grouped_by_ff(ft_values, ff_values):
    grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for pos in range(int(ft_values.shape[0])):
        ft_stat = min(TOTAL_ROWS, int(ft_values[pos]) * GEM_SCALE_FEVER)
        ff_stat = min(TOTAL_ROWS, int(ff_values[pos]) * GEM_SCALE_FEVER)
        grid[ft_stat, ff_stat] = int(ff_values[pos])
    return grid


def _frontier_idx_sparse_stat_grid_ids(ft_values, ff_values):
    grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for pos in range(int(ft_values.shape[0])):
        ft_stat = min(TOTAL_ROWS, int(ft_values[pos]) * GEM_SCALE_FEVER)
        ff_stat = min(TOTAL_ROWS, int(ff_values[pos]) * GEM_SCALE_FEVER)
        grid[ft_stat, ff_stat] = int((ft_stat * (TOTAL_ROWS + 1)) + ff_stat)
    return grid


def _covering_grid(frontier_id_by_pos, base_components, ft_values, ff_values):
    # Every stat key reached from each candidate's FT/FF base gets a frontier id (later bases win on overlap).
    grid = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for base_ft, base_ff in base_components[:, 5:7].tolist():
        ft_stat = np.clip(base_ft + ft_values * GEM_SCALE_FEVER, 0, TOTAL_ROWS)
        ff_stat = np.clip(base_ff + ff_values * GEM_SCALE_FEVER, 0, TOTAL_ROWS)
        grid[ft_stat, ff_stat] = frontier_id_by_pos
    return grid


_FRONTIER_ID_BY_POS = {
    "per_pos": lambda ft_values, ff_values: np.arange(int(ft_values.shape[0]), dtype=np.int32),
    "grouped_by_ff": lambda ft_values, ff_values: ff_values,
}


def _assert_six_equal(gpu_out, ref_out):
    names = ("group_meta", "group_ft", "group_ff", "group_ft_stat", "group_ff_stat", "candidate_slices")
    for name, g, c in zip(names, gpu_out, ref_out):
        g = np.asarray(g)
        c = np.asarray(c)
        assert g.shape == c.shape, f"{name} shape {g.shape} != {c.shape}"
        assert np.array_equal(g, c), f"{name} mismatch:\nGPU={g}\nREF={c}"


def _run_case(*, budget, base_components, score_elements_constant, geometry, head_len=100, body_total=8):
    ft_values, ff_values, remaining = ftff_combo_arrays(int(budget))
    ft_values = np.ascontiguousarray(ft_values, dtype=np.int32)
    ff_values = np.ascontiguousarray(ff_values, dtype=np.int32)
    residual_values = np.ascontiguousarray(remaining, dtype=np.int32)
    grid = geometry(ft_values, ff_values)
    base_components = np.ascontiguousarray(base_components, dtype=np.int32)
    if score_elements_constant:
        primary_delta = np.zeros_like(ft_values)
        secondary_delta = np.zeros_like(ff_values)
    else:
        primary_delta = np.ascontiguousarray(ft_values * GEM_SCALE_FEVER, dtype=np.int32)
        secondary_delta = np.ascontiguousarray(ff_values * GEM_SCALE_FEVER, dtype=np.int32)

    args = (
        base_components,
        ft_values,
        ff_values,
        residual_values,
        grid,
        primary_delta,
        secondary_delta,
        bool(score_elements_constant),
        int(head_len),
        int(body_total),
    )
    ref_out = build_response_group_rows_reference(*args)
    gpu_out = build_response_group_rows_gpu(*args)
    _assert_six_equal(gpu_out, ref_out)


def test_group_build_constant_path_per_pos_geometry():
    base = np.array(
        [
            [10, 20, 30, 40, 50, 0, 0],
            [30, 15, 25, 20, 80, 0, 0],
            [5, 5, 5, 1, 2, 0, 0],
        ],
        dtype=np.int32,
    )
    _run_case(budget=10, base_components=base, score_elements_constant=True, geometry=_frontier_idx_per_pos)


def test_group_build_constant_path_grouped_geometry():
    base = np.array([[10, 20, 30, 40, 50, 0, 0], [7, 8, 9, 11, 13, 0, 0]], dtype=np.int32)
    _run_case(budget=12, base_components=base, score_elements_constant=True, geometry=_frontier_idx_grouped_by_ff)


def test_group_build_dominance_path_grouped_geometry():
    base = np.array(
        [
            [10, 20, 30, 40, 50, 0, 0],
            [30, 15, 25, 20, 80, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ],
        dtype=np.int32,
    )
    _run_case(budget=12, base_components=base, score_elements_constant=False, geometry=_frontier_idx_grouped_by_ff)


def test_group_build_dominance_path_per_pos_geometry():
    base = np.array([[10, 20, 30, 40, 50, 0, 0], [3, 6, 9, 12, 15, 0, 0]], dtype=np.int32)
    _run_case(budget=16, base_components=base, score_elements_constant=False, geometry=_frontier_idx_per_pos)


def test_group_build_larger_budget_stress():
    base = np.array([[100, 50, 25, 60, 70, 0, 0], [10, 20, 30, 5, 9, 0, 0]], dtype=np.int32)
    _run_case(budget=24, base_components=base, score_elements_constant=False, geometry=_frontier_idx_grouped_by_ff)


def test_group_build_accepts_sparse_stat_grid_frontier_ids():
    base = np.array([[100, 50, 25, 60, 70, 0, 0], [10, 20, 30, 5, 9, 0, 0]], dtype=np.int32)
    _run_case(budget=12, base_components=base, score_elements_constant=False, geometry=_frontier_idx_sparse_stat_grid_ids)


@pytest.mark.parametrize("frontier_ids", sorted(_FRONTIER_ID_BY_POS))
@pytest.mark.parametrize("score_elements_constant", (True, False))
@pytest.mark.parametrize("candidate_count", (1, 51, 63, 64, 65, 128, 129, 300))
def test_group_build_any_batch_size_matches_reference(candidate_count, score_elements_constant, frontier_ids):
    # Sizes straddle the per-launch candidate chunk boundaries and exceed the old 256-candidate cap.
    rng = np.random.default_rng(candidate_count)
    base = np.concatenate(
        (rng.integers(0, 100, size=(candidate_count, 5)), rng.integers(0, 41, size=(candidate_count, 2))),
        axis=1,
    ).astype(np.int32)

    def geometry(ft_values, ff_values):
        return _covering_grid(_FRONTIER_ID_BY_POS[frontier_ids](ft_values, ff_values), base, ft_values, ff_values)

    _run_case(budget=12, base_components=base, score_elements_constant=score_elements_constant, geometry=geometry)
