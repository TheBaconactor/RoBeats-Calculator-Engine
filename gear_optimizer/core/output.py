"""Console output suppression, at the Python level (sys.stdout/sys.stderr) and the OS level (file descriptors 1/2)."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Iterator


class NullWriter:
    """A stream that discards everything written to it."""

    def write(self, data) -> int:
        return len(data)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        # multiprocessing's spawn inherits stdio through fileno(); a made-up descriptor (-1) breaks process
        # creation ("bad value(s) in fds_to_keep"), so behave like io.IOBase does for a stream without one.
        raise OSError("NullWriter has no file descriptor")

    def reconfigure(self, **_kwargs) -> None:
        return None


def suppress_stdout(suppress: bool) -> object | None:
    """Replace sys.stdout with a NullWriter; returns the previous stream (None when not suppressing)."""
    if not suppress:
        return None
    old, sys.stdout = sys.stdout, NullWriter()
    return old


def suppress_stderr(suppress: bool) -> object | None:
    """Replace sys.stderr with a NullWriter; returns the previous stream (None when not suppressing)."""
    if not suppress:
        return None
    old, sys.stderr = sys.stderr, NullWriter()
    return old


def restore_stdout(old_stdout: object | None) -> None:
    if old_stdout is not None:
        sys.stdout = old_stdout


def restore_stderr(old_stderr: object | None) -> None:
    if old_stderr is not None:
        sys.stderr = old_stderr


def _os_stdio(call, *args):
    """An OS-level stdio call; None when the OS refuses it (e.g. a spawned Windows child's invalid console handle)."""
    try:
        return call(*args)
    except OSError:
        return None


@contextmanager
def quiet_stdio(quiet: bool = True) -> Iterator[None]:
    """Silence stdout and stderr, including native libraries (Taichi) that write to descriptors 1/2 directly.

    Best effort at the OS level: a descriptor that cannot be duplicated or redirected stays as it is.
    """
    if not quiet:
        yield
        return
    old_stdout, old_stderr = suppress_stdout(True), suppress_stderr(True)
    devnull = _os_stdio(os.open, os.devnull, os.O_WRONLY)
    saved = (None, None) if devnull is None else (_os_stdio(os.dup, 1), _os_stdio(os.dup, 2))
    if devnull is not None:
        for fd in (1, 2):
            _os_stdio(os.dup2, devnull, fd)
        os.close(devnull)
    try:
        yield
    finally:
        for fd, original in zip((1, 2), saved):
            if original is not None:
                _os_stdio(os.dup2, original, fd)
                _os_stdio(os.close, original)
        restore_stderr(old_stderr)
        restore_stdout(old_stdout)
