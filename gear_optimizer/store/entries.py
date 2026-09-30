"""The pipeline's result entries as store candidates (temporary: the stage 4 pipeline builds candidates itself).

An entry is the dict the post-processor persists: score, fg_score, fg_base_score, gear, minis, details (the
meta result: GemCounts, FT, FF, SelectedElement, song colors, TimelineFrontier) and force (the FG payload:
Score, BaseScore, GemCounts, FT, FF, SelectedElement, Stats/BaseStats, response_surface, ForceGreats).
Identity, mini groups and stats follow the version 18 persistence rules: the loadout hash is over gear names
and each mini's stats as the song sees them (equivalent minis share it), minis are stored as their equivalence
groups in display rotation, and both results' stats are recomputed from the item names and gems.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..core.gem_defs import element_gem_count
from ..core.team_buff import team_buff_effect
from ..core.utils import get_selected_element
from ..data.database.loadout_io import _compact_gear_for_db, _compact_minis_for_db
from ..data.loadout_equivalence import (
    canonical_minis_groups_from_names,
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    rotate_mini_groups_for_slot_display,
)
from ..gamedata import ELEMENTS, MINI_ASCENSION_VERSION, STATS, Gear, Mini, SongMini, song_minis
from ..helpers.song_helpers.force_greats.result_application import read_visible_stats
from ..helpers.song_helpers.loadout_hashing import loadout_hash_from_names
from ..stats import GEM_KINDS, gems, named_loadout_stats
from .boards import Candidate, Row
from .records import FgResult, Loadout, MetaResult, encode_trace

# Stats the FG score reads, plus the song's and the selected element (checked when minis are canonicalized).
_SCORE_STATS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")


def candidates_from_entries(
    song: str,
    tier: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    gears: Mapping[str, Gear],
    minis: Mapping[str, Mini],
    stored_colors: tuple[str, str] | None,
    now: int,
    deferred: bool | None = None,
) -> list[Candidate]:
    """Candidates for one song and tier. `stored_colors` are the song's colors in the database (a fallback
    for entries that carry none); `deferred` overrides the entries' _deferred_fg_update flag."""
    fallback = next((_colors(e) for e in entries if any(_colors(e)[:2])), None)
    if fallback is None and stored_colors is not None:
        fallback = (*stored_colors, stored_colors[0])
    song_minis_by_colors: dict[tuple[str, str], dict[str, SongMini]] = {}

    def minis_for(primary: str, secondary: str) -> Mapping[str, Mini | SongMini]:
        key = (primary, secondary)
        if key not in song_minis_by_colors:
            song_minis_by_colors[key] = {m.name: m for m in song_minis(minis.values(), song, primary, secondary)}
        return song_minis_by_colors[key]

    identified = [_identify(entry, fallback, minis_for) for entry in entries]
    # One entry per (score, loadout): the one with the most element gems, then the best FG score.
    best: dict[tuple[int, str], tuple[Mapping[str, Any], _Identity]] = {}
    for entry, ident in zip(entries, identified):
        key = (int(entry.get("score", 0) or 0), ident.loadout_hash)
        kept = best.get(key)
        if kept is None or _dedup_rank(entry) > _dedup_rank(kept[0]):
            best[key] = (entry, ident)
    out: list[Candidate] = []
    for entry, ident in best.values():
        is_deferred = bool(entry.get("_deferred_fg_update")) if deferred is None else deferred
        candidate = _candidate(song, tier, entry, ident, gears, minis_for, now, is_deferred)
        if candidate is not None:
            out.append(candidate)
    return out


class _Identity:
    __slots__ = ("loadout_hash", "gear", "groups", "reps", "colors")

    def __init__(self, loadout_hash, gear, groups, reps, colors):
        self.loadout_hash = loadout_hash
        self.gear = gear
        self.groups = groups
        self.reps = reps
        self.colors = colors  # (primary, secondary, selected) or None


def _identify(entry: Mapping[str, Any], fallback, minis_for) -> _Identity:
    gear = _compact_gear_for_db(entry.get("gear", []))
    names = _compact_minis_for_db(entry.get("minis", []))
    primary, secondary, selected = _colors(entry)
    if not primary and not secondary and fallback is not None:
        primary, secondary, fallback_selected = fallback
        selected = selected or fallback_selected or primary or secondary
    if not primary and not secondary:
        return _Identity(loadout_hash_from_names(gear, names), gear, [[n] for n in names], names, None)
    selected = selected or primary or secondary
    song_view = minis_for(primary, secondary)
    sigs = [effective_mini_signature_for_name(n, song_view, primary, secondary, selected) for n in names]
    groups = canonical_minis_groups_from_names(names, song_view, primary, secondary, selected, mini_sigs=sigs)
    groups = rotate_mini_groups_for_slot_display(groups)
    return _Identity(
        effective_loadout_hash_from_names(gear, sigs),
        gear,
        groups,
        [g[0] for g in groups if g],
        (primary, secondary, selected),
    )


def _colors(entry: Mapping[str, Any]) -> tuple[str, str, str]:
    """(primary, secondary, selected) from the entry's details, else its FG payload."""
    from ..data.loadout_equivalence import extract_song_colors

    colors = extract_song_colors(entry.get("details") or {})
    if colors[0] or colors[1]:
        return colors
    force = entry.get("force")
    if isinstance(force, dict):
        for source in (force.get("details"), force):
            found = extract_song_colors(source if isinstance(source, dict) else {})
            if found[0] or found[1]:
                return (found[0], found[1], found[2] or colors[2])
    return colors


def _dedup_rank(entry: Mapping[str, Any]) -> tuple[int, int]:
    gem_counts = (entry.get("details") or {}).get("GemCounts") or {}
    return (element_gem_count(gem_counts) if gem_counts else 0, entry.get("fg_score", 0) or 0)


def _candidate(song, tier, entry, ident: _Identity, gears, minis_for, now: int, deferred: bool) -> Candidate | None:
    if ident.colors is None:
        raise ValueError(f"{song}: an entry without song colors cannot be stored")
    primary, secondary, _selected = ident.colors
    song_view = minis_for(primary, secondary)
    fixed = team_buff_effect(tier, primary)
    known = all(n in gears for n in ident.gear) and all(n in song_view for n in ident.reps)
    ascension = MINI_ASCENSION_VERSION if any(isinstance(song_view.get(n), SongMini) for n in ident.reps) else None

    def result_stats(allocation: dict[str, int], element: str, given: Mapping[str, Any] | None) -> tuple[int, ...]:
        if known:
            stats = named_loadout_stats(fixed, ident.gear, ident.reps, gears, song_view, allocation, element)
        elif given:
            stats = given
        else:
            raise ValueError(f"{song}: no stats for a loadout with items the catalog does not know")
        return tuple(int(stats[s]) for s in STATS)

    details = entry.get("details") or {}
    score = int(entry.get("score", 0) or 0)
    meta = meta_trace = None
    if not deferred:
        element = get_selected_element(details, "") or ident.colors[2]
        meta_allocation = _allocation(details.get("GemCounts") or {}, details, element)
        meta = MetaResult(
            element=element,
            gems=tuple(meta_allocation[k] for k in GEM_KINDS),
            stats=result_stats(meta_allocation, element, details.get("Stats")),
            updated=now,
            seq=0,
        )
        meta_trace = details.get("TimelineFrontier") or None

    fg = fg_trace = None
    fg_score = int(entry.get("fg_score", 0) or 0)
    force = entry.get("force")
    if isinstance(force, dict):
        fg_score = fg_score if fg_score > 0 else _force_score(force)
        paired = int(entry.get("fg_base_score") or 0) or int(force.get("BaseScore") or 0) or score
        if deferred:
            # A deferred update's details describe its FG allocation; its loadout's base score is the paired one.
            score = paired
        if fg_score > paired:
            fg, fg_trace = _fg_result(song, force, fg_score, ident, result_stats, now)
    if meta is None and fg is None:
        return None
    loadout = Loadout(
        song=song,
        tier=tier,
        loadout_hash=ident.loadout_hash,
        gear=tuple(ident.gear),
        minis=tuple(tuple(g) for g in ident.groups),
        primary=primary,
        secondary=secondary,
        mini_ascension=ascension,
        score=score,
        fg_score=fg_score or None,
        meta=meta,
        fg=fg,
    )
    return Candidate(Row(loadout, encode_trace(meta_trace), encode_trace(fg_trace)), deferred=deferred)


def _fg_result(song, force: Mapping[str, Any], fg_score: int, ident: _Identity, result_stats, now: int):
    element = get_selected_element(force, "") or ident.colors[2]
    allocation = _allocation(force.get("GemCounts") or {}, force, element)
    stats = result_stats(allocation, element, read_visible_stats(dict(force)))
    solved = read_visible_stats(dict(force))
    relevant = [*_SCORE_STATS, *(c for c in ident.colors if c)]
    changed = [k for k in dict.fromkeys(relevant) if int(solved.get(k, 0) or 0) != stats[STATS.index(k)]]
    if changed:
        raise ValueError(f"{song}: canonical mini representatives change FG scoring stats {changed}")
    meta = force.get("ForceGreats")
    if not isinstance(meta, dict) or not meta.get("frontier_trace"):
        raise ValueError(f"{song}: FG payload without a frontier trace")
    trace = {k: v for k, v in meta.items() if k != "final_score"}
    result = FgResult(
        element=element,
        gems=tuple(allocation[k] for k in GEM_KINDS),
        stats=stats,
        surface=tuple(int(v) for v in force["response_surface"]),
        updated=now,
        seq=0,
    )
    return result, trace


def _allocation(gem_counts: Mapping[str, Any], container: Mapping[str, Any], element: str) -> dict[str, int]:
    return gems(
        pp=gem_counts.get("Perfect Points", 0) or 0,
        cm=gem_counts.get("Combo Multiplier", 0) or 0,
        fm=gem_counts.get("Fever Multiplier", 0) or 0,
        ft=int(container.get("FT", 0) or 0),
        ff=int(container.get("FF", 0) or 0),
        element=element_gem_count(gem_counts) if element in ELEMENTS else 0,
    )


def _force_score(force: Mapping[str, Any]) -> int:
    for key in ("score", "Score"):
        if int(force.get(key, 0) or 0) > 0:
            return int(force[key])
    return int((force.get("ForceGreats") or {}).get("final_score", 0) or 0)
