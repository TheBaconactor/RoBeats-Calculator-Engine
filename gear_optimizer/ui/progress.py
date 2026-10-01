from __future__ import annotations

import re
import shutil
import threading
import time

__all__ = [
    "ProgressUI",
    "_progress_ui_enabled_default",
    "_stream_is_tty",
]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class ProgressUI:
    """Single-line progress bar redrawn by a background thread: spinner, counts, ETA, the current song."""

    _BAR_WIDTH = 24
    _INTERVAL_S = 0.2
    _SPINNER = ("|", "/", "-", "\\")

    def __init__(self, total: int, *, completed: int = 0, new_records: int = 0, stream) -> None:
        self._total = total
        self._completed = completed
        self._failed = 0
        self._new_records = new_records
        self._stream = stream
        self._start = time.perf_counter()
        self._status = ""
        self._song = ""
        self._frame = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ProgressUI", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._render(final=True)

    def update_counts(self, *, completed: int | None = None, total: int | None = None) -> None:
        with self._lock:
            if completed is not None:
                self._completed = max(0, completed)
            if total is not None:
                self._total = max(0, total)
        self._render()

    def add_new_record(self, count: int = 1) -> None:
        with self._lock:
            self._new_records = max(0, self._new_records + count)
        self._render()

    def add_completed(self, count: int = 1) -> None:
        with self._lock:
            self._completed = max(0, self._completed + count)
        self._render()

    def add_failed(self, count: int = 1) -> None:
        with self._lock:
            self._failed = max(0, self._failed + count)
        self._render()

    def set_status(self, song: str | None, status: str | None) -> None:
        with self._lock:
            if song is not None:
                self._song = song
            if status is not None:
                self._status = status
        self._render()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._render()
            self._stop.wait(self._INTERVAL_S)

    def _render(self, *, final: bool = False) -> None:
        now = time.perf_counter()
        with self._lock:
            completed, total, failed, new_records = self._completed, self._total, self._failed, self._new_records
            status = self._status.strip()
            if status.upper() == "DONE":
                status = ""
            song = self._song
            spinner = self._SPINNER[self._frame]
            self._frame = (self._frame + 1) % len(self._SPINNER)
        elapsed = max(0.0, now - self._start)
        eta = max(0.0, (total - completed) * (elapsed / completed)) if 0 < completed <= total else None
        pct = completed / total * 100.0 if total > 0 else 0.0
        filled = max(0, min(self._BAR_WIDTH, round(completed / total * self._BAR_WIDTH))) if total > 0 else 0
        bar = "=" * filled + "-" * (self._BAR_WIDTH - filled)

        tail = ""
        if song:
            tail += f" | Song: {song}"
        if status:
            tail += f" | {status}"
        if len(tail) > 60:
            tail = tail[:57] + "..."

        def c(text: str, code: str) -> str:
            return f"\x1b[{code}m{text}\x1b[0m"

        line = (
            f"{c(spinner, '36')} [{c(bar, '96')}] {completed}/{total} {c(f'{pct:5.1f}%', '92' if pct >= 99.9 else '36')} "
            f"| ETA {self._format_duration(eta)} | Elapsed {self._format_duration(elapsed)} "
            f"| New: {c(str(new_records), '92')} | Failed: {c(str(failed), '91')}{tail}"
        )
        term_width = shutil.get_terminal_size(fallback=(0, 0)).columns
        if term_width > 0:
            line = self._truncate_ansi(line, max_len=max(1, term_width - 1))
        self._stream.write("\r" + line + "\x1b[K")
        if final:
            self._stream.write("\n")
        self._stream.flush()

    @staticmethod
    def _truncate_ansi(text: str, *, max_len: int) -> str:
        """`text` cut to `max_len` visible characters (escape sequences kept), colors reset at the end."""
        out = []
        visible = 0
        i = 0
        while i < len(text) and visible < max_len:
            match = _ANSI_RE.match(text, i) if text[i] == "\x1b" else None
            if match:
                out.append(match.group(0))
                i = match.end()
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
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def _stream_is_tty(stream) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty()) if callable(isatty) else False


def _progress_ui_enabled_default(
    *,
    configured_enabled: bool,
    output_enabled: bool,
    progress_env_present: bool,
    stream_is_tty: bool,
) -> bool:
    """Not when switched off; forced on by METAFINDER_PROGRESS; otherwise only on a terminal without verbose output."""
    return configured_enabled and (progress_env_present or (not output_enabled and stream_is_tty))
