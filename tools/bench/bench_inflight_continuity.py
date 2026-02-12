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


def _run_main(*, config_path: Path, out_log: Path, env_overrides: dict[str, str]) -> dict:
    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env.update({k: str(v) for k, v in (env_overrides or {}).items()})

    t0 = time.time()
    out_log.parent.mkdir(parents=True, exist_ok=True)
    # Write logs directly to disk to avoid large in-memory captures and to prevent
    # Windows pipe inheritance from hanging subprocess output collection.
    with out_log.open("wb") as f:
        proc = subprocess.run(
            [sys.executable, "main.py"],
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(Path.cwd()),
        )
    dt = time.time() - t0

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Config ini path (passed via METAFINDER_CONFIG_PATH).")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--outdir", default=str(Path("artifacts") / "runs" / "inflight_continuity"))
    parser.add_argument("--inflight", type=int, default=4, help="IN_FLIGHT_SONGS override for the inflight run.")
    args = parser.parse_args()

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

        baseline_db = run_dir / "baseline.db"
        inflight_db = run_dir / "inflight.db"
        for db in (baseline_db, inflight_db):
            _rm_if_exists(db)
            _rm_if_exists(db.with_suffix(db.suffix + "-wal"))
            _rm_if_exists(db.with_suffix(db.suffix + "-shm"))

        common_env = {
            "GPU_EXECUTOR_PROFILE": "1",
            "METAFINDER_IGNORE_RESUME_QUEUE": "1",
        }

        baseline = _run_main(
            config_path=config_path,
            out_log=run_dir / "baseline.log",
            env_overrides={
                **common_env,
                "EVOLUTION_DB_PATH": str(baseline_db),
            },
        )

        inflight = _run_main(
            config_path=config_path,
            out_log=run_dir / "inflight.log",
            env_overrides={
                **common_env,
                "EVOLUTION_DB_PATH": str(inflight_db),
                "IN_FLIGHT_SONGS": str(int(args.inflight)),
            },
        )

        run = {
            "run": i,
            "baseline": baseline,
            "inflight": inflight,
        }
        runs.append(run)

        inflight_prof = inflight.get("gpu_executor_profile") or {}
        util = inflight_prof.get("util_pct")
        wait_sec = inflight_prof.get("wait_sec")
        exec_sec = inflight_prof.get("exec_sec")
        util_str = f"{util:.1f}%" if isinstance(util, (int, float)) else "n/a"
        wait_str = f"{wait_sec:.2f}s" if isinstance(wait_sec, (int, float)) else "n/a"
        exec_str = f"{exec_sec:.2f}s" if isinstance(exec_sec, (int, float)) else "n/a"

        print(
            f"[{i}/{args.runs}] baseline={baseline['elapsed_sec']:.1f}s inflight={inflight['elapsed_sec']:.1f}s "
            f"inflight_gpu_exec_util={util_str} (wait={wait_str} exec={exec_str})"
        )

    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    print(f"Saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
