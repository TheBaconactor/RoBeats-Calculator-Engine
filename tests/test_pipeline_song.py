import pytest

from dataclasses import fields

from gear_optimizer.pipeline.song import (
    NativeSong,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongDecodeState,
    NativeSongGPUInputs,
    NativeSongFGState,
    NativeSongRuntimeState,
    native_song_label,
)
from tests.native_song_factory import _FIELD_PATH_BY_NAME, make_native_song


def test_native_song_groups_keep_pipeline_fields_explicit():
    song = NativeSong(
        config=NativeSongConfig(song_name="demo", task_key="task"),
        gpu_inputs=NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=NativeSongRuntimeState(song_slot=3),
    )

    assert song.config.song_name == "demo"
    assert song.gpu_inputs.meta_primary_color == "Rush"
    assert song.runtime.song_slot == 3
    assert song.runtime.fg.fg_owner_score_map is None
    assert song.runtime.db.db_best_score == 0


def test_make_native_song_routes_flat_fields_to_nested_groups():
    marker = object()
    song = make_native_song(
        song_name="demo",
        meta_primary_color="Rush",
        song_slot=3,
        fg_owner_score_map=marker,
    )

    assert song.config.song_name == "demo"
    assert song.gpu_inputs.meta_primary_color == "Rush"
    assert song.runtime.song_slot == 3
    assert song.runtime.fg.fg_owner_score_map is marker


def test_make_native_song_rejects_unknown_fields():
    with pytest.raises(TypeError):
        make_native_song(not_a_field=1)


def test_native_song_label_prefers_task_key_then_song_name():
    keyed = make_native_song(task_key="task-a", song_name="Song A")
    named = make_native_song(task_key="", song_name="Song B")
    unnamed = make_native_song(task_key="", song_name="")

    assert native_song_label(keyed) == "task-a"
    assert native_song_label(named) == "Song B"
    assert native_song_label(unnamed) == ""


def test_native_song_field_path_map_matches_runtime_substate_definitions():
    def mapped_fields(*path: str) -> set[str]:
        target = tuple(path)
        return {field_name for field_name, field_path in _FIELD_PATH_BY_NAME.items() if field_path == target}

    assert {field.name for field in fields(NativeSongConfig)} == mapped_fields("config")
    assert {field.name for field in fields(NativeSongGPUInputs)} == mapped_fields("gpu_inputs")
    assert {field.name for field in fields(NativeSongRuntimeState)} == {"song_slot", "decode", "fg", "db"}
    assert {field.name for field in fields(NativeSongDecodeState)} == mapped_fields("runtime", "decode")
    assert {field.name for field in fields(NativeSongFGState)} == mapped_fields("runtime", "fg")
    assert {field.name for field in fields(NativeSongDBState)} == mapped_fields("runtime", "db")
    assert _FIELD_PATH_BY_NAME["song_slot"] == ("runtime",)
