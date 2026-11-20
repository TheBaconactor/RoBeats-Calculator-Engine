"""Canonicalization: a solved song's results as the store's rows, every value computed once.

Per loadout of the GA surface:
- identity: the effective loadout hash (gear names + each mini's signature as the song sees it) and the minis as
  their equivalence groups in display rotation;
- meta result: the GA's gem allocation (song fixed stats: the baseline TeamBuff), scored by exact replay (precise:
  score + TimelineFrontier witness, physically validated; non-precise: fixed chart timing, no witness), which must
  give the GA's score; a loadout whose Base play no legal hit timing plays keeps no row;
- Force Greats result, for every loadout the FG stage solved: its result (solved at the song's timing), scored by an
  exact surface replay of a physically validated trace (the FG materializer's); it stays attached whether or not it
  beats the meta score (the store ranks the FG board);
- stored stats: recomputed from the item names and gems, and they must give the scores' stats back.
The rows come in the order the store numbers new loadouts (exact score ties rank by it): the run's best, the
loadouts whose FG result beat the base score it was solved against (FG stage order), then the rest of the surface.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..core.team_buff import team_buff_effect
from ..data.loadout_equivalence import (
    rotate_mini_groups_for_slot_display,
    song_mini_identity_table,
)
from ..gamedata import MINI_ASCENSION_VERSION, STATS, Gear, Mini, SongMini, StatCurves, song_minis
from gear_optimizer.data.loadout_hashing import compact_gear_names, compact_mini_names, loadout_hash_from_sig_strings
from ..solver.scoring.exact_rescore import (
    score_stats_exact_with_timeline_trace,
    score_stats_fixed_timing_exact_batch,
)
from gear_optimizer.trace.reconstruct import UnplayableTrace
from ..solver.timing_envelope import TimedSong
from ..stats import GEM_KINDS, apply_gems, total
from ..store.boards import Row
from ..store.records import FgResult, Loadout, MetaResult, encode_trace
from .results import SolvedFg, SolvedLoadout, SongSolve

logger = logging.getLogger(__name__)

# The stats a score reads, besides the song's and the selected element.
_SCORE_STATS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
_FG_TRACE_KEYS = frozenset(("raw_fever_fill", "real_fever_time", "frontier_trace", "non_fever_base"))


@dataclass(frozen=True, slots=True)
class Identity:
    """A loadout as the store keys it: the effective hash and the minis as their equivalence groups (display
    rotation); `reps` are the groups' representative names, which the stored stats are computed from."""

    loadout_hash: str
    gear: tuple[str, ...]
    groups: tuple[tuple[str, ...], ...]
    reps: tuple[str, ...]


MetaScorer = Callable[[Mapping[str, int], TimedSong, StatCurves, int], tuple[int, dict[str, Any] | None]]


def canonical_rows(
    solve: SongSolve,
    gears: Mapping[str, Gear],
    minis: Mapping[str, Mini],
    *,
    meta_scorer: MetaScorer | None = None,
) -> list[Row]:
    """The store rows of `solve` (`gears`/`minis`: the catalogs it was solved with)."""
    song, curves = solve.timed, solve.curves
    primary, secondary = song.chart.primary, song.chart.secondary
    song_view: dict[str, SongMini] = {m.name: m for m in song_minis(minis.values(), solve.song, primary, secondary)}
    mini_lookup = song_mini_identity_table(song_view, primary, secondary, primary)
    fg_by_index = dict(solve.fg)
    if len(fg_by_index) != len(solve.fg):
        raise ValueError(f"{solve.song}: two FG results for one loadout")
    fixed_tier = team_buff_effect(solve.tier, primary)
    fixed_scores = (
        score_stats_fixed_timing_exact_batch([loadout.stats for loadout in solve.loadouts], song, curves)
        if meta_scorer is None and song.mode == "non-precise"
        else None
    )
    timeline_frontier = None
    if meta_scorer is None and fixed_scores is None and solve.loadouts:
        from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload

        timeline_frontier = build_or_load_timeline_frontier_payload(song, curves)
    base_trace_memo: dict[tuple, dict[str, Any]] = {}
    encoded_meta_by_id: dict[int, tuple[Any, bytes]] = {}
    encoded_fg_by_key: dict[tuple[Any, ...], tuple[Any, bytes]] = {}
    out: list[Row] = []
    seen: set[str] = set()
    for i in row_order(len(solve.loadouts), [i for i, fg in solve.fg if fg.score > fg.paired]):
        loadout = solve.loadouts[i]
        ident = loadout_identity(loadout, song_view, primary, secondary, mini_lookup=mini_lookup)
        if ident.loadout_hash in seen:
            raise ValueError(f"{solve.song}: the GA surface holds loadout {ident.loadout_hash} twice")
        seen.add(ident.loadout_hash)

        pre_gem = total(
            fixed_tier,
            *(gears[n].stats for n in ident.gear if n in gears),
            *(song_view[n].stats for n in ident.reps if n in song_view),
        )

        def stats_of(element: str, allocation: tuple[int, ...], solved: Mapping[str, int]) -> tuple[int, ...]:
            return _verified_stats(pre_gem, ident.loadout_hash, element, allocation, solved, (primary, secondary))

        perfect_time = sum(gears[n].perfect_time for n in ident.gear)
        try:
            if meta_scorer is not None:
                score, meta_trace = meta_scorer(loadout.stats, song, curves, perfect_time)
            elif fixed_scores is not None:
                score, meta_trace = int(fixed_scores[i]), None
            else:
                replay = score_stats_exact_with_timeline_trace(
                    loadout.stats,
                    song,
                    curves,
                    perfect_time,
                    copy=False,
                    memo=base_trace_memo,
                    frontier=timeline_frontier,
                )
                score, meta_trace = int(replay["score"]), replay["TimelineFrontier"]
        except UnplayableTrace as exc:
            logger.warning(
                "%s: no row for loadout %s, its Base play is unplayable: %s", solve.song, ident.loadout_hash, exc
            )
            continue
        if score != loadout.score:
            raise ValueError(f"{solve.song}: loadout {ident.loadout_hash} replays to {score}, not the GA's {loadout.score}")
        meta = MetaResult(
            element=primary, gems=loadout.gems, stats=stats_of(primary, loadout.gems, loadout.stats), updated=0, seq=0
        )
        fg = fg_trace = fg_score = None
        solved = fg_by_index.get(i)
        if solved is not None:
            fg_stats = dict(zip(STATS, solved.stats))
            fg_score, fg_trace = solved.score, _fg_trace(solved, song)
            fg = FgResult(
                element=solved.element,
                gems=solved.gems,
                stats=stats_of(solved.element, solved.gems, fg_stats),
                surface=solved.surface,
                updated=0,
                seq=0,
            )
        record = Loadout(
            mode=solve.timed.mode,
            song=solve.song,
            tier=solve.tier,
            loadout_hash=ident.loadout_hash,
            gear=ident.gear,
            minis=ident.groups,
            primary=primary,
            secondary=secondary,
            mini_ascension=MINI_ASCENSION_VERSION,
            score=score,
            fg_score=fg_score,
            meta=meta,
            fg=fg,
        )
        if meta_trace is None:
            meta_blob = None
        else:
            meta_id = id(meta_trace)
            cached_meta = encoded_meta_by_id.get(meta_id)
            if cached_meta is None:
                meta_blob = encode_trace(meta_trace)
                encoded_meta_by_id[meta_id] = (meta_trace, meta_blob)
            else:
                meta_blob = cached_meta[1]
        if fg_trace is None:
            fg_blob = None
        elif fg_trace.keys() == _FG_TRACE_KEYS:
            frontier_obj = fg_trace["frontier_trace"]
            fg_key = (
                fg_trace["raw_fever_fill"],
                fg_trace["real_fever_time"],
                id(frontier_obj),
                fg_trace["non_fever_base"],
            )
            cached_fg = encoded_fg_by_key.get(fg_key)
            if cached_fg is None:
                fg_blob = encode_trace(fg_trace)
                encoded_fg_by_key[fg_key] = (frontier_obj, fg_blob)
            else:
                fg_blob = cached_fg[1]
        else:
            fg_blob = encode_trace(fg_trace)
        out.append(Row(record, meta_blob, fg_blob))
    return out


def row_order(count: int, fg_indices: Sequence[int]) -> list[int]:
    """Surface indices in store order: the best, the loadouts with a winning FG result (FG stage order), the rest."""
    order = list(dict.fromkeys([0, *fg_indices])) if count else []
    return order + [i for i in range(count) if i not in set(order)]


def loadout_identity(
    loadout: SolvedLoadout,
    song_view: Mapping[str, SongMini],
    primary: str,
    secondary: str,
    *,
    mini_lookup: Mapping[str, tuple[str, tuple[str, ...]]] | None = None,
) -> Identity:
    """The store identity of a meta-selected (primary element) loadout."""
    gear = compact_gear_names(list(loadout.gear))
    names = compact_mini_names(list(loadout.minis))
    lookup = song_mini_identity_table(song_view, primary, secondary, primary) if mini_lookup is None else mini_lookup
    entries = sorted(
        (lookup.get(n) or (f"name|{n}", (n,)) for n in names),
        key=lambda item: item[0],
    )
    groups = rotate_mini_groups_for_slot_display([list(g) for _sig, g in entries if g])
    return Identity(
        loadout_hash=loadout_hash_from_sig_strings(gear, [sig for sig, _g in entries]),
        gear=tuple(gear),
        groups=tuple(tuple(g) for g in groups),
        reps=tuple(g[0] for g in groups if g),
    )


def _verified_stats(
    pre_gem: Mapping[str, int],
    loadout_hash: str,
    element: str,
    allocation: tuple[int, ...],
    solved: Mapping[str, int],
    colors: tuple[str, str],
) -> tuple[int, ...]:
    stats = apply_gems(pre_gem, dict(zip(GEM_KINDS, allocation)), element)
    changed = [k for k in dict.fromkeys((*_SCORE_STATS, *colors, element)) if stats[k] != solved[k]]
    if changed:
        raise ValueError(f"the canonical minis of {loadout_hash} change scoring stats {changed}")
    return tuple(int(stats[s]) for s in STATS)


def stored_stats(
    fixed: Mapping[str, int],
    ident: Identity,
    gears: Mapping[str, Gear],
    song_view: Mapping[str, SongMini],
    element: str,
    allocation: tuple[int, ...],
    solved: Mapping[str, int],
    colors: tuple[str, str],
) -> tuple[int, ...]:
    """A result's stored stats: its gems on the loadout's items with the minis' representatives. They may differ
    from the stats it was solved with only in stats no score reads, else the representatives are wrong."""
    pre_gem = total(
        fixed,
        *(gears[n].stats for n in ident.gear if n in gears),
        *(song_view[n].stats for n in ident.reps if n in song_view),
    )
    return _verified_stats(pre_gem, ident.loadout_hash, element, allocation, solved, colors)


def _fg_trace(solved: SolvedFg, song: TimedSong) -> dict[str, Any]:
    """An FG result's replay witness (validated by the FG materializer); precise results must carry one."""
    if song.mode != "non-precise" and not solved.trace.get("frontier_trace"):
        raise ValueError(f"{song.chart.name}: an FG result without a frontier trace")
    return solved.trace
