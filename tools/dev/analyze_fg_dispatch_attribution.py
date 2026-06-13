"""
Attribute FG dispatch-window time from profile_events.jsonl.

Reconciles inflight_fg_worker dispatch_start/done windows with per-batch
fg_score_engine events (build wait, finalize, surface pack, submit wait,
owner queue/exec, host wait, materialize, pipeline poll).

Usage:
  python tools/dev/analyze_fg_dispatch_attribution.py artifacts/profile/<run_id>
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = str(line or "").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                events.append(obj)
    events.sort(key=lambda e: float(e.get("ts_wall", 0.0) or 0.0))
    return events


def _sum_metric(events: list[dict[str, Any]], key: str) -> float:
    total = 0.0
    for event in events:
        metrics = event.get("metrics")
        if not isinstance(metrics, dict):
            continue
        total += float(metrics.get(key, 0.0) or 0.0)
    return total


def _dispatch_windows(events: list[dict[str, Any]]) -> tuple[list[tuple[float, float, str]], int, float]:
    per_song: dict[str, dict[str, float]] = defaultdict(dict)
    for event in events:
        if event.get("component") != "inflight_fg_worker":
            continue
        song_key = str(event.get("song_key", "") or "")
        if not song_key:
            continue
        ev = str(event.get("event", "") or "")
        ts = float(event.get("ts_wall", 0.0) or 0.0)
        if ev == "dispatch_start":
            per_song[song_key]["start"] = ts
        elif ev == "dispatch_done":
            per_song[song_key]["done"] = ts
            metrics = event.get("metrics") or {}
            per_song[song_key]["owner_exec_ms"] = float(metrics.get("owner_exec_ms", 0.0) or 0.0)
            per_song[song_key]["owner_queue_ms"] = float(metrics.get("owner_queue_ms", 0.0) or 0.0)

    windows: list[tuple[float, float, str]] = []
    for song_key, data in per_song.items():
        if "start" not in data or "done" not in data:
            continue
        windows.append((float(data["start"]), float(data["done"]), song_key))

    points: list[tuple[float, int]] = []
    for start, done, _song_key in windows:
        points.append((start, 1))
        points.append((done, -1))
    points.sort()
    cur = 0
    max_concurrency = 0
    weighted_wall = 0.0
    prev_t: float | None = None
    for ts, delta in points:
        if prev_t is not None and cur > 0:
            weighted_wall += (float(ts) - float(prev_t)) * float(cur)
        cur += int(delta)
        max_concurrency = max(max_concurrency, cur)
        prev_t = float(ts)

    return windows, int(max_concurrency), float(weighted_wall)


def analyze(run_dir: Path) -> None:
    events_path = run_dir / "profile_events.jsonl"
    if not events_path.exists():
        raise SystemExit(f"missing {events_path}")

    events = _load_events(events_path)
    windows, max_concurrency, weighted_wall = _dispatch_windows(events)
    dispatch_total_s = sum(done - start for start, done, _sk in windows)

    fg_score_events = [e for e in events if e.get("component") == "fg_score_engine"]
    batch_events = [e for e in fg_score_events if e.get("event") == "batch_done"]
    prefetch_events = [e for e in fg_score_events if e.get("event") == "prefetch_done"]
    pipeline_events = [e for e in fg_score_events if e.get("event") == "pipeline_done"]
    plan_events = [e for e in fg_score_events if e.get("event") == "plan_done"]
    reducer_events = [e for e in fg_score_events if e.get("event") == "reducer_done"]

    prefetch_ms = _sum_metric(prefetch_events, "prefetch_ms")
    reducer_ms = _sum_metric(reducer_events, "reducer_ms")
    build_wait_ms = _sum_metric(batch_events, "build_wait_ms")
    finalize_ms = _sum_metric(batch_events, "finalize_ms")
    surface_pack_ms = _sum_metric(batch_events, "surface_pack_ms")
    submit_wait_ms = _sum_metric(batch_events, "submit_wait_ms")
    owner_queue_ms = _sum_metric(batch_events, "owner_queue_ms")
    owner_exec_ms = _sum_metric(batch_events, "owner_exec_ms")
    host_wait_ms = _sum_metric(batch_events, "host_wait_ms")
    materialize_ms = _sum_metric(batch_events, "materialize_ms")
    pipeline_wait_ms = _sum_metric(pipeline_events, "pipeline_wait_ms")
    plan_wall_ms = _sum_metric(plan_events, "plan_wall_ms")

    attributed_ms = (
        prefetch_ms
        + build_wait_ms
        + finalize_ms
        + owner_queue_ms
        + owner_exec_ms
        + materialize_ms
        + reducer_ms
    )
    # host_wait_ms is the portion of submit_wait not covered by owner queue+exec.
    # pipeline_wait_ms overlaps host_wait (poll loop); do not double-count in residual.
    dispatch_total_ms = dispatch_total_s * 1000.0
    residual_ms = dispatch_total_ms - attributed_ms - host_wait_ms

    print(f"== {run_dir.name} ==")
    print(f"dispatch windows: n={len(windows)} sum={dispatch_total_s:.1f}s max_concurrency={max_concurrency}")
    print(f"concurrency-weighted wall: {weighted_wall:.1f}s")
    print()
    print("fg_score_engine totals (ms):")
    print(f"  prefetch_submit:     {prefetch_ms:10.1f}")
    print(f"  build_wait:          {build_wait_ms:10.1f}")
    print(f"  finalize:            {finalize_ms:10.1f}")
    print(f"  surface_pack(host):  {surface_pack_ms:10.1f}")
    print(f"  submit_wait(wall):   {submit_wait_ms:10.1f}")
    print(f"    owner_queue:       {owner_queue_ms:10.1f}")
    print(f"    owner_exec:        {owner_exec_ms:10.1f}")
    print(f"    host_wait(gap):    {host_wait_ms:10.1f}  [submit_wait - owner_queue - owner_exec]")
    print(f"  materialize:         {materialize_ms:10.1f}")
    print(f"  reducer(host):       {reducer_ms:10.1f}")
    print(f"  pipeline_wait(poll): {pipeline_wait_ms:10.1f}")
    print(f"  plan_wall:           {plan_wall_ms:10.1f}")
    print()
    print("reconciliation vs dispatch windows:")
    print(f"  dispatch total:      {dispatch_total_ms:10.1f} ms")
    print(f"  attributed (prefetch+build+finalize+owner+mat): {attributed_ms:10.1f} ms")
    print(f"  + host_wait gap:     {host_wait_ms:10.1f} ms")
    print(f"  residual:            {residual_ms:10.1f} ms")
    if dispatch_total_ms > 0:
        covered = attributed_ms + host_wait_ms
        print(f"  covered: {100.0 * covered / dispatch_total_ms:.1f}% of dispatch-window ms")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=str, help="Profile run directory")
    args = parser.parse_args()
    analyze(Path(args.run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
