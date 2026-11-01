"""offline_cache_lock across processes: a second process waits for the holder and then takes the lock (Windows: it
never reads the byte the holder has locked, a read that fails with PermissionError)."""

import multiprocessing
import time

from gear_optimizer.solver.taichi_gem import runtime


def _hold(held, release) -> None:
    with runtime.offline_cache_lock():
        held.set()
        release.wait(60)


def _take(trying, out) -> None:
    trying.set()
    started = time.monotonic()
    try:
        with runtime.offline_cache_lock():
            out.put(time.monotonic() - started)
    except Exception as exc:
        out.put(repr(exc))


def test_a_second_process_waits_for_the_holder_then_takes_the_lock():
    ctx = multiprocessing.get_context("spawn")
    held, release, trying, out = ctx.Event(), ctx.Event(), ctx.Event(), ctx.Queue()
    holder = ctx.Process(target=_hold, args=(held, release))
    holder.start()
    try:
        assert held.wait(60)
        taker = ctx.Process(target=_take, args=(trying, out))
        taker.start()
        assert trying.wait(60)
        time.sleep(0.5)
        assert out.empty(), out.get()  # still waiting while the holder has the lock
        release.set()
        waited = out.get(timeout=60)
        taker.join(60)
    finally:
        release.set()
        holder.join(60)
    assert isinstance(waited, float) and waited >= 0.5, waited
    assert holder.exitcode == 0 and taker.exitcode == 0
