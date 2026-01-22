"""
Synthetic repro for "optionality-first vs exactness-first" inventory behavior.

This does NOT require an evolution.db with loadouts; it builds a small synthetic witness pool and runs the
GPU full solver directly, then prints the optionality metrics added to `inventory_optimizer.coverage`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_synthetic(*, a_songs: int, b_songs: int, m_offsets: int) -> tuple[list[str], np.ndarray, np.ndarray]:
    """
    Build a witness pool with two disjoint gear-ID clusters:
    - A cluster: gear IDs 1..6, but each song needs a "sliding window" of possible offsets for slot 0.
      This encourages spending many variants on the same gear ID to cover more songs.
    - B cluster: gear IDs 7..12, all offsets fixed to 0 (cheap if you invest in the second gear set).
    """
    a_songs = int(a_songs)
    b_songs = int(b_songs)
    m_offsets = int(m_offsets)

    s_count = a_songs + b_songs
    k = 3

    gear_names = [f"Gear{i}" for i in range(1, 13)]
    gear_ids_np = np.zeros((s_count, 6), dtype=np.int32)
    offsets_np = np.zeros((s_count, k, 6), dtype=np.int32)

    # Cluster A: same gear set, but offsets for slot 0 vary per song.
    for s in range(a_songs):
        gear_ids_np[s, :] = np.asarray([1, 2, 3, 4, 5, 6], dtype=np.int32)
        base = int(s % max(1, m_offsets))
        for p in range(k):
            offsets_np[s, p, :] = 0
            offsets_np[s, p, 0] = int((base + p) % max(1, m_offsets))

    # Cluster B: different gear set, fixed offsets (represents "need different gear IDs" wall).
    for s in range(a_songs, s_count):
        gear_ids_np[s, :] = np.asarray([7, 8, 9, 10, 11, 12], dtype=np.int32)
        offsets_np[s, :, :] = 0

    return gear_names, gear_ids_np, offsets_np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-cap", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--a-songs", type=int, default=18)
    ap.add_argument("--b-songs", type=int, default=18)
    ap.add_argument("--m-offsets", type=int, default=18)
    args = ap.parse_args()

    from inventory_optimizer.coverage import _MemoryLogger, _optionality_stats_single, _run_gpu_full_solver_from_offsets

    gear_names, gear_ids_np, offsets_np = _build_synthetic(a_songs=args.a_songs, b_songs=args.b_songs, m_offsets=args.m_offsets)
    mem = _MemoryLogger(enabled=False)

    sol = _run_gpu_full_solver_from_offsets(
        gear_ids_np,
        offsets_np,
        inventory_cap=int(args.inventory_cap),
        seed=int(args.seed),
        gpu_repack_passes=2,
        gpu_full_repack_rarity_weighted=False,
        gpu_full_k_scan_select=0,
        gpu_full_k_scan_repack=0,
        lns_time_sec=0.0,
        lns_attempts=50,
        gpu_lns_destroy=6,
        gpu_full_lns_freq_weighted=False,
        gpu_full_lns_random_destroy_prob=0.0,
        gpu_full_lns_restore_after=12,
        gpu_full_lns_restore_drop=4,
        gpu_full_variant_freq_mode="occurrence",
        gpu_full_counter_stripes=1,
        mem=mem,
        v_pad_bin=256,
    )

    covered_np = np.asarray(sol.covered, dtype=np.int32)
    chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)

    opt = _optionality_stats_single(
        gear_names=gear_names,
        gear_ids_np=gear_ids_np,
        covered_np=covered_np,
        chosen_offsets_np=chosen_offsets_np,
        seeded_raw_vids=None,
    )

    print(
        json.dumps(
            {
                "synthetic": {"a_songs": int(args.a_songs), "b_songs": int(args.b_songs), "m_offsets": int(args.m_offsets)},
                "solution": {"covered": int(covered_np.sum()), "total": int(covered_np.size)},
                "optionality": opt,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
