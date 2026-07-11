from __future__ import annotations

import numpy as np

from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices


def _timeline_transitions(fn) -> list[int]:
    # Boundary from In Time (Hard): the old on-disk Numba kernel kept four same-time events in
    # fever even though the current source formula ends before their 56.752s timestamp.
    timestamps = np.asarray(
        [20.163] * 133
        + [56.597] * 365
        + [56.752] * 4
        + [56.907 + i * 0.155 for i in range(688)],
        dtype=np.float32,
    )
    mask = np.zeros(timestamps.size, dtype=np.bool_)
    fn(
        timestamps,
        int(timestamps.size),
        0.4266503765,
        2.318051911,
        256,
        104.194,
        mask,
    )
    return np.flatnonzero(mask[1:] != mask[:-1]).tolist()


def test_cached_fever_kernel_matches_current_python_formula() -> None:
    assert _timeline_transitions(calculate_fever_timeline_indices) == _timeline_transitions(
        calculate_fever_timeline_indices.py_func
    )
