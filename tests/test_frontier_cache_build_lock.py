"""CPU tests for the cross-process single-builder frontier cache lock.

The lock serializes the multi-GB cold build so two concurrent ``main.py`` processes do not duplicate
work or multiply peak RAM (the 2026-07-02 "Unable to allocate memory" incident). These exercise the
race (two threads contending on a tmp cache dir) and the fail-loud stale-lock break (dead pid /
stale heartbeat), all without GPU/Taichi.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from gear_optimizer.solver import frontier_cache_build_lock as lock_mod
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock, _LOCK_FILE_NAME


def test_two_threads_racing_the_lock_never_hold_it_concurrently(tmp_path: Path) -> None:
    """Two threads racing the same cache dir must serialize: at no instant do both hold the lock,
    and both eventually run their critical section."""
    concurrency = {"current": 0, "max": 0}
    order: list[str] = []
    mu = threading.Lock()
    start = threading.Barrier(2)

    def worker(name: str) -> None:
        start.wait()
        with FrontierBuildLock(tmp_path, label="test"):
            with mu:
                concurrency["current"] += 1
                concurrency["max"] = max(concurrency["max"], concurrency["current"])
                order.append(name)
            # Hold the critical section long enough that a broken lock would overlap.
            time.sleep(0.2)
            with mu:
                concurrency["current"] -= 1

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert concurrency["max"] == 1, "both threads held the build lock at once"
    assert len(order) == 2
    # Lock file is cleaned up after both release.
    assert not (tmp_path / _LOCK_FILE_NAME).exists()


def test_stale_lock_from_dead_pid_is_broken(tmp_path: Path, monkeypatch) -> None:
    """A lock owned by a pid that is no longer alive is fail-loud broken, not silently waited on."""
    lock_path = tmp_path / _LOCK_FILE_NAME
    dead_pid = 424242
    lock_path.write_text(
        json.dumps({"pid": dead_pid, "token": "dead-owner", "heartbeat_ns": int(time.time_ns())}),
        encoding="utf-8",
    )
    monkeypatch.setattr(lock_mod, "_pid_alive", lambda pid: pid != dead_pid)

    acquired = threading.Event()

    def worker() -> None:
        with FrontierBuildLock(tmp_path, label="test"):
            acquired.set()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert acquired.is_set(), "acquire did not break a lock owned by a dead pid"
    assert not lock_path.exists()


def test_stale_lock_from_frozen_heartbeat_is_broken(tmp_path: Path, monkeypatch) -> None:
    """A lock whose owner is 'alive' but whose heartbeat stopped advancing past the stale window is
    broken -- covers a hung (not crashed) owner."""
    monkeypatch.setattr(lock_mod, "_HEARTBEAT_STALE_S", 1.0)
    monkeypatch.setattr(lock_mod, "_pid_alive", lambda pid: True)

    lock_path = tmp_path / _LOCK_FILE_NAME
    frozen_heartbeat_ns = int(time.time_ns()) - int(5.0 * 1e9)
    lock_path.write_text(
        json.dumps({"pid": os.getpid(), "token": "frozen-owner", "heartbeat_ns": frozen_heartbeat_ns}),
        encoding="utf-8",
    )

    with FrontierBuildLock(tmp_path, label="test"):
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        assert int(owner["heartbeat_ns"]) > frozen_heartbeat_ns, "stale heartbeat lock was not reclaimed"
    assert not lock_path.exists()


def test_live_owner_lock_is_waited_on_not_broken(tmp_path: Path, monkeypatch) -> None:
    """A fresh lock from a live owner must NOT be broken: a waiter parks until it is released."""
    monkeypatch.setattr(lock_mod, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(lock_mod, "_POLL_INTERVAL_S", 0.02)

    lock_path = tmp_path / _LOCK_FILE_NAME
    lock_path.write_text(
        json.dumps({"pid": 999999, "token": "live-owner", "heartbeat_ns": int(time.time_ns())}),
        encoding="utf-8",
    )

    acquired = threading.Event()

    def worker() -> None:
        with FrontierBuildLock(tmp_path, label="test"):
            acquired.set()

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        # The live-owner lock is still held, so the waiter must not acquire.
        assert not acquired.wait(timeout=0.5), "waiter broke a live owner's lock"
        # Owner releases -> waiter proceeds.
        lock_path.unlink()
        assert acquired.wait(timeout=10), "waiter did not acquire after the lock was released"
    finally:
        thread.join(timeout=10)
        assert not thread.is_alive()


def test_broken_out_owner_cannot_clobber_or_delete_new_holders_lock(tmp_path: Path, monkeypatch) -> None:
    """Reviewer regression: an owner whose lock is broken as stale must not, on resuming, recreate or
    replace the new holder's lock via its heartbeat, nor delete it on release.

    Sequence: holder A acquires; A's heartbeat stalls (thread stopped, but A stays 'alive' with its
    fd open, simulating a paged-out process); waiter B judges A stale, breaks it, and acquires a
    fresh lock; A resumes and fires a heartbeat, then releases. Throughout, the on-disk lock must
    remain B's."""
    monkeypatch.setattr(lock_mod, "_pid_alive", lambda pid: True)  # same-pid threads: force 'alive'
    monkeypatch.setattr(lock_mod, "_HEARTBEAT_STALE_S", 0.0)  # any non-refreshed heartbeat is stale

    lock_path = tmp_path / _LOCK_FILE_NAME

    holder_a = FrontierBuildLock(tmp_path, label="A")
    holder_a._acquire()
    # Simulate A's heartbeat stalling: stop the thread but keep A 'alive' with its fd open and unreleased.
    holder_a._stop.set()
    if holder_a._heartbeat_thread is not None:
        holder_a._heartbeat_thread.join(timeout=5)
    assert json.loads(lock_path.read_text(encoding="utf-8"))["token"] == holder_a._token

    # B breaks A's stale lock and acquires its own.
    holder_b = FrontierBuildLock(tmp_path, label="B")
    holder_b._acquire()
    assert json.loads(lock_path.read_text(encoding="utf-8"))["token"] == holder_b._token

    try:
        # A resumes and fires one more heartbeat: it must land on A's orphaned inode, not B's lock.
        holder_a._emit_heartbeat()
        assert (
            json.loads(lock_path.read_text(encoding="utf-8"))["token"] == holder_b._token
        ), "a broken-out owner's heartbeat clobbered the new holder's lock"

        # A releases: it must not delete B's lock (token gate).
        holder_a._release()
        assert lock_path.exists(), "a broken-out owner's release deleted the new holder's lock"
        assert json.loads(lock_path.read_text(encoding="utf-8"))["token"] == holder_b._token
    finally:
        holder_b._release()
    assert not lock_path.exists()
