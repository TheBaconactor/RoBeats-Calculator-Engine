"""The FG group-row builder's scratch is module-global, so it must be owner-serialized.

The host application reaches this through a thread pool, which is how production hit
`TaichiRuntimeError: Field builder ... is not finalized`: two threads interleaved FieldsBuilder
placement. The crash was the visible half -- the quiet half is that two threads sharing the
per-candidate scratch slabs can swap rows between callers.

Kernel-free on purpose: the guard is host-side control flow, so it is testable without Vulkan.
"""
import threading
import time

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem import runtime
from gear_optimizer.solver.taichi_gem.force_greats import response_group_build_kernels as mod


class _Cell:
    """Stands in for a 1-D Taichi field: indexable, and reports a fixed keep count."""

    def __init__(self, count: int) -> None:
        self._values: dict[int, int] = {}
        self._count = count

    def __getitem__(self, key: int) -> int:
        return self._values.get(key, 0)

    def __setitem__(self, key: int, value: int) -> None:
        self._values[key] = value

    def to_numpy(self) -> np.ndarray:
        return np.ones((self._count,), dtype=np.int32)


def test_group_row_build_is_serialized_across_threads(monkeypatch):
    inside = 0
    overlaps = 0

    def kernel(*_args, **_kwargs):
        nonlocal inside, overlaps
        inside += 1
        if inside > 1:
            overlaps += 1
        # sleep() drops the GIL, so without the guard the other threads really do get in here.
        time.sleep(0.02)
        inside -= 1

    monkeypatch.setattr(mod, "_ensure_fields", lambda: None)
    monkeypatch.setattr(mod, "_fg_count_group_rows_kernel", kernel)
    monkeypatch.setattr(mod, "_fg_emit_group_rows_kernel", kernel)
    monkeypatch.setattr(mod, "ti", type("_Ti", (), {"sync": staticmethod(lambda: None)}))
    monkeypatch.setattr(mod, "_err", _Cell(1))
    monkeypatch.setattr(mod, "_kc", _Cell(1))
    monkeypatch.setattr(mod, "_wb", _Cell(1))

    def build():
        return mod.build_response_group_rows_gpu(
            base_components=np.zeros((1, 8), dtype=np.int32),
            ft_values=np.zeros((1,), dtype=np.int32),
            ff_values=np.zeros((1,), dtype=np.int32),
            residual_values=np.zeros((1,), dtype=np.int32),
            frontier_idx_by_stat=np.zeros((1, 1), dtype=np.int32),
            primary_ftff_delta_values=np.zeros((1,), dtype=np.int32),
            secondary_ftff_delta_values=np.zeros((1,), dtype=np.int32),
            score_elements_constant=True,
            head_len=1,
            body_total=1,
        )

    errors: list[BaseException] = []

    def run():
        try:
            build()
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)

    assert not errors, errors
    assert overlaps == 0, f"{overlaps} threads were inside the owner section at once"


def test_owner_lock_is_the_runtime_lock_and_reentrant():
    # Vulkan recovery calls reset_taichi from inside owner work, and reset_taichi takes this same
    # lock -- a plain Lock would self-deadlock there.
    lock = runtime.taichi_runtime_lock()
    assert lock is runtime._ti_lock
    with lock:
        assert lock.acquire(blocking=False), "owner lock must be reentrant"
        lock.release()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
