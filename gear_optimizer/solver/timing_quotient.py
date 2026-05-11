from __future__ import annotations

from functools import lru_cache

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, MAX_STAT_INDEX, TOTAL_GEM_BUDGET
from gear_optimizer.solver.taichi_gem.ftff_combos import ftff_combo_arrays as _shared_ftff_combo_arrays


@lru_cache(maxsize=None)
def ftff_combo_arrays(total_budget: int = TOTAL_GEM_BUDGET) -> tuple[np.ndarray, np.ndarray]:
    ft_values, ff_values, _budget_left = _shared_ftff_combo_arrays(int(total_budget))
    return (
        np.asarray(ft_values, dtype=np.int16),
        np.asarray(ff_values, dtype=np.int16),
    )


def _pack_keep_bits(keep_mask: np.ndarray, word_count: int) -> np.ndarray:
    words = np.zeros(word_count, dtype=np.uint32)
    kept_indices = np.flatnonzero(keep_mask)
    for idx in kept_indices:
        words[idx >> 5] |= np.uint32(1 << (idx & 31))
    return words


def build_timing_quotient_keep_bits(
    sig0: np.ndarray,
    sig1: np.ndarray,
    frontier_count: np.ndarray,
    templates: np.ndarray,
    *,
    w_ft: int,
    w_ff: int,
    w_overflow: int,
    total_budget: int = TOTAL_GEM_BUDGET,
    gem_scale: int = GEM_SCALE_FEVER,
) -> tuple[np.ndarray, dict[str, int]]:
    """Build exact candidate-local FT/FF quotient masks.

    The quotient is base-only and candidate-local. It never deletes a loadout;
    it only removes an FT/FF timing allocation when another reachable allocation
    has the same base timing response, no less residual gem budget, and enough
    overflow-adjusted selected-element value to copy the removed residual solve.
    """

    sig0_arr = np.asarray(sig0, dtype=np.uint64)
    sig1_arr = np.asarray(sig1, dtype=np.uint64)
    frontier_arr = np.asarray(frontier_count, dtype=np.int16)
    template_arr = np.asarray(templates, dtype=np.int16)
    if template_arr.size == 0:
        template_arr = np.empty((0, 2), dtype=np.int16)
    elif template_arr.ndim != 2 or template_arr.shape[1] != 2:
        raise ValueError("templates must have shape (n, 2)")

    combo_ft, combo_ff = ftff_combo_arrays(total_budget)
    combo_count = int(combo_ft.size)
    word_count = (combo_count + 31) // 32

    keep_bits = np.full(
        (MAX_STAT_INDEX + 1, MAX_STAT_INDEX + 1, word_count),
        np.uint32(0xFFFFFFFF),
        dtype=np.uint32,
    )
    if combo_count % 32:
        tail_bits = combo_count & 31
        keep_bits[:, :, -1] = np.uint32((1 << tail_bits) - 1)

    stats = {
        "timing_quotient_templates": int(template_arr.shape[0]),
        "timing_quotient_raw_records": 0,
        "timing_quotient_kept_records": 0,
        "timing_quotient_pruned_records": 0,
    }
    if template_arr.shape[0] == 0:
        return keep_bits, stats

    unique_templates = np.unique(template_arr.astype(np.int16, copy=False), axis=0)
    stats["timing_quotient_templates"] = int(unique_templates.shape[0])

    residual = (total_budget - combo_ft.astype(np.int32) - combo_ff.astype(np.int32)).astype(
        np.int16
    )
    delta_v = combo_ft.astype(np.int32) * int(w_ft) + combo_ff.astype(np.int32) * int(w_ff)
    adjusted_value = delta_v + int(w_overflow) * residual.astype(np.int32)

    for base_ft_raw, base_ff_raw in unique_templates:
        base_ft = int(np.clip(base_ft_raw, 0, MAX_STAT_INDEX))
        base_ff = int(np.clip(base_ff_raw, 0, MAX_STAT_INDEX))
        max_ft_gems = max(0, (MAX_STAT_INDEX - base_ft) // gem_scale)
        max_ff_gems = max(0, (MAX_STAT_INDEX - base_ff) // gem_scale)
        valid = (combo_ft <= max_ft_gems) & (combo_ff <= max_ff_gems)

        final_ft = np.minimum(MAX_STAT_INDEX, base_ft + combo_ft.astype(np.int32) * gem_scale)
        final_ff = np.minimum(MAX_STAT_INDEX, base_ff + combo_ff.astype(np.int32) * gem_scale)
        single_frontier = frontier_arr[final_ft, final_ff] <= 1

        keep = valid.copy()
        quotable = valid & single_frontier
        raw_count = int(valid.sum())
        stats["timing_quotient_raw_records"] += raw_count

        if np.any(quotable):
            sig_pairs = np.column_stack(
                (
                    sig0_arr[final_ft[quotable], final_ff[quotable]],
                    sig1_arr[final_ft[quotable], final_ff[quotable]],
                )
            )
            _unique_pairs, sig_group = np.unique(sig_pairs, axis=0, return_inverse=True)
            source_indices = np.flatnonzero(quotable)
            keep[source_indices] = False

            for signature in np.unique(sig_group):
                group_mask = sig_group == signature
                group_indices = source_indices[group_mask]
                group_residual = residual[group_indices].astype(np.int32)
                group_adjusted = adjusted_value[group_indices].astype(np.int32)
                order = np.lexsort((group_indices, -group_adjusted, -group_residual))

                best_adjusted = None
                for local_pos in order:
                    combo_idx = int(group_indices[local_pos])
                    value = int(group_adjusted[local_pos])
                    if best_adjusted is not None and best_adjusted >= value:
                        continue
                    keep[combo_idx] = True
                    best_adjusted = value

        kept_count = int(keep.sum())
        stats["timing_quotient_kept_records"] += kept_count
        stats["timing_quotient_pruned_records"] += raw_count - kept_count
        keep_bits[base_ft, base_ff, :] = _pack_keep_bits(keep, word_count)

    return keep_bits, stats
