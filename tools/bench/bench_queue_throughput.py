import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path


THROUGHPUT_RE = re.compile(
    r"^\[Throughput\]\s+Completed\s+(?P<done>\d+)/(?P<total>\d+)\s+task\(s\).*->\s+"
    r"(?P<songs_per_h>[0-9.]+)\s+songs/hour,\s+(?P<tasks_per_h>[0-9.]+)\s+tasks/hour",
    re.IGNORECASE,
)


def _run_one(*, inflight: int, song_limit: int, config_path: Path, db_path: Path) -> dict:
    env = os.environ.copy()
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["METAFINDER_THROUGHPUT"] = "1"
    env["SONG_QUEUE_LIMIT"] = str(int(song_limit))
    env["IN_FLIGHT_SONGS"] = str(int(inflight))
    env["EVOLUTION_DB_PATH"] = str(db_path)

    # Safety: ensure profiling toggles don't sneak in during throughput runs.
    env["METAFINDER_DEBUG_PROFILE"] = "0"
    for k in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "GPU_EXECUTOR_PROFILE",
        "GPU_PROFILER",
        "GPU_BATCH_LOG",
        "GPU_SERVICE_PROFILE",
        "GPU_SERVICE_PROFILE_PRINT",
        "INFLIGHT_STAGE_PROFILE",
        "INFLIGHT_STAGE_PROFILE_EMIT_SEC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        env.pop(k, None)

    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(Path.cwd()),
    )
    wall_s = time.perf_counter() - t0

    throughput = None
    for line in (proc.stdout or "").splitlines():
        m = THROUGHPUT_RE.match(line.strip())
        if m:
            throughput = {
                "done": int(m.group("done")),
                "total": int(m.group("total")),
                "songs_per_h": float(m.group("songs_per_h")),
                "tasks_per_h": float(m.group("tasks_per_h")),
            }

    return {
        "inflight": int(inflight),
        "song_limit": int(song_limit),
        "exit_code": int(proc.returncode),
        "wall_s": float(wall_s),
        "db_path": str(db_path),
        "throughput": throughput,
        "log_tail": (proc.stdout or "")[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--song-limit", type=int, default=120)
    parser.add_argument("--inflight", default="12,18,22", help="Comma-separated InFlightSongs values to test.")
    parser.add_argument("--config", default="config.ini")
    parser.add_argument("--out", default=str(Path("artifacts") / "bench" / "queue120_inflight_throughput.json"))
    args = parser.parse_args()

    song_limit = max(1, int(args.song_limit))
    inflight_vals = []
    for tok in str(args.inflight).split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            inflight_vals.append(int(tok))
        except Exception:
            pass
    inflight_vals = [v for v in inflight_vals if v >= 0]
    if not inflight_vals:
        raise SystemExit("--inflight must include at least one integer >= 0")

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for inflight in inflight_vals:
        db_path = Path("artifacts") / "bench" / f"queue120_inflight{inflight}.db"
        for suffix in ("", "-wal", "-shm"):
            try:
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        res = _run_one(inflight=inflight, song_limit=song_limit, config_path=config_path, db_path=db_path)
        results.append(res)
        t = res.get("throughput") or {}
        print(f"inflight={inflight} exit={res['exit_code']} wall_s={res['wall_s']:.1f} tasks/h={t.get('tasks_per_h')}")

    payload = {"song_limit": song_limit, "inflight": inflight_vals, "results": results}
    out_path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

