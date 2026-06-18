"""Wall-clock the base-frontier full grid build for a few specific songs (min of N reps).
Cross-version safe: uses only prepare_perfect_timing_envelope + build_timeline_frontier_grid_payload,
so it runs on both the current and the pre-PR baseline. Run on each to size the regression."""
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
from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope  # noqa: E402

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
    n = int(ts.shape[0])
    lnt = float(d.get("song_details", {}).get("Last Note Time", ts[-1]))
    lon = int(np.count_nonzero(nt == 2))
    p = prepare_perfect_timing_envelope(ts, nt, perfect_lower_ms=-20, perfect_upper_ms=40,
                                        held_tail_type=3, held_tail_time_multiplier=2, quantize_ms=True)
    gs = np.asarray(p["group_starts"], np.int32); ge = np.asarray(p["group_ends"], np.int32)
    gb = np.asarray(p["group_base_t"], np.int32); gl = np.asarray(p["group_low"], np.int32)
    gh = np.asarray(p["group_high"], np.int32)
    ngi = np.repeat(np.arange(gs.shape[0], dtype=np.int32), (ge - gs).astype(np.int32))
    G = int(gs.shape[0])
    best = None
    for _ in range(reps):
        t0 = time.perf_counter()
        tef.build_timeline_frontier_grid_payload(
            song_slot=0, total_notes=n, long_notes=lon, last_note_time=lnt, song_key=None,
            group_starts=gs, group_ends=ge, group_base_t_ms=gb, group_low_ms=gl, group_high_ms=gh,
            note_group_idx=ngi, ref_ft=FT, ref_ff=FF)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return G, n, best


def main():
    print(f"{'G':>6} {'notes':>6} {'full(ms)':>9}  song")
    for rel in SONGS:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            print(f"  (missing: {rel})")
            continue
        G, n, full = time_one(fp)
        print(f"{G:>6} {n:>6} {full*1e3:>9.1f}  {os.path.basename(fp)[:46]}")


if __name__ == "__main__":
    main()
