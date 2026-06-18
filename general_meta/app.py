from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS, TOTAL_ROWS
from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    resolve_baseline_team_buff_from_cfg,
    team_buff_display_label,
    team_buff_effect,
)
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data
from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display
from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches

from .analysis import (
    _ELEMENT_ORDER,
    _relevant_elements_for_category,
    find_most_common_loadout,
    format_gem_counts,
    sort_gears_by_slot,
)
from .db import prepare_team_buff_tier_replay
from .song_scan import get_songs_by_elemental_combo


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


def _representative_mini_names(mini_groups: object) -> list[str]:
    groups = normalize_minis_groups_for_display(mini_groups or [])
    return sorted([min(group) for group in groups if group])


def _assert_known_mini_names(
    mini_names: list[str],
    minis_by_name: Dict[str, dict],
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


def _serialize_details_json(details: object) -> str | None:
    if not isinstance(details, dict) or not details:
        return None
    try:
        return json.dumps(details, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return None


def _build_replayed_loadout_rows_for_song(
    song: dict,
    *,
    team_color: str,
    cfg_dict: dict | None,
    ref_arrays: dict | None,
) -> tuple[dict | None, dict | None, dict[str, list[dict]]]:
    song_name = str((song or {}).get("song_name") or "").strip()
    song_file = str((song or {}).get("file_path") or "").strip()
    if not song_name or not song_file:
        return cfg_dict, ref_arrays, {}

    cfg_dict_out, ref_arrays_out, entries, calc_song, _ = prepare_team_buff_tier_replay(
        song_name=song_name,
        song_file=song_file,
        limit=int(LOADOUTS_PER_SONG_LIMIT),
        element="primary",
        team_color=str(team_color or "").strip() or None,
        cfg_dict=cfg_dict,
        ref_arrays=ref_arrays,
    )
    if not entries:
        return cfg_dict_out, ref_arrays_out, {}

    batches = build_team_buff_tier_db_batches(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays_out,
        cfg_dict=cfg_dict_out,
        limit=int(LOADOUTS_PER_SONG_LIMIT),
        tiers=DEFAULT_TEAM_BUFF_REPLAY_TIERS,
        target_team_color_override=team_color,
    )

    entry_by_hash: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        loadout_hash = str(entry.get("loadout_hash") or "").strip()
        if loadout_hash and loadout_hash not in entry_by_hash:
            entry_by_hash[loadout_hash] = entry

    rows_by_tier: dict[str, list[dict]] = {}
    for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS:
        tier_key = str(tier)
        tier_label = team_buff_display_label(tier_key, default="NONE")
        tier_rows: list[dict] = []
        for row in batches.get(tier_key) or []:
            if not isinstance(row, dict):
                continue
            loadout_hash = str(row.get("loadout_hash") or "").strip()
            orig_entry = entry_by_hash.get(loadout_hash) or {}
            mini_groups = normalize_minis_groups_for_display(orig_entry.get("mini_groups") or [])
            if not mini_groups:
                mini_groups = normalize_minis_groups_for_display([[m] for m in (row.get("minis") or []) if m])

            tier_rows.append(
                {
                    "song_name": song_name,
                    "loadout_hash": loadout_hash,
                    "score": int(row.get("score") or 0),
                    "fg_score": int(row.get("fg_score") or 0),
                    "fg_base_score": int(row.get("fg_base_score") or 0),
                    "gear": list(row.get("gear") or []),
                    "mini_groups": mini_groups,
                    "minis": list(row.get("minis") or []),
                    "details_json": _serialize_details_json(row.get("details")),
                }
            )
        rows_by_tier[tier_label] = tier_rows

    return cfg_dict_out, ref_arrays_out, rows_by_tier


def run_general_meta(cfg, paths: dict) -> dict:
    """
    Main entry point for GeneralMeta optimization.
    """
    import numpy as np

    print("\n" + "=" * 60)
    print("GENERAL META - Cross-Song Optimization")
    print("=" * 60)

    sync_exported_game_data()

    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    _ = cfg
    _ = ref_arrays

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    team_buff_tiers = [team_buff_display_label(tier, default="NONE") for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS]

    def _resolve_team_color(default_color: str) -> str:
        try:
            if cfg is not None and cfg.has_section("TeamContributionBuffConstant"):
                v = cfg.get("TeamContributionBuffConstant", "teamcolor", fallback="").strip()
                if v:
                    return v
                v = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip()
                if v:
                    return v
        except Exception:
            pass
        return str(default_color or "").strip()

    def _team_buff_base_stats(team_buff: str, team_color: str) -> dict:
        return team_buff_effect(team_buff, team_color)

    def _empty_team_buff_winners() -> dict[str, dict]:
        return {tier: {"songs_count_with_data": 0, "winner": None} for tier in team_buff_tiers}

    def _empty_team_buff_loadouts() -> dict[str, list[dict]]:
        return {tier: [] for tier in team_buff_tiers}

    def _build_loadout_entry(loadout_data: dict, selected_element: str, *, team_buff: str, team_color: str) -> dict:
        loadout_key = str(loadout_data.get("loadout_key") or "").strip()
        gear_names = sort_gears_by_slot(loadout_data["gear_names"], gears_by_name)
        minis_groups = normalize_minis_groups_for_display(loadout_data.get("mini_groups") or [])
        mini_names = _representative_mini_names(minis_groups)
        _assert_known_mini_names(
            mini_names,
            minis_by_name,
            context=f"loadout_key={loadout_key or '<unknown>'}, team_buff={team_buff}",
        )
        avg_gems = loadout_data["avg_gems"]
        peak_in_songs = loadout_data.get("peak_in_songs") or []
        peak_in_songs_meta = loadout_data.get("peak_in_songs_meta") or []
        peak_in_songs_fg = loadout_data.get("peak_in_songs_fg") or []
        song_wins = loadout_data.get("song_wins") or []

        stats_base = compute_full_stats(
            gear_names,
            mini_names,
            format_gem_counts(avg_gems),
            selected_element,
            gears_by_name,
            minis_by_name,
            {},
        )
        base_stats = _team_buff_base_stats(team_buff, team_color)
        gem_counts = format_gem_counts(avg_gems)
        full_stats = compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
        )
        return {
            "rank": loadout_data["rank"],
            "loadout_key": loadout_key,
            "team_buff": str(team_buff),
            "gear": gear_names,
            "mini_groups": minis_groups,
            "peak_in_songs": peak_in_songs,
            "peak_in_songs_meta": peak_in_songs_meta,
            "peak_in_songs_fg": peak_in_songs_fg,
            "song_wins": song_wins,
            "songs_with_set": loadout_data["songs_with_set"],
            "win_frequency": loadout_data["win_frequency"],
            "stats_base": stats_base,
            "stats": full_stats,
            "gems": avg_gems,
            "avg_score": loadout_data["avg_score"],
        }

    print("\nScanning songs by elemental combination...")
    songs_by_combo = get_songs_by_elemental_combo(paths)

    for combo, songs in songs_by_combo.items():
        print(f"  {combo[0]}/{combo[1]}: {len(songs)} songs")

    baseline_team_buff = resolve_baseline_team_buff_from_cfg(cfg, default="T5")
    baseline_label = team_buff_display_label(baseline_team_buff, default="T5")
    default_team_buff_label = team_buff_display_label("T5", default="T5")
    print(f"\nPreparing TeamBuff tier replay seed rows (baseline TeamBuff={baseline_label})...")
    replay_cfg_dict: dict | None = None
    replay_ref_arrays: dict | None = None
    song_tier_rows_cache: dict[str, dict[str, list[dict]]] = {}

    results: Dict[str, Any] = {}

    canonical_combos: list[tuple[str, str]] = [(p, s) for p in _ELEMENT_ORDER for s in _ELEMENT_ORDER]
    canonical_combo_set = set(canonical_combos)
    extra_combos = [c for c in songs_by_combo.keys() if c not in canonical_combo_set]
    combos_to_process = canonical_combos + sorted(extra_combos, key=lambda c: (str(c[0]), str(c[1])))

    for primary, secondary in combos_to_process:
        songs = songs_by_combo.get((primary, secondary), [])
        combo_key = f"{primary}/{secondary}"
        print(f"\n--- Processing {combo_key} ({len(songs)} songs) ---")

        if not songs:
            print("  No songs found for this category")
            results[combo_key] = {
                "songs_count": 0,
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": list(
                    _relevant_elements_for_category([{"primary": primary, "secondary": secondary}])
                ),
                "default_team_buff_tier": default_team_buff_label,
                "team_buff_tiers": team_buff_tiers,
                "team_buff_winners": _empty_team_buff_winners(),
                "loadouts_by_team_buff": _empty_team_buff_loadouts(),
                "top_loadouts": [],
            }
            continue

        team_color = _resolve_team_color(primary)
        loadouts_by_tier_by_song: dict[str, dict[str, list[dict]]] = {tier: {} for tier in team_buff_tiers}
        songs_with_data_by_tier: dict[str, set[str]] = {tier: set() for tier in team_buff_tiers}

        for song in songs:
            song_name = str((song or {}).get("song_name") or "").strip()
            if not song_name:
                continue
            rows_by_tier = song_tier_rows_cache.get(song_name)
            if rows_by_tier is None:
                replay_cfg_dict, replay_ref_arrays, rows_by_tier = _build_replayed_loadout_rows_for_song(
                    song,
                    team_color=team_color,
                    cfg_dict=replay_cfg_dict,
                    ref_arrays=replay_ref_arrays,
                )
                song_tier_rows_cache[song_name] = rows_by_tier

            for tier_label in team_buff_tiers:
                tier_rows = list(rows_by_tier.get(tier_label) or [])
                if not tier_rows:
                    continue
                loadouts_by_tier_by_song[tier_label][song_name] = tier_rows
                songs_with_data_by_tier[tier_label].add(song_name)

        loadout_entries_by_tier: dict[str, list[dict]] = _empty_team_buff_loadouts()
        team_buff_winners = _empty_team_buff_winners()

        for tier_label in team_buff_tiers:
            tier_loadouts = find_most_common_loadout(
                songs,
                [],
                minis_by_name,
                top_n=None,
                loadouts_by_song=loadouts_by_tier_by_song.get(tier_label) or {},
                gears_by_name=gears_by_name,
            )
            loadout_entries_by_tier[tier_label] = [
                _build_loadout_entry(loadout_data, primary, team_buff=tier_label, team_color=team_color)
                for loadout_data in tier_loadouts
            ]
            _assert_no_stats_only_duplicate_loadouts(
                loadout_entries_by_tier[tier_label],
                context=f"{combo_key} tier={tier_label}",
            )
            team_buff_winners[tier_label]["songs_count_with_data"] = len(songs_with_data_by_tier[tier_label])
            team_buff_winners[tier_label]["winner"] = (
                loadout_entries_by_tier[tier_label][0] if loadout_entries_by_tier[tier_label] else None
            )

        top_loadouts = loadout_entries_by_tier.get(default_team_buff_label) or loadout_entries_by_tier.get(baseline_label) or []
        if not top_loadouts:
            print("  No loadouts found for this category")
            results[combo_key] = {
                "songs_count": len(songs),
                "selected_element": primary,
                "primary_element": primary,
                "secondary_element": secondary,
                "relevant_elements": list(_relevant_elements_for_category(songs)),
                "default_team_buff_tier": default_team_buff_label,
                "team_buff_tiers": team_buff_tiers,
                "team_buff_winners": team_buff_winners,
                "loadouts_by_team_buff": loadout_entries_by_tier,
                "top_loadouts": [],
            }
            continue

        for loadout_entry in top_loadouts:
            gear_names = sort_gears_by_slot(list(loadout_entry.get("gear") or []), gears_by_name)
            minis_groups = normalize_minis_groups_for_display(loadout_entry.get("mini_groups") or [])
            mini_names = sorted([min(g) for g in minis_groups if g])
            avg_gems = loadout_entry.get("gems") or {}
            peak_in_songs = loadout_entry.get("peak_in_songs") or []

            print(
                f"  #{int(loadout_entry.get('rank') or 0)} loadout: {int(loadout_entry.get('win_frequency') or 0)} wins "
                f"(stats averaged from {int(loadout_entry.get('songs_with_set') or 0)} entries)"
            )
            print(f"    Gear: {gear_names}")
            print(f"    Minis: {mini_names}")
            print(
                f"    Avg Gems: PP={int(avg_gems.get('PP') or 0)}, CM={int(avg_gems.get('CM') or 0)}, "
                f"FM={int(avg_gems.get('FM') or 0)}, FT={int(avg_gems.get('FT') or 0)}, "
                f"FF={int(avg_gems.get('FF') or 0)}, OV={int(avg_gems.get('Element') or 0)}"
            )
            print(f"    Avg Score: {int(loadout_entry.get('avg_score') or 0):,}")
            if peak_in_songs:
                print(f"    Peak In Songs ({len(peak_in_songs)}): {', '.join(peak_in_songs)}")

        winners_to_print = [t for t in team_buff_tiers if team_buff_winners[t]["winner"] is not None]
        if winners_to_print:
            print("  TeamBuff winners (build-time static tier replay):")
            for label in winners_to_print:
                winner = team_buff_winners[label]["winner"] or {}
                minis_groups = winner.get("mini_groups") or []
                mini_names = sorted([min(g) for g in minis_groups if g])
                print(
                    f"    {label}: {int(winner.get('win_frequency') or 0)} wins "
                    f"(from {int(team_buff_winners[label]['songs_count_with_data'] or 0)} songs)"
                )
                print(f"      Gear: {winner.get('gear') or []}")
                print(f"      Minis: {mini_names}")

        results[combo_key] = {
            "songs_count": len(songs),
            "selected_element": primary,
            "primary_element": primary,
            "secondary_element": secondary,
            "relevant_elements": list(_relevant_elements_for_category(songs)),
            "default_team_buff_tier": default_team_buff_label,
            "team_buff_tiers": team_buff_tiers,
            "team_buff_winners": team_buff_winners,
            "loadouts_by_team_buff": loadout_entries_by_tier,
            "top_loadouts": top_loadouts,
        }

    output = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }
    return output


def export_general_meta_json(results: dict, output_path: str = None) -> str:
    if output_path is None:
        output_path = os.path.join(PATHS.script_dir, "artifacts", "general_meta_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults exported to: {output_path}")
    return output_path


__all__ = ["export_general_meta_json", "run_general_meta"]
