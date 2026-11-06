"""The :8765 service's solve process: one JSON request per stdin line, one JSON answer per stdout line. The GPU executor
keeps Taichi and the kernels warm between requests, and each request has its own result database."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from gear_optimizer.core.macos_background import make_process_background_only, reassert_process_background_only

if __name__ == "__main__":
    make_process_background_only()

from gear_optimizer.core.memory import compute_memory_guard_limit, memory_release_requested, set_memory_watchdog_limit
from gear_optimizer.data.game_export import custom_catalog, load_catalog
from gear_optimizer.domain.jobs import SharedRunContext
from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.pipeline.queue import chart_tasks
from gear_optimizer.settings import RunSettings, paths, reasoning_search
from gear_optimizer.store import db, legacy, schema


def solve(request: dict[str, Any], executor: Any) -> list[dict[str, Any]]:
    """One chart's T5 leaderboard. `promoteTo` (a clean official solve) also merges every result into that database."""
    from gear_optimizer.frontier.startup_prebuild import run_startup_cpu_work
    from gear_optimizer.pipeline.solve import solve_song
    from gear_optimizer.pipeline.storing import store_solve

    engine_paths = paths()
    chart_path, result_db = engine_paths.bin_path("service_request.txt"), engine_paths.database
    chart_path.write_text(request["chartText"], encoding="utf-8")
    depth, multi_start = reasoning_search(request["reasoning"])
    run = RunSettings(search_depth=depth, multi_start=multi_start)
    catalog = custom_catalog(load_catalog(engine_paths.game_export), request["customPool"])
    context = SharedRunContext(multi_start=multi_start, curves=stat_curves(), gears=catalog.gears, minis=catalog.minis,
                               ga_depth=depth)
    tasks = chart_tasks(chart_path, run, context)
    mode = tasks[0].mode  # a request solves the one mode of its Timing Mode header
    if request["uploaded"]:
        run_startup_cpu_work(charts_by_mode={mode: [str(chart_path)]}, curves=context.curves)
    set_memory_watchdog_limit(compute_memory_guard_limit(run))
    try:
        schema.ensure(result_db)
        with contextlib.closing(schema.connect(result_db, write=True)) as conn:
            for task in tasks:
                store_solve(conn, solve_song(task, executor), dict(catalog.gears), dict(catalog.minis))
        entries = legacy.read_best_loadouts(result_db, mode, request["songName"], "T5", limit=LOADOUTS_PER_SONG_LIMIT)
        if not entries:
            raise RuntimeError("optimizer produced no T5 loadout")
        if request["promoteTo"]:
            db.promote(result_db, request["promoteTo"], mode, request["songName"], "T5")
        return entries
    finally:
        for path in (result_db, Path(f"{result_db}-wal"), Path(f"{result_db}-shm")):
            path.unlink(missing_ok=True)


def _started_executor(request: dict[str, Any]) -> Any:
    """The GPU executor, with GA buffers for every multi-start this worker can get: an uploaded chart's worker serves that
    chart alone, the warm worker any reasoning level."""
    from gear_optimizer.gpu.executor import start_gpu_executor

    executor = start_gpu_executor(reasoning_search(request["reasoning"] if request["uploaded"] else "max")[1])
    reassert_process_background_only()
    return executor


def main() -> int:
    make_process_background_only()
    from gear_optimizer.cli import apply_service_frontier_threads
    from gear_optimizer.core.logging_config import configure_default_logging

    answers = sys.stdout
    with open(os.devnull, "w", encoding="utf-8") as devnull, contextlib.redirect_stdout(devnull):
        sys.__stdout__ = devnull
        configure_default_logging()
        os.environ.setdefault("TI_ENABLE_PYBUF", "0")
        apply_service_frontier_threads()
        reassert_process_background_only()
        from gear_optimizer.gpu.executor import is_fatal_gpu_error

        executor = None
        for line in sys.stdin:
            try:
                request = json.loads(line)
                executor = executor or _started_executor(request)
                answer = {"ok": True, "loadouts": solve(request, executor)}
            except Exception as exc:
                # A failed request leaves nothing behind; the worker keeps serving unless its GPU is gone.
                answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": is_fatal_gpu_error(exc)}
            except BaseException as exc:
                answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": True}
            answers.write(json.dumps(answer, separators=(",", ":")) + "\n")
            answers.flush()
            # Past the memory guard's limit the worker exits after answering; the service starts a fresh one.
            if answer.get("restart") or memory_release_requested():
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
