"""Process logging: warnings and errors to <bin>/error.log, and messages to stderr."""

from __future__ import annotations

import logging
import sys

from gear_optimizer import settings


def configure_default_logging() -> None:
    """Install the engine's logging on the root logger of this process.

    Every process entry point calls it (CLI, app, service worker, spawned post-processor), so fail-loud
    errors are recorded in <bin>/error.log even when the console is quiet. A root logger that an embedding
    application or test runner already configured is left alone.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    log_file = settings.paths().bin_path("error.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO if settings.output_enabled() else logging.ERROR)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(file_handler)
    root.addHandler(console)
    root.setLevel(min(file_handler.level, console.level))
