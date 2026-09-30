from gear_optimizer.solver.song_db_context import PreparedSongDbContext
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver import song_preparation
from tests.songs_support import make_song


def test_build_prepared_song_core_owns_song_stats_and_db_setup(monkeypatch):
    song = make_song([1.25, 2.5], primary="Rush", secondary="Flow")
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

    def _fake_prepare(fp):
        calls["fp"] = fp
        return song

    def _fake_db(**kwargs):
        calls["db"] = kwargs
        return db_context

    monkeypatch.setattr(song_preparation, "prepare_song", _fake_prepare)
    monkeypatch.setattr(song_preparation, "load_prepared_song_db_context", _fake_db)

    prepared = song_preparation.build_prepared_song_core(
        fp="song.txt",
        found_song_name="Song",
        minis={},
        cache_db_context=True,
    )

    assert calls["fp"] == "song.txt"
    assert prepared.song is song
    assert prepared.fixed_stats == baseline_fixed_stats(song.chart)
    assert prepared.fixed_stats["Rush"] == 30
    assert prepared.db_context is db_context
    assert calls["db"]["found_song_name"] == "Song"
    assert calls["db"]["cache_db_context"] is True
