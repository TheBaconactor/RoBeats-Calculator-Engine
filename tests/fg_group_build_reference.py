"""Exact reference for FG response group-row build (prune composition oracle)."""
from __future__ import annotations

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_ROWS
from tests.parity.response_ftff_prune import (
    prune_best_positions_by_frontier,
    prune_dominated_ftff_response_positions,
)


def build_response_group_rows_reference(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
    residual_values: np.ndarray,
    frontier_idx_by_stat: np.ndarray,
    primary_ftff_delta_values: np.ndarray,
    secondary_ftff_delta_values: np.ndarray,
    score_elements_constant: bool,
    head_len: int,
    body_total: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    base_components = np.ascontiguousarray(base_components, dtype=np.int32)
    ft_values = np.ascontiguousarray(ft_values, dtype=np.int32)
    ff_values = np.ascontiguousarray(ff_values, dtype=np.int32)
    residual_values = np.ascontiguousarray(residual_values, dtype=np.int32)
    frontier_idx_by_stat = np.ascontiguousarray(frontier_idx_by_stat, dtype=np.int32)
    primary_ftff_delta_values = np.ascontiguousarray(primary_ftff_delta_values, dtype=np.int32)
    secondary_ftff_delta_values = np.ascontiguousarray(secondary_ftff_delta_values, dtype=np.int32)

    pair_count = int(ft_values.shape[0])
    positions = np.arange(pair_count, dtype=np.int32)
    meta_blocks: list[np.ndarray] = []
    ft_blocks: list[np.ndarray] = []
    ff_blocks: list[np.ndarray] = []
    ft_stat_blocks: list[np.ndarray] = []
    ff_stat_blocks: list[np.ndarray] = []
    slices: list[tuple[int, int]] = []
    start = 0

    for base in base_components:
        base_pp, base_cm, base_fm, base_primary, base_secondary, base_ft, base_ff = (int(v) for v in base)
        ft_stat_seq = np.clip(base_ft + ft_values * GEM_SCALE_FEVER, 0, TOTAL_ROWS).astype(np.int32)
        ff_stat_seq = np.clip(base_ff + ff_values * GEM_SCALE_FEVER, 0, TOTAL_ROWS).astype(np.int32)
        frontier_ids = np.ascontiguousarray(frontier_idx_by_stat[ft_stat_seq, ff_stat_seq], dtype=np.int32)
        if bool(score_elements_constant):
            best_positions = prune_best_positions_by_frontier(
                positions=positions,
                frontier_ids=frontier_ids,
                residuals=residual_values,
            )
            primary_values = np.full((int(best_positions.shape[0]),), base_primary, dtype=np.int32)
            secondary_values = np.full((int(best_positions.shape[0]),), base_secondary, dtype=np.int32)
        else:
            primary_seq = np.asarray(base_primary + primary_ftff_delta_values, dtype=np.int32)
            secondary_seq = np.asarray(base_secondary + secondary_ftff_delta_values, dtype=np.int32)
            best_positions = prune_dominated_ftff_response_positions(
                positions=positions,
                frontier_ids=frontier_ids,
                residuals=residual_values,
                primary_values=primary_seq,
                secondary_values=secondary_seq,
            )
            primary_values = np.ascontiguousarray(primary_seq[best_positions], dtype=np.int32)
            secondary_values = np.ascontiguousarray(secondary_seq[best_positions], dtype=np.int32)

        meta = np.empty((int(best_positions.shape[0]), 8), dtype=np.int32)
        meta[:, 0] = residual_values[best_positions]
        meta[:, 1] = base_pp
        meta[:, 2] = base_cm
        meta[:, 3] = base_fm
        meta[:, 4] = primary_values
        meta[:, 5] = secondary_values
        meta[:, 6] = int(head_len)
        meta[:, 7] = int(body_total)
        meta_blocks.append(meta)
        ft_blocks.append(np.ascontiguousarray(ft_values[best_positions], dtype=np.int32))
        ff_blocks.append(np.ascontiguousarray(ff_values[best_positions], dtype=np.int32))
        ft_stat_blocks.append(np.ascontiguousarray(ft_stat_seq[best_positions], dtype=np.int32))
        ff_stat_blocks.append(np.ascontiguousarray(ff_stat_seq[best_positions], dtype=np.int32))
        kept = int(best_positions.shape[0])
        slices.append((start, kept))
        start += kept

    return (
        np.concatenate(meta_blocks, axis=0),
        np.concatenate(ft_blocks),
        np.concatenate(ff_blocks),
        np.concatenate(ft_stat_blocks),
        np.concatenate(ff_stat_blocks),
        np.asarray(slices, dtype=np.int32),
    )
