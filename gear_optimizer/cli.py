from __future__ import annotations

import argparse
import multiprocessing
import sys
from typing import Sequence

from gear_optimizer import settings


def common_init() -> None:
    multiprocessing.freeze_support()


def apply_service_frontier_threads() -> None:
    if not settings.service_mode():
        return
    from gear_optimizer.core.cpu_affinity import frontier_prebuild_cpu_count
    from gear_optimizer.frontier.timeline_producer import configure_timeline_pair_build_threads

    configure_timeline_pair_build_threads(frontier_prebuild_cpu_count())


def run() -> int:
    common_init()
    try:
        from gear_optimizer.core.cpu_affinity import pin_to_performance_cores
        from gear_optimizer.core.logging_config import configure_default_logging

        # On a hybrid Intel CPU, force the fast P-cores before the worker pool spawns (workers inherit
        # affinity). Without this, Windows EcoQoS parks the cold FG build on the slow E-cores.
        pin_to_performance_cores()
        configure_default_logging()
        apply_service_frontier_threads()
        from gear_optimizer.app import GearOptimizerApp

        return GearOptimizerApp().run()
    except KeyboardInterrupt:
        return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metafinder")
    parser.add_argument("command", nargs="?", choices=("run",), default="run", help="Run optimizer.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return {"run": run}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
