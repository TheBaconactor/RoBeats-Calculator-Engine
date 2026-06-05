from __future__ import annotations

import re
import shutil
import sys
import threading
import time
import logging

from gear_optimizer.core.parsing import truthy


logger = logging.getLogger(__name__)
__all__ = [
    "ProgressUI",
    "_banner_enabled_default",
    "_progress_ui_enabled_default",
    "_stream_is_tty",
]


class ProgressUI:
    """Lightweight single-line progress renderer with spinner + ETA."""

    def __init__(
        self,
        total: int,
        *,
        completed: int = 0,
        failed: int = 0,
        new_records: int = 0,
        enabled: bool = True,
        bar_width: int = 24,
        update_interval: float = 0.2,
        stream=None,
    ) -> None:
        self._enabled = bool(enabled)
        self._total = max(0, int(total or 0))
        self._completed = max(0, int(completed or 0))
        self._failed = max(0, int(failed or 0))
        self._new_records = max(0, int(new_records or 0))
        self._bar_width = max(10, int(bar_width or 24))
        self._interval = max(0.05, float(update_interval or 0.2))
        self._stream = stream or getattr(sys, "__stdout__", None) or sys.stdout
        self._start = time.perf_counter()
        self._status = ""
        self._song = ""
        self._spinner = ["|", "/", "-", "\\"]
        self._frame = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self._enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ProgressUI", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop.set()
        if self._thread is not None:
            try:
                self._thread.join(timeout=2.0)
            except Exception as e:
                logger.debug(f"progress:stop: {e}")
        self._render(final=True)

    def update_counts(
        self, *, completed: int | None = None, total: int | None = None, failed: int | None = None
    ) -> None:
        if not self._enabled:
            return
        with self._lock:
            if completed is not None:
                self._completed = max(0, int(completed))
            if total is not None:
                self._total = max(0, int(total))
            if failed is not None:
                self._failed = max(0, int(failed))
        self._render()

    def add_new_record(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._new_records = max(0, int(self._new_records + int(count)))
        self._render()

    def add_completed(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._completed = max(0, int(self._completed + int(count)))
        self._render()

    def add_failed(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._failed = max(0, int(self._failed + int(count)))
        self._render()

    def set_status(self, song: str | None, status: str | None) -> None:
        if not self._enabled:
            return
        with self._lock:
            if song is not None:
                self._song = str(song)
            if status is not None:
                self._status = str(status)
        self._render()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._render()
            self._stop.wait(self._interval)

    def _render(self, *, final: bool = False) -> None:
        if not self._enabled:
            return
        try:
            now = time.perf_counter()
            with self._lock:
                completed = int(self._completed)
                total = int(self._total)
                failed = int(self._failed)
                new_records = int(self._new_records)
                status = str(self._status or "")
                status_clean = status.strip()
                if status_clean.upper() == "DONE":
                    status_clean = ""
                song = str(self._song or "")
                frame = self._frame
                self._frame = (self._frame + 1) % len(self._spinner)
            elapsed = max(0.0, float(now - self._start))
            eta_s = None
            if completed > 0 and total > 0 and completed <= total:
                avg = float(elapsed) / float(completed)
                eta_s = max(0.0, float(total - completed) * avg)

            spinner = self._spinner[frame % len(self._spinner)]
            pct = (float(completed) / float(total) * 100.0) if total > 0 else 0.0
            filled = int(round((float(completed) / float(total)) * self._bar_width)) if total > 0 else 0
            filled = max(0, min(self._bar_width, filled))
            bar = "=" * filled + "-" * (self._bar_width - filled)

            eta_str = self._format_duration(eta_s) if eta_s is not None else "--:--"
            elapsed_str = self._format_duration(elapsed)

            tail = ""
            if song:
                tail += f" | Song: {song}"
            if status_clean:
                tail += f" | {status_clean}"
            if len(tail) > 60:
                tail = tail[:57] + "..."

            def c(text: str, code: str) -> str:
                return f"\x1b[{code}m{text}\x1b[0m"

            spinner_s = c(spinner, "36")
            bar_s = c(bar, "96")
            pct_s = c(f"{pct:5.1f}%", "92" if pct >= 99.9 else "36")
            new_s = c(str(new_records), "92")
            failed_s = c(str(failed), "91")
            line = (
                f"{spinner_s} [{bar_s}] {completed}/{total} {pct_s} "
                f"| ETA {eta_str} | Elapsed {elapsed_str} | New: {new_s} | Failed: {failed_s}{tail}"
            )
            self._write(line, final=final)
        except Exception as e:
            logger.debug(f"progress:c: {e}")

    def _write(self, line: str, *, final: bool = False) -> None:
        if not self._enabled or self._stream is None:
            return
        try:
            term_width = 0
            try:
                term_width = int(shutil.get_terminal_size(fallback=(0, 0)).columns or 0)
            except Exception as e:
                logger.debug(f"progress:_write: {e}")
                term_width = 0
            if term_width > 0:
                line = self._truncate_ansi(line, max_len=max(1, term_width - 1))
            self._stream.write("\r" + line + "\x1b[K")
            if final:
                self._stream.write("\n")
            self._stream.flush()
        except Exception as e:
            logger.debug(f"progress:_write: {e}")

    @staticmethod
    def _truncate_ansi(text: str, *, max_len: int) -> str:
        if max_len <= 0:
            return ""
        ansi_re = re.compile(r"\x1b\[[0-9;]*m")
        out = []
        visible = 0
        i = 0
        n = len(text)
        while i < n and visible < max_len:
            if text[i] == "\x1b":
                m = ansi_re.match(text, i)
                if m:
                    out.append(m.group(0))
                    i = m.end()
                    continue
            out.append(text[i])
            visible += 1
            i += 1
        out.append("\x1b[0m")
        return "".join(out)

    @staticmethod
    def _format_duration(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        try:
            total = int(max(0.0, float(seconds)))
        except Exception as e:
            logger.debug(f"progress:_format_duration: {e}")
            total = 0
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def _stream_is_tty(stream) -> bool:
    try:
        isatty = getattr(stream, "isatty", None)
        if callable(isatty):
            return bool(isatty())
    except Exception as e:
        logger.debug(f"progress:_stream_is_tty: {e}")
        return False
    return False


def _progress_ui_enabled_default(
    *,
    configured_enabled: bool,
    output_enabled: bool,
    progress_env_present: bool,
    stream_is_tty: bool,
) -> bool:
    if not bool(configured_enabled):
        return False
    if bool(output_enabled) and not bool(progress_env_present):
        return False
    if (not bool(progress_env_present)) and (not bool(stream_is_tty)):
        return False
    return True


def _banner_enabled_default(*, stream_is_tty: bool, banner_env: str | None) -> bool:
    raw = str(banner_env or "").strip().lower()
    if not raw:
        return bool(stream_is_tty)
    return truthy(raw)
