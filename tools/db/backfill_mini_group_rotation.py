import argparse
import os
import sqlite3
import sys

# Ensure repo root directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _pack_id_groups,
    _unpack_id_groups,
    get_evolution_db_path,
)
from gear_optimizer.data.loadout_equivalence import rotate_mini_groups_for_slot_display


def _as_bytes(blob: object) -> bytes:
    if blob is None:
        return b""
    if isinstance(blob, memoryview):
        return blob.tobytes()
    if isinstance(blob, (bytes, bytearray)):
        return bytes(blob)
    return b""


def _rotate_minis_blob(blob: object, maps) -> bytes:
    raw = _as_bytes(blob)
    if not raw:
        return raw

    id_groups = _unpack_id_groups(raw)
    if not id_groups:
        return raw

    # Decode IDs to names (preserve slot order).
    groups: list[list[str]] = []
    for g in id_groups:
        if not g:
            continue
        names: list[str] = []
        for idx in g:
            try:
                name = str(maps.mini_id_to_name.get(int(idx), "") or "").strip()
            except Exception:
                name = ""
            if name:
                names.append(name)
        if names:
            groups.append(names)

    if not groups:
        return raw

    rotated = rotate_mini_groups_for_slot_display(groups)
    if not rotated:
        return raw

    # Re-encode names back to IDs in the rotated order.
    out_groups: list[list[int]] = []
    for g in rotated:
        if not g:
            continue
        ids: list[int] = []
        for name in g:
            try:
                idx = int(maps.mini_name_to_id.get(str(name), 0) or 0)
            except Exception:
                idx = 0
            if idx <= 0:
                # Conservative: if we can't map back to IDs, keep the original blob unchanged.
                return raw
            ids.append(idx)
        out_groups.append(ids)

    new_blob = _pack_id_groups(out_groups)
    return new_blob if new_blob else raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill compact DB mini variant-group ordering so each slot's representative mini "
            "is persisted as the first element (legacy minis_json display contract)."
        )
    )
    parser.add_argument("--db", default="", help="Path to evolution DB (defaults to EVOLUTION_DB_PATH / ./evolution.db)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report updates without writing.")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows per table (0 = no limit).")
    parser.add_argument("--commit-every", type=int, default=5000, help="Commit every N updated rows.")
    args = parser.parse_args()

    db_path = str(args.db or get_evolution_db_path() or "").strip()
    if not db_path or not os.path.exists(db_path):
        print(f"[backfill_mini_group_rotation] DB not found: {db_path!r}")
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))
        total_updated = 0

        for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
            print(f"\n[{table}] scanning minis_ids_blob...")
            updated = 0
            scanned = 0

            sql = f"SELECT rowid, minis_ids_blob FROM {table}"
            if int(args.limit or 0) > 0:
                sql += f" LIMIT {int(args.limit)}"

            cur = conn.execute(sql)
            while True:
                rows = cur.fetchmany(5000)
                if not rows:
                    break
                for row in rows:
                    scanned += 1
                    old_blob = _as_bytes(row["minis_ids_blob"])
                    new_blob = _rotate_minis_blob(old_blob, maps)
                    if new_blob != old_blob:
                        updated += 1
                        total_updated += 1
                        if not args.dry_run:
                            conn.execute(
                                f"UPDATE {table} SET minis_ids_blob = ? WHERE rowid = ?",
                                (new_blob, int(row["rowid"])),
                            )
                            if int(args.commit_every or 0) > 0 and (updated % int(args.commit_every)) == 0:
                                conn.commit()
                if scanned % 50000 == 0:
                    print(f"[{table}] processed {scanned} rows (updated {updated})...")

            if not args.dry_run:
                conn.commit()

            print(f"[{table}] done: processed {scanned} rows, updated {updated} rows.")

        print(f"\nDone. Total updated rows: {total_updated}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

