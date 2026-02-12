"""Run persistence mutation checks across major commits.

Workflow per commit:
1) run baseline optimizer workload into an isolated DB
2) audit baseline DB for persistence issues
3) copy DB, inject one synthetic persistence bug, audit again
4) require mutated DB to show at least one audit issue (coverage proof)

This script is designed for regression investigation across historical versions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.persistence_audit import audit_persistence_db, inject_synthetic_persistence_bug


DEFAULT_MAJOR_COMMITS = [
    "088981a",
    "797c256",
    "66a1646",
    "a07676e",
    "5018285",
    "61a4e8a",
    "ff85ba2",
    "8e7fe3f",
    "0ee6353",
    "5d9cacd",
]


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _start_ref(repo: Path) -> str:
    ref = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip()
    if ref == "HEAD":
        return _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
    return ref


def _run_baseline(
    *,
    repo: Path,
    commit: str,
    config_path: Path,
    output_dir: Path,
    song_limit: int,
    ga_seed: int,
    timeout_sec: int,
) -> dict[str, Any]:
    db_path = output_dir / f"{commit}.db"
    log_path = output_dir / f"{commit}.log"
    if db_path.exists():
        db_path.unlink()
    if log_path.exists():
        log_path.unlink()

    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["GA_SEED"] = str(int(ga_seed))
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["SONG_QUEUE_LIMIT"] = str(int(song_limit))
    env["SONG_REPEATS"] = "1"

    t0 = time.perf_counter()
    with open(log_path, "w", encoding="utf-8", errors="replace") as log_fp:
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(repo),
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            text=True,
        )
        timed_out = False
        try:
            proc.wait(timeout=int(timeout_sec))
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
    wall_s = time.perf_counter() - t0

    return {
        "commit": commit,
        "db_path": str(db_path),
        "log_path": str(log_path),
        "exit_code": int(proc.returncode),
        "timed_out": bool(timed_out),
        "wall_s": float(wall_s),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run persistence mutation matrix across major commits.")
    parser.add_argument(
        "--commits",
        nargs="+",
        default=list(DEFAULT_MAJOR_COMMITS),
        help="Commit shas to test (default: built-in major-commit list).",
    )
    parser.add_argument(
        "--song-limit",
        type=int,
        default=25,
        help="Song queue limit per run (default: 25).",
    )
    parser.add_argument(
        "--ga-seed",
        type=int,
        default=424242,
        help="Deterministic GA seed (default: 424242).",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=360,
        help="Timeout per commit run in seconds (default: 360).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("artifacts/bench/cross_git_persistence/cross_git_config.ini"),
        help="Config path used for all runs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/bench/persistence_bug_mutation_matrix"),
        help="Output directory for logs, DBs, and summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path.cwd()
    output_dir = (repo / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = (repo / args.config).resolve()

    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        return 2

    start_ref = _start_ref(repo)
    start_sha = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
    results: list[dict[str, Any]] = []

    try:
        for commit in args.commits:
            _run(["git", "checkout", "--detach", commit], cwd=repo)

            baseline = _run_baseline(
                repo=repo,
                commit=str(commit),
                config_path=config_path,
                output_dir=output_dir,
                song_limit=int(args.song_limit),
                ga_seed=int(args.ga_seed),
                timeout_sec=int(args.timeout_sec),
            )

            baseline_audit = audit_persistence_db(
                baseline["db_path"],
                expected_min_songs=int(args.song_limit),
                expected_pending_fg_jobs=0,
            )

            mutated_db = output_dir / f"{commit}.mutated.db"
            if mutated_db.exists():
                mutated_db.unlink()

            if Path(baseline["db_path"]).exists() and Path(baseline["db_path"]).stat().st_size > 0:
                shutil.copy2(baseline["db_path"], mutated_db)
                mutation = inject_synthetic_persistence_bug(mutated_db)
                mutated_audit = audit_persistence_db(
                    mutated_db,
                    expected_min_songs=int(args.song_limit),
                    expected_pending_fg_jobs=0,
                )
            else:
                mutation = {"applied": False, "error": "baseline_db_missing_or_empty"}
                mutated_audit = {
                    "db_path": str(mutated_db),
                    "issues": [{"code": "baseline_db_missing_or_empty", "detail": "cannot mutate missing baseline DB"}],
                }

            baseline_clean = len(baseline_audit.get("issues", [])) == 0
            mutation_detected = bool(mutated_audit.get("issues"))

            row = {
                "commit": str(commit),
                "baseline": baseline,
                "baseline_audit": baseline_audit,
                "baseline_clean": bool(baseline_clean),
                "mutation": mutation,
                "mutated_db_path": str(mutated_db),
                "mutated_audit": mutated_audit,
                "mutation_detected": bool(mutation_detected),
            }
            results.append(row)

            print(
                "[MATRIX]"
                f" commit={commit}"
                f" exit={baseline['exit_code']}"
                f" timeout={int(bool(baseline['timed_out']))}"
                f" baseline_clean={int(bool(baseline_clean))}"
                f" mutation_applied={int(bool(mutation.get('applied')))}"
                f" mutation_detected={int(bool(mutation_detected))}"
            )
    finally:
        _run(["git", "checkout", start_ref], cwd=repo, check=False)

    summary = {
        "generated_at": _utc_now(),
        "start_ref": start_ref,
        "start_sha": start_sha,
        "song_limit": int(args.song_limit),
        "ga_seed": int(args.ga_seed),
        "config_path": str(config_path),
        "commits": [str(c) for c in args.commits],
        "results": results,
    }

    summary_path = output_dir / "persistence_bug_mutation_matrix_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[MATRIX] wrote summary: {summary_path}")

    current_clean = None
    for row in results:
        if str(row.get("commit", "")).startswith(start_sha):
            current_clean = bool(row.get("baseline_clean"))
            break

    mutation_detected_all = all(bool(r.get("mutation_detected")) for r in results)

    # Return non-zero when coverage is broken or current commit shows persistence issues.
    if not mutation_detected_all:
        print("[MATRIX][FAIL] At least one synthetic mutation was not detected by the audit.")
        return 3
    if current_clean is False:
        print("[MATRIX][FAIL] Current commit baseline shows persistence audit issues.")
        return 4

    print("[MATRIX][PASS] Mutation coverage detected across all commits.")
    if current_clean is True:
        print("[MATRIX][PASS] Current commit baseline is clean for audited persistence invariants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
