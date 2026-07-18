from tools.db.compare_overall_best_to_legacy_db import _song_file_from_name, _song_path_index


def test_song_file_fallback_indexes_chart_headers(tmp_path):
    chart = tmp_path / "Data" / "Normal" / "filename-does-not-match.txt"
    chart.parent.mkdir(parents=True)
    chart.write_text(
        "Song Name\tCanonical Song by Artist\n"
        "Primary Color\tRush\n"
        "Secondary Color\tFlow\n"
        "Difficulty\tNormal\n"
        "Song Data\n",
        encoding="utf-8",
    )

    _song_path_index.cache_clear()
    assert _song_file_from_name(tmp_path, "Canonical Song by Artist") == chart
