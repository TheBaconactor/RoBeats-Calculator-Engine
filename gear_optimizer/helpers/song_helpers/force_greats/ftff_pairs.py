from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import logging


logger = logging.getLogger(__name__)
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

