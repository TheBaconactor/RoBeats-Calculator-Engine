"""Quantify the fever-extent impact of the per-note (vs chord-collapsed) FG envelopes on real
songs: for every note as a candidate fever activation, compare the per-note extent against the
old grouped extent, using each song's base Fever Time as the fever duration. Reports the
potential per-activation fever-note gains across the corpus."""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.data.song_io import read_song_file  # noqa: E402
from gear_optimizer.solver.timing_envelope import (  # noqa: E402
    build_per_note_perfect_window_ms,
    floor_to_int_ms,
    prepare_grouped_timing_windows,
)

LO, HI, TAIL, MULT = -20, 40, 3, 2


def envelopes(ts_sec, nt):
    low, high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=LO, perfect_upper_ms=HI, held_tail_type=TAIL, held_tail_time_multiplier=MULT
    )
    low = np.asarray(low, np.int64)
    high = np.asarray(high, np.int64)
    q = np.asarray(floor_to_int_ms(ts_sec), np.int64)
    # per-note (the fix)
    cand_pn = (q + high).astype(np.float64) * 1e-3
    floor_pn = np.maximum.accumulate(q + low).astype(np.float64) * 1e-3
    # grouped (the old chord-collapse)
    prep = prepare_grouped_timing_windows(
        ts_sec, note_low_ms=low.astype(np.int32), note_high_ms=high.astype(np.int32), quantize_ms=True
    )
    s = np.asarray(prep["group_starts"], np.int64)
    e = np.asarray(prep["group_ends"], np.int64)
    b = np.asarray(prep["group_base_t"], np.int64)
    gl = np.asarray(prep["group_low"], np.int64)
    gh = np.asarray(prep["group_high"], np.int64)
    n = q.shape[0]
    cand_g = np.empty(n, np.int64)
    floor_g = np.empty(n, np.int64)
    for gi in range(s.shape[0]):
        cand_g[int(s[gi]):int(e[gi])] = b[gi] + gh[gi]
        floor_g[int(s[gi]):int(e[gi])] = b[gi] + gl[gi]
    np.maximum.accumulate(floor_g, out=floor_g)
    return cand_pn, floor_pn, (cand_g.astype(np.float64) * 1e-3), (floor_g.astype(np.float64) * 1e-3)


def measure_song(fp):
    data = read_song_file(fp)
    ts = np.asarray(data.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(data.get("note_types", []), np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    try:
        rft = float(str(data.get("song_details", {}).get("Fever Time", "")).strip())
    except (TypeError, ValueError):
        return None
    if rft <= 0:
        rft = float(data.get("song_details", {}).get("Last Note Time", ts[-1])) * 0.15 + 0.15
    cand_pn, floor_pn, cand_g, floor_g = envelopes(ts, nt.astype(np.int16))
    a = np.arange(n)
    e_pn = np.searchsorted(floor_pn, (cand_pn + rft).astype(np.float32), side="left")
    e_g = np.searchsorted(floor_g, (cand_g + rft).astype(np.float32), side="left")
    ext_pn = np.maximum(e_pn - a, 1)
    ext_g = np.maximum(e_g - a, 1)
    gain = np.maximum(0, ext_pn - ext_g)
    return {
        "n": n,
        "activations_with_gain": int(np.count_nonzero(gain > 0)),
        "total_gain": int(gain.sum()),
        "max_gain": int(gain.max()) if n else 0,
    }


def main():
    grand = {"songs": 0, "notes": 0, "act_gain": 0, "total_gain": 0, "songs_with_gain": 0, "max_gain": 0}
    for diff in ("Easy", "Normal", "Hard"):
        for fp in sorted(glob.glob(os.path.join(ROOT, "Data", diff, "*.txt"))):
            r = measure_song(fp)
            if r is None:
                continue
            grand["songs"] += 1
            grand["notes"] += r["n"]
            grand["act_gain"] += r["activations_with_gain"]
            grand["total_gain"] += r["total_gain"]
            grand["max_gain"] = max(grand["max_gain"], r["max_gain"])
            if r["activations_with_gain"] > 0:
                grand["songs_with_gain"] += 1
    print("=== Per-note vs chord-collapsed FG fever extent (all notes as candidate activation) ===")
    print(f"songs scanned:                 {grand['songs']}")
    print(f"total notes (candidate acts):  {grand['notes']:,}")
    print(f"candidate activations w/ gain: {grand['act_gain']:,}  "
          f"({100.0 * grand['act_gain'] / max(1, grand['notes']):.3f}% of all notes)")
    print(f"sum of fever-note gains:       {grand['total_gain']:,}")
    print(f"songs with >=1 gain activation:{grand['songs_with_gain']}  "
          f"({100.0 * grand['songs_with_gain'] / max(1, grand['songs']):.1f}%)")
    print(f"max single-activation gain:    {grand['max_gain']} fever notes")


if __name__ == "__main__":
    main()
