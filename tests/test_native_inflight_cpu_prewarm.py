from __future__ import annotations

import concurrent.futures

from gear_optimizer.solver.native_inflight_lifecycle import CpuPrewarmQueue
from gear_optimizer.solver.native_inflight_config import make_native_song


def test_cpu_prewarm_queue_submits_once_and_finishes_success():
    seen: list[str] = []
    queue = CpuPrewarmQueue(
        max_workers=1,
        lookahead=2,
        prewarm_fn=lambda song: seen.append(song.config.task_key),
    )
    try:
        song = make_native_song(task_key="song-a", song_name="Song A")
        registered = []

        assert queue.submit(song, register_future=registered.append) is True
        assert queue.submit(song, register_future=registered.append) is False
        assert len(registered) == 1
        assert song.runtime.prep.cpu_prewarm_future is registered[0]

        concurrent.futures.wait(registered, timeout=2)
        completions = queue.finish_completed()

        assert seen == ["song-a"]
        assert len(completions) == 1
        assert completions[0].song is song
        assert completions[0].label == "song-a"
        assert completions[0].error is None
        assert song.runtime.prep.cpu_prewarm_future is None
        assert len(queue) == 0
    finally:
        queue.shutdown(wait=True, cancel_futures=True)


def test_cpu_prewarm_queue_failure_clears_future_and_allows_retry():
    def _fail(_song):
        raise RuntimeError("prewarm boom")

    queue = CpuPrewarmQueue(
        max_workers=1,
        lookahead=1,
        prewarm_fn=_fail,
    )
    try:
        song = make_native_song(task_key="song-b", song_name="Song B")
        registered = []

        assert queue.submit(song, register_future=registered.append) is True
        concurrent.futures.wait(registered, timeout=2)
        completions = queue.finish_completed()

        assert len(completions) == 1
        assert completions[0].label == "song-b"
        assert isinstance(completions[0].error, RuntimeError)
        assert "song-b" not in queue.submitted
        assert song.runtime.prep.cpu_prewarm_future is None

        queue.prewarm_fn = lambda _song: None
        assert queue.submit(song, register_future=lambda _future: None) is True
    finally:
        queue.shutdown(wait=True, cancel_futures=True)


def test_cpu_prewarm_queue_disabled_without_executor_or_lookahead():
    song = make_native_song(task_key="song-c", song_name="Song C")
    no_executor = CpuPrewarmQueue(max_workers=0, lookahead=1, prewarm_fn=lambda _song: None)
    assert no_executor.submit(song, register_future=lambda _future: None) is False

    no_lookahead = CpuPrewarmQueue(max_workers=1, lookahead=0, prewarm_fn=lambda _song: None)
    try:
        assert no_lookahead.submit(song, register_future=lambda _future: None) is False
    finally:
        no_lookahead.shutdown(wait=True, cancel_futures=True)


def test_cpu_prewarm_queue_submit_prepared_backlog_respects_lookahead_and_extra_submit():
    queue = CpuPrewarmQueue(max_workers=0, lookahead=2, prewarm_fn=lambda _song: None)
    songs = [
        make_native_song(task_key="song-a", song_name="Song A"),
        make_native_song(task_key="song-b", song_name="Song B"),
        make_native_song(task_key="song-c", song_name="Song C"),
    ]
    extra_seen = []

    started = queue.submit_prepared_backlog(
        songs,
        register_future=lambda _future: None,
        extra_submit=lambda song: not extra_seen.append(song.config.task_key),
    )

    assert started == 2
    assert extra_seen == ["song-a", "song-b"]


def test_cpu_prewarm_queue_submit_prepared_backlog_disabled_at_zero_lookahead():
    queue = CpuPrewarmQueue(max_workers=0, lookahead=0, prewarm_fn=lambda _song: None)
    song = make_native_song(task_key="song-a", song_name="Song A")
    extra_seen = []

    started = queue.submit_prepared_backlog(
        [song],
        register_future=lambda _future: None,
        extra_submit=lambda queued: not extra_seen.append(queued.config.task_key),
    )

    assert started == 0
    assert extra_seen == []
