#!/usr/bin/env python3
"""
Inventory Meta Coverage - Real-World Benchmark (GPU-only).

Purpose:
- Measure real-world coverage changes across code/algorithm updates (no synthetic DBs).
- Deterministic by default (fixed seed), and stores a history file so you can compare against the last run.
- Runs via a subprocess worker to isolate Taichi/driver state (more stable on macOS).

Modes:
- fast:    runs Chill + All
- precise: runs Chill, Vibe, Flow, Rush, Beat + All
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    msg["wall_time_sec"] = float(round(wall, 6))
    return msg


def _git_sha(repo_root: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out if out else None


def _load_history(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"schema_version": 1, "runs": []}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {"schema_version": 1, "runs": []}
    if not isinstance(parsed, dict):
        return {"schema_version": 1, "runs": []}
    if not isinstance(parsed.get("runs"), list):
        parsed["runs"] = []
    if not isinstance(parsed.get("schema_version"), int):
        parsed["schema_version"] = 1
    return parsed


def _atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class BenchRow:
    label: str
    songs_total: int
    songs_covered: int
    gear_variants_used: int
    gear_variants_cap: int
    unique_gears_used: int
    time_sec: float
    wall_time_sec: float


def _row_from_worker(msg: dict) -> BenchRow:
    st = msg.get("stats") or {}
    return BenchRow(
        label=str(msg.get("label") or ""),
        songs_total=int(st.get("songs_total") or 0),
        songs_covered=int(st.get("songs_covered") or 0),
        gear_variants_used=int(st.get("gear_variants_used") or 0),
        gear_variants_cap=int(st.get("gear_variants_cap") or 0),
        unique_gears_used=int(st.get("unique_gears_used") or 0),
        time_sec=float(msg.get("time_sec") or 0.0),
        wall_time_sec=float(msg.get("wall_time_sec") or 0.0),
    )


def _print_row(prefix: str, row: BenchRow) -> None:
    print(
        f"{prefix}{row.label:>5s}  covered={row.songs_covered:4d}/{row.songs_total:4d}  "
        f"variants={row.gear_variants_used:3d}/{row.gear_variants_cap:3d}  "
        f"gears={row.unique_gears_used:2d}  time={row.time_sec:6.2f}s (wall={row.wall_time_sec:6.2f}s)"
    )


def _print_delta(now: BenchRow, prev: BenchRow) -> None:
    dc = int(now.songs_covered - prev.songs_covered)
    dv = int(now.gear_variants_used - prev.gear_variants_used)
    dg = int(now.unique_gears_used - prev.unique_gears_used)
    dt = float(now.time_sec - prev.time_sec)
    print(f"       delta  covered={dc:+4d}  variants={dv:+4d}  gears={dg:+3d}  time={dt:+6.2f}s")


def main() -> None:
    ap = argparse.ArgumentParser(prog="bench_inventory_meta_real_world.py")
    ap.add_argument("--db-path", type=str, default="", help="Path to evolution.db (default: EVOLUTION_DB_PATH).")
    ap.add_argument("--mode", type=str, default="fast", choices=["fast", "precise"], help="Benchmark mode.")
    ap.add_argument("--seed", type=int, default=1, help="Deterministic seed (default: 1).")
    ap.add_argument("--inventory-cap", type=int, default=100, help="Inventory cap (default: 100).")
    ap.add_argument("--timeout-sec", type=float, default=900.0, help="Per-run timeout (default: 900s).")
    ap.add_argument(
        "--history-path",
        type=str,
        default="",
        help="Where to store/compare history (default: artifacts/inventory_meta_real_bench/history.json).",
    )
    ap.add_argument("--no-write", action="store_true", help="Do not update history file.")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    worker_path = Path(__file__).resolve().parent / "inventory_meta_bench_worker.py"

    db_path_str = args.db_path.strip() or (os.environ.get("EVOLUTION_DB_PATH") or "").strip()
    if not db_path_str:
        raise SystemExit("Missing --db-path and EVOLUTION_DB_PATH is not set.")
    db_path = Path(db_path_str).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    history_path_str = (args.history_path or "").strip()
    history_path = (
        Path(history_path_str).expanduser().resolve()
        if history_path_str
        else (repo_root / "artifacts" / "inventory_meta_real_bench" / "history.json")
    )

    mode = str(args.mode)
    seed = int(args.seed)
    inventory_cap = max(1, int(args.inventory_cap))
    timeout_sec = float(args.timeout_sec)

    if mode == "fast":
        suite = [("Chill", "Chill"), ("All", None)]
        cfg = {
            "partitions_per_song": 256,
            "lns_time_sec": 3.0,
            "lns_attempts": 300,
            "gpu_lns_destroy": 10,
            "gpu_full_k_scan_select": 128,
            "gpu_full_k_scan_repack": 64,
            "gpu_full_repair_attempts": 128,
            "element_restarts": 2,
        }
    else:
        suite = [("Chill", "Chill"), ("Vibe", "Vibe"), ("Flow", "Flow"), ("Rush", "Rush"), ("Beat", "Beat"), ("All", None)]
        cfg = {
            "partitions_per_song": 512,
            "lns_time_sec": 10.0,
            "lns_attempts": 1000,
            "gpu_lns_destroy": 12,
            "gpu_full_k_scan_select": 256,
            "gpu_full_k_scan_repack": 128,
            "gpu_full_repair_attempts": 256,
            "element_restarts": 3,
        }

    base_kwargs = {
        "solver": "gpu_full",
        "inventory_cap": int(inventory_cap),
        "seed": int(seed),
        "seed_inventory_gear": None,
        "secondary_element": None,
        "adaptive_rounds": 0,
        "gpu_repack_passes": 3,
        "gpu_full_wildcard_freq_bonus": 40,
        "gpu_full_wildcard_palette_size": 256,
        "gpu_full_wildcard_palette_min_count": 2,
        "gpu_full_wildcard_palette_scan": 8,
        "gpu_full_wildcard_palette_tail_slots": 3,
        "gpu_full_synergy_weight": 0,
        "gpu_full_new_gear_penalty": 0,
        "gpu_full_witness_anchor_patterns": 24,
        "gpu_full_witness_seed_streams": 4,
        "gpu_full_witness_palettes": 1,
        "gpu_full_witness_pattern_profile": 0,
        "gpu_full_top_candidates": 1,
        "gpu_full_human_mode": False,
        "gpu_full_candidate_score_delta": 0,
        "gpu_full_candidate_limit_per_song": 0,
        "gpu_full_lns_freq_weighted": True,
        "gpu_full_counter_stripes": 4,
        "gpu_full_repair_enabled": True,
        "profile": False,
    }
    base_kwargs.update(
        {
            "partitions_per_song": int(cfg["partitions_per_song"]),
            "lns_time_sec": float(cfg["lns_time_sec"]),
            "lns_attempts": int(cfg["lns_attempts"]),
            "gpu_lns_destroy": int(cfg["gpu_lns_destroy"]),
            "gpu_full_k_scan_select": int(cfg["gpu_full_k_scan_select"]),
            "gpu_full_k_scan_repack": int(cfg["gpu_full_k_scan_repack"]),
            "gpu_full_repair_attempts": int(cfg["gpu_full_repair_attempts"]),
        }
    )

    config_sig = {
        "mode": mode,
        "seed": int(seed),
        "inventory_cap": int(inventory_cap),
        "solver": "gpu_full",
        "params": {
            "partitions_per_song": int(cfg["partitions_per_song"]),
            "lns_time_sec": float(cfg["lns_time_sec"]),
            "lns_attempts": int(cfg["lns_attempts"]),
            "gpu_lns_destroy": int(cfg["gpu_lns_destroy"]),
            "gpu_full_k_scan_select": int(cfg["gpu_full_k_scan_select"]),
            "gpu_full_k_scan_repack": int(cfg["gpu_full_k_scan_repack"]),
            "gpu_full_repair_attempts": int(cfg["gpu_full_repair_attempts"]),
            "gpu_full_witness_anchor_patterns": int(base_kwargs["gpu_full_witness_anchor_patterns"]),
            "gpu_full_witness_seed_streams": int(base_kwargs["gpu_full_witness_seed_streams"]),
            "gpu_full_witness_pattern_profile": int(base_kwargs["gpu_full_witness_pattern_profile"]),
            "gpu_full_wildcard_palette_size": int(base_kwargs["gpu_full_wildcard_palette_size"]),
        },
    }

    history = _load_history(history_path)
    prev_run = None
    for run in reversed(history.get("runs") or []):
        if not isinstance(run, dict):
            continue
        if run.get("config_sig") == config_sig and run.get("db_path") == str(db_path):
            prev_run = run
            break

    print(f"DB: {db_path}")
    print(f"Mode: {mode}  seed={seed}  cap={inventory_cap}")
    if prev_run is not None:
        print(f"Prev: {prev_run.get('git_sha') or '?'}  ts={prev_run.get('ts_utc') or '?'}")
    else:
        print("Prev: (none for this config/db)")
    print()

    rows: List[BenchRow] = []
    prev_rows: Dict[str, BenchRow] = {}
    if prev_run is not None:
        by_label = prev_run.get("results_by_label") or {}
        if isinstance(by_label, dict):
            for k, v in by_label.items():
                if not isinstance(v, dict):
                    continue
                try:
                    prev_rows[str(k)] = BenchRow(
                        label=str(k),
                        songs_total=int(v.get("songs_total") or 0),
                        songs_covered=int(v.get("songs_covered") or 0),
                        gear_variants_used=int(v.get("gear_variants_used") or 0),
                        gear_variants_cap=int(v.get("gear_variants_cap") or 0),
                        unique_gears_used=int(v.get("unique_gears_used") or 0),
                        time_sec=float(v.get("time_sec") or 0.0),
                        wall_time_sec=float(v.get("wall_time_sec") or 0.0),
                    )
                except Exception:
                    continue

    t_suite0 = time.perf_counter()
    for label, element in suite:
        kwargs = dict(base_kwargs)
        kwargs["element"] = element
        # Avoid relying on implicit restart heuristics so historical comparisons stay stable.
        kwargs["restarts"] = int(cfg["element_restarts"]) if element else 1

        msg = _run_worker(
            worker_path=worker_path,
            repo_root=repo_root,
            db_path=db_path,
            label=str(label),
            kwargs=kwargs,
            timeout_sec=timeout_sec,
        )
        row = _row_from_worker(msg)
        rows.append(row)
        _print_row(prefix="now:  ", row=row)
        prev = prev_rows.get(row.label)
        if prev is not None:
            _print_delta(row, prev)
        print()

    suite_wall = time.perf_counter() - t_suite0

    out_by_label = {
        row.label: {
            "songs_total": row.songs_total,
            "songs_covered": row.songs_covered,
            "gear_variants_used": row.gear_variants_used,
            "gear_variants_cap": row.gear_variants_cap,
            "unique_gears_used": row.unique_gears_used,
            "time_sec": float(round(row.time_sec, 6)),
            "wall_time_sec": float(round(row.wall_time_sec, 6)),
        }
        for row in rows
    }

    run = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": _git_sha(repo_root),
        "db_path": str(db_path),
        "mode": mode,
        "suite_labels": [str(x[0]) for x in suite],
        "suite_wall_time_sec": float(round(suite_wall, 6)),
        "config_sig": config_sig,
        "results_by_label": out_by_label,
    }

    if not args.no_write:
        history.setdefault("runs", []).append(run)
        _atomic_write_json(history_path, history)
        print(f"Saved: {history_path}")
    else:
        print("Saved: (disabled via --no-write)")


if __name__ == "__main__":
    main()

