import numpy as np

from gear_optimizer.solver import song_preparation


def test_build_prepared_calc_song_clones_preloaded_song_and_normalizes_timestamps(monkeypatch):
    monkeypatch.setattr(
        song_preparation,
        "_apply_timing_envelope",
        lambda calc_song: {"mode": "pytest", "great_mode": "strict", "notes": 2},
    )
    preloaded = {
        "metadata": {"Primary Color": "Rush"},
        "song_data": {
            "timestamps": [1.25, 2.5],
            "note_types": [1, 1],
        },
    }

    prepared = song_preparation.build_prepared_calc_song(
        fp="unused",
        cfg_dict={},
        preloaded_calc_song=preloaded,
    )

    assert prepared.read_sec == 0.0
    assert prepared.timing_envelope_info == {"mode": "pytest", "great_mode": "strict", "notes": 2}
    assert prepared.timing_envelope_sec >= 0.0
    assert prepared.calc_song is not preloaded
    assert prepared.calc_song["song_data"] is not preloaded["song_data"]
    assert "chart_timestamps" not in preloaded["song_data"]
    np.testing.assert_allclose(prepared.calc_song["song_data"]["chart_timestamps"], np.asarray([1.25, 2.5]))
    assert prepared.calc_song["song_data"]["chart_timestamps"].dtype == np.float32


def test_build_prepared_calc_song_clones_cached_base_song(monkeypatch):
    base = {
        "metadata": {"Primary Color": "Rush"},
        "song_data": {
            "timestamps": np.asarray([4.0], dtype=np.float32),
            "chart_timestamps": np.asarray([4.0], dtype=np.float32),
        },
    }
    monkeypatch.setattr(song_preparation, "get_base_calc_song", lambda fp, cfg_dict: base)
    monkeypatch.setattr(song_preparation, "_apply_timing_envelope", lambda calc_song: None)

    prepared = song_preparation.build_prepared_calc_song(fp="song.txt", cfg_dict={"x": "y"})
    prepared.calc_song["metadata"]["Primary Color"] = "Changed"

    assert prepared.calc_song is not base
    assert base["metadata"]["Primary Color"] == "Rush"
    np.testing.assert_allclose(prepared.calc_song["song_data"]["chart_timestamps"], base["song_data"]["chart_timestamps"])


def test_build_prepared_song_config_names_setup_tuple_fields(monkeypatch):
    ga_settings = object()
    monkeypatch.setattr(
        song_preparation,
        "_setup_song_config",
        lambda *args, **kwargs: (
            ga_settings,
            {"Perfect Points": 1},
            {"gear": 2},
            [{"Name": "G"}],
            {"mini": 3},
            [{"Name": "M"}],
            1,
            1,
            0,
            1,
            0,
            1,
            [["fg"]],
            0,
        ),
    )

    prepared = song_preparation.build_prepared_song_config(
        cfg=object(),
        calc_song={"metadata": {}, "song_data": {}},
        auto_buff=False,
        paths={},
        gears_by_name={},
        minis_by_name={},
    )

    assert prepared.ga_settings is ga_settings
    assert prepared.fixed_stats == {"Perfect Points": 1}
    assert prepared.current_gear_stats == {"gear": 2}
    assert prepared.current_gear_list == [{"Name": "G"}]
    assert prepared.current_mini_stats == {"mini": 3}
    assert prepared.current_mini_list == [{"Name": "M"}]
    assert prepared.meta_finder is True
    assert prepared.enable_fever is True
    assert prepared.enable_mini is False
    assert prepared.enable_gear is True
    assert prepared.force_greats_mode is False
    assert prepared.force_greats_finder is True
    assert prepared.force_greats_config == [["fg"]]
    assert prepared.manual_force_greats is False
