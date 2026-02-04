"""
Inventory Meta Coverage - Real-World Benchmark + Tuning Worker (GPU-only).

This module is intentionally placed under `inventory_optimizer/` (not `tools/`) because it is part of
the inventory-meta system: its history files and outputs are meant to be consumed when tuning settings
and validating algorithm changes.

Modes:
- Benchmark runner (default): deterministic by default, stores history, and compares against the most recent
  compatible run (same benchmark config + same DB song set).
- Worker mode (`--worker`): subprocess-safe runner used by the benchmark and auto-tuner to isolate Taichi state.

Important:
- Benchmarking for regression comparisons should use a deterministic seed.
- Tuning settings should use non-deterministic seeds to measure robustness across random witness pools and LNS walks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# -----------------------------------------------------------------------------
# Shared utils
# -----------------------------------------------------------------------------


def _extract_json_object_from_stdout(stdout: str) -> Optional[Dict[str, Any]]:
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
        return {"schema_version": 2, "runs": []}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {"schema_version": 2, "runs": []}
    if not isinstance(parsed, dict):
        return {"schema_version": 2, "runs": []}
    if not isinstance(parsed.get("runs"), list):
        parsed["runs"] = []
    if not isinstance(parsed.get("schema_version"), int):
        parsed["schema_version"] = 2
    return parsed


def _atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def compute_db_song_signature(db_path: Path) -> dict:
    """
    A stable signature of the song set in the DB.

    This is used to prevent misleading comparisons when new songs are added (or renamed)
    between benchmark runs.
    """
    db_path = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(str(db_path))
    try:
        names = [str(r[0]) for r in conn.execute("SELECT name FROM songs ORDER BY name").fetchall()]
    finally:
        conn.close()

    h = hashlib.blake2b(digest_size=16)
    for name in names:
        h.update(name.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return {
        "songs_total": int(len(names)),
        "songs_name_hash": h.hexdigest(),
    }


# -----------------------------------------------------------------------------
# Worker mode (subprocess-safe Taichi runner)
# -----------------------------------------------------------------------------


def _json_safe(obj: Any) -> Any:
    # Best-effort conversion for solver stats (which sometimes include numpy scalars).
    try:
        import numpy as np  # type: ignore

        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass

    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _run_worker_from_stdin() -> int:
    """
    Worker protocol:
      stdin JSON: { "db_path": "...", "kwargs": { ... }, "label": "..." }
      stdout JSON: { "ok": true/false, ... }
    """
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object payload on stdin.")

        db_path = str(payload.get("db_path") or "").strip()
        if db_path:
            os.environ["EVOLUTION_DB_PATH"] = db_path

        repo_root = Path(__file__).resolve().parents[1]
        repo_str = str(repo_root)
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)

        from inventory_optimizer import run_inventory_meta_coverage

        kwargs = payload.get("kwargs") or {}
        if not isinstance(kwargs, dict):
            raise ValueError("payload.kwargs must be an object")

        t0 = time.perf_counter()
        result = run_inventory_meta_coverage(**kwargs)
        elapsed = time.perf_counter() - t0

        stats = result.get("stats", {}) if isinstance(result, dict) else {}
        inventory = result.get("inventory", {}) if isinstance(result, dict) else {}
        variants = inventory.get("gear_variants", []) if isinstance(inventory, dict) else []
        unique_gears = (
            len({str(v.get("gear_name") or "") for v in variants if isinstance(v, dict) and v.get("gear_name")})
            if isinstance(variants, list)
            else 0
        )

        solver_stats = result.get("solver_stats", {}) if isinstance(result, dict) else {}
        solver_stats = _json_safe(solver_stats)

        out = {
            "ok": True,
            "label": str(payload.get("label") or ""),
            "time_sec": float(round(elapsed, 6)),
            "seed": int(kwargs.get("seed") or 0),
            "stats": {
                "songs_total": int(stats.get("songs_total") or 0) if isinstance(stats, dict) else 0,
                "songs_total_unfiltered": int(stats.get("songs_total_unfiltered") or 0)
                if isinstance(stats, dict)
                else 0,
                "songs_filtered_out": int(stats.get("songs_filtered_out") or 0) if isinstance(stats, dict) else 0,
                "songs_covered": int(stats.get("songs_covered") or 0) if isinstance(stats, dict) else 0,
                "gear_variants_used": int(stats.get("gear_variants_used") or 0) if isinstance(stats, dict) else 0,
                "gear_variants_cap": int(stats.get("gear_variants_cap") or 0) if isinstance(stats, dict) else 0,
                "unique_gears_used": int(unique_gears),
                "element_filter": (stats.get("element_filter") if isinstance(stats, dict) else None),
                "secondary_element_filter": (
                    stats.get("secondary_element_filter") if isinstance(stats, dict) else None
                ),
            },
            # Keep all solver stats for future analysis (witness pool meta, GPU solver attempts, etc).
            "solver_stats": solver_stats,
        }
        sys.stdout.write(json.dumps(out))
        return 0
    except BaseException as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        )
        return 0


# -----------------------------------------------------------------------------
# Benchmark runner
# -----------------------------------------------------------------------------


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
    seed: int
    solver_stats: dict


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
        seed=int(msg.get("seed") or 0),
        solver_stats=(msg.get("solver_stats") or {}) if isinstance(msg.get("solver_stats") or {}, dict) else {},
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


def build_benchmark_suite(mode: str) -> tuple[list[tuple[str, Optional[str]]], dict]:
    """
    Returns (suite, cfg) where suite is [(label, element_filter)].
    """
    mode = str(mode).strip().lower()
    if mode == "fast":
        suite = [("Chill", "Chill"), ("All", None)]
        cfg = {
            # Keep fast cheap: the goal is iteration speed.
            "partitions_per_song": 256,
            "lns_time_sec": 3.0,
            "lns_attempts": 300,
            "gpu_lns_destroy": 10,
            # Leave these on auto (0) so results match the main CLI defaults.
            "gpu_full_k_scan_select": 0,
            "gpu_full_k_scan_repack": 0,
            "gpu_full_repair_attempts": 128,
            "element_restarts": 2,
            # All-elements is materially harder; budget a few deterministic restarts while
            # keeping per-restart budgets aligned with the element-scoped runs.
            "all_restarts": 3,
            "all_lns_time_sec": 9.0,
            "all_lns_attempts": 900,
        }
        return suite, cfg
    if mode == "precise":
        suite = [
            ("Chill", "Chill"),
            ("Vibe", "Vibe"),
            ("Flow", "Flow"),
            ("Rush", "Rush"),
            ("Beat", "Beat"),
            ("All", None),
        ]
        cfg = {
            "partitions_per_song": 512,
            "lns_time_sec": 10.0,
            "lns_attempts": 1000,
            "gpu_lns_destroy": 12,
            # Leave these on auto (0) so results match the main CLI defaults.
            "gpu_full_k_scan_select": 0,
            "gpu_full_k_scan_repack": 0,
            "gpu_full_repair_attempts": 256,
            "element_restarts": 3,
            # All-elements needs more exploration; keep per-restart budgets at 10s/1000 attempts.
            "all_restarts": 3,
            "all_lns_time_sec": 30.0,
            "all_lns_attempts": 3000,
        }
        return suite, cfg
    raise ValueError("mode must be 'fast' or 'precise'")


def build_base_kwargs(*, seed: int, inventory_cap: int, cfg: dict) -> dict:
    """
    Baseline settings for real-world benchmarks.

    Constraints:
    - exact-peak-only (human mode disabled, candidate delta disabled)
    - single peak per song
    """
    base = {
        "inventory_cap": int(inventory_cap),
        "seed": int(seed),
        "seed_inventory_gear": None,
        "secondary_element": None,
        "adaptive_rounds": 0,
        "gpu_repack_passes": 3,
        "gpu_full_wildcard_freq_bonus": 40,
        # Match the main CLI defaults: keep wildcard palette injection off by default.
        # (It tends to bias the All-elements case into islands unless explicitly tuned.)
        "gpu_full_wildcard_palette_size": 0,
        "gpu_full_wildcard_palette_min_count": 2,
        "gpu_full_wildcard_palette_scan": 0,
        "gpu_full_wildcard_palette_tail_slots": 3,
        "gpu_full_synergy_weight": 0,
        "gpu_full_new_gear_penalty": 0,
        # Match the main CLI defaults.
        "gpu_full_witness_anchor_patterns": 128,
        "gpu_full_witness_seed_streams": 1,
        "gpu_full_witness_palettes": 1,
        "gpu_full_witness_pattern_profile": 1,
        "gpu_full_top_candidates": 1,
        # Exact-peak-only constraints (no human mode).
        "gpu_full_human_mode": False,
        "gpu_full_candidate_score_delta": 0,
        "gpu_full_candidate_limit_per_song": 0,
        "gpu_full_lns_freq_weighted": False,
        "gpu_full_counter_stripes": 1,
        "gpu_full_variant_freq_mode": "song_support",
        "gpu_full_repair_enabled": True,
        "gpu_full_repair_max_cands_per_slot": 16,
        "profile": False,
    }
    base.update(
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
    return base


def make_benchmark_config_sig(*, mode: str, seed: int, inventory_cap: int, cfg: dict, base_kwargs: dict) -> dict:
    # Keep this stable and intentionally small; this is just for lookup compatibility.
    return {
        "mode": str(mode),
        "seed": int(seed),
        "inventory_cap": int(inventory_cap),
        "params": {
            "partitions_per_song": int(cfg["partitions_per_song"]),
            "lns_time_sec": float(cfg["lns_time_sec"]),
            "lns_attempts": int(cfg["lns_attempts"]),
            "all_restarts": int(cfg.get("all_restarts") or 1),
            "all_lns_time_sec": float(cfg.get("all_lns_time_sec") or cfg["lns_time_sec"]),
            "all_lns_attempts": int(cfg.get("all_lns_attempts") or cfg["lns_attempts"]),
            "gpu_lns_destroy": int(cfg["gpu_lns_destroy"]),
            "gpu_full_k_scan_select": int(cfg["gpu_full_k_scan_select"]),
            "gpu_full_k_scan_repack": int(cfg["gpu_full_k_scan_repack"]),
            "gpu_full_repair_attempts": int(cfg["gpu_full_repair_attempts"]),
            "gpu_full_repair_max_cands_per_slot": int(base_kwargs.get("gpu_full_repair_max_cands_per_slot") or 0),
            # Allow older history/tests to pass a partial `base_kwargs` dict by applying
            # the same defaults as `build_base_kwargs`.
            "gpu_full_witness_anchor_patterns": int(base_kwargs.get("gpu_full_witness_anchor_patterns") or 128),
            "gpu_full_witness_seed_streams": int(base_kwargs.get("gpu_full_witness_seed_streams") or 1),
            "gpu_full_witness_pattern_profile": int(base_kwargs.get("gpu_full_witness_pattern_profile") or 1),
            "gpu_full_counter_stripes": int(base_kwargs.get("gpu_full_counter_stripes") or 1),
            "gpu_full_lns_freq_weighted": bool(base_kwargs.get("gpu_full_lns_freq_weighted") or False),
            "gpu_full_variant_freq_mode": str(base_kwargs.get("gpu_full_variant_freq_mode") or "song_support"),
            "gpu_full_wildcard_palette_size": int(base_kwargs.get("gpu_full_wildcard_palette_size") or 0),
        },
    }


def find_previous_run(
    history: dict, *, db_path: Path, config_sig: dict, db_sig: dict
) -> tuple[Optional[dict], Optional[str]]:
    runs = history.get("runs") or []
    if not isinstance(runs, list):
        return None, None
    for run in reversed(runs):
        if not isinstance(run, dict):
            continue
        if run.get("db_path") != str(db_path):
            continue
        if run.get("config_sig") != config_sig:
            continue
        prev_db_sig = run.get("db_song_signature")
        if prev_db_sig != db_sig:
            return None, "db_song_signature_changed"
        return run, None
    return None, None


def run_inventory_meta_coverage_subprocess(
    *,
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
        [sys.executable, "-m", "inventory_optimizer.real_bench", "--worker"],
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


def benchmark_main(
    *,
    db_path: Path,
    mode: str,
    seed: int,
    inventory_cap: int,
    timeout_sec: float,
    history_path: Path,
    no_write: bool,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    db_path = Path(db_path).expanduser().resolve()
    history_path = Path(history_path).expanduser().resolve()

    suite, cfg = build_benchmark_suite(mode)
    base_kwargs = build_base_kwargs(seed=seed, inventory_cap=inventory_cap, cfg=cfg)

    db_sig = compute_db_song_signature(db_path)
    config_sig = make_benchmark_config_sig(
        mode=mode, seed=seed, inventory_cap=inventory_cap, cfg=cfg, base_kwargs=base_kwargs
    )

    history = _load_history(history_path)
    prev_run, prev_reason = find_previous_run(history, db_path=db_path, config_sig=config_sig, db_sig=db_sig)

    print(f"DB: {db_path}")
    print(f"Mode: {mode}  seed={seed}  cap={inventory_cap}")
    print(f"DB songs: {db_sig.get('songs_total')}  hash={db_sig.get('songs_name_hash')}")
    if prev_run is not None:
        print(f"Prev: {prev_run.get('git_sha') or '?'}  ts={prev_run.get('ts_utc') or '?'}")
    elif prev_reason == "db_song_signature_changed":
        print("Prev: (ignored; song set changed since last run)")
    else:
        print("Prev: (none for this config/db)")
    print()

    prev_rows: Dict[str, BenchRow] = {}
    if prev_run is not None:
        by_label = prev_run.get("results_by_label") or {}
        if isinstance(by_label, dict):
            for lbl, v in by_label.items():
                if not isinstance(v, dict):
                    continue
                try:
                    prev_rows[str(lbl)] = BenchRow(
                        label=str(lbl),
                        songs_total=int(v.get("songs_total") or 0),
                        songs_covered=int(v.get("songs_covered") or 0),
                        gear_variants_used=int(v.get("gear_variants_used") or 0),
                        gear_variants_cap=int(v.get("gear_variants_cap") or 0),
                        unique_gears_used=int(v.get("unique_gears_used") or 0),
                        time_sec=float(v.get("time_sec") or 0.0),
                        wall_time_sec=float(v.get("wall_time_sec") or 0.0),
                        seed=int(v.get("seed") or 0),
                        solver_stats=(v.get("solver_stats") or {})
                        if isinstance(v.get("solver_stats") or {}, dict)
                        else {},
                    )
                except Exception:
                    continue

    rows: List[BenchRow] = []
    t_suite0 = time.perf_counter()
    for label, element in suite:
        kwargs = dict(base_kwargs)
        kwargs["element"] = element
        # Avoid relying on implicit restart heuristics so historical comparisons stay stable.
        if element:
            kwargs["restarts"] = int(cfg["element_restarts"])
        else:
            kwargs["restarts"] = int(cfg.get("all_restarts") or 1)
            kwargs["lns_time_sec"] = float(cfg.get("all_lns_time_sec") or cfg["lns_time_sec"])
            kwargs["lns_attempts"] = int(cfg.get("all_lns_attempts") or cfg["lns_attempts"])

        msg = run_inventory_meta_coverage_subprocess(
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
            "seed": int(row.seed),
            "time_sec": float(round(row.time_sec, 6)),
            "wall_time_sec": float(round(row.wall_time_sec, 6)),
            "solver_stats": row.solver_stats,
        }
        for row in rows
    }

    run = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": _git_sha(repo_root),
        "db_path": str(db_path),
        "db_song_signature": dict(db_sig),
        "mode": str(mode),
        "suite_labels": [str(x[0]) for x in suite],
        "suite_wall_time_sec": float(round(suite_wall, 6)),
        "config_sig": config_sig,
        "base_kwargs": base_kwargs,
        "results_by_label": out_by_label,
    }

    if no_write:
        print("Saved: (disabled via --no-write)")
        return

    history.setdefault("runs", []).append(run)
    _atomic_write_json(history_path, history)
    print(f"Saved: {history_path}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="inventory_optimizer.real_bench")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)

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

    args = ap.parse_args(list(argv) if argv is not None else None)

    if bool(args.worker):
        return _run_worker_from_stdin()

    db_path_str = str(args.db_path or "").strip() or (os.environ.get("EVOLUTION_DB_PATH") or "").strip()
    if not db_path_str:
        raise SystemExit("Missing --db-path and EVOLUTION_DB_PATH is not set.")
    db_path = Path(db_path_str).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    history_path_str = str(args.history_path or "").strip()
    history_path = (
        Path(history_path_str).expanduser().resolve()
        if history_path_str
        else (Path(__file__).resolve().parents[1] / "artifacts" / "inventory_meta_real_bench" / "history.json")
    )

    benchmark_main(
        db_path=db_path,
        mode=str(args.mode),
        seed=int(args.seed),
        inventory_cap=int(args.inventory_cap),
        timeout_sec=float(args.timeout_sec),
        history_path=history_path,
        no_write=bool(args.no_write),
    )
    return 0


__all__ = [
    "BenchRow",
    "benchmark_main",
    "build_benchmark_suite",
    "build_base_kwargs",
    "compute_db_song_signature",
    "find_previous_run",
    "main",
    "make_benchmark_config_sig",
    "run_inventory_meta_coverage_subprocess",
]


if __name__ == "__main__":
    raise SystemExit(main())
