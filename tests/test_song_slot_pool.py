import pytest

from gear_optimizer.solver.song_slot_pool import SongSlotPool


def test_song_slot_pool_reserves_zero_and_reuses_released_slots():
    pool = SongSlotPool(max_song_slots=3)

    first = pool.acquire()
    second = pool.acquire()

    assert first == 1
    assert second == 2
    with pytest.raises(RuntimeError, match="No free GPU song slots"):
        pool.acquire()

    pool.release(first)
    assert pool.acquire() == first


def test_song_slot_pool_ignores_zero_release():
    pool = SongSlotPool(max_song_slots=2)
    assert pool.acquire() == 1

    pool.release(0)
    with pytest.raises(RuntimeError, match="No free GPU song slots"):
        pool.acquire()
