#!/usr/bin/env python3
"""
Inventory Meta Coverage benchmark (GPU-only).

Runs the inventory meta coverage solver multiple times with random seeds, assuming NO seeded inventory.
This uses a subprocess worker per run to isolate Taichi/driver state (more stable on macOS).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def _extract_json_object_from_stdout(stdout: str) -> Dict[str, Any] | None:
    raw = (stdout or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    for idx in range(len(raw) - 1, -1, -1):
        if raw[idx] != "{":
            continue
        try:
            parsed = json.loads(raw[idx:])
        except Exception:
            continue
        if isinstance(parsed, dict) and ("ok" in parsed):
            return parsed
    return None


def _mean(xs: List[float]) -> float:
    return float(statistics.mean(xs)) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    return float(statistics.stdev(xs)) if len(xs) > 1 else 0.0


def _run_worker(
    *,
    worker_path: Path,
    repo_root: Path,
    db_path: Path,
    label: str,
    kwargs: dict,
    timeout_sec: float,
) -> dict:
    env = os.environ.copy()
    env["EVOLUTION_DB_PATH"] = str(db_path)
    payload = {"db_path": str(db_path), "label": str(label), "kwargs": kwargs}
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(worker_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
        timeout=float(timeout_sec),
    )
    wall = time.perf_counter() - t0
    msg = _extract_json_object_from_stdout(proc.stdout)
    if msg is None:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"Worker returned invalid output (exit={proc.returncode}).\n{stderr}".strip())
    if not msg.get("ok"):
        raise RuntimeError(f"Worker failed: {msg.get('error')}\n{msg.get('traceback')}".strip())
    # Prefer worker-reported solve time; include wall time for visibility.
    msg["wall_time_sec"] = float(round(wall, 6))
    return msg


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench_inventory_meta_coverage.py")
    parser.add_argument("--db-path", type=str, default="", help="Path to evolution.db (default: EVOLUTION_DB_PATH).")
    parser.add_argument("--runs", type=int, default=5, help="Runs per config (default: 5).")
    parser.add_argument("--song-limit", type=int, default=0, help="Limit songs (0=all; default: 0).")
    parser.add_argument("--inventory-cap", type=int, default=100, help="Inventory cap (default: 100).")
    parser.add_argument("--timeout-sec", type=float, default=900.0, help="Per-run timeout (default: 900s).")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    worker_path = Path(__file__).resolve().parent / "inventory_meta_bench_worker.py"

    db_path_str = args.db_path.strip() or (os.environ.get("EVOLUTION_DB_PATH") or "").strip()
    if not db_path_str:
        raise SystemExit("Missing --db-path and EVOLUTION_DB_PATH is not set.")
    db_path = Path(db_path_str).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    runs = max(1, int(args.runs))
    song_limit = int(args.song_limit) or None
    inventory_cap = max(1, int(args.inventory_cap))

    # Random (non-deterministic) seeds, but shared across configs for fair comparisons.
    seeds = [secrets.randbelow(2_000_000_000) + 1 for _ in range(runs)]

    base_kwargs = {
        "inventory_cap": inventory_cap,
        "seed_inventory_gear": None,
        "element": None,
        "secondary_element": None,
        "solver": "gpu_full",
        "restarts": 1,
        "partitions_per_song": 512,
        "adaptive_rounds": 0,
        "gpu_full_wildcard_freq_bonus": 40,
        "gpu_full_witness_anchor_patterns": 0,
        "gpu_full_witness_seed_streams": 4,
        "gpu_full_witness_palettes": 1,
        "gpu_full_repack_rarity_weighted": True,
        "gpu_full_lns_freq_weighted": True,
        "gpu_full_v_pad_bin": 4096,
        "gpu_full_variant_freq_mode": "song_support",
        "gpu_full_witness_pattern_profile": 0,
        "gpu_full_counter_stripes": 4,
        "gpu_full_k_scan_select": 256,
        "gpu_full_k_scan_repack": 128,
        "gpu_full_repair_enabled": False,
        "lns_time_sec": 10.0,
        "lns_attempts": 1000,
        "gpu_lns_destroy": 12,
        "song_limit": song_limit,
        "profile": False,
    }

    configs = [
        ("gpu_full_top1", {"gpu_full_top_candidates": 1}),
        ("gpu_full_top4", {"gpu_full_top_candidates": 4}),
        ("gpu_full_top4_r3", {"gpu_full_top_candidates": 4, "restarts": 3}),
    ]

    print(f"DB: {db_path}")
    print(f"Runs per config: {runs}")
    if song_limit:
        print(f"Song limit: {song_limit}")
    print()

    results_by_label: Dict[str, List[dict]] = {}
    for label, overrides in configs:
        runs_out: List[dict] = []
        print(f"== {label} ==")
        for i, seed in enumerate(seeds, start=1):
            kwargs = dict(base_kwargs)
            kwargs.update(overrides)
            kwargs["seed"] = int(seed)
            r = _run_worker(
                worker_path=worker_path,
                repo_root=repo_root,
                db_path=db_path,
                label=label,
                kwargs=kwargs,
                timeout_sec=float(args.timeout_sec),
            )
            st = r.get("stats") or {}
            print(
                f"  run {i}/{runs} seed={seed} "
                f"covered={st.get('songs_covered')}/{st.get('songs_total')} "
                f"variants={st.get('gear_variants_used')}/{st.get('gear_variants_cap')} "
                f"gears={st.get('unique_gears_used')} "
                f"time={r.get('time_sec')}s (wall={r.get('wall_time_sec')}s)"
            )
            runs_out.append(r)
        results_by_label[label] = runs_out
        print()

    print("== Summary ==")
    for label, rows in results_by_label.items():
        cov = [float((row.get("stats") or {}).get("songs_covered") or 0) for row in rows]
        used = [float((row.get("stats") or {}).get("gear_variants_used") or 0) for row in rows]
        gears = [float((row.get("stats") or {}).get("unique_gears_used") or 0) for row in rows]
        t = [float(row.get("time_sec") or 0.0) for row in rows]
        print(
            f"{label}: "
            f"covered(mean±sd)={_mean(cov):.1f}±{_stdev(cov):.1f} "
            f"variants(mean±sd)={_mean(used):.1f}±{_stdev(used):.1f} "
            f"gears(mean±sd)={_mean(gears):.1f}±{_stdev(gears):.1f} "
            f"time_sec(mean±sd)={_mean(t):.2f}±{_stdev(t):.2f}"
        )


if __name__ == "__main__":
    main()
