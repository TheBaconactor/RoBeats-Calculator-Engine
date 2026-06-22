from __future__ import annotations

import threading
import time

import numpy as np


def test_cpu_response_search_serializes_concurrent_thread_entry(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host

    current = 0
    max_concurrent = 0
    state_lock = threading.Lock()
    start_gate = threading.Event()

    def _fake_resolve(*_args, **_kwargs):
        nonlocal current, max_concurrent
        with state_lock:
            current += 1
            max_concurrent = max(max_concurrent, current)
        try:
            time.sleep(0.05)
            return np.zeros((1, 11), dtype=np.int64)
        finally:
            with state_lock:
                current -= 1

    monkeypatch.setattr(response_inner_host, "resolve_fg_response_groups_native_f64", _fake_resolve)

    kwargs = {
        "group_meta": np.zeros((1, 8), dtype=np.int32),
        "group_offsets": np.zeros((1,), dtype=np.int64),
        "group_lengths": np.ones((1,), dtype=np.int64),
        "primary_color": "Chill",
        "secondary_color": "Chill",
        "selected_color": "Chill",
        "ref_arrays": {
            "Perfect Points": np.ones((4,), dtype=np.float64),
            "Combo Multiplier": np.ones((4,), dtype=np.float64),
            "Fever Multiplier": np.ones((4,), dtype=np.float64),
            "Fever Fill Rate": np.ones((4,), dtype=np.float64),
            "Fever Time": np.ones((4,), dtype=np.float64),
        },
        "surface_words": np.zeros((1, 8), dtype=np.uint32),
        "surface_counts": np.zeros((1, 3), dtype=np.int32),
    }

    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            start_gate.wait(timeout=2.0)
            response_inner_host._score_response_group_meta_cpu(**kwargs)
        except BaseException as exc:  # pragma: no cover - surfaced by assertion
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    start_gate.set()
    for thread in threads:
        thread.join(timeout=2.0)
        assert not thread.is_alive()

    assert errors == []
    assert max_concurrent == 1
