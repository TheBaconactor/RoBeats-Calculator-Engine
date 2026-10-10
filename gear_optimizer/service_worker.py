from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from gear_optimizer.gamedata import Gear, Mini, StatCurves
from gear_optimizer.core.macos_background import (
    make_process_background_only,
    reassert_process_background_only,
)

if __name__ == "__main__":
    make_process_background_only()

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import (
    compute_memory_guard_limit,
    memory_release_requested,
    set_memory_watchdog_limit,
)
from gear_optimizer.store import db, legacy, schema
from gear_optimizer.gamedata import load_gears, load_minis, stat_curves
from gear_optimizer.settings import RunSettings, paths, reasoning_search, service_settings


def request_run_settings(*, repeats: int, reasoning: str) -> RunSettings:
    """The run settings of one service solve: the request's Hard chart once per repeat, no resume queue."""
    depth, multi_start = reasoning_search(reasoning)
    return RunSettings(
        difficulty="Hard",
        song_repeats=max(1, int(repeats)),
        song_queue_limit=1,
        ignore_resume_queue=True,
        search_depth=depth,
        multi_start=multi_start,
    )


class PersistentOptimizerSession:
    def __init__(self) -> None:
        from gear_optimizer.app import GearOptimizerApp

        self._app = GearOptimizerApp()
        engine_paths = paths()
        self._chart_path = engine_paths.chart_dir("Hard") / "service_request.txt"
        # Deleted between solves, so it must be this worker's own database (the service sets EVOLUTION_DB_PATH to it).
        self._result_db = engine_paths.bin_path("service_result.db")
        if engine_paths.database != self._result_db:
            raise RuntimeError(f"EVOLUTION_DB_PATH must be {self._result_db} for the persistent worker")
        self._curves: StatCurves | None = None
        self._gears: Mapping[str, Gear] = {}
        self._minis: Mapping[str, Mini] = {}
        self._initialized = False
        self._prepare_data_root()

    def _prepare_data_root(self) -> None:
        self._chart_path.parent.mkdir(parents=True, exist_ok=True)
        gear_dir = paths().gear_dir
        if not gear_dir.is_dir():
            source = Path(service_settings().gear_source_dir)
            if not source.is_dir():
                raise RuntimeError(f"persistent optimizer gear source is unavailable: {source}")
            shutil.copytree(source, gear_dir)

    def _initialize(self) -> None:
        self._curves = stat_curves()
        self._gears = load_gears(paths().gears_csv)
        self._minis = load_minis(paths().minis_csv)

        # Size the GA run buffers for the largest multi-start a request can ask for.
        self._app._configure_execution_and_prewarm(reasoning_search("max")[1])
        reassert_process_background_only()
        self._initialized = True

    def _remove_result_db(self) -> None:
        for path in (self._result_db, Path(f"{self._result_db}-wal"), Path(f"{self._result_db}-shm")):
            path.unlink(missing_ok=True)

    def solve(
        self,
        *,
        chart_text: str,
        song_name: str,
        repeats: int,
        reasoning: str,
        promote_to: str | None = None,
        gear_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """Solve one chart and return its T5 leaderboard; `promote_to` (a clean official solve) also merges every
        result into that catalog database; `gear_dir` holds the request's own Gears.csv / Minis.csv (a custom pool)."""
        run = request_run_settings(repeats=repeats, reasoning=reasoning)
        self._chart_path.write_text(chart_text, encoding="utf-8")
        self._remove_result_db()
        if not self._initialized:
            self._initialize()
        assert self._curves is not None
        gears, minis = self._gears, self._minis
        if gear_dir:
            gears, minis = load_gears(Path(gear_dir) / "Gears.csv"), load_minis(Path(gear_dir) / "Minis.csv")

        self._app._stop_cached_result = False
        self._app._stop_requested.clear()
        self._app._force_exit_requested.clear()
        set_memory_watchdog_limit(compute_memory_guard_limit(run))
        schema.ensure(self._result_db)
        tasks = self._app._prepare_tasks([(str(self._chart_path), song_name, "Hard")], run, self._curves, gears, minis)
        try:
            self._solve_direct(tasks, gears, minis)
            mode = tasks[0].mode  # the chart's Timing Mode header: a request solves one mode
            entries = legacy.read_best_loadouts(
                self._result_db, mode, song_name, "T5", limit=LOADOUTS_PER_SONG_LIMIT
            )
            if not entries:
                raise RuntimeError("optimizer produced no T5 loadout")
            if promote_to:
                db.promote(self._result_db, promote_to, mode, song_name, "T5")
            return entries
        finally:
            self._remove_result_db()

    def _solve_direct(self, tasks: list, gears: Mapping[str, Gear], minis: Mapping[str, Mini]) -> None:
        """Each task (a song repeat) solved in this process and stored into the result database."""
        from gear_optimizer.pipeline.post_processor import store_solve
        from gear_optimizer.pipeline.solve import solve_song
        from gear_optimizer.solver.gpu_executor import get_gpu_executor

        executor = get_gpu_executor()
        executor.start()  # once: it keeps Taichi and the kernels warm between requests
        conn = schema.connect(self._result_db, write=True)
        try:
            for task in tasks:
                store_solve(conn, solve_song(task, executor), dict(gears), dict(minis))
        finally:
            conn.close()


def main() -> int:
    make_process_background_only()
    from gear_optimizer.cli import (
        _apply_service_mode_frontier_threads,
        _apply_taichi_shell_env,
        common_init,
    )
    from gear_optimizer.core.logging_config import configure_default_logging

    protocol = sys.stdout
    original_stdout = sys.__stdout__
    with open(os.devnull, "w", encoding="utf-8") as devnull, contextlib.redirect_stdout(devnull):
        sys.__stdout__ = devnull
        try:
            common_init()
            configure_default_logging()
            _apply_taichi_shell_env()
            _apply_service_mode_frontier_threads()
            reassert_process_background_only()
            session = PersistentOptimizerSession()
            from gear_optimizer.solver.gpu_executor import is_fatal_gpu_error

            for raw_line in sys.stdin:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                    if not isinstance(request, dict):
                        raise ValueError("worker request must be an object")
                    result = session.solve(
                        chart_text=str(request.get("chartText") or ""),
                        song_name=str(request.get("songName") or ""),
                        repeats=int(request.get("repeats") or 1),
                        reasoning=str(request.get("reasoning") or "default"),
                        promote_to=request.get("promoteTo") or None,
                        gear_dir=request.get("gearDir") or None,
                    )
                    response = {"ok": True, "loadouts": result}
                except Exception as exc:
                    # A failed request leaves nothing behind (each one rewrites the chart and the result database);
                    # the worker keeps serving unless its GPU is gone.
                    response = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": is_fatal_gpu_error(exc)}
                except BaseException as exc:
                    response = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": True}
                protocol.write(json.dumps(response, separators=(",", ":")) + "\n")
                protocol.flush()
                # Past the memory guard's limit the worker exits after answering; the service starts a fresh one.
                if response.get("restart") or memory_release_requested():
                    break
        finally:
            sys.__stdout__ = original_stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
