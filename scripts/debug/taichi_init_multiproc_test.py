"""
Repro: init Taichi/Vulkan from multiple spawned processes.

This is used to diagnose dual-process in-flight startup failures on Windows/Vulkan.

Usage (PowerShell):
  $env:PYTHONUTF8='1'
  python scripts/debug/taichi_init_multiproc_test.py
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
from pathlib import Path


from gear_optimizer.core.parsing import env_get
def _worker(i: int) -> None:
    # Ensure spawned children can import the repo package when this script is run directly.
    try:
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root))
        os.chdir(str(repo_root))
    except Exception:
        pass
    try:
        from gear_optimizer.solver.taichi_gem.runtime import init_taichi

        init_taichi()
        print(f"worker {i}: OK")
    except Exception as exc:
        import traceback

        print(f"worker {i}: FAIL {type(exc).__name__}: {exc}")
        traceback.print_exc()


def main() -> None:
    ctx = mp.get_context("spawn")
    daemon = str(env_get("TAICHI_INIT_DAEMON", "") or "").strip().lower() in {"1", "true", "yes", "on"}
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
