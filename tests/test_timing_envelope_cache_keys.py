import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_song_cache_key
from tests.songs_support import make_song


def _song(header=None):
    return make_song(
        np.array([0.0, 0.5, 1.0]),
        name="Timing Envelope Cache Song",
        primary="Beat",
        secondary="Vibe",
        header=header,
    )


def test_timeline_and_fg_cache_keys_are_stable_for_identical_chart_inputs() -> None:
    song_a = _song()
    song_b = _song()

    assert song_a is not song_b
    assert song_a.timeline_key == song_b.timeline_key
    assert fg_response_frontier_song_cache_key(song_a) == fg_response_frontier_song_cache_key(song_b)


def test_timeline_cache_key_ignores_unkeyed_header_fields() -> None:
    song_a = _song({"TimelineAnalysisMaxWindows": "0"})
    song_b = _song({"TimelineAnalysisMaxWindows": "3"})

    assert song_a.timeline_key == song_b.timeline_key
