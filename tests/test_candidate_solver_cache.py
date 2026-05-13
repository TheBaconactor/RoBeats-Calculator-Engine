from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver import candidate_solver_cache
from gear_optimizer.solver import genetic
from gear_optimizer.solver import native_force_greats


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

    assert shard.put_result8(stats, result8)
    assert not shard.put_result8(stats, result8)

    reloaded = candidate_solver_cache.BaseCandidateCacheShard.load("b" * 32)
    keys, stats_rows, result_rows = reloaded.gpu_rows()
    assert keys.tolist() == [candidate_solver_cache.base_stats_hash_key(stats)]
    assert stats_rows.tolist() == [list(stats)]
    assert result_rows.tolist() == [[0, 2, 3, 4, 5, 6]]

    assert not reloaded.put_result8(stats, (1235, 2, 0, 2, 3, 4, 5, 6))
    with pytest.raises(ValueError, match="value changed"):
        reloaded.put_result8(stats, (1235, 3, 0, 2, 3, 4, 5, 6))


def test_selected_payload_records_base_candidate_cache_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_solver_cache, "solver_candidate_cache_root", lambda: tmp_path)
    shard = candidate_solver_cache.BaseCandidateCacheShard.load("c" * 32)
    combo_index = genetic._base_candidate_combo_index(total_budget=2, max_ft_gems=2, max_ff_gems=2)

    payload = np.zeros((3, 26), dtype=np.int32)
    payload[0, 0] = 2
    payload[1, 2] = 3000
    payload[1, 2 + 1 + 9 : 2 + 1 + 9 + 7] = [3000, 0, 2, 3, 4, 5, 6]
    payload[1, 2 + 1 + 9 + 7 : 2 + 1 + 9 + 7 + 7] = [10, 20, 30, 40, 50, 60, 70]
    payload[2, 2] = 3100
    payload[2, 2 + 1 + 9 : 2 + 1 + 9 + 7] = [3100, 1, 1, 7, 8, 9, 10]
    payload[2, 2 + 1 + 9 + 7 : 2 + 1 + 9 + 7 + 7] = [11, 21, 31, 41, 51, 61, 71]

    writes = genetic._record_base_candidate_cache_rows(
        cache=shard,
        selected_payload=payload,
        combo_index=combo_index,
    )

    assert writes == 2
    reloaded = candidate_solver_cache.BaseCandidateCacheShard.load("c" * 32)
    _keys, stats_rows, result_rows = reloaded.gpu_rows()
    assert stats_rows.tolist() == [[10, 20, 30, 40, 50, 60, 70], [11, 21, 31, 41, 51, 61, 71]]
    assert result_rows.tolist() == [
        [0, combo_index[(0, 2)], 3, 4, 5, 6],
        [0, combo_index[(1, 1)], 7, 8, 9, 10],
    ]


def test_native_fg_solver_reuses_global_candidate_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_solver_cache, "solver_candidate_cache_root", lambda: tmp_path)
    monkeypatch.setattr(native_force_greats, "_section_summary", lambda *_args, **_kwargs: (1, 10))
    monkeypatch.setattr(native_force_greats, "_materialize_best", lambda best, **_kwargs: _result(best["final_score"]))
    monkeypatch.setattr(native_force_greats, "create_scorer_from_calc_song", lambda *_args, **_kwargs: object())

    calls = {"n": 0}

    class _Future:
        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

    class _Gpu:
        def submit_solve_force_greats_finder(self, genome_stats, *_args, **_kwargs):
            calls["n"] += 1
            out = []
            for idx in range(int(genome_stats.shape[0])):
                out.append(
                    {
                        "final_score": 2000 + idx,
                        "base_score": 1000,
                        "score_penalty": 0,
                        "fill_penalty": 0,
                        "cfg_idx": 0,
                        "FT": 1,
                        "FF": 2,
                        "gem_counts": {},
                        "cfg_counts": [0],
                    }
                )
            return SimpleNamespace(future=_Future(out))

    calc_song = {
        "metadata": {
            "Song Name": "Cache Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 1.0,
        },
        "song_data": {"timestamps": np.asarray([0.0, 1.0], dtype=np.float32)},
    }
    ref_arrays = {
        "Perfect Points": np.arange(161, dtype=np.float32),
        "Combo Multiplier": np.arange(161, dtype=np.float32),
        "Fever Multiplier": np.arange(161, dtype=np.float32),
        "Fever Time": np.arange(161, dtype=np.float32),
        "Fever Fill Rate": np.arange(161, dtype=np.float32),
    }
    base_stats = {
        "Perfect Points": 1,
        "Combo Multiplier": 2,
        "Fever Multiplier": 3,
        "Rush": 4,
        "Flow": 5,
        "Fever Time": 6,
        "Fever Fill Rate": 7,
    }

    first, first_stats = native_force_greats.solve_native_force_greats_gpu_batch(
        base_stats_list=[base_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_colors=["Rush"],
        center_fts=[3],
        center_ffs=[4],
        search_radius=5,
        gpu_client=_Gpu(),
    )
    assert calls["n"] == 1
    assert first[0]["final_score"] == 2000
    assert first_stats["candidate_cache_hits"] == 0
    assert first_stats["candidate_cache_writes"] == 1

    second, second_stats = native_force_greats.solve_native_force_greats_gpu_batch(
        base_stats_list=[base_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_colors=["Rush"],
        center_fts=[3],
        center_ffs=[4],
        search_radius=5,
        gpu_client=_Gpu(),
    )
    assert calls["n"] == 1
    assert second[0]["final_score"] == 2000
    assert second_stats["candidate_cache_hits"] == 1
    assert second_stats["candidate_cache_misses"] == 0
