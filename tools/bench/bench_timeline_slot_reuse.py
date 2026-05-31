"""
Benchmark: timeline slot reuse vs slot-0 thrash.

Goal:
- Show why deterministic song_slot assignment matters in in-flight pipelines.
- Demonstrate CPU->GPU upload and wall-time differences when the same songs are
  repeatedly evaluated with:
  (A) slot 0 shared (cache constantly clobbered), vs
  (B) dedicated slots per song (cache hits, no re-upload/recompute).

Run:
  python tools/bench/bench_timeline_slot_reuse.py
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@dataclass(frozen=True)
class _Case:
    name: str
    seq: list[tuple[str, int]]  # (song_id, slot)


def _make_ref_arrays() -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }


def _make_calc_song(song_id: str, *, n_notes: int) -> dict:
    # Use float64 timestamps to mimic the real pipeline; GPU API casts internally.
    timestamps = np.linspace(0.0, 120.0, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": f"Bench:{song_id}",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(n_notes),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": timestamps, "chart_timestamps": timestamps},
    }


def _run_case(case: _Case, *, songs: dict[str, dict], ref_arrays: dict, iters: int) -> tuple[float, int]:
    import taichi as ti
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu, reset_timeline_state

    reset_timeline_state()

    t0 = time.perf_counter()
    for _ in range(int(iters)):
        for song_id, slot in case.seq:
            precompute_timeline_gpu(songs[song_id], ref_arrays, song_slot=int(slot))
    ti.sync()
    t1 = time.perf_counter()

    return float(t1 - t0), 0


def main() -> int:
    ref_arrays = _make_ref_arrays()
    songs = {
        "A": _make_calc_song("A", n_notes=2000),
        "B": _make_calc_song("B", n_notes=2000),
    }

    # Warmup (JIT + first grid compute), then reset timeline cache state in each case.
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    import taichi as ti

    precompute_timeline_gpu(songs["A"], ref_arrays, song_slot=0)
    ti.sync()

    iters = 20
    cases = [
        _Case(
            name="slot0_thrash(A/B alternate on slot 0)",
            seq=[("A", 0), ("B", 0)],
        ),
        _Case(
            name="slot_reuse(A->1, B->2)",
            seq=[("A", 1), ("B", 2)],
        ),
    ]

    print(f"[bench] iters={iters} seq_len={len(cases[0].seq)} notes={len(songs['A']['song_data']['timestamps'])}")
    results = []
    for c in cases:
        dt, up = _run_case(c, songs=songs, ref_arrays=ref_arrays, iters=iters)
        results.append((c.name, dt, up))
        print(f"[bench] {c.name}: wall={dt * 1000:.1f}ms upload_bytes={up}")

    if len(results) == 2:
        a = results[0]
        b = results[1]
        dt0 = float(a[1])
        dt1 = float(b[1])
        up0 = int(a[2])
        up1 = int(b[2])
        speedup = (dt0 / dt1) if dt1 > 0 else float("inf")
        up_ratio = (up0 / up1) if up1 > 0 else float("inf")
        print(f"[bench] speedup={speedup:.2f}x upload_reduction={up_ratio:.2f}x")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
