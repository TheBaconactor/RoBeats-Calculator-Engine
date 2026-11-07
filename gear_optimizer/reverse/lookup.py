"""Score reverse-lookup: a shown score and what the game's UI shows beside it, to the sets that give it.

The all-Perfect score equation leaves a few stat lines per surface; a ceiling over the released items keeps those a
loadout can reach, a walk over the items finds the loadouts, and gear_optimizer.score confirms every one. A play with
other judgments has no such equation: where its Greats lie is unknown, so its score only bounds its line. It gets the
stored plans of its song, the Casual score proof and the ceiling.

Cost in the song's real sizes: prepare O(C E log n) for the walk of C = 25,921 cells, O(P J) for the ceiling over P
(surface, cell) pairs (~60,000) and J vertices, ~30 + 6 dual solves: 0.1-0.5 s, once per song. A lookup near a song's top:
~5 ms of invert.perfect_lines, 0.3 ms per dual solve, milliseconds of walks. Far below the top it takes ~0.5 s and
lists whatever sets the search budget reaches: every stat line is then reachable and only Gear Power tells them apart.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from math import ceil

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_ORDER, team_buff_effect
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import ELEMENTS, STATS, SongMini, StatCurves, empty_stats, song_minis
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.score import HEAD_NOTES, factors, fg_surface_score
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, named_loadout_stats
from gear_optimizer.store.records import Loadout

from .fever_reach import FeverSurfaces, event_times, fever_span, fever_surfaces, pattern_words, walk_cell
from .invert import line_targets, perfect_lines, score_ceiling
from .loadouts import (
    GEAR_SLOTS,
    FixedStats,
    LoadoutSpace,
    fixed_stats,
    loadout_space,
    lowest_bound,
    points_conjugate,
    prices_at_gems,
    relaxed_best,
    walk_loadouts,
)

_AXIS = MAX_STAT + 1
_STAT_PRICE_SHARES = (1.0, 0.7)
_POINTS_PRICES = (0.6, 1.5)
_SHARPENING_ROUNDS = 6
_BOUND_STEPS = 200
_LINE_ROWS = 1 << 14
_TARGET_ROWS = 1 << 15
_FOUND_ROWS = 16
_SCRATCH_ROWS = 1 << 15
_PREFERRED_TIER = "T5"
# Items a lookup may try, and what a dual solve counts for: ~60 ms past the lines.
_SEARCH_ITEMS = 5_000_000
_ITEMS_PER_TARGET = 400_000
_ITEMS_PER_BOUND = 30_000
# The widest Perfect window any build can wear (gems trade stats for Perfect Time): no honest play is judged wider.
_WIDEST_PERFECT_TIME = MAX_STAT
# The most fever notes one off-Perfect note moved on the dev rows, and an unreleased item's plausible share over its
# slot's strongest: an owner decision.
_FEVER_NOTES_PER_NOTE = 12
_PLAUSIBLE_SHARE = 0.25


@jit(nopython=True, cache=True)
def _cell_relief(cell_start, cells, prices):
    """Per surface and vertex, the most a cell of the surface gives back at the vertex's FT and FF prices."""
    relief = np.empty((cell_start.shape[0] - 1, prices.shape[0]))
    for u in range(relief.shape[0]):
        for j in range(relief.shape[1]):
            best = -1.0e18
            for k in range(cell_start[u], cell_start[u + 1]):
                best = max(best, -prices[j, 3] * (cells[k] // _AXIS) - prices[j, 4] * (cells[k] % _AXIS))
            relief[u, j] = best
    return relief


@dataclass(frozen=True, slots=True, eq=False)
class ReverseSong:
    """A song prepared for lookups: its Perfect timelines, its loadouts and their ceiling over every TeamBuff."""

    chart: Chart
    curves: StatCurves
    gears: dict
    minis: dict[str, SongMini]
    surfaces: FeverSurfaces
    space: LoadoutSpace
    fixed: tuple[FixedStats, ...]
    vertex_values: np.ndarray
    vertex_prices: np.ndarray
    relief: np.ndarray
    top_pp: int
    widest: dict = field(default_factory=dict)  # the surfaces of the widest Perfect window, once a lookup needs them

    @property
    def ceiling(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.vertex_values, self.vertex_prices, self.relief

    @property
    def notes(self) -> tuple[int, int]:
        return min(self.chart.total_notes, HEAD_NOTES), max(0, self.chart.total_notes - HEAD_NOTES)

    @property
    def multipliers(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.curves.f64["Combo Multiplier"], self.curves.combo_ramp, self.curves.f64["Fever Multiplier"]


def prepare_song(chart: Chart, catalog: Catalog, curves: StatCurves) -> ReverseSong:
    surfaces = fever_surfaces(chart, curves, event_times(chart, 0))
    space = loadout_space(catalog, chart.name, chart.primary, chart.secondary)
    fixed = sorted(fixed_stats(space, TEAM_BUFF_TIER_ORDER), key=lambda row: row.tier != _PREFERRED_TIER)
    caps = prices_at_gems(space)
    grid = np.meshgrid(_POINTS_PRICES, *(caps[d] * np.asarray(_STAT_PRICE_SHARES) for d in range(1, 5)), indexing="ij")
    prices = np.stack([axis.ravel() for axis in grid], axis=1)
    used = np.zeros(5)
    gifts = np.asarray([[2.0 * row.row[5] + row.row[6] + price * row.row[0] for row in fixed] for price in prices[:, 0]])
    values = gifts.max(axis=1) + np.asarray([
        relaxed_best(space.items, space.starts, space.gems, vertex, used) + points_conjugate(curves.f64["Perfect Points"], vertex[0])[0]
        for vertex in prices
    ])
    minis = {mini.name: mini for mini in song_minis(catalog.minis.values(), chart.name, chart.primary, chart.secondary)}
    song = ReverseSong(
        chart, curves, dict(catalog.gears), minis, surfaces, space, tuple(fixed), values, prices,
        _cell_relief(surfaces.cell_start, surfaces.cells, prices), max(int(row.row[0]) for row in fixed),
    )
    return _sharpened(song)


def _lowest_at(song: ReverseSong, stats: np.ndarray) -> tuple[float, np.ndarray]:
    """The lowest bound the steps find at stats (minus the top fixed Perfect Points, CM, FM, FT, FF), over every TeamBuff:
    as a vertex value (the bound before the fever stats' prices), and its prices."""
    prices = song.vertex_prices[np.argmin(song.vertex_values - song.vertex_prices[:, 1:] @ stats[1:])].copy()
    space = song.space
    bound = lowest_bound(space.items, space.starts, space.gems, song.curves.f64["Perfect Points"], stats, prices, _BOUND_STEPS)
    gift = max(2.0 * fixed.row[5] + fixed.row[6] + prices[0] * (fixed.row[0] - song.top_pp) for fixed in song.fixed)
    return bound + gift + float(prices[1:] @ stats[1:]), prices


def _sharpened(song: ReverseSong) -> ReverseSong:
    """The song with vertices added at its best lines: the lowest prices there stay tight for the lines around them,
    where most lookups land (a cutting plane over the whole song)."""
    surfaces = song.surfaces
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    for _ in range(_SHARPENING_ROUNDS):
        _best, (u, cm, fm, _base) = score_ceiling(arrays, song.multipliers[::2], song.notes, song.ceiling, 0.0)
        cells = surfaces.cells[surfaces.cell_start[u] : surfaces.cell_start[u + 1]]
        stats = np.column_stack((np.full(cells.shape, cm), np.full(cells.shape, fm), cells // _AXIS, cells % _AXIS))
        cell = cells[int(np.argmax((song.vertex_values[None, :] - stats @ song.vertex_prices[:, 1:].T).min(axis=1)))]
        value, prices = _lowest_at(song, np.asarray([-song.top_pp, cm, fm, cell // _AXIS, cell % _AXIS], dtype=np.float64))
        song = replace(
            song,
            vertex_values=np.append(song.vertex_values, value),
            vertex_prices=np.vstack((song.vertex_prices, prices)),
            relief=np.hstack((song.relief, _cell_relief(surfaces.cell_start, surfaces.cells, prices[None, :]))),
        )
    return song


@dataclass(frozen=True, slots=True)
class ShownPlay:
    """What a player can read of a play: the tool's input contract. score: the Compete score of the results screen and
    every leaderboard; casual_score: Play Info's Casual Mode Score; accuracy: percent as shown; the four counts: the
    results screen's, all or none; gear_power and match_mode: Play Info's."""

    score: int
    casual_score: int | None = None
    accuracy: float | None = None
    perfect: int | None = None
    great: int | None = None
    okay: int | None = None
    miss: int | None = None
    gear_power: int | None = None
    match_mode: str = "Compete"


@dataclass(frozen=True, slots=True)
class Judged:
    """A play's judgments: Greats between great_lo and great_hi (accuracy leaves a range), Okays and Misses."""

    great_lo: int
    great_hi: int
    okay: int
    miss: int

    @property
    def can_be_clean(self) -> bool:
        return self.great_lo == 0 and self.okay == 0 and self.miss == 0

    @property
    def clean(self) -> bool:
        return self.can_be_clean and self.great_hi == 0


def judged_play(play: ShownPlay, notes: int) -> Judged:
    """The judgments a shown play can have. Accuracy alone leaves the Greats of its rounding (a Great costs a quarter
    of a note; Okays and Misses are not told apart); with neither, a clean play is assumed."""
    counts = (play.perfect, play.great, play.okay, play.miss)
    if any(count is not None for count in counts):
        if any(count is None for count in counts):
            raise ValueError("the results screen shows all four counts: give all of them or none")
        return Judged(play.great, play.great, play.okay, play.miss)
    if play.accuracy is None:
        return Judged(0, 0, 0, 0)
    middle = (100.0 - play.accuracy) / 100.0 * notes * 4.0
    spread = 0.005 / 100.0 * notes * 4.0
    return Judged(max(0, ceil(middle - spread)), max(0, int(middle + spread)), 0, 0)


@dataclass(frozen=True, slots=True)
class FoundSet:
    """A released set that gives the score exactly on `surface` (its slack: how far under the loadout bound it sits)."""

    gear: tuple[str, ...]
    minis: tuple[str, ...]
    gems: dict[str, int]
    element: str
    team_buff: str
    team_color: str
    stats: dict[str, int]
    surface: FgResponseSurface
    slack: float


@dataclass(frozen=True, slots=True)
class UnreleasedItem:
    """What a set would need beyond the released items: the slot, the item it would beat, the extra primary points."""

    slot: str
    beats: str
    extra_primary: int
    plausible: bool


@dataclass(frozen=True, slots=True)
class Reverse:
    verdict: str  # sets, unresolved, unreleased or exploited
    sets: tuple[FoundSet, ...]
    lines: int  # the exact stat lines under the ceiling
    finished: bool  # every line was searched to its end
    ceiling: float | None = None
    unreleased: UnreleasedItem | None = None
    evidence: tuple[str, ...] = ()


def _found_row(song: ReverseSong, row: np.ndarray, fixed: FixedStats) -> tuple:
    """A walk's found row as (gear, minis, gems, selected element, final stats)."""
    gear = tuple(song.space.names[i] for i in row[:6].tolist())
    minis = tuple(song.space.names[i] for i in row[6:9].tolist())
    pp, cm, fm, ft, ff, element_gems, element_row = row[9:].tolist()
    colors = {5: song.space.primary, 6: song.space.secondary}
    element = colors.get(element_row, next(color for color in ELEMENTS if color not in colors.values()))
    gems = dict(zip(GEM_KINDS, (pp, cm, fm, ft, ff, element_gems)))
    start = team_buff_effect(fixed.tier, fixed.team_color)
    return gear, minis, gems, element, named_loadout_stats(start, gear, minis, song.gears, song.minis, gems, element)


def _targets_of(song: ReverseSong, lines: np.ndarray, power: int) -> np.ndarray:
    """The lines (surface, CM, FM, base) on their cells: target rows (surface, CM, FM, FT, FF, base) under the vertices
    and at the Gear Power (negative: any), nearest their bound first."""
    points = song.curves.f64["Perfect Points"]
    terms = np.sort(5.0 * np.arange(points.shape[0]) - 2.0 * points)
    out = np.empty((_TARGET_ROWS, 7), dtype=np.int64)
    count = line_targets(lines, song.surfaces.cell_start, song.surfaces.cells, song.ceiling, terms, power, out)
    rows = out[: min(count, _TARGET_ROWS)]
    return rows[np.argsort(rows[:, 6], kind="stable"), :6]


def _tight_bound(song: ReverseSong, target: np.ndarray, cuts: list) -> tuple[float, np.ndarray] | None:
    """The bound of a target row and its prices; None when a bound already found rules it out. A new bound is kept in
    `cuts`: its prices stay nearly as tight for the rows beside it."""
    stats = np.asarray([-song.top_pp, *target[1:5].tolist()], dtype=np.float64)
    if any(value - float(prices[1:] @ stats[1:]) < target[5] for value, prices in cuts):
        return None
    value, prices = _lowest_at(song, stats)
    cuts.append((value, prices))
    bound = value - float(prices[1:] @ stats[1:])
    return (bound, prices) if bound >= target[5] else None


def _loadouts_of(song: ReverseSong, target: np.ndarray, tight: tuple, power: int) -> tuple[list[tuple], int]:
    """The released sets of a target row at this Gear Power: (gear, minis, gems, element, stats, fixed row, slack), and
    the items tried."""
    bound, prices = tight
    gift = max(2.0 * fixed.row[5] + fixed.row[6] + prices[0] * (fixed.row[0] - song.top_pp) for fixed in song.fixed)
    cm, fm, ft, ff, base = target[1:].tolist()
    rows = np.empty((_FOUND_ROWS, 16), dtype=np.int64)
    walk_target = np.asarray([0, cm, fm, ft, ff], dtype=np.int64)
    bases = np.asarray([base, base, power], dtype=np.int64)
    space = song.space
    points = song.curves.f64["Perfect Points"]
    found: list[tuple] = []
    tried = 0
    for fixed in song.fixed:
        slack = bound - gift + prices[0] * (fixed.row[0] - song.top_pp) + 2.0 * fixed.row[5] + fixed.row[6] - base
        if slack >= 0.0 and tried < _ITEMS_PER_TARGET:
            query = (walk_target, bases, slack, prices, fixed.row)
            count, used = walk_loadouts(space.items, space.starts, space.gems, points, query, rows, _ITEMS_PER_TARGET - tried)
            tried += used
            found += [(*_found_row(song, row, fixed), fixed, float(slack)) for row in rows[:count]]
    return found, tried


def _perfect_sets(play: ShownPlay, song: ReverseSong, limit: int) -> tuple[list[FoundSet], int, bool]:
    """The sets of an all-Perfect play, nearest the loadout bound first, until `limit` or the search budget: the sets,
    the lines, and whether every line was searched to its end."""
    chart = song.chart
    surfaces = song.surfaces
    out = np.empty((_LINE_ROWS, 4), dtype=np.int64)
    arrays = surfaces.words, surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    count = perfect_lines(int(play.score), arrays, song.multipliers, song.notes, song.ceiling, out)
    power = -1 if play.gear_power is None else play.gear_power
    found: list[FoundSet] = []
    cuts: list = []
    spent = 0
    finished = count <= _LINE_ROWS
    for target in _targets_of(song, out[: min(count, _LINE_ROWS)], power):
        if len(found) >= limit or spent > _SEARCH_ITEMS:
            return found, count, False
        tight = _tight_bound(song, target, cuts)
        if tight is None:
            continue
        rows, tried = _loadouts_of(song, target, tight, power)
        spent += tried + _ITEMS_PER_BOUND
        surface = FgResponseSurface(*surfaces.words[surfaces.pattern[target[0]]].tolist(), int(surfaces.body_fever[target[0]]), 0, 0)
        for gear, minis, gems, element, stats, fixed, slack in rows:
            value = fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)
            if value != play.score:
                raise ValueError(f"reverse lookup: a set of line {target.tolist()} scores {value}, not {play.score}")
            found.append(FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, slack))
    return found, count, finished


def board_sets(play: ShownPlay, song: ReverseSong, board: Iterable[Loadout]) -> list[FoundSet]:
    """The Force Great plans stored with exactly this score: a play copied from a published plan."""
    chart = song.chart
    found = []
    for row in board:
        if row.fg is None or row.fg_score != play.score:
            continue
        stats = dict(zip(STATS, row.fg.stats))
        surface = FgResponseSurface(*row.fg.surface)
        value = fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)
        if value != play.score:
            raise ValueError(f"reverse lookup: stored plan {row.loadout_hash} scores {value}, not {play.score}")
        gems = dict(zip(GEM_KINDS, row.fg.gems))
        found.append(FoundSet(row.gear, tuple(group[0] for group in row.minis), gems, row.fg.element, row.tier, chart.primary, stats, surface, 0.0))
    return found


def _casual_axes(song: ReverseSong, greats: int) -> tuple:
    """Cell (0, 0)'s event times at the widest window with this many Greats, its Perfect-only fill and its fever ms."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    return event_times(chart, _WIDEST_PERFECT_TIME, greats), float(thresholds[0]), float(durations[0]) * 1000.0


def _clean_casual_values(song: ReverseSong) -> set[int]:
    """Every Casual score of a clean play: base stats, any timing inside the widest Perfect window."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, 0)
    scratch = (np.empty((_SCRATCH_ROWS, 6), dtype=np.int64), np.empty((_SCRATCH_ROWS, 6), dtype=np.int64))
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    written = walk_cell(times, ceil(threshold), duration, scratch, out)
    if written < 0:
        raise ValueError("fever walk: the casual cell outgrew its tables")
    words = pattern_words(out[:written, 0], out[:written, 1])
    values = set()
    for pattern, (lowest, highest, bits) in zip(words.tolist(), out[:written, 2:5].tolist()):
        for body_fever in range(lowest, highest + 1):
            if bits < 0 or (bits >> (body_fever - lowest)) & 1:
                values.add(fg_surface_score(naked, FgResponseSurface(*pattern, body_fever, 0, 0), chart.total_notes))
    return values


def _casual_span(song: ReverseSong, greats: int) -> tuple[float, float]:
    """The lowest and highest Casual score of a full combo with this many Greats."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, greats)
    fewest, most = fever_span(times, (ceil(threshold), ceil(threshold + greats / 2.0)), duration)
    normal, full = naked.base * naked.combo, naked.base * naked.combo * naked.fever
    head = min(chart.total_notes, HEAD_NOTES)
    lowest = chart.total_notes * normal - float(np.sum(naked.combo - naked.ramp[:head])) * naked.base
    return lowest + fewest * naked.base * float(naked.ramp[0]) * (naked.fever - 1.0) - greats * 0.25 * full, chart.total_notes * normal + most * (full - normal)


def _casual_evidence(play: ShownPlay, song: ReverseSong, judged: Judged) -> str | None:
    """Why the Casual score cannot come from an honest Compete play, if it cannot. The server fills the bar from each
    event's time offset and scores the result the event states (push_note_sequence), so a Perfect stated on a Great's
    offset keeps a Perfect's points and a Great's fill; that moves the casual fever too, and base stats hide nothing.
    Casual matches are out: their client zeroes Perfect Time and their server does not. Okays and Misses drain fever
    and break combos in ways this span does not hold."""
    if play.casual_score is None or play.match_mode != "Compete" or judged.okay or judged.miss:
        return None
    if judged.clean:
        values = _clean_casual_values(song)
        if play.casual_score in values:
            return None
        return f"Casual score {play.casual_score} is not one of the {len(values)} a clean play reaches: {sorted(values)[:6]}"
    lowest, highest = _casual_span(song, judged.great_hi)
    if lowest <= play.casual_score <= highest:
        return None
    return f"Casual score {play.casual_score} is outside {lowest:.0f}..{highest:.0f}, all a play with these Greats reaches"


def _honest_ceiling(song: ReverseSong, judged: Judged) -> tuple[float, float]:
    """The most an honest play scores with any released loadout at any Perfect window, never under a real score, and the
    base value there."""
    if not song.widest:
        surfaces = fever_surfaces(song.chart, song.curves, event_times(song.chart, _WIDEST_PERFECT_TIME))
        song.widest.update(arrays=(surfaces.coeffs, surfaces.pattern, surfaces.body_fever))
        song.widest.update(relief=_cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices))
    spare = float(_FEVER_NOTES_PER_NOTE * (judged.great_hi + judged.okay + judged.miss))
    ceiling = (song.vertex_values, song.vertex_prices, song.widest["relief"])
    best, line = score_ceiling(song.widest["arrays"], song.multipliers[::2], song.notes, ceiling, spare)
    return best, line[3]


def _unreleased_item(play: ShownPlay, song: ReverseSong, ceiling: float, base: float) -> UnreleasedItem:
    """The item that would close the gap to the ceiling, in the slot where it stands least over the slot's strongest."""
    space = song.space
    per_point = float(2 * space.gems[5, 5] + space.gems[5, 6]) / float(space.gems[5, 5])
    extra = ceil((float(play.score) / ceiling - 1.0) * base / per_point)
    choices = []
    for slot, name in enumerate((*GEAR_SLOTS, "Mini")):
        weights = space.items[space.starts[slot] : space.starts[slot + 1], 1:].sum(axis=1)
        strongest = int(np.argmax(weights))
        choices.append((extra / max(float(weights[strongest]), 1.0), name, space.names[int(space.starts[slot]) + strongest]))
    share, slot, item = min(choices)
    return UnreleasedItem(slot, item, extra, share <= _PLAUSIBLE_SHARE)


def reverse_score(play: ShownPlay, song: ReverseSong, *, limit: int = 8, board: Iterable[Loadout] = ()) -> Reverse:
    """The sets behind a shown play, ranked; or what it would take; or the verdict that no honest play gives it.
    board: stored loadouts of the song, whose Force Great plans a play may have copied."""
    judged = judged_play(play, song.chart.total_notes)
    found = board_sets(play, song, board)
    count, finished = 0, judged.clean
    if not found and judged.can_be_clean:
        found, count, finished = _perfect_sets(play, song, limit)
    found.sort(key=lambda row: row.slack)
    evidence = _casual_evidence(play, song, judged)
    if evidence is not None:
        return Reverse("exploited", tuple(found), count, finished, evidence=(evidence,))
    if found:
        return Reverse("sets", tuple(found), count, finished)
    ceiling, base = _honest_ceiling(song, judged)
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling, base)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)
