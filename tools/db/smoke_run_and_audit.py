"""
Run a tiny optimizer job into a fresh DB, then audit the DB for integrity.

This is meant as a "real output" smoke test you can run locally on a Vulkan-capable GPU.

Usage:
  python tools/db/smoke_run_and_audit.py --song insight --difficulty Hard
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import json
import sqlite3
from configparser import ConfigParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _write_smoke_config(*, out_path: Path, base_config_path: Path, song: str, difficulty: str) -> None:
    cfg = ConfigParser()
    if base_config_path.exists():
        cfg.read(base_config_path, encoding="utf-8")

    def ensure(section: str) -> None:
        if not cfg.has_section(section):
            cfg.add_section(section)

    ensure("CalculateSong")
    ensure("IterationEngine")
    ensure("TeamContributionBuffConstant")

    cfg.set("CalculateSong", "Song_Name", song)
    cfg.set("CalculateSong", "Difficulty", difficulty)
    cfg.set("CalculateSong", "TargetPrimary", "All")
    cfg.set("CalculateSong", "TargetSecondary", "All")

    # Keep GPU on (GPU-only policy).
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")

    # Make it fast.
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "UseEvolutionDB", "true")
    cfg.set("IterationEngine", "SongRepeats", "1")
    cfg.set("IterationEngine", "SongQueueLimit", "1")
    cfg.set("IterationEngine", "InFlightSongs", "1")
    cfg.set("IterationEngine", "GA_SearchDepth", "5")
    cfg.set("IterationEngine", "GA_MultiStart", "1")
    cfg.set("IterationEngine", "GA_DBSeedProbability", "0.0")
    cfg.set("IterationEngine", "FG_CandidateLimit", "10")
    cfg.set("IterationEngine", "FG_SearchRadius", "3")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        cfg.write(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tiny optimizer job and audit the produced DB.")
    parser.add_argument("--song", type=str, default="insight", help="Song search text (as used by config.ini).")
    parser.add_argument("--difficulty", type=str, default="Hard", help="Easy/Normal/Hard/All")
    parser.add_argument(
        "--db",
        type=str,
        default="",
        help="Output DB path (default: artifacts/smoke_run/smoke_evolution.db).",
    )
    parser.add_argument("--keep", action="store_true", help="Keep existing output DB (do not delete).")
    args = parser.parse_args()

    smoke_root = PROJECT_ROOT / "artifacts" / "smoke_run"
    smoke_db = Path(args.db) if args.db else (smoke_root / "smoke_evolution.db")
    smoke_cfg = smoke_root / "smoke_config.ini"
    base_cfg = PROJECT_ROOT / "config.ini"

    if smoke_db.exists() and not args.keep:
        smoke_db.unlink()

    _write_smoke_config(out_path=smoke_cfg, base_config_path=base_cfg, song=args.song, difficulty=args.difficulty)

    env = os.environ.copy()
    env["EVOLUTION_DB_PATH"] = str(smoke_db)
    env["METAFINDER_CONFIG_PATH"] = str(smoke_cfg)
    env["GA_SEED"] = "1337"

    print(f"Running optimizer -> DB: {smoke_db}")
    print(f"Config: {smoke_cfg}")

    proc = subprocess.run([sys.executable, str(PROJECT_ROOT / "main.py")], cwd=str(PROJECT_ROOT), env=env, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

    print("\nAuditing DB (compact schema)...")
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load
    from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg

    conn2 = sqlite3.connect(str(smoke_db))
    conn2.row_factory = sqlite3.Row
    try:
        audit_cfg = ConfigParser()
        try:
            audit_cfg.read(str(smoke_cfg), encoding="utf-8")
        except Exception:
            pass
        baseline_team_buff = str(resolve_baseline_team_buff_from_cfg(audit_cfg, default="T5") or "T5").strip().upper() or "T5"

        version = conn2.execute("PRAGMA user_version").fetchone()[0]
        print(f"PRAGMA user_version: {version}")

        required_tables = {
            "songs",
            "team_buff_loadouts",
            "team_buff_fg_loadouts",
            "gear_name_encoding",
            "mini_name_encoding",
        }
        existing = {r["name"] for r in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = sorted(required_tables - existing)
        if missing:
            print(f"Missing required tables: {missing}")
            raise SystemExit(2)

        base_rows = conn2.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE UPPER(COALESCE(team_buff,'UNKNOWN'))=?",
            (baseline_team_buff,),
        ).fetchone()[0]
        print(f"team_buff_loadouts({baseline_team_buff}) rows: {int(base_rows or 0):,}")
        if int(base_rows or 0) <= 0:
            print("No baseline rows persisted.")
            raise SystemExit(2)

        row = conn2.execute(
            """
            SELECT score, fg_score, gear_ids_blob, minis_ids_blob, details_json
            FROM team_buff_loadouts
            WHERE UPPER(COALESCE(team_buff,'UNKNOWN'))=?
            ORDER BY score DESC
            LIMIT 1
            """,
            (baseline_team_buff,),
        ).fetchone()
        if row is None:
            print("No rows found to audit.")
            raise SystemExit(2)

        maps = _load_piece_name_encoding_maps(conn2, db_path=str(smoke_db))
        gear_ids = _unpack_id_list(row["gear_ids_blob"])
        gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
        gear = [g for g in gear if g]
        mini_id_groups = _unpack_id_groups(row["minis_ids_blob"])
        minis = [
            sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
        ]
        minis = [[n for n in g if n] for g in minis if g]

        details = json.loads(row["details_json"]) if row["details_json"] else {}
        details = _unpack_stats_after_load(details) or {}
        stats = details.get("Stats") if isinstance(details, dict) else None

        print(f"Top row score={int(row['score'] or 0):,} fg_score={int(row['fg_score'] or 0):,}")
        print(f"Top row gear_count={len(gear)} minis_slots={len(minis)} stats_keys={len(stats or {}) if isinstance(stats, dict) else 0}")

        if len(gear) != 6:
            print("Unexpected gear length (expected 6).")
            raise SystemExit(2)
        if not isinstance(stats, dict) or not stats:
            print("Missing/empty Stats after unpack.")
            raise SystemExit(2)

        print("Audit OK.")
        raise SystemExit(0)
    finally:
        conn2.close()


if __name__ == "__main__":
    main()
