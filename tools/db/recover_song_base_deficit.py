"""
Run a targeted single-song recovery pass for real base-score deficits.

This uses the normal optimizer entrypoint and persistence path, but writes a temporary
config that increases per-song revisit/DB-seed coverage without changing the repo's
global live defaults.

Usage:
  python tools/db/recover_song_base_deficit.py --song "RoBeats: The Light Speed Mashup [EXTENDED CUT] by Various Artists (Arranged by ZirconEscalus and Got1Butter)" --difficulty Normal
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from configparser import ConfigParser
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True)
class RecoverySettings:
    song_repeats: int = 5
    ga_search_depth: int = 125
    ga_multistart: int = 5
    ga_db_seed_probability: float = 1.0
    in_flight_songs: int = 1
    fg_candidate_limit: int | None = None
    fg_search_radius: int | None = None
    bundle_song_repeats: bool = True


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Hard"


def _read_details_difficulty(details_json: str | None) -> str:
    try:
        details = json.loads(details_json) if details_json else {}
    except Exception:
        details = {}
    diff = str((details or {}).get("Difficulty") or "").strip().title()
    if diff in {"Easy", "Normal", "Hard"}:
        return diff
    return ""


def _normalize_difficulty(value: str | None) -> str:
    diff = str(value or "").strip().title()
    if diff in {"Easy", "Normal", "Hard"}:
        return diff
    return ""


def _slugify(text: str) -> str:
    out = []
    prev_sep = False
    for ch in str(text or "").strip():
        if ch.isalnum():
            out.append(ch.lower())
            prev_sep = False
            continue
        if not prev_sep:
            out.append("_")
            prev_sep = True
    return "".join(out).strip("_") or "song"


def _resolve_song_target(*, db_path: Path, song_search: str, difficulty: str) -> dict[str, str]:
    wanted_diff = _normalize_difficulty(difficulty)
    needle = str(song_search or "").strip()
    if not needle:
        raise SystemExit("Missing --song.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT song_name, score, details_json
            FROM team_buff_loadouts
            WHERE UPPER(COALESCE(team_buff,''))='T5'
              AND LOWER(song_name) LIKE ?
            ORDER BY CASE WHEN LOWER(song_name)=? THEN 0 ELSE 1 END, score DESC, song_name ASC
            """,
            (f"%{needle.lower()}%", needle.lower()),
        ).fetchall()
    finally:
        conn.close()

    candidates: list[dict[str, str | int]] = []
    for row in rows or []:
        row_diff = _read_details_difficulty(row["details_json"]) or _infer_difficulty_from_song_name(str(row["song_name"] or ""))
        if wanted_diff and row_diff != wanted_diff:
            continue
        candidates.append(
            {
                "song_name": str(row["song_name"] or "").strip(),
                "difficulty": row_diff,
                "score": int(row["score"] or 0),
            }
        )

    if not candidates:
        suffix = f" ({wanted_diff})" if wanted_diff else ""
        raise SystemExit(f"No T5 base row matched song search {needle!r}{suffix}.")

    chosen = candidates[0]
    return {
        "song_name": str(chosen["song_name"]),
        "difficulty": str(chosen["difficulty"] or wanted_diff or "Hard"),
    }


def _write_recovery_config(
    *,
    out_path: Path,
    base_config_path: Path,
    target_song_name: str,
    difficulty: str,
    settings: RecoverySettings,
) -> None:
    cfg = ConfigParser()
    if base_config_path.exists():
        cfg.read(base_config_path, encoding="utf-8")

    def ensure(section: str) -> None:
        if not cfg.has_section(section):
            cfg.add_section(section)

    ensure("CalculateSong")
    ensure("IterationEngine")
    cfg.set("CalculateSong", "Song_Name", str(target_song_name))
    cfg.set("CalculateSong", "Difficulty", str(difficulty))
    cfg.set("CalculateSong", "TargetPrimary", "All")
    cfg.set("CalculateSong", "TargetSecondary", "All")

    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "UseEvolutionDB", "true")
    cfg.set("IterationEngine", "IgnoreResumeQueue", "true")
    cfg.set("IterationEngine", "SongRepeats", str(int(settings.song_repeats)))
    cfg.set("IterationEngine", "BundleSongRepeats", "true" if settings.bundle_song_repeats else "false")
    cfg.set("IterationEngine", "SongQueueLimit", "1")
    cfg.set("IterationEngine", "InFlightSongs", str(int(settings.in_flight_songs)))
    cfg.set("IterationEngine", "GA_SearchDepth", str(int(settings.ga_search_depth)))
    cfg.set("IterationEngine", "GA_MultiStart", str(int(settings.ga_multistart)))
    cfg.set("IterationEngine", "GA_DBSeedProbability", str(float(settings.ga_db_seed_probability)))
    if settings.fg_candidate_limit is not None:
        cfg.set("IterationEngine", "FG_CandidateLimit", str(int(settings.fg_candidate_limit)))
    if settings.fg_search_radius is not None:
        cfg.set("IterationEngine", "FG_SearchRadius", str(int(settings.fg_search_radius)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        cfg.write(f)


def _load_song_snapshot(*, db_path: Path, song_name: str) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        song_row = conn.execute(
            """
            SELECT name, best_score, best_fg_score, attempt_lifetime, attempts_first, last_updated
            FROM songs
            WHERE name=?
            """,
            (str(song_name),),
        ).fetchone()
        base_row = conn.execute(
            """
            SELECT score, fg_score, loadout_hash, details_json
            FROM team_buff_loadouts
            WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5'
            ORDER BY score DESC, loadout_hash ASC
            LIMIT 1
            """,
            (str(song_name),),
        ).fetchone()
        fg_row = conn.execute(
            """
            SELECT score, fg_score, loadout_hash
            FROM team_buff_fg_loadouts
            WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5'
            ORDER BY fg_score DESC, loadout_hash ASC
            LIMIT 1
            """,
            (str(song_name),),
        ).fetchone()
    finally:
        conn.close()

    details = {}
    if base_row is not None:
        try:
            details = json.loads(base_row["details_json"]) if base_row["details_json"] else {}
        except Exception:
            details = {}

    return {
        "song_name": str(song_name),
        "songs_best_score": int(song_row["best_score"] or 0) if song_row is not None else 0,
        "songs_best_fg_score": int(song_row["best_fg_score"] or 0) if song_row is not None else 0,
        "attempt_lifetime": int(song_row["attempt_lifetime"] or 0) if song_row is not None else 0,
        "attempts_first": int(song_row["attempts_first"] or 0) if song_row is not None else 0,
        "last_updated": float(song_row["last_updated"] or 0.0) if song_row is not None else 0.0,
        "top_base_score": int(base_row["score"] or 0) if base_row is not None else 0,
        "top_base_fg_score": int(base_row["fg_score"] or 0) if base_row is not None else 0,
        "top_base_hash": str(base_row["loadout_hash"] or "") if base_row is not None else "",
        "top_base_difficulty": str((details or {}).get("Difficulty") or ""),
        "top_base_selected_element": str((details or {}).get("SelectedElement") or ""),
        "top_fg_score": int(fg_row["fg_score"] or 0) if fg_row is not None else 0,
        "top_fg_base_score": int(fg_row["score"] or 0) if fg_row is not None else 0,
        "top_fg_hash": str(fg_row["loadout_hash"] or "") if fg_row is not None else "",
    }


def _snapshot_delta(before: dict, after: dict) -> dict:
    return {
        "best_score_delta": int(after.get("songs_best_score", 0) or 0) - int(before.get("songs_best_score", 0) or 0),
        "best_fg_score_delta": int(after.get("songs_best_fg_score", 0) or 0) - int(before.get("songs_best_fg_score", 0) or 0),
        "attempt_lifetime_delta": int(after.get("attempt_lifetime", 0) or 0) - int(before.get("attempt_lifetime", 0) or 0),
        "attempts_first_delta": int(after.get("attempts_first", 0) or 0) - int(before.get("attempts_first", 0) or 0),
    }


def _backup_db_if_requested(*, db_path: Path, backup_root: Path, enabled: bool) -> str:
    if not enabled or not db_path.exists():
        return ""
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / f"{db_path.stem}_backup_{stamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return str(backup_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a targeted single-song base deficit recovery pass.")
    parser.add_argument("--song", type=str, required=True, help="Exact or substring song search against the target DB.")
    parser.add_argument("--difficulty", type=str, default="", help="Optional difficulty override (Easy/Normal/Hard).")
    parser.add_argument("--db", type=str, default="", help="Target DB path (default: ./evolution.db).")
    parser.add_argument("--base-config", type=str, default="", help="Base config path to clone (default: ./config.ini).")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="",
        help="Artifact/report root (default: ./artifacts/db_recovery).",
    )
    parser.add_argument("--ga-seed", type=int, default=1337, help="Deterministic GA seed for the recovery run.")
    parser.add_argument("--song-repeats", type=int, default=5, help="Per-song repeat count for the recovery pass.")
    parser.add_argument("--ga-search-depth", type=int, default=125, help="GA search depth override.")
    parser.add_argument("--ga-multistart", type=int, default=5, help="GA multistart override.")
    parser.add_argument("--ga-db-seed-probability", type=float, default=1.0, help="DB seed probability override.")
    parser.add_argument("--in-flight-songs", type=int, default=1, help="In-flight song count override.")
    parser.add_argument("--fg-candidate-limit", type=int, default=None, help="Optional FG candidate limit override.")
    parser.add_argument("--fg-search-radius", type=int, default=None, help="Optional FG search radius override.")
    parser.add_argument("--no-backup", action="store_true", help="Skip making a timestamped DB backup before the run.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else (PROJECT_ROOT / "evolution.db")
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    base_config_path = Path(args.base_config) if args.base_config else (PROJECT_ROOT / "config.ini")
    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else (PROJECT_ROOT / "artifacts" / "db_recovery")

    target = _resolve_song_target(db_path=db_path, song_search=str(args.song), difficulty=str(args.difficulty))
    settings = RecoverySettings(
        song_repeats=max(1, int(args.song_repeats)),
        ga_search_depth=max(1, int(args.ga_search_depth)),
        ga_multistart=max(1, int(args.ga_multistart)),
        ga_db_seed_probability=max(0.0, float(args.ga_db_seed_probability)),
        in_flight_songs=max(1, int(args.in_flight_songs)),
        fg_candidate_limit=int(args.fg_candidate_limit) if args.fg_candidate_limit is not None else None,
        fg_search_radius=int(args.fg_search_radius) if args.fg_search_radius is not None else None,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_root = artifacts_dir / f"{stamp}_{_slugify(target['song_name'])}"
    run_root.mkdir(parents=True, exist_ok=True)
    config_path = run_root / "recovery_config.ini"

    backup_path = _backup_db_if_requested(
        db_path=db_path,
        backup_root=run_root,
        enabled=not bool(args.no_backup),
    )
    before = _load_song_snapshot(db_path=db_path, song_name=target["song_name"])

    _write_recovery_config(
        out_path=config_path,
        base_config_path=base_config_path,
        target_song_name=target["song_name"],
        difficulty=target["difficulty"],
        settings=settings,
    )

    env = os.environ.copy()
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_CONFIG_PATH"] = str(config_path)
    env["GA_SEED"] = str(int(args.ga_seed))
    env["METAFINDER_IGNORE_RESUME_QUEUE"] = "1"
    env["SONG_QUEUE_LIMIT"] = "1"
    env["METAFINDER_PROGRESS"] = "0"
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[Recovery] Song: {target['song_name']}")
    print(f"[Recovery] Difficulty: {target['difficulty']}")
    print(f"[Recovery] DB: {db_path}")
    print(f"[Recovery] Config: {config_path}")
    if backup_path:
        print(f"[Recovery] Backup: {backup_path}")
    print(
        "[Recovery] Settings: "
        f"SongRepeats={settings.song_repeats}, "
        f"GA_SearchDepth={settings.ga_search_depth}, "
        f"GA_MultiStart={settings.ga_multistart}, "
        f"GA_DBSeedProbability={settings.ga_db_seed_probability}, "
        f"InFlightSongs={settings.in_flight_songs}"
    )
    print(
        "[Recovery] Before: "
        f"best_score={before['songs_best_score']:,}, "
        f"best_fg_score={before['songs_best_fg_score']:,}, "
        f"attempt_lifetime={before['attempt_lifetime']}"
    )

    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
        check=False,
    )

    after = _load_song_snapshot(db_path=db_path, song_name=target["song_name"])
    delta = _snapshot_delta(before, after)

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "db": str(db_path),
        "backup_db": backup_path,
        "target": target,
        "settings": asdict(settings),
        "ga_seed": int(args.ga_seed),
        "returncode": int(completed.returncode),
        "before": before,
        "after": after,
        "delta": delta,
        "config_path": str(config_path),
    }
    report_path = run_root / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        "[Recovery] After: "
        f"best_score={after['songs_best_score']:,}, "
        f"best_fg_score={after['songs_best_fg_score']:,}, "
        f"attempt_lifetime={after['attempt_lifetime']}"
    )
    print(
        "[Recovery] Delta: "
        f"best_score={delta['best_score_delta']:+,}, "
        f"best_fg_score={delta['best_fg_score_delta']:+,}, "
        f"attempt_lifetime={delta['attempt_lifetime_delta']:+d}"
    )
    print(f"[Recovery] Report: {report_path}")

    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
