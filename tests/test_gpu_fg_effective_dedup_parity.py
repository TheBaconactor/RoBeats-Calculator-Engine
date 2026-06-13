from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.solver.fg_effective_dedup import select_top_base_fg_candidates_reference
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu

_REAL_POOLS = Path("artifacts/profile/_slice1_pools.jsonl")


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _gpu_select(candidates: np.ndarray, gear_name_rank: np.ndarray, mini_sig_id: np.ndarray, *, limit: int) -> set:
    """Run the device select over one run's candidate rows; return selected (score, ids) set.

    candidates: (N, 10) int32 rows of [score, gear_ids(6), mini_ids(3, sorted)].
    """
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        ga_download_fg_selected_payload,
        ga_upload_fg_effective_tables,
    )
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready

    table_slot = 0
    with _GPU_LOCK:
        ensure_ready()
        ga_upload_fg_effective_tables(
            np.asarray(gear_name_rank, dtype=np.int32),
            np.asarray(mini_sig_id, dtype=np.int32),
        )
        packed = np.zeros(
            tuple(int(dim) for dim in gpu_fields.ga_fg_candidates_packed.shape),
            dtype=np.int32,
        )
        per_run_rows = int(packed.shape[2])
        n_runs = 0
        for i in range(int(candidates.shape[0])):
            run_idx, row_idx = divmod(int(i), per_run_rows - 1)
            row_idx += 1  # rows 1..K are candidates; row 0 is the per-run best
            packed[table_slot, run_idx, row_idx, 0] = int(candidates[i, 0])
            packed[table_slot, run_idx, row_idx, 1:10] = candidates[i, 1:10]
            packed[table_slot, run_idx, row_idx, 10] = int(candidates[i, 0])
            n_runs = max(n_runs, run_idx + 1)
        gpu_fields.ga_fg_candidates_packed.from_numpy(packed)
        payload = ga_download_fg_selected_payload(table_slot=table_slot, n_runs=int(n_runs), limit=int(limit))

    selected_count = int(payload[0, 0])
    out = set()
    for row in payload[1 : 1 + selected_count]:
        score = int(row[2])
        ids = tuple(int(v) for v in row[3:12])
        out.add((score, ids))
    return out


def _reference_select(candidates: np.ndarray, gear_name_rank: np.ndarray, mini_sig_id: np.ndarray, *, limit: int) -> set:
    idx = select_top_base_fg_candidates_reference(
        base_scores=candidates[:, 0].astype(np.int64),
        gear_ids=candidates[:, 1:7].astype(np.int64),
        mini_ids=candidates[:, 7:10].astype(np.int64),
        gear_name_rank=np.asarray(gear_name_rank, dtype=np.int64),
        mini_sig_id=np.asarray(mini_sig_id, dtype=np.int64),
        limit=int(limit),
    )
    out = set()
    for i in np.asarray(idx).reshape(-1):
        score = int(candidates[int(i), 0])
        ids = tuple(int(v) for v in candidates[int(i), 1:10])
        out.add((score, ids))
    return out


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_effective_dedup_collapses_equivalent_loadouts_like_reference() -> None:
    # gear ids 1 and 2 share a name rank; mini ids 101 and 102 share a sig.
    gear_name_rank = np.zeros(16, dtype=np.int32)
    for gid in range(1, 13):
        gear_name_rank[gid] = gid
    gear_name_rank[2] = gear_name_rank[1]
    mini_sig_id = np.zeros(112, dtype=np.int32)
    for mid in (101, 102, 103):
        mini_sig_id[mid] = mid
    mini_sig_id[102] = mini_sig_id[101]

    candidates = np.asarray(
        [
            # A and B are raw-id distinct but effective-equivalent: keep max (A).
            [100, 1, 3, 4, 5, 6, 7, 101, 103, 103],
            [90, 2, 3, 4, 5, 6, 7, 102, 103, 103],
            # C is a distinct effective loadout.
            [80, 8, 9, 10, 11, 12, 3, 103, 103, 103],
        ],
        dtype=np.int32,
    )

    expected = _reference_select(candidates, gear_name_rank, mini_sig_id, limit=51)
    got = _gpu_select(candidates, gear_name_rank, mini_sig_id, limit=51)

    assert len(expected) == 2  # the equivalent pair collapsed by the reference
    assert got == expected


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.skipif(not _REAL_POOLS.exists(), reason="no captured real pools on this machine")
def test_gpu_effective_dedup_matches_reference_on_real_pool() -> None:
    line = _REAL_POOLS.read_text(encoding="utf-8").splitlines()[0]
    pool = json.loads(line)
    cands = pool["candidates"]
    candidates = np.asarray(
        [[int(c["score"])] + [int(g) for g in c["gear_ids"]] + sorted(int(m) for m in c["mini_ids"]) for c in cands],
        dtype=np.int32,
    )
    gear_name_rank = np.asarray(pool["gear_name_rank"], dtype=np.int32)
    mini_sig_id = np.asarray(pool["mini_sig_id"], dtype=np.int32)
    limit = int(pool["limit"])

    expected = _reference_select(candidates, gear_name_rank, mini_sig_id, limit=limit)
    got = _gpu_select(candidates, gear_name_rank, mini_sig_id, limit=limit)

    assert got == expected
