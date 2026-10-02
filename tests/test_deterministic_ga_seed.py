import os
import zlib

from gear_optimizer.settings import RunSettings


def _expected_seed(*, base: int, song_name: str, repeat_index: int) -> int:
    base_u32 = int(base) & 0xFFFFFFFF
    name_crc = int(zlib.crc32(str(song_name).encode("utf-8", errors="replace")) & 0xFFFFFFFF)
    idx = int(repeat_index) & 0xFFFFFFFF
    seed = (base_u32 + name_crc + (idx * 0x9E3779B1)) & 0xFFFFFFFF
    return int(seed)


def test_prepare_tasks_uses_deterministic_ga_seed_when_env_set(monkeypatch):
    # Import inside the test so monkeypatch env applies before execution.
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")

    run = RunSettings(song_repeats=2, search_depth=1)

    # Minimal song queue: (fp, found_song_name, task_diff)
    song_queue = [
        ("Data/Hard/FakeSongA.txt", "Fake Song A (Hard) by Tester", "hard"),
        ("Data/Hard/FakeSongB.txt", "Fake Song B (Hard) by Tester", "hard"),
    ]

    app = GearOptimizerApp()
    tasks = app._prepare_tasks(
        song_queue,
        run,
        None,
        None,
        None,
    )

    # With SongRepeats=2 and 2 songs, expect 4 tasks, each with its own seed.
    assert len(tasks) == 4
    got = {(t.song_name, t.repeat_index): t.ga_seed for t in tasks}

    assert got[("Fake Song A (Hard) by Tester", 1)] == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=1)
    assert got[("Fake Song A (Hard) by Tester", 2)] == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=2)
    assert got[("Fake Song B (Hard) by Tester", 1)] == _expected_seed(base=1337, song_name="Fake Song B (Hard) by Tester", repeat_index=1)
    assert got[("Fake Song B (Hard) by Tester", 2)] == _expected_seed(base=1337, song_name="Fake Song B (Hard) by Tester", repeat_index=2)

    # Sanity: uniqueness across the queue.
    assert len(set(got.values())) == 4


def test_prepare_tasks_seeds_a_single_run_deterministically_when_env_set(monkeypatch):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")

    run = RunSettings(song_repeats=1, search_depth=1)

    song_queue = [
        ("Data/Hard/FakeSongA.txt", "Fake Song A (Hard) by Tester", "hard"),
    ]

    app = GearOptimizerApp()
    tasks = app._prepare_tasks(
        song_queue,
        run,
        None,
        None,
        None,
    )

    assert len(tasks) == 1
    t0 = tasks[0]
    assert (t0.repeat_total, t0.repeat_index) == (1, 1)
    assert t0.ga_seed == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=1)


def test_prepare_tasks_rejects_invalid_debug_ga_seed(monkeypatch):
    import pytest

    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "not-an-int")

    run = RunSettings(song_repeats=1, search_depth=1)

    app = GearOptimizerApp()
    with pytest.raises(ValueError, match="GA_SEED must be an integer"):
        app._prepare_tasks(
            [("Data/Hard/FakeSongA.txt", "Fake Song A (Hard) by Tester", "hard")],
            run,
            None,
            None,
            None,
        )
