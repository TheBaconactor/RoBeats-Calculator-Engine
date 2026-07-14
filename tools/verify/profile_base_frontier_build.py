"""Profile the engine-physical Base frontier build on representative charts."""
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


def _ref_arrays():
    try:
        from gear_optimizer.helpers.song_helpers.ref_array_builder import (
            get_exact_replay_ref_arrays_cached,
        )

        ra = get_exact_replay_ref_arrays_cached()
        ft = np.asarray(ra.get("Fever Time", ()), np.float32).reshape(-1)
        ff = np.asarray(ra.get("Fever Fill Rate", ()), np.float32).reshape(-1)
        if ft.shape[0] == GRID and ff.shape[0] == GRID:
            return ft, ff
    except Exception as e:
        print(f"(ref arrays unavailable: {e}; using synthetic axes)")
    # synthetic but realistic-shaped stat axes (multipliers ~0.5..1.6)
    ft = np.linspace(0.5, 1.6, GRID).astype(np.float32)
    ff = np.linspace(0.5, 1.6, GRID).astype(np.float32)
    return ft, ff


def profile_song(fp, ref_ft, ref_ff, reps=3):
    data = read_song_file(fp)
    ts = np.asarray(data.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(data.get("note_types", []), np.int16).reshape(-1)
    lanes = np.asarray(data.get("lanes", []), np.int32).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    last_note_time = float(data.get("song_details", {}).get("Last Note Time", ts[-1]))
    long_notes = int(np.count_nonzero(nt == 2))  # held heads ~ long notes (approx)
    perfect_candidates = build_perfect_candidate_envelope_sec(ts, nt)
    perfect_floor = build_perfect_floor_envelope_sec(ts, nt)

    # time the full payload build
    t_full = []
    for _ in range(reps):
        t0 = time.perf_counter()
        tef.build_timeline_frontier_grid_payload(
            song_slot=0, total_notes=n, long_notes=long_notes, last_note_time=last_note_time,
            song_key=None, timestamps=ts, perfect_candidate_timestamps=perfect_candidates,
            perfect_floor_timestamps=perfect_floor, lanes=lanes, ref_ft=ref_ft, ref_ff=ref_ff,
        )
        t_full.append(time.perf_counter() - t0)

    full = min(t_full)
    return n, full


def main():
    ref_ft, ref_ff = _ref_arrays()
    songs = [
        "Data/Hard/Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt",       # worst held-tail, G~1815
        "Data/Hard/#include signal.h by Kurokotei.txt",
        "Data/Normal/#include signal.h by Kurokotei.txt",
        "Data/Easy/Game On, Beats High by Lappy.txt",
    ]
    print(f"{'notes':>6} {'full(ms)':>9}  song")
    for rel in songs:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            # fall back to any file matching the basename stem
            import glob
            cand = glob.glob(os.path.join(ROOT, os.path.dirname(rel), "*" + os.path.basename(rel).split(" by ")[0].split("[")[0].strip() + "*"))
            fp = cand[0] if cand else None
        if not fp or not os.path.exists(fp):
            print(f"  (missing: {rel})")
            continue
        r = profile_song(fp, ref_ft, ref_ff)
        if r is None:
            print(f"  (unreadable: {rel})")
            continue
        n, full = r
        print(f"{n:>6} {full*1e3:>9.1f}  {os.path.basename(fp)[:46]}")


if __name__ == "__main__":
    main()
