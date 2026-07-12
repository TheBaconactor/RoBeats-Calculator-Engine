"""Measure the exact corner-0 index opportunity after bounded duplicate elimination.

This is research-only replay tooling. It consumes preserved region2 candidate streams, runs the
canonical cone insertion predicate, and counts how many retained-row scans a score-0-descending
auxiliary index could exclude without changing the retained producer-order frontier.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from numba import njit, types
from numba.typed import Dict, List

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _NUMBA_HEAD_SCORES_TYPE,
    _NUMBA_SURFACE_TYPE,
    _numba_head_basis_corner_scores_row,
    _numba_head_cached_scores_dominate,
    _numba_head_surface_basis,
)


@njit(cache=True, nogil=True)
def _profile_stream(rows):
    frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    frontier_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    scores = np.empty(16, dtype=np.float64)
    # raw, unique, duplicate, rejected, accepted, accepted-with-eviction,
    # reject scans, reject corner-0 eligible, eviction scans, eviction corner-0 eligible,
    # index rebuild rows, max frontier
    stats = np.zeros(12, dtype=np.int64)
    for row_idx in range(int(rows.shape[0])):
        candidate = (
            rows[row_idx, 0],
            rows[row_idx, 1],
            rows[row_idx, 2],
            rows[row_idx, 3],
            rows[row_idx, 4],
            rows[row_idx, 5],
            rows[row_idx, 6],
        )
        stats[0] += 1
        if candidate in seen:
            stats[2] += 1
            continue
        seen[candidate] = np.uint8(1)
        stats[1] += 1
        _numba_head_basis_corner_scores_row(
            _numba_head_surface_basis(candidate, 0, 100), scores
        )
        rejected = False
        for idx in range(len(frontier)):
            stats[6] += 1
            if frontier_scores[idx][0] >= scores[0]:
                stats[7] += 1
            if _numba_head_cached_scores_dominate(
                frontier_scores[idx], scores, frontier[idx], candidate
            ):
                rejected = True
                break
        if rejected:
            stats[3] += 1
            continue

        first_dominated = -1
        for idx in range(len(frontier)):
            stats[8] += 1
            if scores[0] >= frontier_scores[idx][0]:
                stats[9] += 1
            if _numba_head_cached_scores_dominate(
                scores, frontier_scores[idx], candidate, frontier[idx]
            ):
                first_dominated = idx
                break
        if first_dominated < 0:
            frontier.append(candidate)
            frontier_scores.append(scores.copy())
        else:
            stats[5] += 1
            write = int(first_dominated)
            for idx in range(int(first_dominated) + 1, len(frontier)):
                stats[8] += 1
                if scores[0] >= frontier_scores[idx][0]:
                    stats[9] += 1
                kept_scores = frontier_scores[idx]
                if not _numba_head_cached_scores_dominate(
                    scores, kept_scores, candidate, frontier[idx]
                ):
                    frontier[int(write)] = frontier[idx]
                    frontier_scores[int(write)] = kept_scores
                    write += 1
            while len(frontier) > int(write):
                frontier.pop()
                frontier_scores.pop()
            frontier.append(candidate)
            frontier_scores.append(scores.copy())
        stats[4] += 1
        # A sorted index changes on every accepted row. This is the number of retained rows
        # an O(K) maintenance strategy would touch; it is an intentionally pessimistic bound.
        stats[10] += len(frontier)
        if len(frontier) > int(stats[11]):
            stats[11] = len(frontier)

    out = np.empty((len(frontier), 7), dtype=np.uint64)
    for idx in range(len(frontier)):
        for col in range(7):
            out[idx, col] = frontier[idx][col]
    return out, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stream_bundle", type=Path)
    args = parser.parse_args()
    with np.load(args.stream_bundle, allow_pickle=False) as bundle:
        names = sorted(bundle.files, key=lambda name: int(name.rsplit("_", 1)[1]))
        total = np.zeros(12, dtype=np.int64)
        for name in names:
            _frontier, stats = _profile_stream(np.ascontiguousarray(bundle[name]))
            total += stats

    reject_cut = 1.0 - (int(total[7]) / max(1, int(total[6])))
    eviction_cut = 1.0 - (int(total[9]) / max(1, int(total[8])))
    print(f"bundle={args.stream_bundle}")
    print(
        f"raw={total[0]:,} unique={total[1]:,} duplicates={total[2]:,} "
        f"duplicate_rate={total[2] / max(1, total[0]):.3%}"
    )
    print(
        f"rejected={total[3]:,} accepted={total[4]:,} evicting_accepts={total[5]:,} "
        f"max_frontier={total[11]:,}"
    )
    print(
        f"reject_scans={total[6]:,} corner0_eligible={total[7]:,} "
        f"cutoff_reduction={reject_cut:.3%}"
    )
    print(
        f"eviction_scans={total[8]:,} corner0_eligible={total[9]:,} "
        f"cutoff_reduction={eviction_cut:.3%}"
    )
    print(
        f"accepted_index_touch_bound={total[10]:,} "
        f"eligible_scan_to_index_touch_ratio="
        f"{(total[7] + total[9]) / max(1, total[10]):.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
