from __future__ import annotations

from pathlib import Path

import pytest

from tools.db.repair_db_scores_vs_gpu import _build_song_header_index


def _write_chart(path: Path, song_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"Song Name\t{song_name}\n"
        "Primary Color\tRush\n"
        "Difficulty\tHard\n"
        "Song Data\n",
        encoding="utf-8",
    )


def test_song_header_index_resolves_canonical_name_independent_of_filename(
    tmp_path: Path,
) -> None:
    chart = tmp_path / "Data" / "Hard" / "chart-706.txt"
    _write_chart(chart, "Canonical Song (Hard) by Example")

    index = _build_song_header_index(tmp_path, "Hard")

    assert index == {"Canonical Song (Hard) by Example": chart}


def test_song_header_index_rejects_duplicate_canonical_names(tmp_path: Path) -> None:
    chart_dir = tmp_path / "Data" / "Hard"
    _write_chart(chart_dir / "one.txt", "Duplicate Song (Hard) by Example")
    _write_chart(chart_dir / "two.txt", "Duplicate Song (Hard) by Example")

    with pytest.raises(ValueError, match="Duplicate Song Name header"):
        _build_song_header_index(tmp_path, "Hard")
