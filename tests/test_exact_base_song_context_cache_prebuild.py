from __future__ import annotations

import concurrent.futures
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def test_prebuild_song_inputs_use_canonical_timeline_and_catalog_free_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer.solver import exact_base_song_context_cache_prebuild as prebuild

    calls: list[str] = []
    calc_song = {
        "metadata": {
            "Total Notes": 1,
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
        }
    }
    timeline = SimpleNamespace(payload=object(), cache_source="disk")
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda *_args, **_kwargs: calc_song,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.timing_envelope.apply_timing_envelope",
        lambda song: calls.append("envelope") or song,
    )

    def _load(song, refs):
        assert calls == ["envelope"]
        assert song is calc_song
        assert refs is ref_arrays
        calls.append("timeline")
        return timeline

    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.api.timeline.load_prebuilt_timeline_frontier_payload",
        _load,
    )
    ref_arrays = {"Perfect Points": np.ones(161, dtype=np.float32)}

    inputs, loaded_timeline = prebuild._load_prebuilt_song_inputs(
        "Data/Easy/Song.txt",
        ref_arrays,
    )

    assert calls == ["envelope", "timeline"]
    assert loaded_timeline is timeline
    assert inputs.calc_song == calc_song
    assert inputs.ref_arrays == ref_arrays
    assert inputs.color_flags["is_p_ft"] == 1
    assert inputs.color_flags["is_s_ff"] == 1
    assert inputs.color_flags["is_p_ov"] == 1
    assert not hasattr(inputs, "gear_pool")
    assert not hasattr(inputs, "mini_pool")


def test_single_missing_context_prebuild_runs_in_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer.solver import exact_base_song_context_cache_prebuild as prebuild

    class _UnexpectedExecutor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("one missing context must not spawn a process pool")

    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", _UnexpectedExecutor)
    monkeypatch.setattr(
        prebuild,
        "build_exact_base_song_context_cache_for_path",
        lambda path, _refs: prebuild.ExactBaseSongContextCacheBuildResult(
            path=path,
            source="built",
            build_ms=12.0,
            cache_file="context.npz",
        ),
    )

    summary, results = prebuild._run_missing_context_prebuild(["song.txt"], {})

    assert summary.total == 1
    assert summary.completed == 1
    assert summary.built == 1
    assert summary.failures == 0
    assert [result.path for result in results] == ["song.txt"]


def test_multi_context_prebuild_uses_drained_bounded_generations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gear_optimizer.solver import exact_base_song_context_cache_prebuild as prebuild

    paths = [f"song-{index}.txt" for index in range(9)]
    submitted: list[str] = []
    executor_workers: list[int] = []

    def _thread_pool_factory(**kwargs):
        executor_workers.append(int(kwargs["max_workers"]))
        assert kwargs["initializer"] is prebuild._init_prebuild_worker
        return concurrent.futures.ThreadPoolExecutor(
            max_workers=int(kwargs["max_workers"])
        )

    def _build(path: str):
        submitted.append(path)
        return prebuild.ExactBaseSongContextCacheBuildResult(
            path=path,
            source="built",
            build_ms=1.0,
            cache_file=f"{path}.npz",
        )

    monkeypatch.setattr(prebuild.concurrent.futures, "ProcessPoolExecutor", _thread_pool_factory)
    monkeypatch.setattr(prebuild, "timeline_prebuild_worker_count", lambda: 2)
    monkeypatch.setattr(prebuild, "_PREBUILD_TASKS_PER_WORKER", 2)
    monkeypatch.setattr(prebuild, "_build_exact_base_song_context_cache_for_path_shared", _build)

    summary, results = prebuild._run_missing_context_prebuild(paths, {})

    assert sorted(submitted) == paths
    assert sorted(result.path for result in results) == paths
    assert summary.total == len(paths)
    assert summary.completed == len(paths)
    assert summary.built == len(paths)
    assert summary.failures == 0
    assert executor_workers == [2, 2, 1]


def test_empty_queue_prebuild_uses_all_corpus_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from gear_optimizer.solver import exact_base_song_context_cache_prebuild as prebuild

    paths = [str(tmp_path / f"song-{index}.txt") for index in range(2249)]
    captured: dict[str, object] = {}

    def _ordered(*, queue_paths, data_root):
        captured["queue_paths"] = list(queue_paths)
        captured["data_root"] = data_root
        return paths

    class _Plan:
        total_paths = len(paths)
        hit_paths = tuple(paths)
        missing_paths = ()
        validated_entry_count = 0

        @property
        def hit_count(self) -> int:
            return len(self.hit_paths)

    monkeypatch.setattr(prebuild, "ordered_frontier_cache_song_paths", _ordered)
    monkeypatch.setattr(prebuild, "_build_manifest_plan", lambda *_args, **_kwargs: _Plan())

    summary = prebuild.run_exact_base_song_context_cache_prebuild(
        cfg=object(),
        song_queue=[],
        ref_arrays={},
        data_root=tmp_path,
    )

    assert captured == {"queue_paths": [], "data_root": tmp_path}
    assert summary.total == 2249
    assert summary.completed == 2249
    assert summary.disk == 2249


def test_strict_timeline_loader_rejects_startup_cache_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError
    from gear_optimizer.solver.taichi_gem.api import timeline

    monkeypatch.setattr(timeline, "_timeline_calc_song_is_zero_ms", lambda _song: False)
    monkeypatch.setattr(
        timeline,
        "_timeline_payload_lookup_context",
        lambda *_args, **_kwargs: {
            "song_key": ("song",),
            "ref_ft": np.zeros(1, dtype=np.float32),
            "ref_ff": np.zeros(1, dtype=np.float32),
            "song_profile_key": "song",
            "total_notes": 1,
            "long_notes": 0,
        },
    )
    monkeypatch.setattr(timeline, "_frontier_payload_cache_key", lambda *_args: ("cache",))
    monkeypatch.setattr(
        timeline,
        "_get_cached_frontier_payload_with_source",
        lambda *_args, **_kwargs: (None, "missing"),
    )
    expected_path = tmp_path / "missing.npz"
    monkeypatch.setattr(timeline, "_frontier_disk_cache_path", lambda _key: expected_path)

    with pytest.raises(MissingFrontierCacheError, match=str(expected_path).replace("\\", "\\\\")):
        timeline.load_prebuilt_timeline_frontier_payload({}, {})
