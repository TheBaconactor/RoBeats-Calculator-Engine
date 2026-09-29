"""The CPU FG gem search split across cores equals one serial call, and releases the GIL."""

import threading
import time

import numpy as np

from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host as host


def _random_batch(group_count: int, seed: int, colors=("Chill", "Flow", "Chill")):
    rng = np.random.default_rng(seed)
    lengths = rng.integers(1, 9, group_count).astype(np.int64)
    offsets = np.concatenate(([0], np.cumsum(lengths)[:-1])).astype(np.int64)
    surface_rows = int(lengths.sum())
    meta = np.column_stack(
        [
            rng.integers(0, 25, group_count),  # residual gem budget
            rng.integers(0, 161, group_count),  # perfect points
            rng.integers(0, 161, group_count),  # combo multiplier
            rng.integers(0, 161, group_count),  # fever multiplier
            rng.integers(0, 200, group_count),  # primary
            rng.integers(0, 120, group_count),  # secondary
            np.full(group_count, 100),  # head length (one per batch)
            np.full(group_count, 120),  # body total
        ]
    ).astype(np.int32)
    patterns = 16
    words = rng.integers(0, 2**32, (patterns, 8), dtype=np.uint32)
    counts = np.column_stack(
        [rng.integers(0, 121, surface_rows), rng.integers(0, 60, surface_rows), rng.integers(0, 40, surface_rows)]
    ).astype(np.int32)
    refs = get_exact_replay_ref_arrays_cached()
    shared = (
        rng.integers(0, patterns, surface_rows).astype(np.int32),
        words,
        counts,
        host._precompute_surface_head_coeffs(words, head_len=100),
        np.array(host._color_flags(*colors), dtype=np.int32),
        np.ascontiguousarray(refs["Perfect Points"], dtype=np.float64),
        np.ascontiguousarray(refs["Combo Multiplier"], dtype=np.float64),
        np.ascontiguousarray(refs["Fever Multiplier"], dtype=np.float64),
        True,
        160,
    )
    return offsets, lengths, meta, shared


def test_parallel_search_equals_one_serial_call():
    for group_count, seed in ((1, 1), (7, 2), (33, 3), (257, 4), (1000, 5)):
        offsets, lengths, meta, shared = _random_batch(group_count, seed)
        serial = host._score_fg_response_groups_native_f64(offsets, lengths, meta, *shared)
        parallel = host._score_fg_response_groups_on_cpu_cores(offsets, lengths, meta, shared)
        np.testing.assert_array_equal(parallel, serial)


def test_search_kernel_releases_the_gil():
    offsets, lengths, meta, shared = _random_batch(20000, 9)
    host._score_fg_response_groups_native_f64(offsets[:2], lengths[:2], meta[:2], *shared)  # compile
    done = threading.Event()
    kernel = {}

    def run_kernel():
        kernel["start"] = time.perf_counter()
        host._score_fg_response_groups_native_f64(offsets, lengths, meta, *shared)
        kernel["stop"] = time.perf_counter()
        done.set()

    worker = threading.Thread(target=run_kernel)
    longest_gap = 0.0
    last = time.perf_counter()
    worker.start()
    while not done.is_set():
        now = time.perf_counter()
        if "start" in kernel:
            longest_gap = max(longest_gap, now - last)
        last = now
    worker.join()
    kernel_seconds = kernel["stop"] - kernel["start"]
    # A GIL-holding kernel starves this thread for its whole run; a nogil one only for a switch.
    assert kernel_seconds > 0.05
    assert longest_gap < kernel_seconds / 2
