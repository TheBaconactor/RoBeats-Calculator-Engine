from __future__ import annotations

from collections import deque
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_lifecycle import prime_native_inflight_prepared_queue


def _task(name: str) -> tuple:
    return (
        f"{name}.txt",
        name,
        "Hard",
        {"IterationEngine": {}},
        {},
        {},
        [],
        [],
        {},
        {},
        True,
        1,
        None,
        0,
        False,
    )


class _StageProfiler:
    def __init__(self) -> None:
        self.records = []

    def record(self, *args, **kwargs) -> None:
        self.records.append((args, kwargs))


def test_prime_native_inflight_prepared_queue_prepares_initial_backlog():
    pending = deque([_task("A"), _task("B")])
    prepared = deque()
    bound = []
    stage_profiler = _StageProfiler()

    def _prepare(task: tuple):
        return SimpleNamespace(runtime=SimpleNamespace(prep=SimpleNamespace(cpu_prep_s=0.25)), task=task)

    count = prime_native_inflight_prepared_queue(
        prime_target=2,
        pending_tasks=pending,
        prepared=prepared,
        completed_songs=set(),
        next_logical_task=lambda task: (task, None),
        bind_bundle_song=lambda song, parent, repeat_ctx: bound.append((song, parent, repeat_ctx)),
        prepare_song=_prepare,
        post=lambda payload: None,
        advance_bundle=lambda *_args, **_kwargs: False,
        stage_profiler=stage_profiler,
    )

    assert count == 2
    assert not pending
    assert [song.task[1] for song in prepared] == ["A", "B"]
    assert [parent[1] for _song, parent, _repeat_ctx in bound] == ["A", "B"]
    assert [record[1]["song"] for record in stage_profiler.records] == ["A", "B"]


def test_prime_native_inflight_prepared_queue_posts_error_and_marks_task_completed():
    pending = deque([_task("Broken")])
    prepared = deque()
    posts = []
    completed: set[str] = set()

    def _prepare(_task: tuple):
        raise RuntimeError("prep failed")

    count = prime_native_inflight_prepared_queue(
        prime_target=1,
        pending_tasks=pending,
        prepared=prepared,
        completed_songs=completed,
        next_logical_task=lambda task: (task, None),
        bind_bundle_song=lambda *_args: None,
        prepare_song=_prepare,
        post=lambda payload: posts.append(payload),
        advance_bundle=lambda *_args, **_kwargs: False,
        stage_profiler=_StageProfiler(),
    )

    assert count == 0
    assert not pending
    assert not prepared
    assert completed == {"Broken"}
    assert posts[0]["_error"] == "prep failed"
    assert posts[0]["song"] == "Broken"
    assert posts[0]["_error_type"] == "RuntimeError"
