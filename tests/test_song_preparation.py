import numpy as np

from gear_optimizer.solver.song_db_context import PreparedSongDbContext
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
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
    monkeypatch.setattr(song_preparation, "get_base_calc_song", lambda fp: base)
    monkeypatch.setattr(song_preparation, "_apply_timing_envelope", lambda calc_song: None)

    prepared = song_preparation.build_prepared_calc_song(fp="song.txt")
    prepared.calc_song["metadata"]["Primary Color"] = "Changed"

    assert prepared.calc_song is not base
    assert base["metadata"]["Primary Color"] == "Rush"
    np.testing.assert_allclose(prepared.calc_song["song_data"]["chart_timestamps"], base["song_data"]["chart_timestamps"])


def test_build_prepared_song_core_owns_calc_stats_and_db_setup(monkeypatch):
    prepared_calc = song_preparation.PreparedCalcSong(
        calc_song={"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}, "song_data": {}},
        read_sec=1.5,
        timing_envelope_sec=0.25,
        timing_envelope_info=None,
    )
    db_context = PreparedSongDbContext(
        baseline_team_buff="T5",
        db_key="Song",
        prev_record=None,
        db_best_score=0,
        db_best_fg_score=0,
        attempt_lifetime=0,
        attempts_first=0,
        prev_attempts_first=0,
        db_baseline_valid=False,
    )
    calls = {}

    def _fake_calc(**kwargs):
        calls["calc"] = kwargs
        return prepared_calc

    def _fake_db(**kwargs):
        calls["db"] = kwargs
        return db_context

    monkeypatch.setattr(song_preparation, "build_prepared_calc_song", _fake_calc)
    monkeypatch.setattr(song_preparation, "load_prepared_song_db_context", _fake_db)

    prepared = song_preparation.build_prepared_song_core(
        fp="song.txt",
        found_song_name="Song",
        gears_by_name={},
        minis_by_name={},
        cache_db_context=True,
    )

    assert prepared.calc_song is prepared_calc.calc_song
    assert prepared.fixed_stats == baseline_fixed_stats(prepared_calc.calc_song)
    assert prepared.fixed_stats["Rush"] == 30
    assert prepared.db_context is db_context
    assert prepared.meta_primary_color == "Rush"
    assert prepared.meta_secondary_color == "Flow"
    assert calls["db"]["calc_song"] is prepared_calc.calc_song
    assert calls["db"]["cache_db_context"] is True
