from __future__ import annotations

import json
import os
import time
from pathlib import Path
import multiprocessing as mp
import sys

# Spawned child processes may not inherit repo-root on sys.path (Windows spawn),
# so insert it explicitly for local package imports.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _wait_for_warmup_done(hb_path: Path, *, timeout_sec: float) -> dict:
    deadline = time.monotonic() + float(timeout_sec)
    last = None
    while time.monotonic() < deadline:
        if hb_path.exists():
            data = _read_json(hb_path)
            if data is not None:
                last = data
                phase = str(data.get("phase") or "")
                ready = bool(data.get("ready"))
                if ready and phase in {"ready", "idle", "running", "warmup_cached", "stopping", "stopped"}:
                    return data
        time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for warmup done; last={last}")


def _worker(idx: int, *, run_dir: str, cache_key: str, q) -> None:
    run_dir_p = Path(run_dir)
    hb = run_dir_p / f"gpu_executor_heartbeat_warmup_probe.w{idx}.json"
    err_path = run_dir_p / f"worker_{idx}.error.txt"

    try:
        os.environ["TAICHI_OFFLINE_CACHE_KEY"] = str(cache_key)
        os.environ["GPU_EXECUTOR_WARMUP_FG"] = "1"
        os.environ["GPU_EXECUTOR_WARMUP_GA"] = "1"
        os.environ["GPU_EXECUTOR_HEARTBEAT_PATH"] = str(hb)
        os.environ["METAFINDER_PROGRESS"] = "0"

        from gear_optimizer.solver.gpu_executor import get_gpu_executor

        ex = get_gpu_executor()
        t0 = time.perf_counter()
        ex.start(in_process=True)
        try:
            data = _wait_for_warmup_done(hb, timeout_sec=1200.0)
            ok = True
            err = ""
        except Exception as exc:
            data = _read_json(hb) or {}
            ok = False
            err = f"{type(exc).__name__}: {exc}"

        dt = time.perf_counter() - t0
        try:
            ex.stop()
        except Exception:
            pass

        q.put(
            {
                "idx": int(idx),
                "ok": bool(ok),
                "error": str(err),
                "elapsed_sec": float(dt),
                "hb_path": str(hb),
                "phase": str((data or {}).get("phase") or ""),
                "note": str((data or {}).get("note") or ""),
            }
        )
    except Exception as exc:
        try:
            err_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        except Exception:
            pass
        try:
            q.put(
                {
                    "idx": int(idx),
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "elapsed_sec": 0.0,
                    "hb_path": str(hb),
                    "phase": "",
                    "note": "",
                }
            )
        except Exception:
            pass


def main() -> int:
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = (Path(__file__).resolve().parents[2] / "artifacts" / "debug" / f"warmup_probe3_{ts}").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    cache_key = f"warmup_probe3_cold_{ts}"

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [
        ctx.Process(target=_worker, kwargs={"idx": 0, "run_dir": str(run_dir), "cache_key": cache_key, "q": q}),
        ctx.Process(target=_worker, kwargs={"idx": 1, "run_dir": str(run_dir), "cache_key": cache_key, "q": q}),
    ]

    wall_t0 = time.perf_counter()
    for p in procs:
        p.start()

    results = []
    # Keep this probe bounded: if workers fail to start, don't hang forever.
    deadline = time.monotonic() + 300.0
    while len(results) < 2 and time.monotonic() < deadline:
        try:
            results.append(q.get(timeout=0.5))
        except Exception:
            pass

    for p in procs:
        p.join(timeout=5.0)
        if p.is_alive():
            p.terminate()

    wall_sec = time.perf_counter() - wall_t0

    print(f"run_dir={run_dir}")
    print(f"cache_key={cache_key}")
    print(f"wall_sec={wall_sec:.2f}")
    for r in sorted(results, key=lambda x: x.get("idx", 0)):
        print(r)
    if len(results) < 2:
        print(f"missing_results={2 - len(results)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
