"""Canonicalization: a solved song's results as the store's rows, every value computed once.

Per loadout of the GA surface:
- identity: the effective loadout hash (gear names + each mini's signature as the song sees it) and the minis as
  their equivalence groups in display rotation;
- meta result: the gem allocation re-solved exhaustively for the loadout's items (song fixed stats: the baseline
  TeamBuff), scored by exact replay (precise: score + TimelineFrontier witness, physically validated;
  non_precise: fixed chart timing, no witness);
- Force Greats result, for every loadout the FG stage solved: its result (solved at the song's timing), scored by an
  exact surface replay of a physically validated trace (the FG materializer's); it stays attached whether or not it
  beats the meta score (the store ranks the FG board);
- stored stats: recomputed from the item names and gems, and they must give the scores' stats back.
The rows come in the order the store numbers new loadouts (exact score ties rank by it): the run's best, the
loadouts whose FG result beat the base score it was solved against (FG stage order), then the rest of the surface.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.team_buff import team_buff_effect
from ..data.loadout_equivalence import (
    canonical_minis_groups_from_names,
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    rotate_mini_groups_for_slot_display,
)
from ..gamedata import MINI_ASCENSION_VERSION, STATS, Gear, Mini, SongMini, StatCurves, song_minis
from ..helpers.song_helpers.loadout_hashing import compact_gear_names, compact_mini_names
from ..helpers.song_helpers.song_config import baseline_fixed_stats
from ..solver.fg_response_scoring.note_graph import UnplayableTrace
from ..solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace, score_stats_fixed_timing_exact
from ..solver.timing_envelope import TimedSong
from ..stats import GEM_KINDS, named_loadout_stats, total
from ..store.boards import Row
from ..store.records import FgResult, Loadout, MetaResult, encode_trace
from .results import SolvedFg, SolvedLoadout, SongSolve

if TYPE_CHECKING:
    from ..solver.scoring.fever_solver import GemSolve

logger = logging.getLogger(__name__)
# The stats a score reads, besides the song's and the selected element.
_SCORE_STATS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")


@dataclass(frozen=True, slots=True)
class Identity:
    """A loadout as the store keys it: the effective hash and the minis as their equivalence groups (display
    rotation); `reps` are the groups' representative names, which the stored stats are computed from."""

    loadout_hash: str
    gear: tuple[str, ...]
    groups: tuple[tuple[str, ...], ...]
    reps: tuple[str, ...]


def canonical_rows(solve: SongSolve, gears: Mapping[str, Gear], minis: Mapping[str, Mini]) -> list[Row]:
    """The store rows of `solve` (`gears`/`minis`: the catalogs it was solved with)."""
    song, curves = solve.timed, solve.curves
    primary, secondary = song.chart.primary, song.chart.secondary
    song_view: dict[str, SongMini] = {m.name: m for m in song_minis(minis.values(), solve.song, primary, secondary)}
    fg_by_index = dict(solve.fg)
    if len(fg_by_index) != len(solve.fg):
        raise ValueError(f"{solve.song}: two FG results for one loadout")
    items = [[gears[n] for n in x.gear] + [song_view[n] for n in x.minis] for x in solve.loadouts]
    fixed = baseline_fixed_stats(song.chart)
    solves = _meta_resolve(fixed, items, song, curves, primary)

    fixed_tier = team_buff_effect(solve.tier, primary)
    out: list[Row] = []
    seen: set[str] = set()
    for i in row_order(len(solve.loadouts), [i for i, fg in solve.fg if fg.score > fg.paired]):
        ident = loadout_identity(solve.loadouts[i], song_view, primary, secondary)
        if ident.loadout_hash in seen:
            raise ValueError(f"{solve.song}: the GA surface holds loadout {ident.loadout_hash} twice")
        seen.add(ident.loadout_hash)

        def stats_of(element: str, allocation: tuple[int, ...], solved: Mapping[str, int]) -> tuple[int, ...]:
            return stored_stats(fixed_tier, ident, gears, song_view, element, allocation, solved, (primary, secondary))

        meta_gems, meta_stats = solves[i].gems, {k: int(v) for k, v in solves[i].stats.items()}
        try:
            score, meta_trace = _meta_score(meta_stats, song, curves)
        except UnplayableTrace as exc:
            if song.mode != "frame_robust":
                raise
            # No frame timing plays this loadout's Base plan: it gets no row, rather than failing the song.
            logger.warning("%s: no row for %s, its Base plan is unplayable: %s", solve.song, ident.loadout_hash, exc)
            continue
        meta = MetaResult(
            element=primary, gems=meta_gems, stats=stats_of(primary, meta_gems, meta_stats), updated=0, seq=0
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
        out.append(Row(record, encode_trace(meta_trace), encode_trace(fg_trace)))
    return out


def row_order(count: int, fg_indices: Sequence[int]) -> list[int]:
    """Surface indices in store order: the best, the loadouts with a winning FG result (FG stage order), the rest."""
    order = list(dict.fromkeys([0, *fg_indices])) if count else []
    return order + [i for i in range(count) if i not in set(order)]


def loadout_identity(
    loadout: SolvedLoadout, song_view: Mapping[str, SongMini], primary: str, secondary: str
) -> Identity:
    """The store identity of a meta-selected (primary element) loadout."""
    gear = compact_gear_names(list(loadout.gear))
    names = compact_mini_names(list(loadout.minis))
    sigs = [effective_mini_signature_for_name(n, song_view, primary, secondary, primary) for n in names]
    groups = rotate_mini_groups_for_slot_display(
        canonical_minis_groups_from_names(names, song_view, primary, secondary, primary, mini_sigs=sigs)
    )
    return Identity(
        loadout_hash=effective_loadout_hash_from_names(gear, sigs),
        gear=tuple(gear),
        groups=tuple(tuple(g) for g in groups),
        reps=tuple(g[0] for g in groups if g),
    )


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
    stats = named_loadout_stats(
        fixed, ident.gear, ident.reps, gears, song_view, dict(zip(GEM_KINDS, allocation)), element
    )
    changed = [k for k in dict.fromkeys((*_SCORE_STATS, *colors, element)) if stats[k] != solved[k]]
    if changed:
        raise ValueError(f"the canonical minis of {ident.loadout_hash} change scoring stats {changed}")
    return tuple(int(stats[s]) for s in STATS)


def _meta_resolve(
    fixed: Mapping[str, int], items: list[list[Any]], song: TimedSong, curves: StatCurves, primary: str
) -> list[GemSolve]:
    """Each loadout's exhaustive base gem allocation (one GPU dispatch for all)."""
    from ..solver.scoring.fever_solver import solve_best_fever_combination_batch  # loads Taichi

    rows = [total(fixed, *(item.stats for item in row)) for row in items]
    return solve_best_fever_combination_batch(rows, song, curves, selected_color=primary)


def _meta_score(stats: Mapping[str, int], song: TimedSong, curves: StatCurves) -> tuple[int, dict[str, Any] | None]:
    """The exact score of the meta stats and, for precise, the TimelineFrontier witness (the exact replay
    validates it physically when it reconstructs it)."""
    if song.mode == "non-precise":
        return int(score_stats_fixed_timing_exact(stats, song, curves)), None
    replay = score_stats_exact_with_timeline_trace(stats, song, curves)
    return int(replay["score"]), replay["TimelineFrontier"]


def _fg_trace(solved: SolvedFg, song: TimedSong) -> dict[str, Any]:
    """An FG result's replay witness (validated by the FG materializer); precise results must carry one."""
    if song.mode != "non-precise" and not solved.trace.get("frontier_trace"):
        raise ValueError(f"{song.chart.name}: an FG result without a frontier trace")
    return solved.trace
