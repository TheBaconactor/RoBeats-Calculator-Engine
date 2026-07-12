"""Bounded Vulkan probe for exact compact body-pair aggregation.

This is research tooling, not a production route.  It compares the retired dense
per-key pair table with a cooperative workgroup hash.  The hash keeps exactly the
maximum body-fever value for every touched ``pair_idx`` and fails loudly when its
fixed capacity or collision-round contract is exhausted.

The algorithm deliberately avoids compare-and-swap, which Taichi 1.7.4 does not
expose on Vulkan.  Each insertion round has three barriers:

1. contenders use ``atomic_min`` to elect the smallest key for an unsettled slot;
2. every contender for the elected key contributes through ``atomic_max``;
3. the elected key marks the slot settled before the next round begins.

Settled slots are immutable.  Losing keys advance by linear probing.  Therefore
hashes only select storage slots; full integer key equality decides identity.

Run:
    python tools/dev/issue116_gpu_compact_pair_reduce_probe.py
"""

import argparse
import math
import os
import sys
import time

import numpy as np

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.solver.taichi_gem.runtime import init_taichi

init_taichi()

import taichi as ti  # noqa: E402


_BLOCK_DIM = 64
_HASH_CAPACITY = 1024
_HASH_MASK = _HASH_CAPACITY - 1
_MAX_CANDIDATES = 2048
_MAX_COLLISION_ROUNDS = _BLOCK_DIM
_EMPTY_KEY = 2_147_483_647


@ti.kernel
def _dense_pair_reduce(
    batch_count: ti.i32,
    pair_size: ti.i32,
    stamp: ti.i32,
    candidates: ti.types.ndarray(dtype=ti.i32, ndim=3),
    candidate_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    dense_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    dense_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    ti.loop_config(block_dim=_BLOCK_DIM)
    for gid in range(batch_count * _BLOCK_DIM):
        batch = gid // _BLOCK_DIM
        thread = ti.simt.block.thread_idx()

        # Match the archived kernel's epoch-stamped dense table: claim distinct
        # pairs first, then scatter maxima after a barrier.  The full pair table
        # is initialized once per key, not once per state/timed launch.
        candidate_idx = thread
        while candidate_idx < candidate_counts[batch]:
            key = candidates[batch, candidate_idx, 0]
            if key < 0 or key >= pair_size:
                key = 0
            old_stamp = ti.atomic_max(dense_stamps[batch, key], stamp)
            if old_stamp < stamp:
                dense_values[batch, key] = -1
            candidate_idx += _BLOCK_DIM
        ti.simt.block.sync()

        candidate_idx = thread
        while candidate_idx < candidate_counts[batch]:
            key = candidates[batch, candidate_idx, 0]
            value = candidates[batch, candidate_idx, 1]
            if key < 0 or key >= pair_size:
                key = 0
                value = -1
            ti.atomic_max(dense_values[batch, key], value)
            candidate_idx += _BLOCK_DIM


@ti.kernel
def _compact_pair_reduce(
    batch_count: ti.i32,
    pair_size: ti.i32,
    candidates: ti.types.ndarray(dtype=ti.i32, ndim=3),
    candidate_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    output_keys: ti.types.ndarray(dtype=ti.i32, ndim=2),
    output_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    output_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    error_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    ti.loop_config(block_dim=_BLOCK_DIM)
    for gid in range(batch_count * _BLOCK_DIM):
        batch = gid // _BLOCK_DIM
        thread = ti.simt.block.thread_idx()

        keys = ti.simt.block.SharedArray((_HASH_CAPACITY,), ti.i32)
        values = ti.simt.block.SharedArray((_HASH_CAPACITY,), ti.i32)
        settled = ti.simt.block.SharedArray((_HASH_CAPACITY,), ti.i32)
        shared_error = ti.simt.block.SharedArray((1,), ti.i32)
        remaining = ti.simt.block.SharedArray((1,), ti.i32)

        slot = thread
        while slot < _HASH_CAPACITY:
            keys[slot] = _EMPTY_KEY
            values[slot] = -1
            settled[slot] = 0
            slot += _BLOCK_DIM
        if thread == 0:
            shared_error[0] = 0
        ti.simt.block.sync()

        # One candidate per thread keeps its probe state in registers.  Chunks
        # retain the settled hash, so duplicate keys across chunks coalesce too.
        for chunk in range(_MAX_CANDIDATES // _BLOCK_DIM):
            candidate_idx = chunk * _BLOCK_DIM + thread
            active = candidate_idx < candidate_counts[batch]
            key = ti.i32(0)
            value = ti.i32(-1)
            probe = ti.i32(0)
            done = not active
            if thread == 0:
                remaining[0] = ti.max(
                    0,
                    ti.min(
                        _BLOCK_DIM,
                        candidate_counts[batch] - chunk * _BLOCK_DIM,
                    ),
                )
            ti.simt.block.sync()
            if active:
                key = candidates[batch, candidate_idx, 0]
                value = candidates[batch, candidate_idx, 1]
                if key < 0 or key >= pair_size or value < 0:
                    ti.atomic_or(shared_error[0], 1)
                    done = True

            # At most 64 distinct candidates enter in one chunk, so 64 election
            # rounds are sufficient even when every candidate hashes identically.
            for _round in range(_MAX_COLLISION_ROUNDS):
                proposed = False
                proposed_slot = ti.i32(0)
                completed_now = False
                if not done:
                    scanned = ti.i32(0)
                    while scanned < _HASH_CAPACITY and not done and not proposed:
                        candidate_slot = (
                            ti.i32(ti.u32(key) * ti.u32(2_654_435_761)) + probe
                        ) & _HASH_MASK
                        if settled[candidate_slot] != 0:
                            if keys[candidate_slot] == key:
                                ti.atomic_max(values[candidate_slot], value)
                                done = True
                                completed_now = True
                            else:
                                probe += 1
                                scanned += 1
                        else:
                            ti.atomic_min(keys[candidate_slot], key)
                            proposed_slot = candidate_slot
                            proposed = True
                    if scanned >= _HASH_CAPACITY and not done:
                        ti.atomic_or(shared_error[0], 2)
                        done = True
                        completed_now = True

                # All contenders have proposed before anybody treats an elected
                # key as immutable.
                ti.simt.block.sync()
                won = proposed and keys[proposed_slot] == key
                if won:
                    ti.atomic_max(values[proposed_slot], value)
                    done = True
                    completed_now = True
                elif proposed:
                    probe += 1
                ti.simt.block.sync()
                if won:
                    settled[proposed_slot] = 1
                if completed_now:
                    ti.atomic_sub(remaining[0], 1)
                ti.simt.block.sync()
                if remaining[0] == 0:
                    break

            if not done:
                ti.atomic_or(shared_error[0], 4)
            ti.simt.block.sync()

        write_count = ti.simt.block.SharedArray((1,), ti.i32)
        if thread == 0:
            write_count[0] = 0
        ti.simt.block.sync()

        slot = thread
        while slot < _HASH_CAPACITY:
            if settled[slot] != 0:
                output_idx = ti.atomic_add(write_count[0], 1)
                output_keys[batch, output_idx] = keys[slot]
                output_values[batch, output_idx] = values[slot]
            slot += _BLOCK_DIM
        ti.simt.block.sync()
        if thread == 0:
            output_counts[batch] = write_count[0]
            error_flags[batch] = shared_error[0]


def _make_batches(
    *,
    rng: np.random.Generator,
    batch_count: int,
    pair_size: int,
    candidate_count: int,
    unique_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    if not 0 < unique_count <= min(candidate_count, _HASH_CAPACITY):
        raise ValueError("unique_count must fit both candidate_count and compact hash")
    if candidate_count > _MAX_CANDIDATES:
        raise ValueError(f"candidate_count exceeds {_MAX_CANDIDATES}")
    if unique_count > pair_size:
        raise ValueError("unique_count exceeds pair_size")

    candidates = np.zeros((batch_count, _MAX_CANDIDATES, 2), dtype=np.int32)
    counts = np.full((batch_count,), candidate_count, dtype=np.int32)
    for batch in range(batch_count):
        unique_keys = rng.choice(pair_size, size=unique_count, replace=False).astype(np.int32)
        selected = rng.integers(0, unique_count, size=candidate_count)
        candidates[batch, :candidate_count, 0] = unique_keys[selected]
        candidates[batch, :candidate_count, 1] = rng.integers(
            0, 10_000, size=candidate_count, dtype=np.int32
        )
    return candidates, counts


def _expected_rows(candidates: np.ndarray, count: int) -> dict[int, int]:
    expected: dict[int, int] = {}
    for key, value in candidates[:count]:
        expected[int(key)] = max(expected.get(int(key), -1), int(value))
    return expected


def _time_ms(callable_, *, repetitions: int) -> float:
    callable_()
    ti.sync()
    samples = []
    for _ in range(repetitions):
        started = time.perf_counter()
        callable_()
        ti.sync()
        samples.append((time.perf_counter() - started) * 1_000.0)
    return float(np.median(np.asarray(samples, dtype=np.float64)))


def _run_case(
    *,
    label: str,
    candidates: np.ndarray,
    counts: np.ndarray,
    pair_size: int,
    repetitions: int,
) -> dict[str, float]:
    batch_count = int(candidates.shape[0])
    if np.any(counts < 0) or np.any(counts > _MAX_CANDIDATES):
        raise ValueError("candidate count outside probe contract")
    active = np.arange(_MAX_CANDIDATES)[None, :] < counts[:, None]
    active_keys = candidates[:, :, 0][active]
    active_values = candidates[:, :, 1][active]
    if np.any(active_keys < 0) or np.any(active_keys >= pair_size):
        raise ValueError("candidate pair key outside dense oracle range")
    if np.any(active_values < 0):
        raise ValueError("candidate value must be nonnegative")

    candidates_device = ti.ndarray(ti.i32, shape=candidates.shape)
    candidates_device.from_numpy(candidates)
    counts_device = ti.ndarray(ti.i32, shape=counts.shape)
    counts_device.from_numpy(counts)

    dense_values_device = ti.ndarray(ti.i32, shape=(batch_count, pair_size))
    dense_values_device.from_numpy(
        np.full((batch_count, pair_size), -1, dtype=np.int32)
    )
    dense_stamps_device = ti.ndarray(ti.i32, shape=(batch_count, pair_size))
    dense_stamps_device.from_numpy(
        np.zeros((batch_count, pair_size), dtype=np.int32)
    )
    output_keys_device = ti.ndarray(
        ti.i32, shape=(batch_count, _HASH_CAPACITY)
    )
    output_values_device = ti.ndarray(
        ti.i32, shape=(batch_count, _HASH_CAPACITY)
    )
    output_counts_device = ti.ndarray(ti.i32, shape=(batch_count,))
    error_flags_device = ti.ndarray(ti.i32, shape=(batch_count,))

    dense_stamp = [0]

    def dense_call():
        dense_stamp[0] += 1
        _dense_pair_reduce(
            batch_count,
            pair_size,
            dense_stamp[0],
            candidates_device,
            counts_device,
            dense_values_device,
            dense_stamps_device,
        )
    compact_call = lambda: _compact_pair_reduce(
        batch_count,
        pair_size,
        candidates_device,
        counts_device,
        output_keys_device,
        output_values_device,
        output_counts_device,
        error_flags_device,
    )

    dense_ms = _time_ms(dense_call, repetitions=repetitions)
    compact_ms = _time_ms(compact_call, repetitions=repetitions)

    # A final untimed launch leaves deterministic host-visible verification data.
    dense_call()
    compact_call()
    ti.sync()
    dense_values = dense_values_device.to_numpy()
    output_keys = output_keys_device.to_numpy()
    output_values = output_values_device.to_numpy()
    output_counts = output_counts_device.to_numpy()
    error_flags = error_flags_device.to_numpy()
    if np.any(error_flags != 0):
        bad = np.flatnonzero(error_flags != 0)
        raise RuntimeError(
            f"{label}: compact hash failed loudly for batches {bad[:8].tolist()} "
            f"with flags {error_flags[bad[:8]].tolist()}"
        )

    for batch in range(batch_count):
        expected = _expected_rows(candidates[batch], int(counts[batch]))
        compact = {
            int(output_keys[batch, idx]): int(output_values[batch, idx])
            for idx in range(int(output_counts[batch]))
        }
        dense = {
            int(key): int(dense_values[batch, key])
            for key in expected
            if int(dense_values[batch, key]) >= 0
        }
        if compact != expected or dense != expected:
            raise AssertionError(
                f"{label}: aggregation mismatch in batch {batch}: "
                f"expected={len(expected)} compact={len(compact)} dense={len(dense)}"
            )

    dense_bytes = batch_count * pair_size * np.dtype(np.int32).itemsize * 2
    compact_bytes = output_keys.nbytes + output_values.nbytes
    speedup = dense_ms / compact_ms
    print(
        f"{label:>18}: dense={dense_ms:8.3f} ms  compact={compact_ms:8.3f} ms  "
        f"speedup={speedup:6.2f}x  pair-scratch={dense_bytes / 2**20:7.1f}->"
        f"{compact_bytes / 2**20:5.1f} MiB ({dense_bytes / compact_bytes:5.1f}x)"
    )
    return {"dense_ms": dense_ms, "compact_ms": compact_ms, "speedup": speedup}


def _collision_case(pair_size: int) -> tuple[np.ndarray, np.ndarray]:
    # Odd multiplicative hashing preserves identical low ten bits for keys spaced
    # by HASH_CAPACITY, forcing one 64-way collision chain.
    candidate_count = _BLOCK_DIM
    candidates = np.zeros((1, _MAX_CANDIDATES, 2), dtype=np.int32)
    candidates[0, :candidate_count, 0] = np.arange(candidate_count, dtype=np.int32) * _HASH_CAPACITY
    candidates[0, :candidate_count, 1] = np.arange(candidate_count, dtype=np.int32)
    counts = np.asarray([candidate_count], dtype=np.int32)
    if int(candidates[0, candidate_count - 1, 0]) >= pair_size:
        raise ValueError("pair_size is too small for adversarial collision case")
    return candidates, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=192)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--pair-size", type=int, default=126_504)
    parser.add_argument("--candidates", type=int, default=1_888)
    parser.add_argument("--unique", type=int, default=472)
    args = parser.parse_args()

    if args.batches <= 0 or args.repetitions <= 0:
        raise ValueError("batches and repetitions must be positive")
    if args.pair_size <= 0:
        raise ValueError("pair-size must be positive")

    rng = np.random.default_rng(116)
    random_candidates, random_counts = _make_batches(
        rng=rng,
        batch_count=args.batches,
        pair_size=args.pair_size,
        candidate_count=args.candidates,
        unique_count=args.unique,
    )
    collision_candidates, collision_counts = _collision_case(args.pair_size)

    print(
        "Issue #116 compact pair-reduce Vulkan probe\n"
        f"  block_dim={_BLOCK_DIM} hash_capacity={_HASH_CAPACITY} "
        f"max_candidates={_MAX_CANDIDATES} collision_rounds={_MAX_COLLISION_ROUNDS}\n"
        f"  production-shaped synthetic: batches={args.batches} "
        f"candidates={args.candidates} unique={args.unique} pair_size={args.pair_size}"
    )
    collision = _run_case(
        label="64-way collision",
        candidates=collision_candidates,
        counts=collision_counts,
        pair_size=args.pair_size,
        repetitions=max(2, args.repetitions // 2),
    )
    random_case = _run_case(
        label="production-shape",
        candidates=random_candidates,
        counts=random_counts,
        pair_size=args.pair_size,
        repetitions=args.repetitions,
    )

    if not math.isfinite(random_case["speedup"]):
        raise RuntimeError("non-finite speed ratio")
    if collision["speedup"] <= 0.0:
        raise RuntimeError("invalid collision-case timing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
