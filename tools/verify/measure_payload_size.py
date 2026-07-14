"""Compare base-frontier payload size (per-scoring proxy) for a few songs. Run on current vs
baseline. grid_frontier_count = per-cell surfaces the GPU scorer argmaxes over (per-eval cost);
frontier_pool_used = total distinct surfaces (payload memory)."""
from __future__ import annotations

import os
import sys

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
    "Data/Normal/#include signal.h by Kurokotei.txt",
    "Data/Easy/Game On, Beats High by Lappy.txt",
]


def measure(fp):
    d = read_song_file(fp)
    ts = np.asarray(d.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(d.get("note_types", []), np.int16).reshape(-1)
    lanes = np.asarray(d.get("lanes", []), np.int32).reshape(-1)
    n = int(ts.shape[0])
    lnt = float(d.get("song_details", {}).get("Last Note Time", ts[-1]))
    lon = int(np.count_nonzero(nt == 2))
    perfect_candidates = build_perfect_candidate_envelope_sec(ts, nt)
    perfect_floor = build_perfect_floor_envelope_sec(ts, nt)
    pay = tef.build_timeline_frontier_grid_payload(
        song_slot=0, total_notes=n, long_notes=lon, last_note_time=lnt, song_key=None,
        timestamps=ts, perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor, lanes=lanes, ref_ft=FT, ref_ff=FF)
    fc = np.asarray(pay.grid_frontier_count).reshape(-1)
    pool = int(getattr(pay, "frontier_pool_used", -1))
    return n, int(fc.sum()), int(fc.max()), float(fc[fc > 0].mean()), pool


def main():
    print(f"{'notes':>6} {'sum_fc':>8} {'max_fc':>6} {'mean_fc':>8} {'pool':>7}  song")
    for rel in SONGS:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            print(f"  (missing: {rel})")
            continue
        n, s, mx, mn, pool = measure(fp)
        print(f"{n:>6} {s:>8} {mx:>6} {mn:>8.2f} {pool:>7}  {os.path.basename(fp)[:40]}")


if __name__ == "__main__":
    main()
