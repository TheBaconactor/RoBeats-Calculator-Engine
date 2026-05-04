"""
Profile a full queue run (default: 120 songs) and capture GPU utilization dips.

What it records:
- Per-process GPU Engine utilization via Windows `typeperf` for this Python PID.
- GpuExecutor wait/exec trace via `GPU_EXECUTOR_TRACE_PATH`.
- Native in-flight stage profile via `INFLIGHT_STAGE_PROFILE_PATH` (if in-flight is enabled).

This script does NOT tune optimizer settings. It only sets:
- `SONG_QUEUE_LIMIT` (queue length)
- profiling env vars gated behind `DEBUG_PROFILE`
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from gear_optimizer.core.parsing import env_flag


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_float(v: Any) -> float:
    if v is None:
        return 0.0
    s = str(v).strip().strip('"')
    if not s or s in {" ", "NaN"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _parse_typeperf_timestamp(s: str) -> float | None:
    s = str(s or "").strip().strip('"')
    if not s:
        return None
    # Example: 12/30/2025 19:17:26.371
    for fmt in ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S"):
        try:
            dt = _dt.datetime.strptime(s, fmt)
            return dt.timestamp()
        except Exception:
            continue
    return None


def _read_typeperf_csv(path: Path, *, pid: int) -> dict[str, Any]:
    """
    Returns:
      {
        "samples": [{"ts": epoch_sec, "max_util": float, "compute_max_util": float}],
        "counter_count": int,  # filtered to this pid
        "counter_count_compute": int,  # filtered to this pid + compute engines
        "counter_count_total": int,
      }
    """
    samples: list[dict[str, Any]] = []
    counter_count = 0
    counter_count_compute = 0
    counter_count_total = 0
    keep_idxs: list[int] | None = None
    keep_compute_idxs: list[int] | None = None
    pid_tag = f"pid_{int(pid)}_"

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = None
        for row in reader:
            if not row:
                continue
            if header is None:
                header = row
                counter_count_total = max(0, len(header) - 1)
                keep_idxs = [i for i, name in enumerate(header[1:], start=1) if pid_tag in str(name or "").lower()]
                keep_compute_idxs = [
                    i
                    for i, name in enumerate(header[1:], start=1)
                    if (pid_tag in str(name or "").lower())
                    and (
                        "engtype_compute" in str(name or "").lower()
                        or "high priority compute" in str(name or "").lower()
                    )
                ]
                counter_count = int(len(keep_idxs))
                counter_count_compute = int(len(keep_compute_idxs))
                continue
            ts = _parse_typeperf_timestamp(row[0])
            if ts is None:
                continue
            if keep_idxs is None or keep_compute_idxs is None:
                continue
            vals = [_parse_float(row[i]) for i in keep_idxs if i < len(row)]
            compute_vals = [_parse_float(row[i]) for i in keep_compute_idxs if i < len(row)]
            if not vals:
                continue
            samples.append(
                {
                    "ts": float(ts),
                    "max_util": float(max(vals)),
                    "compute_max_util": float(max(compute_vals) if compute_vals else 0.0),
                }
            )

    return {
        "samples": samples,
        "counter_count": int(counter_count),
        "counter_count_compute": int(counter_count_compute),
        "counter_count_total": int(counter_count_total),
    }


def _summarize_series(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    # Windows GPU Engine counters can exceed 100% (multiple engines/adapters). Clamp for readability.
    values_c = [min(100.0, max(0.0, float(v))) for v in values]
    values_sorted = sorted(values_c)
    p50 = values_sorted[int(round(0.50 * (len(values_sorted) - 1)))]
    p95 = values_sorted[int(round(0.95 * (len(values_sorted) - 1)))]
    return {
        "count": int(len(values)),
        "avg": float(sum(values_sorted) / len(values_sorted)),
        "min": float(min(values_sorted)),
        "p50": float(p50),
        "p95": float(p95),
        "max": float(max(values_sorted)),
    }


def _find_low_util_intervals(
    samples: list[dict[str, Any]], *, threshold: float, min_len_s: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not samples:
        return out

    # Assume samples are ~1Hz and timestamp ordered.
    in_run = False
    start_idx = 0
    min_util = 1e9
    for i, s in enumerate(samples):
        util = float(s.get("compute_max_util", s.get("max_util", 0.0)) or 0.0)
        util = min(100.0, max(0.0, util))
        low = util < float(threshold)
        if low and not in_run:
            in_run = True
            start_idx = i
            min_util = util
        elif low and in_run:
            if util < min_util:
                min_util = util
        elif (not low) and in_run:
            in_run = False
            end_idx = i - 1
            t0 = float(samples[start_idx]["ts"])
            t1 = float(samples[end_idx]["ts"])
            dur = t1 - t0
            if dur >= float(min_len_s):
                out.append({"t0": t0, "t1": t1, "dur_s": float(dur), "min_max_util": float(min_util)})
    if in_run:
        end_idx = len(samples) - 1
        t0 = float(samples[start_idx]["ts"])
        t1 = float(samples[end_idx]["ts"])
        dur = t1 - t0
        if dur >= float(min_len_s):
            out.append({"t0": t0, "t1": t1, "dur_s": float(dur), "min_max_util": float(min_util)})
    return out


def _read_gpu_executor_trace(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"events": []}
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                events.append(
                    {
                        "wall_ts": float(row.get("wall_ts") or 0.0),
                        "event": str(row.get("event") or ""),
                        "wait_sec": float(row.get("wait_sec") or 0.0),
                        "exec_sec": float(row.get("exec_sec") or 0.0),
                        "types": str(row.get("types") or ""),
                        "batch_size": int(float(row.get("batch_size") or 0.0)),
                    }
                )
            except Exception:
                continue
    return {"events": events}


def _correlate_intervals_with_trace(
    intervals: list[dict[str, Any]],
    trace_events: list[dict[str, Any]],
    *,
    pad_s: float = 2.0,
) -> list[dict[str, Any]]:
    if not intervals or not trace_events:
        return []

    out: list[dict[str, Any]] = []
    for itv in intervals:
        t0 = float(itv["t0"]) - float(pad_s)
        t1 = float(itv["t1"]) + float(pad_s)
        window = [e for e in trace_events if t0 <= float(e.get("wall_ts", 0.0) or 0.0) <= t1]
        if not window:
            out.append({**itv, "trace": {"events": 0}})
            continue

        exec_types: dict[str, int] = {}
        wait_sum = 0.0
        exec_sum = 0.0
        for e in window:
            if e.get("event") == "wait":
                wait_sum += float(e.get("wait_sec", 0.0) or 0.0)
            elif e.get("event") == "exec":
                exec_sum += float(e.get("exec_sec", 0.0) or 0.0)
                name = str(e.get("types") or "")
                exec_types[name] = int(exec_types.get(name, 0) + 1)

        top_exec = sorted(exec_types.items(), key=lambda kv: kv[1], reverse=True)[:6]
        out.append(
            {
                **itv,
                "trace": {
                    "events": int(len(window)),
                    "wait_sum_s": float(wait_sum),
                    "exec_sum_s": float(exec_sum),
                    "busy_pct": float(100.0 * exec_sum / (exec_sum + wait_sum + 1e-9)),
                    "top_exec_types": top_exec,
                },
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--sample-interval-sec", type=int, default=1)
    ap.add_argument("--low-threshold", type=float, default=30.0)
    ap.add_argument("--low-min-len-sec", type=int, default=3)
    args = ap.parse_args()

    root = _repo_root()
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()

    # Use the same config + settings resolution as `main.py`, only changing the queue limit.
    os.environ["SONG_QUEUE_LIMIT"] = str(int(args.limit))

    # Profiling is gated behind DebugProfile in main; this forces it on for this run without
    # changing config.ini.
    os.environ["DEBUG_PROFILE"] = "1"
    os.environ.setdefault("GPU_EXECUTOR_PROFILE", "1")
    os.environ.setdefault("INFLIGHT_STAGE_PROFILE", "1")

    # Persist trace/profile artifacts.
    trace_path = bin_dir / f"gpu_executor_trace_{int(args.limit)}_{ts}.csv"
    stage_path = bin_dir / f"inflight_stage_profile_{int(args.limit)}_{ts}.json"
    summary_path = bin_dir / f"gpu_usage_summary_{int(args.limit)}_{ts}.json"
    gpu_csv = bin_dir / f"gpu_typeperf_pid_{pid}_{int(args.limit)}_{ts}.csv"
    gpu_err = bin_dir / f"gpu_typeperf_pid_{pid}_{int(args.limit)}_{ts}.err.txt"

    os.environ["GPU_EXECUTOR_TRACE_PATH"] = str(trace_path)
    os.environ["INFLIGHT_STAGE_PROFILE_PATH"] = str(stage_path)

    # Per-PID GPU Engine instances only appear after the process uses the GPU.
    # We start `typeperf` in a background retry-loop so we don't fail early with "No valid counters."
    counter = rf"\GPU Engine(pid_{pid}_*)\Utilization Percentage"
    tp_args = [
        "typeperf",
        counter,
        "-si",
        str(int(args.sample_interval_sec)),
        "-f",
        "CSV",
        "-y",
        "-o",
        str(gpu_csv.resolve()),
    ]

    tp_proc: subprocess.Popen | None = None
    tp_stderr_fh = None
    tp_lock = threading.Lock()
    tp_started = threading.Event()
    tp_stop = threading.Event()
    t0 = time.perf_counter()
    dt = 0.0
    try:

        def _typeperf_worker() -> None:
            nonlocal tp_proc, tp_stderr_fh
            while not tp_stop.is_set():
                try:
                    if gpu_csv.exists():
                        gpu_csv.unlink()
                except Exception:
                    pass
                try:
                    if gpu_err.exists():
                        gpu_err.unlink()
                except Exception:
                    pass

                try:
                    stderr_fh = gpu_err.open("w", encoding="utf-8")
                    proc = subprocess.Popen(
                        tp_args,
                        stdout=subprocess.DEVNULL,
                        stderr=stderr_fh,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    )
                except Exception:
                    try:
                        stderr_fh.close()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    continue

                # If counters aren't ready, `typeperf` exits quickly with no output file.
                time.sleep(0.75)
                if proc.poll() is not None and not gpu_csv.exists():
                    try:
                        stderr_fh.close()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    continue

                with tp_lock:
                    tp_proc = proc
                    tp_stderr_fh = stderr_fh
                tp_started.set()
                break

            # Wait for stop and then exit cleanly.
            tp_started.wait(timeout=0)  # no-op if already set
            tp_stop.wait()
            with tp_lock:
                proc = tp_proc
                stderr_fh = tp_stderr_fh
            if proc is not None and proc.poll() is None:
                try:
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    pass
                try:
                    proc.wait(timeout=15)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            try:
                if stderr_fh is not None:
                    stderr_fh.close()
            except Exception:
                pass

        threading.Thread(target=_typeperf_worker, name="TypePerfSupervisor", daemon=True).start()

        # Run the app inline so the PID matches the typeperf filter.
        project_root = str(root)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        import main as metafinder_main

        cfg_path = metafinder_main._read_config_path()
        metafinder_main._apply_debug_profile_env(cfg_path)
        metafinder_main._apply_gpu_song_slots_default()
        metafinder_main._apply_throughput_mode_env()

        from gear_optimizer.app import GearOptimizerApp

        GearOptimizerApp().run()
    finally:
        dt = time.perf_counter() - t0
        tp_stop.set()
        tp_started.wait(timeout=2.0)
        if tp_started.is_set():
            for _ in range(80):
                if gpu_csv.exists():
                    break
                time.sleep(0.05)

        # Analyze GPU utilization and correlate with GPU executor trace.
        summary: dict[str, Any] = {
            "run": {
                "queue_limit": int(args.limit),
                "wall_s": float(dt),
                "pid": int(pid),
                "typeperf_started": bool(tp_started.is_set()),
                "gpu_typeperf_csv": str(gpu_csv),
                "gpu_executor_trace_csv": str(trace_path),
                "inflight_stage_profile_json": str(stage_path),
            }
        }

        if gpu_csv.exists():
            tp = _read_typeperf_csv(gpu_csv, pid=int(pid))
            samples = list(tp.get("samples") or [])
            max_series = [float(s.get("max_util", 0.0) or 0.0) for s in samples]
            compute_max_series = [float(s.get("compute_max_util", 0.0) or 0.0) for s in samples]
            summary["typeperf"] = {
                "counter_count": int(tp.get("counter_count") or 0),
                "counter_count_compute": int(tp.get("counter_count_compute") or 0),
                "counter_count_total": int(tp.get("counter_count_total") or 0),
                "samples": int(len(samples)),
                "max_util": _summarize_series(max_series),
                "compute_max_util": _summarize_series(compute_max_series),
            }

            low = _find_low_util_intervals(
                samples,
                threshold=float(args.low_threshold),
                min_len_s=int(args.low_min_len_sec),
            )
            summary["low_util_intervals"] = {
                "threshold": float(args.low_threshold),
                "min_len_s": int(args.low_min_len_sec),
                "count": int(len(low)),
                "intervals": low[:50],  # cap for file size
            }
        else:
            err_txt = ""
            try:
                if gpu_err.exists():
                    err_txt = gpu_err.read_text(encoding="utf-8", errors="replace")[-2000:]
            except Exception:
                err_txt = ""
            summary["typeperf"] = {"error": "missing typeperf csv", "stderr_tail": err_txt}

        trace = _read_gpu_executor_trace(trace_path)
        events = list(trace.get("events") or [])
        summary["gpu_executor_trace"] = {"events": int(len(events))}

        intervals = list((summary.get("low_util_intervals") or {}).get("intervals") or [])
        if intervals and events:
            summary["low_util_trace_correlation"] = _correlate_intervals_with_trace(intervals, events, pad_s=2.0)

        try:
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass

        # Print a compact summary for the console.
        try:
            tp0 = summary.get("typeperf", {}) if isinstance(summary.get("typeperf"), dict) else {}
            tp_sum = tp0.get("compute_max_util", {}) or tp0.get("max_util", {})
            low_count = int((summary.get("low_util_intervals") or {}).get("count") or 0)
            print(
                "[Profile120] "
                f"wall_s={dt:.2f} "
                f"gpu_max_avg={float(tp_sum.get('avg') or 0.0):.1f}% "
                f"gpu_max_p95={float(tp_sum.get('p95') or 0.0):.1f}% "
                f"low_intervals={low_count} "
                f"summary={summary_path}"
            )
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
