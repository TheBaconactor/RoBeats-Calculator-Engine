"""
Loadout persistence: batch writes into the tiered base/FG leaderboards.

`save_loadouts_batch` is the public single-transaction entry; it delegates to
`save_team_buff_loadouts_batch`, which owns the tier-partitioned write surface.
"""
import os
import sqlite3
import time
import warnings
import logging
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from ...core.fallback_monitor import warn_fallback
from ...core.gem_defs import fg_score_from_force
from ...core.parsing import env_flag
from ...core.team_buff import (
    canonicalize_team_buff,
    normalize_team_buff,
    team_buff_effect,
)
from ...core.types import PersistenceEntry
from ..database_fg_summary import (
    normalize_details_for_persistence as _normalize_details_for_persistence,
    repair_base_loadout_fg_summaries as _repair_base_loadout_fg_summaries,
)
from ..database_codecs import (
    _json_dumps_compact,
    _json_loads,
    _pack_id_groups,
    _pack_id_list,
    _pack_stats_for_storage,
    _strip_computed_details_fields,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
)
from ..piece_encoding_store import (
    _GEAR_NAME_ENCODING_TABLE,
    _MINI_NAME_ENCODING_TABLE,
    _insert_missing_piece_names,
    _load_piece_name_encoding_maps,
)
from ..loadout_equivalence import (
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    canonical_minis_groups_from_names,
    representative_mini_names,
    rotate_mini_groups_for_slot_display,
)
from ..mini_ascension import MINI_ASCENSION_CACHE_VERSION, materialize_minis_for_song
from gear_optimizer.core.parsing import env_get
from .connection import get_db_connection, get_evolution_db_path, get_db_connection_cached
from .songs import get_song_counters, _update_song_counters_in_transaction
from .loadout_io import _compact_gear_for_db, _compact_minis_for_db
from .force_normalize import (
    _get_overflow_from_details,
    _ensure_stats_in_details,
    _force_payload_base_score,
    _base_details_from_force_payload,
    _align_force_stats_with_persisted_loadout,
    _compact_force_details_for_storage,
    _coerce_db_int,
    _normalize_force_for_persistence,
    _normalize_force_base_score_for_persistence,
    _assert_force_score_pairing,
)
from ...helpers.song_helpers.fg_payload import strip_retired_fg_fields

logger = logging.getLogger(__name__)


def _is_lock_error(err: sqlite3.Error) -> bool:
    msg = str(err or "").lower()
    return (
        ("database is locked" in msg)
        or ("database is busy" in msg)
        or ("database table is locked" in msg)
    )


def _run_write_transaction(conn: sqlite3.Connection, operation: Callable[[], None]) -> None:
    """Run one exact write transaction with the established SQLite lock retry policy."""
    max_attempts = 6
    base_sleep_sec = 0.05
    for attempt in range(max_attempts):
        try:
            conn.execute("BEGIN IMMEDIATE")
            operation()
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            if _is_lock_error(exc) and attempt < (max_attempts - 1):
                sleep_sec = min(2.0, float(base_sleep_sec) * (2**attempt))
                time.sleep(max(0.0, sleep_sec))
                continue
            raise
        except BaseException:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            raise


def configure_persistent_writer_connection(conn: sqlite3.Connection) -> None:
    """Apply the established write PRAGMA once, before any writer transaction starts."""
    if conn.in_transaction:
        raise RuntimeError("Cannot configure SQLite writer connection during a transaction")
    conn.execute("PRAGMA synchronous=NORMAL;")


def _loadout_score_maxima(entries: Sequence[Mapping[str, Any]]) -> tuple[int | None, int | None]:
    best_score_max = None
    best_fg_max = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        score = _coerce_db_int(entry.get("score", 0))
        fg_score = _coerce_db_int(entry.get("fg_score", 0))
        fg_base_score = score
        try:
            raw_fg_base = entry.get("fg_base_score")
        except Exception as e:
            logger.warning(f"database:_coerce_db_int: {e}")
            raw_fg_base = None
        if raw_fg_base is not None:
            fg_base_score = _coerce_db_int(raw_fg_base)
            if fg_base_score <= 0:
                fg_base_score = score
        force_data = entry.get("force")
        if fg_score <= 0 and force_data is not None:
            fg_score = fg_score_from_force(force_data)
        if force_data is not None:
            force_base_score = _force_payload_base_score(force_data)
            if force_base_score > 0:
                fg_base_score = force_base_score
        if best_score_max is None or score > best_score_max:
            best_score_max = score
        if (
            force_data is not None
            and fg_score > fg_base_score
            and _base_details_from_force_payload(entry.get("details", {}), force_data)
            and (best_fg_max is None or fg_score > best_fg_max)
        ):
            best_fg_max = fg_score
    return best_score_max, best_fg_max


def _save_loadouts_batch_in_transaction(
    conn: sqlite3.Connection,
    song_name: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    db_path: str,
    team_buff: str,
    preserve_attempt_meta: bool,
) -> None:
    updated_at = time.time()
    best_score_max, best_fg_max = _loadout_score_maxima(entries)
    save_team_buff_loadouts_batch(
        song_name,
        team_buff,
        entries,
        conn=conn,
        commit=False,
        db_path=db_path,
        preserve_attempt_meta=bool(preserve_attempt_meta),
    )
    if best_score_max is not None:
        conn.execute(
            """
            INSERT INTO songs (name, best_score, last_updated) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                best_score = MAX(best_score, excluded.best_score),
                last_updated = excluded.last_updated
            """,
            (song_name, best_score_max, updated_at),
        )
    if best_fg_max:
        conn.execute(
            """
            INSERT INTO songs (name, best_fg_score, last_updated) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                last_updated = excluded.last_updated
            """,
            (song_name, best_fg_max, updated_at),
        )


def save_loadouts_batch(
    song_name: str,
    entries: List[PersistenceEntry],
    *,
    db_path: Optional[str] = None,
    team_buff: str = "T5",
    preserve_attempt_meta: bool = False,
) -> None:
    """Batch insert/update loadouts for one song in one transaction."""
    if not entries:
        return
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    team_buff = normalize_team_buff(team_buff, default="T5")
    resolved_db_path = str(db_path or get_evolution_db_path())
    conn = get_db_connection(resolved_db_path)
    try:
        configure_persistent_writer_connection(conn)
        _run_write_transaction(
            conn,
            lambda: _save_loadouts_batch_in_transaction(
                conn,
                song_name,
                entries,
                db_path=resolved_db_path,
                team_buff=team_buff,
                preserve_attempt_meta=bool(preserve_attempt_meta),
            ),
        )
    finally:
        conn.close()


def _normalize_db_path(db_path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(str(db_path))))


def _resolve_connection_db_path(conn: sqlite3.Connection, db_path: Optional[str]) -> str:
    rows = conn.execute("PRAGMA database_list").fetchall()
    connection_path = ""
    for row in rows:
        name = row[1] if not isinstance(row, sqlite3.Row) else row["name"]
        if str(name) != "main":
            continue
        connection_path = str(row[2] if not isinstance(row, sqlite3.Row) else row["file"] or "")
        break
    if not connection_path:
        raise ValueError("Optimizer persistence requires a file-backed SQLite connection")
    resolved_connection_path = _normalize_db_path(connection_path)
    if db_path is not None and _normalize_db_path(str(db_path)) != resolved_connection_path:
        raise ValueError("Optimizer persistence db_path does not match the supplied SQLite connection")
    return resolved_connection_path


def _validate_optimizer_entry_integers(entries: Sequence[Mapping[str, Any]]) -> None:
    """Fail loudly on malformed optimizer-owned score fields before persistence."""
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise TypeError(f"Optimizer persistence entry {index} must be a mapping")
        for field in ("score", "fg_score", "fg_base_score"):
            if field not in entry:
                continue
            try:
                int(entry.get(field) or 0)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Optimizer persistence entry {index} has invalid {field}") from exc


def save_optimizer_song_result(
    song_name: str,
    entries: List[PersistenceEntry],
    *,
    processed_run: bool,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
    team_buff: str = "T5",
) -> None:
    """Atomically persist one optimizer result, including its attempt counters."""
    song_name = str(song_name or "").strip()
    if not song_name:
        raise ValueError("Optimizer persistence requires a non-empty song key")
    entries = entries or []
    _validate_optimizer_entry_integers(entries)
    team_buff = normalize_team_buff(team_buff, default="T5")
    own_conn = conn is None
    if conn is None:
        resolved_db_path = str(db_path or get_evolution_db_path())
        conn = get_db_connection(resolved_db_path)
        try:
            configure_persistent_writer_connection(conn)
        except BaseException:
            conn.close()
            raise
    else:
        resolved_db_path = _resolve_connection_db_path(conn, db_path)

    def _save_attempt() -> None:
        prev_life, prev_attempts, prev_best_score, prev_best_fg = get_song_counters(song_name, conn=conn)
        run_score, run_best_fg = _loadout_score_maxima(entries)
        record_improved = (int(run_score or 0) > int(prev_best_score or 0)) or (
            int(run_best_fg or 0) > int(prev_best_fg or 0)
        )

        if processed_run:
            attempt_lifetime = int(prev_life or 0) + 1
            attempts_first = (
                1 if record_improved else (int(prev_attempts or 0) + 1 if int(prev_attempts or 0) else 1)
            )
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                details = entry.get("details") or {}
                if not isinstance(details, dict):
                    details = {}
                details = dict(details)
                details["attempt_lifetime"] = attempt_lifetime
                details["attempts_first"] = attempts_first
                entry["details"] = details

        if entries:
            _save_loadouts_batch_in_transaction(
                conn,
                song_name,
                entries,
                db_path=resolved_db_path,
                team_buff=team_buff,
                preserve_attempt_meta=False,
            )
        _update_song_counters_in_transaction(
            conn,
            song_name,
            processed_run=processed_run,
            record_improved=record_improved,
        )

    try:
        _run_write_transaction(conn, _save_attempt)
    finally:
        if own_conn:
            conn.close()


def save_team_buff_loadouts_batch(
    song_name: str,
    team_buff: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    conn: Optional[sqlite3.Connection] = None,
    commit: bool = True,
    db_path: Optional[str] = None,
    preserve_attempt_meta: bool = False,
) -> None:
    """
    Batch insert/update tiered leaderboards for a song in a single transaction.
    Mirrors `save_loadouts_batch`, but partitions by `team_buff` (`NONE/T1/T5/T10/T20/T50/T51`) into:
    - team_buff_loadouts (base leaderboard for that tier)
    - team_buff_fg_loadouts (FG leaderboard for that tier; FG strictly beats base)
    """
    # Resolve monkeypatchable names through the package facade at call time so
    # tests that patch `gear_optimizer.data.database.<name>` are honored.
    from gear_optimizer.data import database as _db
    song_name = str(song_name or "").strip()
    team_buff = canonicalize_team_buff(team_buff)
    if not song_name or not team_buff or not entries:
        return
    timing = env_flag("DB_TIMING")
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(env_get("DB_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception as e:
        logger.warning(f"database:save_team_buff_loadouts_batch: {e}")
        timing_threshold_ms = 50.0
    def _log_timing(label: str, dt_sec: float) -> None:
        if not timing:
            return
        ms = float(dt_sec) * 1000.0
        if ms < timing_threshold_ms:
            return
        print(f"[DB][TIMING] {song_name} {team_buff} {label}={ms:.1f}ms")
    _t0 = time.perf_counter()
    minis_by_name = _db.get_minis_by_name_cached()
    gears_by_name = _db.get_gears_by_name_cached()
    # LIFETIME INVARIANT for every id()-keyed memo in this function
    # (entry_color_cache, entry_names_cache, effective_cache_by_entry_id):
    # they are call-local and `entries` holds strong references to every entry
    # for the whole call, so an id() can never be reused while cached. If a
    # refactor ever streams/spills entries instead of holding the full list,
    # these must switch to content keys.
    entry_color_cache: Dict[int, tuple[str, str, str]] = {}
    def _extract_entry_colors(entry: Mapping[str, Any]) -> tuple[str, str, str]:
        entry_id = int(id(entry))
        cached = entry_color_cache.get(entry_id)
        if cached is not None:
            return cached
        p_color, s_color, sel_color = extract_song_colors(entry.get("details", {}))
        if p_color or s_color:
            out = (p_color, s_color, sel_color)
            entry_color_cache[entry_id] = out
            return out
        force_data = entry.get("force")
        if isinstance(force_data, dict):
            nested = force_data.get("details")
            if isinstance(nested, dict):
                p2, s2, sel2 = extract_song_colors(nested)
                if p2 or s2:
                    out = (p2, s2, sel2 or sel_color)
                    entry_color_cache[entry_id] = out
                    return out
            p2, s2, sel2 = extract_song_colors(force_data)
            if p2 or s2:
                out = (p2, s2, sel2 or sel_color)
                entry_color_cache[entry_id] = out
                return out
        out = (p_color, s_color, sel_color)
        entry_color_cache[entry_id] = out
        return out
    song_color_fallback: Optional[tuple[str, str, str]] = None
    for entry in entries:
        p_color, s_color, sel_color = _extract_entry_colors(entry)
        if p_color or s_color:
            song_color_fallback = (p_color, s_color, sel_color)
            break
    if song_color_fallback is None:
        db_path_lookup = str(db_path or get_evolution_db_path())
        try:
            lookup_conn = get_db_connection_cached(db_path_lookup)
            rows = lookup_conn.execute(
                """
                SELECT details_json
                FROM team_buff_loadouts
                WHERE song_name = ? AND team_buff = ? AND details_json IS NOT NULL
                ORDER BY score DESC, timestamp DESC
                LIMIT 25
                """,
                (song_name, team_buff),
            ).fetchall()
            for row in rows:
                try:
                    details_row = _json_loads(row["details_json"]) if row["details_json"] else {}
                    details_row = _unpack_stats_after_load(details_row)
                except Exception as e:
                    logger.warning(f"database:_extract_entry_colors: {e}")
                    continue
                p_color, s_color, sel_color = extract_song_colors(details_row)
                if p_color or s_color:
                    song_color_fallback = (p_color, s_color, sel_color)
                    warn_fallback(
                        "db.song_color_fallback",
                        "using existing DB details colors as fallback for effective mini hashing",
                        context={
                            "song_name": song_name,
                            "team_buff": team_buff,
                            "primary": p_color,
                            "secondary": s_color,
                        },
                        fatal=False,
                    )
                    break
        except sqlite3.Error:
            pass
    song_aware_minis_cache: Dict[tuple[str, str], Dict[str, dict]] = {}
    def _song_aware_minis_by_name(p_color: str, s_color: str) -> Dict[str, dict]:
        source = minis_by_name if isinstance(minis_by_name, dict) else {}
        if not source:
            return {}
        primary = str(p_color or "").strip()
        secondary = str(s_color or "").strip()
        if not primary and not secondary:
            return source
        key = (primary, secondary)
        cached = song_aware_minis_cache.get(key)
        if cached is not None:
            return cached
        _minis, by_name, _context = materialize_minis_for_song(
            minis_by_name=source,
            song_name=song_name,
            primary_color=primary,
            secondary_color=secondary,
        )
        song_aware_minis_cache[key] = by_name
        return by_name
    mini_sig_cache: Dict[tuple[str, str, str, str], tuple[Any, ...]] = {}
    def _mini_signature_cached(name: str, p_color: str, s_color: str, sel_color: str) -> tuple[Any, ...]:
        key = (str(name or ""), str(p_color or ""), str(s_color or ""), str(sel_color or ""))
        sig = mini_sig_cache.get(key)
        if sig is not None:
            return sig
        sig = effective_mini_signature_for_name(name, _song_aware_minis_by_name(p_color, s_color), p_color, s_color, sel_color)
        mini_sig_cache[key] = sig
        return sig
    entry_names_cache: Dict[int, tuple[list[str], list[str]]] = {}
    def _compact_entry_names(entry: Mapping[str, Any]) -> tuple[list[str], list[str]]:
        entry_id = int(id(entry))
        cached = entry_names_cache.get(entry_id)
        if cached is not None:
            return cached
        out = (_compact_gear_for_db(entry.get("gear", [])), _compact_minis_for_db(entry.get("minis", [])))
        entry_names_cache[entry_id] = out
        return out
    def _effective_hash_for_entry(
        entry: Mapping[str, Any],
    ) -> Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]:
        gear_names_local, mini_names_local = _compact_entry_names(entry)
        p_color, s_color, sel_color = _extract_entry_colors(entry)
        if (not p_color and not s_color) and song_color_fallback is not None:
            p_color, s_color, fallback_sel = song_color_fallback
            if not sel_color:
                sel_color = fallback_sel or p_color or s_color
        if not p_color and not s_color:
            return None
        if not sel_color:
            sel_color = p_color or s_color
        mini_sigs_local = [_mini_signature_cached(n, p_color, s_color, sel_color) for n in mini_names_local]
        return (
            effective_loadout_hash_from_names(gear_names_local, mini_sigs_local),
            mini_sigs_local,
            p_color,
            s_color,
            sel_color,
        )
    _t_dedup0 = time.perf_counter()
    dedup_groups: Dict[tuple[int, str], list[Mapping[str, Any]]] = {}
    effective_cache_by_entry_id: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}
    for entry in entries:
        entry_id = int(id(entry))
        eff = effective_cache_by_entry_id.get(entry_id)
        if entry_id not in effective_cache_by_entry_id:
            eff = _effective_hash_for_entry(entry)
            effective_cache_by_entry_id[entry_id] = eff
        if eff is None:
            warn_fallback(
                "db.hash.raw_names",
                "missing song color metadata; using raw name hash fallback",
                context={"song_name": song_name, "team_buff": team_buff},
                fatal=False,
            )
            gear_names_local, mini_names_local = _compact_entry_names(entry)
            h = _db._loadout_hash_from_names(gear_names_local, mini_names_local)
        else:
            h = eff[0]
        key = (int(entry.get("score", 0) or 0), str(h))
        dedup_groups.setdefault(key, []).append(entry)
    deduplicated_entries: list[Mapping[str, Any]] = []
    for (_score, _h), group in dedup_groups.items():
        if len(group) == 1:
            deduplicated_entries.append(group[0])
            continue
        try:
            best_entry = max(
                group, key=lambda e: (_get_overflow_from_details(e.get("details", {})), e.get("fg_score", 0))
            )
            deduplicated_entries.append(best_entry)
        except Exception as e:
            logger.warning(f"database:_effective_hash_for_entry: {e}")
            deduplicated_entries.append(group[0])
    _log_timing("dedup_entries", time.perf_counter() - _t_dedup0)
    def _can_recompute_stats_for_persistence(gear_names_local: list[str], mini_names_local: list[str]) -> bool:
        gear_ok = (not gear_names_local) or (
            isinstance(gears_by_name, dict)
            and bool(gears_by_name)
            and all((not n or n in gears_by_name) for n in gear_names_local)
        )
        mini_ok = (not mini_names_local) or (
            isinstance(minis_by_name, dict)
            and bool(minis_by_name)
            and all((not n or n in minis_by_name) for n in mini_names_local)
        )
        return bool(gear_ok and mini_ok)
    def _details_with_representative_stats(
        details_obj: Any,
        *,
        gear_names_local: list[str],
        mini_names_local: list[str],
        team_color: str,
    ) -> dict:
        """
        Recompute `details["Stats"]` deterministically from:
        - canonical representative gear + mini names
        - persisted gem counts (GemCounts + FT/FF)
        - TeamBuff tier effect for correct frontend display
        This prevents persisting:
        - mini-variant off-element drift (equivalence-group representatives),
        - config-tainted Stats snapshots that don't match legacy DB semantics.
        """
        if not isinstance(details_obj, dict):
            details_obj = {}
        try:
            from gear_optimizer.core.stats_calculator import compute_full_stats
        except Exception as e:
            logger.warning(f"database:_recompute_stats_in_details_for_persistence: {e}")
            return details_obj
        base_stats = {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 0,
        }
        buff_tier = str(team_buff or "").strip().upper()
        buff_color = str(team_color or "").strip()
        if not buff_color:
            buff_color = str(
                details_obj.get("PrimaryColor")
                or details_obj.get("Primary Color")
                or details_obj.get("SelectedElement")
                or details_obj.get("Selected Element")
                or ""
            ).strip()
        for stat_name, delta in team_buff_effect(buff_tier, buff_color).items():
            base_stats[stat_name] = int(base_stats.get(stat_name, 0) or 0) + int(delta)
        gem_counts = details_obj.get("GemCounts")
        if isinstance(gem_counts, dict):
            gem_counts = dict(gem_counts)
        else:
            gem_counts = {}
        gem_counts["Fever Time"] = int(details_obj.get("FT", 0) or 0)
        gem_counts["Fever Fill Rate"] = int(details_obj.get("FF", 0) or 0)
        selected_element = details_obj.get("SelectedElement") or details_obj.get("Selected Element") or ""
        selected_element = str(selected_element or "").strip()
        stats_primary, stats_secondary, _stats_selected = extract_song_colors(details_obj)
        if not stats_primary:
            stats_primary = buff_color
        minis_for_stats = _song_aware_minis_by_name(stats_primary, stats_secondary)
        computed = compute_full_stats(
            gear_names_local,
            mini_names_local,
            gem_counts,
            selected_element,
            gears_by_name if isinstance(gears_by_name, dict) else {},
            minis_for_stats,
            base_stats,
        )
        if not isinstance(computed, dict) or not computed:
            return details_obj
        out = dict(details_obj)
        out.pop("st", None)  # Always repack from Stats at persistence time.
        out["Stats"] = computed
        if any(
            bool((minis_for_stats.get(name) or {}).get("Mini Ascension Materialized"))
            for name in mini_names_local
        ):
            out["Mini Ascension Materialized"] = True
            out["Mini Ascension Source Version"] = MINI_ASCENSION_CACHE_VERSION
            out["Mini Ascension Materialized Song"] = song_name
            out["Mini Ascension Materialized Primary Color"] = stats_primary
            out["Mini Ascension Materialized Secondary Color"] = stats_secondary
        return out
    def _canonical_persistence_minis(
        gear_names_local: list[str],
        mini_names_local: list[str],
        eff: Optional[tuple[str, list[tuple[Any, ...]], str, str, str]],
    ) -> tuple[str, list[list[str]], list[str]]:
        if eff is None:
            warn_fallback(
                "db.minis_groups.singletons",
                "effective mini grouping unavailable; persisting singleton mini groups",
                context={"song_name": song_name, "team_buff": team_buff},
                fatal=False,
            )
            return _db._loadout_hash_from_names(gear_names_local, mini_names_local), [[n] for n in mini_names_local], [
                *mini_names_local
            ]
        loadout_hash, mini_sigs, p_color, s_color, sel_color = eff
        minis_for_hash = _song_aware_minis_by_name(p_color, s_color)
        groups = canonical_minis_groups_from_names(
            mini_names_local,
            minis_for_hash,
            p_color,
            s_color,
            sel_color,
            mini_sigs=mini_sigs,
        )
        groups = rotate_mini_groups_for_slot_display(groups)
        return loadout_hash, groups, [g[0] for g in groups if g]
    def _canonicalize_persistence_details(
        details_obj: Any,
        *,
        gear_names_local: list[str],
        representative_mini_names_local: list[str],
        original_gear: Any,
        original_minis: Any,
        eff: Optional[tuple[str, list[tuple[Any, ...]], str, str, str]],
    ) -> dict:
        details_unpacked = _unpack_stats_after_load(details_obj) if isinstance(details_obj, dict) else details_obj
        if not isinstance(details_unpacked, dict):
            details_unpacked = {}
        team_color_for_stats = str(
            details_unpacked.get("PrimaryColor") or details_unpacked.get("Primary Color") or ""
        ).strip()
        if (eff is not None) and _can_recompute_stats_for_persistence(
            gear_names_local, representative_mini_names_local
        ):
            return _details_with_representative_stats(
                details_unpacked,
                gear_names_local=gear_names_local,
                mini_names_local=representative_mini_names_local,
                team_color=team_color_for_stats,
            )
        current_stats = details_unpacked.get("Stats")
        if isinstance(current_stats, dict) and current_stats:
            return details_unpacked
        fallback_primary, fallback_secondary, _fallback_selected = extract_song_colors(details_unpacked)
        if eff is not None and (not fallback_primary and not fallback_secondary):
            _hash, _sigs, fallback_primary, fallback_secondary, _sel_color = eff
        if not fallback_primary:
            fallback_primary = team_color_for_stats
        return _ensure_stats_in_details(
            details_unpacked,
            original_gear,
            original_minis,
            _song_aware_minis_by_name(fallback_primary, fallback_secondary),
            team_buff=team_buff,
            team_color=team_color_for_stats,
        )
    own_conn = conn is None
    if conn is None:
        resolved_db_path = str(db_path or get_evolution_db_path())
        conn = get_db_connection(resolved_db_path)
    else:
        resolved_db_path = str(db_path or get_evolution_db_path())
    try:
        if not conn.in_transaction:
            try:
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception as e:
                logger.warning(f"database:_recompute_stats_in_details_for_persistence: {e}")
        _t_params0 = time.perf_counter()
        loadouts_params = []
        deferred_fg_loadouts_params = []
        fg_loadouts_params = []
        encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
        def _encode_gear_names_to_blob(gear_names: list[str]) -> bytes:
            nonlocal encoding_maps
            missing = [n for n in (gear_names or []) if n and n not in encoding_maps.gear_name_to_id]
            if missing:
                _insert_missing_piece_names(conn, table=_GEAR_NAME_ENCODING_TABLE, names=missing)
                encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
            ids: list[int] = []
            for n in gear_names or []:
                if not n:
                    continue
                i = int(encoding_maps.gear_name_to_id.get(n, 0) or 0)
                if i > 0:
                    ids.append(i)
            return bytes(_pack_id_list(ids))
        def _encode_mini_groups_to_blob(groups: list[list[str]]) -> bytes:
            nonlocal encoding_maps
            flat: list[str] = []
            for g in groups or []:
                if not g:
                    continue
                for n in g:
                    if n:
                        flat.append(str(n))
            missing = [n for n in sorted(set(flat)) if n and n not in encoding_maps.mini_name_to_id]
            if missing:
                _insert_missing_piece_names(conn, table=_MINI_NAME_ENCODING_TABLE, names=missing)
                encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
            id_groups: list[list[int]] = []
            for g in groups or []:
                if not g:
                    continue
                ids: list[int] = []
                for n in g:
                    if not n:
                        continue
                    i = int(encoding_maps.mini_name_to_id.get(str(n), 0) or 0)
                    if i > 0:
                        ids.append(i)
                if ids:
                    id_groups.append(ids)
            return bytes(_pack_id_groups(id_groups))
        for entry in deduplicated_entries:
            score = _coerce_db_int(entry.get("score", 0))
            fg_score = _coerce_db_int(entry.get("fg_score", 0))
            fg_base_score = score
            has_explicit_fg_base = False
            try:
                raw_fg_base = entry.get("fg_base_score")
            except Exception as e:
                logger.warning(f"database:_encode_mini_groups_to_blob: {e}")
                raw_fg_base = None
            if raw_fg_base is not None:
                has_explicit_fg_base = True
                fg_base_score = _coerce_db_int(raw_fg_base)
                if fg_base_score <= 0:
                    fg_base_score = score
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")
            entry_id = int(id(entry))
            eff = effective_cache_by_entry_id.get(entry_id)
            if entry_id not in effective_cache_by_entry_id:
                eff = _effective_hash_for_entry(entry)
                effective_cache_by_entry_id[entry_id] = eff
            if eff is not None and isinstance(details, dict):
                (_loadout_hash_eff, _mini_sigs_eff, p_color_eff, s_color_eff, sel_color_eff) = eff
                if (
                    (p_color_eff or s_color_eff)
                    and not (details.get("PrimaryColor") or details.get("Primary Color"))
                    and not (details.get("SecondaryColor") or details.get("Secondary Color"))
                ):
                    details_out = dict(details)
                    if p_color_eff:
                        details_out["PrimaryColor"] = p_color_eff
                    if s_color_eff:
                        details_out["SecondaryColor"] = s_color_eff
                    if sel_color_eff and not (
                        details_out.get("SelectedElement") or details_out.get("Selected Element")
                    ):
                        details_out["SelectedElement"] = sel_color_eff
                    details = details_out
            if fg_score <= 0 and force_data is not None:
                fg_score = fg_score_from_force(force_data)
            force_data = _normalize_force_for_persistence(force_data, fg_score=fg_score)
            force_base_score = _force_payload_base_score(force_data)
            if has_explicit_fg_base and fg_base_score > 0:
                force_data = _normalize_force_base_score_for_persistence(force_data, fg_base_score=fg_base_score)
            elif force_base_score > 0:
                fg_base_score = force_base_score
            elif fg_base_score > 0:
                force_data = _normalize_force_base_score_for_persistence(force_data, fg_base_score=fg_base_score)
            if force_data is not None and fg_score > fg_base_score:
                _assert_force_score_pairing(force_data, fg_base_score=fg_base_score, fg_score=fg_score)
            details = _normalize_details_for_persistence(
                details,
                score=score,
                fg_score=fg_score,
                force_data=force_data,
                preserve_attempt_meta=bool(preserve_attempt_meta),
            )
            gear_names, mini_names = _compact_entry_names(entry)
            loadout_hash, groups, mini_names = _canonical_persistence_minis(gear_names, mini_names, eff)
            details = _canonicalize_persistence_details(
                details,
                gear_names_local=gear_names,
                representative_mini_names_local=mini_names,
                original_gear=gear,
                original_minis=minis,
                eff=eff,
            )
            if force_data is not None:
                force_details = dict(force_data)
                primary = details.get("PrimaryColor") or details.get("Primary Color")
                secondary = details.get("SecondaryColor") or details.get("Secondary Color")
                if primary and not (force_details.get("PrimaryColor") or force_details.get("Primary Color")):
                    force_details["PrimaryColor"] = primary
                if secondary and not (force_details.get("SecondaryColor") or force_details.get("Secondary Color")):
                    force_details["SecondaryColor"] = secondary
                force_details = _details_with_representative_stats(
                    force_details,
                    gear_names_local=gear_names,
                    mini_names_local=mini_names,
                    team_color=str(primary or ""),
                )
                force_data = _align_force_stats_with_persisted_loadout(force_data, force_details)
            details, _retired_details_count = strip_retired_fg_fields(details)
            force_data, _retired_force_count = strip_retired_fg_fields(force_data)
            if (
                isinstance(details, dict)
                and isinstance(details.get("Stats"), dict)
                and details.get("Stats")
                and details.get("st") is not None
            ):
                details = dict(details)
                details.pop("st", None)
            gear_ids_blob = _encode_gear_names_to_blob(gear_names) or None
            minis_ids_blob = _encode_mini_groups_to_blob(groups) or None
            details_storage = _pack_stats_for_storage(_strip_computed_details_fields(details)) if details else None
            details_json = _json_dumps_compact(details_storage) if details_storage else None
            force_storage = _compact_force_details_for_storage(force_data)
            force_json = _json_dumps_compact(force_storage) if force_storage else None
            loadouts_params.append(
                (
                    song_name,
                    team_buff,
                    loadout_hash,
                    score,
                    fg_score,
                    gear_ids_blob,
                    minis_ids_blob,
                    details_json,
                    None,
                )
            )
            if bool(entry.get("_deferred_fg_update")):
                deferred_fg_loadouts_params.append(loadouts_params.pop())
            if force_data is not None and fg_score > fg_base_score:
                fg_details = _base_details_from_force_payload(details, force_data)
                if not fg_details:
                    continue
                fg_details_storage = _pack_stats_for_storage(_strip_computed_details_fields(fg_details))
                fg_details_json = _json_dumps_compact(fg_details_storage) if fg_details_storage else None
                fg_loadouts_params.append(
                    (
                        song_name,
                        team_buff,
                        loadout_hash,
                        fg_base_score,
                        fg_score,
                        gear_ids_blob,
                        minis_ids_blob,
                        fg_details_json,
                        force_json,
                    )
                )
        _log_timing("build_params_json", time.perf_counter() - _t_params0)
        if loadouts_params:
            _t_ins0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_ids_blob = CASE WHEN excluded.score > score THEN excluded.gear_ids_blob ELSE gear_ids_blob END,
                    minis_ids_blob = CASE WHEN excluded.score > score THEN excluded.minis_ids_blob ELSE minis_ids_blob END,
                    details_json = CASE WHEN excluded.score > score THEN excluded.details_json ELSE details_json END,
                    force_details_json = NULL,
                    timestamp = strftime('%s', 'now')
            """,
                loadouts_params,
            )
            _log_timing("insert_team_buff_loadouts", time.perf_counter() - _t_ins0)
        if deferred_fg_loadouts_params:
            _t_ins0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    -- Deferred FG-only update: preserve base leaderboard payload (score/details/gear/minis)
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_ids_blob = CASE WHEN gear_ids_blob IS NULL THEN excluded.gear_ids_blob ELSE gear_ids_blob END,
                    minis_ids_blob = CASE WHEN minis_ids_blob IS NULL THEN excluded.minis_ids_blob ELSE minis_ids_blob END,
                    details_json = CASE WHEN details_json IS NULL THEN excluded.details_json ELSE details_json END,
                    force_details_json = NULL,
                    timestamp = strftime('%s', 'now')
            """,
                deferred_fg_loadouts_params,
            )
            _log_timing("insert_team_buff_loadouts_deferred_fg", time.perf_counter() - _t_ins0)
        if fg_loadouts_params:
            _t_insfg0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_fg_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    fg_score = MAX(fg_score, excluded.fg_score),
                    score = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.score
                        WHEN excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL THEN excluded.score
                        ELSE score
                    END,
                    gear_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.gear_ids_blob
                        ELSE gear_ids_blob
                    END,
                    minis_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.minis_ids_blob
                        ELSE minis_ids_blob
                    END,
                    details_json = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.details_json
                        ELSE details_json
                    END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
                        WHEN excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL
                            THEN excluded.force_details_json
                        ELSE force_details_json
                    END,
                    timestamp = strftime('%s', 'now')
                """,
                fg_loadouts_params,
            )
            _log_timing("insert_team_buff_fg_loadouts", time.perf_counter() - _t_insfg0)
        _t_inv0 = time.perf_counter()
        conn.execute(
            """
            DELETE FROM team_buff_fg_loadouts
            WHERE song_name = ?
            AND team_buff = ?
            AND fg_score <= score
            """,
            (song_name, team_buff),
        )
        conn.execute(
            """
            UPDATE team_buff_loadouts
            SET fg_score = score
            WHERE song_name = ?
            AND team_buff = ?
            AND fg_score > score
            AND NOT EXISTS (
                SELECT 1
                FROM team_buff_fg_loadouts fg
                WHERE fg.song_name = team_buff_loadouts.song_name
                AND fg.team_buff = team_buff_loadouts.team_buff
                AND fg.loadout_hash = team_buff_loadouts.loadout_hash
            )
            """,
            (song_name, team_buff),
        )
        _log_timing("delete_team_buff_fg_invariant", time.perf_counter() - _t_inv0)
        _t_clear0 = time.perf_counter()
        conn.execute(
            """
            UPDATE team_buff_loadouts
            SET force_details_json = NULL
            WHERE song_name = ?
            AND team_buff = ?
            AND force_details_json IS NOT NULL
            """,
            (song_name, team_buff),
        )
        _log_timing("clear_base_force_details", time.perf_counter() - _t_clear0)
        for table in ["team_buff_loadouts", "team_buff_fg_loadouts"]:
            _t_cnt0 = time.perf_counter()
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE song_name = ? AND team_buff = ?",
                (song_name, team_buff),
            )
            count = cursor.fetchone()[0]
            _log_timing(f"count_{table}", time.perf_counter() - _t_cnt0)
            if count <= _db.LOADOUTS_PER_SONG_LIMIT:
                continue
            if table == "team_buff_loadouts":
                _t_pr0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM team_buff_loadouts
                    WHERE song_name = ?
                    AND team_buff = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM team_buff_loadouts
                        WHERE song_name = ?
                        AND team_buff = ?
                        ORDER BY score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, team_buff, song_name, team_buff, _db.LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_team_buff_loadouts", time.perf_counter() - _t_pr0)
            else:
                _t_prfg0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM team_buff_fg_loadouts
                    WHERE song_name = ?
                    AND team_buff = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM team_buff_fg_loadouts
                        WHERE song_name = ?
                        AND team_buff = ?
                        ORDER BY fg_score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, team_buff, song_name, team_buff, _db.LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_team_buff_fg_loadouts", time.perf_counter() - _t_prfg0)
        _t_repair0 = time.perf_counter()
        _repair_base_loadout_fg_summaries(conn, song_name=song_name, team_buff=team_buff)
        _log_timing("repair_base_fg_summaries", time.perf_counter() - _t_repair0)
        verify_integrity = env_flag("DB_VERIFY_WRITE_INTEGRITY", "0")
        if verify_integrity:
            strict = env_flag("DB_STRICT_WRITE_INTEGRITY", "0")
            def _warn_or_raise(msg: str) -> None:
                if strict:
                    raise RuntimeError(msg)
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            def _verify_table_row(
                *, table: str, loadout_hash: str, expected_score: int, expected_fg_score: int
            ) -> None:
                row = conn.execute(
                    f"SELECT score, fg_score, gear_ids_blob, minis_ids_blob, details_json FROM {table} "
                    "WHERE song_name = ? AND team_buff = ? AND loadout_hash = ?",
                    (song_name, team_buff, loadout_hash),
                ).fetchone()
                if row is None:
                    _warn_or_raise(
                        f"[DB] Missing expected row after persistence: table={table} song={song_name!r} "
                        f"team_buff={team_buff!r} hash={loadout_hash}"
                    )
                    return
                got_score = int(row["score"] or 0)
                got_fg_score = int(row["fg_score"] or 0)
                if table != "team_buff_fg_loadouts" or got_fg_score <= int(expected_fg_score):
                    if got_score < int(expected_score):
                        _warn_or_raise(
                            f"[DB] Score regressed after persistence (possible override/race): table={table} "
                            f"song={song_name!r} team_buff={team_buff!r} hash={loadout_hash} "
                            f"expected>={int(expected_score)} got={got_score}"
                        )
                if got_fg_score < int(expected_fg_score):
                    _warn_or_raise(
                        f"[DB] FG score regressed after persistence (possible override/race): table={table} "
                        f"song={song_name!r} team_buff={team_buff!r} hash={loadout_hash} "
                        f"expected>={int(expected_fg_score)} got={got_fg_score}"
                    )
                try:
                    gear_ids_blob_row = row["gear_ids_blob"]
                    minis_ids_blob_row = row["minis_ids_blob"]
                    gear_names_row: list[str] = []
                    ids = _unpack_id_list(gear_ids_blob_row)
                    if ids:
                        gear_names_row = [
                            str(encoding_maps.gear_id_to_name.get(int(i), "") or "") for i in ids if int(i) > 0
                        ]
                        gear_names_row = [n for n in gear_names_row if n]
                    mini_groups_row: list[list[str]] = []
                    id_groups = _unpack_id_groups(minis_ids_blob_row)
                    if id_groups:
                        for g in id_groups:
                            if not g:
                                continue
                            names = [str(encoding_maps.mini_id_to_name.get(int(i), "") or "") for i in g if int(i) > 0]
                            names = [n for n in names if n]
                            if names:
                                mini_groups_row.append(names)
                    mini_names_row = representative_mini_names(mini_groups_row)
                    details_row = _json_loads(row["details_json"]) if row["details_json"] else {}
                    p_color, s_color, sel_color = extract_song_colors(details_row)
                    if p_color or s_color:
                        minis_for_verify = _song_aware_minis_by_name(p_color, s_color)
                        mini_sigs_row = [
                            effective_mini_signature_for_name(n, minis_for_verify, p_color, s_color, sel_color)
                            for n in mini_names_row
                        ]
                        expected_hash = effective_loadout_hash_from_names(gear_names_row, mini_sigs_row)
                    else:
                        expected_hash = _db._loadout_hash_from_names(gear_names_row, mini_names_row)
                    if expected_hash and str(expected_hash) != str(loadout_hash):
                        _warn_or_raise(
                            f"[DB] Loadout hash mismatch after persistence (possible override/race): table={table} "
                            f"song={song_name!r} team_buff={team_buff!r} stored={loadout_hash} expected={expected_hash}"
                        )
                except Exception as e:
                    logger.warning(f"database:_verify_table_row: {e}")
            try:
                if loadouts_params:
                    best = max(loadouts_params, key=lambda t: int(t[3] or 0))
                    _verify_table_row(
                        table="team_buff_loadouts",
                        loadout_hash=str(best[2]),
                        expected_score=int(best[3] or 0),
                        expected_fg_score=int(best[4] or 0),
                    )
                if fg_loadouts_params:
                    best_fg = max(fg_loadouts_params, key=lambda t: int(t[4] or 0))
                    _verify_table_row(
                        table="team_buff_fg_loadouts",
                        loadout_hash=str(best_fg[2]),
                        expected_score=int(best_fg[3] or 0),
                        expected_fg_score=int(best_fg[4] or 0),
                    )
            except Exception as exc:
                _warn_or_raise(
                    f"[DB] Write integrity verification failed: song={song_name!r} team_buff={team_buff!r} "
                    f"error={type(exc).__name__}: {exc}"
                )
        if commit:
            _t_commit0 = time.perf_counter()
            conn.commit()
            _log_timing("commit", time.perf_counter() - _t_commit0)
    except sqlite3.Error as e:
        print(f"[DB] Error saving TeamBuff batch loadouts: {e}")
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        if own_conn:
            try:
                conn.execute("PRAGMA synchronous=FULL;")
            except sqlite3.Error:
                pass
            conn.close()
        _log_timing("total", time.perf_counter() - _t0)
