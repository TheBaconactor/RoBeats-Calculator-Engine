"""
Console output helpers.

Provides a lightweight stdout suppressor used for quiet CLI mode.
"""

from __future__ import annotations

import os
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
        # Some stdlib code (notably `multiprocessing` spawn) may attempt to inherit
        # stdio file descriptors via `fileno()`. Returning an invalid FD (like -1)
        # can crash process creation with "bad value(s) in fds_to_keep)". Mirror
        # `io.IOBase.fileno()` behavior for non-FD streams by raising instead.
        raise OSError("NullWriter has no file descriptor")

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


def suppress_native_stdio(suppress: bool) -> tuple[int | None, int | None]:
    """
    Best-effort OS-level stdout/stderr suppression (C/C++ prints).

    Some native libraries (notably Taichi) write directly to the OS-level stdout/stderr
    file descriptors, bypassing Python's `sys.stdout`/`sys.stderr`. Swapping the Python
    objects alone (NullWriter) does not silence those messages.

    This function redirects file descriptors 1 and 2 to `os.devnull` and returns
    duplicates of the original fds for restoration via `restore_native_stdio()`.

    Notes:
    - Works on Windows (NUL) and POSIX.
    - Best-effort and never raises (optimizer must not crash due to logging helpers).
    """
    if not suppress:
        return (None, None)

    try:
        sys.stdout.flush()
    except OSError:
        pass
    try:
        sys.stderr.flush()
    except OSError:
        pass

    saved_out: int | None = None
    saved_err: int | None = None
    try:
        saved_out = os.dup(1)
    except OSError:
        saved_out = None
    try:
        saved_err = os.dup(2)
    except OSError:
        saved_err = None

    try:
        with open(os.devnull, "w") as devnull:
            try:
                os.dup2(devnull.fileno(), 1)
            except OSError:
                pass
            try:
                os.dup2(devnull.fileno(), 2)
            except OSError:
                pass
    except OSError:
        # If we failed to redirect, close any saved fds so we don't leak.
        if saved_out is not None:
            try:
                os.close(saved_out)
            except OSError:
                pass
            saved_out = None
        if saved_err is not None:
            try:
                os.close(saved_err)
            except OSError:
                pass
            saved_err = None

    return (saved_out, saved_err)


def restore_native_stdio(saved: tuple[int | None, int | None] | None) -> None:
    """Restore OS-level stdout/stderr from a guard returned by `suppress_native_stdio()`."""
    if not saved:
        return
    saved_out, saved_err = saved

    try:
        sys.stdout.flush()
    except OSError:
        pass
    try:
        sys.stderr.flush()
    except OSError:
        pass

    if saved_out is not None:
        try:
            os.dup2(saved_out, 1)
        except OSError:
            pass
        try:
            os.close(saved_out)
        except OSError:
            pass
    if saved_err is not None:
        try:
            os.dup2(saved_err, 2)
        except OSError:
            pass
        try:
            os.close(saved_err)
        except OSError:
            pass
