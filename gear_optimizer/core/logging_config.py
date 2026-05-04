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
