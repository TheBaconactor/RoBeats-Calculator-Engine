"""Exact scalar-versus-block cone-inserter replay for Issue #116 Layer 3.

Research only: preserved candidate streams are replayed into the same producer-order maximal
frontier using contiguous surface rows and corner-major float64 score storage. Block mode
transposes only the independent 16-corner rejection precheck; margin arithmetic and canonical
eviction/compaction remain scalar and unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
from numba import njit, types
from numba.typed import Dict

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _NUMBA_SURFACE_TYPE,
    _numba_head_basis_corner_scores_row,
    _numba_head_cached_scores_dominate,
    _numba_head_surface_basis,
    _numba_head_surface_margin,
)


@njit(cache=True, nogil=True)
def _surface_tuple(rows, idx: int):
    return (
        rows[int(idx), 0],
        rows[int(idx), 1],
        rows[int(idx), 2],
        rows[int(idx), 3],
        rows[int(idx), 4],
        rows[int(idx), 5],
        rows[int(idx), 6],
    )


@njit(cache=True, nogil=True)
def _grow(frontier_rows, score_cols, count: int):
    if int(count) < int(frontier_rows.shape[0]):
        return frontier_rows, score_cols
    new_cap = max(1, int(frontier_rows.shape[0]) * 2)
    new_rows = np.empty((int(new_cap), 7), dtype=np.uint64)
    new_scores = np.empty((16, int(new_cap)), dtype=np.float64)
    if int(count) > 0:
        new_rows[: int(count), :] = frontier_rows[: int(count), :]
        new_scores[:, : int(count)] = score_cols[:, : int(count)]
    return new_rows, new_scores


@njit(cache=True, nogil=True)
def _scalar_dominator(frontier_rows, score_cols, count: int, candidate, candidate_scores) -> int:
    retained_scores = np.empty(16, dtype=np.float64)
    for idx in range(int(count)):
        for corner in range(16):
            retained_scores[int(corner)] = score_cols[int(corner), int(idx)]
        if _numba_head_cached_scores_dominate(
            retained_scores,
            candidate_scores,
            _surface_tuple(frontier_rows, int(idx)),
            candidate,
        ):
            return int(idx)
    return -1


@njit(cache=True, nogil=True)
def _block_dominator(
    frontier_rows,
    score_cols,
    count: int,
    candidate,
    candidate_scores,
    block_width: int,
    eligible,
) -> int:
    for start in range(0, int(count), int(block_width)):
        width = min(int(block_width), int(count) - int(start))
        for lane in range(int(width)):
            eligible[int(lane)] = 1
        for corner in range(16):
            active = 0
            candidate_score = candidate_scores[int(corner)]
            for lane in range(int(width)):
                if (
                    int(eligible[int(lane)]) != 0
                    and score_cols[int(corner), int(start) + int(lane)] < candidate_score
                ):
                    eligible[int(lane)] = 0
                active += int(eligible[int(lane)])
            if int(active) == 0:
                break
        for lane in range(int(width)):
            if int(eligible[int(lane)]) == 0:
                continue
            idx = int(start) + int(lane)
            retained = _surface_tuple(frontier_rows, int(idx))
            margin = _numba_head_surface_margin(retained, candidate)
            if margin <= 0.0:
                return int(idx)
            dominates = True
            for corner in range(16):
                if (
                    score_cols[int(corner), int(idx)] - candidate_scores[int(corner)]
                    < margin
                ):
                    dominates = False
                    break
            if dominates:
                return int(idx)
    return -1


@njit(cache=True, nogil=True)
def _candidate_dominates_row(
    frontier_rows,
    score_cols,
    idx: int,
    candidate,
    candidate_scores,
    retained_scores,
) -> bool:
    for corner in range(16):
        retained_scores[int(corner)] = score_cols[int(corner), int(idx)]
    return _numba_head_cached_scores_dominate(
        candidate_scores,
        retained_scores,
        candidate,
        _surface_tuple(frontier_rows, int(idx)),
    )


@njit(cache=True, nogil=True)
def _replay(rows, mode: int, block_width: int):
    frontier_rows = np.empty((256, 7), dtype=np.uint64)
    score_cols = np.empty((16, 256), dtype=np.float64)
    count = 0
    seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    candidate_scores = np.empty(16, dtype=np.float64)
    retained_scores = np.empty(16, dtype=np.float64)
    eligible = np.empty(64, dtype=np.uint8)
    for row_idx in range(int(rows.shape[0])):
        candidate = _surface_tuple(rows, int(row_idx))
        if candidate in seen:
            continue
        seen[candidate] = np.uint8(1)
        _numba_head_basis_corner_scores_row(
            _numba_head_surface_basis(candidate, 0, 100), candidate_scores
        )
        if int(mode) == 0:
            dominator = _scalar_dominator(
                frontier_rows, score_cols, int(count), candidate, candidate_scores
            )
        else:
            dominator = _block_dominator(
                frontier_rows,
                score_cols,
                int(count),
                candidate,
                candidate_scores,
                int(block_width),
                eligible,
            )
        if int(dominator) >= 0:
            continue

        write = 0
        for idx in range(int(count)):
            if not _candidate_dominates_row(
                frontier_rows,
                score_cols,
                int(idx),
                candidate,
                candidate_scores,
                retained_scores,
            ):
                if int(write) != int(idx):
                    for col in range(7):
                        frontier_rows[int(write), int(col)] = frontier_rows[int(idx), int(col)]
                    for corner in range(16):
                        score_cols[int(corner), int(write)] = score_cols[int(corner), int(idx)]
                write += 1
        count = int(write)
        frontier_rows, score_cols = _grow(frontier_rows, score_cols, int(count))
        for col in range(7):
            frontier_rows[int(count), int(col)] = candidate[int(col)]
        for corner in range(16):
            score_cols[int(corner), int(count)] = candidate_scores[int(corner)]
        count += 1
    return frontier_rows[: int(count), :].copy()


def _run(bundle, names: list[str], mode: int, width: int) -> tuple[float, str, list[np.ndarray]]:
    outputs = []
    digest = hashlib.sha256()
    started = time.perf_counter()
    for name in names:
        output = _replay(np.ascontiguousarray(bundle[name]), mode, width)
        outputs.append(output)
        digest.update(output.tobytes(order="C"))
    return time.perf_counter() - started, digest.hexdigest(), outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stream_bundle", type=Path)
    parser.add_argument("--widths", type=int, nargs="+", default=(4, 8, 16, 32, 64))
    args = parser.parse_args()
    if any(width < 1 or width > 64 for width in args.widths):
        raise SystemExit("block widths must be in [1, 64]")
    with np.load(args.stream_bundle, allow_pickle=False) as bundle:
        names = sorted(bundle.files, key=lambda name: int(name.rsplit("_", 1)[1]))
        warm = np.ascontiguousarray(bundle[names[-1]][: min(512, len(bundle[names[-1]]))])
        _replay(warm, 0, 1)
        _replay(warm, 1, int(args.widths[0]))
        scalar_time, scalar_digest, scalar_outputs = _run(bundle, names, 0, 1)
        print(f"scalar={scalar_time:.3f}s digest={scalar_digest}")
        for width in args.widths:
            block_time, block_digest, block_outputs = _run(bundle, names, 1, int(width))
            for name, scalar, block in zip(names, scalar_outputs, block_outputs, strict=True):
                if not np.array_equal(scalar, block):
                    raise SystemExit(f"ordered frontier mismatch for {name} at width {width}")
            if block_digest != scalar_digest:
                raise SystemExit(f"digest mismatch at width {width}")
            print(
                f"block{width}={block_time:.3f}s speedup={scalar_time / block_time:.3f}x "
                f"digest={block_digest}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
