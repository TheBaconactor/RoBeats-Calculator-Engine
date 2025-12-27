import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


SONG_KEYS = (
    "Aether (Easy) by Geoxor",
    "Aether (Hard) by Geoxor",
    "Aether by Geoxor",
)


def _rm_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _read_best_scores(db_path: Path) -> dict[str, dict[str, int]]:
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, best_score, best_fg_score FROM songs WHERE name IN (?, ?, ?)",
            SONG_KEYS,
        ).fetchall()
        out: dict[str, dict[str, int]] = {}
        for r in rows:
            out[str(r["name"])] = {
                "best_score": int(r["best_score"] or 0),
                "best_fg_score": int(r["best_fg_score"] or 0),
            }
        return out
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Config ini path (passed via METAFINDER_CONFIG_PATH).")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--outdir", default=str(Path("artifacts") / "runs" / "runs_bench"))
    parser.add_argument("--db", default="evolution.db")
    parser.add_argument("--resume", default=str(Path("bin") / "memory_guard_resume.json"))
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    db_path = Path(args.db)
    resume_path = Path(args.resume)

    runs: list[dict] = []

    for i in range(1, int(args.runs) + 1):
        _rm_if_exists(db_path)
        _rm_if_exists(db_path.with_suffix(db_path.suffix + "-wal"))
        _rm_if_exists(db_path.with_suffix(db_path.suffix + "-shm"))
        _rm_if_exists(resume_path)

        log_path = outdir / f"run_{i}.log"
        env = os.environ.copy()
        env["METAFINDER_CONFIG_PATH"] = str(config_path)
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(Path.cwd()),
        )
        dt = time.time() - t0
        log_path.write_text(proc.stdout, encoding="utf-8", errors="replace")

        scores = _read_best_scores(db_path)
        run = {
            "run": i,
            "exit_code": int(proc.returncode),
            "elapsed_sec": float(dt),
            "scores": scores,
        }
        runs.append(run)
        print(f"[{i}/{args.runs}] exit={proc.returncode} time={dt:.1f}s hard_fg={scores.get(SONG_KEYS[1], {}).get('best_fg_score', 0)}")

    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
