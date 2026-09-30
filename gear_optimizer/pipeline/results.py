"""A solved song: what the in-flight pipeline hands to canonicalization and the store.

The song as timed for the solve, the stat curves, the GA's selected surface (the best effective loadouts, best
first) and the Force Greats results the FG stage published for some of them, in the order it published them.
Built from the pipeline's decode surface and FG variants (song_solve) until the GA and FG stages return typed
results themselves.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..core.gem_defs import element_gem_count
from ..core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from ..core.utils import get_selected_element
from ..gamedata import ELEMENTS, STATS, StatCurves
from ..helpers.song_helpers.fg_payload import require_response_surface, strip_retired_fg_fields
from ..helpers.song_helpers.force_greats.result_application import read_visible_stats
from ..helpers.song_helpers.ga_entry_utils import materialize_candidate_names
from ..helpers.song_helpers.item_utils import names_list
from ..solver.timing_envelope import TimedSong
from ..stats import GEM_KINDS, gems


@dataclass(frozen=True, slots=True)
class SolvedFg:
    """A Force Greats result as the FG stage solved it."""

    element: str
    gems: tuple[int, ...]  # per stats.GEM_KINDS
    stats: tuple[int, ...]  # per gamedata.STATS, gems applied: the stats its score was computed from
    surface: tuple[int, ...]  # the response surface the score replays from
    trace: dict[str, Any]  # the replay witness (ForceGreats without its score)
    score: int
    paired: int  # the base score it was solved against (the FG stage's own gate: a winner beats it)


@dataclass(frozen=True, slots=True)
class SolvedLoadout:
    gear: tuple[str, ...]  # 6 names, slot order
    minis: tuple[str, ...]  # 3 names


@dataclass(frozen=True, slots=True)
class SongSolve:
    song: str  # the results key (the chart's song name)
    tier: str
    timed: TimedSong
    curves: StatCurves
    loadouts: tuple[SolvedLoadout, ...]  # the selected GA surface, best first
    fg: tuple[tuple[int, SolvedFg], ...]  # (index into loadouts, its FG result) in the FG stage's order (FG score)


def song_solve(song: Any) -> SongSolve:
    """The results of a NativeSong whose FG stage has finished."""
    runtime = song.runtime
    if not runtime.decode.fg_surface_prepared or runtime.fg.fg_variants is None:
        raise RuntimeError(f"{song.config.task_key}: results are read after the FG stage")
    loadouts = []
    for candidate in runtime.decode.ga_candidates:
        gear, minis = materialize_candidate_names(candidate, registry=song.gpu_inputs.registry, mutate=False)
        loadouts.append(SolvedLoadout(tuple(gear), tuple(minis)))
    index = {(x.gear, x.minis): i for i, x in enumerate(loadouts)}
    fg = []
    for variant in runtime.fg.fg_variants:
        key = (tuple(names_list(variant["gear"])), tuple(names_list(variant["minis"])))
        if key not in index:
            raise RuntimeError(f"{song.config.task_key}: an FG result for a loadout outside the GA surface {key}")
        fg.append((index[key], solved_fg(variant["data"], default_element=song.gpu_inputs.meta_primary_color)))
    return SongSolve(
        song=str(song.config.db_key),
        tier=OPTIMIZER_BASELINE_TEAM_BUFF,
        timed=song.gpu_inputs.timed_song,
        curves=song.gpu_inputs.curves,
        loadouts=tuple(loadouts),
        fg=tuple(fg),
    )


def solved_fg(payload: Mapping[str, Any], *, default_element: str) -> SolvedFg:
    """An FG payload (Score, GemCounts, FT, FF, Selected Element, Stats, response_surface, ForceGreats)."""
    element = get_selected_element(payload, "") or default_element
    trace = {k: v for k, v in payload["ForceGreats"].items() if k != "final_score"}
    return SolvedFg(
        element=element,
        gems=gem_allocation(payload, element),
        stats=stats_tuple(read_visible_stats(dict(payload))),
        surface=tuple(require_response_surface(payload)),
        trace=strip_retired_fg_fields(trace, parent_key="ForceGreats")[0],
        score=int(payload["Score"]),
        paired=int(payload["BaseScore"]),
    )


def gem_allocation(result: Mapping[str, Any], element: str) -> tuple[int, ...]:
    """The GEM_KINDS counts of a gem result (GemCounts + FT + FF); element gems count only for an element."""
    counts = result.get("GemCounts") or {}
    allocation = gems(
        pp=counts.get("Perfect Points", 0) or 0,
        cm=counts.get("Combo Multiplier", 0) or 0,
        fm=counts.get("Fever Multiplier", 0) or 0,
        ft=int(result.get("FT", 0) or 0),
        ff=int(result.get("FF", 0) or 0),
        element=element_gem_count(counts) if element in ELEMENTS else 0,
    )
    return tuple(allocation[k] for k in GEM_KINDS)


def stats_tuple(stats: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(int(stats[s]) for s in STATS)
