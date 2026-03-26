from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_tiers(text: str) -> tuple[str, ...]:
    raw = [t.strip().upper() for t in str(text or "").split(",")]
    cleaned = [t for t in raw if t]
    return tuple(cleaned) if cleaned else ("NONE", "T1", "T5", "T10", "T15")


def _print_top(label: str, rows: Iterable[dict], *, score_key: str) -> None:
    rows = list(rows or [])
    if not rows:
        print(f"  {label}: (no rows)")
        return
    best = rows[0] or {}
    gear = best.get("gear") or []
    minis = best.get("minis") or []
    score = int(best.get(score_key, 0) or 0)
    base = int(best.get("score", 0) or 0)
    fg = int(best.get("fg_score", 0) or 0)
    if score_key == "fg_score":
        print(f"  {label}: fg_score={score:,} (base={base:,}) | gear={gear} | minis={minis}")
    else:
        print(f"  {label}: score={score:,} (fg={fg:,}) | gear={gear} | minis={minis}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-score the persisted baseline (typically T5) loadouts under TeamBuff tiers on demand.\n\n"
            "Intended for the default compact `evolution.db` workflow where we do NOT store derived tiers "
            "(T1/T10/T15/NONE) in SQLite."
        )
    )
    parser.add_argument("--song", required=True, help="DB song key (e.g. \"Rainshower (Easy) by Silentroom\")")
    parser.add_argument("--file", required=True, help="Path to the song file (.txt) matching the DB song key")
    parser.add_argument(
        "--tiers",
        default="NONE,T1,T5,T10,T15",
        help="Comma-separated tiers to compute (default: NONE,T1,T5,T10,T15)",
    )
    parser.add_argument("--limit", type=int, default=51, help="Top-N retained candidates to consider (default: 51)")
    parser.add_argument(
        "--db",
        default="",
        help="Override DB path (sets EVOLUTION_DB_PATH for this process). If omitted, uses normal resolution.",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Override config.ini path (sets METAFINDER_CONFIG_PATH for this process).",
    )
    parser.add_argument(
        "--element",
        default="selected",
        choices=("selected", "primary", "secondary"),
        help="Which TeamColor to evaluate tiers under (default: selected song color).",
    )
    parser.add_argument(
        "--team-color",
        default="",
        help="Explicit TeamColor override (e.g. Rush/Flow/Beat/Vibe/Chill). Overrides --element.",
    )
    args = parser.parse_args(argv)

    if args.db:
        os.environ["EVOLUTION_DB_PATH"] = str(args.db)
    if args.config:
        os.environ["METAFINDER_CONFIG_PATH"] = str(args.config)

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import get_best_loadouts, get_evolution_db_path
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)

    resolved_db_path = str(get_evolution_db_path() or "").strip()

    def _available_team_buffs_from_db() -> list[str]:
        if not resolved_db_path:
            return []
        if not os.path.exists(resolved_db_path):
            return []
        tiers: list[str] = []
        try:
            conn = sqlite3.connect(resolved_db_path)
            try:
                for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
                    rows = conn.execute(
                        f"SELECT DISTINCT team_buff FROM {table} WHERE song_name = ?",
                        (str(args.song),),
                    ).fetchall()
                    for (t,) in rows or []:
                        s = str(t or "").strip().upper()
                        if s and s not in tiers:
                            tiers.append(s)
                    if tiers:
                        break
            finally:
                conn.close()
        except Exception:
            return []
        return tiers

    available_tiers = _available_team_buffs_from_db()

    # Resolve baseline tier to seed from.
    try:
        from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict

        cfg_base_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    except Exception:
        cfg_base_team_buff = "T5"

    base_team_buff = str(cfg_base_team_buff or "").strip().upper() or "T5"
    if len(available_tiers) == 1:
        base_team_buff = available_tiers[0]
    elif available_tiers:
        if base_team_buff not in available_tiers:
            base_team_buff = "T5" if "T5" in available_tiers else available_tiers[0]

    # Ensure the tier scorer uses the same baseline tier as the persisted rows.
    cfg_dict_for_tiering = dict(cfg_dict)
    team_section = cfg_dict_for_tiering.get("TeamContributionBuffConstant") or {}
    team_section = dict(team_section) if isinstance(team_section, dict) else {}
    team_section["TeamBuff"] = base_team_buff
    team_section["teambuff"] = base_team_buff
    cfg_dict_for_tiering["TeamContributionBuffConstant"] = team_section

    if base_team_buff != "T5":
        ie = cfg_dict_for_tiering.get("IterationEngine") or {}
        ie = dict(ie) if isinstance(ie, dict) else {}
        ie["AutoSelectBuffAndColor"] = "false"
        ie["autoselectbuffandcolor"] = "false"
        cfg_dict_for_tiering["IterationEngine"] = ie

    # Load persisted candidates (union of top base + top FG rows) for the baseline tier.
    entries = get_best_loadouts(str(args.song), limit=max(1, int(args.limit)), team_buff=str(base_team_buff))
    if not entries:
        print(f"No persisted rows found for song={args.song!r} team_buff={base_team_buff!r}.")
        return 2

    # Build calc_song + ref_arrays (match the tier postprocess path).
    base_calc_song = get_base_calc_song(str(args.file), cfg_dict)
    calc_song = clone_calc_song(base_calc_song)

    # Apply HumanHitSim if enabled, so recomputation matches per-run timing semantics
    # (as long as the seed is deterministic).
    try:
        from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

        apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
    except Exception:
        pass

    try:
        from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached

        ref_arrays = _get_team_buff_ref_arrays_cached()
    except Exception:
        ref_arrays = None
    if ref_arrays is None:
        raise RuntimeError("Failed to load ref_arrays (Stats lookup tables).")

    meta0 = calc_song.get("metadata", {}) or {}
    primary_color = str(meta0.get("Primary Color", "") or "").strip()
    secondary_color = str(meta0.get("Secondary Color", "") or "").strip()
    target_team_color_override = None
    if str(args.team_color or "").strip():
        target_team_color_override = str(args.team_color).strip()
    elif str(args.element).lower() == "primary":
        target_team_color_override = primary_color or None
    elif str(args.element).lower() == "secondary":
        target_team_color_override = secondary_color or primary_color or None

    tiers = _parse_tiers(args.tiers)
    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict_for_tiering,
        limit=max(1, int(args.limit)),
        tiers=tiers,
        target_team_color_override=target_team_color_override,
    )

    meta = payload.get("meta") or {}
    print(f"Song: {args.song}")
    print(
        f"Baseline TeamBuff: {meta.get('base_team_buff')} | "
        f"TeamColor: {meta.get('team_color')} | "
        f"base_team_color={meta.get('base_team_color')} target_team_color={meta.get('target_team_color')}"
    )
    print(f"Candidates: {meta.get('candidate_count')}")

    tiers_out = payload.get("tiers") or {}
    for tier in tiers:
        tier_payload = tiers_out.get(tier) or {}
        print(f"\n[{tier}]")
        _print_top("Base Top1", tier_payload.get("base_top51") or [], score_key="score")
        _print_top("FG Top1", tier_payload.get("fg_top51") or [], score_key="fg_score")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
