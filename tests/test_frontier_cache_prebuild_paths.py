from __future__ import annotations

from pathlib import Path


def test_frontier_cache_prebuild_uses_queue_scope_when_queue_is_present(tmp_path: Path) -> None:
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths

    queued = tmp_path / "queued.txt"
    queued.write_text("Song Name\tQueued\n", encoding="utf-8")
    data_song = tmp_path / "Data" / "Hard" / "global.txt"
    data_song.parent.mkdir(parents=True)
    data_song.write_text("Song Name\tGlobal\n", encoding="utf-8")

    paths = ordered_frontier_cache_song_paths(queue_paths=(str(queued),), data_root=tmp_path / "Data")

    assert paths == [str(queued)]


def test_frontier_cache_prebuild_scans_data_when_queue_is_empty(tmp_path: Path) -> None:
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths

    data_song = tmp_path / "Data" / "Hard" / "global.txt"
    data_song.parent.mkdir(parents=True)
    data_song.write_text("Song Name\tGlobal\n", encoding="utf-8")

    paths = ordered_frontier_cache_song_paths(queue_paths=(), data_root=tmp_path / "Data")

    assert paths == [str(data_song)]
