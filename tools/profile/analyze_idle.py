"""Ad-hoc idle analysis for Issue #34.

Reads a profile run dir and reports GPU compute idle fraction (typeperf 0% runs)
and inter-dispatch gaps from profile_events.jsonl. Read-only diagnostic.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def analyze_typeperf(path: Path) -> None:
    if not path.exists():
        print(f"  typeperf: MISSING {path}")
        return
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        print("  typeperf: empty")
        return
    header = rows[0]
    # Find compute engine columns (engtype_Compute) on the AMD adapter.
    compute_cols = [
        i
        for i, h in enumerate(header)
        if "engtype_3D" not in h and "Compute" in h and "Utilization" in h
    ]
    if not compute_cols:
        # Fallback: any utilization column mentioning Compute.
        compute_cols = [i for i, h in enumerate(header) if "Compute" in h]
    print(f"  typeperf cols: {len(header)} total, {len(compute_cols)} compute util cols")
    samples = []
    for row in rows[1:]:
        if len(row) < 2:
            continue
        vals = []
        for i in compute_cols:
            if i < len(row):
                try:
                    vals.append(float(row[i]))
                except ValueError:
                    pass
        if vals:
            samples.append(max(vals))
    if not samples:
        print("  typeperf: no compute samples parsed")
        return
    n = len(samples)
    near_zero = [s for s in samples if s < 1.0]
    busy = [s for s in samples if s >= 1.0]
    mean = sum(samples) / n
    # Longest consecutive run of near-zero samples.
    longest = 0
    cur = 0
    for s in samples:
        if s < 1.0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    print(f"  typeperf compute: n={n} mean={mean:.1f}%")
    print(
        f"    idle(<1%) samples={len(near_zero)} ({100.0*len(near_zero)/n:.1f}%) "
        f"longest_idle_run={longest} samples (~{longest}s @1s interval)"
    )
    if busy:
        print(f"    busy mean(>=1%)={sum(busy)/len(busy):.1f}%")
    # Utilization histogram buckets.
    buckets = [0, 1, 25, 50, 75, 90, 101]
    labels = ["<1", "1-25", "25-50", "50-75", "75-90", "90-100"]
    counts = [0] * (len(buckets) - 1)
    for s in samples:
        for bi in range(len(buckets) - 1):
            if buckets[bi] <= s < buckets[bi + 1]:
                counts[bi] += 1
                break
    print("    util histogram: " + ", ".join(
        f"{labels[i]}%={counts[i]}({100.0*counts[i]/n:.0f}%)" for i in range(len(counts))
    ))
    # Idle run positions (as index fraction of timeline).
    runs = []
    start = None
    for i, s in enumerate(samples):
        if s < 1.0 and start is None:
            start = i
        elif s >= 1.0 and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, n - 1))
    if runs:
        pos = ", ".join(
            f"[{a}-{b}]({100.0*a/n:.0f}%,len={b-a+1})" for a, b in runs if (b - a + 1) >= 2
        )
        print(f"    idle runs(len>=2): {pos}")


def analyze_events(path: Path) -> None:
    if not path.exists():
        print(f"  events: MISSING {path}")
        return
    dispatch = []
    comps: dict[str, int] = {}
    events: dict[str, int] = {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            comp = obj.get("component", "")
            ev = obj.get("event", "")
            comps[comp] = comps.get(comp, 0) + 1
            events[ev] = events.get(ev, 0) + 1
            ts = obj.get("ts_wall")
            if ev in ("dispatch_start", "dispatch_done") and isinstance(ts, (int, float)):
                dispatch.append((float(ts), ev))
    print(f"  events components: {comps}")
    starts = sorted(t for t, e in dispatch if e == "dispatch_start")
    dones = sorted(t for t, e in dispatch if e == "dispatch_done")
    print(f"  dispatch_start={len(starts)} dispatch_done={len(dones)}")
    # Inter-dispatch gap = next start - previous done.
    if starts and dones:
        gaps = []
        di = 0
        for s in starts:
            # find last done before s
            prev = [d for d in dones if d <= s]
            if prev:
                gaps.append(s - prev[-1])
        gaps = [g for g in gaps if g >= 0]
        if gaps:
            gaps_sorted = sorted(gaps)
            total = sum(gaps)
            print(
                f"  inter-dispatch gaps: n={len(gaps)} total={total:.1f}s "
                f"max={max(gaps):.2f}s p50={gaps_sorted[len(gaps)//2]:.3f}s"
            )


def main() -> None:
    d = Path(sys.argv[1])
    print(f"== {d.name} ==")
    analyze_typeperf(d / "gpu_typeperf.csv")
    analyze_events(d / "profile_events.jsonl")


if __name__ == "__main__":
    main()
