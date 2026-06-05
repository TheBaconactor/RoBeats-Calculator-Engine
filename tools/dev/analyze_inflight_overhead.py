"""
Non-computation overhead analyzer for a 16-song in-flight optimization run.

Reads the `profile_events.jsonl` (+ optional summary.json) produced by
tools/profile/profile_system_run.py --deep and reconstructs:

  - One-time STARTUP timeline (run_start -> queue_built -> startup_cpu_work ->
    taichi init -> tasks_prepared -> first GPU request).
  - GPU-busy time = sum of gpu_service::latency_sample latency_sec
    (single GPU owner => requests serialize, so this ~ GPU busy wall).
    Split by request key (GA run vs FG response-frontier batch).
  - PER-SONG timeline from per-song_key events: FG prep, GA decode, FG worker
    (with owner_exec_ms = real FG GPU exec, owner_queue_ms = GPU queue wait).
  - INTER-SONG scheduling gaps: wall gap between consecutive songs' first GPU
    request (is the pipeline overlapping or serial?).
  - GPU utilization (busy% vs idle%) and the overhead fraction.

This is read-only analysis; it does not modify production code.

Usage:
  python -u tools/dev/analyze_inflight_overhead.py --events <profile_events.jsonl> [--summary <summary.json>]
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                events.append(obj)
    events.sort(key=lambda e: float(e.get("ts_wall", 0.0) or 0.0))
    return events


def _stats(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"n": 0, "sum": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0, "min": 0.0}
    s = sorted(xs)
    n = len(s)
    return {
        "n": n,
        "sum": float(sum(s)),
        "mean": float(sum(s) / n),
        "p50": float(s[n // 2]),
        "p95": float(s[min(n - 1, int(round(0.95 * (n - 1))))]),
        "max": float(s[-1]),
        "min": float(s[0]),
    }


def _fmt(x: float) -> str:
    return f"{x:.3f}"


def analyze(events: list[dict[str, Any]], summary: dict[str, Any] | None) -> None:
    if not events:
        print("NO EVENTS")
        return

    t0 = float(events[0].get("ts_wall", 0.0) or 0.0)
    t_end = float(events[-1].get("ts_wall", 0.0) or 0.0)

    def rel(ts: float) -> float:
        return float(ts) - t0

    # ---- Component / event inventory ----
    comp_counts: dict[str, int] = defaultdict(int)
    evt_counts: dict[str, int] = defaultdict(int)
    for e in events:
        comp_counts[str(e.get("component", ""))] += 1
        evt_counts[f"{e.get('component','')}::{e.get('event','')}"] += 1

    # ---- One-time startup markers (component=app / cpu_work_manager) ----
    first_by_key: dict[str, float] = {}
    for e in events:
        key = f"{e.get('component','')}::{e.get('event','')}"
        if key not in first_by_key:
            first_by_key[key] = float(e.get("ts_wall", 0.0) or 0.0)

    # ---- GPU requests: gpu_service::latency_sample (latency_sec, key) ----
    gpu_lat_by_key: dict[str, list[float]] = defaultdict(list)
    gpu_lat_all: list[float] = []
    gpu_lat_ts: list[tuple[float, str, float]] = []  # (ts_wall_done, key, latency)
    for e in events:
        if e.get("component") == "gpu_service" and e.get("event") == "latency_sample":
            m = e.get("metrics") or {}
            lat = float(m.get("latency_sec", 0.0) or 0.0)
            key = str(m.get("key", "") or "")
            gpu_lat_by_key[key].append(lat)
            gpu_lat_all.append(lat)
            ts_done = float(e.get("ts_wall", 0.0) or 0.0)
            gpu_lat_ts.append((ts_done, key, lat))

    # ---- FG worker dispatch_done: owner_exec_ms / owner_queue_ms ----
    fg_owner_exec_ms: list[float] = []
    fg_owner_queue_ms: list[float] = []
    for e in events:
        if e.get("component") == "inflight_fg_worker" and e.get("event") == "dispatch_done":
            m = e.get("metrics") or {}
            fg_owner_exec_ms.append(float(m.get("owner_exec_ms", 0.0) or 0.0))
            fg_owner_queue_ms.append(float(m.get("owner_queue_ms", 0.0) or 0.0))

    # ---- FG prep timings (inflight_fg_prep::prep_done) ----
    fg_prep_total_ms: list[float] = []
    fg_prep_plan_ms: list[float] = []
    fg_prep_queue_wait_ms: list[float] = []
    for e in events:
        if e.get("component") == "inflight_fg_prep" and e.get("event") == "prep_done":
            m = e.get("metrics") or {}
            fg_prep_total_ms.append(float(m.get("total_ms", 0.0) or 0.0))
            fg_prep_plan_ms.append(float(m.get("plan_ms", 0.0) or 0.0))
            fg_prep_queue_wait_ms.append(float(m.get("queue_wait_ms", 0.0) or 0.0))

    # ---- GA decode timings (inflight_decode::future_done cpu_s) ----
    decode_cpu_s: list[float] = []
    for e in events:
        if e.get("component") == "inflight_decode" and e.get("event") == "future_done":
            m = e.get("metrics") or {}
            decode_cpu_s.append(float(m.get("cpu_s", 0.0) or 0.0))

    # ---- Per-song timeline reconstruction (group by song_key) ----
    # For each song, capture first/last timestamp of each stage.
    per_song: dict[str, dict[str, Any]] = defaultdict(lambda: {"events": []})
    for e in events:
        sk = str(e.get("song_key", "") or "")
        if not sk:
            continue
        per_song[sk]["events"].append(e)

    song_rows: list[dict[str, Any]] = []
    for sk, info in per_song.items():
        evs = sorted(info["events"], key=lambda e: float(e.get("ts_wall", 0.0) or 0.0))
        ev_first = {}
        ev_last = {}
        for e in evs:
            k = f"{e.get('component','')}::{e.get('event','')}"
            ts = float(e.get("ts_wall", 0.0) or 0.0)
            if k not in ev_first:
                ev_first[k] = ts
            ev_last[k] = ts
        # song "start" = earliest event; "end" = latest event (typically fg dispatch_done)
        song_start = float(evs[0].get("ts_wall", 0.0) or 0.0)
        song_end = float(evs[-1].get("ts_wall", 0.0) or 0.0)
        # FG dispatch_done owner exec/queue for this song
        fg_exec = 0.0
        fg_queue = 0.0
        for e in evs:
            if e.get("component") == "inflight_fg_worker" and e.get("event") == "dispatch_done":
                m = e.get("metrics") or {}
                fg_exec += float(m.get("owner_exec_ms", 0.0) or 0.0)
                fg_queue += float(m.get("owner_queue_ms", 0.0) or 0.0)
        song_rows.append(
            {
                "song_key": sk,
                "start": song_start,
                "end": song_end,
                "span_s": max(0.0, song_end - song_start),
                "fg_dispatch_done": ev_last.get("inflight_fg_worker::dispatch_done"),
                "fg_start": ev_first.get("inflight_fg_worker::start"),
                "decode_submit": ev_first.get("inflight_decode::submit"),
                "fg_owner_exec_ms": fg_exec,
                "fg_owner_queue_ms": fg_queue,
            }
        )

    # Order songs by their FG dispatch_done (completion order) for inter-song analysis.
    completed = [r for r in song_rows if r.get("fg_dispatch_done") is not None]
    completed.sort(key=lambda r: float(r["fg_dispatch_done"]))

    # ---- INTER-SONG scheduling gap ----
    # Two complementary measures:
    #  (A) completion-to-completion wall delta between consecutive finished songs
    #      (the effective per-song throughput interval in steady state).
    #  (B) gap between a song's GA decode-submit (first GPU-derived activity for that
    #      song after GA) — used to see if work for song N+1 overlaps song N.
    comp_to_comp: list[float] = []
    for i in range(1, len(completed)):
        prev = float(completed[i - 1]["fg_dispatch_done"])
        cur = float(completed[i]["fg_dispatch_done"])
        comp_to_comp.append(max(0.0, cur - prev))

    # ---- GPU idle reconstruction from latency intervals (merge overlapping) ----
    # Reconstruct [submit, done] per request from done_ts and latency, then merge.
    gpu_intervals = []
    for ts_done, key, lat in gpu_lat_ts:
        gpu_intervals.append((ts_done - lat, ts_done))
    gpu_intervals.sort()
    merged: list[list[float]] = []
    for a, b in gpu_intervals:
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    gpu_busy_union = sum(b - a for a, b in merged)
    gpu_busy_sum = sum(gpu_lat_all)  # over-counts if requests overlap on GPU
    gpu_span = (merged[-1][1] - merged[0][0]) if merged else 0.0

    # Idle gaps between merged GPU-busy windows.
    gpu_gaps: list[tuple[float, float, float]] = []  # (gap_s, gap_start_rel, gap_end_rel)
    for i in range(1, len(merged)):
        gap = merged[i][0] - merged[i - 1][1]
        if gap > 0:
            gpu_gaps.append((gap, rel(merged[i - 1][1]), rel(merged[i][0])))
    gpu_gaps_sorted = sorted(gpu_gaps, key=lambda g: g[0], reverse=True)

    # ---- run_start / run_end / queue_built / startup markers ----
    run_start = first_by_key.get("app::run_start")
    queue_built = first_by_key.get("app::queue_built")
    cpu_work_start = first_by_key.get("cpu_work_manager::startup_cpu_work_start")
    cpu_work_done = None
    for e in events:
        if e.get("component") == "cpu_work_manager" and "done" in str(e.get("event", "")).lower():
            cpu_work_done = float(e.get("ts_wall", 0.0) or 0.0)
            break
    taichi_init_start = first_by_key.get("app::taichi_init_start")
    taichi_init_done = first_by_key.get("app::taichi_init_done")
    tasks_prepared = first_by_key.get("app::tasks_prepared")
    first_gpu_req = (merged[0][0] if merged else None)
    run_end = None
    for e in reversed(events):
        if e.get("component") == "app" and e.get("event") == "run_end":
            run_end = float(e.get("ts_wall", 0.0) or 0.0)
            break

    # ============ REPORT ============
    print("=" * 78)
    print("IN-FLIGHT 16-SONG RUN: NON-COMPUTATION OVERHEAD ANALYSIS")
    print("=" * 78)
    total_wall = (run_end - run_start) if (run_end and run_start) else (t_end - t0)
    print(f"\nEvent window wall:          {_fmt(t_end - t0)} s ({len(events)} events)")
    if run_start and run_end:
        print(f"run_start -> run_end wall:   {_fmt(run_end - run_start)} s")
    print(f"Completed songs (FG done):  {len(completed)}")

    print("\n----- ONE-TIME STARTUP TIMELINE (relative to run_start) -----")
    base = run_start or t0

    def relb(ts):
        return None if ts is None else float(ts) - base

    def line(label, ts):
        r = relb(ts)
        print(f"  {label:<34} {'' if r is None else _fmt(r)+' s'}")

    line("run_start", run_start)
    line("queue_built", queue_built)
    line("startup_cpu_work_start", cpu_work_start)
    line("startup_cpu_work_done", cpu_work_done)
    line("taichi_init_start", taichi_init_start)
    line("taichi_init_done", taichi_init_done)
    line("tasks_prepared", tasks_prepared)
    line("first_gpu_request (submit)", first_gpu_req)
    if taichi_init_start and taichi_init_done:
        print(f"  -> Taichi/Vulkan init dur:        {_fmt(taichi_init_done - taichi_init_start)} s")
    if cpu_work_start and cpu_work_done:
        print(f"  -> startup CPU (cache) dur:       {_fmt(cpu_work_done - cpu_work_start)} s")
    if first_gpu_req and run_start:
        print(f"  -> startup BEFORE 1st GPU crunch: {_fmt(first_gpu_req - run_start)} s")

    print("\n----- GPU BUSY (from gpu_service::latency_sample) -----")
    print(f"  GPU requests sampled:        {len(gpu_lat_all)}")
    print(f"  GPU busy (sum of latency):   {_fmt(gpu_busy_sum)} s  [over-counts if overlap]")
    print(f"  GPU busy (merged union):     {_fmt(gpu_busy_union)} s  [true wall GPU-busy]")
    print(f"  GPU active span:             {_fmt(gpu_span)} s")
    if gpu_span > 0:
        print(f"  GPU busy% of active span:    {100.0*gpu_busy_union/gpu_span:.1f}%")
        print(f"  GPU idle  within span:       {_fmt(gpu_span - gpu_busy_union)} s ({100.0*(gpu_span-gpu_busy_union)/gpu_span:.1f}%)")
    for key, lats in sorted(gpu_lat_by_key.items(), key=lambda kv: -sum(kv[1])):
        st = _stats(lats)
        print(f"    [{key}] n={st['n']:<4} sum={_fmt(st['sum'])}s mean={st['mean']*1000:.1f}ms p95={st['p95']*1000:.1f}ms max={st['max']*1000:.1f}ms")

    print("\n----- GPU IDLE GAPS (between merged GPU-busy windows) -----")
    gst = _stats([g[0] for g in gpu_gaps])
    print(f"  idle gaps: n={gst['n']} sum={_fmt(gst['sum'])}s mean={gst['mean']*1000:.1f}ms p95={gst['p95']*1000:.1f}ms max={gst['max']*1000:.1f}ms")
    print("  top idle gaps (gap_s @ rel_start -> rel_end):")
    for gap, rs, re_ in gpu_gaps_sorted[:10]:
        print(f"    {gap*1000:8.1f} ms   @ {rs:8.2f}s -> {re_:8.2f}s")

    print("\n----- INTER-SONG SCHEDULING (completion-to-completion) -----")
    cst = _stats(comp_to_comp)
    print(f"  consecutive song completions: n={cst['n']}")
    print(f"  inter-completion interval:    mean={_fmt(cst['mean'])}s p50={_fmt(cst['p50'])}s p95={_fmt(cst['p95'])}s max={_fmt(cst['max'])}s min={_fmt(cst['min'])}s")
    print("  per-song completion order (rel_done, span, fg_exec_ms, fg_queue_ms, gap_to_prev):")
    prev_done = None
    for r in completed:
        done = relb(r["fg_dispatch_done"])
        gap = "" if prev_done is None else f"{(r['fg_dispatch_done'] - prev_done):.3f}s"
        sk = r["song_key"]
        if len(sk) > 40:
            sk = sk[:37] + "..."
        print(f"    {sk:<40} done={done:8.2f}s span={r['span_s']:7.2f}s fg_exec={r['fg_owner_exec_ms']:8.1f}ms fg_q={r['fg_owner_queue_ms']:7.1f}ms gap={gap}")
        prev_done = float(r["fg_dispatch_done"])

    print("\n----- PER-STAGE CPU PREP (overlap-able, off GPU) -----")
    pst = _stats([x / 1000.0 for x in fg_prep_total_ms])
    print(f"  FG prep total:   n={pst['n']} sum={_fmt(pst['sum'])}s mean={pst['mean']*1000:.1f}ms p95={pst['p95']*1000:.1f}ms max={pst['max']*1000:.1f}ms")
    plst = _stats([x / 1000.0 for x in fg_prep_plan_ms])
    print(f"    of which plan:  mean={plst['mean']*1000:.1f}ms p95={plst['p95']*1000:.1f}ms max={plst['max']*1000:.1f}ms")
    qwst = _stats([x / 1000.0 for x in fg_prep_queue_wait_ms])
    print(f"    fg_prep queue-wait: mean={qwst['mean']*1000:.1f}ms p95={qwst['p95']*1000:.1f}ms max={qwst['max']*1000:.1f}ms")
    dst = _stats(decode_cpu_s)
    print(f"  GA decode cpu:   n={dst['n']} sum={_fmt(dst['sum'])}s mean={dst['mean']*1000:.1f}ms p95={dst['p95']*1000:.1f}ms max={dst['max']*1000:.1f}ms")
    fest = _stats([x / 1000.0 for x in fg_owner_exec_ms])
    fqst = _stats([x / 1000.0 for x in fg_owner_queue_ms])
    print(f"  FG owner GPU exec: n={fest['n']} sum={_fmt(fest['sum'])}s mean={fest['mean']*1000:.1f}ms  (real FG GPU)")
    print(f"  FG owner GPU queue-wait: sum={_fmt(fqst['sum'])}s mean={fqst['mean']*1000:.1f}ms p95={fqst['p95']*1000:.1f}ms  (waiting for GPU owner)")

    # ---- Orchestrator bubble / stall / heartbeat idle ----
    hb_idle: list[float] = []
    stalls = 0
    bubble_total_idle = None
    for e in events:
        if e.get("component") == "inflight_orchestrator":
            m = e.get("metrics") or {}
            if e.get("event") == "heartbeat":
                hb_idle.append(float(m.get("idle_sec", 0.0) or 0.0))
            elif e.get("event") == "stall":
                stalls += 1
            elif e.get("event") == "bubble_summary":
                bubble_total_idle = float(m.get("bubble_total_idle_sec", 0.0) or 0.0)
    print("\n----- ORCHESTRATOR SELF-REPORTED BUBBLES -----")
    if bubble_total_idle is not None:
        print(f"  bubble_total_idle_sec (orchestrator GPU-idle accounting): {_fmt(bubble_total_idle)} s")
    if hb_idle:
        hst = _stats(hb_idle)
        print(f"  heartbeat idle_sec: n={hst['n']} mean={_fmt(hst['mean'])}s p95={_fmt(hst['p95'])}s max={_fmt(hst['max'])}s")
    print(f"  stall events: {stalls}")

    # ---- Overall budget ----
    print("\n----- OVERALL WALL BUDGET -----")
    if total_wall > 0:
        startup_s = (first_gpu_req - run_start) if (first_gpu_req and run_start) else 0.0
        steady = total_wall - startup_s
        print(f"  Total wall (run_start->run_end):     {_fmt(total_wall)} s")
        print(f"  Startup (->1st GPU req):             {_fmt(startup_s)} s ({100.0*startup_s/total_wall:.1f}%)")
        print(f"  GPU busy (union):                    {_fmt(gpu_busy_union)} s ({100.0*gpu_busy_union/total_wall:.1f}%)")
        gpu_idle_total = max(0.0, total_wall - startup_s - gpu_busy_union)
        print(f"  GPU idle (steady, non-startup):      {_fmt(gpu_idle_total)} s ({100.0*gpu_idle_total/total_wall:.1f}%)")
        # tail = after last gpu req to run_end
        if merged and run_end:
            tail = max(0.0, run_end - merged[-1][1])
            print(f"  Tail (last GPU req -> run_end):      {_fmt(tail)} s ({100.0*tail/total_wall:.1f}%)")

    if summary:
        gpu_sum = summary.get("gpu_summary") or {}
        tgt = (gpu_sum.get("target_engine_util_pct_max") or {})
        glob = (gpu_sum.get("global_engine_util_pct_max") or {})
        print("\n----- WINDOWS GPU COUNTERS (typeperf, cross-check) -----")
        if tgt:
            print(f"  target-pid GPU engine util%: mean={tgt.get('mean',0):.1f} p50={tgt.get('p50',0):.1f} p95={tgt.get('p95',0):.1f} max={tgt.get('max',0):.1f} (n={tgt.get('count',0)})")
        if glob:
            print(f"  global GPU engine util%:     mean={glob.get('mean',0):.1f} p50={glob.get('p50',0):.1f} p95={glob.get('p95',0):.1f} max={glob.get('max',0):.1f} (n={glob.get('count',0)})")
        by_type = (gpu_sum.get("target_engine_util_pct_by_type_max") or {})
        for typ, st in sorted(by_type.items()):
            print(f"    engtype={typ}: mean={st.get('mean',0):.1f} p95={st.get('p95',0):.1f} max={st.get('max',0):.1f}")
        cpu_sum = summary.get("cpu_summary") or {}
        ct = (cpu_sum.get("cpu_tree_pct") or {})
        if ct:
            print(f"  CPU tree%: mean={ct.get('mean',0):.1f} p95={ct.get('p95',0):.1f} max={ct.get('max',0):.1f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True, type=str)
    ap.add_argument("--summary", default="", type=str)
    ns = ap.parse_args()
    events = _load_events(Path(ns.events))
    summary = None
    if ns.summary:
        sp = Path(ns.summary)
        if sp.exists():
            try:
                summary = json.loads(sp.read_text(encoding="utf-8"))
            except Exception:
                summary = None
    analyze(events, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
