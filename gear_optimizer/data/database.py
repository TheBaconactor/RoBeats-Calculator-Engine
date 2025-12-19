"""
Database operations for the gear optimizer.
Handles all SQLite interactions for loadout persistence and retrieval.
"""
import hashlib
import json
import os
import sqlite3
from ..core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS, DB_FILE


def get_evolution_db_path():
    """
    Return the configured evolution DB location (env override supported).

    Returns:
        str: Path to evolution database file
    """
    env_path = os.getenv("EVOLUTION_DB_PATH", "")
    return env_path if env_path else PATHS.evolution_db_default


def get_db_connection(db_path=None):
    """
    Create a SQLite connection with optimized settings.

    Args:
        db_path: Optional database path (defaults to evolution DB)

    Returns:
        sqlite3.Connection: Database connection with WAL mode enabled
    """
    if db_path is None:
        db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    """
    Initialize the SQLite database schema if it doesn't exist.

    Storage optimization: gear_json and minis_json store only names (not full stats)
    as a JSON array of strings, e.g. ["Gear1", "Gear2", ...]. Full stats are looked
    up from Gears.csv/Minis.csv when loading. This reduces storage by ~90%.
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0,
                last_updated REAL
            );
            CREATE TABLE IF NOT EXISTS loadouts (
                song_name TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER DEFAULT 0,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, loadout_hash),
                FOREIGN KEY (song_name) REFERENCES songs(name)
            );
            CREATE INDEX IF NOT EXISTS idx_loadouts_score ON loadouts (song_name, score DESC);
        """)
        conn.commit()
    finally:
        conn.close()


def _compact_gear_for_db(gear_list):
    """
    Convert gear list to compact storage format (names only).
    Handles both dicts and strings.

    Args:
        gear_list: List of gear items (dicts or strings)

    Returns:
        list: List of gear names
    """
    if not gear_list:
        return []
    result = []
    for g in gear_list:
        if isinstance(g, dict):
            name = g.get("Name", "")
        else:
            name = str(g) if g else ""
        if name:
            result.append(name)
    return result


def _compact_minis_for_db(mini_list):
    """
    Convert mini list to compact storage format (names only).
    Handles both dicts and strings.

    Args:
        mini_list: List of mini items (dicts or strings)

    Returns:
        list: List of mini names
    """
    if not mini_list:
        return []
    result = []
    for m in mini_list:
        if isinstance(m, dict):
            name = m.get("Name", "")
        else:
            name = str(m) if m else ""
        if name:
            result.append(name)
    return result


def _expand_gear_from_db(gear_names, gears_by_name):
    """
    Expand gear names back to full stat dictionaries.

    Args:
        gear_names: List of gear names
        gears_by_name: Lookup dict mapping names to full gear dicts

    Returns:
        list: List of full gear dictionaries
    """
    if not gear_names or not gears_by_name:
        return []
    return [gears_by_name.get(name, {"Name": name}) for name in gear_names]


def _expand_minis_from_db(mini_names, minis_by_name):
    """
    Expand mini names back to full stat dictionaries.

    Args:
        mini_names: List of mini names
        minis_by_name: Lookup dict mapping names to full mini dicts

    Returns:
        list: List of full mini dictionaries
    """
    if not mini_names or not minis_by_name:
        return []
    return [minis_by_name.get(name, {"Name": name}) for name in mini_names]


def get_loadout_hash(gear_list, mini_list):
    """
    Generate a unique hash for a loadout (gear + minis).
    Sorts items by name to ensure consistent hashing regardless of order.
    Handles both dicts (with 'Name' key) and plain strings.

    Args:
        gear_list: List of gear items
        mini_list: List of mini items

    Returns:
        str: MD5 hash of the loadout
    """
    # Extract names, handling both dict and string inputs
    gear_names = []
    for g in (gear_list or []):
        if isinstance(g, dict):
            gear_names.append(g.get("Name", ""))
        else:
            gear_names.append(str(g) if g else "")
    gear_names = sorted([n for n in gear_names if n])

    mini_names = []
    for m in (mini_list or []):
        if isinstance(m, dict):
            mini_names.append(m.get("Name", ""))
        else:
            mini_names.append(str(m) if m else "")
    mini_names = sorted([n for n in mini_names if n])

    # Create a string representation
    payload = f"GEAR:{'|'.join(gear_names)}::MINIS:{'|'.join(mini_names)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _get_overflow_from_details(details):
    """
    Extract overflow value from details dict.

    Args:
        details: Details dictionary containing GemCounts

    Returns:
        int: Overflow value (Element), or 0 if not found
    """
    if not details:
        return 0
    gem_counts = details.get("GemCounts", {})
    if not gem_counts:
        return 0
    return gem_counts.get("Element", 0)


def _deduplicate_entries(entries):
    """
    Deduplicate entries before database insertion.

    Rules:
    1. Exact same loadout hash + score → keep first
    2. Same score + same loadout → keep first
    3. Same score + different gem allocation → keep one with higher overflow

    Args:
        entries: List of entry dicts

    Returns:
        list: Deduplicated entries
    """
    if not entries:
        return []

    # Group by (score, loadout_hash)
    score_hash_groups = {}
    for entry in entries:
        score = entry.get("score", 0)
        gear = entry.get("gear", [])
        minis = entry.get("minis", [])
        loadout_hash = get_loadout_hash(gear, minis)
        key = (score, loadout_hash)

        if key not in score_hash_groups:
            score_hash_groups[key] = []
        score_hash_groups[key].append(entry)

    deduplicated = []
    for (score, loadout_hash), group in score_hash_groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
        else:
            # Multiple entries with same score and loadout - keep one with highest overflow AND FG score
            best_entry = max(group, key=lambda e: (
                _get_overflow_from_details(e.get("details", {})),
                e.get("fg_score", 0)
            ))
            deduplicated.append(best_entry)

    return deduplicated


def _deduplicate_db_loadouts(conn, song_name):
    """
    Remove duplicate loadouts from database for a specific song.

    Identifies and removes tie-breakers:
    - Same score with exact same loadout hash (shouldn't happen but just in case)
    - Same score with different loadouts (keep one with highest overflow)

    Args:
        conn: SQLite connection
        song_name: Name of the song to deduplicate

    Returns:
        int: Number of duplicates removed
    """
    try:
        # Find all loadouts grouped by score
        cursor = conn.execute("""
            SELECT loadout_hash, score, details_json, fg_score
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC, fg_score DESC
        """, (song_name,))

        rows = cursor.fetchall()
        if not rows:
            return 0

        # Group by score
        score_groups = {}
        for row in rows:
            score = row["score"]
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append({
                "loadout_hash": row["loadout_hash"],
                "score": score,
                "details_json": row["details_json"],
                "fg_score": row["fg_score"],
            })

        hashes_to_delete = set()

        for score, group in score_groups.items():
            if len(group) <= 1:
                continue  # No duplicates at this score level

            # Multiple loadouts with same score - keep best one(s) based on overflow and fg_score
            loadouts_with_overflow = []
            for loadout in group:
                details = {}
                if loadout["details_json"]:
                    try:
                        details = json.loads(loadout["details_json"])
                    except Exception:
                        pass
                overflow = _get_overflow_from_details(details)
                loadouts_with_overflow.append({
                    **loadout,
                    "overflow": overflow,
                })

            # Sort by overflow (descending), then fg_score (descending)
            loadouts_with_overflow.sort(key=lambda x: (x["overflow"], x["fg_score"]), reverse=True)

            # Keep the best one, mark rest for deletion
            for loadout in loadouts_with_overflow[1:]:
                hashes_to_delete.add(loadout["loadout_hash"])

        # Delete duplicates
        if hashes_to_delete:
            placeholders = ",".join("?" * len(hashes_to_delete))
            conn.execute(f"""
                DELETE FROM loadouts
                WHERE song_name = ? AND loadout_hash IN ({placeholders})
            """, (song_name, *hashes_to_delete))
            return len(hashes_to_delete)

        return 0
    except Exception as e:
        print(f"[DB] Error deduplicating loadouts: {e}")
        return 0


def save_loadout_to_db(song_name, score, fg_score, gear, minis, details, force_data=None):
    """
    Save a loadout to the database.
    Enforces the per-song loadout limit.

    Storage is optimized: only gear/mini names are stored, not full stats.

    Args:
        song_name: Name of the song
        score: Total score
        fg_score: Full gems score
        gear: List of gear items
        minis: List of mini items
        details: Details dictionary
        force_data: Optional force greats data
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        loadout_hash = get_loadout_hash(gear, minis)

        # Compact storage: store only names, not full stat dictionaries
        gear_names = _compact_gear_for_db(gear)
        mini_names = _compact_minis_for_db(minis)

        # Upsert the loadout (preserve better FG score)
        conn.execute("""
            INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                fg_score = MAX(fg_score, excluded.fg_score),
                gear_json = excluded.gear_json,
                minis_json = excluded.minis_json,
                details_json = CASE WHEN excluded.score > score THEN excluded.details_json ELSE details_json END,
                force_details_json = CASE 
                    WHEN excluded.fg_score > fg_score THEN excluded.force_details_json 
                    ELSE force_details_json 
                END,
                timestamp = strftime('%s', 'now')
        """, (
            song_name,
            loadout_hash,
            score,
            fg_score,
            json.dumps(gear_names, separators=(',', ':')),
            json.dumps(mini_names, separators=(',', ':')),
            json.dumps(details, separators=(',', ':')) if details else None,
            json.dumps(force_data, separators=(',', ':')) if force_data else None,
        ))

        # Update the song's best score if this is better
        conn.execute("""
            INSERT INTO songs (name, best_score)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                best_score = MAX(best_score, excluded.best_score),
                last_updated = strftime('%s', 'now')
        """, (song_name, score))

        # Update best FG score if provided
        try:
            fg_val = int(fg_score) if fg_score is not None else 0
        except Exception:
            fg_val = 0
        if fg_val:
            conn.execute("""
                INSERT INTO songs (name, best_fg_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, fg_val))

        # Enforce limit: Keep top N by score and preserve best FG entry
        cursor = conn.execute("SELECT COUNT(*) FROM loadouts WHERE song_name = ?", (song_name,))
        count = cursor.fetchone()[0]

        if count > LOADOUTS_PER_SONG_LIMIT:
            # Delete the worst ones, keeping top limit by score AND always keep the best FG entry (if any)
            conn.execute("""
                DELETE FROM loadouts
                WHERE song_name = ?
                AND loadout_hash NOT IN (
                    -- keep top N by score
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY score DESC
                    LIMIT ?
                )
                AND loadout_hash NOT IN (
                    -- keep best FG entry if it exists
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY fg_score DESC
                    LIMIT 1
                )
            """, (song_name, song_name, LOADOUTS_PER_SONG_LIMIT, song_name))

        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving loadout: {e}")
    finally:
        conn.close()


def save_loadouts_batch(song_name, entries):
    """
    Batch insert/update loadouts for a song in a single transaction.

    Implements tie-breaker prevention:
    - Deduplicates exact same loadouts with same score
    - For same score with different gem allocations, keeps entry with highest overflow

    Args:
        song_name: Name of the song
        entries: List of dicts with keys: score, fg_score, gear, minis, details, force
    """
    if not entries:
        return

    # Deduplicate entries before DB insertion
    deduplicated_entries = _deduplicate_entries(entries)

    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    best_score_max = None
    best_fg_max = None
    try:
        # Relax sync during batch for throughput; WAL is already enabled in get_db_connection
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass

        for entry in deduplicated_entries:
            score = entry.get("score", 0)
            fg_score = entry.get("fg_score", 0)
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")

            loadout_hash = get_loadout_hash(gear, minis)
            gear_names = _compact_gear_for_db(gear)
            mini_names = _compact_minis_for_db(minis)

            # Upsert loadout (preserve better FG score)
            conn.execute("""
                INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    details_json = CASE WHEN excluded.score > score THEN excluded.details_json ELSE details_json END,
                    force_details_json = CASE 
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json 
                        ELSE force_details_json 
                    END,
                    timestamp = strftime('%s', 'now')
            """, (
                song_name,
                loadout_hash,
                score,
                fg_score,
                json.dumps(gear_names, separators=(',', ':')),
                json.dumps(mini_names, separators=(',', ':')),
                json.dumps(details, separators=(',', ':')) if details else None,
                json.dumps(force_data, separators=(',', ':')) if force_data else None,
            ))

            if best_score_max is None or score > best_score_max:
                best_score_max = score
            if fg_score and (best_fg_max is None or fg_score > best_fg_max):
                best_fg_max = fg_score

        if best_score_max is not None:
            conn.execute("""
                INSERT INTO songs (name, best_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_score = MAX(best_score, excluded.best_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, best_score_max))

        if best_fg_max:
            conn.execute("""
                INSERT INTO songs (name, best_fg_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, best_fg_max))

        # Deduplicate existing DB entries after batch insert
        _deduplicate_db_loadouts(conn, song_name)

        cursor = conn.execute("SELECT COUNT(*) FROM loadouts WHERE song_name = ?", (song_name,))
        count = cursor.fetchone()[0]
        if count > LOADOUTS_PER_SONG_LIMIT:
            conn.execute("""
                DELETE FROM loadouts
                WHERE song_name = ?
                AND loadout_hash NOT IN (
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY score DESC
                    LIMIT ?
                )
                AND loadout_hash NOT IN (
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY fg_score DESC
                    LIMIT 1
                )
            """, (song_name, song_name, LOADOUTS_PER_SONG_LIMIT, song_name))

        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving batch loadouts: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.execute("PRAGMA synchronous=FULL;")
        except Exception:
            pass
        conn.close()


def get_best_loadouts(song_name, limit=LOADOUTS_PER_SONG_LIMIT, gears_by_name=None, minis_by_name=None):
    """
    Retrieve the top N loadouts for a song to seed the GA.

    Storage format: gear_json and minis_json are JSON arrays of name strings.
    If gears_by_name/minis_by_name are provided, expands names to full stat dicts.

    Args:
        song_name: Name of the song
        limit: Maximum number of loadouts to retrieve
        gears_by_name: Optional dict mapping gear names to full dicts
        minis_by_name: Optional dict mapping mini names to full dicts

    Returns:
        list: List of loadout dictionaries
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []

    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC
            LIMIT ?
        """, (song_name, limit))

        results = []
        for row in cursor:
            gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
            mini_names = json.loads(row["minis_json"]) if row["minis_json"] else []
            force_block = json.loads(row["force_details_json"]) if row["force_details_json"] else None

            # Expand names to full dicts if lookup provided
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups

            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names

            results.append({
                "score": row["score"],
                "fg_score": row["fg_score"],
                "gear": gear_data,
                "minis": minis_data,
                "details": json.loads(row["details_json"]) if row["details_json"] else {},
                "force": force_block if isinstance(force_block, dict) else None,
            })
        return results
    except Exception as e:
        print(f"[DB] Error retrieving loadouts: {e}")
        return []
    finally:
        conn.close()
