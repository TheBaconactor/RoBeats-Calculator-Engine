import pytest

from gear_optimizer.domain.jobs import (
    LEGACY_TASK_FIXED_FIELD_COUNT,
    LegacyTaskIndex,
    effective_task_count,
    extract_repeat_bundle,
    extract_repeat_context,
    legacy_task_tuple_from_job_context,
    materialize_repeat_task,
    seed_plan_from_song_job,
    task_cfg_dict,
    task_difficulty,
    task_ga_seed,
    task_queue_label,
    task_song_name,
    task_tuple_to_legacy_view,
    task_tuple_to_shared_context,
    task_tuple_to_song_job,
)


def _legacy_task(*extras):
    prefix = (
        "Data/Hard/FakeSong.txt",
        "Fake Song (Hard) by Tester",
        "Hard",
        {"IterationEngine": {"GA_SearchDepth": "125"}},
        {"base": "paths"},
        ("ref",),
        ("gear",),
        ("mini",),
        {"gear": object()},
        {"mini": object()},
        125,
        6,
        True,
    )
    assert len(prefix) == LEGACY_TASK_FIXED_FIELD_COUNT
    return prefix + tuple(extras)


def test_legacy_task_indices_match_production_tuple_prefix():
    task = _legacy_task()

    assert task[LegacyTaskIndex.FILE_PATH] == "Data/Hard/FakeSong.txt"
    assert task[LegacyTaskIndex.SONG_NAME] == "Fake Song (Hard) by Tester"
    assert task[LegacyTaskIndex.DIFFICULTY] == "Hard"
    assert task[LegacyTaskIndex.GA_DEPTH] == 125
    assert task[LegacyTaskIndex.PARALLEL_WORKERS] == 6


def test_task_field_helpers_name_the_production_tuple_prefix():
    task = _legacy_task({"extra": True})

    assert task_song_name(task) == "Fake Song (Hard) by Tester"
    assert task_difficulty(task) == "Hard"
    assert task_cfg_dict(task) == {"IterationEngine": {"GA_SearchDepth": "125"}}
    assert task[LegacyTaskIndex.FILE_PATH] == "Data/Hard/FakeSong.txt"
    assert task[LegacyTaskIndex.REF_ARRAYS] == ("ref",)
    assert task[LEGACY_TASK_FIXED_FIELD_COUNT:] == ({"extra": True},)


def test_task_tuple_to_song_job_preserves_queue_identity_and_repeat_metadata():
    repeat_ctx = {"repeat_index": 2, "repeat_total": 3, "ga_seed": 987}
    job = task_tuple_to_song_job(_legacy_task(repeat_ctx))

    assert job.file_path == "Data/Hard/FakeSong.txt"
    assert job.song_name == "Fake Song (Hard) by Tester"
    assert job.difficulty == "Hard"
    assert job.repeat_index == 2
    assert job.repeat_total == 3
    assert job.ga_seed == 987
    assert job.repeat_bundle is False
    assert job.queue_source == "legacy_task_tuple"


def test_seed_plan_from_song_job_preserves_repeat_label_and_seed():
    repeat_ctx = {"repeat_index": 2, "repeat_total": 3, "ga_seed": 987}
    job = task_tuple_to_song_job(_legacy_task(repeat_ctx))
    seed_plan = seed_plan_from_song_job(job)

    assert seed_plan.queue_label == "Fake Song (Hard) by Tester (Run 2/3)"
    assert seed_plan.repeat_index == 2
    assert seed_plan.repeat_total == 3
    assert seed_plan.ga_seed == 987


def test_seed_plan_from_song_job_defaults_non_repeat_to_base_label():
    seed_plan = seed_plan_from_song_job(task_tuple_to_song_job(_legacy_task()))

    assert seed_plan.queue_label == "Fake Song (Hard) by Tester"
    assert seed_plan.repeat_index == 0
    assert seed_plan.repeat_total == 0
    assert seed_plan.ga_seed is None


def test_task_tuple_to_shared_context_preserves_shared_runtime_fields():
    ctx = task_tuple_to_shared_context(_legacy_task())

    assert ctx.cfg_dict == {"IterationEngine": {"GA_SearchDepth": "125"}}
    assert ctx.paths == {"base": "paths"}
    assert ctx.ref_arrays == ("ref",)
    assert ctx.all_gears == ("gear",)
    assert ctx.all_minis == ("mini",)
    assert ctx.ga_depth == 125
    assert ctx.parallel_workers == 6
    assert ctx.fg_debug is True


def test_task_tuple_to_legacy_view_keeps_extras_separate_from_shared_context():
    repeat_ctx = {"repeat_index": 1, "repeat_total": 2, "ga_seed": 123}
    extra = {"debug": True}
    view = task_tuple_to_legacy_view(_legacy_task(extra, repeat_ctx))

    assert view.job.song_name == "Fake Song (Hard) by Tester"
    assert view.context.ga_depth == 125
    assert view.extras == (extra, repeat_ctx)


def test_legacy_task_tuple_from_job_context_is_single_tuple_writer():
    repeat_ctx = {"repeat_index": 2, "repeat_total": 3, "ga_seed": 987}
    original = _legacy_task(repeat_ctx)
    view = task_tuple_to_legacy_view(original)

    rebuilt = legacy_task_tuple_from_job_context(view.job, view.context, *view.extras)

    assert rebuilt == original


def test_repeat_helpers_are_the_single_legacy_tuple_contract():
    repeat_ctx = {"repeat_index": 3, "repeat_total": 4, "ga_seed": "456"}
    task = _legacy_task({"unrelated": True}, repeat_ctx)

    assert extract_repeat_context(task) is repeat_ctx
    assert task_queue_label(task) == "Fake Song (Hard) by Tester (Run 3/4)"
    assert task_ga_seed(task) == 456


def test_bundle_helpers_count_logical_repeats_without_materializing_work():
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 3,
        "runs": [
            {"repeat_index": 1, "repeat_total": 3, "ga_seed": 101},
            {"repeat_index": 2, "repeat_total": 3, "ga_seed": 202},
            {"repeat_index": 3, "repeat_total": 3, "ga_seed": 303},
        ],
    }
    task = _legacy_task(bundle)

    assert extract_repeat_bundle(task) is bundle
    assert task_tuple_to_song_job(task).repeat_bundle is True
    assert task_tuple_to_song_job(task).repeat_total == 3
    assert effective_task_count([task, _legacy_task()]) == 4


def test_materialize_repeat_task_replaces_bundle_metadata_with_one_repeat_context():
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 2,
        "runs": [{"repeat_index": 1, "repeat_total": 2, "ga_seed": 101}],
    }
    old_repeat = {"repeat_index": 9, "repeat_total": 9, "ga_seed": 999}
    unrelated = {"keep": True}
    repeat_ctx = {"repeat_index": 1, "repeat_total": 2, "ga_seed": 101}

    original = _legacy_task(bundle, unrelated, old_repeat)
    materialized = materialize_repeat_task(original, repeat_ctx)

    assert materialized[:LEGACY_TASK_FIXED_FIELD_COUNT] == original[:LEGACY_TASK_FIXED_FIELD_COUNT]
    assert materialized[LEGACY_TASK_FIXED_FIELD_COUNT:] == (unrelated, repeat_ctx)


def test_short_legacy_tuple_is_rejected_at_the_adapter_boundary():
    with pytest.raises(ValueError, match="13-field production prefix"):
        task_tuple_to_song_job(("too", "short"))
