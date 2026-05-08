from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import logging


logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class FTFFSurfaceReductionResult:
    """Lossless FT/FF pair reduction result for an exact FG max-FP surface."""

    pairs: Any
    max_fp_matrix: Any
    dropped: int


@dataclass(frozen=True)
class FTFFKeyReductionResult:
    """Lossless FT/FF pair reduction result for an exact surface-key stream."""

    pairs: Any
    kept_indices: Any
    dropped: int


def _ftff_pair_state(
    pair: tuple[int, int],
    *,
    total_budget: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
) -> tuple[int, int, int, int, int]:
    ft_gems, ff_gems = pair
    budget = int(total_budget) - int(ft_gems) - int(ff_gems)
    p_delta = (int(ft_gems) * int(is_p_ft) + int(ff_gems) * int(is_p_ff)) * 3
    s_delta = (int(ft_gems) * int(is_s_ft) + int(ff_gems) * int(is_s_ff)) * 3
    return int(budget), int(p_delta), int(s_delta), int(ft_gems), int(ff_gems)


def _ftff_state_dominates(a: tuple[int, int, int, int, int], b: tuple[int, int, int, int, int]) -> bool:
    a_budget, a_p, a_s, a_ft, a_ff = a
    b_budget, b_p, b_s, b_ft, b_ff = b
    if a_budget < b_budget or a_p < b_p or a_s < b_s:
        return False
    if a_budget > b_budget or a_p > b_p or a_s > b_s:
        return True
    return (a_ft, a_ff) <= (b_ft, b_ff)


def _hashable_surface_key(key: Any) -> object:
    try:
        hash(key)
        return key
    except TypeError:
        pass

    if hasattr(key, "tobytes"):
        try:
            return key.tobytes()
        except Exception as e:
            logger.debug(f"ftff_pairs:_hashable_surface_key: {e}")
    if hasattr(key, "tolist"):
        try:
            key = key.tolist()
        except Exception as e:
            logger.debug(f"ftff_pairs:_hashable_surface_key: {e}")
    if isinstance(key, list):
        return tuple(_hashable_surface_key(item) for item in key)
    if isinstance(key, dict):
        items = ((_hashable_surface_key(k), _hashable_surface_key(v)) for k, v in key.items())
        return tuple(sorted(items, key=lambda item: repr(item[0])))
    return repr(key)


def reduce_ftff_pairs_by_surface_keys(
    ftff_pairs: Any,
    surface_keys: Any,
    *,
    total_budget: int,
    is_p_ft: int = 0,
    is_s_ft: int = 0,
    is_p_ff: int = 0,
    is_s_ff: int = 0,
) -> FTFFKeyReductionResult:
    """Reduce FT/FF pairs inside exact same-surface buckets.

    The caller owns the proof that each `surface_key` is a complete downstream
    scoring surface. This helper implements the shared BASE-2 / BASE-9
    dominance certificate only: within one exact key, drop a pair when another
    pair leaves no less remaining budget and no less primary/secondary value.
    """
    import numpy as np

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception as e:
        logger.debug(f"ftff_pairs:reduce_ftff_pairs_by_surface_keys: {e}")
        pairs_arr = np.asarray(list(ftff_pairs), dtype=np.int32)
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return FTFFKeyReductionResult(ftff_pairs, np.asarray([], dtype=np.int64), 0)
    n_pairs = int(pairs_arr.shape[0])
    if n_pairs <= 0:
        return FTFFKeyReductionResult(pairs_arr[:, :2], np.asarray([], dtype=np.int64), 0)

    try:
        keys_list = list(surface_keys)
    except Exception as e:
        logger.debug(f"ftff_pairs:reduce_ftff_pairs_by_surface_keys: {e}")
        keys_list = []
    if len(keys_list) < n_pairs:
        return FTFFKeyReductionResult(pairs_arr[:, :2], np.arange(n_pairs, dtype=np.int64), 0)

    kept_by_surface: dict[object, list[tuple[int, tuple[int, int, int, int, int]]]] = {}
    kept_indices: list[int] = []
    for idx in range(n_pairs):
        key = _hashable_surface_key(keys_list[int(idx)])
        pair = (int(pairs_arr[int(idx), 0]), int(pairs_arr[int(idx), 1]))
        state = _ftff_pair_state(
            pair,
            total_budget=int(total_budget),
            is_p_ft=int(is_p_ft),
            is_s_ft=int(is_s_ft),
            is_p_ff=int(is_p_ff),
            is_s_ff=int(is_s_ff),
        )
        frontier = kept_by_surface.setdefault(key, [])
        if any(_ftff_state_dominates(prev_state, state) for _prev_idx, prev_state in frontier):
            continue
        removed = {prev_idx for prev_idx, prev_state in frontier if _ftff_state_dominates(state, prev_state)}
        if removed:
            frontier[:] = [(prev_idx, prev_state) for prev_idx, prev_state in frontier if prev_idx not in removed]
            kept_indices = [prev_idx for prev_idx in kept_indices if prev_idx not in removed]
        frontier.append((int(idx), state))
        kept_indices.append(int(idx))

    if len(kept_indices) >= n_pairs:
        return FTFFKeyReductionResult(pairs_arr[:, :2], np.arange(n_pairs, dtype=np.int64), 0)

    kept_idx_arr = np.asarray(sorted(kept_indices), dtype=np.int64)
    reduced_pairs = np.ascontiguousarray(pairs_arr[kept_idx_arr, :2], dtype=np.int32)
    return FTFFKeyReductionResult(reduced_pairs, kept_idx_arr, int(n_pairs - int(reduced_pairs.shape[0])))


def reduce_ftff_pairs_by_max_fp_surface(
    ftff_pairs: Any,
    max_fp_matrix: Any,
    *,
    n_sections: int,
    total_budget: int,
    is_p_ft: int = 0,
    is_s_ft: int = 0,
    is_p_ff: int = 0,
    is_s_ff: int = 0,
) -> tuple[Any, Any, int]:
    """Losslessly reduce FT/FF pairs after the exact downstream FG surface exists.

    Pairs with identical max-FP rows expose the same forced-Great breakpoint
    surface to the exact-inner solver. Within one surface bucket, a pair can be
    removed only if another pair leaves at least as much remaining gem budget
    and at least as much elemental value on both primary/secondary lanes.

    This is the shared reduction contract for both older explicit max-FP paths
    and newer fused GPU paths. Full-window callers should run this before
    pair-tiling so dominance can see representatives across tile boundaries.
    """
    import numpy as np

    try:
        n_sections_i = max(0, int(n_sections))
    except Exception as e:
        logger.debug(f"ftff_pairs:reduce_ftff_pairs_by_max_fp_surface: {e}")
        n_sections_i = 0
    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception as e:
        logger.debug(f"ftff_pairs:reduce_ftff_pairs_by_max_fp_surface: {e}")
        pairs_arr = np.asarray(list(ftff_pairs), dtype=np.int32)
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return FTFFSurfaceReductionResult(ftff_pairs, max_fp_matrix, 0)
    n_pairs = int(pairs_arr.shape[0])
    if n_pairs <= 0 or n_sections_i <= 0:
        return FTFFSurfaceReductionResult(pairs_arr[:, :2], max_fp_matrix, 0)

    m = np.asarray(max_fp_matrix, dtype=np.int16)
    if m.ndim != 2 or int(m.shape[0]) < n_pairs:
        return FTFFSurfaceReductionResult(pairs_arr[:, :2], max_fp_matrix, 0)
    if int(m.shape[1]) < n_sections_i:
        n_sections_i = int(m.shape[1])
    if n_sections_i <= 0:
        return FTFFSurfaceReductionResult(pairs_arr[:, :2], m[:n_pairs], 0)

    rows = np.maximum(m[:n_pairs, :n_sections_i], 0)
    rows = np.ascontiguousarray(rows, dtype=np.int16)
    row_dtype = np.dtype((np.void, int(rows.dtype.itemsize) * int(n_sections_i)))
    keys = rows.view(row_dtype).reshape(-1)

    reduced_by_key = reduce_ftff_pairs_by_surface_keys(
        pairs_arr,
        (bytes(keys[int(idx)]) for idx in range(n_pairs)),
        total_budget=int(total_budget),
        is_p_ft=int(is_p_ft),
        is_s_ft=int(is_s_ft),
        is_p_ff=int(is_p_ff),
        is_s_ff=int(is_s_ff),
    )
    if int(reduced_by_key.dropped) <= 0:
        return FTFFSurfaceReductionResult(pairs_arr[:, :2], m[:n_pairs], 0)

    kept_idx_arr = np.asarray(reduced_by_key.kept_indices, dtype=np.int64)
    reduced_pairs = np.ascontiguousarray(pairs_arr[kept_idx_arr, :2], dtype=np.int32)
    reduced_matrix = np.ascontiguousarray(m[kept_idx_arr, :], dtype=np.int16)
    return FTFFSurfaceReductionResult(reduced_pairs, reduced_matrix, int(reduced_by_key.dropped))


def _group_ftff_pairs_by_max_fp_matrix(
    ftff_pairs: Any,
    max_fp_matrix: Any,
    *,
    n_sections: int,
) -> list[dict]:
    """
    Group FT/FF pairs by identical per-section max-FP caps.

    Ordering matches deterministic dict-insertion behavior:
    - Groups are yielded in order of first appearance in `ftff_pairs`.
    - Pairs within each group preserve their original order.
    """
    import numpy as np

    try:
        n_sections_i = max(0, int(n_sections))
    except Exception as e:
        logger.debug(f"ftff_pairs:_group_ftff_pairs_by_max_fp_matrix: {e}")
        n_sections_i = 0
    if n_sections_i <= 0:
        return []

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception as e:
        logger.debug(f"ftff_pairs:_group_ftff_pairs_by_max_fp_matrix: {e}")
        pairs_arr = np.asarray(list(ftff_pairs), dtype=np.int32)
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return []
    n_pairs = int(pairs_arr.shape[0])
    if n_pairs <= 0:
        return []

    m = np.asarray(max_fp_matrix, dtype=np.int16)
    if m.ndim != 2 or int(m.shape[0]) < n_pairs:
        return []
    if int(m.shape[1]) < n_sections_i:
        n_sections_i = int(m.shape[1])
    if n_sections_i <= 0:
        return []

    m0 = np.maximum(m[:n_pairs, :n_sections_i], 0)
    m0 = np.ascontiguousarray(m0, dtype=np.int16)

    row_dtype = np.dtype((np.void, int(m0.dtype.itemsize) * int(n_sections_i)))
    keys = m0.view(row_dtype).reshape(-1)
    uniq, first, inv = np.unique(keys, return_index=True, return_inverse=True)
    if int(getattr(uniq, "size", 0) or 0) <= 0:
        return []

    order = np.argsort(first)
    # `inv` already identifies the group for each pair. Sort once by group id,
    # then slice contiguous ranges instead of rescanning the full inverse array
    # for every unique group.
    sort_idx = np.argsort(inv, kind="stable")
    inv_sorted = inv[sort_idx]
    group_count = int(getattr(uniq, "size", 0) or 0)
    if group_count <= 0:
        return []
    group_starts = np.empty(group_count, dtype=np.int64)
    group_ends = np.empty(group_count, dtype=np.int64)
    if group_count == 1:
        group_starts[0] = 0
        group_ends[0] = int(sort_idx.size)
    else:
        boundaries = np.flatnonzero(inv_sorted[1:] != inv_sorted[:-1]).astype(np.int64, copy=False) + 1
        group_starts[0] = 0
        group_starts[1:] = boundaries
        group_ends[:-1] = boundaries
        group_ends[-1] = int(sort_idx.size)

    out: list[dict] = []
    for u in order:
        group_idx = int(u)
        start = int(group_starts[group_idx])
        end = int(group_ends[group_idx])
        if end <= start:
            continue
        idxs = sort_idx[start:end]
        max_fp_row = m0[int(first[group_idx])]
        out.append(
            {
                "ftff_pairs": pairs_arr[idxs, :2],
                "counts_max_fp": [int(x) for x in max_fp_row[:n_sections_i]],
            }
        )
    return out

