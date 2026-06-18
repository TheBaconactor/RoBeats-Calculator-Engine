"""Verify the base timeline-frontier chord-tied held-tail fix: A/B the old (timestamp-only)
grouping vs the new (timestamp+window) split grouping, on a held-tail-chord chart (fever count
must rise to the brute-force legal max) and on a no-held-tail chart (must be bit-identical)."""
from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.solver import timeline_exact_frontier as tef  # noqa: E402
from gear_optimizer.solver.timing_envelope import (  # noqa: E402
    build_per_note_perfect_window_ms,
    floor_to_int_ms,
)

LO, HI, TAIL, MULT = -20, 40, 3, 2


def _grouping(chart_ms, note_types, *, split_window: bool):
    """Build group arrays. split_window=False => old (ts-only); True => new (ts+window)."""
    nt = np.asarray(note_types, np.int16)
    low, high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=LO, perfect_upper_ms=HI, held_tail_type=TAIL, held_tail_time_multiplier=MULT
    )
    low = np.asarray(low, np.int32)
    high = np.asarray(high, np.int32)
    ts_ms = np.asarray(floor_to_int_ms(np.asarray(chart_ms, np.float32) / np.float32(1000.0)), np.int32)
    n = len(chart_ms)
    if split_window:
        chg = (ts_ms[1:] != ts_ms[:-1]) | (low[1:] != low[:-1]) | (high[1:] != high[:-1])
    else:
        chg = ts_ms[1:] != ts_ms[:-1]
    starts = np.concatenate([[0], np.nonzero(chg)[0] + 1]).astype(np.int32)
    ends = np.concatenate([starts[1:], [n]]).astype(np.int32)
    G = int(starts.shape[0])
    base = ts_ms[starts].astype(np.int32)
    glow = np.empty(G, np.int32)
    ghigh = np.empty(G, np.int32)
    for g in range(G):
        s, e = int(starts[g]), int(ends[g])
        rl = int(np.max(low[s:e]))
        rh = int(np.min(high[s:e]))
        glow[g] = min(rl, rh)
        ghigh[g] = max(rl, rh)
    ngi = np.repeat(np.arange(G, dtype=np.int32), (ends - starts).astype(np.int32))
    return starts, ends, base, glow, ghigh, ngi, G


def _max_fever(chart_ms, note_types, *, fill_count, d_ms, split_window):
    starts, ends, base, glow, ghigh, ngi, G = _grouping(chart_ms, note_types, split_window=split_window)
    ctx = tef._build_grouped_timeline_context(
        len(chart_ms), group_starts=starts, group_ends=ends, group_base_t_ms=base,
        group_low_ms=glow, group_high_ms=ghigh, note_group_idx=ngi,
    )
    pack = tef._build_exact_timeline_frontier_from_context(ctx, fill_count=fill_count, d_ms=d_ms)
    best = 0
    for surf in pack.surfaces:
        hb = surf.head_bits
        fever = bin(int(hb[0]) | (int(hb[1]) << 32) | (int(hb[2]) << 64) | (int(hb[3]) << 96)).count("1")
        fever += int(surf.body_fever)
        best = max(best, fever)
    return best, G


def _brute_base(chart_ms, a, rft_ms, note_types):
    """All-Perfect max fever run from activation a, per-note windows (the legal max)."""
    import itertools
    nt = np.asarray(note_types, np.int16)
    low, high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=LO, perfect_upper_ms=HI, held_tail_type=TAIL, held_tail_time_multiplier=MULT
    )
    low = np.asarray(low, np.int64); high = np.asarray(high, np.int64)
    n = len(chart_ms)
    grids = [range(int(low[i]), int(high[i]) + 1, 5) for i in range(n)]
    best = 0
    for combo in itertools.product(*grids):
        ev = [chart_ms[i] + combo[i] for i in range(n)]
        if any(ev[i] < ev[i - 1] for i in range(1, n)):
            continue
        fe = ev[a] + rft_ms
        best = max(best, sum(1 for i in range(a, n) if ev[i] < fe))
    return best


def main():
    # Held-tail ACTIVATION chord: idx 3 (held tail) chorded with idx 2 (normal) at 200 ms.
    # fill_count=4 => first activation note = 0 + (4-1) = idx 3. rft (d_ms) = 1000.
    chart = [0, 100, 200, 200, 1260, 1500]
    nt = [1, 1, 1, 3, 1, 1]
    old, go = _max_fever(chart, nt, fill_count=4, d_ms=1000, split_window=False)
    new, gn = _max_fever(chart, nt, fill_count=4, d_ms=1000, split_window=True)
    brute = _brute_base(chart, 3, 1000, nt)
    print("=== held-tail-chord activation (idx3=held tail @200, chord with idx2 normal) ===")
    print(f"  old grouping (ts-only): G={go}  max fever={old}")
    print(f"  new grouping (ts+win) : G={gn}  max fever={new}")
    print(f"  brute-force legal max (per-note): {brute}")
    print(f"  => fix gains {new - old} fever note(s); new == brute? {new == brute}")

    # No held tails -> grouping identical -> frontier bit-identical for several cells.
    chart2 = [0, 100, 200, 200, 1260, 1500]
    nt2 = [1, 1, 1, 1, 1, 1]
    identical = True
    for fc in (2, 3, 4, 5):
        for dm in (500, 1000, 1500):
            o, _ = _max_fever(chart2, nt2, fill_count=fc, d_ms=dm, split_window=False)
            n2, _ = _max_fever(chart2, nt2, fill_count=fc, d_ms=dm, split_window=True)
            if o != n2:
                identical = False
                print(f"  MISMATCH no-tail fc={fc} dm={dm}: old={o} new={n2}")
    print(f"\n=== no-held-tail control: old==new across cells? {identical} ===")


if __name__ == "__main__":
    main()
