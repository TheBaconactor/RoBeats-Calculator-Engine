"""Definitive bit-identical check for the exit-enumeration numba kernel: compare the JIT
context enumerator against the independent Python row enumerator (the cross-check reference)
across a broad sweep of (activation_group, act_lo, act_hi, d_ms) on real-song contexts."""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.data.song_io import read_song_file  # noqa: E402
from gear_optimizer.solver import timeline_exact_frontier as tef  # noqa: E402
from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope  # noqa: E402


def ctx_for(fp):
    d = read_song_file(fp)
    ts = np.asarray(d.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(d.get("note_types", []), np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    p = prepare_perfect_timing_envelope(ts, nt, perfect_lower_ms=-20, perfect_upper_ms=40,
                                        held_tail_type=3, held_tail_time_multiplier=2, quantize_ms=True)
    gs = np.asarray(p["group_starts"], np.int32); ge = np.asarray(p["group_ends"], np.int32)
    gb = np.asarray(p["group_base_t"], np.int32); gl = np.asarray(p["group_low"], np.int32)
    gh = np.asarray(p["group_high"], np.int32)
    ngi = np.repeat(np.arange(gs.shape[0], dtype=np.int32), (ge - gs).astype(np.int32))
    ctx = tef._build_grouped_timeline_context(n, group_starts=gs, group_ends=ge, group_base_t_ms=gb,
                                              group_low_ms=gl, group_high_ms=gh, note_group_idx=ngi)
    return ctx, gs, gb, gl, gh, n


def main():
    files = []
    for diff in ("Easy", "Normal", "Hard"):
        files += sorted(glob.glob(os.path.join(ROOT, "Data", diff, "*.txt")))[::300]
    bands = [(-40, 80), (-40, 40), (-20, 40), (0, 40), (20, 80), (-10, 10), (40, 80)]
    d_set = [0, 200, 500, 1000, 5000, 20000, 60000]
    total = 0
    mism = 0
    for fp in files[:6]:
        r = ctx_for(fp)
        if r is None:
            continue
        ctx, gs, gb, gl, gh, n = r
        G = int(ctx.gcount)
        step = max(1, G // 60)  # sample activation groups
        for s in range(0, G, step):
            for lo, hi in bands:
                for dm in d_set:
                    row = tef._enumerate_first_exit_boundary_intervals_from_activation_band(
                        total_notes=n, group_starts=gs, group_base_t_ms=gb, group_low_ms=gl,
                        group_high_ms=gh, activation_group=s, act_lo=lo, act_hi=hi, d_ms=dm,
                    )
                    jit = tef._enumerate_first_exit_boundary_intervals_from_context(
                        ctx, activation_group=s, act_lo=lo, act_hi=hi, d_ms=dm,
                    )
                    total += 1
                    if [tuple(int(x) for x in t) for t in row] != [tuple(int(x) for x in t) for t in jit]:
                        mism += 1
                        if mism <= 5:
                            print(f"  MISMATCH {os.path.basename(fp)[:30]} s={s} lo={lo} hi={hi} d={dm}")
                            print(f"    row={row}\n    jit={jit}")
    print(f"\ncompared {total} (activation_group, band, d_ms) cases across {min(6, len(files))} songs")
    print(f"mismatches: {mism}   => {'BIT-IDENTICAL (PASS)' if mism == 0 else 'FAILED'}")


if __name__ == "__main__":
    main()
