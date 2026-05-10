"""
skyline convergence trace writer (production, opt-in).

Writes one JSON object per sampled generation to a JSONL file. Tracing is best-effort:
file-system errors are swallowed so optimizer execution is never interrupted.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any
import logging

from gear_optimizer.core.parsing import truthy
from gear_optimizer.core.utils import safe_int as _safe_int


logger = logging.getLogger(__name__)
def _sanitize_name(value: str, *, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raw = str(fallback)
    out_chars: list[str] = []
    for ch in raw:
        if ch.isalnum() or ch in {"-", "_", "."}:
            out_chars.append(ch)
        elif ch in {" ", "/", "\\", ":"}:
            out_chars.append("_")
    out = "".join(out_chars).strip("._")
    return out or str(fallback)


def _metadata(calc_song: dict) -> dict:
    meta = calc_song.get("metadata", {})
    return meta if isinstance(meta, dict) else {}


def _song_name(calc_song: dict) -> str:
    return str(_metadata(calc_song).get("Song Name", "") or "").strip()


def _difficulty(calc_song: dict) -> str:
    return str(_metadata(calc_song).get("Difficulty", "") or "").strip()


def _trace_song_matches_filter(song_name: str, raw_filter: str) -> bool:
    token = str(raw_filter or "").strip()
    if not token:
        return True
    return token.lower() in str(song_name or "").lower()


@dataclass(frozen=True)
class ConvergenceTraceConfig:
    enabled: bool
    every: int
    out_dir: str
    song_filter: str

    @staticmethod
    def from_cfg_data(cfg_data: dict | None) -> "ConvergenceTraceConfig":
        cfg_data = cfg_data if isinstance(cfg_data, dict) else {}
        enabled = truthy(cfg_data.get("SKYLINE_convergence_trace_enabled", False))
        every = max(1, _safe_int(cfg_data.get("SKYLINE_convergence_trace_every", 1), 1))
        out_dir = str(cfg_data.get("SKYLINE_convergence_trace_out_dir", "artifacts/SKYLINE_trace") or "artifacts/SKYLINE_trace")
        song_filter = str(cfg_data.get("SKYLINE_convergence_trace_song_filter", "") or "")
        return ConvergenceTraceConfig(
            enabled=bool(enabled),
            every=int(every),
            out_dir=out_dir,
            song_filter=song_filter,
        )


class ConvergenceTraceWriter:
    def __init__(
        self,
        *,
        out_dir: str,
        song_name: str,
        difficulty: str,
        skyline_seed: int,
    ) -> None:
        self.song_name = str(song_name or "")
        self.difficulty = str(difficulty or "")
        self.skyline_seed = int(skyline_seed)
        self._lock = threading.Lock()
        self._file_path = self._build_path(out_dir=out_dir)

    def _build_path(self, *, out_dir: str) -> str | None:
        try:
            out_dir_norm = os.path.abspath(str(out_dir or "artifacts/SKYLINE_trace"))
            os.makedirs(out_dir_norm, exist_ok=True)
            song_slug = _sanitize_name(self.song_name, fallback="song")
            diff_slug = _sanitize_name(self.difficulty, fallback="diff")
            ts_ms = int(time.time() * 1000.0)
            pid = int(os.getpid())
            filename = f"{song_slug}__{diff_slug}__ga{int(self.skyline_seed)}__{ts_ms}__p{pid}.jsonl"
            return os.path.join(out_dir_norm, filename)
        except Exception as e:
            logger.debug(f"convergence_trace:_build_path: {e}")
            return None

    @property
    def file_path(self) -> str | None:
        return self._file_path

    def append(
        self,
        *,
        generation_idx: int,
        elapsed_s: float,
        best_score: int,
        best_results: Any | None = None,
        extra: dict | None = None,
    ) -> None:
        path = self._file_path
        if not path:
            return

        row: dict[str, Any] = {
            "song_name": self.song_name,
            "difficulty": self.difficulty,
            "skyline_seed": int(self.skyline_seed),
            "generation_idx": int(generation_idx),
            "elapsed_s": float(elapsed_s),
            "wall_time_unix_s": float(time.time()),
            "best_score": int(best_score),
        }
        if best_results is not None:
            try:
                vals = [int(x) for x in list(best_results)]
            except Exception as e:
                logger.debug(f"convergence_trace:append: {e}")
                vals = []
            if len(vals) >= 7:
                row["best_score"] = int(vals[0])
                row["best_ft"] = int(vals[1])
                row["best_ff"] = int(vals[2])
                row["best_pp"] = int(vals[3])
                row["best_cm"] = int(vals[4])
                row["best_fm"] = int(vals[5])
                row["best_ov"] = int(vals[6])
        if isinstance(extra, dict) and extra:
            row.update(extra)

        payload = json.dumps(row, separators=(",", ":"), ensure_ascii=True)
        try:
            with self._lock:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(payload)
                    fh.write("\n")
        except Exception as e:
            logger.debug(f"convergence_trace:append: {e}")
            return


def build_convergence_trace_writer(
    *,
    calc_song: dict,
    cfg_data: dict | None,
    skyline_seed: int | None,
) -> tuple[ConvergenceTraceWriter | None, int]:
    """
    Build a trace writer for a song/run when enabled by cfg_data.

    Returns:
        (writer_or_none, sample_every_generations)
    """
    cfg = ConvergenceTraceConfig.from_cfg_data(cfg_data)
    if not cfg.enabled:
        return None, int(cfg.every)

    song_name = _song_name(calc_song)
    if not _trace_song_matches_filter(song_name, cfg.song_filter):
        return None, int(cfg.every)

    writer = ConvergenceTraceWriter(
        out_dir=cfg.out_dir,
        song_name=song_name,
        difficulty=_difficulty(calc_song),
        skyline_seed=_safe_int(skyline_seed, 0),
    )
    if not writer.file_path:
        return None, int(cfg.every)
    return writer, int(cfg.every)
