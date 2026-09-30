from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.core.macos_background import (
    make_process_background_only,
    reassert_process_background_only,
)

if __name__ == "__main__":
    make_process_background_only()

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import (
    MEMORY_GUARD_RESUME_FILE,
    MemoryGuardResumeTracker,
    build_memory_guard_resume_context,
    compute_memory_guard_limit,
    set_memory_watchdog_limit,
)
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list
from gear_optimizer.data.database import get_best_loadouts, init_db
from gear_optimizer.data.database.connection import close_cached_db_connection
from gear_optimizer.gamedata import load_stat_curves
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
        self._all_gears: list[dict[str, Any]] = []
        self._all_minis: list[dict[str, Any]] = []
        self._gears_by_name: dict[str, dict[str, Any]] = {}
        self._minis_by_name: dict[str, dict[str, Any]] = {}
        self._initialized = False
        self._request_count = 0
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
        self._curves = load_stat_curves(paths().stats_txt)
        self._all_gears = load_all_gears_list()
        self._all_minis = load_all_minis_list()
        self._gears_by_name = {str(item["Name"]): item for item in self._all_gears}
        self._minis_by_name = {str(item["Name"]): item for item in self._all_minis}

        # Size the GA run buffers for the largest multi-start a request can ask for.
        self._app._configure_execution_and_prewarm(reasoning_search("max")[1])
        reassert_process_background_only()
        self._initialized = True

    def _remove_result_db(self) -> None:
        close_cached_db_connection(str(self._result_db))
        for path in (
            self._result_db,
            Path(f"{self._result_db}-wal"),
            Path(f"{self._result_db}-shm"),
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def solve(
        self,
        *,
        chart_text: str,
        song_name: str,
        repeats: int,
        reasoning: str,
    ) -> list[dict[str, Any]]:
        run = request_run_settings(repeats=repeats, reasoning=reasoning)
        self._chart_path.write_text(chart_text, encoding="utf-8")
        self._remove_result_db()
        if not self._initialized:
            self._initialize()
        assert self._curves is not None

        self._app._stop_cached_result = False
        self._app._stop_requested.clear()
        self._app._force_exit_requested.clear()
        set_memory_watchdog_limit(compute_memory_guard_limit(run))
        init_db()
        task_queue = [(str(self._chart_path), str(song_name), "Hard")]
        tasks = self._app._prepare_tasks(
            task_queue,
            run,
            self._curves,
            self._all_gears,
            self._all_minis,
            self._gears_by_name,
            self._minis_by_name,
        )
        if not tasks:
            raise RuntimeError("persistent optimizer produced no task")
        tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
        tracker.prime(task_queue, build_memory_guard_resume_context(*self._app._get_filter_params(run)))
        try:
            self._app._execute_tasks(tasks, tracker)
            if self._app._memory_guard_restart_needed(tracker):
                raise RuntimeError("persistent optimizer requested a memory-guard restart")
            entries = get_best_loadouts(
                song_name,
                limit=LOADOUTS_PER_SONG_LIMIT,
                team_buff="T5",
                db_path=str(self._result_db),
            )
            if not entries:
                raise RuntimeError("optimizer produced no T5 loadout")
            self._request_count += 1
            return entries
        finally:
            close_cached_db_connection(str(self._result_db))
            self._remove_result_db()


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
                    )
                    response = {"ok": True, "loadouts": result}
                except BaseException as exc:
                    response = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "restart": True}
                protocol.write(json.dumps(response, separators=(",", ":")) + "\n")
                protocol.flush()
                if not response.get("ok"):
                    break
        finally:
            sys.__stdout__ = original_stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
