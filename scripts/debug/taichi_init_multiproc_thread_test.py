"""
Repro: init Taichi/Vulkan from a non-main thread inside spawned processes.

Dual-process in-flight workers start the in-process GPU executor, which initializes
Taichi inside a background thread. Some Windows/Vulkan stacks can behave differently
when initialization happens off the main thread.

Usage (PowerShell):
  python scripts/debug/taichi_init_multiproc_thread_test.py
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import threading
import traceback
from pathlib import Path


def _worker(i: int) -> None:
    # Ensure spawned children can import the repo package when this script is run directly.
    try:
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root))
        os.chdir(str(repo_root))
    except Exception:
        pass

    out: dict[str, object] = {"ok": False, "err": ""}

    def _thread_main() -> None:
        try:
            from gear_optimizer.solver.taichi_gem.runtime import init_taichi

            init_taichi()
            out["ok"] = True
        except Exception as exc:
            out["ok"] = False
            out["err"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"

    t = threading.Thread(target=_thread_main, name="taichi_init_thread")
    t.start()
    t.join()

    ok = bool(out.get("ok"))
    err = str(out.get("err") or "")
    if ok:
        print(f"worker {i}: OK (thread init)")
        return
    print(f"worker {i}: FAIL (thread init) {err.splitlines()[0] if err else ''}")
    if err:
        print(err)


def main() -> None:
    ctx = mp.get_context("spawn")
    daemon = str(os.environ.get("TAICHI_INIT_DAEMON", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    procs: list[mp.Process] = []
    for i in range(2):
        p = ctx.Process(target=_worker, args=(i,))
        p.daemon = daemon
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
    print("exitcodes:", [p.exitcode for p in procs])


if __name__ == "__main__":
    main()

