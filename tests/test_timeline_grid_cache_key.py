import numpy as np


def test_song_timeline_grid_cache_key_uses_timing_envelope_context():
    from gear_optimizer.solver.fever_timeline import SONG_TIMELINE_GRIDS, get_song_timeline_grid
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    SONG_TIMELINE_GRIDS.clear()

    ref_arrays = {
        "Fever Time": np.ones(161, dtype=np.float32),
        "Fever Fill Rate": np.ones(161, dtype=np.float32),
    }
    timestamps = np.array([0.0, 0.1, 0.2], dtype=np.float64)

    calc_song1 = {
        "metadata": {
            "Song Name": "CacheKey Song",
            "Last Note Time": 0.2,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "chart_timestamps": timestamps.copy(),
            "note_types": np.ones(timestamps.shape[0], dtype=np.int16),
        },
    }
    calc_song2 = {
        "metadata": {
            "Song Name": "CacheKey Song",
            "Last Note Time": 0.2,
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "chart_timestamps": timestamps.copy(),
            "note_types": np.ones(timestamps.shape[0], dtype=np.int16),
        },
    }
    apply_timing_envelope(calc_song1)
    apply_timing_envelope(calc_song2)

    grid1 = get_song_timeline_grid(calc_song1, ref_arrays)
    grid1_again = get_song_timeline_grid(calc_song1, ref_arrays)
    grid2 = get_song_timeline_grid(calc_song2, ref_arrays)

    assert grid1 is grid1_again
    assert grid1 is grid2
    assert getattr(grid1, "cache_key", None) == getattr(grid2, "cache_key", None)
