"""
Console output helpers.

Provides a lightweight stdout suppressor used for quiet CLI mode.
"""

from __future__ import annotations

import sys


class NullWriter:
    """Best-effort no-op stream compatible with common stdout calls."""

    def write(self, data) -> int:
        return len(data)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return -1

    def reconfigure(self, **_kwargs) -> None:
        return None


def suppress_stdout(suppress: bool) -> object | None:
    """
    Replace sys.stdout with NullWriter when suppressing output.

    Returns the previous stdout if suppression is enabled, else None.
    """
    if not suppress:
        return None
    old = sys.stdout
    sys.stdout = NullWriter()
    return old


def suppress_stderr(suppress: bool) -> object | None:
    """
    Replace sys.stderr with NullWriter when suppressing output.

    Returns the previous stderr if suppression is enabled, else None.
    """
    if not suppress:
        return None
    old = sys.stderr
    sys.stderr = NullWriter()
    return old


def restore_stdout(old_stdout: object | None) -> None:
    """Restore sys.stdout to the provided stream (no-op if None)."""
    if old_stdout is None:
        return
    sys.stdout = old_stdout


def restore_stderr(old_stderr: object | None) -> None:
    """Restore sys.stderr to the provided stream (no-op if None)."""
    if old_stderr is None:
        return
    sys.stderr = old_stderr
