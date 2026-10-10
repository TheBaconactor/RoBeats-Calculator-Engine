import zlib

import pytest

from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE
from gear_optimizer.domain.jobs import SharedRunContext
from gear_optimizer.pipeline import queue as queue_module
from gear_optimizer.pipeline.queue import build_queue
from gear_optimizer.settings import RunSettings
from gear_optimizer.store import db, schema
from tests.store_support import result

CONTEXT = SharedRunContext(multi_start=1, curves=None, gears={}, minis={}, ga_depth=1)


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path / "Data"))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    monkeypatch.delenv("GA_SEED", raising=False)
    schema.ensure(tmp_path / "results.db")
    return tmp_path


def _chart(data, difficulty, name, *, primary="Flow", secondary="Beat", mode=""):
    folder = data / "Data" / difficulty
    folder.mkdir(parents=True, exist_ok=True)
    header = f"Song Name\t{name}\nPrimary Color\t{primary}\nSecondary Color\t{secondary}\n"
    if mode:
        header += f"Timing Mode\t{mode}\n"
    (folder / f"{name}.txt").write_text(header + "Song Data\n", encoding="utf-8")


def _stored(data, song, mode, when):
    conn = schema.connect(data / "results.db", write=True)
    try:
        db.store_results(conn, mode, song, "T5", [result("h1", 100, song=song, mode=mode)], now=when)
    finally:
        conn.close()


def _solves(tasks):
    return [(task.song_name, task.mode) for task in tasks]


def test_unstored_solves_come_first_by_chart_then_the_least_recently_solved(data):
    for name in ("C", "A", "B", "D"):
        _chart(data, "Hard", name)
    _stored(data, "A", PRECISE, 300.0)
    _stored(data, "A", NON_PRECISE, 100.0)
    _stored(data, "B", PRECISE, 200.0)
    tasks = build_queue(RunSettings(), CONTEXT)
    assert _solves(tasks) == [
        ("B", NON_PRECISE), ("C", PRECISE), ("C", NON_PRECISE), ("D", PRECISE), ("D", NON_PRECISE),
        ("A", NON_PRECISE), ("B", PRECISE), ("A", PRECISE),
    ]


def test_the_queue_limit_counts_solve_runs_and_a_relaunched_pass_skips_what_it_stored(data):
    for name in ("A", "B"):
        _chart(data, "Hard", name)
    _stored(data, "A", PRECISE, 100.0)
    assert _solves(build_queue(RunSettings(song_queue_limit=3), CONTEXT)) == [
        ("A", NON_PRECISE), ("B", PRECISE), ("B", NON_PRECISE)
    ]
    _stored(data, "B", PRECISE, 500.0)
    assert _solves(build_queue(RunSettings(), CONTEXT, solved_before=400.0)) == [
        ("A", NON_PRECISE), ("B", NON_PRECISE), ("A", PRECISE)
    ]


def test_charts_are_filtered_by_difficulty_name_and_colors_and_a_header_mode_is_its_only_solve(data):
    _chart(data, "Hard", "Alpha Song", primary="Rush")
    _chart(data, "Hard", "Beta Song", primary="Flow", secondary="Vibe")
    _chart(data, "Easy", "Alpha Easy", primary="Rush")
    _chart(data, "Normal", "Pinned", mode=NON_PRECISE)
    assert {task.song_name for task in build_queue(RunSettings(difficulty="Hard"), CONTEXT)} == {"Alpha Song", "Beta Song"}
    assert {task.song_name for task in build_queue(RunSettings(song_name="alpha"), CONTEXT)} == {"Alpha Song", "Alpha Easy"}
    assert {task.song_name for task in build_queue(RunSettings(target_primary="rush,beat"), CONTEXT)} == {
        "Alpha Song", "Alpha Easy"
    }
    assert {task.song_name for task in build_queue(RunSettings(target_secondary="Vibe|*"), CONTEXT)} == {
        "Alpha Song", "Beta Song", "Alpha Easy", "Pinned"
    }
    assert _solves(build_queue(RunSettings(song_name="Pinned"), CONTEXT)) == [("Pinned", NON_PRECISE)]


def test_a_chart_without_a_song_name_is_an_error(data):
    folder = data / "Data" / "Hard"
    folder.mkdir(parents=True)
    (folder / "nameless.txt").write_text("Primary Color\tFlow\nSong Data\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no Song Name header"):
        build_queue(RunSettings(), CONTEXT)


def _expected_seed(base, song, mode, run):
    crc = zlib.crc32(f"{song}\0{mode}".encode("utf-8", errors="replace"))
    return ((base & 0xFFFFFFFF) + crc + run * 0x9E3779B1) & 0xFFFFFFFF


def test_every_run_has_its_own_seed_stable_per_song_mode_and_run_with_ga_seed(data, monkeypatch):
    _chart(data, "Hard", "A")
    _chart(data, "Normal", "Pinned", mode=NON_PRECISE)
    monkeypatch.setenv("GA_SEED", "1337")
    tasks = build_queue(RunSettings(song_repeats=2), CONTEXT)
    assert [(t.song_name, t.mode, t.repeat_index, t.ga_seed) for t in tasks] == [
        (song, mode, run, _expected_seed(1337, song, mode, run))
        for song, mode in (("A", PRECISE), ("A", NON_PRECISE), ("Pinned", NON_PRECISE))
        for run in (1, 2)
    ]
    assert [t.label for t in tasks[:2]] == ["A (precise, Run 1/2)", "A (precise, Run 2/2)"]
    monkeypatch.setenv("GA_SEED", "not-an-int")
    with pytest.raises(ValueError, match="GA_SEED must be an integer"):
        build_queue(RunSettings(), CONTEXT)


def test_without_ga_seed_the_seeds_are_random_and_never_repeat_in_a_queue(data, monkeypatch):
    _chart(data, "Hard", "A", mode=PRECISE)
    seeds = iter([7, 7, 0])
    monkeypatch.setattr(queue_module.secrets, "randbits", lambda _bits: next(seeds))
    assert [t.ga_seed for t in build_queue(RunSettings(song_repeats=2), CONTEXT)] == [7, 0]
