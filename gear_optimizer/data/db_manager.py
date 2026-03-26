from __future__ import annotations

"""
DB Manager (Centralized DB API)

This module provides a single, documented entry point for common SQLite operations used by
the optimizer, tools, and (optionally) a website/backend exporter.

Design goals:
- Keep DB path selection centralized (default `evolution.db`, override via `EVOLUTION_DB_PATH`).
- Make call sites explicit about which DB file they are reading/writing.
- Avoid scattering direct `sqlite3.connect(...)` usage across the codebase.

Typical usage:

    from gear_optimizer.data.db_manager import EvolutionDbManager

    db = EvolutionDbManager.from_env()
    db.init_schema()

    # Persist baseline tier rows (usually T5)
    db.save_baseline_loadouts(song_key, entries, team_buff="T5")

    # Read baseline candidates (union of base + FG rows)
    rows = db.get_best_loadouts(song_key, limit=51, team_buff="T5")
"""

import os
import sqlite3
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..core.types import PersistenceEntry
from .database import (
    get_db_connection_with_timeout,
    get_db_connection_readonly,
    get_evolution_db_path,
    get_evolution_overlay_db_path,
    get_best_loadouts,
    save_loadouts_batch,
    save_team_buff_loadouts_batch,
    update_song_counters,
)


def _int_env(name: str, default: int) -> int:
    try:
        raw = str(os.environ.get(name, str(default)) or "").strip()
        v = int(raw) if raw else int(default)
    except Exception:
        v = int(default)
    return max(1, int(v))


_DB_MANAGER_EXECUTOR = ThreadPoolExecutor(max_workers=_int_env("DB_MANAGER_MAX_WORKERS", 1))


def _norm_leaderboard_key(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in {"base", "score"}:
        return "base"
    if s in {"fg", "force", "forcegreats"}:
        return "fg"
    return ""


_SONG_INDEX_LOCK = threading.Lock()
_SONG_INDEX_BY_DIFFICULTY: dict[str, dict[str, str]] = {}
_PATHS_CACHE: dict | None = None


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


def _load_paths_cache_dict() -> dict:
    global _PATHS_CACHE
    if isinstance(_PATHS_CACHE, dict) and _PATHS_CACHE:
        return _PATHS_CACHE
    from ..core.config import load_paths_cache

    out = load_paths_cache()
    _PATHS_CACHE = out if isinstance(out, dict) else {}
    return _PATHS_CACHE


def _build_song_index_for_difficulty(difficulty: str) -> dict[str, str]:
    from pathlib import Path

    from ..pipeline.song_processor import scan_song_header

    paths = _load_paths_cache_dict()
    root = str(paths.get(str(difficulty).strip().title(), "") or "").strip()
    if not root:
        return {}
    root_path = Path(root)
    if not root_path.exists():
        return {}

    out: dict[str, str] = {}
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not str(filename).lower().endswith(".txt"):
                continue
            fp = str(Path(dirpath) / filename)
            try:
                meta = scan_song_header(fp)
            except Exception:
                meta = None
            if not isinstance(meta, dict):
                continue
            name = str(meta.get("Song Name") or "").strip()
            if not name:
                continue
            out.setdefault(name, fp)
    return out


@dataclass(frozen=True, slots=True)
class EvolutionDbManager:
    """
    Centralized DB manager for the Evolution SQLite DB.

    Notes:
    - `db_path` is the canonical DB for the optimizer (default: `./evolution.db`).
    - `overlay_db_path` is optional and used by backend/service mode to mirror writes.
    """

    db_path: str
    overlay_db_path: Optional[str] = None

    @classmethod
    def from_env(cls, *, include_overlay: bool = False) -> "EvolutionDbManager":
        """
        Construct a manager using the repo's standard path resolution.

        - `EVOLUTION_DB_PATH` overrides the canonical DB path.
        - Overlay DB is opt-in:
          - Pass `include_overlay=True` to wire `overlay_db_path` from `get_evolution_overlay_db_path()`.
          - Otherwise, `overlay_db_path` is left unset (None).
        """
        overlay = str(get_evolution_overlay_db_path()) if bool(include_overlay) else None
        return cls(db_path=str(get_evolution_db_path()), overlay_db_path=overlay)

    def connect(self, *, timeout: float = 30.0) -> sqlite3.Connection:
        """Open a connection to `db_path` (ensures schema + WAL PRAGMAs)."""
        return get_db_connection_with_timeout(self.db_path, timeout=timeout)

    def connect_readonly(self, *, timeout: float = 0.0) -> sqlite3.Connection:
        """Open a read-only connection (never runs migrations/PRAGMAs)."""
        return get_db_connection_readonly(self.db_path, timeout=timeout)

    def connect_overlay(self, *, timeout: float = 30.0) -> sqlite3.Connection:
        """
        Open a connection to `overlay_db_path` if set; otherwise connects to `db_path`.
        """
        return get_db_connection_with_timeout(self.overlay_db_path or self.db_path, timeout=timeout)

    def init_schema(self) -> None:
        """Ensure migrations/schema exist for `db_path`."""
        conn = self.connect()
        try:
            conn.commit()
        finally:
            conn.close()

    # ---------------------------------------------------------------------
    # Queueing (on-demand compute)
    # ---------------------------------------------------------------------

    def submit(self, fn, /, *args, **kwargs) -> Future:
        """
        Submit a DB-manager task to the shared queue.

        Default executor is single-threaded (`DB_MANAGER_MAX_WORKERS=1`) so calls are
        naturally queued and won't spike CPU usage.
        """
        return _DB_MANAGER_EXECUTOR.submit(fn, *args, **kwargs)

    # ---------------------------------------------------------------------
    # Song discovery
    # ---------------------------------------------------------------------

    def resolve_song_file(self, song_name: str) -> Optional[str]:
        """
        Resolve a DB `song_name` to a chart file path using the repo's Data/ layout.

        Caches an index per difficulty (Easy/Normal/Hard) for fast repeat lookups.
        """
        song_name = str(song_name or "").strip()
        if not song_name:
            return None
        diff = _infer_difficulty_from_song_name(song_name)
        key = str(diff).strip().title()
        with _SONG_INDEX_LOCK:
            cached = _SONG_INDEX_BY_DIFFICULTY.get(key)
            if cached is None:
                cached = _build_song_index_for_difficulty(key)
                _SONG_INDEX_BY_DIFFICULTY[key] = cached
        return str(cached.get(song_name)) if cached.get(song_name) else None

    def get_song_catalog(
        self,
        *,
        team_buff: str = "T5",
        max_rank: int = 51,
        limit_songs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Return available songs + leaderboard availability for a baseline tier.

        Output shape (JSON-friendly):
            {
              "team_buff": "T5",
              "songs": [
                {"song_name": "...", "base_ranks": [1..], "fg_ranks": [1..]},
                ...
              ]
            }
        """
        team_buff = str(team_buff or "").strip().upper() or "T5"
        max_rank_i = max(1, int(max_rank))
        song_limit_i = int(limit_songs) if limit_songs is not None else None

        conn = self.connect_readonly()
        try:
            base_counts: dict[str, int] = {}
            fg_counts: dict[str, int] = {}
            try:
                rows = conn.execute(
                    "SELECT song_name, COUNT(*) AS cnt FROM team_buff_loadouts WHERE team_buff = ? GROUP BY song_name",
                    (team_buff,),
                ).fetchall()
                for r in rows or []:
                    if not r:
                        continue
                    base_counts[str(r[0])] = int(r[1] or 0)
            except sqlite3.Error:
                base_counts = {}

            try:
                rows = conn.execute(
                    "SELECT song_name, COUNT(*) AS cnt FROM team_buff_fg_loadouts WHERE team_buff = ? GROUP BY song_name",
                    (team_buff,),
                ).fetchall()
                for r in rows or []:
                    if not r:
                        continue
                    fg_counts[str(r[0])] = int(r[1] or 0)
            except sqlite3.Error:
                fg_counts = {}
        finally:
            conn.close()

        song_names = sorted(set(base_counts.keys()) | set(fg_counts.keys()))
        if song_limit_i is not None and song_limit_i > 0:
            song_names = song_names[:song_limit_i]

        songs: list[dict[str, Any]] = []
        for name in song_names:
            bc = int(base_counts.get(name, 0) or 0)
            fc = int(fg_counts.get(name, 0) or 0)
            songs.append(
                {
                    "song_name": name,
                    "base_ranks": list(range(1, min(max_rank_i, bc) + 1)) if bc > 0 else [],
                    "fg_ranks": list(range(1, min(max_rank_i, fc) + 1)) if fc > 0 else [],
                    "leaderboards": [k for k, c in (("base", bc), ("fg", fc)) if c > 0],
                }
            )

        return {"team_buff": team_buff, "songs": songs}

    # ---------------------------------------------------------------------
    # Leaderboard views (on-demand compute)
    # ---------------------------------------------------------------------

    def get_leaderboard_entry(
        self,
        song_name: str,
        *,
        leaderboard: str = "base",
        rank: int = 1,
        tier: str = "T5",
        limit: int = 51,
        element: str = "selected",
        team_color: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        View a single leaderboard entry by (song, tier, leaderboard, rank).

        This computes tier scores on demand from the persisted baseline candidates.
        """
        song_name = str(song_name or "").strip()
        if not song_name:
            return None
        lb = _norm_leaderboard_key(leaderboard)
        if not lb:
            return None
        tier = str(tier or "").strip().upper() or "T5"
        rank_i = max(1, int(rank))
        limit_i = max(1, int(limit))

        song_file = self.resolve_song_file(song_name)
        if not song_file:
            return None

        # Lazy imports keep this module lightweight.
        from ..core.config import load_config
        from ..core.utils import cfg_to_dict
        from ..app_async_db import _get_team_buff_ref_arrays_cached
        from ..core.team_buff import resolve_baseline_team_buff_from_cfg_dict
        from ..pipeline.song_processor import clone_calc_song, get_base_calc_song
        from ..helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

        cfg_dict = cfg_to_dict(load_config())
        ref_arrays = _get_team_buff_ref_arrays_cached()
        if ref_arrays is None:
            raise RuntimeError("ref_arrays unavailable (failed to load Stats lookup tables)")

        baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
        entries = self.get_best_loadouts(
            song_name, limit=limit_i, team_buff=str(baseline_team_buff), allow_fallback=True
        )

        base_calc_song = get_base_calc_song(str(song_file), cfg_dict)
        calc_song = clone_calc_song(base_calc_song)

        # Resolve element override into an explicit TeamColor target (optional).
        target_team_color_override = None
        if team_color:
            target_team_color_override = str(team_color)
        else:
            mode = str(element or "selected").strip().lower()
            meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
            p0 = str(meta0.get("Primary Color", "") or "").strip()
            s0 = str(meta0.get("Secondary Color", "") or "").strip()
            if mode == "primary" and p0:
                target_team_color_override = p0
            elif mode == "secondary":
                target_team_color_override = s0 or p0 or None

        batches = build_team_buff_tier_db_batches(
            entries=entries,
            calc_song=calc_song,
            ref_arrays=dict(ref_arrays),
            cfg_dict=dict(cfg_dict),
            limit=limit_i,
            tiers=(tier,),
            target_team_color_override=target_team_color_override,
        )
        rows = list(batches.get(tier) or [])
        if not rows:
            return None

        if lb == "fg":
            rows = [r for r in rows if int(r.get("fg_score", 0) or 0) > int(r.get("score", 0) or 0)]
            rows.sort(key=lambda r: int(r.get("fg_score", 0) or 0), reverse=True)
        else:
            rows.sort(key=lambda r: int(r.get("score", 0) or 0), reverse=True)

        if rank_i > len(rows):
            return None
        out = dict(rows[rank_i - 1])
        out.update({"song_name": song_name, "tier": tier, "leaderboard": lb, "rank": rank_i})
        return out

    def save_baseline_loadouts(
        self,
        song_name: str,
        entries: Sequence[PersistenceEntry],
        *,
        team_buff: str = "T5",
    ) -> None:
        """
        Persist baseline-tier leaderboards for a song into `team_buff_loadouts` and `team_buff_fg_loadouts`.

        This is the canonical write surface for the compact DB workflow.
        """
        save_loadouts_batch(str(song_name), list(entries), db_path=self.db_path, team_buff=str(team_buff))

    def save_team_buff_tier_loadouts(
        self,
        song_name: str,
        team_buff: str,
        entries: Sequence[Mapping[str, Any]],
        *,
        commit: bool = True,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """
        Persist already-scored rows for a specific TeamBuff tier key.

        This is mainly intended for optional tier materialization workflows.
        """
        save_team_buff_loadouts_batch(
            str(song_name),
            str(team_buff),
            entries,
            conn=conn,
            commit=commit,
            db_path=self.db_path,
        )

    def get_best_loadouts(
        self,
        song_name: str,
        *,
        limit: int = 51,
        team_buff: str = "T5",
        gears_by_name: Optional[Dict[str, Any]] = None,
        minis_by_name: Optional[Dict[str, Any]] = None,
        allow_fallback: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Read the top-N baseline candidates for a song (union of base + FG tables).
        """
        return get_best_loadouts(
            str(song_name),
            limit=int(limit),
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            team_buff=str(team_buff),
            allow_fallback=bool(allow_fallback),
            db_path=self.db_path,
        )

    def update_song_counters(
        self,
        song_name: str,
        *,
        processed_run: bool,
        record_improved: bool,
    ) -> None:
        """
        Update per-song attempt counters in `songs`.
        """
        update_song_counters(
            str(song_name),
            processed_run=bool(processed_run),
            record_improved=bool(record_improved),
            db_path=self.db_path,
        )

    def compute_team_buff_tier_leaderboards_on_demand(
        self,
        song_name: str,
        *,
        song_file: str,
        tiers: Sequence[str] = ("NONE", "T1", "T5", "T10", "T15"),
        limit: int = 51,
        element: str = "selected",
        team_color: Optional[str] = None,
        cfg_dict: Optional[Mapping[str, Any]] = None,
        ref_arrays: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute TeamBuff tier leaderboards from the persisted baseline candidates.

        Notes:
        - This does NOT require tier materialization in SQLite.
        - HumanHitSim runs are reproduced deterministically when persisted rows include
          the compact timing context (`details["hs"]`).

        Args:
            song_name: DB song key (songs.name / loadouts.song_name)
            song_file: Path to the song .txt used to parse chart timestamps
            tiers: Tier list to compute (default: NONE,T1,T5,T10,T15)
            limit: Top-N retained candidates (default: 51)
            element: TeamColor override mode: selected (default), primary, secondary
            team_color: Explicit TeamColor override; supersedes `element`
            cfg_dict: Optional config dict; defaults to repo config resolution
            ref_arrays: Optional ref_arrays table; defaults to cached Stats-derived lookup arrays
        """
        # Lazy imports to keep db_manager import-safe/lightweight.
        if cfg_dict is None:
            from ..core.config import load_config
            from ..core.utils import cfg_to_dict

            cfg_dict = cfg_to_dict(load_config())

        if ref_arrays is None:
            from ..app_async_db import _get_team_buff_ref_arrays_cached

            ref_arrays = _get_team_buff_ref_arrays_cached()
            if ref_arrays is None:
                raise RuntimeError("ref_arrays unavailable (failed to load Stats lookup tables)")

        from ..core.team_buff import resolve_baseline_team_buff_from_cfg_dict

        baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
        entries = self.get_best_loadouts(
            str(song_name),
            limit=int(limit),
            team_buff=str(baseline_team_buff),
            allow_fallback=True,
        )

        from ..pipeline.song_processor import clone_calc_song, get_base_calc_song
        from ..helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

        base_calc_song = get_base_calc_song(str(song_file), cfg_dict)
        calc_song = clone_calc_song(base_calc_song)

        # Resolve element override into an explicit TeamColor target (optional).
        target_team_color_override = None
        if team_color:
            target_team_color_override = str(team_color)
        else:
            mode = str(element or "selected").strip().lower()
            meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
            p0 = str(meta0.get("Primary Color", "") or "").strip()
            s0 = str(meta0.get("Secondary Color", "") or "").strip()
            if mode == "primary" and p0:
                target_team_color_override = p0
            elif mode == "secondary":
                target_team_color_override = s0 or p0 or None

        return compute_team_buff_tier_leaderboards(
            entries=entries,
            calc_song=calc_song,
            ref_arrays=dict(ref_arrays),
            cfg_dict=dict(cfg_dict) if isinstance(cfg_dict, dict) else dict(cfg_dict),
            limit=int(limit),
            tiers=tuple(str(t) for t in tiers),
            target_team_color_override=target_team_color_override,
        )
