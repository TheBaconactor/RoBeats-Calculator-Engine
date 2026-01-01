import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


GPU_EXECUTOR_PROFILE_RE = re.compile(
    r"^\[GpuExecutor\]\[PROFILE\]\s+wait=(?P<wait>[0-9.]+)s\s+exec=(?P<exec>[0-9.]+)s\s+(?:busy|util)=(?P<util>[0-9.]+)%.*$"
)


def _rm_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _parse_gpu_executor_profile(log_text: str) -> dict | None:
    for line in (log_text or "").splitlines():
        m = GPU_EXECUTOR_PROFILE_RE.match(line.strip())
        if not m:
            continue
        try:
            return {
                "wait_sec": float(m.group("wait")),
                "exec_sec": float(m.group("exec")),
                "util_pct": float(m.group("util")),
            }
        except Exception:
            return None
    return None


def _run_main(*, config_path: Path, out_log: Path, db_path: Path, seed: int) -> dict:
    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["GA_SEED"] = str(int(seed))
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["GPU_EXECUTOR_PROFILE"] = "1"

    out_log.parent.mkdir(parents=True, exist_ok=True)
    with out_log.open("wb") as fh:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "main.py"],
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(Path.cwd()),
        )
        dt = time.perf_counter() - t0

    try:
        log_text = out_log.read_text(encoding="utf-8", errors="replace")
    except Exception:
        log_text = ""

    return {
        "exit_code": int(proc.returncode),
        "elapsed_sec": float(dt),
        "gpu_executor_profile": _parse_gpu_executor_profile(log_text),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path("configs") / "profile" / "config_profile_inflight_queue24_fast.ini"))
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--outdir", default=str(Path("artifacts") / "bench" / "queue24_runs"))
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    for i in range(1, int(args.runs) + 1):
        run_dir = outdir / f"run_{i}"
        run_dir.mkdir(parents=True, exist_ok=True)

        db_out = run_dir / "evolution.db"
        for suffix in ("", "-wal", "-shm"):
            _rm_if_exists(Path(str(db_out) + suffix))

        log_out = run_dir / "run.log"
        seed = int(args.seed_base) + i
        meta = _run_main(config_path=config_path, out_log=log_out, db_path=db_out, seed=seed)
        run = {
            "run": i,
            "seed": seed,
            "config": str(config_path),
            "db": str(db_out),
            "log": str(log_out),
            **meta,
        }
        runs.append(run)

        prof = run.get("gpu_executor_profile") or {}
        util = prof.get("util_pct")
        util_str = f"{util:.1f}%" if isinstance(util, (int, float)) else "n/a"
        print(
            f"[{i}/{int(args.runs)}] exit={run['exit_code']} time={run['elapsed_sec']:.1f}s gpu_executor_util={util_str}"
        )

    summary = {
        "runs": runs,
        "config": str(config_path),
        "runs_count": int(args.runs),
        "seed_base": int(args.seed_base),
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
