"""
Repair common DB integrity issues that break frontend/export consumers.

This tool is intended to be safe to run on large, messy datasets where:
  - Tier tables already exist (team_buff_*), but have corrupted minis_json shapes.
  - details_json["Stats"] is missing/empty, causing frontend to show 0 stats.
  - FG tables contain rows where fg_score <= score (should never happen).

It is conservative:
  - It repairs known-corruption patterns and missing Stats.
  - It does not attempt to recompute scores.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.database import get_evolution_db_path
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.data.loadout_equivalence import (
    decode_minis_json,
    encode_minis_groups,
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    merge_minis_groups_for_entry,
    representative_mini_names,
)


EXPECTED_TEAM_BUFFS = {"NONE", "T1", "T5", "T10", "T15"}
ELEMENT_KEYS = ("Chill", "Flow", "Rush", "Beat", "Vibe")
_TEAM_BUFF_TIERS: dict[str, dict[str, int]] = {
    "NONE": {"PP": 0, "Elem": 0},
    "T1": {"PP": 25, "Elem": 35},
    "T5": {"PP": 25, "Elem": 30},
    "T10": {"PP": 20, "Elem": 25},
    "T15": {"PP": 15, "Elem": 20},
}


def _json_loads(s: Any, default: Any) -> Any:
    if s is None:
        return default
    if isinstance(s, (dict, list)):
        return s
    text = str(s).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _stats_missing_or_empty(stats: Any) -> bool:
    if stats is None:
        return True
    if isinstance(stats, dict) and not stats:
        return True
    if isinstance(stats, dict):
        # Treat "all zeros" as empty.
        if not any(float(v or 0) != 0.0 for v in stats.values() if isinstance(v, (int, float))):
            # If there are non-numeric values this could be a false positive; handle that below.
            any_nonzero = False
            for v in stats.values():
                try:
                    if float(v or 0) != 0.0:
                        any_nonzero = True
                        break
                except Exception:
                    continue
            return not any_nonzero
    return False


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value) if value is not None else int(default)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(default)


def _stats_from_force_payload(force: Any) -> dict[str, Any] | None:
    if not isinstance(force, dict) or not force:
        return None
    base_stats = force.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return None
    gem_counts = force.get("GemCounts")
    if not isinstance(gem_counts, dict):
        gem_counts = {}
    selected_element = force.get("Selected Element") or force.get("SelectedElement") or ""
    ft_val = _safe_int(force.get("FT", gem_counts.get("Fever Time", 0)), 0)
    ff_val = _safe_int(
        force.get("FF", gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0))),
        0,
    )
    g_pp = _safe_int(gem_counts.get("Perfect Points", 0), 0)
    g_cm = _safe_int(gem_counts.get("Combo Multiplier", 0), 0)
    g_fm = _safe_int(gem_counts.get("Fever Multiplier", 0), 0)
    g_ov = _safe_int(gem_counts.get("Element", gem_counts.get("Element Overflow", 0)), 0)
    try:
        from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast

        stats = apply_gems_to_base_fast(
            base_stats,
            str(selected_element),
            ft_val,
            ff_val,
            g_pp,
            g_cm,
            g_fm,
            g_ov,
        )
        return stats if isinstance(stats, dict) else dict(base_stats)
    except Exception:
        return dict(base_stats)


def _team_buff_effect(team_buff: str, team_color: str) -> dict[str, int]:
    tier = _TEAM_BUFF_TIERS.get(str(team_buff or "").strip().upper())
    if not tier:
        return {}
    pp_add = int(tier["PP"])
    elem_add = int(tier["Elem"])
    out: dict[str, int] = {"Perfect Points": pp_add}

    team_color = str(team_color or "").strip()
    valid_color_key = next((k for k in ELEMENT_KEYS if k.lower() == team_color.lower()), None)
    if valid_color_key:
        out[valid_color_key] = elem_add
    elif team_color:
        out["Perfect Points"] += pp_add
    return out


def _apply_stat_delta(stats: dict[str, Any], delta: dict[str, int]) -> dict[str, Any]:
    out = dict(stats or {})
    for k, d in (delta or {}).items():
        out[str(k)] = _safe_int(out.get(k, 0), 0) + int(d)
    return out


def _delta_map(base_team_buff: str, target_team_buff: str, team_color: str) -> dict[str, int]:
    base = _team_buff_effect(base_team_buff, team_color)
    target = _team_buff_effect(target_team_buff, team_color)
    keys = set(base.keys()) | set(target.keys())
    out: dict[str, int] = {}
    for k in keys:
        out[k] = int(target.get(k, 0)) - int(base.get(k, 0))
    return out


def _ensure_stats_include_base_effect(stats: dict[str, Any], base_effect: dict[str, int]) -> dict[str, Any]:
    if not isinstance(stats, dict) or not stats or not isinstance(base_effect, dict) or not base_effect:
        return dict(stats or {})
    base_pp = _safe_int(base_effect.get("Perfect Points", 0), 0)
    if base_pp <= 0:
        return dict(stats)
    pp0 = _safe_int(stats.get("Perfect Points", 0), 0)
    if pp0 < base_pp:
        return _apply_stat_delta(stats, base_effect)
    return dict(stats)


def _normalize_force_payload(force: Any, *, fallback_selected: str, team_buff: str) -> Any:
    if not isinstance(force, dict) or not force:
        return force
    out = dict(force)

    selected = out.get("SelectedElement") or out.get("Selected Element") or (fallback_selected or "")
    selected = str(selected or "").strip()
    if selected:
        out["SelectedElement"] = selected
        out["Selected Element"] = selected

    score_val = _safe_int(out.get("score", out.get("Score", 0)), 0)
    if score_val <= 0:
        fg_meta = out.get("ForceGreats")
        if isinstance(fg_meta, dict):
            score_val = _safe_int(fg_meta.get("final_score", 0), 0)
    if score_val > 0:
        out["score"] = int(score_val)
        out["Score"] = int(score_val)

    # If the payload includes BaseStats, ensure it includes the base T5 effect.
    base_stats = out.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        base_effect = _team_buff_effect("T5", selected)
        out["BaseStats"] = _ensure_stats_include_base_effect(base_stats, base_effect)

    # If Stats are missing, materialize from BaseStats + gems (and apply tier delta).
    if _stats_missing_or_empty(out.get("Stats")):
        stats_from_force = _stats_from_force_payload(out)
        if stats_from_force is not None:
            delta = _delta_map("T5", team_buff, selected)
            out["Stats"] = _apply_stat_delta(stats_from_force, delta)

    return out


def _repair_minis_node(node: Any) -> tuple[Any, int]:
    """
    Repair minis_json corruption where a string contains a python-list literal like:
      \"['Electroman']\"
    Returns: (new_node, repair_count)
    """
    if isinstance(node, str):
        text = node.strip()
        if text.startswith("[") and text.endswith("]") and "['" in text:
            try:
                val = ast.literal_eval(text)
            except Exception:
                return node, 0
            if isinstance(val, list) and all(isinstance(x, str) for x in val):
                return val, 1
        return node, 0

    if isinstance(node, list):
        repaired = 0
        out: list[Any] = []
        for item in node:
            new_item, r = _repair_minis_node(item)
            repaired += r
            out.append(new_item)
        return out, repaired

    return node, 0


def _representative_mini_names(minis_json_obj: Any) -> list[str]:
    """
    Normalize minis_json into a list[str] for Stats recompute.
    - Supports legacy flat list[str]
    - Supports grouped list[list[str]] (variant groups)
    """
    minis: list[str] = []
    if isinstance(minis_json_obj, list):
        for item in minis_json_obj:
            if isinstance(item, list) and item:
                if isinstance(item[0], str):
                    minis.append(item[0])
            elif isinstance(item, str):
                minis.append(item)
    return minis


def _extract_base_stats_from_force(force: Any) -> dict[str, Any] | None:
    if not isinstance(force, dict) or not force:
        return None
    if isinstance(force.get("BaseStats"), dict) and force["BaseStats"]:
        return force["BaseStats"]
    if (
        isinstance(force.get("details"), dict)
        and isinstance(force["details"].get("BaseStats"), dict)
        and force["details"]["BaseStats"]
    ):
        return force["details"]["BaseStats"]
    # Some legacy shapes embed under ForceGreats.
    if isinstance(force.get("ForceGreats"), dict) and isinstance(force["ForceGreats"].get("BaseStats"), dict):
        if force["ForceGreats"]["BaseStats"]:
            return force["ForceGreats"]["BaseStats"]
    return None


@dataclass
class RepairStats:
    scanned_rows: int = 0
    minis_fixed: int = 0
    minis_reordered: int = 0
    stats_fixed: int = 0
    stats_team_buff_fixed: int = 0
    force_normalized: int = 0
    fg_invariant_deleted: int = 0
    team_buff_fixed_case: int = 0
    team_buff_unexpected: int = 0
    team_buff_rehash_scanned: int = 0
    team_buff_rehash_deduped: int = 0


def repair_frontend_db(
    *,
    db_path: Path,
    dry_run: bool,
    verbose: bool,
) -> RepairStats:
    # Allow downstream helpers that read get_evolution_db_path() to use this DB.
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    paths = load_paths_cache()
    gears_list = parse_gear_rows(paths.get("Gears", ""))
    minis_list = parse_mini_rows(paths.get("Minis", ""))
    gears_by_name = {g["Name"]: g for g in gears_list}
    minis_by_name = {m["Name"]: m for m in minis_list}

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

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    stats = RepairStats()

    def table_exists(name: str) -> bool:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    # 1) Normalize team_buff casing for tables that have it.
    for tbl in ("fg_loadouts", "team_buff_loadouts", "team_buff_fg_loadouts"):
        if not table_exists(tbl):
            continue
        # Skip if column missing.
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
        if "team_buff" not in cols:
            continue

        before = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE team_buff != UPPER(TRIM(team_buff))").fetchone()[0]
        if before:
            stats.team_buff_fixed_case += int(before)
            if not dry_run:
                conn.execute(f"UPDATE {tbl} SET team_buff = UPPER(TRIM(team_buff))")

        # Map common bad values to NONE.
        if not dry_run:
            conn.execute(
                f"""
                UPDATE {tbl}
                SET team_buff = 'NONE'
                WHERE team_buff IN ('0', 'NO_BUFF', 'NO BUFF', 'NONEBUFF', 'NONE BUFF')
                """
            )

        unexpected = conn.execute(
            f"""
            SELECT COUNT(*) FROM {tbl}
            WHERE team_buff IS NOT NULL
              AND team_buff != ''
              AND UPPER(team_buff) NOT IN ('NONE','T1','T5','T10','T15')
            """
        ).fetchone()[0]
        stats.team_buff_unexpected += int(unexpected)

    # 2) Enforce FG invariant (delete rows where fg_score <= score).
    for tbl in ("fg_loadouts", "team_buff_fg_loadouts"):
        if not table_exists(tbl):
            continue
        deleted = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE fg_score <= score").fetchone()[0]
        stats.fg_invariant_deleted += int(deleted)
        if deleted and not dry_run:
            conn.execute(f"DELETE FROM {tbl} WHERE fg_score <= score")

    # 3) Repair minis_json corruption + missing Stats.
    tables = ("loadouts", "fg_loadouts", "team_buff_loadouts", "team_buff_fg_loadouts")
    for tbl in tables:
        if not table_exists(tbl):
            continue

        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
        if not {"gear_json", "minis_json", "details_json"}.issubset(cols):
            continue
        has_force = "force_details_json" in cols
        has_team_buff = "team_buff" in cols

        if verbose:
            print(f"[Repair] Scanning table: {tbl}")

        select_cols = ["rowid", "gear_json", "minis_json", "details_json"]
        if has_force:
            select_cols.append("force_details_json")
        if has_team_buff:
            select_cols.append("team_buff")
        cur = conn.execute(f"SELECT {', '.join(select_cols)} FROM {tbl}")
        for row in cur:
            stats.scanned_rows += 1

            minis_text_in = row["minis_json"] or ""
            minis_obj = _json_loads(minis_text_in, [])
            minis_fixed_obj, minis_repairs = _repair_minis_node(minis_obj)
            if minis_repairs:
                stats.minis_fixed += minis_repairs

            # Always re-encode minis groups to:
            # - canonicalize shape (list[list[str]])
            # - rotate repeated groups so naive frontends don't show duplicate minis in multiple slots
            groups = []
            if isinstance(minis_fixed_obj, list):
                if minis_fixed_obj and all(isinstance(x, str) for x in minis_fixed_obj):
                    groups = [[str(x).strip()] for x in minis_fixed_obj if str(x).strip()]
                else:
                    groups = [
                        [str(x).strip() for x in (g or []) if x is not None and str(x).strip()]
                        for g in minis_fixed_obj
                        if isinstance(g, list)
                    ]
            minis_text_out = (
                encode_minis_groups(groups) if groups else encode_minis_groups(decode_minis_json(minis_text_in))
            )
            if minis_text_out and minis_text_out != minis_text_in:
                stats.minis_reordered += 1

            details = _json_loads(row["details_json"], {})
            if not isinstance(details, dict):
                details = {}

            force = _json_loads(row["force_details_json"], {}) if has_force else {}
            team_buff_val = str(row["team_buff"] or "").strip().upper() if has_team_buff else "T5"
            if not team_buff_val:
                team_buff_val = "T5"
            if team_buff_val not in EXPECTED_TEAM_BUFFS:
                team_buff_val = "T5"

            # Try to pull a stable selected element for normalization.
            fallback_selected = str(details.get("SelectedElement") or details.get("Selected Element") or "").strip()

            force_changed = False
            if has_force and isinstance(force, dict) and force:
                force_out = _normalize_force_payload(force, fallback_selected=fallback_selected, team_buff=team_buff_val)
                if isinstance(force_out, dict) and json.dumps(force_out, sort_keys=True) != json.dumps(force, sort_keys=True):
                    force = force_out
                    stats.force_normalized += 1
                    force_changed = True

            stats_needs_repair = _stats_missing_or_empty(details.get("Stats"))
            if stats_needs_repair:
                stats_from_force = _stats_from_force_payload(force)
                if stats_from_force is not None:
                    details["Stats"] = stats_from_force
                    stats.stats_fixed += 1
                else:
                    gear_names = _json_loads(row["gear_json"], [])
                    mini_names = _representative_mini_names(minis_fixed_obj)

                    gem_counts = dict(details.get("GemCounts", {}) or {})
                    gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
                    gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
                    selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

                    computed_stats = compute_full_stats(
                        gear_names,
                        mini_names,
                        gem_counts,
                        selected_element,
                        gears_by_name,
                        minis_by_name,
                        base_stats,
                    )
                    details["Stats"] = computed_stats
                    stats.stats_fixed += 1

            # Tiered FG tables: ensure details Stats includes the TeamBuff effect for the row's tier.
            # This prevents "T5" rows from displaying "NONE" stats (e.g., missing +PP/+color).
            team_buff_fixed_this_row = False
            if tbl == "team_buff_fg_loadouts" and isinstance(force, dict) and force and isinstance(details.get("Stats"), dict):
                try:
                    from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast

                    det_stats = dict(details.get("Stats") or {})
                    selected = str(
                        force.get("SelectedElement")
                        or force.get("Selected Element")
                        or fallback_selected
                        or details.get("PrimaryColor")
                        or ""
                    ).strip()
                    team_color = str(details.get("PrimaryColor") or selected or "").strip()
                    base_effect = _team_buff_effect("T5", team_color)
                    base_stats = force.get("BaseStats")
                    if isinstance(base_stats, dict) and base_stats:
                        base_stats2 = _ensure_stats_include_base_effect(base_stats, base_effect)
                        gem_counts = force.get("GemCounts") if isinstance(force.get("GemCounts"), dict) else {}
                        stats_t5 = apply_gems_to_base_fast(
                            base_stats2,
                            selected,
                            _safe_int(force.get("FT", gem_counts.get("Fever Time", 0)), 0),
                            _safe_int(
                                force.get("FF", gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0))),
                                0,
                            ),
                            _safe_int(gem_counts.get("Perfect Points", 0), 0),
                            _safe_int(gem_counts.get("Combo Multiplier", 0), 0),
                            _safe_int(gem_counts.get("Fever Multiplier", 0), 0),
                            _safe_int(gem_counts.get("Element", gem_counts.get("Element Overflow", 0)), 0),
                        )
                        if isinstance(stats_t5, dict) and stats_t5:
                            expected = _apply_stat_delta(stats_t5, _delta_map("T5", team_buff_val, team_color))

                            changed = False
                            for k in ("Perfect Points",):
                                if _safe_int(det_stats.get(k, 0), 0) != _safe_int(expected.get(k, 0), 0):
                                    det_stats[k] = _safe_int(expected.get(k, 0), 0)
                                    changed = True
                            color_key = next((k for k in ELEMENT_KEYS if k.lower() == team_color.lower()), None)
                            if color_key and _safe_int(det_stats.get(color_key, 0), 0) != _safe_int(
                                expected.get(color_key, 0), 0
                            ):
                                det_stats[color_key] = _safe_int(expected.get(color_key, 0), 0)
                                changed = True

                            if changed:
                                details["Stats"] = det_stats
                                stats.stats_team_buff_fixed += 1
                                team_buff_fixed_this_row = True
                except Exception:
                    pass

            needs_update = minis_repairs or stats_needs_repair or (minis_text_out and minis_text_out != minis_text_in)
            needs_update = needs_update or force_changed or team_buff_fixed_this_row

            if needs_update:
                if not dry_run:
                    if has_force:
                        conn.execute(
                            f"UPDATE {tbl} SET minis_json = ?, details_json = ?, force_details_json = ? WHERE rowid = ?",
                            (minis_text_out, json.dumps(details), json.dumps(force), row["rowid"]),
                        )
                    else:
                        conn.execute(
                            f"UPDATE {tbl} SET minis_json = ?, details_json = ? WHERE rowid = ?",
                            (minis_text_out, json.dumps(details), row["rowid"]),
                        )

    # 4) Rehash + dedupe team_buff tables to collapse legacy/variant hash drift.
    def _rehash_team_buff_table(table_name: str) -> None:
        if not table_exists(table_name):
            return

        total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if not total_rows:
            return

        stats.team_buff_rehash_scanned += int(total_rows)
        if verbose:
            print(f"[Repair] Rehashing table: {table_name} ({total_rows:,} rows)")

        new_table = f"{table_name}__rehash"
        if not dry_run:
            conn.execute(f"DROP TABLE IF EXISTS {new_table};")
            conn.execute(
                f"""
                CREATE TABLE {new_table} (
                    song_name TEXT,
                    team_buff TEXT,
                    loadout_hash TEXT,
                    score INTEGER,
                    fg_score INTEGER DEFAULT 0,
                    gear_json TEXT,
                    minis_json TEXT,
                    details_json TEXT,
                    force_details_json TEXT,
                    timestamp REAL,
                    PRIMARY KEY (song_name, team_buff, loadout_hash),
                    FOREIGN KEY (song_name) REFERENCES songs(name)
                );
                """
            )

        is_fg_table = table_name == "team_buff_fg_loadouts"

        song_rows = conn.execute(f"SELECT DISTINCT song_name FROM {table_name}").fetchall()
        total_out = 0
        for (song_name,) in song_rows:
            aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
            cur = conn.execute(
                f"""
                SELECT song_name, team_buff, loadout_hash, score, fg_score,
                       gear_json, minis_json, details_json, force_details_json, timestamp
                FROM {table_name}
                WHERE song_name = ?
                """,
                (song_name,),
            )
            for row in cur:
                team_buff = str(row["team_buff"] or "").strip().upper()
                if not team_buff:
                    team_buff = "T5"
                if team_buff not in EXPECTED_TEAM_BUFFS:
                    team_buff = "T5"

                details = _json_loads(row["details_json"], {})
                if not isinstance(details, dict):
                    details = {}
                p_color, s_color, sel_color = extract_song_colors(details)

                gear_names = _json_loads(row["gear_json"], [])
                if not isinstance(gear_names, list):
                    gear_names = []
                gear_names = [str(n) for n in gear_names if str(n)]

                groups_in = decode_minis_json(row["minis_json"])
                mini_names_rep = representative_mini_names(groups_in)

                new_hash = str(row["loadout_hash"] or "")
                can_hash = bool(minis_by_name) and (p_color or s_color) and bool(mini_names_rep)
                if can_hash:
                    try:
                        mini_sigs = [
                            effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color)
                            for n in mini_names_rep
                        ]
                        new_hash = effective_loadout_hash_from_names(gear_names, mini_sigs)
                    except Exception:
                        new_hash = str(row["loadout_hash"] or "")

                key = (str(song_name), team_buff, new_hash)
                prev = aggregated.get(key)
                score = _safe_int(row["score"], 0)
                fg_score = _safe_int(row["fg_score"], 0)
                timestamp = float(row["timestamp"] or 0.0)

                if prev is None:
                    aggregated[key] = {
                        "song_name": str(song_name),
                        "team_buff": team_buff,
                        "loadout_hash": new_hash,
                        "score": score,
                        "fg_score": fg_score,
                        "gear_json": row["gear_json"],
                        "details_json": row["details_json"],
                        "force_details_json": row["force_details_json"],
                        "timestamp": timestamp,
                        "minis_groups": groups_in,
                        "p_color": p_color,
                        "s_color": s_color,
                        "sel_color": sel_color,
                    }
                    continue

                # Merge minis groups (best-effort).
                prev_groups = prev.get("minis_groups") or []
                use_p = prev.get("p_color") or p_color
                use_s = prev.get("s_color") or s_color
                use_sel = prev.get("sel_color") or sel_color
                if minis_by_name and (use_p or use_s):
                    merged = merge_minis_groups_for_entry(
                        prev_groups,
                        mini_names_rep,
                        minis_by_name,
                        use_p,
                        use_s,
                        use_sel,
                    )
                    prev["minis_groups"] = merged
                else:
                    flat = []
                    for g in prev_groups + groups_in:
                        flat.extend(g or [])
                    prev["minis_groups"] = [[n] for n in sorted(set([n for n in flat if n]))]

                prev["p_color"] = use_p
                prev["s_color"] = use_s
                prev["sel_color"] = use_sel

                # Align score/fg_score + details/force to the best row.
                if is_fg_table:
                    better = fg_score > _safe_int(prev.get("fg_score"), 0)
                    if not better and fg_score == _safe_int(prev.get("fg_score"), 0):
                        better = score > _safe_int(prev.get("score"), 0) or timestamp >= float(prev.get("timestamp") or 0)
                    if better:
                        prev["score"] = score
                        prev["fg_score"] = fg_score
                        prev["gear_json"] = row["gear_json"]
                        prev["details_json"] = row["details_json"]
                        prev["force_details_json"] = row["force_details_json"]
                else:
                    better = score > _safe_int(prev.get("score"), 0)
                    if not better and score == _safe_int(prev.get("score"), 0):
                        better = timestamp >= float(prev.get("timestamp") or 0)
                    if better:
                        prev["score"] = score
                        prev["gear_json"] = row["gear_json"]
                        prev["details_json"] = row["details_json"]
                    if fg_score > _safe_int(prev.get("fg_score"), 0):
                        prev["fg_score"] = fg_score
                        prev["force_details_json"] = row["force_details_json"]

                prev["timestamp"] = max(float(prev.get("timestamp") or 0.0), timestamp)

            total_out += len(aggregated)

            if not dry_run:
                for rec in aggregated.values():
                    minis_json = encode_minis_groups(rec.get("minis_groups") or [])
                    conn.execute(
                        f"""
                        INSERT INTO {new_table} (
                            song_name, team_buff, loadout_hash, score, fg_score,
                            gear_json, minis_json, details_json, force_details_json, timestamp
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rec.get("song_name"),
                            rec.get("team_buff"),
                            rec.get("loadout_hash"),
                            _safe_int(rec.get("score"), 0),
                            _safe_int(rec.get("fg_score"), 0),
                            rec.get("gear_json"),
                            minis_json,
                            rec.get("details_json"),
                            rec.get("force_details_json"),
                            rec.get("timestamp"),
                        ),
                    )

        stats.team_buff_rehash_deduped += int(total_rows - total_out)

        if not dry_run:
            conn.execute(f"DELETE FROM {table_name};")
            conn.execute(
                f"""
                INSERT INTO {table_name} (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_json, minis_json, details_json, force_details_json, timestamp
                )
                SELECT song_name, team_buff, loadout_hash, score, fg_score,
                       gear_json, minis_json, details_json, force_details_json, timestamp
                FROM {new_table};
                """
            )
            conn.execute(f"DROP TABLE IF EXISTS {new_table};")

    _rehash_team_buff_table("team_buff_loadouts")
    _rehash_team_buff_table("team_buff_fg_loadouts")

    if not dry_run:
        conn.commit()
    conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair common frontend-breaking DB integrity issues.")
    parser.add_argument(
        "--db",
        type=str,
        default="",
        help="DB path (defaults to EVOLUTION_DB_PATH / ./evolution.db).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Scan and report, but do not write changes.")
    parser.add_argument("--verbose", action="store_true", help="Print per-table progress.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    result = repair_frontend_db(db_path=db_path, dry_run=bool(args.dry_run), verbose=bool(args.verbose))
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 60)
    print(f"DB: {db_path}")
    print(f"scanned_rows: {result.scanned_rows:,}")
    print(f"minis_fixed: {result.minis_fixed:,}")
    print(f"minis_reordered: {result.minis_reordered:,}")
    print(f"stats_fixed: {result.stats_fixed:,}")
    print(f"stats_team_buff_fixed: {result.stats_team_buff_fixed:,}")
    print(f"force_normalized: {result.force_normalized:,}")
    print(f"fg_invariant_rows_deleted: {result.fg_invariant_deleted:,}")
    print(f"team_buff_case_fixed_rows: {result.team_buff_fixed_case:,}")
    print(f"team_buff_rehash_scanned: {result.team_buff_rehash_scanned:,}")
    print(f"team_buff_rehash_deduped: {result.team_buff_rehash_deduped:,}")
    if result.team_buff_unexpected:
        print(f"WARNING: unexpected team_buff rows remain: {result.team_buff_unexpected:,}")
        print(f"expected: {sorted(EXPECTED_TEAM_BUFFS)}")


if __name__ == "__main__":
    main()
