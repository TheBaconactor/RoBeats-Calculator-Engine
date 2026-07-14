"""Wall-clock the engine-physical Base frontier grid build for selected songs."""
from __future__ import annotations

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.data.song_io import read_song_file  # noqa: E402
from gear_optimizer.solver import timeline_exact_frontier as tef  # noqa: E402
from gear_optimizer.solver.timing_envelope import (  # noqa: E402
    build_perfect_candidate_envelope_sec,
    build_perfect_floor_envelope_sec,
)

GRID = 161
FT = np.linspace(0.5, 1.6, GRID).astype(np.float32)
FF = np.linspace(0.5, 1.6, GRID).astype(np.float32)
SONGS = [
    "Data/Hard/Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt",
    "Data/Hard/#include signal.h by Kurokotei.txt",
    "Data/Normal/#include signal.h by Kurokotei.txt",
]


def time_one(fp, reps=3):
    d = read_song_file(fp)
    ts = np.asarray(d.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(d.get("note_types", []), np.int16).reshape(-1)
    lanes = np.asarray(d.get("lanes", []), np.int32).reshape(-1)
    n = int(ts.shape[0])
    lnt = float(d.get("song_details", {}).get("Last Note Time", ts[-1]))
    lon = int(np.count_nonzero(nt == 2))
    perfect_candidates = build_perfect_candidate_envelope_sec(ts, nt)
    perfect_floor = build_perfect_floor_envelope_sec(ts, nt)
    best = None
    for _ in range(reps):
        t0 = time.perf_counter()
        tef.build_timeline_frontier_grid_payload(
            song_slot=0, total_notes=n, long_notes=lon, last_note_time=lnt, song_key=None,
            timestamps=ts, perfect_candidate_timestamps=perfect_candidates,
            perfect_floor_timestamps=perfect_floor, lanes=lanes, ref_ft=FT, ref_ff=FF)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return n, best


def main():
    print(f"{'notes':>6} {'full(ms)':>9}  song")
    for rel in SONGS:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            print(f"  (missing: {rel})")
            continue
        n, full = time_one(fp)
        print(f"{n:>6} {full*1e3:>9.1f}  {os.path.basename(fp)[:46]}")


if __name__ == "__main__":
    main()
