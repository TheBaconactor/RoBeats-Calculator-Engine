import pytest


def _has_taichi() -> bool:
    try:
        import taichi  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_prefetch_key_is_tuple_and_stable():
    from gear_optimizer.solver.taichi_gem.api.gpu_prefetch import GPUPrefetchManager

    mgr = GPUPrefetchManager(num_slots=1)
    ref_arrays = {}
    calc_song = {
        "metadata": {
            "Song Name": "SongA",
            "Difficulty": "Hard",
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": [0.01, 0.02, 0.03]},
    }

    key1 = mgr._make_song_key(calc_song, ref_arrays)
    key2 = mgr._make_song_key(calc_song, ref_arrays)

    calc_song_other = {
        "metadata": calc_song["metadata"],
        "song_data": {"timestamps": [0.01, 0.02, 0.031]},
    }
    key3 = mgr._make_song_key(calc_song_other, ref_arrays)

    assert isinstance(key1, tuple)
    assert isinstance(key1[-1], bytes)
    assert key1 == key2
    assert key1 != key3
