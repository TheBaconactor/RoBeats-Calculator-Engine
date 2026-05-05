from gear_optimizer.solver.native_inflight_types import (
    _NativeSong,
    _NativeSongConfig,
    _NativeSongGPUInputs,
    _NativeSongRuntimeState,
    native_song_get,
    native_song_set,
)


def test_native_song_groups_keep_pipeline_fields_explicit():
    song = _NativeSong(
        config=_NativeSongConfig(fp="file.txt", song_name="demo", task_key="task"),
        gpu_inputs=_NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=_NativeSongRuntimeState(song_slot=3),
    )

    assert song.config.fp == "file.txt"
    assert song.config.song_name == "demo"
    assert song.gpu_inputs.meta_primary_color == "Rush"
    assert song.runtime.song_slot == 3

    assert not hasattr(song, "fp")
    assert not hasattr(song, "meta_primary_color")
    assert not hasattr(song, "song_slot")


def test_native_song_get_set_delegate_to_nested_groups():
    song = _NativeSong(
        config=_NativeSongConfig(fp="file.txt"),
        gpu_inputs=_NativeSongGPUInputs(meta_primary_color="Rush"),
        runtime=_NativeSongRuntimeState(song_slot=3),
    )

    assert native_song_get(song, "fp") == "file.txt"
    assert native_song_get(song, "meta_primary_color") == "Rush"
    assert native_song_get(song, "song_slot") == 3

    native_song_set(song, "fp", "updated.txt")
    native_song_set(song, "meta_primary_color", "Flow")
    native_song_set(song, "song_slot", 7)

    assert song.config.fp == "updated.txt"
    assert song.gpu_inputs.meta_primary_color == "Flow"
    assert song.runtime.song_slot == 7
