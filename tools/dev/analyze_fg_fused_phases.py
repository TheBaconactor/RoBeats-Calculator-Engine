"""Summarize fused GA->FG owner-thread phase timings from a profile_events JSONL.

Reads the gated instrumentation events added for
``docs/research/GPU_FUSED_FG_OWNER_GAP_REVIEW_REQUEST_20260613.md``
(component="fg_fused", event="fg_owner_phase"). Read-only diagnostic.

Per song the GPU owner thread emits, in order:
  download       (the ga_download_fg_selected_payload to_numpy; first event of the song)
  ga_run_total   (GA generations enqueue + the download to_numpy sync)
  build / pack / score_total / resolve  (slices of the fused FG block)
  score_loop     (the chunked score loop internals: plan/enqueue/sync/reduce)
  fg_block_total (the whole fused FG continuation)

NOTE on attribution: Taichi launches kernels async, so GPU exec time surfaces at
whatever host call forces the sync (e.g. to_numpy). "download" therefore largely
reflects the GA generations' GPU compute awaited at the sync, not transfer. Treat
the host wall-time split as real; host-vs-GPU within a phase needs explicit syncs.

Usage:
    python tools/dev/analyze_fg_fused_phases.py <profile_events.jsonl> [skip_first_songs]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict


def main(path: str, skip_songs: int = 0) -> int:
    phase_ms: dict[str, float] = defaultdict(float)
    phase_n: dict[str, int] = defaultdict(int)
    loop = {"plan_ms": 0.0, "enqueue_ms": 0.0, "sync_ms": 0.0, "reduce_ms": 0.0, "n_chunks": 0, "songs": 0}
    n_events = 0
    song_idx = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("component") != "fg_fused":
                continue
            m = ev.get("metrics") or {}
            phase = str(m.get("phase") or "")
            if phase == "download":
                song_idx += 1
            if song_idx <= skip_songs:
                continue
            n_events += 1
            if phase == "score_loop":
                for k in ("plan_ms", "enqueue_ms", "sync_ms", "reduce_ms"):
                    loop[k] += float(m.get(k) or 0.0)
                loop["n_chunks"] += int(m.get("n_chunks") or 0)
                loop["songs"] += 1
            else:
                phase_ms[phase] += float(m.get("total_ms") or 0.0)
                phase_n[phase] += 1

    if n_events == 0:
        print(f"No fg_fused events found in {path} (after skipping {skip_songs} songs)")
        return 1

    ga = phase_ms.get("ga_run_total", 0.0)
    fg = phase_ms.get("fg_block_total", 0.0)
    dl = phase_ms.get("download", 0.0)
    owner_total = ga + fg

    def pct(ms: float) -> float:
        return 100.0 * ms / owner_total if owner_total else 0.0

    def row(name: str, ms: float, n: int) -> None:
        mean = ms / n if n else 0.0
        print(f"  {name:<22}{ms / 1000.0:>9.2f}s{n:>7}{mean:>10.1f}{pct(ms):>9.1f}%")

    songs = phase_n.get("ga_run_total", 0)
    print(f"== fused owner timeline ({path}) ==")
    print(f"  songs analyzed: {songs}   (skipped first {skip_songs} as warmup)   fg_fused events: {n_events}")
    print(f"  {'phase':<22}{'total':>10}{'n':>7}{'mean_ms':>10}{'%owner':>10}")
    row("ga_run_total", ga, songs)
    row("  download(=ga sync)", dl, phase_n.get("download", 0))
    row("  (ga_gens = ga-dl)", ga - dl, songs)
    row("fg_block_total", fg, phase_n.get("fg_block_total", 0))
    for p in ("build", "pack", "score_total", "resolve"):
        row("  " + p, phase_ms.get(p, 0.0), phase_n.get(p, 0))
    fg_remainder = fg - sum(phase_ms.get(p, 0.0) for p in ("build", "pack", "score_total", "resolve"))
    row("  prepare+overhead*", fg_remainder, phase_n.get("fg_block_total", 0))
    print("    (*remainder of fg_block_total = dedup + prepare_..._scoring_batch + handoff overhead)")

    print()
    print(
        f"  OWNER SPLIT:  GA {pct(ga):.1f}%   |   FG {pct(fg):.1f}%      "
        f"(owner_total={owner_total / 1000.0:.1f}s, {owner_total / songs if songs else 0:.0f} ms/song)"
    )

    if loop["songs"]:
        tot = loop["plan_ms"] + loop["enqueue_ms"] + loop["sync_ms"] + loop["reduce_ms"]
        host = loop["plan_ms"] + loop["enqueue_ms"] + loop["reduce_ms"]
        gpu = loop["sync_ms"]

        def lpct(ms: float) -> float:
            return 100.0 * ms / tot if tot else 0.0

        print()
        print(f"== score_loop internals ({loop['songs']} chunked songs, {loop['n_chunks']} chunks) ==")
        for k in ("plan_ms", "enqueue_ms", "sync_ms", "reduce_ms"):
            print(f"  {k:<12}{loop[k] / 1000.0:>9.2f}s{lpct(loop[k]):>8.1f}%")
        print(f"  --> explicit-sync GPU {lpct(gpu):.1f}%   |   launch+host {lpct(host):.1f}%")
        print("      (sync~0 => kernel launches are effectively synchronous; 'enqueue' lumps GPU exec + host launch)")
    else:
        print("\n  (no chunked score_loop events — score path used the single-dispatch kernel only)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python tools/dev/analyze_fg_fused_phases.py <profile_events.jsonl> [skip_first_songs]")
        raise SystemExit(2)
    _skip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    raise SystemExit(main(sys.argv[1], _skip))
