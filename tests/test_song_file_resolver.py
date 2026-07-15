from importlib import import_module

from gear_optimizer.data.song_io import SongFileResolver


def _write_song(path, *, song_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"Song Name\t{song_name}\n"
        "Primary Color\tRush\n"
        "Secondary Color\tFlow\n"
        "Difficulty\tHard\n"
        "Song Data\n",
        encoding="utf-8",
    )


def test_song_file_resolver_uses_header_name_when_filename_differs(tmp_path) -> None:
    song_file = tmp_path / "Data" / "Hard" / "website-upload.txt"
    _write_song(song_file, song_name="Custom Song (Hard) by User")

    resolver = SongFileResolver(tmp_path / "Data")

    assert resolver.resolve("Custom Song (Hard) by User") == song_file.resolve()
    assert resolver.resolve("missing") is None


def test_db_comparator_imports_current_song_resolver() -> None:
    module = import_module("tools.db.compare_overall_best_to_legacy_db")

    assert module.SongFileResolver is SongFileResolver
