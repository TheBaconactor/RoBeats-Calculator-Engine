"""Aggregate wall-clock of the base frontier build over a representative song sample. Run twice
(current vs git-stashed baseline) to size the chord-split fix's real prebuild cost."""
from __future__ import annotations

import glob
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


def build_one(fp):
    d = read_song_file(fp)
    ts = np.asarray(d.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(d.get("note_types", []), np.int16).reshape(-1)
    lanes = np.asarray(d.get("lanes", []), np.int32).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    lnt = float(d.get("song_details", {}).get("Last Note Time", ts[-1]))
    lon = int(np.count_nonzero(nt == 2))
    perfect_candidates = build_perfect_candidate_envelope_sec(ts, nt)
    perfect_floor = build_perfect_floor_envelope_sec(ts, nt)
    t0 = time.perf_counter()
    tef.build_timeline_frontier_grid_payload(
        song_slot=0, total_notes=n, long_notes=lon, last_note_time=lnt, song_key=None,
        timestamps=ts, perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor, lanes=lanes, ref_ft=FT, ref_ff=FF,
    )
    return time.perf_counter() - t0


def main():
    files = []
    for diff in ("Easy", "Normal", "Hard"):
        files += sorted(glob.glob(os.path.join(ROOT, "Data", diff, "*.txt")))[::40]  # every 40th
    total = 0.0
    cnt = 0
    for fp in files:
        try:
            t = build_one(fp)
        except Exception:
            t = None
        if t is not None:
            total += t
            cnt += 1
    print(f"sample songs built: {cnt}   total base-build wall-clock: {total:.2f}s   mean/song: {1000*total/max(cnt,1):.1f}ms")


if __name__ == "__main__":
    main()
