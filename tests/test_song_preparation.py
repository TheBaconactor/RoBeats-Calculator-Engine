from gear_optimizer.helpers.song_helpers.database_context import SongDbBaseline
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver import song_preparation
from tests.songs_support import make_song


def test_build_prepared_song_core_owns_song_stats_and_db_setup(monkeypatch):
    song = make_song([1.25, 2.5], primary="Rush", secondary="Flow")
    baseline = SongDbBaseline("Song", 0, 0, False)
    calls = {}

    def _fake_prepare(fp):
        calls["fp"] = fp
        return song

    def _fake_db(found_song_name):
        calls["db"] = found_song_name
        return baseline

    monkeypatch.setattr(song_preparation, "prepare_song", _fake_prepare)
    monkeypatch.setattr(song_preparation, "load_song_db_baseline", _fake_db)

    prepared = song_preparation.build_prepared_song_core(fp="song.txt", found_song_name="Song", minis={})

    assert calls == {"fp": "song.txt", "db": "Song"}
    assert prepared.song is song
    assert prepared.fixed_stats == baseline_fixed_stats(song.chart)
    assert prepared.fixed_stats["Rush"] == 30
    assert prepared.db_context is baseline
