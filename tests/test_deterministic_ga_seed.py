import configparser
import os
import zlib


def _expected_seed(*, base: int, song_name: str, repeat_index: int) -> int:
    base_u32 = int(base) & 0xFFFFFFFF
    name_crc = int(zlib.crc32(str(song_name).encode("utf-8", errors="replace")) & 0xFFFFFFFF)
    idx = int(repeat_index) & 0xFFFFFFFF
    seed = (base_u32 + name_crc + (idx * 0x9E3779B1)) & 0xFFFFFFFF
    return int(seed or 1)


def test_prepare_tasks_uses_deterministic_ga_seed_when_env_set(monkeypatch):
    # Import inside the test so monkeypatch env applies before execution.
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"SongRepeats": "2"}

    # Minimal song queue: (fp, found_song_name, task_diff)
    song_queue = [
        ("Data/Hard/FakeSongA.txt", "Fake Song A (Hard) by Tester", "hard"),
        ("Data/Hard/FakeSongB.txt", "Fake Song B (Hard) by Tester", "hard"),
    ]

    app = GearOptimizerApp()
    tasks = app._prepare_tasks(
        song_queue,
        cfg,
        None,
        None,
        None,
        None,
        None,
        None,
        1,
        None,
        False,
    )

    # With SongRepeats=2 and 2 songs, expect 4 tasks, all with repeat_ctx.
    assert len(tasks) == 4
    got = {}
    for t in tasks:
        repeat_ctx = t[14]
        song_name = t[1]
        idx = int(repeat_ctx["repeat_index"])
        ga_seed = int(repeat_ctx["ga_seed"])
        got[(song_name, idx)] = ga_seed

    assert got[("Fake Song A (Hard) by Tester", 1)] == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=1)
    assert got[("Fake Song A (Hard) by Tester", 2)] == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=2)
    assert got[("Fake Song B (Hard) by Tester", 1)] == _expected_seed(base=1337, song_name="Fake Song B (Hard) by Tester", repeat_index=1)
    assert got[("Fake Song B (Hard) by Tester", 2)] == _expected_seed(base=1337, song_name="Fake Song B (Hard) by Tester", repeat_index=2)

    # Sanity: uniqueness across the queue.
    assert len(set(got.values())) == 4


def test_prepare_tasks_injects_repeat_ctx_when_songrepeats_1_and_env_set(monkeypatch):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"SongRepeats": "1"}

    song_queue = [
        ("Data/Hard/FakeSongA.txt", "Fake Song A (Hard) by Tester", "hard"),
    ]

    app = GearOptimizerApp()
    tasks = app._prepare_tasks(
        song_queue,
        cfg,
        None,
        None,
        None,
        None,
        None,
        None,
        1,
        None,
        False,
    )

    assert len(tasks) == 1
    t0 = tasks[0]
    assert len(t0) >= 15
    repeat_ctx = t0[14]
    assert isinstance(repeat_ctx, dict)
    assert int(repeat_ctx["repeat_total"]) == 1
    assert int(repeat_ctx["repeat_index"]) == 1
    assert int(repeat_ctx["ga_seed"]) == _expected_seed(base=1337, song_name="Fake Song A (Hard) by Tester", repeat_index=1)
