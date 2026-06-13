"""Create a self-contained evolution.db copy safe to share (no WAL/SHM sidecars)."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def export_db(src: Path, dst: Path) -> None:
    if dst.exists():
        dst.unlink()

    conn = sqlite3.connect(str(src), timeout=60.0)
    try:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        dst_posix = str(dst.resolve()).replace("\\", "/")
        conn.execute(f"VACUUM INTO '{dst_posix}'")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()

    # Ensure the export stays a single portable file (no WAL sidecars).
    finalize = sqlite3.connect(str(dst), timeout=60.0)
    try:
        finalize.execute("PRAGMA journal_mode=DELETE")
    finally:
        finalize.close()


def verify_db(path: Path) -> dict[str, object]:
    conn = sqlite3.connect(str(path))
    try:
        return {
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
            "tables": conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0],
            "songs": conn.execute("SELECT count(*) FROM songs").fetchone()[0],
            "integrity": conn.execute("PRAGMA integrity_check").fetchone()[0],
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src",
        type=Path,
        default=PROJECT_ROOT / "evolution.db",
        help="Source evolution.db path",
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=PROJECT_ROOT / "evolution_export.db",
        help="Portable export path (single .db file)",
    )
    args = parser.parse_args()

    if not args.src.is_file():
        raise SystemExit(f"Source DB not found: {args.src}")

    export_db(args.src, args.dst)
    info = verify_db(args.dst)

    print(f"export_path: {args.dst}")
    print(f"export_bytes: {args.dst.stat().st_size}")
    for key, value in info.items():
        print(f"{key}: {value}")
    print(f"wal_exists: {args.dst.with_name(args.dst.name + '-wal').exists()}")
    print(f"shm_exists: {args.dst.with_name(args.dst.name + '-shm').exists()}")


if __name__ == "__main__":
    main()
