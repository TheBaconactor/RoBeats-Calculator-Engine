import configparser

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.domain.jobs import (
    SharedRunContext,
    SongJob,
    extract_repeat_bundle,
    extract_repeat_context,
    materialize_repeat_task,
    task_queue_label,
    task_tuple_from_job_context,
)


def _build_cfg(song_repeats: int) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "SongRepeats", str(int(song_repeats)))
    return cfg


def _prepare(song_repeats: int):
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    return app._prepare_tasks(
        song_queue=[("dummy.txt", "Dummy Song", "Hard")],
        cfg=_build_cfg(song_repeats),
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        fg_debug=False,
    )


def test_prepare_tasks_song_repeats_expands_queue_with_run_metadata():
    tasks = _prepare(3)

    assert len(tasks) == 3
    assert all(len(task) == 13 for task in tasks)
    assert [task_queue_label(task) for task in tasks] == [
        "Dummy Song (Run 1/3)",
        "Dummy Song (Run 2/3)",
        "Dummy Song (Run 3/3)",
    ]
    assert [extract_repeat_context(task) for task in tasks] == [
        {"repeat_index": 1, "repeat_total": 3},
        {"repeat_index": 2, "repeat_total": 3},
        {"repeat_index": 3, "repeat_total": 3},
    ]


def test_prepare_tasks_single_run_has_no_redundant_repeat_metadata():
    tasks = _prepare(1)

    assert len(tasks) == 1
    assert len(tasks[0]) == 12
    assert extract_repeat_context(tasks[0]) is None
    assert task_queue_label(tasks[0]) == "Dummy Song"


def test_prepare_tasks_does_not_collapse_explicit_song_repeats():
    tasks = _prepare(25)

    assert len(tasks) == 25
    assert [task_queue_label(task) for task in tasks] == [
        f"Dummy Song (Run {index}/25)" for index in range(1, 26)
    ]


def test_native_repeat_bundle_materializes_logical_run_label():
    context = SharedRunContext(
        cfg_dict={},
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        parallel_workers=1,
        fg_debug=False,
    )
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 3,
        "runs": [
            {"repeat_index": 1, "repeat_total": 3},
            {"repeat_index": 2, "repeat_total": 3},
            {"repeat_index": 3, "repeat_total": 3},
        ],
    }
    bundle_task = task_tuple_from_job_context(
        SongJob("dummy.txt", "Dummy Song", "Hard", repeat_total=3, repeat_bundle=True),
        context,
        bundle,
    )

    assert extract_repeat_bundle(bundle_task) is bundle
    assert task_queue_label(bundle_task) == "Dummy Song"

    logical_task = materialize_repeat_task(bundle_task, bundle["runs"][1])
    assert extract_repeat_bundle(logical_task) is None
    assert task_queue_label(logical_task) == "Dummy Song (Run 2/3)"
