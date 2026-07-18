"""
Compare same-top-overall winner hashes across two DBs and replay both sides.

This diagnostic is focused on one question:
when both DBs picked the same top overall loadout hash for a song, do persisted
scores and replay-authoritative scores agree?
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _base_details_from_force_payload, _unpack_stats_after_load
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.fg_payload import require_response_surface
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact, score_stats_exact
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from tools.db.compare_overall_best_to_legacy_db import _song_file_from_name


@dataclass(frozen=True)
class Winner:
    song: str
    source: str
    loadout_hash: str
    persisted_score: int


@dataclass(frozen=True)
class ReplayResult:
    song: str
    source: str
    loadout_hash: str
    persisted_score: int
    replay_score: int
    has_stats: bool
    has_force_payload: bool
    reason: str


def _best_base(conn: sqlite3.Connection, *, song: str, team_buff: str) -> tuple[int, str]:
    if not _table_exists(conn, "team_buff_loadouts"):
        return 0, ""
    row = conn.execute(
        """
        SELECT score, loadout_hash
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?)
        ORDER BY score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (song, team_buff),
    ).fetchone()
    if row is None:
        return 0, ""
    return int(row[0] or 0), str(row[1] or "").strip()


def _best_fg(conn: sqlite3.Connection, *, song: str, team_buff: str) -> tuple[int, str]:
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return 0, ""
    row = conn.execute(
        """
        SELECT fg_score, loadout_hash
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?)
        ORDER BY fg_score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (song, team_buff),
    ).fetchone()
    if row is None:
        return 0, ""
    return int(row[0] or 0), str(row[1] or "").strip()


def _best_overall(conn: sqlite3.Connection, *, song: str, team_buff: str) -> Winner | None:
    base_score, base_hash = _best_base(conn, song=song, team_buff=team_buff)
    fg_score, fg_hash = _best_fg(conn, song=song, team_buff=team_buff)
    if fg_score > base_score and fg_hash:
        return Winner(song=song, source="fg", loadout_hash=fg_hash, persisted_score=int(fg_score))
    if base_hash:
        return Winner(song=song, source="base", loadout_hash=base_hash, persisted_score=int(base_score))
    return None


def _songs_in_db(conn: sqlite3.Connection, *, team_buff: str) -> set[str]:
    out: set[str] = set()
    if _table_exists(conn, "team_buff_loadouts"):
        rows = conn.execute(
            "SELECT DISTINCT song_name FROM team_buff_loadouts WHERE UPPER(COALESCE(team_buff,''))=UPPER(?)",
            (team_buff,),
        ).fetchall()
        out |= {str(r[0] or "") for r in rows}
    if _table_exists(conn, "team_buff_fg_loadouts"):
        rows = conn.execute(
            "SELECT DISTINCT song_name FROM team_buff_fg_loadouts WHERE UPPER(COALESCE(team_buff,''))=UPPER(?)",
            (team_buff,),
        ).fetchall()
        out |= {str(r[0] or "") for r in rows}
    out.discard("")
    return out


def _resolve_calc_song(
    *,
    song: str,
    cfg_dict: dict[str, Any],
    calc_song_cache: dict[str, dict | None],
) -> tuple[dict | None, str]:
    if song in calc_song_cache:
        calc_song = calc_song_cache[song]
        return calc_song, "ok" if isinstance(calc_song, dict) else "song_file_missing"

    fp = _song_file_from_name(PROJECT_ROOT, song)
    if fp is None:
        calc_song_cache[song] = None
        return None, "song_file_missing"

    try:
        calc_song = get_base_calc_song(str(fp), cfg_dict)
    except Exception:
        calc_song_cache[song] = None
        return None, "calc_song_load_error"

    if not isinstance(calc_song, dict) or not calc_song:
        calc_song_cache[song] = None
        return None, "calc_song_load_error"

    meta = calc_song.get("metadata") or {}
    if not isinstance(meta, dict):
        calc_song_cache[song] = calc_song
        return calc_song, "metadata_missing"

    primary = str(meta.get("Primary Color", "") or "").strip()
    secondary = str(meta.get("Secondary Color", "") or "").strip()
    calc_song_cache[song] = calc_song
    if not primary and not secondary:
        return calc_song, "metadata_missing"
    return calc_song, "ok"


def _replay_base(
    conn: sqlite3.Connection,
    *,
    winner: Winner,
    team_buff: str,
    ref_arrays: dict[str, Any] | None,
    cfg_dict: dict[str, Any],
    calc_song_cache: dict[str, dict | None],
) -> ReplayResult:
    row = conn.execute(
        """
        SELECT score, details_json, force_details_json
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?) AND loadout_hash=?
        """,
        (winner.song, team_buff, winner.loadout_hash),
    ).fetchone()
    if row is None:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=winner.persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=False,
            reason="row_missing",
        )

    details_blob = row[1]
    if not details_blob:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=False,
            has_force_payload=bool(row[2]),
            reason="details_missing",
        )

    try:
        details = json.loads(details_blob)
    except Exception:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=False,
            has_force_payload=bool(row[2]),
            reason="details_json_parse_error",
        )
    details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
    if not isinstance(details, dict):
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=False,
            has_force_payload=bool(row[2]),
            reason="details_not_object",
        )

    stats = details.get("Stats")
    has_stats = isinstance(stats, dict) and bool(stats)
    if not has_stats:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=False,
            has_force_payload=bool(row[2]),
            reason="stats_missing",
        )

    if not isinstance(ref_arrays, dict) or not ref_arrays:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=True,
            has_force_payload=bool(row[2]),
            reason="ref_arrays_missing",
        )

    calc_song, calc_reason = _resolve_calc_song(
        song=winner.song,
        cfg_dict=cfg_dict,
        calc_song_cache=calc_song_cache,
    )
    if not isinstance(calc_song, dict):
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=True,
            has_force_payload=bool(row[2]),
            reason=calc_reason,
        )

    try:
        replay_score = int(score_stats_exact(stats, calc_song, ref_arrays))
    except Exception:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=int(row[0] or 0),
            replay_score=0,
            has_stats=True,
            has_force_payload=bool(row[2]),
            reason="replay_error",
        )

    reason = "ok" if replay_score > 0 else "replay_zero"
    return ReplayResult(
        song=winner.song,
        source=winner.source,
        loadout_hash=winner.loadout_hash,
        persisted_score=int(row[0] or 0),
        replay_score=int(replay_score),
        has_stats=True,
        has_force_payload=bool(row[2]),
        reason=reason,
    )


def _replay_fg(
    conn: sqlite3.Connection,
    *,
    winner: Winner,
    team_buff: str,
    ref_arrays: dict[str, Any] | None,
    cfg_dict: dict[str, Any],
    calc_song_cache: dict[str, dict | None],
) -> ReplayResult:
    row = conn.execute(
        """
        SELECT fg_score, force_details_json, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?) AND loadout_hash=?
        """,
        (winner.song, team_buff, winner.loadout_hash),
    ).fetchone()
    if row is None:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=winner.persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=False,
            reason="fg_row_missing",
        )

    persisted_score = int(row[0] or 0)
    force_blob = row[1]
    details_blob = row[2]
    if not force_blob:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=False,
            reason="force_payload_missing",
        )

    try:
        force_details = json.loads(force_blob)
    except Exception:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=True,
            reason="force_json_parse_error",
        )
    if not isinstance(force_details, dict):
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=True,
            reason="force_not_object",
        )

    details: dict[str, Any] = {}
    if details_blob:
        try:
            details0 = json.loads(details_blob)
            details = _unpack_stats_after_load(details0) if isinstance(details0, dict) else {}
        except Exception:
            return ReplayResult(
                song=winner.song,
                source=winner.source,
                loadout_hash=winner.loadout_hash,
                persisted_score=persisted_score,
                replay_score=0,
                has_stats=False,
                has_force_payload=True,
                reason="details_json_parse_error",
            )

    fg_details = _base_details_from_force_payload(details, force_details)
    stats = fg_details.get("Stats") if isinstance(fg_details, dict) else None
    has_stats = isinstance(stats, dict) and bool(stats)
    if not has_stats:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=False,
            has_force_payload=True,
            reason="stats_missing",
        )

    if not isinstance(ref_arrays, dict) or not ref_arrays:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=True,
            has_force_payload=True,
            reason="ref_arrays_missing",
        )

    calc_song, calc_reason = _resolve_calc_song(
        song=winner.song,
        cfg_dict=cfg_dict,
        calc_song_cache=calc_song_cache,
    )
    if not isinstance(calc_song, dict):
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=True,
            has_force_payload=True,
            reason=calc_reason,
        )

    try:
        surface = require_response_surface(force_details)
        replay = score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, surface)
        replay_score = int(replay or 0)
    except Exception:
        return ReplayResult(
            song=winner.song,
            source=winner.source,
            loadout_hash=winner.loadout_hash,
            persisted_score=persisted_score,
            replay_score=0,
            has_stats=True,
            has_force_payload=True,
            reason="replay_error",
        )

    reason = "ok" if replay_score > 0 else "replay_zero"
    return ReplayResult(
        song=winner.song,
        source=winner.source,
        loadout_hash=winner.loadout_hash,
        persisted_score=persisted_score,
        replay_score=int(replay_score),
        has_stats=True,
        has_force_payload=True,
        reason=reason,
    )


def _replay_winner(
    conn: sqlite3.Connection,
    *,
    winner: Winner,
    team_buff: str,
    ref_arrays: dict[str, Any] | None,
    cfg_dict: dict[str, Any],
    calc_song_cache: dict[str, dict | None],
) -> ReplayResult:
    if winner.source == "fg":
        return _replay_fg(
            conn,
            winner=winner,
            team_buff=team_buff,
            ref_arrays=ref_arrays,
            cfg_dict=cfg_dict,
            calc_song_cache=calc_song_cache,
        )
    return _replay_base(
        conn,
        winner=winner,
        team_buff=team_buff,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        calc_song_cache=calc_song_cache,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare same-top-overall hash parity between two DBs.")
    ap.add_argument("--current", type=str, default="evolution.db")
    ap.add_argument("--legacy", type=str, default="evolutionref5.db")
    ap.add_argument("--team-buff", type=str, default="T5")
    ap.add_argument("--sample-limit", type=int, default=20)
    ap.add_argument("--json-out", type=str, default="")
    args = ap.parse_args()

    cur_db = str(Path(args.current))
    leg_db = str(Path(args.legacy))
    team_buff = str(args.team_buff or "T5").strip().upper()
    sample_limit = max(1, int(args.sample_limit or 20))

    cur = sqlite3.connect(cur_db)
    leg = sqlite3.connect(leg_db)
    cur.row_factory = sqlite3.Row
    leg.row_factory = sqlite3.Row

    try:
        ref_arrays = _get_team_buff_ref_arrays_cached()
        cfg_dict: dict[str, Any] = {}
        calc_song_cache_cur: dict[str, dict | None] = {}
        calc_song_cache_leg: dict[str, dict | None] = {}

        songs = sorted(_songs_in_db(cur, team_buff=team_buff) | _songs_in_db(leg, team_buff=team_buff))

        same_hash_count = 0
        persisted_equal = 0
        persisted_diff = 0
        max_abs_diff = 0
        max_diff_row: dict[str, Any] | None = None

        valid_nonzero_replay = 0
        replay_equal = 0
        replay_diff = 0

        samples_persisted_diff: list[dict[str, Any]] = []
        samples_replay_zero: list[dict[str, Any]] = []
        samples_replay_diff: list[dict[str, Any]] = []

        reason_counts: dict[str, int] = {}

        for song in songs:
            current_winner = _best_overall(cur, song=song, team_buff=team_buff)
            legacy_winner = _best_overall(leg, song=song, team_buff=team_buff)
            if current_winner is None or legacy_winner is None:
                continue
            if not current_winner.loadout_hash or current_winner.loadout_hash != legacy_winner.loadout_hash:
                continue

            same_hash_count += 1
            persisted_delta = int(current_winner.persisted_score) - int(legacy_winner.persisted_score)
            if persisted_delta == 0:
                persisted_equal += 1
            else:
                persisted_diff += 1
                if len(samples_persisted_diff) < sample_limit:
                    samples_persisted_diff.append(
                        {
                            "song": song,
                            "hash": current_winner.loadout_hash,
                            "current_source": current_winner.source,
                            "legacy_source": legacy_winner.source,
                            "current_persisted": int(current_winner.persisted_score),
                            "legacy_persisted": int(legacy_winner.persisted_score),
                            "delta": int(persisted_delta),
                        }
                    )
                if abs(persisted_delta) > max_abs_diff:
                    max_abs_diff = abs(persisted_delta)
                    max_diff_row = {
                        "song": song,
                        "hash": current_winner.loadout_hash,
                        "current_source": current_winner.source,
                        "legacy_source": legacy_winner.source,
                        "current_persisted": int(current_winner.persisted_score),
                        "legacy_persisted": int(legacy_winner.persisted_score),
                        "delta": int(persisted_delta),
                    }

            cur_replay = _replay_winner(
                cur,
                winner=current_winner,
                team_buff=team_buff,
                ref_arrays=ref_arrays,
                cfg_dict=cfg_dict,
                calc_song_cache=calc_song_cache_cur,
            )
            leg_replay = _replay_winner(
                leg,
                winner=legacy_winner,
                team_buff=team_buff,
                ref_arrays=ref_arrays,
                cfg_dict=cfg_dict,
                calc_song_cache=calc_song_cache_leg,
            )

            reason_counts[f"current:{cur_replay.reason}"] = reason_counts.get(f"current:{cur_replay.reason}", 0) + 1
            reason_counts[f"legacy:{leg_replay.reason}"] = reason_counts.get(f"legacy:{leg_replay.reason}", 0) + 1

            if cur_replay.replay_score <= 0 or leg_replay.replay_score <= 0:
                if len(samples_replay_zero) < sample_limit:
                    samples_replay_zero.append(
                        {
                            "song": song,
                            "hash": current_winner.loadout_hash,
                            "current": asdict(cur_replay),
                            "legacy": asdict(leg_replay),
                        }
                    )
                continue

            valid_nonzero_replay += 1
            replay_delta = int(cur_replay.replay_score) - int(leg_replay.replay_score)
            if replay_delta == 0:
                replay_equal += 1
            else:
                replay_diff += 1
                if len(samples_replay_diff) < sample_limit:
                    samples_replay_diff.append(
                        {
                            "song": song,
                            "hash": current_winner.loadout_hash,
                            "current": asdict(cur_replay),
                            "legacy": asdict(leg_replay),
                            "replay_delta": int(replay_delta),
                        }
                    )

        print("=" * 88)
        print(f"same_top_overall_hash parity (team_buff={team_buff})")
        print("=" * 88)
        print(f"same_hash_count={same_hash_count}")
        print(f"persisted_equal={persisted_equal} persisted_diff={persisted_diff}")
        print(f"max_persisted_abs_diff={max_abs_diff}")
        if isinstance(max_diff_row, dict):
            print("max_diff_row=" + json.dumps(max_diff_row, ensure_ascii=False))
        print(
            f"valid_nonzero_replay={valid_nonzero_replay} replay_equal={replay_equal} replay_diff={replay_diff}"
        )
        print("")
        print("reason_counts:")
        for key in sorted(reason_counts.keys()):
            print(f"  {key}={reason_counts[key]}")

        print("")
        print(f"samples_persisted_diff (up to {sample_limit}):")
        for row in samples_persisted_diff:
            print("  " + json.dumps(row, ensure_ascii=False))

        print("")
        print(f"samples_replay_zero (up to {sample_limit}):")
        for row in samples_replay_zero:
            print("  " + json.dumps(row, ensure_ascii=False))

        print("")
        print(f"samples_replay_diff (up to {sample_limit}):")
        for row in samples_replay_diff:
            print("  " + json.dumps(row, ensure_ascii=False))

        if args.json_out:
            out_path = Path(str(args.json_out))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "team_buff": team_buff,
                "same_hash_count": int(same_hash_count),
                "persisted_equal": int(persisted_equal),
                "persisted_diff": int(persisted_diff),
                "max_persisted_abs_diff": int(max_abs_diff),
                "max_diff_row": max_diff_row,
                "valid_nonzero_replay": int(valid_nonzero_replay),
                "replay_equal": int(replay_equal),
                "replay_diff": int(replay_diff),
                "reason_counts": reason_counts,
                "samples_persisted_diff": samples_persisted_diff,
                "samples_replay_zero": samples_replay_zero,
                "samples_replay_diff": samples_replay_diff,
            }
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print("")
            print(f"wrote_json={out_path}")
        return 0
    finally:
        cur.close()
        leg.close()


if __name__ == "__main__":
    raise SystemExit(main())
