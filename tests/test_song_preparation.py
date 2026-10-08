from gear_optimizer.chart import load_chart
from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.helpers.song_helpers.database_context import SongDbBaseline
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver import song_preparation


def test_build_prepared_song_core_times_the_shared_chart_in_the_tasks_mode(monkeypatch, tmp_path):
    chart = tmp_path / "song.txt"
    chart.write_text(
        "Song Name\tSong\nDifficulty\tHard\nPrimary Color\tRush\nSecondary Color\tFlow\nLast Note Time\t0.4\n"
        "Total Notes\t3\nLong Notes\t1\nSong Data\n0.0 0 0 1\n0.2 0 0 3\n0.4 0 0 1\n",
        encoding="utf-8",
    )
    baseline = SongDbBaseline("Song", 0, 0, False)
    calls = []

    def _fake_db(found_song_name, mode):
        calls.append((found_song_name, mode))
        return baseline

    monkeypatch.setattr(song_preparation, "load_song_db_baseline", _fake_db)

    prepared = song_preparation.build_prepared_song_core(fp=str(chart), found_song_name="Song", mode=PRECISE, minis={})

    assert calls == [("Song", PRECISE)]
    assert prepared.song.chart is load_chart(chart)
    assert prepared.song.mode == PRECISE and prepared.song.perfect_candidates is not None
    assert prepared.fixed_stats == baseline_fixed_stats(prepared.song.chart)
    assert prepared.fixed_stats["Rush"] == 30
    assert prepared.db_context is baseline
