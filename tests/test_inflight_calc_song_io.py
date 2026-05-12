import numpy as np

from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.solver.song_preparation import build_prepared_calc_song


def _write_song(path):
    path.write_text(
        "\n".join(
            [
                "Song Name\tShared IO Song",
                "Difficulty\tHard",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Last Note Time\t0.4",
                "Total Notes\t3",
                "Long Notes\t1",
                "Song Data",
                "0.0 0 0 1",
                "0.2 0 0 3",
                "0.4 0 0 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_native_calc_song_uses_shared_base_song_io_and_clones_before_timing_envelope(tmp_path):
    song_path = tmp_path / "shared_io_song.txt"
    _write_song(song_path)
    cfg_dict = {"IterationEngine": {"GA_SearchDepth": "125"}}

    base_calc_song = get_base_calc_song(str(song_path), cfg_dict)
    native_calc_song = build_prepared_calc_song(fp=str(song_path), cfg_dict=cfg_dict).calc_song

    assert native_calc_song is not base_calc_song
    assert native_calc_song["metadata"]["Song Name"] == "Shared IO Song"
    assert native_calc_song["metadata"]["TimingEnvelopeApplied"] is True
    assert "TimingEnvelopeApplied" not in base_calc_song["metadata"]

    assert np.array_equal(
        native_calc_song["song_data"]["timestamps"],
        base_calc_song["song_data"]["timestamps"],
    )
    assert np.array_equal(
        native_calc_song["song_data"]["note_types"],
        np.asarray([1, 3, 1], dtype=np.int16),
    )
    assert np.array_equal(
        native_calc_song["song_data"]["fg_timestamps"],
        native_calc_song["song_data"]["chart_timestamps"],
    )
    assert "fg_timestamps" not in base_calc_song["song_data"]
