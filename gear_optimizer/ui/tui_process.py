from __future__ import annotations

import os
import queue
import re
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.config import load_config
from gear_optimizer.data.database import get_best_loadouts, get_song_counters
from gear_optimizer.ui.progress_ipc import SharedProgress
from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg

_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    try:
        total = int(max(0.0, float(seconds)))
    except Exception:
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _truncate_ansi(text: str, *, max_len: int) -> str:
    if max_len <= 0:
        return ""
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    out: list[str] = []
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


def _normalize_song_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    try:
        return re.sub(r"\s*\(Run\s+\d+\s*/\s*\d+\)\s*$", "", text).strip()
    except Exception:
        return text


def _color(text: str, code: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m"


@dataclass
class _UiState:
    epoch: int = -1
    start_perf: float = 0.0
    spinner: tuple[str, ...] = ("|", "/", "-", "\\")
    frame: int = 0


def _emit_block(stream, lines: list[str]) -> None:
    try:
        stream.write("\r\x1b[K\n")
        for line in lines:
            stream.write(str(line) + "\n")
        stream.flush()
    except Exception:
        pass


def _render_progress_line(
    stream,
    ui: _UiState,
    *,
    completed: int,
    total: int,
    failed: int,
    new_records: int,
    song: str,
    status: str,
    bar_width: int,
) -> None:
    now = time.perf_counter()
    elapsed = max(0.0, float(now - ui.start_perf))
    eta_s = None
    if completed > 0 and total > 0 and completed <= total:
        avg = float(elapsed) / float(completed)
        eta_s = max(0.0, float(total - completed) * avg)

    spinner = ui.spinner[ui.frame % len(ui.spinner)]
    ui.frame = (ui.frame + 1) % len(ui.spinner)
    pct = (float(completed) / float(total) * 100.0) if total > 0 else 0.0
    filled = int(round((float(completed) / float(total)) * int(bar_width))) if total > 0 else 0
    filled = max(0, min(int(bar_width), int(filled)))
    bar = "=" * filled + "-" * (int(bar_width) - filled)

    eta_str = _format_duration(eta_s) if eta_s is not None else "--:--"
    elapsed_str = _format_duration(elapsed)

    tail = ""
    song = str(song or "").strip()
    status = str(status or "").strip()
    status_clean = status
    if status_clean.upper() == "DONE":
        status_clean = ""
    if song:
        tail += f" | Song: {song}"
    if status_clean:
        tail += f" | {status_clean}"
    if len(tail) > 60:
        tail = tail[:57] + "..."

    spinner_s = _color(spinner, "36")
    bar_s = _color(bar, "96")
    pct_s = _color(f"{pct:5.1f}%", "92" if pct >= 99.9 else "36")
    new_s = _color(str(int(new_records)), "92")
    failed_s = _color(str(int(failed)), "91")
    line = (
        f"{spinner_s} [{bar_s}] {int(completed)}/{int(total)} {pct_s} "
        f"| ETA {eta_str} | Elapsed {elapsed_str} | New: {new_s} | Failed: {failed_s}{tail}"
    )

    try:
        term_width = int(shutil.get_terminal_size(fallback=(0, 0)).columns or 0)
    except Exception:
        term_width = 0
    if term_width > 0:
        line = _truncate_ansi(line, max_len=max(1, int(term_width) - 1))
    try:
        stream.write("\r" + line + "\x1b[K")
        stream.flush()
    except Exception:
        pass


def _hotkey_help() -> list[str]:
    return [
        "\x1b[96mRoBeats MetaFinder Hotkeys\x1b[0m",
        "  n  show next 10 songs in queue",
        "  d  show best loadout from DB for current song",
        "  c  show DB counters/best scores for current song",
        "  q  request graceful stop",
    ]


def _db_best_block(song_label: str) -> list[str]:
    label = _normalize_song_label(song_label)
    if not label:
        return ["\x1b[91m[DB]\x1b[0m No current song yet."]
    try:
        baseline_team_buff = resolve_baseline_team_buff_from_cfg(load_config(), default="T5")
        rows = get_best_loadouts(
            label,
            limit=3,
            gears_by_name=None,
            minis_by_name=None,
            team_buff=baseline_team_buff,
        )
    except Exception as exc:
        return [f"\x1b[91m[DB]\x1b[0m Error: {type(exc).__name__}: {exc}"]
    if not rows:
        return [f"\x1b[90m[DB]\x1b[0m No loadouts found for \x1b[93m{label}\x1b[0m"]
    best = rows[0]
    gear = best.get("gear") or []
    minis = best.get("minis") or []
    score = best.get("score", 0)
    fg_score = best.get("fg_score", 0)
    out = [
        f"\x1b[96mDB Best Loadout\x1b[0m \x1b[93m{label}\x1b[0m",
        f"  score:    \x1b[92m{score}\x1b[0m",
        f"  fg_score: \x1b[92m{fg_score}\x1b[0m",
        "  gear:",
    ]
    for g in gear:
        out.append(f"    - {g}")
    out.append("  minis:")
    for m in minis:
        out.append(f"    - {m}")
    return out


def _db_counters_block(song_label: str) -> list[str]:
    label = _normalize_song_label(song_label)
    if not label:
        return ["\x1b[91m[DB]\x1b[0m No current song yet."]
    try:
        a, af, bs, bfg = get_song_counters(label)
    except Exception as exc:
        return [f"\x1b[91m[DB]\x1b[0m Error: {type(exc).__name__}: {exc}"]
    return [
        f"\x1b[96mDB Counters\x1b[0m \x1b[93m{label}\x1b[0m",
        f"  attempts_lifetime: {a}",
        f"  attempts_first:    {af}",
        f"  best_score:        {bs}",
        f"  best_fg_score:     {bfg}",
    ]


def run_tui_process(
    *,
    progress_shm_name: str,
    stop_event,
    cmd_queue,
    resp_queue,
    bar_width: int,
    update_interval: float,
) -> None:
    stream = getattr(sys, "__stdout__", None) or sys.stdout
    ui = _UiState(epoch=-1, start_perf=time.perf_counter())
    progress = SharedProgress.attach(progress_shm_name)
    hotkeys_enabled = _truthy(os.environ.get("METAFINDER_HOTKEYS", "1"))

    # Windows-only hotkeys.
    msvcrt = None
    if hotkeys_enabled and os.name == "nt":
        try:
            import msvcrt as _msvcrt

            msvcrt = _msvcrt
        except Exception:
            msvcrt = None

    _emit_block(stream, ["\x1b[90m[Hotkeys]\x1b[0m n=next 10  d=db best  c=db counters  ?=help  q=stop"])
    last_render = 0.0
    try:
        while True:
            if stop_event is not None and bool(getattr(stop_event, "is_set", None)) and stop_event.is_set():
                return

            # Drain responses (blocks printed by compute).
            try:
                while True:
                    msg = resp_queue.get_nowait()
                    if isinstance(msg, dict) and isinstance(msg.get("lines"), list):
                        _emit_block(stream, [str(x) for x in msg.get("lines")])
            except queue.Empty:
                pass
            except Exception:
                pass

            # Hotkeys.
            if msvcrt is not None:
                try:
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        key = str(ch).strip().lower()
                        if key == "q":
                            try:
                                cmd_queue.put_nowait({"cmd": "stop", "reason": "hotkey"})
                            except Exception:
                                pass
                        elif key in {"?", "h"}:
                            _emit_block(stream, _hotkey_help())
                        elif key == "n":
                            try:
                                cmd_queue.put_nowait({"cmd": "next", "n": 10})
                            except Exception:
                                pass
                        elif key == "d":
                            snap = progress.read()
                            _emit_block(stream, _db_best_block(snap.song))
                        elif key == "c":
                            snap = progress.read()
                            _emit_block(stream, _db_counters_block(snap.song))
                except Exception:
                    pass

            # Progress render (cadence-limited).
            now = time.monotonic()
            if (now - last_render) >= float(update_interval):
                snap = progress.read()
                if int(snap.epoch) != int(ui.epoch):
                    ui.epoch = int(snap.epoch)
                    ui.start_perf = time.perf_counter()
                    ui.frame = 0
                _render_progress_line(
                    stream,
                    ui,
                    completed=int(snap.completed),
                    total=int(snap.total),
                    failed=int(snap.failed),
                    new_records=int(snap.new_records),
                    song=str(snap.song),
                    status=str(snap.status),
                    bar_width=int(bar_width),
                )
                last_render = now

            time.sleep(0.02)
    finally:
        try:
            progress.close()
        except Exception:
            pass
