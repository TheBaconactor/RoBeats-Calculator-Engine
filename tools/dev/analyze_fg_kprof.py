"""Pair the Taichi kernel-profiler dump (per-kernel GPU device time) with fg_fused
owner-phase wall-times from the same run. Read-only.

  kprof.json    : _dump_kernel_profiler_records output (TAICHI_KERNEL_PROFILER_PATH)
  fg_fused.jsonl: fg_owner_phase events (METAFINDER_PROFILE_EVENTS_PATH)

Usage: python tools/dev/analyze_fg_kprof.py <kprof.json> <fg_fused.jsonl>
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict


def main(kprof_path: str, fg_path: str) -> int:
    kp = json.loads(open(kprof_path, encoding="utf-8").read())
    kernels = kp.get("kernels") or []
    dev_total = float(kp.get("device_total_ms") or 0.0)
    print(f"== kernel profiler ({kprof_path}) ==")
    print(f"  device_total={dev_total / 1000.0:.1f}s  n_kernels={kp.get('n_kernels')}  n_launches={kp.get('n_launches')}")
    print(f"  {'kernel':<48}{'GPU_s':>9}{'count':>8}{'avg_ms':>10}")
    for k in kernels[:14]:
        print(f"  {str(k['kernel'])[:48]:<48}{k['total_ms'] / 1000.0:>9.2f}{int(k['count']):>8}{k['avg_ms']:>10.3f}")

    def gpu_ms(*subs: str) -> tuple[float, int]:
        tot = 0.0
        cnt = 0
        for k in kernels:
            nm = str(k["kernel"]).lower()
            if any(s in nm for s in subs):
                tot += float(k["total_ms"])
                cnt += int(k["count"])
        return tot, cnt

    inner_gpu, inner_cnt = gpu_ms("response_inner_batch", "response_inner_group")

    phase = defaultdict(float)
    loop = defaultdict(float)
    for line in open(fg_path, encoding="utf-8"):
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
        ph = str(m.get("phase") or "")
        if ph == "score_loop":
            loop["enqueue_ms"] += float(m.get("enqueue_ms") or 0.0)
            loop["logical_rows"] += int(m.get("logical_surface_rows") or 0)
        else:
            phase[ph] += float(m.get("total_ms") or 0.0)

    score_wall = loop["enqueue_ms"]
    rows = loop["logical_rows"]
    print("\n== inner score kernel: GPU time vs score-loop wall (same run) ==")
    print(f"  inner kernel GPU = {inner_gpu / 1000.0:8.2f}s  ({inner_cnt} launches)")
    print(f"  score_loop wall  = {score_wall / 1000.0:8.2f}s  (enqueue)")
    if score_wall > 0:
        print(f"  -> inner kernel is {100.0 * inner_gpu / score_wall:.0f}% of score-loop wall (GPU-exec bound if high)")
    if rows > 0:
        print(f"  -> GPU {1000.0 * inner_gpu / (rows / 1e6):.1f} ns/row over {rows / 1e6:.1f}M surface rows")
    owner_wall_ms = sum(phase[name] for name in ("build", "pack", "score_total", "resolve"))
    print(
        f"\n  device_total GPU = {dev_total / 1000.0:.1f}s"
        f"   native FG owner wall = {owner_wall_ms / 1000.0:.1f}s"
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python tools/dev/analyze_fg_kprof.py <kprof.json> <fg_fused.jsonl>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
