from __future__ import annotations

import queue
import threading
from typing import Any

from gear_optimizer.pipeline.skyline_streaming import (
    completion_payload_from_deferred,
    drain_post_queue_for_tests,
    iter_streamed_song_results,
    with_streaming_extras,
)


def test_with_streaming_extras_preserves_task_order() -> None:
    task = ("fp", "song")
    assets = object()

    out = with_streaming_extras(task, assets, defer_post=True)

    assert out[:2] == task
    assert out[2] is assets
    assert out[3] is True


def test_completion_payload_from_deferred_does_not_persist_twice() -> None:
    payload = {
        "song": "Song A",
        "_queue_key": "Song A|Hard",
        "db_payload": {"score": 1},
        "persist_entries": [{"score": 1}],
        "best_data": {"BaseScore": 1},
        "_record": {"is_new_record": True},
        "fg_variants": [{"fg_score": 2}],
    }

    out = completion_payload_from_deferred(payload)

    assert out["song"] == "Song A"
    assert out["_record"] == {"is_new_record": True}
    assert out["best_data"] == {"BaseScore": 1}
    assert out["_deferred_post_dispatched"] is True
    assert "db_payload" not in out
    assert "persist_entries" not in out


def test_streaming_iterator_prefetches_next_before_current_process() -> None:
    b_prefetch_started = threading.Event()
    process_a_entered = threading.Event()
    post_q: queue.Queue[Any] = queue.Queue()
    events: list[str] = []

    def preload(task: tuple[str]) -> dict[str, str]:
        name = task[0]
        events.append(f"preload:{name}")
        if name == "b":
            b_prefetch_started.set()
        return {"asset": name}

    def process(task: tuple[Any, ...]) -> dict[str, Any]:
        name = task[0]
        events.append(f"process:{name}")
        if name == "a":
            process_a_entered.set()
            assert b_prefetch_started.wait(timeout=2.0)
        return {
            "_deferred_post": True,
            "song": name,
            "_queue_key": name,
            "best_data": {"BaseScore": len(name)},
            "_stage_timing": {},
        }

    results = list(
        iter_streamed_song_results(
            [("a",), ("b",)],
            process_fn=process,
            preload_fn=preload,
            post_queue=post_q,
        )
    )

    assert process_a_entered.is_set()
    assert [result["song"] for result in results] == ["a", "b"]
    assert all(result.get("_deferred_post_dispatched") for result in results)
    assert [item["song"] for item in drain_post_queue_for_tests(post_q)] == ["a", "b"]
    assert b_prefetch_started.is_set()


def test_task_execution_streaming_disabled_for_duplicate_inputs(monkeypatch: Any) -> None:
    from gear_optimizer.task_execution import TaskExecutionMixin

    class Dummy(TaskExecutionMixin):
        pass

    monkeypatch.setenv("SKYLINE_STREAMING_PIPELINE", "1")
    runner = Dummy()

    assert runner._streaming_skyline_enabled([("a.osu", "A"), ("b.osu", "B")]) is True
    assert runner._streaming_skyline_enabled([("a.osu", "A"), ("a.osu", "A")]) is False
