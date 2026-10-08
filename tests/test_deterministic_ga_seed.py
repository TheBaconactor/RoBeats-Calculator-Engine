import zlib

import pytest

from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE
from gear_optimizer.settings import RunSettings


def _expected_seed(*, base: int, song_name: str, mode: str, repeat_index: int) -> int:
    base_u32 = int(base) & 0xFFFFFFFF
    task_crc = int(zlib.crc32(f"{song_name}\0{mode}".encode("utf-8", errors="replace")) & 0xFFFFFFFF)
    idx = int(repeat_index) & 0xFFFFFFFF
    return int((base_u32 + task_crc + (idx * 0x9E3779B1)) & 0xFFFFFFFF)


def _chart(tmp_path, name: str, song_name: str, header: str = "") -> str:
    path = tmp_path / name
    path.write_text(f"Song Name\t{song_name}\n{header}Song Data\n", encoding="utf-8")
    return str(path)


def test_prepare_tasks_uses_deterministic_ga_seed_when_env_set(monkeypatch, tmp_path):
    # Import inside the test so monkeypatch env applies before execution.
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")

    run = RunSettings(song_repeats=2, search_depth=1)

    # Charts without a Timing Mode header are solved in both modes.
    a, b = "Fake Song A (Hard) by Tester", "Fake Song B (Hard) by Tester"
    song_queue = [(_chart(tmp_path, "a.txt", a), a, "hard"), (_chart(tmp_path, "b.txt", b), b, "hard")]

    tasks = GearOptimizerApp()._prepare_tasks(song_queue, run, None, None, None)

    # 2 songs x 2 modes x 2 runs, each with its own seed; Precise is solved first.
    assert [(t.song_name, t.mode) for t in tasks[:4]] == [(a, PRECISE)] * 2 + [(a, NON_PRECISE)] * 2
    got = {(t.song_name, t.mode, t.repeat_index): t.ga_seed for t in tasks}
    assert got == {
        (song, mode, run_index): _expected_seed(base=1337, song_name=song, mode=mode, repeat_index=run_index)
        for song in (a, b)
        for mode in (PRECISE, NON_PRECISE)
        for run_index in (1, 2)
    }
    assert len(set(got.values())) == 8


def test_a_mode_is_seeded_the_same_alone_or_beside_the_other(monkeypatch, tmp_path):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "1337")
    run = RunSettings(song_repeats=1, search_depth=1)
    song = "Fake Song A (Hard) by Tester"

    both = GearOptimizerApp()._prepare_tasks([(_chart(tmp_path, "a.txt", song), song, "hard")], run, None, None, None)
    alone = GearOptimizerApp()._prepare_tasks(
        [(_chart(tmp_path, "p.txt", song, "Timing Mode\tnon-precise\n"), song, "hard")], run, None, None, None
    )

    assert [(t.mode, t.ga_seed) for t in alone] == [(t.mode, t.ga_seed) for t in both if t.mode == NON_PRECISE]


def test_prepare_tasks_rejects_invalid_debug_ga_seed(monkeypatch, tmp_path):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("GA_SEED", "not-an-int")

    run = RunSettings(song_repeats=1, search_depth=1)

    with pytest.raises(ValueError, match="GA_SEED must be an integer"):
        GearOptimizerApp()._prepare_tasks(
            [(_chart(tmp_path, "a.txt", "Fake Song A (Hard) by Tester"), "Fake Song A (Hard) by Tester", "hard")],
            run,
            None,
            None,
            None,
        )
