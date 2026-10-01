from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from typing import Sequence

from gear_optimizer import settings


def common_init() -> None:
    multiprocessing.freeze_support()


def _apply_taichi_shell_env() -> None:
    os.environ.setdefault("TI_ENABLE_PYBUF", "0")


def _apply_service_mode_frontier_threads() -> None:
    if not settings.service_mode():
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

        _apply_taichi_shell_env()
        _apply_service_mode_frontier_threads()
        from gear_optimizer.app import GearOptimizerApp

        return GearOptimizerApp().run()
    except KeyboardInterrupt:
        return 0


def sync_data() -> int:
    common_init()
    from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data

    print("Syncing optimizer gear/mini CSVs from exported_game_data.json ...")
    result = sync_exported_game_data(force=True)
    if not result.synced:
        raise RuntimeError(f"Forced exported-game-data sync did not run: {result.reason}")
    return 0


def meta() -> int:
    common_init()
    print("=" * 60)
    print("GENERAL META - Universal Loadout Finder")
    print("=" * 60)
    print()
    try:
        from gear_optimizer.settings import paths
        from gear_optimizer.store import schema
        from general_meta import export_general_meta_json, run_general_meta

        schema.ensure(paths().database)
        results = run_general_meta()
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
    return {"run": run, "meta": meta, "sync-data": sync_data}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
