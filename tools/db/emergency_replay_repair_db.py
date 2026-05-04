"""
Emergency replay repair for Evolution DB score/detail contracts.

This is intentionally stricter than ordinary backfills:
- `team_buff_loadouts.details_json` must replay `team_buff_loadouts.score`.
- `team_buff_fg_loadouts.details_json` must replay `team_buff_fg_loadouts.score`.
- `team_buff_fg_loadouts.force_details_json` must replay `team_buff_fg_loadouts.fg_score`.
- songs whose chart or replay payload cannot be proven are deleted for re-evaluation.

Usage:
  python tools/db/emergency_replay_repair_db.py --db evolution.db --write
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from gear_optimizer.core.utils import safe_int as _safe_int
from gear_optimizer.data.migrations import _table_exists


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


def _resolve_song_file(project_root: Path, song_name: str) -> Path | None:
    song_name = str(song_name or "").strip()
    if not song_name:
        return None
    inferred = _infer_difficulty_from_song_name(song_name)
    diffs = [inferred] + [d for d in ("Easy", "Normal", "Hard") if d != inferred]
    for diff in diffs:
        fp = project_root / "Data" / diff / f"{song_name}.txt"
        if fp.exists():
            return fp
    for diff in diffs:
        root = project_root / "Data" / diff
        if not root.exists():
            continue
        match = _build_song_header_index(root).get(song_name)
        if match:
            return match
    return None


_SONG_HEADER_INDEX_CACHE: dict[Path, dict[str, Path]] = {}


def _build_song_header_index(root: Path) -> dict[str, Path]:
    root = Path(root).resolve()
    cached = _SONG_HEADER_INDEX_CACHE.get(root)
    if cached is not None:
        return cached

    from gear_optimizer.pipeline.song_processor import scan_song_header

    out: dict[str, Path] = {}
    for fp in root.rglob("*.txt"):
        try:
            meta = scan_song_header(str(fp))
        except Exception:
            meta = None
        if not isinstance(meta, dict):
            continue
        name = str(meta.get("Song Name") or "").strip()
        if name:
            out.setdefault(name, fp)
    _SONG_HEADER_INDEX_CACHE[root] = out
    return out

def _forced_counts_from_payload(force_payload: dict[str, Any]) -> list[int]:
    raw = force_payload.get("forced_counts")
    if isinstance(raw, list):
        return [_safe_int(v, 0) for v in raw]

    fg = force_payload.get("ForceGreats")
    if not isinstance(fg, dict):
        nested = force_payload.get("details")
        if isinstance(nested, dict):
            fg = nested.get("ForceGreats")
    cfg = (fg or {}).get("config") if isinstance(fg, dict) else None
    if not isinstance(cfg, dict):
        return []

    pairs: list[tuple[int, int]] = []
    for key, value in cfg.items():
        k = str(key or "")
        if not k.lower().startswith("nonfever"):
            continue
        idx_txt = k[len("NonFever") :]
        try:
            idx = int(idx_txt)
        except Exception:
            continue
        if idx > 0:
            pairs.append((idx, _safe_int(value, 0)))
    if not pairs:
        return []
    max_idx = max(i for i, _ in pairs)
    out = [0] * max_idx
    for idx, value in pairs:
        out[idx - 1] = int(value)
    return out


def _load_json(value: Any) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _score_fixed_stats(stats: dict[str, Any], calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> int:
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    return int(score_stats_exact(stats, calc_song, ref_arrays))


def _repair_db(db_path: Path, *, write: bool) -> dict[str, int]:
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import (
        _base_details_from_force_payload,
        _compact_force_details_for_storage,
        _json_dumps_compact,
        _pack_stats_for_storage,
        _strip_computed_details_fields,
        _unpack_stats_after_load,
    )
    from gear_optimizer.pipeline.song_processor import get_base_calc_song
    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise RuntimeError("reference arrays unavailable")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    calc_cache: dict[str, dict[str, Any] | None] = {}

    counts = {
        "songs_deleted": 0,
        "base_checked": 0,
        "base_updated": 0,
        "fg_checked": 0,
        "fg_updated": 0,
        "fg_deleted": 0,
        "songs_rescored": 0,
        "unguaranteed_songs": 0,
    }
    bad_songs: set[str] = set()
    base_changed_songs: set[str] = set()
    fg_changed_songs: set[str] = set()

    def calc_song_for(song_name: str) -> dict[str, Any] | None:
        if song_name in calc_cache:
            return calc_cache[song_name]
        fp = _resolve_song_file(PROJECT_ROOT, song_name)
        if fp is None:
            calc_cache[song_name] = None
            return None
        try:
            calc_song = get_base_calc_song(str(fp), cfg_dict)
        except Exception:
            calc_song = None
        calc_cache[song_name] = calc_song if isinstance(calc_song, dict) and calc_song else None
        return calc_cache[song_name]

    try:
        for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
            if not _table_exists(conn, table):
                continue

            if table == "team_buff_loadouts":
                rows = conn.execute("SELECT rowid, song_name, score, details_json FROM team_buff_loadouts").fetchall()
                for row in rows:
                    song_name = str(row["song_name"] or "").strip()
                    calc_song = calc_song_for(song_name)
                    if calc_song is None:
                        bad_songs.add(song_name)
                        continue
                    details = _unpack_stats_after_load(_load_json(row["details_json"])) or {}
                    stats = details.get("Stats") if isinstance(details, dict) else None
                    if not isinstance(stats, dict) or not stats:
                        bad_songs.add(song_name)
                        continue
                    replay_score = _score_fixed_stats(stats, calc_song, ref_arrays)
                    counts["base_checked"] += 1
                    if replay_score != _safe_int(row["score"], 0):
                        counts["base_updated"] += 1
                        base_changed_songs.add(song_name)
                        if write:
                            conn.execute(
                                "UPDATE team_buff_loadouts SET score=?, timestamp=strftime('%s','now') WHERE rowid=?",
                                (int(replay_score), int(row["rowid"])),
                            )
                continue

            rows = conn.execute(
                """
                SELECT rowid, song_name, score, fg_score, details_json, force_details_json
                FROM team_buff_fg_loadouts
                """
            ).fetchall()
            for row in rows:
                song_name = str(row["song_name"] or "").strip()
                calc_song = calc_song_for(song_name)
                if calc_song is None:
                    bad_songs.add(song_name)
                    continue

                details = _unpack_stats_after_load(_load_json(row["details_json"])) or {}
                force_payload = _load_json(row["force_details_json"])
                if not isinstance(force_payload, dict) or not force_payload:
                    bad_songs.add(song_name)
                    continue

                fg_details = _base_details_from_force_payload(details, force_payload)
                stats = fg_details.get("Stats") if isinstance(fg_details, dict) else None
                if not isinstance(stats, dict) or not stats:
                    bad_songs.add(song_name)
                    continue

                replay_base = _score_fixed_stats(stats, calc_song, ref_arrays)
                fg_replay = evaluate_force_greats_exact(
                    stats, calc_song, ref_arrays, _forced_counts_from_payload(force_payload)
                )
                if not isinstance(fg_replay, dict) or "final_score" not in fg_replay:
                    bad_songs.add(song_name)
                    continue
                replay_fg = int(fg_replay.get("final_score", 0) or 0)
                counts["fg_checked"] += 1

                if replay_fg <= replay_base:
                    counts["fg_deleted"] += 1
                    fg_changed_songs.add(song_name)
                    if write:
                        conn.execute("DELETE FROM team_buff_fg_loadouts WHERE rowid=?", (int(row["rowid"]),))
                    continue

                force_out = dict(force_payload)
                force_out["BaseScore"] = int(replay_base)
                force_out["Score"] = int(replay_fg)
                fg_meta = dict(force_out.get("ForceGreats") or {})
                fg_meta["final_score"] = int(replay_fg)
                if fg_replay.get("config_dict"):
                    fg_meta["config"] = dict(fg_replay.get("config_dict") or {})
                force_out["ForceGreats"] = fg_meta
                if fg_replay.get("config_counts") is not None:
                    force_out["forced_counts"] = [int(v) for v in (fg_replay.get("config_counts") or [])]

                fg_details["BaseScore"] = int(replay_base)
                details_json = _json_dumps_compact(_pack_stats_for_storage(_strip_computed_details_fields(fg_details)))
                force_json = _json_dumps_compact(_compact_force_details_for_storage(force_out))

                old_base = _safe_int(row["score"], 0)
                old_fg = _safe_int(row["fg_score"], 0)
                old_details = row["details_json"] or ""
                old_force = row["force_details_json"] or ""
                if (
                    replay_base != old_base
                    or replay_fg != old_fg
                    or details_json != old_details
                    or force_json != old_force
                ):
                    counts["fg_updated"] += 1
                    fg_changed_songs.add(song_name)
                    if write:
                        conn.execute(
                            """
                            UPDATE team_buff_fg_loadouts
                            SET score=?, fg_score=?, details_json=?, force_details_json=?, timestamp=strftime('%s','now')
                            WHERE rowid=?
                            """,
                            (int(replay_base), int(replay_fg), details_json, force_json, int(row["rowid"])),
                        )

        bad_songs = {s for s in bad_songs if s}
        counts["unguaranteed_songs"] = len(bad_songs)
        counts["base_changed_songs"] = len(base_changed_songs)
        counts["fg_changed_songs"] = len(fg_changed_songs)
        counts["changed_songs"] = len(base_changed_songs | fg_changed_songs | bad_songs)
        if write and bad_songs:
            for table in ("pending_fg_jobs", "team_buff_fg_loadouts", "team_buff_loadouts"):
                if _table_exists(conn, table):
                    conn.executemany(f"DELETE FROM {table} WHERE song_name=?", [(s,) for s in bad_songs])
            conn.executemany("DELETE FROM songs WHERE name=?", [(s,) for s in bad_songs])
            counts["songs_deleted"] = len(bad_songs)

        if _table_exists(conn, "songs"):
            song_names = [
                str(r[0] or "")
                for r in conn.execute(
                    """
                    SELECT name FROM songs
                    UNION
                    SELECT song_name FROM team_buff_loadouts
                    UNION
                    SELECT song_name FROM team_buff_fg_loadouts
                    """
                ).fetchall()
                if str(r[0] or "")
            ]
            for song_name in song_names:
                if song_name in bad_songs:
                    continue
                best_row = (
                    conn.execute(
                        "SELECT MAX(score) FROM team_buff_loadouts WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5'",
                        (song_name,),
                    ).fetchone()
                    if _table_exists(conn, "team_buff_loadouts")
                    else None
                )
                best_fg_row = (
                    conn.execute(
                        "SELECT MAX(fg_score) FROM team_buff_fg_loadouts WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5'",
                        (song_name,),
                    ).fetchone()
                    if _table_exists(conn, "team_buff_fg_loadouts")
                    else None
                )
                best = _safe_int(best_row[0] if best_row else 0, 0)
                best_fg = _safe_int(best_fg_row[0] if best_fg_row else 0, 0)
                if best <= 0 and best_fg <= 0:
                    if write:
                        conn.execute("DELETE FROM songs WHERE name=?", (song_name,))
                    counts["songs_deleted"] += 1
                    continue
                counts["songs_rescored"] += 1
                if write:
                    conn.execute(
                        """
                        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
                        VALUES (?, ?, ?, strftime('%s','now'))
                        ON CONFLICT(name) DO UPDATE SET
                            best_score=excluded.best_score,
                            best_fg_score=excluded.best_fg_score,
                            last_updated=strftime('%s','now')
                        """,
                        (song_name, int(best), int(best_fg)),
                    )

        if write:
            conn.commit()
            conn.execute("VACUUM")

    finally:
        conn.close()

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Emergency replay repair for Evolution DBs.")
    parser.add_argument("--db", action="append", default=[], help="DB path. May be repeated.")
    parser.add_argument("--write", action="store_true", help="Write changes. Default is dry-run.")
    args = parser.parse_args()

    dbs = [Path(p).resolve() for p in (args.db or [])]
    if not dbs:
        dbs = [PROJECT_ROOT / "evolution.db", PROJECT_ROOT / "evolutionref.db", PROJECT_ROOT / "evolutionref2.db"]

    for db_path in dbs:
        if not db_path.exists():
            print(f"[skip] missing DB: {db_path}")
            continue
        counts = _repair_db(db_path, write=bool(args.write))
        mode = "WRITE" if args.write else "DRY-RUN"
        print(f"[{mode}] {db_path}")
        for key in sorted(counts):
            print(f"  {key}: {counts[key]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
