import numpy as np
import pytest

from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs


def test_extract_fg_song_inputs_requires_floor_with_timing_candidates() -> None:
    timestamps = np.asarray([0.0, 1.0], dtype=np.float32)
    calc_song = {
        "metadata": {"Long Notes": 0, "Last Note Time": 1.0},
        "song_data": {
            "timestamps": timestamps,
            "fg_timestamps": timestamps,
            "fg_perfect_candidate_timestamps": timestamps + np.float32(0.04),
        },
    }

    with pytest.raises(ValueError, match="fg_perfect_floor_timestamps"):
        extract_fg_song_inputs(calc_song)


def test_extract_fg_song_inputs_accepts_explicit_degenerate_floor() -> None:
    timestamps = np.asarray([0.0, 1.0], dtype=np.float32)
    calc_song = {
        "metadata": {"Long Notes": 0, "Last Note Time": 1.0},
        "song_data": {
            "timestamps": timestamps,
            "fg_timestamps": timestamps,
            "fg_perfect_candidate_timestamps": timestamps,
            "fg_perfect_floor_timestamps": timestamps,
        },
    }

    song_inputs = extract_fg_song_inputs(calc_song)

    assert np.array_equal(np.asarray(song_inputs.perfect_floor, dtype=np.float32), timestamps)
