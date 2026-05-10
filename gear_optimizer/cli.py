from __future__ import annotations

import argparse
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence
import logging

from gear_optimizer.core.config import find_and_cache_paths, get_config_path, load_config, load_paths_cache
from gear_optimizer.core.parsing import env_flag
from gear_optimizer.data.database import init_db



logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]


def common_init() -> None:
    multiprocessing.freeze_support()


def _read_config_path() -> str:
    return get_config_path("config.ini")


def _debug_profile_enabled(cfg_path: str) -> bool:
    del cfg_path
    if env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE"):
        return True
    return False


def _apply_debug_profile_env(cfg_path: str) -> None:
    if _debug_profile_enabled(cfg_path):
        os.environ.setdefault("METAFINDER_DEBUG_PROFILE", "1")
        return
    for k in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "GPU_EXECUTOR_PROFILE",
        "GPU_PROFILER",
        "GPU_SERVICE_PROFILE",
        "GPU_SERVICE_PROFILE_PRINT",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(k, None)


def _apply_throughput_mode_env() -> None:
    throughput = env_flag("METAFINDER_THROUGHPUT") or env_flag("THROUGHPUT_MODE")
    allow_profiling = env_flag("METAFINDER_ALLOW_PROFILING")
    if not throughput and allow_profiling:
        return
    if throughput or not allow_profiling:
        for k in (
            "PERF_TIMING",
            "GPU_SYNC_FOR_TIMING",
            "GPU_FORCE_SYNC",
            "TAICHI_KERNEL_PROFILER",
            "TAICHI_KERNEL_PROFILER_PRINT",
        ):
            os.environ.pop(k, None)


def _apply_taichi_shell_env() -> None:
    os.environ.setdefault("TI_ENABLE_PYBUF", "0")


def run() -> int:
    common_init()
    try:
        cfg_path = _read_config_path()
        _apply_taichi_shell_env()
        _apply_debug_profile_env(cfg_path)
        _apply_throughput_mode_env()
        from gear_optimizer.app import GearOptimizerApp

        app = GearOptimizerApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Fatal Error: {e}")
        return 1


def _sync_optimizer_csvs_from_exported_data(repo_root: Path) -> None:
    exporter = repo_root / "tools" / "data" / "export_game_data_gear_minis.py"
    exported_data = repo_root / "Data" / "exported_game_data.json"
    gears_out = repo_root / "Data" / "Gear" / "Gears.csv"
    minis_out = repo_root / "Data" / "Gear" / "Minis.csv"

    if not exporter.exists():
        raise FileNotFoundError(f"Missing exporter script: {exporter}")
    if not exported_data.exists():
        raise FileNotFoundError(f"Missing exported game data: {exported_data}")

    cmd = [
        sys.executable,
        str(exporter),
        "--input",
        str(exported_data),
        "--gears-out",
        str(gears_out),
        "--minis-out",
        str(minis_out),
    ]
    print("Syncing optimizer gear/mini CSVs from exported_game_data.json ...")
    subprocess.run(cmd, check=True, cwd=str(repo_root))


def meta() -> int:
    common_init()
    print("=" * 60)
    print("GENERAL META - Universal Loadout Finder")
    print("=" * 60)
    print()
    try:
        from general_meta import export_general_meta_json, run_general_meta

        _sync_optimizer_csvs_from_exported_data(REPO_ROOT)
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
    except Exception as e:
        print(f"\nFatal Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def inventory(argv: Sequence[str] | None = None) -> int:
    """
    Delegate to the inventory entry implementation.
    """
    from gear_optimizer.inventory_cli import main as inventory_main

    return int(inventory_main(list(argv) if argv is not None else None))


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metafinder")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Run optimizer.")
    sub.add_parser("meta", help="Run GeneralMeta analysis.")
    inv = sub.add_parser("inventory", help="Run inventory coverage CLI.")
    inv.add_argument("inventory_args", nargs=argparse.REMAINDER, help="Args forwarded to inventory CLI.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "run":
        return run()
    if args.command == "meta":
        return meta()
    if args.command == "inventory":
        return inventory(getattr(args, "inventory_args", []) or [])
    parser.error(f"Unknown command: {args.command}")
    return 2
