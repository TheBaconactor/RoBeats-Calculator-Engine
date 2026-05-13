import pytest

from dataclasses import fields

from gear_optimizer.solver.native_inflight_types import (
    NativeSong,
    NativeSongConfig,
    NativeSongBundleState,
    NativeSongDBState,
    NativeSongDecodeState,
    NativeSongGPUInputs,
    NativeSongFGState,
    NativeSongGAState,
    NativeSongPrepState,
    NativeSongPostState,
    NativeSongRuntimeState,
    _FIELD_PATH_BY_NAME,
    make_native_song,
    native_song_get,
    native_song_group,
    native_song_label,
    native_song_set,
)


def test_native_song_groups_keep_pipeline_fields_explicit():
    song = NativeSong(
        config=NativeSongConfig(fp="file.txt", song_name="demo", task_key="task"),
        gpu_inputs=NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=NativeSongRuntimeState(song_slot=3),
    )

    assert song.config.fp == "file.txt"
    assert song.config.song_name == "demo"
    assert song.gpu_inputs.meta_primary_color == "Rush"
    assert song.runtime.song_slot == 3
    assert song.runtime.ga.ga_future is None
    assert song.runtime.fg.fg_static_prep_done is False
    assert song.runtime.db.db_best_score == 0
    assert native_song_group(song, "runtime.fg") is song.runtime.fg

    assert not hasattr(song, "fp")
    assert not hasattr(song, "meta_primary_color")
    assert not hasattr(song, "song_slot")
    assert not hasattr(song, "ga_future")
    assert not hasattr(song, "fg_static_prep_done")


def test_native_song_get_set_delegate_to_nested_groups():
    song = NativeSong(
        config=NativeSongConfig(fp="file.txt"),
        gpu_inputs=NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=NativeSongRuntimeState(song_slot=3),
    )

    assert native_song_get(song, "fp") == "file.txt"
    assert native_song_get(song, "meta_primary_color") == "Rush"
    assert native_song_get(song, "song_slot") == 3
    assert native_song_get(song, "ga_future") is None

    native_song_set(song, "fp", "updated.txt")
    native_song_set(song, "meta_primary_color", "Flow")
    native_song_set(song, "song_slot", 7)
    marker = object()
    native_song_set(song, "ga_future", marker)
    native_song_set(song, "fg_static_prep_done", True)

    assert song.config.fp == "updated.txt"
    assert song.gpu_inputs.meta_primary_color == "Flow"
    assert song.runtime.song_slot == 7
    assert song.runtime.ga.ga_future is marker
    assert song.runtime.fg.fg_static_prep_done is True


def test_native_song_helpers_reject_unknown_fields():
    song = NativeSong(
        config=NativeSongConfig(fp="file.txt"),
        gpu_inputs=NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=NativeSongRuntimeState(song_slot=3),
    )

    assert native_song_get(song, "missing") is None
    assert native_song_get(song, "missing", "fallback") == "fallback"
    with pytest.raises(AttributeError):
        native_song_group(song, "runtime.missing")
    with pytest.raises(AttributeError):
        native_song_set(song, "missing", 1)
    with pytest.raises(TypeError):
        make_native_song(not_a_field=1)


def test_native_song_label_prefers_task_key_then_song_name_then_optional_id():
    keyed = make_native_song(task_key="task-a", song_name="Song A")
    named = make_native_song(task_key="", song_name="Song B")
    unnamed = make_native_song(task_key="", song_name="")

    assert native_song_label(keyed) == "task-a"
    assert native_song_label(named) == "Song B"
    assert native_song_label(unnamed) == ""
    assert native_song_label(unnamed, fallback_id=True) == str(id(unnamed))


def test_native_song_field_path_map_matches_runtime_substate_definitions():
    def mapped_fields(*path: str) -> set[str]:
        target = tuple(path)
        return {field_name for field_name, field_path in _FIELD_PATH_BY_NAME.items() if field_path == target}

    assert {field.name for field in fields(NativeSongConfig)} == mapped_fields("config")
    assert {field.name for field in fields(NativeSongGPUInputs)} == mapped_fields("gpu_inputs")
    assert {field.name for field in fields(NativeSongRuntimeState)} == {"song_slot", "prep", "ga", "decode", "fg", "db", "bundle", "post"}
    assert {field.name for field in fields(NativeSongPrepState)} == mapped_fields("runtime", "prep")
    assert {field.name for field in fields(NativeSongGAState)} == mapped_fields("runtime", "ga")
    assert {field.name for field in fields(NativeSongDecodeState)} == mapped_fields("runtime", "decode")
    assert {field.name for field in fields(NativeSongFGState)} == mapped_fields("runtime", "fg")
    assert {field.name for field in fields(NativeSongDBState)} == mapped_fields("runtime", "db")
    assert {field.name for field in fields(NativeSongBundleState)} == mapped_fields("runtime", "bundle")
    assert {field.name for field in fields(NativeSongPostState)} == mapped_fields("runtime", "post")
    assert _FIELD_PATH_BY_NAME["song_slot"] == ("runtime",)
