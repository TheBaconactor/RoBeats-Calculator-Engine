import numpy as np

from tests.songs_support import make_song


def test_precise_fg_inputs_carry_the_timing_envelopes() -> None:
    song = make_song([0.0, 0.5, 1.0], note_types=[1, 2, 3], lanes=[0, 1, 1], long_notes=1, last_note_time=1.2)

    inputs = song.fg_inputs

    assert inputs.timestamps is song.hit_timestamps
    assert inputs.perfect_candidates is song.perfect_candidates
    assert inputs.great_candidates is song.great_candidates
    assert inputs.perfect_floor is song.perfect_floor
    assert inputs.great_floor is song.great_floor
    assert inputs.use_forced_great_timing is True
    assert np.array_equal(inputs.lanes, [0, 1, 1])
    assert (inputs.total_notes, inputs.long_notes, inputs.last_note_time) == (3, 1, 1.2)
    assert (inputs.primary_color, inputs.secondary_color) == ("Rush", "Flow")


def test_non_precise_fg_inputs_use_the_hit_timeline_without_carry() -> None:
    song = make_song([0.0, 0.5, 1.0], mode="non-precise")

    inputs = song.fg_inputs

    for stream in (inputs.perfect_candidates, inputs.great_candidates, inputs.perfect_floor, inputs.great_floor):
        assert stream is song.hit_timestamps
    assert inputs.use_forced_great_timing is False
