from __future__ import annotations

from gear_optimizer.solver.dual_process_inflight import shard_inflight_tasks


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
