import os

from gear_optimizer.data import song_io


def test_scan_song_header_reuses_persisted_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "song_header_cache.json"
    song_path = tmp_path / "song.txt"
    song_path.write_text(
        "\n".join(
            [
                "Song Name\tCache Test Song",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Difficulty\tHard",
                "Song Data",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    song_io._reset_song_header_cache_for_tests()
    monkeypatch.setattr(song_io, "_SONG_HEADER_CACHE_PATH", str(cache_path))

    open_calls = {"song": 0}
    real_open = open
    song_abspath = os.path.abspath(song_path)

    def _counting_open(path, *args, **kwargs):
        if os.path.abspath(path) == song_abspath:
            open_calls["song"] += 1
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _counting_open)

    first = song_io.scan_song_header(str(song_path))
    song_io._flush_song_header_cache()
    song_io._reset_song_header_cache_for_tests()

    second = song_io.scan_song_header(str(song_path))

    assert first == second
    assert first["Song Name"] == "Cache Test Song"
    assert open_calls["song"] == 1
