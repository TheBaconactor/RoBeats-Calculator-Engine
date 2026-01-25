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
from configparser import ConfigParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    ensure("HumanHitSim")

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

    # Determinism / reduce noise.
    cfg.set("HumanHitSim", "Enabled", "false")
    cfg.set("HumanHitSim", "Seed", "12345")
    cfg.set("HumanHitSim", "ApplyTo", "FG")

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

    print("\nAuditing DB...")
    audit_script = PROJECT_ROOT / "tools" / "db" / "audit_frontend_db.py"
    proc2 = subprocess.run([sys.executable, str(audit_script), "--db", str(smoke_db)], cwd=str(PROJECT_ROOT), env=env)
    raise SystemExit(proc2.returncode)


if __name__ == "__main__":
    main()
