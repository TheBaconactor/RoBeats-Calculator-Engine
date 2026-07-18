"""
Compare CURRENT vs LEGACY/REFERENCE DB on replayed "overall best" per song.

Overall best = max(best base score, best FG score) for a given (song, team_buff).

This tool can compare persisted scores, replay either side with the current scorer,
or replay both sides symmetrically. That makes it useful for "recover and compare"
audits where stale or inflated persisted FG rows must not be trusted at face value.

Usage:
  python tools/db/compare_overall_best_to_legacy_db.py --team-buff T5 --eps 2
  python tools/db/compare_overall_best_to_legacy_db.py --current evolution.db --legacy evolutionref2.db --eps 2
  python tools/db/compare_overall_best_to_legacy_db.py --current evolution.db --legacy evolutionref2.db --replay-current-base --replay-current-fg --replay-legacy-base --replay-legacy-fg --eps 2
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.team_buff import normalize_team_buff
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.data.song_io import scan_song_header


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


@lru_cache(maxsize=6)
def _song_path_index(project_root: Path, difficulty: str) -> dict[str, Path]:
    root = project_root / "Data" / difficulty
    if not root.is_dir():
        return {}
    paths: dict[str, Path] = {}
    for path in root.rglob("*.txt"):
        metadata = scan_song_header(str(path))
        name = str((metadata or {}).get("Song Name") or "").strip()
        if name:
            paths.setdefault(name, path)
    return paths


def _song_file_from_name(project_root: Path, song_name: str) -> Path | None:
    diff = _infer_difficulty_from_song_name(song_name)
    fp = project_root / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return fp
    return _song_path_index(project_root, diff).get(song_name)


@dataclass(frozen=True)
class BestRow:
    score: int
    loadout_hash: str


def _best_base(conn: sqlite3.Connection, *, song: str, team_buff: str) -> BestRow | None:
    if not _table_exists(conn, "team_buff_loadouts"):
        return None
    row = conn.execute(
        """
        SELECT score, loadout_hash
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        ORDER BY score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (str(song), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    return BestRow(score=int(row[0] or 0), loadout_hash=str(row[1] or "").strip())


def _best_fg(conn: sqlite3.Connection, *, song: str, team_buff: str) -> BestRow | None:
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return None
    row = conn.execute(
        """
        SELECT fg_score, loadout_hash
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        ORDER BY fg_score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (str(song), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    return BestRow(score=int(row[0] or 0), loadout_hash=str(row[1] or "").strip())


def _best_overall(conn: sqlite3.Connection, *, song: str, team_buff: str) -> dict:
    base = _best_base(conn, song=song, team_buff=team_buff)
    fg = _best_fg(conn, song=song, team_buff=team_buff)

    base_score = int(base.score) if base else 0
    fg_score = int(fg.score) if fg else 0

    if fg_score > base_score:
        return {"best": fg_score, "source": "fg", "hash": fg.loadout_hash if fg else ""}
    return {"best": base_score, "source": "base", "hash": base.loadout_hash if base else ""}


def _best_base_rescored_legacy(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
):
    """
    Recompute legacy best base score using GPU fixed scoring on persisted Stats.

    NOTE: This is a "staleness correction" pass for legacy DBs whose `score` column
    may have been produced under older scorers / chart data.
    """
    if not _table_exists(conn, "team_buff_loadouts"):
        return {"best": 0, "hash": ""}

    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    calc_song = calc_song_cache.get(song)
    if calc_song is None:
        fp = _song_file_from_name(project_root, song)
        if fp is None:
            return {"best": 0, "hash": ""}
        calc_song = get_base_calc_song(str(fp), cfg_dict)
        calc_song_cache[song] = calc_song

    meta = calc_song.get("metadata", {}) or {}
    primary = str(meta.get("Primary Color", "") or "").strip()
    secondary = str(meta.get("Secondary Color", "") or "").strip()
    if not primary and not secondary:
        return {"best": 0, "hash": ""}

    rows = conn.execute(
        """
        SELECT loadout_hash, details_json
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        """,
        (str(song), str(team_buff)),
    ).fetchall()

    best_score = 0
    best_hash = ""
    for r in rows or []:
        h = str(r[0] or "").strip()
        details_json = r[1]
        if not h or not details_json:
            continue
        try:
            details = json.loads(details_json)
        except Exception:
            continue
        details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
        stats = (details or {}).get("Stats") if isinstance(details, dict) else None
        if not isinstance(stats, dict) or not stats:
            continue
        si = int(score_stats_exact(stats, calc_song, ref_arrays))
        if si > best_score:
            best_score = si
            best_hash = h
    return {"best": best_score, "hash": best_hash}


def _best_fg_rescored_legacy(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
    validate_legality: bool = False,
):
    """
    Recompute persisted FG rows from their canonical response surface.

    The response surface is the replay authority because it represents Fever/Great
    overlap. Forced-count configs cannot, so replaying them here can invent score
    regressions for otherwise valid rows.
    """
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return {"best": 0, "hash": ""}

    from gear_optimizer.data.database import _base_details_from_force_payload, _unpack_stats_after_load
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.fg_payload import require_response_surface
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact

    rows = conn.execute(
        """
        SELECT loadout_hash, force_details_json, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        """,
        (str(song), str(team_buff)),
    ).fetchall()
    if not rows:
        return {"best": 0, "hash": ""}

    calc_song = calc_song_cache.get(song)
    if calc_song is None:
        fp = _song_file_from_name(project_root, song)
        if fp is None:
            return {"best": 0, "hash": ""}
        calc_song = get_base_calc_song(str(fp), cfg_dict)
        calc_song_cache[song] = calc_song

    legality_calc_song = None
    if validate_legality:
        from gear_optimizer.data.song_io import clone_calc_song
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        legality_calc_song = clone_calc_song(calc_song)
        apply_timing_envelope(legality_calc_song, mode="perfect_window")

    best_score = 0
    best_hash = ""
    for row in rows:
        loadout_hash = str(row[0] or "").strip()
        force_json = row[1]
        if not loadout_hash or not force_json:
            continue
        try:
            force_details = json.loads(force_json)
        except Exception:
            continue
        if not isinstance(force_details, dict):
            continue
        try:
            details = json.loads(row[2]) if row[2] else {}
        except Exception:
            details = {}
        if not isinstance(details, dict):
            details = {}
        details = _unpack_stats_after_load(details) if isinstance(details, dict) else {}

        fg_details = _base_details_from_force_payload(details, force_details)
        stats = fg_details.get("Stats") if isinstance(fg_details, dict) else None
        if not isinstance(stats, dict) or not stats:
            continue
        if legality_calc_song is not None:
            from tools.dev.audit_loadout_legality import audit_fg_loadout

            try:
                if audit_fg_loadout(force_details, legality_calc_song, ref_arrays):
                    continue
            except (KeyError, TypeError, ValueError):
                continue
        surface = require_response_surface(force_details)
        replay = score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, surface)
        if replay is None:
            continue
        si = int(replay)
        if si > best_score:
            best_score = si
            best_hash = str(loadout_hash)

    return {"best": best_score, "hash": best_hash}


def _best_base_replayed(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
):
    return _best_base_rescored_legacy(
        conn,
        song=song,
        team_buff=team_buff,
        project_root=project_root,
        cfg_dict=cfg_dict,
        ref_arrays=ref_arrays,
        calc_song_cache=calc_song_cache,
    )


def _best_fg_replayed(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
):
    return _best_fg_rescored_legacy(
        conn,
        song=song,
        team_buff=team_buff,
        project_root=project_root,
        cfg_dict=cfg_dict,
        ref_arrays=ref_arrays,
        calc_song_cache=calc_song_cache,
        validate_legality=True,
    )


def _best_row_parts(best: BestRow | dict | None) -> tuple[int, str]:
    if best is None:
        return 0, ""
    if isinstance(best, dict):
        return int(best.get("best") or 0), str(best.get("hash") or "").strip()
    return int(best.score), str(best.loadout_hash or "").strip()


def _resolve_side_snapshot(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    replay_base: bool,
    replay_fg: bool,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
) -> dict[str, object]:
    base_best = (
        _best_base_replayed(
            conn,
            song=song,
            team_buff=team_buff,
            project_root=project_root,
            cfg_dict=cfg_dict,
            ref_arrays=ref_arrays,
            calc_song_cache=calc_song_cache,
        )
        if replay_base
        else _best_base(conn, song=song, team_buff=team_buff)
    )
    fg_best = (
        _best_fg_replayed(
            conn,
            song=song,
            team_buff=team_buff,
            project_root=project_root,
            cfg_dict=cfg_dict,
            ref_arrays=ref_arrays,
            calc_song_cache=calc_song_cache,
        )
        if replay_fg
        else _best_fg(conn, song=song, team_buff=team_buff)
    )

    base_score, base_hash = _best_row_parts(base_best)
    fg_score, fg_hash = _best_row_parts(fg_best)
    if fg_score > base_score:
        overall_score = int(fg_score)
        overall_hash = str(fg_hash)
        overall_source = "fg"
    else:
        overall_score = int(base_score)
        overall_hash = str(base_hash)
        overall_source = "base"

    return {
        "base_score": int(base_score),
        "base_hash": str(base_hash),
        "fg_score": int(fg_score),
        "fg_hash": str(fg_hash),
        "overall_score": int(overall_score),
        "overall_hash": str(overall_hash),
        "overall_source": str(overall_source),
    }


def _compare_pair(current_score: int, legacy_score: int, *, eps: int) -> str:
    delta = int(current_score) - int(legacy_score)
    if abs(int(delta)) <= int(eps):
        return "tie"
    if delta > 0:
        return "current_win"
    return "legacy_win"


def _songs_in_db(conn: sqlite3.Connection, *, team_buff: str) -> set[str]:
    team_buff = normalize_team_buff(team_buff)
    out: set[str] = set()
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        if not _table_exists(conn, table):
            continue
        rows = conn.execute(
            f"""
            SELECT DISTINCT song_name
            FROM {table}
            WHERE UPPER(COALESCE(team_buff,''))=?
            """,
            (str(team_buff),),
        ).fetchall()
        for r in rows or []:
            s = str(r[0] or "").strip()
            if s:
                out.add(s)
    return out


def _hash_present(conn: sqlite3.Connection, *, song: str, team_buff: str, loadout_hash: str) -> bool:
    if not loadout_hash:
        return False
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        if not _table_exists(conn, table):
            continue
        row = conn.execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? AND loadout_hash=?
            LIMIT 1
            """,
            (str(song), str(team_buff), str(loadout_hash)),
        ).fetchone()
        if row is not None:
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Compare current vs legacy DB overall-best per song.")
    p.add_argument("--current", type=str, default=str(PROJECT_ROOT / "evolution.db"))
    p.add_argument("--legacy", type=str, default=str(PROJECT_ROOT / "evolution_legacy.db"))
    p.add_argument("--team-buff", type=str, default="T5")
    p.add_argument("--eps", type=int, default=2, help="Treat scores within +/- eps as ties.")
    p.add_argument("--artifacts-dir", type=str, default=str(PROJECT_ROOT / "artifacts"))
    p.add_argument("--examples", type=int, default=25, help="Max regression examples to embed in JSON.")
    p.add_argument(
        "--replay-current-base",
        "--rescore-current-base",
        action="store_true",
        help="Replay current-side best base rows with the current GPU fixed scorer.",
    )
    p.add_argument(
        "--replay-current-fg",
        "--rescore-current-fg",
        action="store_true",
        help="Replay current-side FG rows with the current GPU exact-inner solver.",
    )
    p.add_argument(
        "--replay-legacy-base",
        "--rescore-legacy-base",
        action="store_true",
        help="Replay legacy/reference-side best base rows with the current GPU fixed scorer.",
    )
    p.add_argument(
        "--replay-legacy-fg",
        "--rescore-legacy-fg",
        action="store_true",
        help="Replay legacy/reference-side FG rows with the current GPU exact-inner solver.",
    )
    args = p.parse_args()

    current_db = Path(str(args.current))
    legacy_db = Path(str(args.legacy))
    if not current_db.exists():
        raise SystemExit(f"Current DB not found: {current_db}")
    if not legacy_db.exists():
        raise SystemExit(f"Legacy DB not found: {legacy_db}")

    team_buff = normalize_team_buff(args.team_buff)
    eps = max(0, int(args.eps))
    example_limit = max(0, int(args.examples))
    replay_current_base = bool(args.replay_current_base)
    replay_current_fg = bool(args.replay_current_fg)
    replay_legacy_base = bool(args.replay_legacy_base)
    replay_legacy_fg = bool(args.replay_legacy_fg)

    cur = sqlite3.connect(str(current_db))
    leg = sqlite3.connect(str(legacy_db))
    try:
        songs = sorted(_songs_in_db(cur, team_buff=team_buff) | _songs_in_db(leg, team_buff=team_buff))

        cfg_dict: dict = {}
        ref_arrays: dict = {}
        cur_calc_song_cache: dict[str, dict] = {}
        leg_calc_song_cache: dict[str, dict] = {}
        if replay_current_base or replay_current_fg or replay_legacy_base or replay_legacy_fg:
            from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
            from gear_optimizer.core.config import load_config
            from gear_optimizer.core.utils import cfg_to_dict

            cfg_dict = cfg_to_dict(load_config())
            ref_arrays = _get_team_buff_ref_arrays_cached()
            if not isinstance(ref_arrays, dict) or not ref_arrays:
                raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

        sections = ("overall", "base", "fg")
        counts = {
            section: {"current_wins": 0, "ties": 0, "legacy_wins": 0}
            for section in sections
        }
        fg_presence = {"both_present": 0, "current_only": 0, "legacy_only": 0, "both_missing": 0}
        current_win_examples: list[dict] = []
        legacy_win_examples: list[dict] = []

        for song in songs:
            cur_side = _resolve_side_snapshot(
                cur,
                song=song,
                team_buff=team_buff,
                replay_base=replay_current_base,
                replay_fg=replay_current_fg,
                project_root=PROJECT_ROOT,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=cur_calc_song_cache,
            )
            leg_side = _resolve_side_snapshot(
                leg,
                song=song,
                team_buff=team_buff,
                replay_base=replay_legacy_base,
                replay_fg=replay_legacy_fg,
                project_root=PROJECT_ROOT,
                cfg_dict=cfg_dict,
                ref_arrays=ref_arrays,
                calc_song_cache=leg_calc_song_cache,
            )

            cur_fg_present = int(cur_side["fg_score"] or 0) > 0
            leg_fg_present = int(leg_side["fg_score"] or 0) > 0
            if cur_fg_present and leg_fg_present:
                fg_presence["both_present"] += 1
            elif cur_fg_present:
                fg_presence["current_only"] += 1
            elif leg_fg_present:
                fg_presence["legacy_only"] += 1
            else:
                fg_presence["both_missing"] += 1

            section_scores = {
                "overall": (int(cur_side["overall_score"]), int(leg_side["overall_score"])),
                "base": (int(cur_side["base_score"]), int(leg_side["base_score"])),
                "fg": (int(cur_side["fg_score"]), int(leg_side["fg_score"])),
            }
            outcomes: dict[str, str] = {}
            for section, (cur_score, leg_score) in section_scores.items():
                outcome = _compare_pair(cur_score, leg_score, eps=eps)
                outcomes[section] = outcome
                if outcome == "tie":
                    counts[section]["ties"] += 1
                elif outcome == "current_win":
                    counts[section]["current_wins"] += 1
                else:
                    counts[section]["legacy_wins"] += 1

            overall_delta = int(cur_side["overall_score"]) - int(leg_side["overall_score"])
            if outcomes["overall"] == "current_win" and len(current_win_examples) < example_limit:
                current_win_examples.append(
                    {
                        "song": song,
                        "current_overall": int(cur_side["overall_score"]),
                        "legacy_overall": int(leg_side["overall_score"]),
                        "delta": int(overall_delta),
                        "current_source": str(cur_side["overall_source"]),
                        "legacy_source": str(leg_side["overall_source"]),
                        "current_hash": str(cur_side["overall_hash"]),
                        "legacy_hash": str(leg_side["overall_hash"]),
                        "base_delta": int(cur_side["base_score"]) - int(leg_side["base_score"]),
                        "fg_delta": int(cur_side["fg_score"]) - int(leg_side["fg_score"]),
                    }
                )
            if outcomes["overall"] == "legacy_win" and len(legacy_win_examples) < example_limit:
                legacy_hash = str(leg_side["overall_hash"])
                legacy_present = _hash_present(cur, song=song, team_buff=team_buff, loadout_hash=legacy_hash)
                legacy_win_examples.append(
                    {
                        "song": song,
                        "current_overall": int(cur_side["overall_score"]),
                        "legacy_overall": int(leg_side["overall_score"]),
                        "delta": int(overall_delta),
                        "current_source": str(cur_side["overall_source"]),
                        "legacy_source": str(leg_side["overall_source"]),
                        "current_hash": str(cur_side["overall_hash"]),
                        "legacy_hash": legacy_hash,
                        "legacy_winner_present_in_current_db": bool(legacy_present),
                        "base_delta": int(cur_side["base_score"]) - int(leg_side["base_score"]),
                        "fg_delta": int(cur_side["fg_score"]) - int(leg_side["fg_score"]),
                    }
                )

        out = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "team_buff": team_buff,
            "eps": eps,
            "current_db": str(current_db),
            "legacy_db": str(legacy_db),
            "replay": {
                "current_base": bool(replay_current_base),
                "current_fg": bool(replay_current_fg),
                "legacy_base": bool(replay_legacy_base),
                "legacy_fg": bool(replay_legacy_fg),
            },
            "songs_compared": len(songs),
            "counts": counts,
            "fg_presence": fg_presence,
            "current_win_examples": current_win_examples,
            "legacy_win_examples": legacy_win_examples,
        }

        artifacts_dir = Path(str(args.artifacts_dir))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = artifacts_dir / f"db_overall_best_compare_current_vs_legacy_{stamp}_eps{eps}.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

        print("=" * 80)
        print(f"overall_best (team_buff={team_buff}, eps=+/-{eps})")
        print("=" * 80)
        print(f"Songs compared: {len(songs):,}")
        for section in sections:
            section_counts = counts[section]
            print(
                f"{section}: current_wins={section_counts['current_wins']:,} "
                f"ties={section_counts['ties']:,} legacy_wins={section_counts['legacy_wins']:,}"
            )
        print(
            "fg_presence: "
            f"both_present={fg_presence['both_present']:,} "
            f"current_only={fg_presence['current_only']:,} "
            f"legacy_only={fg_presence['legacy_only']:,} "
            f"both_missing={fg_presence['both_missing']:,}"
        )
        print("Wrote report:", str(out_path))
        return 0 if counts["overall"]["legacy_wins"] == 0 else 2
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            leg.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
