import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection_with_timeout

DEFAULT_SONG_NAME = "Test Song (Hard)"


def _looks_like_test_db(path: str) -> bool:
    p = str(path or "").replace("\\", "/").lower()
    return any(token in p for token in ("test", "pytest", "tmp", "temp")) or p.endswith(("_test.db", ".test.db"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Delete a known test song and its loadouts from a SQLite DB.")
    parser.add_argument("--db", dest="db_path", default="", help="Path to the *test* SQLite DB (required)")
    parser.add_argument("--song-name", default=DEFAULT_SONG_NAME, help="Song name to delete (default: %(default)s)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (dangerous; still requires a test-looking DB path unless --force)",
    )
    parser.add_argument("--force", action="store_true", help="Allow non-test-looking DB paths (DANGEROUS)")
    args = parser.parse_args(argv)

    db_path = str(args.db_path or "").strip()
    if not db_path:
        raise SystemExit("Refusing to run without --db. Pass the path to a test DB explicitly.")

    if not bool(args.force) and not _looks_like_test_db(db_path):
        raise SystemExit(f"Refusing to delete from non-test-looking DB path: {db_path!r} (pass --force to override)")

    song_name = str(args.song_name or "").strip()
    if not song_name:
        raise SystemExit("Empty --song-name")

    print(f"DB: {db_path}")
    print(f"Cleaning up {song_name!r} from DB...")
    if not args.yes:
        raw = input("This will DELETE rows. Continue? [y/N] ").strip().lower()
        if raw not in {"y", "yes"}:
            print("Aborted.")
            return 1

    conn = get_db_connection_with_timeout(db_path, timeout=10.0)
    try:
        cur = conn.execute("SELECT count(*) FROM team_buff_loadouts WHERE song_name = ?", (song_name,))
        count = int(cur.fetchone()[0] or 0)
        print(f"Found {count} base loadouts to delete.")

        if count > 0:
            conn.execute("DELETE FROM team_buff_loadouts WHERE song_name = ?", (song_name,))
            conn.execute("DELETE FROM team_buff_fg_loadouts WHERE song_name = ?", (song_name,))
            conn.execute("DELETE FROM songs WHERE name = ?", (song_name,))
            conn.commit()
            print("Deleted.")
        else:
            print("Nothing to delete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
