"""Estimate the per-song group-count growth (and the O(G^2) context-build cost growth) if the
base timeline frontier split held-tail-mixed chords into per-window groups -- i.e. grouped by
(quantized ms, window_low, window_high) instead of (quantized ms) alone. Songs without a
held-tail-mixed chord are unaffected (identical grouping)."""
from __future__ import annotations

import glob
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.data.song_io import read_song_file  # noqa: E402
from gear_optimizer.solver.timing_envelope import build_per_note_perfect_window_ms, floor_to_int_ms  # noqa: E402


def measure(fp):
    data = read_song_file(fp)
    ts = np.asarray(data.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(data.get("note_types", []), np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n == 0 or nt.shape[0] != n:
        return None
    low, high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=-20, perfect_upper_ms=40, held_tail_type=3, held_tail_time_multiplier=2
    )
    q = np.asarray(floor_to_int_ms(ts), np.int64)
    # current grouping: distinct quantized ms
    cur = int(np.count_nonzero(np.diff(q) != 0)) + 1 if n else 0
    # split grouping: distinct (ts, low, high) consecutive runs
    low = np.asarray(low, np.int64)
    high = np.asarray(high, np.int64)
    changed = (np.diff(q) != 0) | (np.diff(low) != 0) | (np.diff(high) != 0)
    new = int(np.count_nonzero(changed)) + 1 if n else 0
    return cur, new, n


def main():
    rows = []
    for diff in ("Easy", "Normal", "Hard"):
        for fp in sorted(glob.glob(os.path.join(ROOT, "Data", diff, "*.txt"))):
            r = measure(fp)
            if r:
                rows.append((r[0], r[1], r[2], os.path.basename(fp)))
    cur = np.array([r[0] for r in rows], float)
    new = np.array([r[1] for r in rows], float)
    ratio = new / np.maximum(cur, 1)
    # O(G^2) context-build cost proxy
    cost_cur = (cur ** 2).sum()
    cost_new = (new ** 2).sum()
    unaffected = int(np.count_nonzero(new == cur))
    print(f"songs: {len(rows)}   unaffected (identical grouping): {unaffected} ({100*unaffected/len(rows):.1f}%)")
    print(f"group-count ratio (new/old): mean={ratio.mean():.3f}  median={np.median(ratio):.3f}  "
          f"p95={np.percentile(ratio,95):.3f}  max={ratio.max():.3f}")
    print(f"O(G^2) context-build cost proxy: total +{100*(cost_new-cost_cur)/cost_cur:.1f}%  "
          f"(worst song G^2 x{(new**2/np.maximum(cur**2,1)).max():.2f})")
    worst = sorted(rows, key=lambda r: (r[1] / max(r[0], 1)), reverse=True)[:8]
    print("top group-growth songs (old->new groups, ratio):")
    for c, nw, nn, name in worst:
        print(f"  {int(c):5}->{int(nw):5}  x{nw/max(c,1):.2f}  (n={nn})  {name[:50]}")


if __name__ == "__main__":
    main()
