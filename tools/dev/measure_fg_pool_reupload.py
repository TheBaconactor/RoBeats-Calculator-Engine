#!/usr/bin/env python3
"""A/B: does the FG score loop re-upload the full surface pool every chunk?

Hypothesis under test
---------------------
`_score_response_group_meta_gpu` passes the FULL packed surface pool
(`surface_words_all`, `surface_counts_all`, `surface_head_coeffs_all`) to
`_fg_response_inner_batch_kernel` on EVERY chunk (response_inner_host.py:577-593).
Those are `ti.types.ndarray` params fed plain numpy arrays, so Taichi transfers
them host->device on every launch. On heavy songs the pool is 9-25M rows
(0.5-1.5 GB) and the loop runs 143-219 chunks -> 90-330 GB of redundant PCIe
traffic. This is invisible to Compute-engine sampling (it's the Copy engine) and
gets lumped into `enqueue_ms`.

This harness loads a REAL cached song pool, then scores it two ways with the
SAME real kernel and the SAME inputs:
  * current   -- pool passed as numpy each chunk (production behavior)
  * uploaded  -- pool uploaded to device-resident ti.ndarray ONCE, reused
Then it asserts `out_rows` is bit-identical (exactness) and reports the speedup
(the re-upload cost). Bit-identical out_rows + a large speedup => the re-upload
is real and the upload-once fix is sound.

Usage:
    python tools/dev/measure_fg_pool_reupload.py            # largest cached pool
    python tools/dev/measure_fg_pool_reupload.py --pool-hash <hash> --target-logical 40000000
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import taichi as ti  # noqa: E402

from gear_optimizer.core.constants import TOTAL_ROWS  # noqa: E402
from gear_optimizer.solver.taichi_gem import api as gem_api  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (  # noqa: E402
    _color_flags,
    _response_inner_combo_counts,
    _response_group_logical_surface_plan,
    _reduce_response_inner_chunk_jit,
    _score_response_group_meta_gpu,
    _FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS as MAX_ROWS,
    _FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK as MAX_WORK,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import (  # noqa: E402
    _fg_response_inner_batch_kernel,
)

CACHE = REPO / "bin" / "fg_response_frontier_cache"


def _largest_pool_hash() -> str:
    best_h, best_rows = None, -1
    for p in glob.glob(str(CACHE / "*.surf_pool.npy")):
        h = os.path.basename(p).split(".surf_pool")[0]
        if not (CACHE / f"{h}.surf_coeffs.npy").exists() or not (CACHE / f"{h}.npz").exists():
            continue
        rows = int(np.load(p, mmap_mode="r").shape[0])
        if rows > best_rows:
            best_h, best_rows = h, rows
    if best_h is None:
        raise SystemExit("no complete cached pool found")
    return best_h


def _build_groups(npz, target_logical: int, residual: int):
    """Replicate the real per-owner structure: each owner references one frontier
    segment (first_offsets[fid], first_counts[fid]); replicate frontiers until we
    reach ~target_logical logical rows, matching the real pool>->logical fan-out."""
    first_offsets = np.asarray(npz["first_offsets"], dtype=np.int64)
    first_counts = np.asarray(npz["first_counts"], dtype=np.int64)
    total_notes = int(npz["total_notes"])
    head_len = min(total_notes, 100)
    body_total = max(0, total_notes - 100)

    keep = first_counts > 0
    offs = first_offsets[keep]
    lens = first_counts[keep]
    order = np.argsort(-lens)  # big frontiers first so the batch path is exercised
    offs, lens = offs[order], lens[order]

    g_off, g_len = [], []
    logical = 0
    i = 0
    n = int(offs.shape[0])
    while logical < target_logical and n > 0:
        j = i % n
        g_off.append(int(offs[j]))
        g_len.append(int(lens[j]))
        logical += int(lens[j])
        i += 1
    group_count = len(g_off)

    group_offsets = np.ascontiguousarray(np.asarray(g_off, dtype=np.int32))
    group_lengths = np.ascontiguousarray(np.asarray(g_len, dtype=np.int32))
    # Representative mid-range stats; residual drives combo work (chunk count).
    mid = TOTAL_ROWS // 3
    group_meta = np.zeros((group_count, 8), dtype=np.int32)
    group_meta[:, 0] = int(residual)         # residual_budget
    group_meta[:, 1] = mid                    # cur_pp
    group_meta[:, 2] = mid                    # cur_cm
    group_meta[:, 3] = mid                    # cur_fm
    group_meta[:, 4] = mid                    # cur_primary
    group_meta[:, 5] = mid // 2               # cur_secondary
    group_meta[:, 6] = int(head_len)
    group_meta[:, 7] = int(body_total)
    return group_meta, group_offsets, group_lengths, int(logical)


def _ref_arrays():
    n = TOTAL_ROWS + 1
    idx = np.arange(n, dtype=np.float64)
    return {
        "Perfect Points": np.ascontiguousarray(1.0 + idx * 0.01),
        "Combo Multiplier": np.ascontiguousarray(1.0 + idx * 0.02),
        "Fever Multiplier": np.ascontiguousarray(2.0 + idx * 0.03),
    }


def _score_upload_once(*, group_meta, group_offsets, group_lengths, primary, secondary,
                       selected, ref_arrays, surface_words, surface_counts, surface_head_coeffs):
    """Bit-identical to the batch path of `_score_response_group_meta_gpu`, except the
    surface POOL is uploaded to a device-resident ti.ndarray ONCE and reused across
    chunks (the proposed fix). Index/output arrays still vary per chunk."""
    group_count = int(group_meta.shape[0])
    flags = np.ascontiguousarray(np.asarray(_color_flags(primary, secondary, selected), dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float64))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float64))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float64))
    sw = np.ascontiguousarray(surface_words, dtype=np.uint32)
    sc = np.ascontiguousarray(surface_counts, dtype=np.int32)
    shc = np.ascontiguousarray(surface_head_coeffs, dtype=np.int32)
    group_offsets_all = np.ascontiguousarray(group_offsets, dtype=np.int32)
    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    group_lengths_all = np.ascontiguousarray(group_lengths, dtype=np.int32)

    flags_tuple = _color_flags(primary, secondary, selected)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    combo_counts_all = _response_inner_combo_counts(group_meta_all, allow_pp=allow_pp)
    logical_owners_all, logical_surfaces_all, logical_work_cumsum_all = _response_group_logical_surface_plan(
        group_lengths_all, combo_counts_all
    )
    logical_surface_rows = int(logical_owners_all.shape[0])
    out_rows = np.zeros((group_count, 11), dtype=np.int32)
    best_scores = np.full((group_count,), np.iinfo(np.int32).min, dtype=np.int32)

    # ---- upload the pool ONCE ----
    d_words = ti.ndarray(dtype=ti.u32, shape=sw.shape)
    d_counts = ti.ndarray(dtype=ti.i32, shape=sc.shape)
    d_coeffs = ti.ndarray(dtype=ti.i32, shape=shc.shape)
    d_words.from_numpy(sw)
    d_counts.from_numpy(sc)
    d_coeffs.from_numpy(shc)
    ti.sync()

    chunk_capacity = max(1, min(int(MAX_ROWS), int(logical_surface_rows)))
    chunk_scores = np.empty((chunk_capacity,), dtype=np.int32)
    chunk_details = np.empty((chunk_capacity, 9), dtype=np.int32)
    chunk_start = 0
    n_chunks = 0
    while chunk_start < int(logical_surface_rows):
        row_stop = min(int(logical_surface_rows), int(chunk_start) + int(MAX_ROWS))
        work_limit = int(logical_work_cumsum_all[int(chunk_start)]) + int(MAX_WORK)
        work_stop = int(np.searchsorted(logical_work_cumsum_all, work_limit, side="right") - 1)
        if work_stop <= int(chunk_start):
            work_stop = int(chunk_start) + 1
        chunk_stop = min(int(row_stop), int(work_stop), int(logical_surface_rows))
        row_count = int(chunk_stop) - int(chunk_start)
        scores_view = chunk_scores[:row_count]
        details_view = chunk_details[:row_count]
        _fg_response_inner_batch_kernel(
            int(row_count),
            d_words, d_counts, d_coeffs,            # <-- device-resident, uploaded once
            group_offsets_all,
            logical_owners_all[int(chunk_start):int(chunk_stop)],
            logical_surfaces_all[int(chunk_start):int(chunk_stop)],
            group_meta_all,
            flags, ref_pp, ref_cm, ref_fm,
            scores_view, details_view,
            bool(allow_pp),
        )
        ti.sync()
        _reduce_response_inner_chunk_jit(
            int(row_count), scores_view, details_view,
            logical_owners_all[int(chunk_start):int(chunk_stop)],
            logical_surfaces_all[int(chunk_start):int(chunk_stop)],
            best_scores, out_rows,
        )
        chunk_start = int(chunk_stop)
        n_chunks += 1
    return out_rows, logical_surface_rows, n_chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-hash", default=None)
    ap.add_argument("--target-logical", type=int, default=36_000_000)
    ap.add_argument("--residual", type=int, default=24)
    ap.add_argument("--repeat", type=int, default=2)
    args = ap.parse_args()

    h = args.pool_hash or _largest_pool_hash()
    pool = np.load(CACHE / f"{h}.surf_pool.npy")           # (N,11) u32
    coeffs = np.load(CACHE / f"{h}.surf_coeffs.npy")       # (N,4) i32
    npz = np.load(CACHE / f"{h}.npz", allow_pickle=True)
    surface_words = np.ascontiguousarray(pool[:, :8], dtype=np.uint32)
    surface_counts = np.ascontiguousarray(pool[:, 8:11], dtype=np.int32)
    surface_head_coeffs = np.ascontiguousarray(coeffs, dtype=np.int32)
    pool_rows = int(surface_words.shape[0])
    pool_bytes = pool_rows * (8 * 4 + 3 * 4 + 4 * 4)

    group_meta, group_offsets, group_lengths, logical = _build_groups(npz, args.target_logical, args.residual)
    ref = _ref_arrays()
    primary, secondary, selected = "Chill", "Flow", "Chill"

    print(f"pool hash         : {h}")
    print(f"pool rows         : {pool_rows:,}  ({pool_bytes/1e9:.2f} GB / chunk re-upload)")
    print(f"groups (owners)   : {group_meta.shape[0]:,}")
    print(f"logical rows      : {logical:,}")
    print(f"residual_budget   : {args.residual}")

    gem_api.ensure_ready()

    def time_call(fn, *, label):
        best = None
        meta = None
        for r in range(args.repeat):
            t0 = time.perf_counter()
            res = fn()
            dt = time.perf_counter() - t0
            out = res[0] if isinstance(res, tuple) else res
            meta = res
            ms = dt * 1000.0
            print(f"  {label} run{r}: {ms:,.0f} ms")
            best = ms if best is None else min(best, ms)
        return best, meta

    cur_ms, cur_res = time_call(
        lambda: _score_response_group_meta_gpu(
            group_meta=group_meta, group_offsets=group_offsets, group_lengths=group_lengths,
            primary_color=primary, secondary_color=secondary, selected_color=selected,
            ref_arrays=ref, surface_words=surface_words, surface_counts=surface_counts,
            surface_head_coeffs=surface_head_coeffs,
        ),
        label="current (numpy/chunk)",
    )
    cur_rows = cur_res[0]

    up_ms, up_res = time_call(
        lambda: _score_upload_once(
            group_meta=group_meta, group_offsets=group_offsets, group_lengths=group_lengths,
            primary=primary, secondary=secondary, selected=selected,
            ref_arrays=ref, surface_words=surface_words, surface_counts=surface_counts,
            surface_head_coeffs=surface_head_coeffs,
        ),
        label="upload-once (device)",
    )
    up_rows, _logical2, n_chunks = up_res

    identical = bool(np.array_equal(cur_rows, up_rows))
    reupload_gb = pool_bytes * n_chunks / 1e9
    print("-" * 64)
    print(f"n_chunks          : {n_chunks}")
    print(f"current  best     : {cur_ms:,.0f} ms")
    print(f"upload-once best  : {up_ms:,.0f} ms")
    print(f"speedup           : {cur_ms/up_ms:.2f}x   (saved {cur_ms-up_ms:,.0f} ms)")
    print(f"redundant upload  : {reupload_gb:.1f} GB across {n_chunks} chunks (current path)")
    print(f"out_rows IDENTICAL: {identical}")
    if not identical:
        diff = int(np.count_nonzero(np.any(cur_rows != up_rows, axis=1)))
        print(f"  !!! {diff} group rows differ -- NOT bit-exact, do not ship")
        sys.exit(2)


if __name__ == "__main__":
    main()
