import pytest

from gear_optimizer.domain.jobs import (
    TASK_FIXED_FIELD_COUNT,
    SongJob,
    TaskIndex,
    effective_task_count,
    extract_repeat_bundle,
    extract_repeat_context,
    materialize_repeat_task,
    task_cfg_dict,
    task_difficulty,
    task_queue_label,
    task_song_name,
    task_tuple_from_job_context,
    task_tuple_to_shared_context,
    task_tuple_to_song_job,
    task_tuple_to_view,
)


def _task(*extras):
    prefix = (
        "Data/Hard/FakeSong.txt",
        "Fake Song (Hard) by Tester",
        "Hard",
        {"IterationEngine": {"InFlightSongs": "12"}},
        {"base": "paths"},
        ("ref",),
        ("gear",),
        ("mini",),
        {"gear": object()},
        {"mini": object()},
        6,
        True,
    )
    assert len(prefix) == TASK_FIXED_FIELD_COUNT
    return prefix + tuple(extras)


def test_task_indices_match_production_tuple_prefix():
    task = _task()

    assert task[TaskIndex.FILE_PATH] == "Data/Hard/FakeSong.txt"
    assert task[TaskIndex.SONG_NAME] == "Fake Song (Hard) by Tester"
    assert task[TaskIndex.DIFFICULTY] == "Hard"
    assert task[TaskIndex.PARALLEL_WORKERS] == 6
    assert task[TaskIndex.FG_DEBUG] is True


def test_task_field_helpers_name_the_production_tuple_prefix():
    task = _task({"extra": True})

    assert task_song_name(task) == "Fake Song (Hard) by Tester"
    assert task_difficulty(task) == "Hard"
    assert task_cfg_dict(task) == {"IterationEngine": {"InFlightSongs": "12"}}
    assert task[TaskIndex.REF_ARRAYS] == ("ref",)
    assert task[TASK_FIXED_FIELD_COUNT:] == ({"extra": True},)


def test_task_tuple_to_song_job_preserves_queue_identity_and_repeat_metadata():
    repeat_ctx = {"repeat_index": 2, "repeat_total": 3}
    job = task_tuple_to_song_job(_task(repeat_ctx))

    assert job.file_path == "Data/Hard/FakeSong.txt"
    assert job.song_name == "Fake Song (Hard) by Tester"
    assert job.difficulty == "Hard"
    assert job.repeat_index == 2
    assert job.repeat_total == 3
    assert job.repeat_bundle is False
    assert job.queue_source == "task_tuple"


def test_task_tuple_to_shared_context_preserves_shared_runtime_fields():
    ctx = task_tuple_to_shared_context(_task())

    assert ctx.cfg_dict == {"IterationEngine": {"InFlightSongs": "12"}}
    assert ctx.paths == {"base": "paths"}
    assert ctx.ref_arrays == ("ref",)
    assert ctx.all_gears == ("gear",)
    assert ctx.all_minis == ("mini",)
    assert ctx.parallel_workers == 6
    assert ctx.fg_debug is True


def test_task_tuple_to_view_keeps_extras_separate_from_shared_context():
    repeat_ctx = {"repeat_index": 1, "repeat_total": 2}
    extra = {"debug": True}
    view = task_tuple_to_view(_task(extra, repeat_ctx))

    assert view.job.song_name == "Fake Song (Hard) by Tester"
    assert view.context.parallel_workers == 6
    assert view.extras == (extra, repeat_ctx)


def test_task_tuple_from_job_context_is_single_tuple_writer():
    original = _task({"repeat_index": 2, "repeat_total": 3})
    view = task_tuple_to_view(original)

    rebuilt = task_tuple_from_job_context(view.job, view.context, *view.extras)

    assert rebuilt == original


def test_repeat_helpers_preserve_logical_run_identity():
    repeat_ctx = {"repeat_index": 3, "repeat_total": 4}
    task = _task({"unrelated": True}, repeat_ctx)

    assert extract_repeat_context(task) is repeat_ctx
    assert task_queue_label(task) == "Fake Song (Hard) by Tester (Run 3/4)"


def test_bundle_helpers_count_logical_repeats_without_materializing_work():
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 3,
        "runs": [
            {"repeat_index": 1, "repeat_total": 3},
            {"repeat_index": 2, "repeat_total": 3},
            {"repeat_index": 3, "repeat_total": 3},
        ],
    }
    task = _task(bundle)

    assert extract_repeat_bundle(task) is bundle
    assert task_tuple_to_song_job(task).repeat_bundle is True
    assert task_tuple_to_song_job(task).repeat_total == 3
    assert effective_task_count([task, _task()]) == 4


def test_materialize_repeat_task_replaces_bundle_metadata_with_one_repeat_context():
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 2,
        "runs": [{"repeat_index": 1, "repeat_total": 2}],
    }
    old_repeat = {"repeat_index": 9, "repeat_total": 9}
    unrelated = {"keep": True}
    repeat_ctx = {"repeat_index": 1, "repeat_total": 2}

    original = _task(bundle, unrelated, old_repeat)
    materialized = materialize_repeat_task(original, repeat_ctx)

    assert materialized[:TASK_FIXED_FIELD_COUNT] == original[:TASK_FIXED_FIELD_COUNT]
    assert materialized[TASK_FIXED_FIELD_COUNT:] == (unrelated, repeat_ctx)


def test_short_task_tuple_is_rejected_at_the_adapter_boundary():
    with pytest.raises(ValueError, match="12-field production prefix"):
        task_tuple_to_song_job(("too", "short"))


def test_task_writer_does_not_reintroduce_optimizer_effort_fields():
    view = task_tuple_to_view(_task())
    job = SongJob(view.job.file_path, view.job.song_name, view.job.difficulty)

    rebuilt = task_tuple_from_job_context(job, view.context)

    assert len(rebuilt) == 12
