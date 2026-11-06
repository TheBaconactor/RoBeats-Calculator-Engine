"""TeamBuff tier replays: a song's stored leaderboard re-solved at other TeamBuff tiers and team colors.

The stored entries supply only the loadout set (gear + minis). Each (tier, team color) re-solves the gems on both
surfaces, because a tier or a team color shifts the stat vector and with it the optimal gem split:
- meta: the gem budget re-allocated from the tier-shifted song fixed stats + the loadout's items by the exact gem search
  (the per-tier optimum, never the stored T5 gems);
- FG: re-allocated through the canonical FG response frontier, scored exactly. The one carry: at precise timing, the
  baseline tier and no team-color shift, nothing differs from the solve that produced the entry, so its stored force
  payload is that optimum and is served verbatim.
The song's timing mode (song.mode) is the timing the replay answers: non-precise puts every hit at its chart time.

Cost per (song, team color): T tiers x L loadouts of gem search, one scoring bundle read, and one trace rebuild per
distinct surface: the traces are shared by the tiers, whose loadouts mostly reach the same surfaces (COMPLEXITY.md
section 11).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from heapq import nsmallest
from typing import Any

from gear_optimizer.chart import Chart
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    normalize_team_buff_sequence,
    team_buff_effect,
)
from gear_optimizer.core.utils import get_selected_element
from gear_optimizer.frontier.fg_cache_keys import fg_response_frontier_bundle_cache_key
from gear_optimizer.frontier.fg_cache_store import release_fg_response_song_memory
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import Gear, Mini, SongMini, StatCurves, song_minis
from gear_optimizer.settings import paths
from gear_optimizer.stats import total
from gear_optimizer.store.fg_payload import require_response_surface
from gear_optimizer.trace.fixed_timing import build_fixed_timing_fg_replays
from gear_optimizer.trace.materialize import FgTraceMaterializationCache
from gear_optimizer.trace.reconstruct import UnplayableTrace

from .scoring.exact_rescore import score_stats_exact_with_timeline_trace
from .scoring.fever_solver import solve_best_fever_combination_batch
from .song_config import baseline_fixed_stats
from .timing_envelope import TimedSong

logger = logging.getLogger(__name__)


def _item_names(items: list) -> list[str]:
    """Stored items as names: an entry's gear and minis are catalog or custom-pool items, or names."""
    return [item if isinstance(item, str) else item.name for item in items]


@dataclass(frozen=True, slots=True)
class _ReplayEntry:
    """A stored entry the tiers re-solve, parsed once."""

    entry: dict
    loadout_hash: str
    gear: list[str]
    minis: list[str]
    items: list[Gear | SongMini]
    source_score: int
    source_fg_base_score: int
    source_fg_score: int
    has_fg: bool  # it carries a valid FG payload (a response surface) and FG is replayed
    perfect_time: int  # its gear's Perfect Time: the hit windows its plans are played at


@dataclass(frozen=True, slots=True)
class _TierResult:
    """One tier's re-solve of the entries, aligned with them: the base witness (Stats, GemCounts, FT, FF) and score, and
    the FG force payload (None: no FG result) and score (0: ranks nowhere on the FG board)."""

    bases: list[dict]
    base_scores: list[int]
    forces: list[dict | None]
    fg_scores: list[int]


def _team_colors(chart: Chart, base_override: Any, target_override: Any) -> tuple[str, str]:
    """(the stored rows' team color: the song's primary unless overridden, the team color the tiers answer for)."""
    base = str(chart.primary if base_override is None else base_override or "").strip()
    return base, base if target_override is None else str(target_override or "").strip()


def _tier_fixed_stats(song_stats: dict, tier: str, base_color: str, target_color: str) -> dict:
    """The song's baseline fixed stats moved from the baseline TeamBuff on the stored color to `tier` on the target's."""
    base = team_buff_effect(OPTIMIZER_BASELINE_TEAM_BUFF, base_color)
    target = team_buff_effect(tier, target_color)
    return song_stats | {stat: song_stats[stat] + target.get(stat, 0) - base.get(stat, 0) for stat in base | target}


def _entry_loadout_items(entry: dict, chart: Chart) -> list[Gear | SongMini]:
    """The loadout's 6 gear + 3 minis, the minis as ``chart``'s song sees them (Mini Ascension).

    The serving paths pass entries whose ``gear``/``minis`` are already items (catalog items, or a job's custom-pool
    items, which only the job knows); stored entries keep item NAME STRINGS, which resolve through the catalog.
    Fails loud when the loadout does not resolve to exactly 6 gear + 3 minis.
    """
    gear = [item for item in entry["gear"][:6] if isinstance(item, Gear)]
    minis = [item for item in entry["minis"][:3] if isinstance(item, (Mini, SongMini))]
    if len(gear) != 6 or len(minis) != 3:
        catalog = load_catalog(paths().game_export)
        gear = [catalog.gears[name] for name in _item_names(entry["gear"]) if name in catalog.gears]
        minis = [catalog.minis[name] for name in _item_names(entry["minis"]) if name in catalog.minis]
    if len(gear) != 6 or len(minis) != 3:
        raise ValueError(
            f"tier re-solve needs 6 gear + 3 minis, got {len(gear)} gear + {len(minis)} minis "
            f"(loadout {entry['loadout_hash']!r})"
        )
    return gear + [
        song_minis([mini], chart.name, chart.primary, chart.secondary)[0] if isinstance(mini, Mini) else mini
        for mini in minis
    ]


def _replay_entries(entries: list[dict], song: TimedSong, *, replay_fg: bool) -> list[_ReplayEntry]:
    """The stored entries with stats, parsed once. The store writes force None for meta-only rows; an FG row without its
    response surface is invalid state."""
    chart = song.chart
    rows = []
    for entry in entries:
        details = entry.get("details") or {}
        if not details.get("Stats"):
            continue
        force = entry.get("force")
        if force is not None:
            require_response_surface(force)
        if song.mode == "non-precise" and chart.secondary:
            # The non-precise re-solve selects the song's primary for the whole batch, as the native optimizer does for
            # meta loadouts; a loadout stored with another selected element would silently diverge from native.
            stored = get_selected_element(force) or get_selected_element(details)
            if stored and stored != chart.primary:
                raise ValueError(
                    f"non-precise re-solve invariant violated: loadout {entry['loadout_hash']!r} persists selected "
                    f"element {stored!r} != song primary {chart.primary!r}; the forced-primary re-solve would diverge "
                    "from native. The re-solve must honor the per-loadout selected element before this can serve."
                )
        score = entry.get("score", 0)
        items = _entry_loadout_items(entry, chart)
        rows.append(
            _ReplayEntry(entry, entry["loadout_hash"], _item_names(entry["gear"]), _item_names(entry["minis"]),
                         items, score, entry.get("fg_base_score", score), entry.get("fg_score", 0),
                         replay_fg and force is not None, sum(gear.perfect_time for gear in items[:6]))
        )
    return rows


def _carried_fg_score(row: _ReplayEntry) -> int:
    """The baseline-tier carry's FG score: the stored fg_score, which every producer sets to the force payload's
    positive exact score. A non-positive one beside a valid force is inconsistent; ranking it would silently drop the
    row (fg_score > 0), so it fails loud."""
    if row.source_fg_score <= 0:
        raise ValueError(
            f"baseline-tier FG carry: loadout {row.loadout_hash!r} carries a valid force payload but a non-positive "
            f"fg_score ({row.source_fg_score}); refusing to silently drop the row. The persisted fg_score IS the exact "
            "surface score and a valid FG force always scores > 0 -- re-canonicalize the source entry."
        )
    return row.source_fg_score


def _resolve_tier(
    rows: list[_ReplayEntry],
    fixed_stats: dict,
    song: TimedSong,
    curves: StatCurves,
    carry_fg: bool,
    trace_cache: FgTraceMaterializationCache,
) -> _TierResult:
    """Re-solve the entries' gems at one tier's fixed stats; `carry_fg`: serve the stored FG payloads instead."""
    primary = song.chart.primary
    pre_gem = [total(fixed_stats, *(item.stats for item in row.items)) for row in rows]
    bases, base_scores = [], []
    for solve in solve_best_fever_combination_batch(pre_gem, song, curves, selected_color=primary):
        pp, cm, fm, ft, ff, element = solve.gems
        bases.append({"Stats": dict(solve.stats), "GemCounts": build_gem_counts(pp, cm, fm, element), "FT": ft, "FF": ff})
        base_scores.append(solve.score)
    forces: list[dict | None] = [None] * len(rows)
    fg_scores = [0] * len(rows)
    fg_rows = [i for i, row in enumerate(rows) if row.has_fg]
    if carry_fg:
        for i in fg_rows:
            forces[i], fg_scores[i] = rows[i].entry["force"], _carried_fg_score(rows[i])
    else:
        replays = build_fixed_timing_fg_replays([pre_gem[i] for i in fg_rows], song, curves, primary, trace_cache,
                                                [rows[i].perfect_time for i in fg_rows])
        for i, force in zip(fg_rows, replays, strict=True):
            # A loadout without an FG result (its plan is unplayable at this timing) ranks nowhere on the FG board.
            forces[i], fg_scores[i] = force, (force or {}).get("Score", 0)
    return _TierResult(bases, base_scores, forces, fg_scores)


def _tier_details(entry: dict, base: dict, song: TimedSong, curves: StatCurves, perfect_time: int) -> dict:
    """A served row's details at a tier: the stored details with the tier's re-solved Stats, GemCounts, FT and FF (never
    the stored T5 allocation, its compact st/gc/gk copies or its witness) and a TimelineFrontier recomputed for those
    Stats. non-precise rows carry no TimelineFrontier: the consumer draws the chart-time timeline from Stats."""
    stale = ("TimelineFrontier", "st", "gc", "gk")
    details = {key: value for key, value in entry["details"].items() if key not in stale} | base
    details["Stats"], details["GemCounts"] = dict(base["Stats"]), dict(base["GemCounts"])
    if song.mode != "non-precise":
        replay = score_stats_exact_with_timeline_trace(details["Stats"], song, curves, perfect_time)
        frontier = replay["TimelineFrontier"]
        if frontier.get("frontier_trace"):
            details["TimelineFrontier"] = frontier
    return details


def _served_rows(
    rows: list[_ReplayEntry], result: _TierResult, n: int, replay_fg: bool, song: TimedSong, curves: StatCurves
) -> list[dict]:
    """A tier's DB-ready rows: its top `n` by base score (ties by loadout hash) and, with `replay_fg`, the top `n` by FG
    score among rows with one, those not already in. An FG row's paired base is the same loadout's re-solved base."""
    indices = range(len(rows))
    meta_top = nsmallest(n, indices, key=lambda i: (-result.base_scores[i], rows[i].loadout_hash))
    fg_top = nsmallest(n, (i for i in indices if rows[i].has_fg and result.fg_scores[i] > 0),
                       key=lambda i: (-result.fg_scores[i], rows[i].loadout_hash))
    in_meta, in_fg = set(meta_top), set(fg_top)
    served = []
    for i in meta_top + [i for i in fg_top if i not in in_meta]:
        row = rows[i]
        try:
            details = _tier_details(row.entry, result.bases[i], song, curves, row.perfect_time)
        except UnplayableTrace as exc:
            logger.warning("%s: no tier row for loadout %s, its Base play is unplayable: %s", song.chart.name,
                           row.loadout_hash, exc)
            continue
        out = {
            "loadout_hash": row.loadout_hash,
            "gear": row.gear,
            "minis": row.minis,
            "score": result.base_scores[i] if i in in_meta else 0,
            "details": details,
            "source_score": row.source_score,
        }
        if replay_fg:
            force = result.forces[i]
            out |= {
                "fg_score": result.fg_scores[i] if i in in_fg else 0,
                "fg_base_score": result.base_scores[i] if i in in_fg else 0,
                "force": None if force is None else dict(force),
                "source_fg_base_score": row.source_fg_base_score if i in in_fg else 0,
                "source_fg_score": row.source_fg_score if i in in_fg else 0,
            }
        served.append(out)
    return served


def build_team_buff_tier_db_batches(
    *,
    entries: list[dict],
    song: TimedSong,
    curves: StatCurves,
    limit: int = 51,
    tiers: tuple[str, ...] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
    replay_surface: str = "both",
) -> dict[str, list[dict]]:
    """DB-ready entry batches per tier: {"T5": [{loadout_hash, gear, minis, score, details, fg_score, fg_base_score,
    force, source_*}, ...], ...}, the fields per `replay_surface`:
    - "meta": the top-N by re-solved base score (no FG fields);
    - "both" (any other value): the top-N by re-solved base score, then the FG-only rows of the top-N by FG score. A row
      outside the FG top-N reports FG score 0, one outside the base top-N base score 0; `force` is the tier's witness
      either way, and a row's `details` the re-solved base, see _tier_details.
    non-precise (song.mode) answers at fixed chart timing: its rankings come from the chart-only response frontier, base
    rows carry no TimelineFrontier and FG rows the re-solved force with its chart-fixed trace; a derived view, never
    persisted to the canonical leaderboards.
    """
    n = max(0, int(limit))
    if not entries or n <= 0:
        return {}
    replay_fg = str(replay_surface or "both").strip().lower() != "meta"
    rows = _replay_entries(entries, song, replay_fg=replay_fg)
    base_color, target_color = _team_colors(song.chart, base_team_color_override, target_team_color_override)
    song_stats = baseline_fixed_stats(song.chart)
    trace_cache = FgTraceMaterializationCache()
    batches: dict[str, list[dict]] = {}
    try:
        for tier in normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS):
            carry_fg = song.mode == "precise" and tier == OPTIMIZER_BASELINE_TEAM_BUFF and base_color == target_color
            fixed_stats = _tier_fixed_stats(song_stats, tier, base_color, target_color)
            result = _resolve_tier(rows, fixed_stats, song, curves, carry_fg, trace_cache)
            batches[tier] = _served_rows(rows, result, n, replay_fg, song, curves)
    finally:
        if replay_fg:
            release_fg_response_song_memory(fg_response_frontier_bundle_cache_key(song, curves))
    return batches
