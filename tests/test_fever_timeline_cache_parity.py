from __future__ import annotations

import numpy as np

from gear_optimizer.solver.fever_timeline import (
    calculate_fever_timeline_indices,
    calculate_fever_timeline_surface_grid,
)


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


def test_batched_surface_grid_matches_every_canonical_scalar_cell() -> None:
    timestamps = np.round(np.arange(137, dtype=np.float32) * np.float32(0.137), 4)
    ft_factors = np.asarray([0.31, 0.73, 1.19, 1.87], dtype=np.float32)
    ff_factors = np.asarray([0.29, 0.61, 0.94, 1.43, 2.05], dtype=np.float32)
    shape = (len(ft_factors), len(ff_factors))
    body_fever = np.zeros(shape, dtype=np.int32)
    body_normal = np.zeros(shape, dtype=np.int32)
    mask_words = np.full((*shape, 4), np.iinfo(np.uint32).max, dtype=np.uint32)
    activations = np.zeros(shape, dtype=np.int32)
    last_end = np.zeros(shape, dtype=np.int32)

    calculate_fever_timeline_surface_grid(
        timestamps,
        len(timestamps),
        ft_factors,
        ff_factors,
        11,
        float(timestamps[-1]),
        body_fever,
        body_normal,
        mask_words,
        activations,
        last_end,
    )

    mask_buffer = np.zeros(len(timestamps), dtype=np.bool_)
    for ft_idx, ft_factor in enumerate(ft_factors):
        for ff_idx, ff_factor in enumerate(ff_factors):
            head, scalar_fever, scalar_normal, scalar_activations, scalar_last_end = (
                calculate_fever_timeline_indices(
                    timestamps,
                    len(timestamps),
                    float(ff_factor),
                    float(ft_factor),
                    11,
                    float(timestamps[-1]),
                    mask_buffer,
                )
            )
            scalar_words = np.zeros(4, dtype=np.uint32)
            for note_idx in np.flatnonzero(head):
                scalar_words[note_idx // 32] |= np.uint32(1) << np.uint32(note_idx % 32)
            assert body_fever[ft_idx, ff_idx] == scalar_fever
            assert body_normal[ft_idx, ff_idx] == scalar_normal
            assert activations[ft_idx, ff_idx] == scalar_activations
            assert last_end[ft_idx, ff_idx] == scalar_last_end
            np.testing.assert_array_equal(mask_words[ft_idx, ff_idx], scalar_words)
