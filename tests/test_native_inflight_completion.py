from gear_optimizer.solver.native_inflight_completion import mark_song_completed


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
