"""
Leaderboard reads: top base + FG loadouts for a song, used to seed the GA.
"""
import os
import json
import sqlite3
import warnings
import logging
from typing import Any, Dict, List, Optional
from ...core.constants import LOADOUTS_PER_SONG_LIMIT
from ...core.team_buff import normalize_team_buff, team_buff_query_values
from ..database_codecs import (
    _json_loads,
    _strip_computed_details_fields,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
)
from ..piece_encoding_store import _load_piece_name_encoding_maps
from ..loadout_equivalence import (
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    representative_mini_names,
)
from gear_optimizer.core.parsing import env_get
from .connection import get_evolution_db_path, get_db_connection_cached
from .loadout_io import _expand_gear_from_db, _expand_minis_from_db

logger = logging.getLogger(__name__)


def get_best_loadouts(
    song_name: str,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    gears_by_name: Optional[Dict[str, Any]] = None,
    minis_by_name: Optional[Dict[str, Any]] = None,
    team_buff: str = "T5",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top N loadouts for a song to seed the GA.
    Storage format:
    - gear_ids_blob: varint-packed list of encoding-table IDs (decoded via `gear_name_encoding`)
    - minis_ids_blob: varint-packed groups of IDs with 0 separators (decoded via `mini_name_encoding`)
    If gears_by_name/minis_by_name are provided, expands representative names to full stat dicts.
    Args:
        song_name: Name of the song
        limit: Maximum number of loadouts to retrieve
        gears_by_name: Optional dict mapping gear names to full dicts
        minis_by_name: Optional dict mapping mini names to full dicts
        team_buff: TeamBuff tier to seed from (defaults to T5)
    Returns:
        list: List of loadout dictionaries
    """
    # Resolve monkeypatchable names through the package facade at call time so
    # tests that patch `gear_optimizer.data.database.<name>` are honored.
    from gear_optimizer.data import database as _db
    resolved_db_path = str(db_path or get_evolution_db_path() or "").strip()
    if not resolved_db_path or not os.path.exists(resolved_db_path):
        return []
    song_name = str(song_name or "").strip()
    team_buff = normalize_team_buff(team_buff, default="T5")
    query_team_buffs = team_buff_query_values(team_buff, default=team_buff)
    strict_seed_hash = str(env_get("DB_STRICT_SEED_HASH", "0") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    conn = get_db_connection_cached(resolved_db_path)
    try:
        results: list[dict[str, Any]] = []
        by_hash: dict[str, dict[str, Any]] = {}
        encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
        def _materialize_common(row) -> tuple[str, list[str], list[list[str]], list[str], dict[str, Any], dict | None]:
            loadout_hash = str(row["loadout_hash"])
            gear_names: list[str] = []
            try:
                gear_ids_blob = row["gear_ids_blob"]
            except Exception as e:
                logger.warning(f"database:_materialize_common: {e}")
                gear_ids_blob = None
            if gear_ids_blob:
                ids = _unpack_id_list(gear_ids_blob)
                if ids:
                    gear_names = [str(encoding_maps.gear_id_to_name.get(int(i), "") or "") for i in ids]
                    gear_names = [n for n in gear_names if n]
            mini_groups: list[list[str]] = []
            try:
                minis_ids_blob = row["minis_ids_blob"]
            except Exception as e:
                logger.warning(f"database:_materialize_common: {e}")
                minis_ids_blob = None
            if minis_ids_blob:
                id_groups = _unpack_id_groups(minis_ids_blob)
                if id_groups:
                    for g in id_groups:
                        names = [str(encoding_maps.mini_id_to_name.get(int(i), "") or "") for i in g]
                        names = [n for n in names if n]
                        if names:
                            mini_groups.append(names)
            mini_names = representative_mini_names(mini_groups)
            details = _json_loads(row["details_json"]) if row["details_json"] else {}
            details = _unpack_stats_after_load(details)
            details = _strip_computed_details_fields(details)
            if strict_seed_hash:
                try:
                    p_color, s_color, sel_color = extract_song_colors(details)
                    if p_color or s_color:
                        lookup = minis_by_name or _db.get_minis_by_name_cached()
                        mini_sigs = [
                            effective_mini_signature_for_name(n, lookup, p_color, s_color, sel_color)
                            for n in mini_names
                        ]
                        expected = effective_loadout_hash_from_names(gear_names, mini_sigs)
                    else:
                        expected = _db._loadout_hash_from_names(gear_names, mini_names)
                    if expected and str(expected) != str(loadout_hash):
                        warnings.warn(
                            f"[DB] Loadout hash mismatch (seed): song={song_name!r} team_buff={team_buff!r} "
                            f"stored={loadout_hash} expected={expected}",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                except Exception as e:
                    logger.warning(f"database:_materialize_common: {e}")
            force_block = _json_loads(row["force_details_json"]) if row["force_details_json"] else None
            force_obj = force_block if isinstance(force_block, dict) else None
            if isinstance(force_obj, dict):
                force_obj = _strip_computed_details_fields(force_obj)
                nested = force_obj.get("details")
                if isinstance(nested, dict):
                    nested_out = _strip_computed_details_fields(nested)
                    if nested_out is not nested:
                        force_obj = dict(force_obj)
                        force_obj["details"] = nested_out
            return loadout_hash, gear_names, mini_groups, mini_names, details, force_obj
        def _expand_items(gear_names: list[str], mini_names: list[str]):
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups
            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names
            return gear_data, minis_data
        query_placeholders = ",".join("?" for _ in query_team_buffs)
        cursor = conn.execute(
            f"""
            SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE song_name = ? AND UPPER(team_buff) IN ({query_placeholders})
            ORDER BY score DESC
            LIMIT ?
            """,
            (song_name, *query_team_buffs, limit),
        )
        for row in cursor:
            loadout_hash, gear_names, mini_groups, mini_names, details, force_obj = _materialize_common(row)
            if loadout_hash in by_hash:
                continue
            gear_data, minis_data = _expand_items(gear_names, mini_names)
            entry = {
                "loadout_hash": loadout_hash,
                "score": row["score"],
                "fg_score": row["fg_score"],
                "gear": gear_data,
                "minis": minis_data,
                "mini_groups": mini_groups,
                "details": details,
                "force": force_obj,
            }
            by_hash[loadout_hash] = entry
            results.append(entry)
        cursor = conn.execute(
            f"""
            SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM team_buff_fg_loadouts
            WHERE song_name = ? AND UPPER(team_buff) IN ({query_placeholders})
            ORDER BY fg_score DESC
            LIMIT ?
            """,
            (song_name, *query_team_buffs, limit),
        )
        for row in cursor:
            loadout_hash, gear_names, mini_groups, mini_names, details, force_obj = _materialize_common(row)
            gear_data, minis_data = _expand_items(gear_names, mini_names)
            fg_score = row["fg_score"]
            fg_base_score = row["score"]
            entry = by_hash.get(loadout_hash)
            if entry is None:
                entry = {
                    "loadout_hash": loadout_hash,
                    "score": row["score"],
                    "fg_score": fg_score,
                    "gear": gear_data,
                    "minis": minis_data,
                    "mini_groups": mini_groups,
                    "details": details,
                    "force": force_obj,
                }
                by_hash[loadout_hash] = entry
                results.append(entry)
                continue
            try:
                existing_fg = int(entry.get("fg_score", 0) or 0)
            except Exception as e:
                logger.warning(f"database:_expand_items: {e}")
                existing_fg = 0
            try:
                fg_i = int(fg_score or 0)
            except Exception as e:
                logger.warning(f"database:_expand_items: {e}")
                fg_i = 0
            if fg_i > existing_fg:
                entry["fg_score"] = fg_score
                entry["force"] = force_obj
                entry["fg_base_score"] = fg_base_score
            elif fg_i == existing_fg:
                if "fg_base_score" not in entry:
                    entry["fg_base_score"] = fg_base_score
                if entry.get("force") is None and force_obj is not None:
                    entry["force"] = force_obj
        return results
    except (sqlite3.Error, json.JSONDecodeError):
        raise
    finally:
        pass
