"""
Compare on-demand TeamBuff tier recompute against a legacy v17 DB that materialized tiers.

This is intended as a scoring-integrity check:
- Load baseline candidates (base+FG union) from legacy DB at a baseline tier (typically T5)
- Recompute tier leaderboards on demand using the current GPU-backed scorer
- Compare against legacy `team_buff_loadouts` / `team_buff_fg_loadouts` rows for each tier

Usage:
  python tools/db/compare_on_demand_tiers_to_legacy_db.py --song "Ice Angel (Hard) by Yooh" --file "Data/Hard/Ice Angel (Hard) by Yooh.txt"
  python tools/db/compare_on_demand_tiers_to_legacy_db.py --song "Ice Angel (Hard) by Yooh" --file "Data/Hard/Ice Angel (Hard) by Yooh.txt" --legacy evolution_legacy.db --baseline T5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _loadout_hash_from_names(gear_names: list[str], mini_names: list[str]) -> str:
    g = sorted([n for n in (gear_names or []) if n])
    m = sorted([n for n in (mini_names or []) if n])
    payload = f"GEAR:{'|'.join(g)}::MINIS:{'|'.join(m)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _json_loads(blob: object) -> object:
    if not blob:
        return None
    try:
        return json.loads(str(blob))
    except Exception:
        return None


def _load_baseline_candidates_from_legacy(
    conn: sqlite3.Connection,
    *,
    song_name: str,
    baseline_team_buff: str,
    limit: int,
) -> list[dict]:
    from gear_optimizer.data.database import _unpack_stats_after_load

    song_name = str(song_name or "").strip()
    baseline_team_buff = str(baseline_team_buff or "").strip().upper() or "T5"
    limit = max(1, int(limit))

    by_hash: dict[str, dict] = {}
    results: list[dict] = []

    def ingest_row(row: sqlite3.Row) -> None:
        loadout_hash = str(row["loadout_hash"] or "").strip()
        if not loadout_hash:
            return
        gear = _json_loads(row["gear_json"]) or []
        minis = _json_loads(row["minis_json"]) or []
        details = _json_loads(row["details_json"]) or {}
        details = _unpack_stats_after_load(details) if isinstance(details, dict) else {}
        force_raw = row["force_details_json"]
        force = _json_loads(force_raw) if force_raw else None
        force_obj = force if isinstance(force, dict) else None

        entry = by_hash.get(loadout_hash)
        if entry is None:
            entry = {
                "loadout_hash": loadout_hash,
                "score": int(row["score"] or 0),
                "fg_score": int(row["fg_score"] or 0),
                "gear": gear,
                "minis": minis,
                "details": details,
                "force": force_obj,
            }
            by_hash[loadout_hash] = entry
            results.append(entry)
            return

        # Merge: keep best base score and best FG score, and preserve a non-null force payload.
        try:
            entry["score"] = max(int(entry.get("score") or 0), int(row["score"] or 0))
        except Exception:
            pass
        try:
            entry["fg_score"] = max(int(entry.get("fg_score") or 0), int(row["fg_score"] or 0))
        except Exception:
            pass
        if entry.get("force") is None and force_obj is not None:
            entry["force"] = force_obj

    # 1) Base leaderboard rows
    base_rows = conn.execute(
        """
        SELECT loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json
        FROM team_buff_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (song_name, baseline_team_buff, int(limit)),
    ).fetchall()
    for r in base_rows:
        ingest_row(r)

    # 2) FG leaderboard rows (union in top-N by fg_score)
    fg_rows = conn.execute(
        """
        SELECT loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json
        FROM team_buff_fg_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY fg_score DESC
        LIMIT ?
        """,
        (song_name, baseline_team_buff, int(limit)),
    ).fetchall()
    for r in fg_rows:
        ingest_row(r)

    return results


def _load_legacy_top_lists(
    conn: sqlite3.Connection,
    *,
    song_name: str,
    team_buff: str,
    limit: int,
) -> tuple[list[tuple[int, int, str]], list[tuple[int, int, str]]]:
    song_name = str(song_name or "").strip()
    team_buff = str(team_buff or "").strip().upper()
    limit = max(1, int(limit))

    base_rows = conn.execute(
        """
        SELECT score, fg_score, loadout_hash
        FROM team_buff_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (song_name, team_buff, int(limit)),
    ).fetchall()
    base_list = [(int(r["score"] or 0), int(r["fg_score"] or 0), str(r["loadout_hash"] or "")) for r in base_rows]
    base_list.sort(key=lambda t: (-int(t[0] or 0), str(t[2] or "")))

    fg_rows = conn.execute(
        """
        SELECT fg_score, score, loadout_hash
        FROM team_buff_fg_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY fg_score DESC
        LIMIT ?
        """,
        (song_name, team_buff, int(limit)),
    ).fetchall()
    fg_list = [(int(r["fg_score"] or 0), int(r["score"] or 0), str(r["loadout_hash"] or "")) for r in fg_rows]
    fg_list.sort(key=lambda t: (-int(t[0] or 0), str(t[2] or "")))
    return base_list, fg_list


def _computed_top_lists(payload: dict, tier: str) -> tuple[list[tuple[int, int, str]], list[tuple[int, int, str]]]:
    tiers = payload.get("tiers") if isinstance(payload, dict) else None
    if not isinstance(tiers, dict):
        return [], []
    tb = tiers.get(str(tier)) if isinstance(tiers.get(str(tier)), dict) else None
    if not isinstance(tb, dict):
        return [], []

    base_rows = tb.get("base_top51") if isinstance(tb.get("base_top51"), list) else []
    fg_rows = tb.get("fg_top51") if isinstance(tb.get("fg_top51"), list) else []

    out_base: list[tuple[int, int, str]] = []
    for r in base_rows:
        if not isinstance(r, dict):
            continue
        gear = r.get("gear") or []
        minis = r.get("minis") or []
        h = str(r.get("loadout_hash") or "").strip()
        if not h:
            h = _loadout_hash_from_names([str(x) for x in gear], [str(x) for x in minis])
        out_base.append((int(r.get("score") or 0), int(r.get("fg_score") or 0), h))

    out_fg: list[tuple[int, int, str]] = []
    for r in fg_rows:
        if not isinstance(r, dict):
            continue
        gear = r.get("gear") or []
        minis = r.get("minis") or []
        h = str(r.get("loadout_hash") or "").strip()
        if not h:
            h = _loadout_hash_from_names([str(x) for x in gear], [str(x) for x in minis])
        out_fg.append((int(r.get("fg_score") or 0), int(r.get("score") or 0), h))

    return out_base, out_fg


def _first_diff(a: list[tuple], b: list[tuple]) -> int | None:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return n
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="Compare on-demand tier recompute vs legacy DB tier materialization.")
    p.add_argument("--legacy", type=str, default="evolution_legacy.db", help="Legacy v17 DB path (default: evolution_legacy.db).")
    p.add_argument("--song", type=str, required=True, help="Song name as stored in DB (songs.name / loadouts.song_name).")
    p.add_argument("--file", type=str, required=True, help="Path to the song .txt file (used to build calc_song).")
    p.add_argument("--baseline", type=str, default="T5", help="Baseline tier key to load candidates from (default: T5).")
    p.add_argument("--tiers", type=str, default="NONE,T1,T5,T10,T15", help="Comma tier list to compare.")
    p.add_argument("--limit", type=int, default=51, help="Top-N limit (default: 51).")
    p.add_argument(
        "--hitsim",
        type=str,
        default="cfg",
        choices=("none", "cfg"),
        help=(
            "HumanHitSim mode for recompute. Legacy DB rows may not persist per-row hit-sim context, "
            "so `cfg` applies current config.ini hit-sim settings to the chart (default: cfg)."
        ),
    )
    args = p.parse_args()

    legacy_db = (PROJECT_ROOT / str(args.legacy)) if not Path(str(args.legacy)).is_absolute() else Path(str(args.legacy))
    if not legacy_db.exists():
        raise SystemExit(f"Legacy DB not found: {legacy_db}")

    song_name = str(args.song or "").strip()
    song_file = (PROJECT_ROOT / str(args.file)) if not Path(str(args.file)).is_absolute() else Path(str(args.file))
    if not song_file.exists():
        raise SystemExit(f"Song file not found: {song_file}")

    baseline = str(args.baseline or "").strip().upper() or "T5"
    tiers = tuple(t.strip().upper() for t in str(args.tiers or "").split(",") if t.strip())
    limit = max(1, int(args.limit))

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    calc_song = clone_calc_song(get_base_calc_song(str(song_file), cfg_dict))
    if str(args.hitsim).lower() == "cfg":
        try:
            from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

            apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
        except Exception:
            pass

    conn = sqlite3.connect(str(legacy_db))
    conn.row_factory = sqlite3.Row
    try:
        candidates = _load_baseline_candidates_from_legacy(conn, song_name=song_name, baseline_team_buff=baseline, limit=limit)
        if not candidates:
            raise SystemExit("No baseline candidates loaded from legacy DB.")

        recomputed = compute_team_buff_tier_leaderboards(
            entries=candidates,
            calc_song=calc_song,
            ref_arrays=dict(ref_arrays),
            cfg_dict=dict(cfg_dict) if isinstance(cfg_dict, dict) else dict(cfg_dict),
            limit=limit,
            tiers=tiers,
        )

        ok = True
        for tier in tiers:
            legacy_base, legacy_fg = _load_legacy_top_lists(conn, song_name=song_name, team_buff=tier, limit=limit)
            got_base, got_fg = _computed_top_lists(recomputed, tier)

            diff_b = _first_diff(got_base, legacy_base)
            diff_f = _first_diff(got_fg, legacy_fg)
            tier_ok = diff_b is None and diff_f is None
            ok = ok and tier_ok

            status = "OK" if tier_ok else "DIFF"
            print(
                f"{status} | {tier} | base_rows={len(got_base)} (legacy {len(legacy_base)}) "
                f"fg_rows={len(got_fg)} (legacy {len(legacy_fg)})"
            )
            if diff_b is not None:
                i = diff_b
                a = got_base[i] if i < len(got_base) else None
                b = legacy_base[i] if i < len(legacy_base) else None
                print(f"  base first diff @ {i}: got={a} legacy={b}")
            if diff_f is not None:
                i = diff_f
                a = got_fg[i] if i < len(got_fg) else None
                b = legacy_fg[i] if i < len(legacy_fg) else None
                print(f"  fg first diff @ {i}: got={a} legacy={b}")

        raise SystemExit(0 if ok else 2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
