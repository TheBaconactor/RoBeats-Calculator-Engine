def test_timeline_slot_cache_key_is_tuple_and_stable():
    from gear_optimizer.solver.taichi_gem.api.initialization import _curves_sig
    from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key

    def _timeline_slot_key(calc_song: dict, curves: dict) -> tuple:
        return _song_timing_cache_key(calc_song) + (bytes(_curves_sig(curves)),)

    curves = {}
    calc_song = {
        "metadata": {
            "Song Name": "SongA",
            "Difficulty": "Hard",
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {
            "timestamps": [0.01, 0.02, 0.03],
            "note_types": [1, 1, 1],
            "lanes": [0, 1, 0],
        },
    }

    key1 = _timeline_slot_key(calc_song, curves)
    key2 = _timeline_slot_key(calc_song, curves)

    calc_song_other = {
        "metadata": calc_song["metadata"],
        "song_data": {
            "timestamps": [0.01, 0.02, 0.031],
            "note_types": [1, 1, 1],
            "lanes": [0, 1, 0],
        },
    }
    key3 = _timeline_slot_key(calc_song_other, curves)
    calc_song_other_lanes = {
        "metadata": calc_song["metadata"],
        "song_data": {
            "timestamps": [0.01, 0.02, 0.03],
            "note_types": [1, 1, 1],
            "lanes": [0, 0, 1],
        },
    }
    key4 = _timeline_slot_key(calc_song_other_lanes, curves)

    assert isinstance(key1, tuple)
    assert isinstance(key1[-1], bytes)
    assert key1 == key2
    assert key1 != key3
    assert key1 != key4
