from __future__ import annotations

import json
import os
from datetime import datetime
from collections.abc import Mapping
from typing import Any, Dict

from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    team_buff_display_label,
    team_buff_effect,
)
from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data
from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display, representative_mini_names
from gear_optimizer.gamedata import Gear, Mini, load_gears, load_minis
from gear_optimizer.settings import ENGINE_ROOT, paths

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


def _song_rows(song_name: str) -> list[dict]:
    """
    The song's stored baseline-tier (T5) leaderboard as General Meta rows (item names, scores, details JSON).

    Every TeamBuff tier of the snapshot is built from these same rows: the tier selector is cosmetic there, and the
    host application re-solves a tier's gems on demand when a user opens it. Real per-tier gems at build time would
    need the timeline + FG response frontier caches and ``build_team_buff_tier_db_batches`` per tier.
    """
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import _flat_item_names
    from gear_optimizer.store.legacy import read_best_loadouts

    rows: list[dict] = []
    for entry in read_best_loadouts(paths().database, song_name, OPTIMIZER_BASELINE_TEAM_BUFF):
        mini_names = _flat_item_names(entry.get("minis") or [])
        details = entry.get("details")
        rows.append(
            {
                "song_name": song_name,
                "loadout_hash": str(entry.get("loadout_hash") or "").strip(),
                "score": int(entry.get("score") or 0),
                "fg_score": int(entry.get("fg_score") or 0),
                "fg_base_score": int(entry.get("fg_base_score") or entry.get("score") or 0),
                "gear": _flat_item_names(entry.get("gear") or []),
                "mini_groups": normalize_minis_groups_for_display(entry.get("mini_groups") or [])
                or normalize_minis_groups_for_display([[m] for m in mini_names if m]),
                "minis": mini_names,
                "details_json": json.dumps(details, separators=(",", ":"), ensure_ascii=False)
                if isinstance(details, dict) and details
                else None,
                "team_buff": OPTIMIZER_BASELINE_TEAM_BUFF,
            }
        )
    return rows


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


def _print_category(top_loadouts: list[dict], team_buff_winners: dict[str, dict]) -> None:
    for entry in top_loadouts:
        gems = entry["gems"]
        print(
            f"  #{entry['rank']} loadout: {entry['win_frequency']} wins "
            f"(stats averaged from {entry['songs_with_set']} entries)"
        )
        print(f"    Gear: {entry['gear']}")
        print(f"    Minis: {sorted([min(g) for g in entry['mini_groups'] if g])}")
        print(
            f"    Avg Gems: PP={gems['PP']}, CM={gems['CM']}, FM={gems['FM']}, FT={gems['FT']}, "
            f"FF={gems['FF']}, OV={gems['Element']}"
        )
        print(f"    Avg Score: {entry['avg_score']:,}")
        if entry["peak_in_songs"]:
            print(f"    Peak In Songs ({len(entry['peak_in_songs'])}): {', '.join(entry['peak_in_songs'])}")
    winners = {label: tier for label, tier in team_buff_winners.items() if tier["winner"] is not None}
    if winners:
        print("  TeamBuff winners (build-time static tier replay):")
    for label, tier in winners.items():
        winner = tier["winner"]
        print(f"    {label}: {winner['win_frequency']} wins (from {tier['songs_count_with_data']} songs)")
        print(f"      Gear: {winner['gear']}")
        print(f"      Minis: {sorted([min(g) for g in winner['mini_groups'] if g])}")


def _category_result(
    primary: str,
    secondary: str,
    songs: list[dict],
    team_buff_tiers: list[str],
    song_rows: dict[str, list[dict]],
    gears_by_name: Mapping[str, Gear],
    minis_by_name: Mapping[str, Mini],
) -> dict:
    """One elemental category (primary/secondary): its ranked sets at every TeamBuff tier."""
    print(f"\n--- Processing {primary}/{secondary} ({len(songs)} songs) ---")
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
        print("  No songs found for this category")
        return result

    loadouts_by_song: dict[str, list[dict]] = {}
    for song in songs:
        song_name = str((song or {}).get("song_name") or "").strip()
        if not song_name:
            continue
        if song_name not in song_rows:
            song_rows[song_name] = _song_rows(song_name)
        if song_rows[song_name]:
            loadouts_by_song[song_name] = song_rows[song_name]
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
    if not top_loadouts:
        print("  No loadouts found for this category")
        return result
    _print_category(top_loadouts, team_buff_winners)
    result["top_loadouts"] = top_loadouts
    return result


def run_general_meta() -> dict:
    """
    Main entry point for GeneralMeta optimization.
    """
    print("\n" + "=" * 60)
    print("GENERAL META - Cross-Song Optimization")
    print("=" * 60)

    sync_exported_game_data()

    gears_by_name = load_gears(paths().gears_csv)
    minis_by_name = load_minis(paths().minis_csv)
    team_buff_tiers = [team_buff_display_label(tier, default="NONE") for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS]

    print("\nScanning songs by elemental combination...")
    songs_by_combo = get_songs_by_elemental_combo()
    for combo, songs in songs_by_combo.items():
        print(f"  {combo[0]}/{combo[1]}: {len(songs)} songs")
    print(f"\nPreparing TeamBuff tier replay seed rows (baseline TeamBuff={_BASELINE_TIER_LABEL})...")

    canonical_combos = [(p, s) for p in _ELEMENT_ORDER for s in _ELEMENT_ORDER]
    extra_combos = sorted((c for c in songs_by_combo if c not in set(canonical_combos)), key=lambda c: (str(c[0]), str(c[1])))
    song_rows: dict[str, list[dict]] = {}
    results: Dict[str, Any] = {
        f"{primary}/{secondary}": _category_result(
            primary,
            secondary,
            songs_by_combo.get((primary, secondary), []),
            team_buff_tiers,
            song_rows,
            gears_by_name,
            minis_by_name,
        )
        for primary, secondary in canonical_combos + extra_combos
    }
    return {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }


def export_general_meta_json(results: dict, output_path: str | None = None) -> str:
    if output_path is None:
        output_path = str(ENGINE_ROOT / "artifacts" / "general_meta_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults exported to: {output_path}")
    return output_path


__all__ = ["export_general_meta_json", "run_general_meta"]
