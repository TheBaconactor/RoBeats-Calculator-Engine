"""The GA's selected rows with exact duplicates collapsed: one row per loadout (the 6 gear ids and the 3 mini ids as a
set), the candidate pool decode_gpu_native_ga_runs_payload hands the FG stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ExactUniqueEvalStats:
    seen: int
    unique: int
    duplicate_hits: int
    replacements: int
    skipped_non_exact: int
    invalid_keys: int


def select_exact_unique_row_indices(
    *,
    genome_ids_mat: Any,
    scores: Any,
    exact: bool = True,
) -> tuple[np.ndarray, ExactUniqueEvalStats]:
    """The rows to keep: one per canonical genome in first-seen order, each its genome's best-scoring row (the earliest
    among equal scores). Only exact scores may be reused, so `exact=False` keeps no row; a row with fewer than 9 ids
    has no canonical genome and is kept on its own."""
    ids_mat = np.asarray(genome_ids_mat, dtype=np.int32)
    scores_arr = np.asarray(scores)
    rows = int(ids_mat.shape[0])
    best: dict[tuple, tuple[int, int]] = {}
    duplicate_hits = replacements = invalid_keys = 0
    for idx in range(rows if exact else 0):
        ids = [int(x) for x in list(ids_mat[idx])[:9]]
        score = int(scores_arr[idx]) if idx < int(scores_arr.shape[0]) else 0
        if len(ids) < 9:
            key: tuple = ("__invalid__", invalid_keys)
            invalid_keys += 1
        else:
            key = (*ids[:6], *sorted(ids[6:9]))
        if key not in best:
            best[key] = (score, idx)
            continue
        duplicate_hits += 1
        if score > best[key][0]:
            best[key] = (score, idx)  # the genome keeps its first-seen position
            replacements += 1
    stats = ExactUniqueEvalStats(
        seen=rows,
        unique=len(best),
        duplicate_hits=duplicate_hits,
        replacements=replacements,
        skipped_non_exact=0 if exact else rows,
        invalid_keys=invalid_keys,
    )
    return np.asarray([idx for _score, idx in best.values()], dtype=np.int32), stats
