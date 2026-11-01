import pytest

from dataclasses import fields

from gear_optimizer.pipeline.song import (
    NativeSong,
    NativeSongConfig,
    NativeSongGPUInputs,
    NativeSongFGState,
    NativeSongRuntimeState,
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
    assert song.runtime.fg.fg_response_scoring_bundle is None


def test_make_native_song_routes_flat_fields_to_nested_groups():
    marker = object()
    song = make_native_song(
        song_name="demo",
        meta_primary_color="Rush",
        song_slot=3,
        fg_response_scoring_bundle=marker,
    )

    assert song.config.song_name == "demo"
    assert song.gpu_inputs.meta_primary_color == "Rush"
    assert song.runtime.song_slot == 3
    assert song.runtime.fg.fg_response_scoring_bundle is marker


def test_make_native_song_rejects_unknown_fields():
    with pytest.raises(TypeError):
        make_native_song(not_a_field=1)


def test_native_song_field_path_map_matches_runtime_substate_definitions():
    def mapped_fields(*path: str) -> set[str]:
        target = tuple(path)
        return {field_name for field_name, field_path in _FIELD_PATH_BY_NAME.items() if field_path == target}

    assert {field.name for field in fields(NativeSongConfig)} == mapped_fields("config")
    assert {field.name for field in fields(NativeSongGPUInputs)} == mapped_fields("gpu_inputs")
    assert {field.name for field in fields(NativeSongRuntimeState)} == {"song_slot", "fg"}
    assert {field.name for field in fields(NativeSongFGState)} == mapped_fields("runtime", "fg")
    assert _FIELD_PATH_BY_NAME["song_slot"] == ("runtime",)
