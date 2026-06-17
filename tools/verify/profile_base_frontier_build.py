"""Profile the base timeline-frontier per-song build: how much wall-clock is the O(G^2) context
build vs the DP loop over the 161x161 grid? This decides whether the chord-split fix's group
growth (which only inflates the context build) is a real runtime regression or a rounding error.
"""
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


def _group_payload(ts, nt):
    prepared = prepare_perfect_timing_envelope(
        ts, nt, perfect_lower_ms=-20, perfect_upper_ms=40,
        held_tail_type=3, held_tail_time_multiplier=2, quantize_ms=True,
    )
    gs = np.asarray(prepared["group_starts"], np.int32)
    ge = np.asarray(prepared["group_ends"], np.int32)
    gb = np.asarray(prepared["group_base_t"], np.int32)
    gl = np.asarray(prepared["group_low"], np.int32)
    gh = np.asarray(prepared["group_high"], np.int32)
    n = int(ts.shape[0])
    lengths = (ge - gs).astype(np.int32)
    note_group_idx = np.repeat(np.arange(int(gs.shape[0]), dtype=np.int32), lengths)
    return gs, ge, gb, gl, gh, note_group_idx, int(gs.shape[0])


def profile_song(fp, ref_ft, ref_ff, reps=3):
    data = read_song_file(fp)
    ts = np.asarray(data.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(data.get("note_types", []), np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    last_note_time = float(data.get("song_details", {}).get("Last Note Time", ts[-1]))
    long_notes = int(np.count_nonzero(nt == 2))  # held heads ~ long notes (approx)
    gs, ge, gb, gl, gh, ngi, G = _group_payload(ts, nt)

    # time the context build alone
    t_ctx = []
    for _ in range(reps):
        t0 = time.perf_counter()
        tef._build_grouped_timeline_context(
            n, group_starts=gs, group_ends=ge, group_base_t_ms=gb,
            group_low_ms=gl, group_high_ms=gh, note_group_idx=ngi,
        )
        t_ctx.append(time.perf_counter() - t0)

    # time the full payload build
    t_full = []
    for _ in range(reps):
        t0 = time.perf_counter()
        tef.build_timeline_frontier_grid_payload(
            song_slot=0, total_notes=n, long_notes=long_notes, last_note_time=last_note_time,
            song_key=None, group_starts=gs, group_ends=ge, group_base_t_ms=gb,
            group_low_ms=gl, group_high_ms=gh, note_group_idx=ngi, ref_ft=ref_ft, ref_ff=ref_ff,
        )
        t_full.append(time.perf_counter() - t0)

    ctx = min(t_ctx)
    full = min(t_full)
    return G, n, ctx, full


def main():
    ref_ft, ref_ff = _ref_arrays()
    songs = [
        "Data/Hard/Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt",       # worst held-tail, G~1815
        "Data/Hard/#include signal.h by Kurokotei.txt",
        "Data/Normal/#include signal.h by Kurokotei.txt",
        "Data/Easy/Game On, Beats High by Lappy.txt",
    ]
    print(f"{'G':>6} {'notes':>6} {'ctx(ms)':>9} {'full(ms)':>9} {'ctx%':>6}  song")
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
        G, n, ctx, full = r
        print(f"{G:>6} {n:>6} {ctx*1e3:>9.1f} {full*1e3:>9.1f} {100*ctx/max(full,1e-9):>5.1f}%  {os.path.basename(fp)[:46]}")


if __name__ == "__main__":
    main()
