"""Batched Vulkan probe for the current exact packet-monoid union.

The abandoned FG Vulkan port evaluated the older per-action body recurrence.  The
current CPU prebuilder instead maintains sliding packet queues whose aggregates are
Pareto unions of packet points.  This research probe assigns one cooperative Vulkan
workgroup to each independent union and one candidate row to each active lane.

Both inputs are already nondominated frontiers.  Therefore a left row only needs to
test right rows, and a right row only needs to test left rows: same-side comparisons
cannot remove anything.  Equal cross-side rows keep the earlier left ordinal.  This
O(L*R) cross-dominance predicate is equivalent to the production incremental
reject-before-evict union and preserves survivor order.

Timed buffers stay device-resident.  Host transfers and JIT compilation are excluded.
The CPU comparison calls the production ``_numba_packet_union`` implementation from a
parallel Numba batch wrapper so all useful CPU cores participate.
"""

import argparse
import os
import sys
import time

import numpy as np
from numba import njit, prange, set_num_threads

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as _nb
from gear_optimizer.solver.taichi_gem.runtime import init_taichi

init_taichi()

import taichi as ti  # noqa: E402


_MAX_SIDE = 256
_MAX_TOTAL = 2 * _MAX_SIDE


@njit(cache=True, nogil=True, parallel=True)
def _cpu_production_packet_union_batch_clean(
    left,
    left_counts,
    right,
    right_counts,
    scratch,
    output,
    output_counts,
):
    for batch in prange(left.shape[0]):
        code, start, end = _nb._numba_packet_union(
            left[batch],
            0,
            int(left_counts[batch]),
            right[batch],
            0,
            int(right_counts[batch]),
            scratch[batch],
            0,
        )
        if int(code) == 1:
            count = int(left_counts[batch])
            for idx in range(count):
                output[batch, idx, 0] = left[batch, idx, 0]
                output[batch, idx, 1] = left[batch, idx, 1]
                output[batch, idx, 2] = left[batch, idx, 2]
        elif int(code) == 2:
            count = int(right_counts[batch])
            for idx in range(count):
                output[batch, idx, 0] = right[batch, idx, 0]
                output[batch, idx, 1] = right[batch, idx, 1]
                output[batch, idx, 2] = right[batch, idx, 2]
        else:
            count = int(end) - int(start)
            for idx in range(count):
                output[batch, idx, 0] = scratch[batch, int(start) + idx, 0]
                output[batch, idx, 1] = scratch[batch, int(start) + idx, 1]
                output[batch, idx, 2] = scratch[batch, int(start) + idx, 2]
        output_counts[batch] = count


@ti.func
def _gpu_packet_coord(
    left: ti.template(),
    right: ti.template(),
    batch: ti.i32,
    left_count: ti.i32,
    row: ti.i32,
    coord: ti.i32,
) -> ti.i32:
    value = ti.i32(0)
    if row < left_count:
        value = left[batch, row, coord]
    else:
        value = right[batch, row - left_count, coord]
    return value


@ti.kernel
def _gpu_packet_union_batch(
    batch_count: ti.i32,
    left: ti.types.ndarray(dtype=ti.i32, ndim=3),
    left_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    right: ti.types.ndarray(dtype=ti.i32, ndim=3),
    right_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    output: ti.types.ndarray(dtype=ti.i32, ndim=3),
    output_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    ti.loop_config(block_dim=64)
    for gid in range(batch_count * 64):
        batch = gid // 64
        thread = ti.simt.block.thread_idx()
        left_count = left_counts[batch]
        total = left_count + right_counts[batch]
        keep = ti.simt.block.SharedArray((_MAX_TOTAL,), ti.i32)

        row = thread
        while row < total:
            cf = _gpu_packet_coord(left, right, batch, left_count, row, 0)
            cn = _gpu_packet_coord(left, right, batch, left_count, row, 1)
            cq = _gpu_packet_coord(left, right, batch, left_count, row, 2)
            dominated = False
            if row < left_count:
                other = ti.i32(0)
                while other < right_counts[batch] and not dominated:
                    kf = right[batch, other, 0]
                    kn = right[batch, other, 1]
                    kq = right[batch, other, 2]
                    weakly_dominates = kf >= cf and kn <= cn and kq <= cq
                    strictly_dominates = kf > cf or kn < cn or kq < cq
                    if weakly_dominates and strictly_dominates:
                        dominated = True
                    other += 1
            else:
                other = ti.i32(0)
                while other < left_count and not dominated:
                    kf = left[batch, other, 0]
                    kn = left[batch, other, 1]
                    kq = left[batch, other, 2]
                    if kf >= cf and kn <= cn and kq <= cq:
                        dominated = True
                    other += 1
            keep[row] = 0 if dominated else 1
            row += 64
        ti.simt.block.sync()

        if thread == 0:
            write = ti.i32(0)
            for row_idx in range(total):
                if keep[row_idx] != 0:
                    output[batch, write, 0] = _gpu_packet_coord(
                        left, right, batch, left_count, row_idx, 0
                    )
                    output[batch, write, 1] = _gpu_packet_coord(
                        left, right, batch, left_count, row_idx, 1
                    )
                    output[batch, write, 2] = _gpu_packet_coord(
                        left, right, batch, left_count, row_idx, 2
                    )
                    write += 1
            output_counts[batch] = write


def _make_nondominated_side(
    rng: np.random.Generator,
    batch_count: int,
    width: int,
    fever_bias: int,
    normal_bias: int,
    fever_great_bias: int,
) -> np.ndarray:
    rows = np.zeros((batch_count, _MAX_SIDE, 3), dtype=np.int64)
    for batch in range(batch_count):
        # Increasing fever is traded against increasing penalties, so rows within
        # one side are mutually nondominating.  Jitter and permutation exercise
        # arbitrary producer order without violating that invariant.
        step = np.arange(width, dtype=np.int64)
        points = np.empty((width, 3), dtype=np.int64)
        points[:, 0] = fever_bias + step * 3 + rng.integers(0, 3, size=width)
        points[:, 1] = normal_bias + step * 2 + rng.integers(0, 2, size=width)
        points[:, 2] = fever_great_bias + step + rng.integers(0, 2, size=width)
        rows[batch, :width] = points[rng.permutation(width)]
    return rows


def _make_case(
    *,
    rng: np.random.Generator,
    batch_count: int,
    left_width: int,
    right_width: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not 0 < left_width <= _MAX_SIDE or not 0 < right_width <= _MAX_SIDE:
        raise ValueError(f"widths must be in [1, {_MAX_SIDE}]")
    left = _make_nondominated_side(rng, batch_count, left_width, 20, 10, 5)
    # Offset the second side both helpfully and harmfully so the union contains a
    # mixture of cross-side domination and true tradeoffs.
    right = _make_nondominated_side(rng, batch_count, right_width, 18, 8, 7)
    left_counts = np.full((batch_count,), left_width, dtype=np.int32)
    right_counts = np.full((batch_count,), right_width, dtype=np.int32)
    return left, left_counts, right, right_counts


def _device_i32(array: np.ndarray):
    device = ti.ndarray(ti.i32, shape=array.shape)
    device.from_numpy(np.asarray(array, dtype=np.int32))
    return device


def _gpu_sample_ms(callable_) -> float:
    started = time.perf_counter()
    callable_()
    ti.sync()
    return (time.perf_counter() - started) * 1_000.0


def _cpu_sample_ms(callable_) -> float:
    started = time.perf_counter()
    callable_()
    return (time.perf_counter() - started) * 1_000.0


def _paired_medians_ms(cpu_call, gpu_call, repetitions: int) -> tuple[float, float]:
    cpu_call()
    gpu_call()
    ti.sync()
    cpu_samples = []
    gpu_samples = []
    for repetition in range(repetitions):
        if repetition % 2 == 0:
            cpu_samples.append(_cpu_sample_ms(cpu_call))
            gpu_samples.append(_gpu_sample_ms(gpu_call))
        else:
            gpu_samples.append(_gpu_sample_ms(gpu_call))
            cpu_samples.append(_cpu_sample_ms(cpu_call))
    return (
        float(np.median(np.asarray(cpu_samples, dtype=np.float64))),
        float(np.median(np.asarray(gpu_samples, dtype=np.float64))),
    )


def _benchmark_arrays(
    label: str,
    left: np.ndarray,
    left_counts: np.ndarray,
    right: np.ndarray,
    right_counts: np.ndarray,
    repetitions: int,
) -> tuple[float, float]:
    batch_count = int(left.shape[0])
    cpu_scratch = np.empty((batch_count, _MAX_TOTAL, 3), dtype=np.int64)
    cpu_output = np.empty((batch_count, _MAX_TOTAL, 3), dtype=np.int64)
    cpu_counts = np.zeros((batch_count,), dtype=np.int64)

    cpu_call = lambda: _cpu_production_packet_union_batch_clean(
        left,
        left_counts,
        right,
        right_counts,
        cpu_scratch,
        cpu_output,
        cpu_counts,
    )

    left_device = _device_i32(left)
    left_counts_device = _device_i32(left_counts)
    right_device = _device_i32(right)
    right_counts_device = _device_i32(right_counts)
    gpu_output_device = ti.ndarray(
        ti.i32, shape=(batch_count, _MAX_TOTAL, 3)
    )
    gpu_counts_device = ti.ndarray(ti.i32, shape=(batch_count,))

    def gpu_call():
        _gpu_packet_union_batch(
            batch_count,
            left_device,
            left_counts_device,
            right_device,
            right_counts_device,
            gpu_output_device,
            gpu_counts_device,
        )

    # Interleaved same-session pairs; both JITs are warm before sampling.
    cpu_ms, gpu_ms = _paired_medians_ms(cpu_call, gpu_call, repetitions)

    cpu_call()
    gpu_call()
    ti.sync()
    gpu_output = gpu_output_device.to_numpy()
    gpu_counts = gpu_counts_device.to_numpy()
    if not np.array_equal(gpu_counts.astype(np.int64), cpu_counts):
        raise AssertionError(
            f"{label}: packet-union count mismatch: "
            f"cpu={cpu_counts[:8].tolist()} gpu={gpu_counts[:8].tolist()}"
        )
    for batch in range(batch_count):
        count = int(cpu_counts[batch])
        if not np.array_equal(
            gpu_output[batch, :count].astype(np.int64),
            cpu_output[batch, :count],
        ):
            raise AssertionError(f"{label}: ordered row mismatch in batch {batch}")

    print(
        f"{label:>21} batches={batch_count:5d}: "
        f"CPU(all cores)={cpu_ms:9.3f} ms  GPU={gpu_ms:9.3f} ms  "
        f"speedup={cpu_ms / gpu_ms:6.2f}x  rows={int(cpu_counts.sum()):,}"
    )
    return cpu_ms, gpu_ms


def _run_case(
    *,
    rng: np.random.Generator,
    left_width: int,
    right_width: int,
    batch_count: int,
    repetitions: int,
) -> tuple[float, float]:
    arrays = _make_case(
        rng=rng,
        batch_count=batch_count,
        left_width=left_width,
        right_width=right_width,
    )
    return _benchmark_arrays(
        f"width={left_width:3d}+{right_width:<3d}",
        *arrays,
        repetitions,
    )


_MEASURED_MONSTER_SHAPES = (
    (2219, 1, 1),
    (404, 1, 130),
    (94, 3, 124),
    (53, 2, 124),
    (51, 3, 39),
    (48, 3, 58),
    (47, 2, 58),
    (35, 4, 58),
    (27, 45, 3),
    (20, 1, 58),
    (19, 48, 3),
    (19, 44, 3),
    (17, 3, 130),
    (16, 42, 3),
    (16, 41, 3),
    (16, 3, 30),
    (15, 97, 3),
    (14, 104, 3),
    (13, 30, 3),
    (13, 125, 3),
    (13, 155, 3),
)


def _run_measured_monster_mix(
    rng: np.random.Generator, repetitions: int, repeats: int = 1
) -> tuple[float, float]:
    batch_count = sum(count for count, _, _ in _MEASURED_MONSTER_SHAPES) * repeats
    left = np.zeros((batch_count, _MAX_SIDE, 3), dtype=np.int64)
    right = np.zeros_like(left)
    left_counts = np.empty((batch_count,), dtype=np.int32)
    right_counts = np.empty((batch_count,), dtype=np.int32)
    cursor = 0
    for count, left_width, right_width in _MEASURED_MONSTER_SHAPES:
        shape_count = count * repeats
        shape_left, shape_left_counts, shape_right, shape_right_counts = _make_case(
            rng=rng,
            batch_count=shape_count,
            left_width=left_width,
            right_width=right_width,
        )
        end = cursor + shape_count
        left[cursor:end] = shape_left
        right[cursor:end] = shape_right
        left_counts[cursor:end] = shape_left_counts
        right_counts[cursor:end] = shape_right_counts
        cursor = end
    order = rng.permutation(batch_count)
    return _benchmark_arrays(
        "measured monster mix",
        left[order],
        left_counts[order],
        right[order],
        right_counts[order],
        repetitions,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    if args.threads <= 0 or args.repetitions <= 0:
        raise ValueError("threads and repetitions must be positive")
    set_num_threads(args.threads)

    cases = [(1, 130, 2048), (3, 124, 2048), (45, 3, 2048)]
    if not args.quick:
        cases.extend(((32, 32, 2048), (64, 64, 1024), (98, 98, 512)))
    rng = np.random.default_rng(116)
    print(
        "Issue #116 current packet-union Vulkan probe\n"
        f"  cpu_threads={args.threads} cooperative_workgroups=yes "
        f"max_side={_MAX_SIDE} persistent_device_buffers=yes"
    )
    for left_width, right_width, batch_count in cases:
        _run_case(
            rng=rng,
            left_width=left_width,
            right_width=right_width,
            batch_count=batch_count,
            repetitions=args.repetitions,
        )
    _run_measured_monster_mix(rng, args.repetitions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
