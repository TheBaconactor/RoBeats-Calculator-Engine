from __future__ import annotations

import contextlib
import sqlite3
from datetime import datetime
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    team_buff_display_label,
    team_buff_effect,
)
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display, representative_mini_names
from gear_optimizer.gamedata import Gear, Mini
from gear_optimizer.settings import paths
from gear_optimizer.store.db import load_boards
from gear_optimizer.store.legacy import served_rows
from gear_optimizer.store.schema import connect

from .analysis import (
    _ELEMENT_ORDER,
    _relevant_elements_for_category,
    find_most_common_loadout,
    format_gem_counts,
    sort_gears_by_slot,
)
from .loadout_stats import build_general_meta_loadout_stats
from .song_scan import get_songs_by_elemental_combo

# The tier a category shows first, and the tier the stored rows were solved at.
_DEFAULT_TIER_LABEL = team_buff_display_label("T5", default="T5")
_BASELINE_TIER_LABEL = team_buff_display_label(OPTIMIZER_BASELINE_TEAM_BUFF, default="T5")


def _canonicalize_loadout_identity(loadout: dict) -> tuple:
    loadout_key = str(loadout.get("loadout_key") or "").strip()
    team_buff = str(loadout.get("team_buff") or "").strip()
    gear = tuple(str(name or "").strip() for name in (loadout.get("gear") or []))
    mini_groups = tuple(
        tuple(str(name or "").strip() for name in group)
        for group in normalize_minis_groups_for_display(loadout.get("mini_groups") or [])
    )
    gems = loadout.get("gems") if isinstance(loadout.get("gems"), dict) else {}
    gems_key = tuple(sorted((str(k), int(v or 0)) for k, v in gems.items()))
    return (loadout_key, team_buff, gear, mini_groups, gems_key)


def _stats_payload(loadout: dict) -> tuple:
    stats = loadout.get("stats") if isinstance(loadout.get("stats"), dict) else {}
    stats_base = loadout.get("stats_base") if isinstance(loadout.get("stats_base"), dict) else {}
    stats_key = tuple(sorted((str(k), int(v or 0)) for k, v in stats.items()))
    stats_base_key = tuple(sorted((str(k), int(v or 0)) for k, v in stats_base.items()))
    return (stats_key, stats_base_key)


def _assert_no_stats_only_duplicate_loadouts(loadouts: list[dict], *, context: str) -> None:
    """
    Guardrail: identical loadout identity must never appear with conflicting stats.

    This catches "stats override" drift where a 1:1 loadout identity is duplicated
    and only stat payload differs, which would create ambiguous duplicate entries.
    """
    seen: dict[tuple, tuple[int, tuple]] = {}
    for idx, loadout in enumerate(loadouts):
        identity = _canonicalize_loadout_identity(loadout)
        stats_payload = _stats_payload(loadout)
        previous = seen.get(identity)
        if previous is None:
            seen[identity] = (idx, stats_payload)
            continue
        prev_idx, prev_payload = previous
        if prev_payload != stats_payload:
            raise AssertionError(
                f"GeneralMeta duplicate loadout conflict in {context}: "
                f"identical loadout identity appears at positions {prev_idx + 1} and {idx + 1} "
                "with different stats/stats_base. You cannot override stats for a 1:1 loadout "
                "because it will cause a duplicate; manual review required."
            )


def _assert_known_mini_names(
    mini_names: list[str],
    minis_by_name: Mapping[str, Mini],
    *,
    context: str,
) -> None:
    missing = sorted({name for name in mini_names if name and name not in minis_by_name})
    if not missing:
        return
    preview = ", ".join(missing[:8])
    if len(missing) > 8:
        preview += ", ..."
    raise RuntimeError(
        f"Missing mini stats in GeneralMeta input ({context}): {preview}. "
        "Refresh optimizer CSVs from exported_game_data.json (auto-synced before GeneralMeta and optimizer startup)."
    )


def _song_rows(conn: sqlite3.Connection, song_name: str) -> list[dict]:
    """
    The song's stored baseline-tier (T5) Precise leaderboard as General Meta rows: the rows the optimizer serves (the
    meta board's best, then the FG board's best not already listed), each with the gems of the board it came from.

    Every TeamBuff tier of the snapshot is built from these same rows: the tier selector is cosmetic there, and the
    host application re-solves a tier's gems on demand when a user opens it. Real per-tier gems at build time would
    need the timeline + FG response frontier caches and ``build_team_buff_tier_db_batches`` per tier.
    """
    meta, fg = served_rows(load_boards(conn, PRECISE, song_name, OPTIMIZER_BASELINE_TEAM_BUFF))
    listed = {x.loadout_hash for x in meta}
    served = [(x, x.meta) for x in meta] + [(x, x.fg) for x in fg if x.loadout_hash not in listed]
    return [
        {
            "song_name": song_name,
            "loadout_hash": x.loadout_hash,
            "score": x.score,
            "fg_score": x.fg_score or 0,
            "gear": list(x.gear),
            "mini_groups": normalize_minis_groups_for_display([list(group) for group in x.minis]),
            "gems": result.gems,
            "team_buff": OPTIMIZER_BASELINE_TEAM_BUFF,
        }
        for x, result in served
    ]


def _build_loadout_entry(
    loadout_data: dict,
    selected_element: str,
    *,
    team_buff: str,
    team_color: str,
    gears_by_name: Mapping[str, Gear],
    minis_by_name: Mapping[str, Mini],
) -> dict:
    """One ranked set of a category at one TeamBuff tier: its items, averaged gems and the resulting stats."""
    minis_groups = normalize_minis_groups_for_display(loadout_data["mini_groups"])
    mini_names = representative_mini_names(minis_groups)
    _assert_known_mini_names(
        mini_names, minis_by_name, context=f"loadout_key={loadout_data['loadout_key']}, team_buff={team_buff}"
    )
    gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
    stats_base, stats = build_general_meta_loadout_stats(
        gear_names=gear_names,
        mini_names=mini_names,
        gem_counts=format_gem_counts(loadout_data["avg_gems"]),
        selected_element=selected_element,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        team_buff_stats=team_buff_effect(team_buff, team_color),
    )
    return {
        "rank": loadout_data["rank"],
        "loadout_key": loadout_data["loadout_key"],
        "team_buff": team_buff,
        "gear": gear_names,
        "mini_groups": minis_groups,
        "peak_in_songs": loadout_data["peak_in_songs"],
        "peak_in_songs_meta": loadout_data["peak_in_songs_meta"],
        "peak_in_songs_fg": loadout_data["peak_in_songs_fg"],
        "song_wins": loadout_data["song_wins"],
        "songs_with_set": loadout_data["songs_with_set"],
        "win_frequency": loadout_data["win_frequency"],
        "stats_base": stats_base,
        "stats": stats,
        "gems": loadout_data["avg_gems"],
        "avg_score": loadout_data["avg_score"],
    }


def _category_result(
    primary: str,
    secondary: str,
    songs: list[dict],
    team_buff_tiers: list[str],
    conn: sqlite3.Connection,
    gears_by_name: Mapping[str, Gear],
    minis_by_name: Mapping[str, Mini],
) -> dict:
    """One elemental category (primary/secondary): its ranked sets at every TeamBuff tier."""
    loadouts_by_team_buff: dict[str, list[dict]] = {tier: [] for tier in team_buff_tiers}
    team_buff_winners = {tier: {"songs_count_with_data": 0, "winner": None} for tier in team_buff_tiers}
    result = {
        "songs_count": len(songs),
        "selected_element": primary,
        "primary_element": primary,
        "secondary_element": secondary,
        "relevant_elements": list(
            _relevant_elements_for_category(songs or [{"primary": primary, "secondary": secondary}])
        ),
        "default_team_buff_tier": _DEFAULT_TIER_LABEL,
        "team_buff_tiers": team_buff_tiers,
        "team_buff_winners": team_buff_winners,
        "loadouts_by_team_buff": loadouts_by_team_buff,
        "top_loadouts": [],
    }
    if not songs:
        return result

    loadouts_by_song: dict[str, list[dict]] = {}
    for song in songs:
        song_name = str((song or {}).get("song_name") or "").strip()
        if song_name and (rows := _song_rows(conn, song_name)):
            loadouts_by_song[song_name] = rows
    ranked_sets = find_most_common_loadout(songs, loadouts_by_song, minis_by_name, gears_by_name=gears_by_name)
    for tier in team_buff_tiers:
        entries = [
            _build_loadout_entry(
                loadout_data,
                primary,
                team_buff=tier,
                team_color=primary.strip(),
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
            )
            for loadout_data in ranked_sets
        ]
        _assert_no_stats_only_duplicate_loadouts(entries, context=f"{primary}/{secondary} tier={tier}")
        loadouts_by_team_buff[tier] = entries
        team_buff_winners[tier]["songs_count_with_data"] = len(loadouts_by_song)
        team_buff_winners[tier]["winner"] = entries[0] if entries else None

    top_loadouts = loadouts_by_team_buff.get(_DEFAULT_TIER_LABEL) or loadouts_by_team_buff.get(_BASELINE_TIER_LABEL)
    if top_loadouts:
        result["top_loadouts"] = top_loadouts
    return result


def run_general_meta(database: Path) -> dict:
    """The General Meta of a results database: every elemental category's ranked sets at each TeamBuff tier."""

    catalog = load_catalog(paths().game_export)
    gears_by_name, minis_by_name = catalog.gears, catalog.minis
    team_buff_tiers = [team_buff_display_label(tier, default="NONE") for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS]
    songs_by_combo = get_songs_by_elemental_combo()

    canonical_combos = [(p, s) for p in _ELEMENT_ORDER for s in _ELEMENT_ORDER]
    extra_combos = sorted((c for c in songs_by_combo if c not in set(canonical_combos)), key=lambda c: (str(c[0]), str(c[1])))
    with contextlib.closing(connect(database)) as conn:
        results: Dict[str, Any] = {
            f"{primary}/{secondary}": _category_result(
                primary,
                secondary,
                songs_by_combo.get((primary, secondary), []),
                team_buff_tiers,
                conn,
                gears_by_name,
                minis_by_name,
            )
            for primary, secondary in canonical_combos + extra_combos
        }
    return {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }


__all__ = ["run_general_meta"]
