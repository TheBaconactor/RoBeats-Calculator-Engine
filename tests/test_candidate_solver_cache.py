from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver import candidate_solver_cache


def _result(score: int = 1234) -> dict:
    return {
        "base_score": 1000,
        "final_score": int(score),
        "score_penalty": 3,
        "fill_penalty": 4,
        "num_non_fever_sections": 1,
        "config_counts": [2],
        "fp_targets": [1],
        "non_fever_base": 10,
        "gem_counts": {
            "Perfect Points": 5,
            "Combo Multiplier": 6,
            "Fever Multiplier": 7,
            "Element": 8,
        },
        "FT": 9,
        "FF": 10,
    }


def test_fg_candidate_cache_round_trips_compact_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_solver_cache, "solver_candidate_cache_root", lambda: tmp_path)
    shard = candidate_solver_cache.FgCandidateCacheShard.load("a" * 32)
    stats = (1, 2, 3, 4, 5, 6, 7)

    assert shard.put(stats, _result())
    assert not shard.put(stats, _result())

    reloaded = candidate_solver_cache.FgCandidateCacheShard.load("a" * 32)
    got = reloaded.get(stats)
    assert got is not None
    assert got["final_score"] == 1234
    assert got["config_counts"] == [2]
    assert got["fp_targets"] == [1]

    with pytest.raises(ValueError, match="value changed"):
        reloaded.put(stats, _result(1235))


def test_base_candidate_cache_round_trips_compact_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_solver_cache, "solver_candidate_cache_root", lambda: tmp_path)
    shard = candidate_solver_cache.BaseCandidateCacheShard.load("b" * 32)
    stats = (1, 2, 3, 4, 5, 6, 7)
    result8 = (1234, 2, 0, 2, 3, 4, 5, 6)

    stats_rows = np.asarray([stats], dtype=np.int32)
    result_rows = np.asarray([result8], dtype=np.int32)

    assert shard.put_result8_rows(stats_rows, result_rows) == 1
    assert shard.put_result8_rows(stats_rows, result_rows) == 0

    reloaded = candidate_solver_cache.BaseCandidateCacheShard.load("b" * 32)
    keys, stats_rows, result_rows = reloaded.gpu_rows_for_stats(np.asarray([stats], dtype=np.int32))
    assert keys.tolist() == [candidate_solver_cache.base_stats_hash_key(stats)]
    assert stats_rows.tolist() == [list(stats)]
    assert result_rows.tolist() == [[1234, 2, 3, 4, 5, 6]]

    with pytest.raises(ValueError, match="value changed"):
        reloaded.put_result8_rows(
            np.asarray([stats], dtype=np.int32),
            np.asarray([(1235, 2, 0, 2, 3, 4, 5, 6)], dtype=np.int32),
        )


def test_base_candidate_cache_records_gpu_delta_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_solver_cache, "solver_candidate_cache_root", lambda: tmp_path)
    shard = candidate_solver_cache.BaseCandidateCacheShard.load("c" * 32)

    stats_rows = np.asarray(
        [[10, 20, 30, 40, 50, 60, 70], [11, 21, 31, 41, 51, 61, 71]],
        dtype=np.int32,
    )
    result8_rows = np.asarray(
        [[3000, 0, 0, 2, 3, 4, 5, 6], [3100, 1, 1, 1, 7, 8, 9, 10]],
        dtype=np.int32,
    )

    writes = shard.put_result8_rows(stats_rows, result8_rows)

    assert writes == 2
    reloaded = candidate_solver_cache.BaseCandidateCacheShard.load("c" * 32)
    _keys, stats_rows, result_rows = reloaded.gpu_rows_for_stats(stats_rows)
    assert stats_rows.tolist() == [[10, 20, 30, 40, 50, 60, 70], [11, 21, 31, 41, 51, 61, 71]]
    assert result_rows.tolist() == [[3000, 0, 3, 4, 5, 6], [3100, 1, 7, 8, 9, 10]]

