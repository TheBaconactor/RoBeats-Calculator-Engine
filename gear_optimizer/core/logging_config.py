from __future__ import annotations

import logging
import os
import sys
import threading

_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False


def configure_logging(
    *,
    log_file_path: str,
    console_level: int,
    file_level: int = logging.WARNING,
) -> None:
    """
    Configure the root logger for this process.

    - Console: stderr, message-only formatting (keeps stdout clean for result printers).
    - File: WARNING+ to `bin/error.log` (or equivalent path).

    This is intentionally idempotent and best-effort: logging must never crash the optimizer.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        root = logging.getLogger()
        if root.handlers:
            # Respect any embedding app/test runner configuration.
            _CONFIGURED = True
            return

        handlers: list[logging.Handler] = []

        try:
            parent = os.path.dirname(str(log_file_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        except OSError:
            pass

        try:
            file_handler = logging.FileHandler(str(log_file_path), encoding="utf-8")
            file_handler.setLevel(int(file_level))
            file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            handlers.append(file_handler)
        except (OSError, ValueError):
            pass

        try:
            stream_handler = logging.StreamHandler(stream=sys.stderr)
            stream_handler.setLevel(int(console_level))
            stream_handler.setFormatter(logging.Formatter("%(message)s"))
            handlers.append(stream_handler)
        except (OSError, ValueError):
            pass

        for handler in handlers:
            try:
                root.addHandler(handler)
            except (OSError, ValueError):
                pass

        # Allow the lowest handler level through.
        min_level = logging.ERROR
        for handler in handlers:
            try:
                min_level = min(min_level, int(handler.level))
            except (OSError, ValueError):
                pass
        try:
            root.setLevel(int(min_level))
        except (OSError, ValueError):
            pass

        _CONFIGURED = True


def configure_default_logging() -> None:
    """
    Install the optimizer's canonical durable diagnostics logging.

    Single source of truth for the production log target (``bin/error.log``, WARNING+)
    and console level (INFO in output mode, ERROR otherwise). Called from every process
    entry point that must record fail-loud diagnostics: the CLI entry (before the heavy
    solver import chain can install a foreign root handler), ``GearOptimizerApp``, and the
    spawned post-processor child (which otherwise runs with an unconfigured root logger).

    The console-output flag is read live via ``env_flag`` rather than from the frozen
    ``ENV`` singleton: the CLI entry calls this before ``_apply_debug_profile_env`` /
    ``_apply_throughput_mode_env`` mutate ``os.environ``, and importing ``env_config`` here
    would freeze ``ENV`` prematurely and disable the config-driven debug/profile family.
    ``METAFINDER_OUTPUT`` / ``METAFINDER_VERBOSE`` are never touched by those helpers, so the
    live read matches ``ENV.output_enabled``.

    Idempotent and best-effort: logging must never crash the optimizer.
    """
    try:
        from gear_optimizer.core.constants import BIN_DIR
        from gear_optimizer.core.parsing import env_flag

        output_enabled = env_flag("METAFINDER_OUTPUT") or env_flag("METAFINDER_VERBOSE")
        console_level = logging.INFO if output_enabled else logging.ERROR
        configure_logging(
            log_file_path=os.path.join(BIN_DIR, "error.log"),
            console_level=console_level,
            file_level=logging.WARNING,
        )
    except Exception:
        # Never let logging setup abort a process entry point.
        pass
