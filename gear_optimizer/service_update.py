"""The service follows origin/main: a new commit is fast-forwarded into the checkout while no solve runs; new code
restarts the service, new Data only refreshes it."""

from __future__ import annotations

import logging
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

_REMOTE_REF = "refs/remotes/origin/main"
_POLL_SECONDS = 300
_GIT_TIMEOUT_SECONDS = 300


class ServiceUpdater:
    """`drain` stops new solves and waits for the running ones, `resume` takes that back, `restart` replaces the process
    with the new code, `refresh` makes the running service current with the checkout's Data. A song publish commits
    Data in this very checkout, so a revision is new against what the service runs, not against the checkout."""

    def __init__(
        self,
        repo_root: Path,
        *,
        drain: Callable[[], None],
        resume: Callable[[], None],
        restart: Callable[[str], None],
        refresh: Callable[[], None],
    ) -> None:
        self.repo_root, self.drain, self.resume, self.restart, self.refresh = repo_root, drain, resume, restart, refresh
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._running: str | None = None  # the revision this process started on
        self._refreshed: str | None = None  # the revision whose Data the service is current with

    def _git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo_root, check=True, capture_output=True, text=True,
                              timeout=_GIT_TIMEOUT_SECONDS).stdout.strip()

    def _fast_forward(self, commit: str) -> None:
        if self._git("status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError("refusing to update a checkout with tracked local changes")
        self._git("merge", "--ff-only", commit)

    def run_once(self) -> None:
        try:
            self._git("fetch", "--quiet", "origin", f"main:{_REMOTE_REF}")
        except (OSError, subprocess.SubprocessError):
            logger.warning("git fetch failed; using the last fetched ref", exc_info=True)
        head = self._git("rev-parse", "HEAD^{commit}")
        commit = self._git("rev-parse", f"{_REMOTE_REF}^{{commit}}")
        self._running = self._running or head
        if commit == self._refreshed:
            return
        new_code = bool(self._git("diff", "--name-only", self._running, commit, "--", ".", ":(exclude)Data/**",
                                  ":(exclude)config.ini"))
        if commit != head or new_code:
            self.drain()
            try:
                if commit != head:
                    self._fast_forward(commit)
            except Exception:
                self.resume()
                raise
            if new_code:
                logger.info("restarting into revision %s", commit)
                self.stop()
                self.restart(commit)
                return
            self.resume()
        self.refresh()
        self._refreshed = commit

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("service update failed; the running revision stays")
            self._wake.wait(_POLL_SECONDS)
            self._wake.clear()

    def request_check(self) -> None:
        """Look for a new revision now, on the updater's thread."""
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
