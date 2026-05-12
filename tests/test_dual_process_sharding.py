from __future__ import annotations

import os

from gear_optimizer.legacy.dual_process_inflight import _configure_worker_vulkan_device
from gear_optimizer.legacy.dual_process_inflight import recommend_dual_process_inflight_thread_overrides
from gear_optimizer.legacy.dual_process_inflight import shard_inflight_tasks


def _shard_idx(shards: list[list[tuple]], task: tuple) -> int:
    for idx, shard in enumerate(shards):
        if task in shard:
            return int(idx)
    raise AssertionError("task not present in any shard")


def test_shard_inflight_tasks_is_deterministic_and_no_duplicates() -> None:
    tasks = [
        ("fp1", "SongA", "Hard"),
        ("fp2", "SongA", "Hard"),  # repeat stays with fp1
        ("fp3", "SongB", "Hard"),
        ("fp4", "SongB", "Normal"),  # same song, different diff can shard differently
        ("fp5", "SongC", "Hard"),
    ]

    shards = shard_inflight_tasks(tasks, instances=2)
    flattened = [t for shard in shards for t in shard]
    assert len(flattened) == len(tasks)
    assert set(flattened) == set(tasks)

    # Same (song,diff) always shards together.
    assert _shard_idx(shards, tasks[0]) == _shard_idx(shards, tasks[1])

    # Deterministic mapping.
    shards2 = shard_inflight_tasks(tasks, instances=2)
    assert [_shard_idx(shards, t) for t in tasks] == [_shard_idx(shards2, t) for t in tasks]

    # Trivial case.
    shards1 = shard_inflight_tasks(tasks, instances=1)
    assert shards1 == [tasks]


def test_shard_inflight_tasks_balances_skewed_groups() -> None:
    tasks: list[tuple[str, str, str]] = []
    for i in range(6):
        tasks.append((f"fpa{i}", "SongA", "Hard"))
    for i in range(6):
        tasks.append((f"fpb{i}", "SongB", "Hard"))
    tasks.append(("fpc0", "SongC", "Easy"))
    tasks.append(("fpd0", "SongD", "Easy"))

    shards = shard_inflight_tasks(tasks, instances=2)
    counts = [len(shard) for shard in shards]
    assert sum(counts) == len(tasks)
    assert max(counts) - min(counts) <= 1


def test_shard_inflight_tasks_preserves_per_shard_input_order() -> None:
    tasks = [
        ("fp1", "SongA", "Hard"),
        ("fp2", "SongB", "Hard"),
        ("fp3", "SongA", "Hard"),
        ("fp4", "SongC", "Easy"),
        ("fp5", "SongB", "Hard"),
        ("fp6", "SongD", "Normal"),
    ]
    task_pos = {task: idx for idx, task in enumerate(tasks)}
    shards = shard_inflight_tasks(tasks, instances=2)
    for shard in shards:
        positions = [task_pos[t] for t in shard]
        assert positions == sorted(positions)


def test_configure_worker_vulkan_device_sets_both_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("INFLIGHT_VULKAN_VISIBLE_DEVICES", "0,2")
    monkeypatch.delenv("TAICHI_VULKAN_VISIBLE_DEVICE", raising=False)
    monkeypatch.delenv("TI_VISIBLE_DEVICE", raising=False)

    _configure_worker_vulkan_device(1, instances=2)

    assert os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] == "2"
    assert os.environ["TI_VISIBLE_DEVICE"] == "2"


def test_recommend_dual_process_inflight_thread_overrides_scales_and_caps() -> None:
    cfg_dict = {
        "IterationEngine": {
            "inflight_prepworkers": "8",
            "inflight_decodeworkers": "8",
            "inflight_fgprepworkers": "8",
        }
    }

    out = recommend_dual_process_inflight_thread_overrides(
        cfg_dict,
        inflight_limit=12,
        instances=2,
        logical_cpus=16,
    )

    assert out["INFLIGHT_PREP_WORKERS"] == 2
    assert out["INFLIGHT_DECODE_WORKERS"] == 2
    assert out["INFLIGHT_FG_PREP_WORKERS"] == 2
    assert out["INFLIGHT_DB_PREFETCH_WORKERS"] == 2
    assert out["INFLIGHT_FG_WORKERS"] == 2


def test_recommend_dual_process_inflight_thread_overrides_noop_for_single_instance() -> None:
    out = recommend_dual_process_inflight_thread_overrides(
        {"IterationEngine": {"inflight_prepworkers": "8"}},
        inflight_limit=12,
        instances=1,
        logical_cpus=16,
    )
    assert out == {}
