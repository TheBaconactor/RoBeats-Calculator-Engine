import json
import os
import sqlite3
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import _unpack_id_groups, _unpack_id_list, get_evolution_db_path


def _load_encoding_maps(conn: sqlite3.Connection):
    gear_id_to_name: dict[int, str] = {}
    mini_id_to_name: dict[int, str] = {}
    for table, out in (("gear_name_encoding", gear_id_to_name), ("mini_name_encoding", mini_id_to_name)):
        try:
            for r in conn.execute(f"SELECT id, name FROM {table}").fetchall():
                try:
                    i = int(r[0] if not isinstance(r, sqlite3.Row) else r["id"])
                    n = str(r[1] if not isinstance(r, sqlite3.Row) else r["name"]).strip()
                except Exception:
                    continue
                if i > 0 and n:
                    out[i] = n
        except sqlite3.Error:
            continue
    return gear_id_to_name, mini_id_to_name


def _decode_gear_names(blob: object, *, gear_id_to_name: dict[int, str]) -> list[str]:
    ids = _unpack_id_list(blob)
    names = [str(gear_id_to_name.get(int(i), "") or "").strip() for i in ids if int(i) > 0]
    return [n for n in names if n]


def _decode_mini_names(blob: object, *, mini_id_to_name: dict[int, str]) -> list[str]:
    groups = _unpack_id_groups(blob)
    out: list[str] = []
    for g in groups or []:
        if not g:
            continue
        names = [str(mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = [n for n in names if n]
        out.extend(names)
    return out


def find_songs_by_gear():
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    gear_query = "Bubble Wand"
    element_query = "Vibe"

    print("Searching for songs with 'nanobii' or 'Bubble' in the name...")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM songs WHERE name LIKE '%nanobii%' OR name LIKE '%Bubble%'")
    song_rows = cursor.fetchall()
    if song_rows:
        print("\nSong Name Matches:")
        for r in song_rows:
            print(f"- {r['name']}")
    else:
        print("\nNo song name matches found.")

    print(f"\nScanning loadouts for gear matching '{gear_query}' with element '{element_query}'...")

    gear_id_to_name, mini_id_to_name = _load_encoding_maps(conn)

    found_songs: set[str] = set()
    try:
        loadout_rows = cursor.execute(
            """
            SELECT song_name, gear_ids_blob, minis_ids_blob, details_json, score
            FROM team_buff_loadouts
            WHERE song_name IS NOT NULL AND song_name != ''
            """
        ).fetchall()
    except sqlite3.Error:
        loadout_rows = []

    for row in loadout_rows or []:
        song_name = str(row["song_name"] or "").strip()
        if not song_name:
            continue

        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
        except Exception:
            details = {}

        selected_element = str(details.get("SelectedElement", "") or "").strip()
        if element_query.lower() not in selected_element.lower():
            continue

        gear_names = _decode_gear_names(row["gear_ids_blob"], gear_id_to_name=gear_id_to_name)
        mini_names = _decode_mini_names(row["minis_ids_blob"], mini_id_to_name=mini_id_to_name)
        all_names = gear_names + mini_names

        if any(gear_query.lower() in n.lower() for n in all_names):
            found_songs.add(song_name)

    if found_songs:
        print(f"\nSongs in element '{element_query}' containing '{gear_query}':")
        for name in sorted(found_songs):
            print(f"- {name}")
    else:
        print(f"\nNo songs found in element '{element_query}' containing '{gear_query}'.")

    print("\nChecking loadouts for all 'nanobii' songs and 'BUBBLE TEA'...")
    cursor.execute(
        "SELECT song_name, details_json FROM team_buff_loadouts WHERE song_name LIKE '%nanobii%' OR song_name LIKE '%BUBBLE TEA%'"
    )
    nb_rows = cursor.fetchall()

    if nb_rows:
        seen_songs = set()
        for r in nb_rows:
            if r["song_name"] in seen_songs:
                continue
            seen_songs.add(r["song_name"])

            details = json.loads(r["details_json"]) if r["details_json"] else {}
            elem = details.get("SelectedElement", "Unknown")
            print(f"- {r['song_name']}: Element = {elem}")
    else:
        print("No loadouts found for nanobii or BUBBLE TEA.")

    exact_name = "nanobii's Bubble Wand"
    print(f"\nExact gear names matching '{exact_name}' (any element):")

    found_matches: list[str] = []
    for row in loadout_rows or []:
        song_name = str(row["song_name"] or "").strip()
        if not song_name:
            continue

        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
        except Exception:
            details = {}
        selected_element = str(details.get("SelectedElement", "") or "").strip() or "Unknown"

        gear_names = _decode_gear_names(row["gear_ids_blob"], gear_id_to_name=gear_id_to_name)
        mini_names = _decode_mini_names(row["minis_ids_blob"], mini_id_to_name=mini_id_to_name)
        all_names = gear_names + mini_names
        for n in all_names:
            if exact_name.lower() in str(n).lower():
                found_matches.append(f"{song_name} ({selected_element}) -> {n}")

    if found_matches:
        for m in sorted(found_matches):
            print(f"- {m}")
    else:
        print("(none)")

    conn.close()


if __name__ == "__main__":
    find_songs_by_gear()
