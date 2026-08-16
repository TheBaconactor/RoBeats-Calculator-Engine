from __future__ import annotations

import configparser
import contextlib
import copy
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from gear_optimizer.core.config import (
    AppRuntimeSettings,
    compute_memory_guard_limit,
    load_config,
    load_paths_cache,
)
from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS
from gear_optimizer.core.memory import (
    MEMORY_GUARD_RESUME_FILE,
    MemoryGuardResumeTracker,
    build_memory_guard_resume_context,
    set_memory_watchdog_limit,
)
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.data.database import get_best_loadouts, init_db
from gear_optimizer.data.database.connection import close_cached_db_connection
from gear_optimizer.core.parsing import env_str

_REPO_ROOT = Path(__file__).resolve().parents[1]


class PersistentOptimizerSession:
    def __init__(self) -> None:
        from gear_optimizer.app import GearOptimizerApp

        self._app = GearOptimizerApp()
        self._data_root = Path(PATHS.data_dir)
        self._bin_root = Path(PATHS.bin_dir)
        self._config_path = Path(env_str("METAFINDER_CONFIG_PATH", str(_REPO_ROOT / "config.ini")))
        self._chart_path = self._data_root / "Hard" / "service_request.txt"
        self._result_db = self._bin_root / "service_result.db"
        self._paths: dict[str, str] | None = None
        self._ref_arrays: dict[str, Any] | None = None
        self._all_gears: list[dict[str, Any]] = []
        self._all_minis: list[dict[str, Any]] = []
        self._gears_by_name: dict[str, dict[str, Any]] = {}
        self._minis_by_name: dict[str, dict[str, Any]] = {}
        self._initialized = False
        self._request_count = 0
        self._prepare_data_root()

    def _prepare_data_root(self) -> None:
        self._chart_path.parent.mkdir(parents=True, exist_ok=True)
        gear_dir = self._data_root / "Gear"
        if not gear_dir.is_dir():
            source = Path(env_str("ROBEATSMETA_OPTIMIZER_GEAR_SOURCE_DIR", ""))
            if not source.is_dir():
                raise RuntimeError(f"persistent optimizer gear source is unavailable: {source}")
            shutil.copytree(source, gear_dir)
        paths_cache = Path(PATHS.bin_path("paths_cache.json"))
        paths_cache.parent.mkdir(parents=True, exist_ok=True)
        paths_cache.write_text(
            json.dumps(
                {
                    "Easy": str(self._data_root / "Easy"),
                    "Normal": str(self._data_root / "Normal"),
                    "Hard": str(self._data_root / "Hard"),
                    "Gear": str(gear_dir),
                    "Gears": str(gear_dir / "Gears.csv"),
                    "Minis": str(gear_dir / "Minis.csv"),
                    "Stats": str(gear_dir / "Stats.txt"),
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _max_reasoning_config(cfg: configparser.ConfigParser) -> configparser.ConfigParser:
        result = copy.deepcopy(cfg)
        if not result.has_section("IterationEngine"):
            result.add_section("IterationEngine")
        result.set("IterationEngine", "GA_SearchDepth", "500")
        result.set("IterationEngine", "GA_MultiStart", "12")
        return result

    def _initialize(self, cfg: configparser.ConfigParser) -> None:
        paths = load_paths_cache()
        stats_path = paths.get("Stats", "") or str(self._data_root / "Gear" / "Stats.txt")
        stats_table = read_table(stats_path)
        self._paths = paths
        self._ref_arrays = self._app._preload_ref_arrays(stats_table)
        self._all_gears = load_all_gears_list(paths)
        self._all_minis = load_all_minis_list(paths)
        self._gears_by_name = {str(item["Name"]): item for item in self._all_gears}
        self._minis_by_name = {str(item["Name"]): item for item in self._all_minis}

        warm_cfg = self._max_reasoning_config(cfg)
        self._app._runtime_settings = AppRuntimeSettings.from_config(warm_cfg)
        self._app._configure_execution_and_prewarm(warm_cfg)
        self._initialized = True

    def _write_request_config(self, *, repeats: int, reasoning: str) -> None:
        cfg = configparser.ConfigParser()
        cfg.read_dict(
            {
                "CalculateSong": {
                    "LoopForever": "false",
                    "Difficulty": "Hard",
                },
                "IterationEngine": {
                    "IgnoreResumeQueue": "true",
                    "SongRepeats": str(max(1, int(repeats))),
                    "SongQueueLimit": "1",
                },
            }
        )
        if reasoning == "strong":
            cfg.set("IterationEngine", "GA_SearchDepth", "250")
            cfg.set("IterationEngine", "GA_MultiStart", "6")
        elif reasoning == "max":
            cfg.set("IterationEngine", "GA_SearchDepth", "500")
            cfg.set("IterationEngine", "GA_MultiStart", "12")
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_path.open("w", encoding="utf-8") as handle:
            cfg.write(handle)

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
        self._write_request_config(repeats=repeats, reasoning=reasoning)
        self._chart_path.write_text(chart_text, encoding="utf-8")
        os.environ["EVOLUTION_DB_PATH"] = str(self._result_db)
        self._remove_result_db()
        cfg = load_config(str(self._config_path))
        if not self._initialized:
            self._initialize(cfg)
        assert self._paths is not None
        assert self._ref_arrays is not None

        self._app._runtime_settings = AppRuntimeSettings.from_config(cfg)
        self._app._stop_cached_result = False
        self._app._stop_requested.clear()
        self._app._force_exit_requested.clear()
        set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
        init_db()
        self._app._disable_inputs_to_prevent_taint(cfg)
        task_queue = [(str(self._chart_path), str(song_name), "Hard")]
        tasks = self._app._prepare_tasks(
            task_queue,
            cfg,
            self._paths,
            self._ref_arrays,
            self._all_gears,
            self._all_minis,
            self._gears_by_name,
            self._minis_by_name,
            int(self._app._runtime_settings.ga.search_depth),
            bool(self._app._runtime_settings.iteration_engine.force_greats_debug),
        )
        if not tasks:
            raise RuntimeError("persistent optimizer produced no task")
        tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
        tracker.prime(task_queue, build_memory_guard_resume_context(*self._app._get_filter_params(cfg)))
        try:
            self._app._execute_tasks(
                tasks,
                int(self._app._runtime_settings.eval_cpu_cores),
                1,
                tracker,
                False,
            )
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
    from gear_optimizer.cli import (
        _apply_service_mode_frontier_threads,
        _apply_taichi_shell_env,
        _apply_throughput_mode_env,
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
            _apply_throughput_mode_env()
            _apply_service_mode_frontier_threads()
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
