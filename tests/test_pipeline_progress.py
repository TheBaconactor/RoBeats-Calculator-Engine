from gear_optimizer.pipeline.progress import (
    ProgressTracker,
    evaluate_fg_progress_record_update,
    mark_song_completed,
    task_error_payload,
)
from gear_optimizer.gamedata import STATS
from gear_optimizer.pipeline.results import SolvedFg
from tests.native_song_factory import make_native_song


def _fg(*, score: int, paired: int) -> SolvedFg:
    return SolvedFg(element="Rush", gems=(0,) * 6, stats=(0,) * len(STATS), surface=(0,) * 11, trace={},
                    score=score, paired=paired)


def test_progress_tracker_emit_progress_forwards_payload():
    tracker = ProgressTracker()
    seen = {}

    def _capture_progress(**kwargs):
        seen.update(kwargs)

    tracker.emit_progress(
        _capture_progress,
        completed_delta=2,
        failed_delta=1,
        record_info={"song": "demo"},
    )

    assert seen == {
        "completed_delta": 2,
        "failed_delta": 1,
        "record_info": {"song": "demo"},
    }


def test_progress_tracker_emit_error_item_progress_forwards_failure():
    tracker = ProgressTracker()
    events = []

    emitted = tracker.emit_error_item_progress(
        lambda **kwargs: events.append(kwargs),
        task_error_payload(song_name="", queue_key="song-a", exc=RuntimeError("boom"), trace=""),
    )

    assert emitted is True
    assert events == [
        {
            "completed_delta": 1,
            "failed_delta": 1,
            "record_info": {"song": "song-a", "status": "FAILED"},
        }
    ]


def test_progress_tracker_emit_error_item_progress_dedupes_queue_key():
    tracker = ProgressTracker()
    events = []

    def emit(**kwargs):
        events.append(kwargs)

    def failure(song: str, key: str) -> dict:
        return task_error_payload(song_name=song, queue_key=key, exc=RuntimeError("boom"), trace="")

    assert tracker.emit_error_item_progress(emit, failure("Song A", "song-a")) is True
    assert tracker.emit_error_item_progress(emit, failure("Song A", "song-a")) is False
    assert tracker.emit_error_item_progress(emit, failure("Song B", "song-b")) is True

    assert events == [
        {
            "completed_delta": 1,
            "failed_delta": 1,
            "record_info": {"song": "Song A", "status": "FAILED"},
        },
        {
            "completed_delta": 1,
            "failed_delta": 1,
            "record_info": {"song": "Song B", "status": "FAILED"},
        },
    ]


def test_progress_tracker_emit_error_item_progress_ignores_a_failure_without_a_message():
    tracker = ProgressTracker()
    events = []
    silent = task_error_payload(song_name="Song A", queue_key="song-a", exc=RuntimeError(), trace="")

    assert tracker.emit_error_item_progress(lambda **kwargs: events.append(kwargs), silent) is False
    assert events == []


def test_progress_tracker_emit_done_song_progress_defaults_done_record():
    tracker = ProgressTracker()
    events = []
    song = make_native_song(task_key="done-song", song_name="Done Song")

    tracker.emit_done_song_progress(lambda **kwargs: events.append(kwargs), song)

    assert events == [
        {
            "completed_delta": 1,
            "failed_delta": 0,
            "record_info": {"song": "done-song", "status": "DONE"},
        }
    ]


def test_progress_tracker_done_record_info_preserves_existing_fields():
    song = make_native_song(task_key="done-song", song_name="Done Song")
    song.runtime.db.record_info = {"song": "custom", "score": 123}

    assert ProgressTracker.done_record_info_for_song(song) == {
        "song": "custom",
        "score": 123,
        "status": "DONE",
    }


def test_progress_tracker_seed_valid_baseline_ignores_invalid_baseline():
    tracker = ProgressTracker()

    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=False)
    assert tracker.snapshot("song-a") == (0, 0, False)

    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)
    assert tracker.snapshot("song-a") == (1000, 900, True)


def test_evaluate_fg_progress_record_update_uses_tracker_snapshot_and_updates_fg_best():
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)
    song = make_native_song(
        db_key="song-a",
        task_key="Song A (Hard)",
        db_best_score=1,
        db_best_fg_score=1,
        db_baseline_valid=False,
    )

    record_info = evaluate_fg_progress_record_update(song, 1000, [_fg(score=1050, paired=1000)], tracker)

    assert isinstance(record_info, dict)
    assert record_info["is_fg_better"] is True
    assert record_info["song"] == "Song A (Hard)"
    assert tracker.snapshot("song-a") == (1000, 1050, True)


def test_evaluate_fg_progress_record_update_updates_base_session_best():
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)
    song = make_native_song(
        db_key="song-a",
        task_key="Song A (Hard)",
        db_best_score=1,
        db_best_fg_score=1,
        db_baseline_valid=False,
    )

    record_info = evaluate_fg_progress_record_update(song, 1100, [], tracker)

    assert isinstance(record_info, dict)
    assert record_info["is_better"] is True
    assert record_info["song"] == "Song A (Hard)"
    assert tracker.snapshot("song-a") == (1100, 900, True)


class _MemoryResumeTracker:
    def __init__(self):
        self.completed = []

    def mark_completed(self, *, song_path=None, song_name=None):
        self.completed.append((song_path, song_name))


def test_mark_song_completed_updates_the_set_and_the_resume_tracker():
    completed = set()
    memory = _MemoryResumeTracker()

    mark_song_completed(
        completed_songs=completed,
        task_key="song-a",
        song_name="Song A",
        song_path="C:/songs/song-a.txt",
        memory_resume_tracker=memory,
    )

    assert completed == {"song-a"}
    assert memory.completed == [("C:/songs/song-a.txt", "Song A")]


def test_mark_song_completed_without_a_song_path():
    completed = set()
    memory = _MemoryResumeTracker()

    mark_song_completed(
        completed_songs=completed,
        task_key="song-b",
        song_name="Song B",
        memory_resume_tracker=memory,
    )

    assert completed == {"song-b"}
    assert memory.completed == [(None, "Song B")]
