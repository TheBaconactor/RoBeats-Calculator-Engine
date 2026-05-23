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
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 3
    assert all(len(t) == 15 for t in tasks)
    assert [task_queue_label(t) for t in tasks] == [
        "Dummy Song (Run 1/3)",
        "Dummy Song (Run 2/3)",
        "Dummy Song (Run 3/3)",
    ]

    seeds = [t[14]["ga_seed"] for t in tasks]
    assert len(seeds) == 3
    assert len(set(seeds)) == 3


def test_prepare_tasks_song_repeats_one_still_seeds_single_run():
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
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 1
    assert len(tasks[0]) == 15
    repeat_ctx = extract_repeat_context(tasks[0])
    assert repeat_ctx is not None
    assert repeat_ctx["repeat_index"] == 1
    assert repeat_ctx["repeat_total"] == 1
    assert isinstance(repeat_ctx["ga_seed"], int)
    assert repeat_ctx["ga_seed"] >= 0
    assert task_queue_label(tasks[0]) == "Dummy Song"


def test_prepare_tasks_song_repeats_one_randomizes_across_preparations(monkeypatch):
    from gear_optimizer import app as app_module

    seeds = iter([101, 202])
    monkeypatch.setattr(app_module.secrets, "randbits", lambda _bits: next(seeds))

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(1)
    song_queue = [("dummy.txt", "Dummy Song", "Hard")]

    first = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )
    second = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert extract_repeat_context(first[0])["ga_seed"] == 101
    assert extract_repeat_context(second[0])["ga_seed"] == 202


def test_prepare_tasks_accepts_zero_as_random_seed(monkeypatch):
    from gear_optimizer import app as app_module

    seeds = iter([0])
    monkeypatch.setattr(app_module.secrets, "randbits", lambda _bits: next(seeds))

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(1)
    tasks = app._prepare_tasks(
        song_queue=[("dummy.txt", "Dummy Song", "Hard")],
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert extract_repeat_context(tasks[0])["ga_seed"] == 0


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
