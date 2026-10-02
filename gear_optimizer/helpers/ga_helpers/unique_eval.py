"""The GA's selected rows with exact duplicates collapsed: one row per loadout (the 6 gear ids and the 3 mini ids as a
set), the candidate pool decode_gpu_native_ga_runs_payload hands the FG stage."""

from __future__ import annotations

from typing import Any

import numpy as np


def select_exact_unique_row_indices(*, genome_ids_mat: Any, scores: Any) -> np.ndarray:
    """The rows to keep: one per canonical genome in first-seen order, each its genome's best-scoring row (the earliest
    among equal scores); a row with fewer than 9 ids has no canonical genome and is kept on its own."""
    ids_mat = np.asarray(genome_ids_mat, dtype=np.int32)
    scores_arr = np.asarray(scores)
    best: dict[tuple, tuple[int, int]] = {}
    for idx in range(int(ids_mat.shape[0])):
        ids = [int(x) for x in list(ids_mat[idx])[:9]]
        score = int(scores_arr[idx]) if idx < int(scores_arr.shape[0]) else 0
        key: tuple = ("__invalid__", idx) if len(ids) < 9 else (*ids[:6], *sorted(ids[6:9]))
        if key not in best or score > best[key][0]:
            best[key] = (score, idx)  # an existing key keeps its first-seen position in the dict
    return np.asarray([idx for _score, idx in best.values()], dtype=np.int32)
