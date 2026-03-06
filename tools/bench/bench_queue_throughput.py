import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


FINAL_THROUGHPUT_RE = re.compile(
    r"^\[Throughput\]\s+Completed\s+(?P<done>\d+)/(?P<total>\d+)\s+task\(s\).*->\s+"
    r"(?P<songs_per_h>[0-9.]+)\s+songs/hour,\s+(?P<tasks_per_h>[0-9.]+)\s+tasks/hour",
    re.IGNORECASE,
)
SNAPSHOT_THROUGHPUT_RE = re.compile(
    r"^\[Throughput\]\s+(?P<tasks_per_h>[0-9.]+)\s+tasks/hour(?:\s+\(avg\s+(?P<avg_s>[0-9.]+)s/task(?:,\s+ETA\s+(?P<eta_min>[0-9.]+)m)?\))?",
    re.IGNORECASE,
)
COMPLETED_RE = re.compile(r"^\[(?P<done>\d+)/(?P<total>\d+)\]\s+Completed:\s+(?P<label>.+)$")
QUEUED_RE = re.compile(r"^\[Run\]\s+Queued\s+(?P<queued_songs>\d+)\s+song\(s\)\s+for processing\.$")
RUN_SUFFIX_RE = re.compile(r"\s*\(Run\s+\d+\s*/\s*\d+\)\s*$", re.IGNORECASE)


def _normalize_task_label(label: str) -> str:
    return RUN_SUFFIX_RE.sub("", str(label or "").strip())


def _parse_throughput(stdout: str, wall_s: float) -> dict | None:
    final = None
    queued_songs = None
    completed_tasks = 0
    completed_total = 0
    completed_song_labels: set[str] = set()
    last_snapshot_tasks_per_h = None

    for raw_line in (stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = FINAL_THROUGHPUT_RE.match(line)
        if match:
            final = {
                "done": int(match.group("done")),
                "total": int(match.group("total")),
                "songs_per_h": float(match.group("songs_per_h")),
                "tasks_per_h": float(match.group("tasks_per_h")),
                "source": "final",
            }
            continue

        match = SNAPSHOT_THROUGHPUT_RE.match(line)
        if match:
            last_snapshot_tasks_per_h = float(match.group("tasks_per_h"))
            continue

        match = QUEUED_RE.match(line)
        if match:
            queued_songs = int(match.group("queued_songs"))
            continue

        match = COMPLETED_RE.match(line)
        if match:
            done = int(match.group("done"))
            total = int(match.group("total"))
            completed_tasks = max(completed_tasks, done)
            completed_total = max(completed_total, total)
            label = _normalize_task_label(match.group("label"))
            if label:
                completed_song_labels.add(label)

    if final is not None:
        if queued_songs is not None:
            final["queued_songs"] = int(queued_songs)
        completed_songs = None
        try:
            tasks_per_h = float(final.get("tasks_per_h") or 0.0)
            songs_per_h = float(final.get("songs_per_h") or 0.0)
            if tasks_per_h > 0.0 and songs_per_h >= 0.0:
                completed_songs = int(round(float(final["done"]) * songs_per_h / tasks_per_h))
        except Exception:
            completed_songs = None
        if completed_songs is not None:
            if queued_songs is not None:
                completed_songs = min(int(queued_songs), max(0, int(completed_songs)))
            final["completed_songs"] = int(completed_songs)
        return final

    if completed_tasks <= 0 or float(wall_s) <= 0.0:
        return None

    completed_songs = len(completed_song_labels) if completed_song_labels else None
    payload = {
        "done": int(completed_tasks),
        "total": int(completed_total or completed_tasks),
        "tasks_per_h": float(completed_tasks) * 3600.0 / float(wall_s),
        "source": "estimated",
    }
    if completed_songs is not None:
        payload["completed_songs"] = int(completed_songs)
        payload["songs_per_h"] = float(completed_songs) * 3600.0 / float(wall_s)
    if queued_songs is not None:
        payload["queued_songs"] = int(queued_songs)
    if last_snapshot_tasks_per_h is not None:
        payload["last_snapshot_tasks_per_h"] = float(last_snapshot_tasks_per_h)
    return payload


def _apply_env_mode(env: dict[str, str], key: str, mode: str) -> None:
    mode_norm = str(mode or "auto").strip().lower()
    if mode_norm == "on":
        env[key] = "1"
    elif mode_norm == "off":
        env[key] = "0"
    else:
        env.pop(key, None)


def _run_one(
    *,
    repo_path: Path,
    inflight: int,
    song_limit: int,
    config_path: Path,
    db_path: Path,
    timeout_sec: float,
    service_mode: str,
    service_defaults: str,
    priority_queue: str,
    benchmark_mode: bool,
    skip_stats_verify: bool,
) -> dict:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["METAFINDER_OUTPUT"] = "1"
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["METAFINDER_THROUGHPUT"] = "1"
    env["SONG_QUEUE_LIMIT"] = str(int(song_limit))
    env["IN_FLIGHT_SONGS"] = str(int(inflight))
    if int(inflight) > 1:
        env.setdefault("GPU_SONG_SLOTS", str(max(24, int(inflight) + 1)))
    env["EVOLUTION_DB_PATH"] = str(db_path)

    _apply_env_mode(env, "ROBEATSMETA_OPTIMIZER_SERVICE_MODE", service_mode)
    _apply_env_mode(env, "ROBEATSMETA_OPTIMIZER_SERVICE_DEFAULTS", service_defaults)
    _apply_env_mode(env, "ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", priority_queue)
    if benchmark_mode:
        env["ROBEATSMETA_OPTIMIZER_BENCHMARK_MODE"] = "1"
        env["METAFINDER_BENCHMARK_MODE"] = "1"
    else:
        env.pop("ROBEATSMETA_OPTIMIZER_BENCHMARK_MODE", None)
        env.pop("METAFINDER_BENCHMARK_MODE", None)
    if skip_stats_verify:
        env["METAFINDER_SKIP_STATS_INTEGRITY_VERIFY"] = "1"
    else:
        env.pop("METAFINDER_SKIP_STATS_INTEGRITY_VERIFY", None)

    env["METAFINDER_DEBUG_PROFILE"] = "0"
    for key in (
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
        env.pop(key, None)

    timed_out = False
    stdout = ""
    exit_code = None
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(repo_path),
            timeout=max(1.0, float(timeout_sec)),
        )
        stdout = proc.stdout or ""
        exit_code = int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        partial = exc.stdout or ""
        stdout = partial.decode("utf-8", errors="replace") if isinstance(partial, bytes) else str(partial)
    wall_s = time.perf_counter() - t0

    throughput = _parse_throughput(stdout, wall_s)
    return {
        "repo_path": str(repo_path),
        "inflight": int(inflight),
        "song_limit": int(song_limit),
        "service_mode": str(service_mode),
        "service_defaults": str(service_defaults),
        "priority_queue": str(priority_queue),
        "benchmark_mode": bool(benchmark_mode),
        "skip_stats_verify": bool(skip_stats_verify),
        "timed_out": bool(timed_out),
        "exit_code": None if exit_code is None else int(exit_code),
        "wall_s": float(wall_s),
        "db_path": str(db_path),
        "throughput": throughput,
        "log_tail": stdout[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Target repo root to benchmark.")
    parser.add_argument("--song-limit", type=int, default=120)
    parser.add_argument("--inflight", default="12,18,22", help="Comma-separated InFlightSongs values to test.")
    parser.add_argument("--config", default="config.ini")
    parser.add_argument("--service-mode", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--service-defaults", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--priority-queue", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--benchmark-mode", action="store_true", help="Enable bounded service-default benchmarking.")
    parser.add_argument("--skip-stats-verify", action="store_true", help="Skip the fresh-queue stats integrity verifier.")
    parser.add_argument("--timeout-sec", type=float, default=900.0)
    parser.add_argument("--out", default=str(Path("artifacts") / "bench" / "queue120_inflight_throughput.json"))
    args = parser.parse_args()

    repo_path = Path(args.repo).expanduser().resolve()
    if not repo_path.exists():
        raise SystemExit(f"Repo not found: {repo_path}")

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
    if not config_path.is_absolute():
        config_path = (repo_path / config_path).resolve()
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for inflight in inflight_vals:
        db_path = repo_path / "artifacts" / "bench" / f"queue_songlimit{song_limit}_inflight{inflight}.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            try:
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        res = _run_one(
            repo_path=repo_path,
            inflight=inflight,
            song_limit=song_limit,
            config_path=config_path,
            db_path=db_path,
            timeout_sec=float(args.timeout_sec),
            service_mode=args.service_mode,
            service_defaults=args.service_defaults,
            priority_queue=args.priority_queue,
            benchmark_mode=bool(args.benchmark_mode),
            skip_stats_verify=bool(args.skip_stats_verify),
        )
        results.append(res)
        t = res.get("throughput") or {}
        print(
            " ".join(
                [
                    f"inflight={inflight}",
                    f"exit={res['exit_code']}",
                    f"timeout={res['timed_out']}",
                    f"wall_s={res['wall_s']:.1f}",
                    f"tasks/h={t.get('tasks_per_h')}",
                    f"songs/h={t.get('songs_per_h')}",
                    f"source={t.get('source')}",
                ]
            )
        )

    payload = {
        "repo_path": str(repo_path),
        "config_path": str(config_path),
        "song_limit": int(song_limit),
        "inflight": inflight_vals,
        "service_mode": str(args.service_mode),
        "service_defaults": str(args.service_defaults),
        "priority_queue": str(args.priority_queue),
        "benchmark_mode": bool(args.benchmark_mode),
        "skip_stats_verify": bool(args.skip_stats_verify),
        "timeout_sec": float(args.timeout_sec),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
