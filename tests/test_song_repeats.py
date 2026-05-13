import configparser

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    extract_repeat_context,
    materialize_repeat_task,
    task_queue_label,
)


def _build_cfg(song_repeats: int) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "SongRepeats", str(int(song_repeats)))
    return cfg


def test_prepare_tasks_song_repeats_expands_queue():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(3)

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 3
    assert all(len(t) == 16 for t in tasks)
    assert [task_queue_label(t) for t in tasks] == [
        "Dummy Song (Run 1/3)",
        "Dummy Song (Run 2/3)",
        "Dummy Song (Run 3/3)",
    ]

    seeds = [t[15]["ga_seed"] for t in tasks]
    assert len(seeds) == 3
    assert len(set(seeds)) == 3


def test_prepare_tasks_song_repeats_one_keeps_single_shape():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(1)

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 1
    assert len(tasks[0]) == 15
    assert extract_repeat_context(tasks[0]) is None
    assert task_queue_label(tasks[0]) == "Dummy Song"


def test_prepare_tasks_bundle_song_repeats_keeps_single_queue_item():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(3)
    cfg.set("IterationEngine", "BundleSongRepeats", "true")

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 1
    assert extract_repeat_context(tasks[0]) is None
    assert task_queue_label(tasks[0]) == "Dummy Song"
    bundle = tasks[0][15]
    assert bundle["repeat_bundle"] is True
    assert int(bundle["repeat_total"]) == 3
    runs = bundle["runs"]
    assert [int(run["repeat_index"]) for run in runs] == [1, 2, 3]
    assert [int(run["repeat_total"]) for run in runs] == [3, 3, 3]
    seeds = [int(run["ga_seed"]) for run in runs]
    assert len(seeds) == 3
    assert len(set(seeds)) == 3


def test_prepare_tasks_backend_priority_new_songs_use_song_repeats_by_default(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = type("DummyApi", (), {"backend_mode_enabled": staticmethod(lambda: True)})()
    app._backend_priority_song_names = {"New Song"}
    app._backend_priority_song_repeat_count = 0
    cfg = _build_cfg(25)

    song_queue = [("dummy.txt", "New Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 25
    assert task_queue_label(tasks[-1]) == "New Song (Run 25/25)"


def test_prepare_tasks_backend_priority_new_songs_honors_repeat_override(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = type("DummyApi", (), {"backend_mode_enabled": staticmethod(lambda: True)})()
    app._backend_priority_song_names = {"New Song"}
    app._backend_priority_song_repeat_count = 40
    cfg = _build_cfg(25)

    song_queue = [("dummy.txt", "New Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 40
    assert task_queue_label(tasks[-1]) == "New Song (Run 40/40)"


def test_prepare_tasks_does_not_collapse_song_repeats():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(25)

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 25
    assert [task_queue_label(t) for t in tasks] == [
        "Dummy Song (Run 1/25)",
        "Dummy Song (Run 2/25)",
        "Dummy Song (Run 3/25)",
        "Dummy Song (Run 4/25)",
        "Dummy Song (Run 5/25)",
        "Dummy Song (Run 6/25)",
        "Dummy Song (Run 7/25)",
        "Dummy Song (Run 8/25)",
        "Dummy Song (Run 9/25)",
        "Dummy Song (Run 10/25)",
        "Dummy Song (Run 11/25)",
        "Dummy Song (Run 12/25)",
        "Dummy Song (Run 13/25)",
        "Dummy Song (Run 14/25)",
        "Dummy Song (Run 15/25)",
        "Dummy Song (Run 16/25)",
        "Dummy Song (Run 17/25)",
        "Dummy Song (Run 18/25)",
        "Dummy Song (Run 19/25)",
        "Dummy Song (Run 20/25)",
        "Dummy Song (Run 21/25)",
        "Dummy Song (Run 22/25)",
        "Dummy Song (Run 23/25)",
        "Dummy Song (Run 24/25)",
        "Dummy Song (Run 25/25)",
    ]


def test_prepare_tasks_bundle_song_repeats_keeps_one_physical_task():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(25)
    cfg.set("IterationEngine", "BundleSongRepeats", "true")

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 1
    assert task_queue_label(tasks[0]) == "Dummy Song"
    bundle = tasks[0][15]
    assert bundle["repeat_bundle"] is True
    assert int(bundle["repeat_total"]) == 25
    assert len(bundle["runs"]) == 25


def test_native_repeat_bundle_materializes_logical_run_label():
    bundle_task = (
        "dummy.txt",
        "Dummy Song",
        "Hard",
        {},
        {},
        {},
        [],
        [],
        {},
        {},
        "",
        1,
        None,
        1,
        False,
        {
            "repeat_bundle": True,
            "repeat_total": 3,
            "runs": [
                {"repeat_index": 1, "repeat_total": 3, "ga_seed": 101},
                {"repeat_index": 2, "repeat_total": 3, "ga_seed": 202},
                {"repeat_index": 3, "repeat_total": 3, "ga_seed": 303},
            ],
        },
    )

    bundle = extract_repeat_bundle(bundle_task)
    assert bundle is not None
    assert task_queue_label(bundle_task) == "Dummy Song"

    logical_task = materialize_repeat_task(bundle_task, bundle["runs"][1])
    assert extract_repeat_bundle(logical_task) is None
    assert task_queue_label(logical_task) == "Dummy Song (Run 2/3)"
