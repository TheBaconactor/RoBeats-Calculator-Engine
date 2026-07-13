"""Measure the exact Issue #149 region schedule-query owner on one real chart/geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("ISSUE149_BENCH_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0, str(ROOT))

from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song  # noqa: E402
from gear_optimizer.solver.timing_envelope import apply_timing_envelope  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _region_hit_value_universe,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True)
    parser.add_argument("--raw-fever-fill", required=True, type=float)
    parser.add_argument("--non-fever-base", required=True, type=int)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if int(args.repeats) <= 0:
        raise ValueError("repeats must be positive")

    calc_song = clone_calc_song(get_base_calc_song(str(Path(args.chart).resolve()), {}))
    apply_timing_envelope(calc_song, mode="perfect_window")
    song_data = calc_song["song_data"]
    timestamps = np.ascontiguousarray(song_data["fg_timestamps"], dtype=np.float32)
    perfect = np.ascontiguousarray(song_data["fg_perfect_candidate_timestamps"], dtype=np.float32)
    great = np.ascontiguousarray(song_data["fg_great_candidate_timestamps"], dtype=np.float32)
    perfect_floor = np.ascontiguousarray(song_data["fg_perfect_floor_timestamps"], dtype=np.float32)
    great_floor = np.ascontiguousarray(song_data["fg_great_floor_timestamps"], dtype=np.float32)
    lanes = np.ascontiguousarray(song_data["lanes"], dtype=np.int32)
    n = int(timestamps.shape[0])
    if any(int(values.shape[0]) != n for values in (perfect, great, perfect_floor, great_floor, lanes)):
        raise ValueError("chart timing arrays must align")

    actions, *_rest = _action_table(
        raw_fever_fill=float(args.raw_fever_fill),
        non_fever_base=int(args.non_fever_base),
        use_forced_great_timing=True,
    )
    action_k = np.ascontiguousarray(actions, dtype=np.int32)
    _hit_values, hit_token_to_id = _region_hit_value_universe(timestamps, perfect, great)
    candidate_high_delta_max = float(
        np.float32(max(0.0, float(np.max(np.maximum(perfect, great) - timestamps))) + 1.0e-6)
    )

    def build() -> tuple[np.ndarray, ...]:
        return response_build_gpu_numba._numba_build_region_core_table(
            n,
            int(action_k.shape[0]),
            action_k,
            float(args.raw_fever_fill),
            timestamps,
            candidate_high_delta_max,
            perfect_floor,
            perfect,
            great_floor,
            great,
            lanes,
            hit_token_to_id,
        )

    build()  # compile/warm outside the measured distribution
    elapsed: list[float] = []
    table: tuple[np.ndarray, ...] | None = None
    for _ in range(int(args.repeats)):
        started = time.perf_counter()
        table = build()
        elapsed.append(float(time.perf_counter() - started))
    if table is None:
        raise RuntimeError("benchmark produced no region table")
    ordered_digest = hashlib.sha256()
    for column in table:
        ordered_digest.update(np.ascontiguousarray(column).view(np.uint8))
    print(
        json.dumps(
            {
                "chart": str(Path(args.chart).resolve()),
                "notes": n,
                "actions": int(action_k.shape[0]),
                "rows": int(table[1].shape[0]),
                "table_bytes": int(sum(int(values.nbytes) for values in table)),
                "ordered_sha256": ordered_digest.hexdigest(),
                "seconds": elapsed,
                "median_seconds": float(np.median(np.asarray(elapsed, dtype=np.float64))),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
