from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path
from typing import Sequence

from gear_optimizer.core.config import find_and_cache_paths, get_config_path, load_config, load_paths_cache
from gear_optimizer.core.parsing import config_bool, env_flag

REPO_ROOT = Path(__file__).resolve().parents[1]


def common_init() -> None:
    multiprocessing.freeze_support()


def _read_config_path() -> str:
    return get_config_path("config.ini")


def _debug_profile_enabled(cfg_path: str) -> bool:
    if env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE"):
        return True
    try:
        cfg = load_config(cfg_path)
        return config_bool(cfg, "Debug", "DebugProfile", default=False) or config_bool(
            cfg,
            "IterationEngine",
            "DebugProfile",
            default=False,
        )
    except Exception:
        return False


def _apply_debug_profile_env(cfg_path: str) -> None:
    if _debug_profile_enabled(cfg_path):
        os.environ.setdefault("METAFINDER_DEBUG_PROFILE", "1")
        return
    for key in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "GPU_SERVICE_PROFILE",
        "GPU_SERVICE_PROFILE_PRINT",
        "INFLIGHT_STAGE_PROFILE",
        "INFLIGHT_STAGE_PROFILE_EMIT_SEC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(key, None)


def _apply_throughput_mode_env() -> None:
    throughput = env_flag("METAFINDER_THROUGHPUT")
    allow_profiling = env_flag("METAFINDER_ALLOW_PROFILING")
    if not throughput and allow_profiling:
        return
    for key in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(key, None)


def _apply_taichi_shell_env() -> None:
    os.environ.setdefault("TI_ENABLE_PYBUF", "0")


def _apply_gpu_song_slots_default() -> None:
    if "GPU_SONG_SLOTS" in os.environ:
        return
    cfg_path = _read_config_path()
    try:
        cfg = load_config(cfg_path)
        cfg_slots = int(str(cfg.get("IterationEngine", "GPU_SongSlots", fallback="0") or "0"))
    except Exception:
        cfg_slots = 0
    if cfg_slots > 0:
        os.environ.setdefault("GPU_SONG_SLOTS", str(cfg_slots))


def _apply_service_mode_frontier_threads() -> None:
    if not env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE"):
        return
    from gear_optimizer.core.cpu_affinity import frontier_prebuild_cpu_count
    from gear_optimizer.solver.timeline_exact_frontier import configure_timeline_pair_build_threads

    configure_timeline_pair_build_threads(frontier_prebuild_cpu_count())


def run() -> int:
    common_init()
    try:
        # Configure durable diagnostics logging BEFORE importing the solver/Taichi stack.
        # The heavy import chain behind `gear_optimizer.app` can install a root logging
        # handler at import time; if it lands first, `configure_logging`'s respect-existing-
        # handlers guard would bail and `bin/error.log` would never get its file handler.
        from gear_optimizer.core.logging_config import configure_default_logging

        configure_default_logging()

        from gear_optimizer.client_update import update_and_restart_client

        update_and_restart_client()

        cfg_path = _read_config_path()
        _apply_taichi_shell_env()
        _apply_debug_profile_env(cfg_path)
        _apply_gpu_song_slots_default()
        _apply_throughput_mode_env()
        _apply_service_mode_frontier_threads()
        from gear_optimizer.app import GearOptimizerApp

        GearOptimizerApp().run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Fatal Error: {exc}")
        return 1


def sync_data() -> int:
    common_init()
    try:
        from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data

        print("Syncing optimizer gear/mini CSVs from exported_game_data.json ...")
        result = sync_exported_game_data(force=True)
        if not result.synced:
            raise RuntimeError(f"Forced exported-game-data sync did not run: {result.reason}")
        return 0
    except Exception as exc:
        print(f"Fatal Error: {exc}")
        return 1


def meta() -> int:
    common_init()
    print("=" * 60)
    print("GENERAL META - Universal Loadout Finder")
    print("=" * 60)
    print()
    try:
        from gear_optimizer.data.database import init_db
        from general_meta import export_general_meta_json, run_general_meta

        find_and_cache_paths()
        cfg = load_config(get_config_path(str(REPO_ROOT / "config.ini")))
        paths = load_paths_cache()
        init_db()
        results = run_general_meta(cfg, paths)
        output_path = export_general_meta_json(results)
        print("\n" + "=" * 60)
        print("GENERAL META COMPLETE")
        print("=" * 60)
        print(f"\nResults exported to: {output_path}")
        print(f"Processed {len(results.get('results', {}))} elemental combinations")
        return 0
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 0
    except Exception as exc:
        print(f"\nFatal Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metafinder")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run optimizer.")
    sub.add_parser("meta", help="Run GeneralMeta analysis.")
    sub.add_parser("sync-data", help="Regenerate Data/Gear CSVs from Data/exported_game_data.json.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "run":
        return run()
    if args.command == "meta":
        return meta()
    if args.command == "sync-data":
        return sync_data()
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
