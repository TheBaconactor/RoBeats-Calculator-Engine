from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, TOTAL_ROWS
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays

_ResponsePair = tuple[int, int, int, dict[str, Any] | tuple[int, ...], Any, float, float]
_FTFF_PRUNE_WARMED = False


@lru_cache(maxsize=4096)
def best_response_positions_for_base_ftff(
    *,
    total_budget: int,
    base_ft: int,
    base_ff: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ft_values, ff_values, remaining = ftff_combo_arrays(int(total_budget))
    ft_stat_seq = np.clip(int(base_ft) + (ft_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
    ff_stat_seq = np.clip(int(base_ff) + (ff_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
    canonical_key_seq = ((ft_stat_seq * (TOTAL_ROWS + 1)) + ff_stat_seq).astype(np.int32, copy=False)
    positions = np.arange(int(ft_values.shape[0]), dtype=np.int32)
    unique_keys, first_positions = np.unique(canonical_key_seq, return_index=True)
    if int(unique_keys.shape[0]) == int(canonical_key_seq.shape[0]):
        best_positions = positions
    else:
        sort_order = np.lexsort((positions, -np.asarray(remaining, dtype=np.int32), canonical_key_seq))
        sorted_keys = canonical_key_seq[sort_order]
        first_sorted = np.empty(int(sorted_keys.shape[0]), dtype=np.bool_)
        first_sorted[0] = True
        first_sorted[1:] = sorted_keys[1:] != sorted_keys[:-1]
        best_positions_by_key = sort_order[first_sorted]
        if int(unique_keys.shape[0]) != int(best_positions_by_key.shape[0]):
            raise ValueError("FG response frontier packed prune found inconsistent frontier groups")
        best_positions = best_positions_by_key[np.argsort(first_positions, kind="stable")]
    return (
        np.ascontiguousarray(best_positions, dtype=np.int32),
        np.ascontiguousarray(ft_stat_seq[best_positions], dtype=np.int32),
        np.ascontiguousarray(ff_stat_seq[best_positions], dtype=np.int32),
    )


def score_elements(stats: dict[str, Any] | tuple[int, ...], primary_color: str, secondary_color: str) -> tuple[int, int]:
    if isinstance(stats, tuple):
        return int(stats[3]), int(stats[4])
    return (
        int(stats.get(str(primary_color or ""), 0) or 0),
        int(stats.get(str(secondary_color or ""), 0) or 0),
    )


@jit(nopython=True, cache=True)
def _prune_best_positions_by_frontier_linear(
    positions: np.ndarray,
    frontier_ids: np.ndarray,
    residuals: np.ndarray,
) -> np.ndarray:
    row_count = int(positions.shape[0])
    max_frontier = -1
    for row in range(row_count):
        fid = int(frontier_ids[row])
        if fid > max_frontier:
            max_frontier = fid
    if max_frontier < 0:
        return np.empty((0,), dtype=np.int32)

    first_order = np.full((max_frontier + 1,), -1, dtype=np.int32)
    best_local = np.full((max_frontier + 1,), -1, dtype=np.int32)
    best_residual = np.full((max_frontier + 1,), -2147483648, dtype=np.int32)
    ordered_frontiers = np.empty((row_count,), dtype=np.int32)
    ordered_count = 0
    for local_idx in range(row_count):
        fid = int(frontier_ids[local_idx])
        if fid < 0:
            continue
        if first_order[fid] < 0:
            first_order[fid] = ordered_count
            ordered_frontiers[ordered_count] = fid
            ordered_count += 1
            best_local[fid] = local_idx
            best_residual[fid] = int(residuals[local_idx])
            continue
        residual = int(residuals[local_idx])
        current_best_local = int(best_local[fid])
        if residual > int(best_residual[fid]) or (
            residual == int(best_residual[fid]) and int(positions[local_idx]) < int(positions[current_best_local])
        ):
            best_local[fid] = local_idx
            best_residual[fid] = residual

    out = np.empty((ordered_count,), dtype=np.int32)
    for order_idx in range(ordered_count):
        fid = int(ordered_frontiers[order_idx])
        out[order_idx] = int(positions[int(best_local[fid])])
    return out


def prune_best_positions_by_frontier(
    *,
    positions: np.ndarray,
    frontier_ids: np.ndarray,
    residuals: np.ndarray,
) -> np.ndarray:
    if int(positions.shape[0]) != int(frontier_ids.shape[0]) or int(positions.shape[0]) != int(residuals.shape[0]):
        raise ValueError("FG response frontier best-position prune received inconsistent arrays")
    if int(positions.shape[0]) <= 1:
        return np.ascontiguousarray(positions, dtype=np.int32)
    if bool(np.any(np.asarray(frontier_ids, dtype=np.int32) < 0)):
        raise ValueError("FG response frontier best-position prune received a negative frontier id")
    return np.ascontiguousarray(
        _prune_best_positions_by_frontier_linear(
            np.ascontiguousarray(positions, dtype=np.int32),
            np.ascontiguousarray(frontier_ids, dtype=np.int32),
            np.ascontiguousarray(residuals, dtype=np.int32),
        ),
        dtype=np.int32,
    )


def warmup_response_ftff_prune() -> None:
    global _FTFF_PRUNE_WARMED
    if bool(_FTFF_PRUNE_WARMED):
        return
    positions = np.asarray([0, 1, 2, 3], dtype=np.int32)
    frontier_ids = np.asarray([0, 0, 1, 0], dtype=np.int32)
    residuals = np.asarray([1, 3, 2, 2], dtype=np.int32)
    got = prune_best_positions_by_frontier(
        positions=positions,
        frontier_ids=frontier_ids,
        residuals=residuals,
    )
    if got.tolist() != [1, 2]:
        raise RuntimeError("FG response FT/FF prune warmup produced an invalid result")
    _FTFF_PRUNE_WARMED = True


def prune_dominated_ftff_response_positions(
    *,
    positions: np.ndarray,
    frontier_ids: np.ndarray,
    residuals: np.ndarray,
    primary_values: np.ndarray,
    secondary_values: np.ndarray,
) -> np.ndarray:
    row_count = int(positions.shape[0])
    if (
        row_count != int(frontier_ids.shape[0])
        or row_count != int(residuals.shape[0])
        or row_count != int(primary_values.shape[0])
        or row_count != int(secondary_values.shape[0])
    ):
        raise ValueError("FG response frontier dominance prune received inconsistent arrays")
    if row_count <= 1:
        return np.ascontiguousarray(positions, dtype=np.int32)

    buckets: dict[int, list[int]] = {}
    frontier_seq = np.asarray(frontier_ids, dtype=np.int32)
    for local_idx, frontier_id in enumerate(frontier_seq.tolist()):
        buckets.setdefault(int(frontier_id), []).append(int(local_idx))

    residual_seq = np.asarray(residuals, dtype=np.int32)
    primary_seq = np.asarray(primary_values, dtype=np.int32)
    secondary_seq = np.asarray(secondary_values, dtype=np.int32)
    kept_local_indices: list[int] = []
    for bucket_indices in buckets.values():
        if len(bucket_indices) <= 1:
            kept_local_indices.extend(bucket_indices)
            continue

        first_idx = int(bucket_indices[0])
        first_primary = int(primary_seq[first_idx])
        first_secondary = int(secondary_seq[first_idx])
        same_score_elements = True
        best_idx = first_idx
        best_residual = int(residual_seq[first_idx])
        for local_idx in bucket_indices[1:]:
            idx = int(local_idx)
            primary = int(primary_seq[idx])
            secondary = int(secondary_seq[idx])
            if primary != first_primary or secondary != first_secondary:
                same_score_elements = False
                break
            residual = int(residual_seq[idx])
            if residual > best_residual:
                best_idx = idx
                best_residual = residual
        if same_score_elements:
            kept_local_indices.append(int(best_idx))
            continue

        order = sorted(
            range(len(bucket_indices)),
            key=lambda idx: (
                -int(residual_seq[int(bucket_indices[idx])]),
                -int(primary_seq[int(bucket_indices[idx])]),
                -int(secondary_seq[int(bucket_indices[idx])]),
                int(idx),
            ),
        )
        skyline: list[tuple[int, int]] = []
        kept_bucket_offsets: set[int] = set()
        for bucket_offset in order:
            local_idx = int(bucket_indices[int(bucket_offset)])
            primary = int(primary_seq[local_idx])
            secondary = int(secondary_seq[local_idx])
            dominated = False
            for kept_primary, kept_secondary in skyline:
                if int(kept_primary) >= primary and int(kept_secondary) >= secondary:
                    dominated = True
                    break
            if dominated:
                continue

            write = 0
            for kept_primary, kept_secondary in skyline:
                if primary >= int(kept_primary) and secondary >= int(kept_secondary):
                    continue
                skyline[write] = (int(kept_primary), int(kept_secondary))
                write += 1
            del skyline[write:]
            skyline.append((primary, secondary))
            kept_bucket_offsets.add(int(bucket_offset))
        kept_local_indices.extend(
            int(bucket_indices[idx]) for idx in range(len(bucket_indices)) if int(idx) in kept_bucket_offsets
        )

    return np.ascontiguousarray(positions[np.asarray(kept_local_indices, dtype=np.intp)], dtype=np.int32)


def element_ftff_delta(color: str, ft: int, ff: int) -> int:
    if str(color or "") == "Beat":
        return int(ft) * GEM_STAT_TO_ELEMENT_SCALE
    if str(color or "") == "Vibe":
        return int(ff) * GEM_STAT_TO_ELEMENT_SCALE
    return 0


def response_pair_dominates(
    a: _ResponsePair,
    b: _ResponsePair,
    *,
    primary_color: str,
    secondary_color: str,
) -> bool:
    if a[4] is not b[4]:
        return False
    if int(a[2]) < int(b[2]):
        return False
    a_primary, a_secondary = score_elements(a[3], primary_color, secondary_color)
    b_primary, b_secondary = score_elements(b[3], primary_color, secondary_color)
    return int(a_primary) >= int(b_primary) and int(a_secondary) >= int(b_secondary)


def prune_dominated_ftff_response_pairs(
    pairs: list[_ResponsePair],
    *,
    primary_color: str,
    secondary_color: str,
    frontier_key_of: Callable[[_ResponsePair], int] | None = None,
) -> list[_ResponsePair]:
    identity_of = frontier_key_of or (lambda pair: int(id(pair[4])))
    by_frontier: dict[int, list[_ResponsePair]] = {}
    for pair in pairs:
        by_frontier.setdefault(int(identity_of(pair)), []).append(pair)

    out: list[_ResponsePair] = []
    for bucket in by_frontier.values():
        if len(bucket) <= 1:
            out.extend(bucket)
            continue
        first_primary, first_secondary = score_elements(bucket[0][3], primary_color, secondary_color)
        best_idx = 0
        best_residual = int(bucket[0][2])
        same_score_elements = True
        for idx, pair in enumerate(bucket[1:], start=1):
            primary, secondary = score_elements(pair[3], primary_color, secondary_color)
            if int(primary) != int(first_primary) or int(secondary) != int(first_secondary):
                same_score_elements = False
                break
            residual = int(pair[2])
            if residual > best_residual:
                best_idx = int(idx)
                best_residual = int(residual)
        if same_score_elements:
            out.append(bucket[best_idx])
            continue

        rows = [
            (
                idx,
                pair,
                int(pair[2]),
                *score_elements(pair[3], primary_color, secondary_color),
            )
            for idx, pair in enumerate(bucket)
        ]
        rows.sort(key=lambda row: (-row[2], -row[3], -row[4], row[0]))
        skyline: list[tuple[int, int]] = []
        kept_indices: set[int] = set()
        for idx, _pair, _residual, primary, secondary in rows:
            dominated = False
            for kept_primary, kept_secondary in skyline:
                if int(kept_primary) >= int(primary) and int(kept_secondary) >= int(secondary):
                    dominated = True
                    break
            if dominated:
                continue

            write = 0
            for kept_primary, kept_secondary in skyline:
                if int(primary) >= int(kept_primary) and int(secondary) >= int(kept_secondary):
                    continue
                skyline[write] = (kept_primary, kept_secondary)
                write += 1
            del skyline[write:]
            skyline.append((int(primary), int(secondary)))
            kept_indices.add(int(idx))
        out.extend(pair for idx, pair in enumerate(bucket) if int(idx) in kept_indices)
    return out
