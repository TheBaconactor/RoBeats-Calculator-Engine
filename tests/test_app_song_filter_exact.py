from __future__ import annotations

from gear_optimizer.app import _song_name_matches_exact_filter


def test_song_name_exact_filter_matches_short_title_before_difficulty_and_artist() -> None:
    assert _song_name_matches_exact_filter("00 (Hard) by garlagan", "00")


def test_song_name_exact_filter_does_not_treat_substring_as_exact_title() -> None:
    assert not _song_name_matches_exact_filter(
        "Exit This Earth's Atomosphere (Camellia's 'Planetary//200step' Remix) [EXTENDED CUT] (Hard) by Camellia",
        "00",
    )


def test_song_name_exact_filter_leaves_broad_substring_queries_to_fallback() -> None:
    assert not _song_name_matches_exact_filter("Afflict (Hard) by Laur [LAUR1200] feat. Risa Yuzuki", "laur")
