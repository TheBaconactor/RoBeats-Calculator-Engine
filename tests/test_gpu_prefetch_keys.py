from tests.curves_support import synthetic_curves
from tests.songs_support import make_song


def test_timeline_slot_cache_key_is_tuple_and_stable():
    from gear_optimizer.solver.taichi_gem.api.initialization import _curves_sig

    def _timeline_slot_key(song, curves) -> tuple:
        return song.timeline_key + (bytes(_curves_sig(curves)),)

    curves = synthetic_curves({})
    key1 = _timeline_slot_key(make_song([0.01, 0.02, 0.03], name="SongA", lanes=[0, 1, 0]), curves)
    key2 = _timeline_slot_key(make_song([0.01, 0.02, 0.03], name="SongA", lanes=[0, 1, 0]), curves)
    key3 = _timeline_slot_key(make_song([0.01, 0.02, 0.031], name="SongA", lanes=[0, 1, 0]), curves)
    key4 = _timeline_slot_key(make_song([0.01, 0.02, 0.03], name="SongA", lanes=[0, 0, 1]), curves)

    assert isinstance(key1, tuple)
    assert isinstance(key1[-1], bytes)
    assert key1 == key2
    assert key1 != key3
    assert key1 != key4
