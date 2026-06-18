"""Scan the real song corpus for chord-tied held tails (the necessary condition for the
FG/base chord-collapse fever under-count).

A held tail (note_type==3, Perfect window [-40,+80]) that shares a *quantized* ms timestamp
with any narrower-window note (type != 3, window [-20,+40]) has its window collapsed to the
chord intersection by `prepare_grouped_timing_windows` (group_low = max(lows), group_high =
min(highs)). That is the only situation where a held tail's wider reach is lost.

We replicate production grouping EXACTLY: build per-note windows with
`build_per_note_perfect_window_ms`, run `prepare_grouped_timing_windows`, and flag any group
whose held-tail members are capped (group_low > -40 or group_high < +80 while the group
contains a tail).

Run: python tools/verify/scan_chord_tied_held_tails.py
"""

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
    prepare_grouped_timing_windows,
)

HELD_TAIL_TYPE = 3
HELD_TAIL_MULT = 2
PERFECT_LO, PERFECT_HI = -20, 40


def scan_song(fp: str) -> dict | None:
    data = read_song_file(fp)
    ts = np.asarray(data.get("timestamps", []), dtype=np.float32).reshape(-1)
    nt = np.asarray(data.get("note_types", []), dtype=np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None

    low, high = build_per_note_perfect_window_ms(
        nt,
        perfect_lower_ms=PERFECT_LO,
        perfect_upper_ms=PERFECT_HI,
        held_tail_type=HELD_TAIL_TYPE,
        held_tail_time_multiplier=HELD_TAIL_MULT,
    )
    prepared = prepare_grouped_timing_windows(
        ts,
        note_low_ms=np.asarray(low, dtype=np.int32),
        note_high_ms=np.asarray(high, dtype=np.int32),
        quantize_ms=True,
    )
    starts = np.asarray(prepared["group_starts"], dtype=np.int64)
    ends = np.asarray(prepared["group_ends"], dtype=np.int64)
    g_low = np.asarray(prepared["group_low"], dtype=np.int64)
    g_high = np.asarray(prepared["group_high"], dtype=np.int64)

    n_tails = int(np.count_nonzero(nt == HELD_TAIL_TYPE))
    n_groups = int(starts.shape[0])
    n_chords = 0           # groups with >1 member
    n_tail_groups = 0      # groups containing >=1 held tail
    n_capped_groups = 0    # groups where a held tail's [-40,+80] is collapsed
    n_capped_tail_notes = 0
    capped_examples: list[tuple[int, int, int]] = []  # (group_size, g_low, g_high)
    for gi in range(n_groups):
        s, e = int(starts[gi]), int(ends[gi])
        size = e - s
        if size > 1:
            n_chords += 1
        types = nt[s:e]
        has_tail = bool(np.any(types == HELD_TAIL_TYPE))
        if not has_tail:
            continue
        n_tail_groups += 1
        # capped iff the group window is narrower than the tail's own [-40,+80]
        capped = int(g_low[gi]) > PERFECT_LO * HELD_TAIL_MULT or int(g_high[gi]) < PERFECT_HI * HELD_TAIL_MULT
        if capped:
            n_capped_groups += 1
            n_capped_tail_notes += int(np.count_nonzero(types == HELD_TAIL_TYPE))
            if len(capped_examples) < 3:
                capped_examples.append((size, int(g_low[gi]), int(g_high[gi])))
    return {
        "n": n,
        "n_tails": n_tails,
        "n_groups": n_groups,
        "n_chords": n_chords,
        "n_tail_groups": n_tail_groups,
        "n_capped_groups": n_capped_groups,
        "n_capped_tail_notes": n_capped_tail_notes,
        "capped_examples": capped_examples,
    }


def main() -> None:
    grand = {
        "songs": 0,
        "songs_with_tails": 0,
        "songs_with_capped": 0,
        "notes": 0,
        "tails": 0,
        "chords": 0,
        "tail_groups": 0,
        "capped_groups": 0,
        "capped_tail_notes": 0,
    }
    worst: list[tuple[int, str]] = []
    for diff in ("Easy", "Normal", "Hard"):
        d = os.path.join(ROOT, "Data", diff)
        files = sorted(glob.glob(os.path.join(d, "*.txt")))
        diff_capped = 0
        diff_songs = 0
        diff_capped_songs = 0
        for fp in files:
            r = scan_song(fp)
            if r is None:
                continue
            diff_songs += 1
            grand["songs"] += 1
            grand["notes"] += r["n"]
            grand["tails"] += r["n_tails"]
            grand["chords"] += r["n_chords"]
            grand["tail_groups"] += r["n_tail_groups"]
            grand["capped_groups"] += r["n_capped_groups"]
            grand["capped_tail_notes"] += r["n_capped_tail_notes"]
            if r["n_tails"] > 0:
                grand["songs_with_tails"] += 1
            if r["n_capped_groups"] > 0:
                grand["songs_with_capped"] += 1
                diff_capped_songs += 1
                worst.append((r["n_capped_groups"], os.path.basename(fp)))
            diff_capped += r["n_capped_groups"]
        print(f"[{diff:6}] songs={diff_songs:4}  capped-chord-tail groups={diff_capped:5}  "
              f"songs_with_capped={diff_capped_songs}")

    print("\n=== CORPUS TOTALS ===")
    print(f"songs scanned:            {grand['songs']}")
    print(f"total notes:              {grand['notes']:,}")
    print(f"total held tails:         {grand['tails']:,}")
    print(f"songs with any held tail: {grand['songs_with_tails']}")
    print(f"total chords (groups>1):  {grand['chords']:,}")
    print(f"groups containing a tail: {grand['tail_groups']:,}")
    print(f"CAPPED chord-tail groups: {grand['capped_groups']:,}  "
          f"({100.0 * grand['capped_groups'] / max(1, grand['tail_groups']):.2f}% of tail groups, "
          f"{100.0 * grand['capped_groups'] / max(1, grand['chords']):.3f}% of all chords)")
    print(f"capped held-tail notes:   {grand['capped_tail_notes']:,}  "
          f"({100.0 * grand['capped_tail_notes'] / max(1, grand['tails']):.3f}% of all held tails)")
    print(f"songs with >=1 capped:    {grand['songs_with_capped']}  "
          f"({100.0 * grand['songs_with_capped'] / max(1, grand['songs']):.1f}% of songs)")
    worst.sort(reverse=True)
    print("\ntop 10 songs by capped chord-tail groups:")
    for cnt, name in worst[:10]:
        print(f"  {cnt:4}  {name}")


if __name__ == "__main__":
    main()
