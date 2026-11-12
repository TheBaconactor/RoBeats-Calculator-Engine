from __future__ import annotations

import contextlib
import os
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from gear_optimizer.chart import read_header
from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    team_buff_display_label,
    team_buff_effect,
)
from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.data.game_export import Catalog, load_catalog
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.gamedata import Mini
from gear_optimizer.settings import paths
from gear_optimizer.stats import GEM_KINDS
from gear_optimizer.store.db import load_boards
from gear_optimizer.store.legacy import served_rows
from gear_optimizer.store.schema import connect

from .analysis import ELEMENT_ORDER, RankedSet, Row, Song, ranked_sets, relevant_elements
from .loadout_stats import build_general_meta_loadout_stats

# The tier a category shows first (also the tier the stored rows were solved at).
_DEFAULT_TIER_LABEL = team_buff_display_label("T5", default="T5")
_HEADER_KEYS = ("Song Name", "Primary Color", "Secondary Color")


def _songs_by_colors() -> dict[tuple[str, str], list[Song]]:
    """The official charts' songs grouped by (primary, secondary) color: Hard, Normal, then Easy, in folder order."""
    songs: dict[tuple[str, str], list[Song]] = {}
    for difficulty in ("Hard", "Normal", "Easy"):
        for root, _, files in os.walk(paths().chart_dir(difficulty)):
            for fname in files:
                if not fname.lower().endswith(".txt"):
                    continue
                header = read_header(os.path.join(root, fname))
                name, primary, secondary = (header.get(key, "") for key in _HEADER_KEYS)
                if name and primary:
                    songs.setdefault((primary, secondary), []).append(Song(name, difficulty, primary, secondary))
    return songs


def _song_rows(conn: sqlite3.Connection, song_name: str) -> list[Row]:
    """
    The song's stored baseline-tier (T5) Precise leaderboard: the rows the optimizer serves (the meta board's best,
    then the FG board's best not already listed), each with the gems of the board it came from.

    Every TeamBuff tier of the snapshot is built from these same rows: the tier selector is cosmetic there, and the
    host application re-solves a tier's gems on demand when a user opens it. Real per-tier gems at build time would
    need the timeline + FG response frontier caches and ``build_team_buff_tier_db_batches`` per tier.
    """
    meta, fg = served_rows(load_boards(conn, PRECISE, song_name, OPTIMIZER_BASELINE_TEAM_BUFF))
    listed = {x.loadout_hash for x in meta}
    served = [(x, x.meta) for x in meta] + [(x, x.fg) for x in fg if x.loadout_hash not in listed]
    return [Row(x.loadout_hash, x.score, x.fg_score or 0, x.gear, x.minis, result.gems) for x, result in served]


def _known_mini_names(ranked: RankedSet, minis_by_name: Mapping[str, Mini]) -> list[str]:
    """The set's representative mini names; raises when the game export lacks one of them."""
    names = representative_mini_names([list(group) for group in ranked.mini_groups])
    missing = sorted({name for name in names if name not in minis_by_name})
    if missing:
        preview = ", ".join(missing[:8]) + (", ..." if len(missing) > 8 else "")
        raise RuntimeError(
            f"Missing mini stats in GeneralMeta input (loadout_key={ranked.loadout_key}): {preview}. "
            "The results database names minis the game export does not have."
        )
    return names


def _category_result(
    primary: str,
    secondary: str,
    songs: list[Song],
    team_buff_tiers: list[str],
    conn: sqlite3.Connection,
    catalog: Catalog,
) -> dict:
    """One elemental category (primary/secondary): its ranked sets at every TeamBuff tier."""
    names = dict.fromkeys(song.name for song in songs)  # a song in two folders is read once
    rows_by_song = {name: rows for name in names if (rows := _song_rows(conn, name))}
    sets = [
        (ranked, _known_mini_names(ranked, catalog.minis))
        for ranked in ranked_sets(songs, rows_by_song, catalog.minis, catalog.gears)
    ]

    def entry(ranked: RankedSet, mini_names: list[str], tier: str) -> dict:
        stats_base, stats = build_general_meta_loadout_stats(
            gear_names=ranked.gear,
            mini_names=mini_names,
            gem_counts=dict(zip(GEM_KINDS, ranked.avg_gems.values())),
            selected_element=primary,
            gears_by_name=catalog.gears,
            minis_by_name=catalog.minis,
            team_buff_stats=team_buff_effect(tier, primary),
        )
        return {
            "rank": ranked.rank,
            "loadout_key": ranked.loadout_key,
            "team_buff": tier,
            "gear": list(ranked.gear),
            "mini_groups": [list(group) for group in ranked.mini_groups],
            "peak_in_songs": ranked.peak_in_songs,
            "peak_in_songs_meta": ranked.peak_in_songs_meta,
            "peak_in_songs_fg": ranked.peak_in_songs_fg,
            "song_wins": ranked.song_wins,
            "songs_with_set": ranked.wins,
            "win_frequency": ranked.wins,
            "stats_base": stats_base,
            "stats": stats,
            "gems": ranked.avg_gems,
            "avg_score": ranked.avg_score,
        }

    loadouts_by_team_buff = {tier: [entry(ranked, names, tier) for ranked, names in sets] for tier in team_buff_tiers}
    return {
        "songs_count": len(songs),
        "selected_element": primary,
        "primary_element": primary,
        "secondary_element": secondary,
        # A category without songs shows its own colors.
        "relevant_elements": list(relevant_elements(songs or [Song("", "", primary, secondary)])),
        "default_team_buff_tier": _DEFAULT_TIER_LABEL,
        "team_buff_tiers": team_buff_tiers,
        "team_buff_winners": {
            tier: {"songs_count_with_data": len(rows_by_song), "winner": entries[0] if entries else None}
            for tier, entries in loadouts_by_team_buff.items()
        },
        "loadouts_by_team_buff": loadouts_by_team_buff,
        "top_loadouts": loadouts_by_team_buff[_DEFAULT_TIER_LABEL] or [],
    }


def run_general_meta(database: Path) -> dict:
    """The General Meta of a results database: every elemental category's ranked sets at each TeamBuff tier."""
    catalog = load_catalog(paths().game_export)
    team_buff_tiers = [team_buff_display_label(tier, default="NONE") for tier in DEFAULT_TEAM_BUFF_REPLAY_TIERS]
    songs_by_colors = _songs_by_colors()

    canonical = [(p, s) for p in ELEMENT_ORDER for s in ELEMENT_ORDER]
    extra = sorted(set(songs_by_colors) - set(canonical))
    with contextlib.closing(connect(database)) as conn:
        results = {
            f"{primary}/{secondary}": _category_result(
                primary, secondary, songs_by_colors.get((primary, secondary), []), team_buff_tiers, conn, catalog
            )
            for primary, secondary in canonical + extra
        }
    return {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }
