"""Score reverse-lookup: a shown score and what the game's UI shows beside it, to the sets that give it.

The input is what the user enters and nothing stored: the answer is worked out from the chart, the released catalog and
the stat curves, the same score math run backwards. The all-Perfect score equation leaves a few stat lines near a song's
top and thousands far below it. A ceiling over the released items keeps those a loadout can reach, value tables and a walk
over the items find the loadouts, and gear_optimizer.score confirms every one. A play with other judgments has no such
equation: where its Greats lie is unknown, so its score only bounds its line. It gets the Casual score proof and the ceiling.

Cost in the song's real sizes: prepare O(C E log n) for the walk of C = 25,921 cells, O(P J) for the ceiling over P
(surface, cell) pairs (~60,000) and J vertices, O(U B) for the surfaces' tops, ~0.2 s once per song. A lookup near a song's
top: ~3 ms of invert.perfect_targets and ~1 ms of walks. Far below it, ~40 ms: the first _TARGET_ROWS lines of a sample of
surfaces, and the sets the search budget reaches among them; every stat line is then reachable and nothing public tells
them apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import ceil

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_ORDER, team_buff_effect
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import ELEMENTS, SongMini, StatCurves, empty_stats, song_minis
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT
from gear_optimizer.score import HEAD_NOTES, factors, fg_surface_score
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, named_loadout_stats

from .fever_reach import FeverSurfaces, event_times, fever_span, fever_surfaces, pattern_words, walk_cell
from .invert import perfect_targets, score_ceiling, surface_tops
from .loadouts import (
    BOUND_ROUNDING,
    GEAR_SLOTS,
    PRIMARY,
    SECONDARY,
    FixedStats,
    LoadoutSpace,
    ValueTables,
    fixed_stats,
    loadout_space,
    lowest_at,
    points_conjugate,
    prices_at_gems,
    relaxed_best,
    search_targets,
    time_gem_losses,
    value_tables,
)

_AXIS = MAX_STAT + 1
_STAT_PRICE_SHARES = (1.0, 0.7)
_POINTS_PRICES = (0.6, 1.5)
_SHARPENING_ROUNDS = 6
_BOUND_STEPS = 100
# Stat lines a lookup keeps, and the (CM, FM) pairs it may walk for them: ~100 ms far below a song's top.
_TARGET_ROWS = 1 << 10
_LINE_PAIRS = 20_000_000
_SETS_PER_LINE = 16
_TOPS_FROM = 0.9
_SCRATCH_ROWS = 1 << 15
_PREFERRED_TIER = "T5"
# Items a lookup may try, a target may try, and what opening a target counts for: ~100 ms past the lines at the most.
_SEARCH_ITEMS = 3_000_000
_ITEMS_PER_TARGET = 10_000
_ITEMS_PER_SETUP = 3_000
# The widest Perfect window any build can wear (gems trade stats for Perfect Time): no honest play is judged wider. A
# Perfect Time gem adds at most 2. The counts of them the ceiling is worked out for, ascending.
_WIDEST_PERFECT_TIME = MAX_STAT
_TIME_PER_GEM = 2
_TIME_GEM_COUNTS = (1, 2, 4, 8, 16, 32)
# Fever notes one off-Perfect note may move in the honest ceiling: 2.5 x the most on 3,005 stored dev rows (26). And an
# unreleased item's plausible share over its slot's strongest: an owner decision.
_FEVER_NOTES_PER_NOTE = 64
_PLAUSIBLE_SHARE = 0.25
_MULTIPLIER_ROUNDING = 0.005


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
    fixed_rows: np.ndarray
    vertex_values: np.ndarray
    vertex_prices: np.ndarray
    relief: np.ndarray
    tables: ValueTables
    surface_order: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))
    surface_tops: np.ndarray = field(default_factory=lambda: np.empty(0))
    widest: dict = field(default_factory=dict)  # _widest

    @property
    def ceiling(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.vertex_values, self.vertex_prices, self.relief

    @property
    def power_terms(self) -> np.ndarray:
        points = self.curves.f64["Perfect Points"]
        return np.sort(5.0 * np.arange(points.shape[0]) - 2.0 * points)

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
    values = BOUND_ROUNDING + gifts.max(axis=1) + np.asarray([
        relaxed_best(space.items, space.starts, space.gems, vertex, used) + points_conjugate(curves.f64["Perfect Points"], vertex[0])[0]
        for vertex in prices
    ])
    minis = {mini.name: mini for mini in song_minis(catalog.minis.values(), chart.name, chart.primary, chart.secondary)}
    song = ReverseSong(
        chart, curves, dict(catalog.gears), minis, surfaces, space, tuple(fixed), np.stack([row.row for row in fixed]), values,
        prices, _cell_relief(surfaces.cell_start, surfaces.cells, prices), value_tables(space),
    )
    return _ranked(_sharpened(song))


def _ranked(song: ReverseSong) -> ReverseSong:
    """The song with its surfaces' tops, in a shuffled order: a score that leaves more lines than a lookup keeps keeps
    a sample of every surface, not all of the first few."""
    surfaces = song.surfaces
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    floor = _TOPS_FROM * score_ceiling(arrays, song.multipliers[::2], song.notes, song.ceiling, 0.0, np.inf)[0]
    tops = surface_tops(arrays, song.multipliers[::2], song.notes, song.ceiling, floor)
    order = np.random.default_rng(0).permutation(tops.shape[0])
    return replace(song, surface_order=order, surface_tops=tops[order])


def _sharpened(song: ReverseSong) -> ReverseSong:
    """The song with vertices added at its best lines: the lowest prices there stay tight for the lines around them,
    where most lookups land (a cutting plane over the whole song)."""
    surfaces = song.surfaces
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    space = song.space.items, song.space.starts, song.space.gems
    for _ in range(_SHARPENING_ROUNDS):
        _best, (u, cm, fm, _base) = score_ceiling(arrays, song.multipliers[::2], song.notes, song.ceiling, 0.0, np.inf)
        cells = surfaces.cells[surfaces.cell_start[u] : surfaces.cell_start[u + 1]]
        stats = np.column_stack((np.full(cells.shape, cm), np.full(cells.shape, fm), cells // _AXIS, cells % _AXIS))
        bounds = (song.vertex_values[None, :] - stats @ song.vertex_prices[:, 1:].T).min(axis=1)
        cell = cells[int(np.argmax(bounds))]
        at = np.asarray([0.0, cm, fm, cell // _AXIS, cell % _AXIS])
        prices = song.vertex_prices[np.argmin(song.vertex_values - song.vertex_prices[:, 1:] @ at[1:])].copy()
        bound = lowest_at(space, song.fixed_rows, song.curves.f64["Perfect Points"], at, prices, _BOUND_STEPS)
        song = replace(
            song,
            vertex_values=np.append(song.vertex_values, bound + float(prices[1:] @ at[1:])),
            vertex_prices=np.vstack((song.vertex_prices, prices)),
            relief=np.hstack((song.relief, _cell_relief(surfaces.cell_start, surfaces.cells, prices[None, :]))),
        )
    return song


@dataclass(frozen=True, slots=True)
class ShownPlay:
    """What a player can read of a play: the tool's input contract. score: the Compete score of the results screen and
    every leaderboard; casual_score: Play Info's Casual Mode Score; accuracy: percent as shown; the four counts: the
    results screen's, all or none; gear_power and match_mode: Play Info's; gear_multiplier: the leaderboards' two
    decimals, score / Casual score, for a row with no Play Info."""

    score: int
    casual_score: int | None = None
    accuracy: float | None = None
    perfect: int | None = None
    great: int | None = None
    okay: int | None = None
    miss: int | None = None
    gear_power: int | None = None
    match_mode: str = "Compete"
    gear_multiplier: float | None = None


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
    lines: int  # the exact stat lines under the ceiling that the lookup kept
    finished: bool  # every line was kept and searched to its end
    ceiling: float | None = None  # past the score: the first line found that reaches it
    unreleased: UnreleasedItem | None = None
    evidence: tuple[str, ...] = ()


def _found_set(song: ReverseSong, row: np.ndarray, target: np.ndarray, play: ShownPlay, slack: float) -> FoundSet:
    """A search's found row, after gear_optimizer.score confirms the score."""
    chart = song.chart
    gear = tuple(song.space.names[i] for i in row[:6].tolist())
    minis = tuple(song.space.names[i] for i in row[6:9].tolist())
    pp, cm, fm, ft, ff, element_gems, element_row = row[9:16].tolist()
    colors = {PRIMARY: song.space.primary, SECONDARY: song.space.secondary}
    element = colors.get(element_row, next(color for color in ELEMENTS if color not in colors.values()))
    gems = dict(zip(GEM_KINDS, (pp, cm, fm, ft, ff, element_gems)))
    fixed = song.fixed[row[17]]
    stats = named_loadout_stats(team_buff_effect(fixed.tier, fixed.team_color), gear, minis, song.gears, song.minis, gems, element)
    surfaces = song.surfaces
    surface = FgResponseSurface(*surfaces.words[surfaces.pattern[target[0]]].tolist(), int(surfaces.body_fever[target[0]]), 0, 0)
    value = fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)
    if value != play.score:
        raise ValueError(f"reverse lookup: a set of line {target.tolist()} scores {value}, not {play.score}")
    return FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, slack)


def _slack_of(song: ReverseSong, target: np.ndarray) -> float:
    """How far a target's base sits under the lowest bound the steps find at its stats."""
    at = target[:5].astype(np.float64)
    prices = song.vertex_prices[target[6]].copy()
    space = song.space.items, song.space.starts, song.space.gems
    return lowest_at(space, song.fixed_rows, song.curves.f64["Perfect Points"], at, prices, _BOUND_STEPS) - float(target[5])


def _perfect_sets(play: ShownPlay, song: ReverseSong, limit: int) -> tuple[list[FoundSet], int, bool]:
    """The sets of an all-Perfect play, nearest the loadout bound first, until `limit` stat lines hold sets or the search
    budget ends: the sets, the stat lines, and whether every line was searched to its end."""
    surfaces = song.surfaces
    order = song.surface_order[song.surface_tops >= play.score]
    arrays = surfaces.words, surfaces.coeffs, surfaces.pattern, surfaces.body_fever, surfaces.cell_start, surfaces.cells, order
    power = -1 if play.gear_power is None else play.gear_power
    out = np.empty((_TARGET_ROWS, 8), dtype=np.int64)
    count, every_line = perfect_targets(
        int(play.score), arrays, song.multipliers, song.notes, song.ceiling, (song.power_terms, power), _LINE_PAIRS, out
    )
    targets = out[np.argsort(out[:count, 7], kind="stable"), :7]
    found = np.empty((limit * _SETS_PER_LINE, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    query = targets, power, limit, _SEARCH_ITEMS, _ITEMS_PER_TARGET, _ITEMS_PER_SETUP, _SETS_PER_LINE
    vertices = song.vertex_values, song.vertex_prices
    written, complete = search_targets(space, song.tables.arrays, song.fixed_rows, song.curves.f64["Perfect Points"], vertices, query, found)
    slacks = {t: _slack_of(song, targets[t]) for t in set(found[:written, 16].tolist())}
    sets = [_found_set(song, row, targets[row[16]], play, slacks[row[16]]) for row in found[:written]]
    return sets, count, complete and every_line


def _widest(song: ReverseSong) -> dict:
    """What the widest Perfect window needs, built when a lookup first does: its surfaces, their relief, the ceiling of a
    build with each count of Perfect Time gems, and the Casual scores found per window."""
    if not song.widest:
        surfaces = fever_surfaces(song.chart, song.curves, event_times(song.chart, _WIDEST_PERFECT_TIME))
        arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
        relief = _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
        losses = time_gem_losses(song.space, song.vertex_prices)
        tops = [
            score_ceiling(arrays, song.multipliers[::2], song.notes, (song.vertex_values - gems * losses, song.vertex_prices, relief), 0.0, np.inf)[0]
            for gems in _TIME_GEM_COUNTS
        ]
        song.widest.update(arrays=arrays, relief=relief, tops=tops, casual={})
    return song.widest


def _honest_time(play: ShownPlay, song: ReverseSong) -> int:
    """The most Perfect Time a build can wear that reaches this score: the strongest gear of each slot, and the gems the
    ceiling leaves room for. A gem spent on it gives up a color gem, so near a song's top there is none."""
    gems = next((count - 1 for count, top in zip(_TIME_GEM_COUNTS, _widest(song)["tops"]) if play.score > top), GEM_BUDGET)
    strongest: dict[str, int] = {}
    for gear in song.gears.values():
        strongest[gear.slot] = max(strongest.get(gear.slot, 0), gear.perfect_time)
    return min(sum(strongest.values()) + _TIME_PER_GEM * gems, _WIDEST_PERFECT_TIME)


def _casual_axes(song: ReverseSong, greats: int, perfect_time: int) -> tuple:
    """Cell (0, 0)'s event times at this Perfect Time with this many Greats, its Perfect-only fill and its fever ms."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    return event_times(chart, perfect_time, greats), float(thresholds[0]), float(durations[0]) * 1000.0


def _clean_casual_values(song: ReverseSong, perfect_time: int) -> set[int]:
    """Every Casual score of a clean play: base stats, any timing inside this Perfect window."""
    known = _widest(song)["casual"]
    if perfect_time in known:
        return known[perfect_time]
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, 0, perfect_time)
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
    known[perfect_time] = values
    return values


def _casual_span(song: ReverseSong, greats: int) -> tuple[float, float]:
    """The lowest and highest Casual score of a full combo with this many Greats, at the widest Perfect window: Greats
    move fever past what the ceiling of clean plays holds, so their score does not narrow it."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, greats, _WIDEST_PERFECT_TIME)
    fewest, most = fever_span(times, (ceil(threshold), ceil(threshold + greats / 2.0)), duration)
    normal, full = naked.base * naked.combo, naked.base * naked.combo * naked.fever
    head = min(chart.total_notes, HEAD_NOTES)
    lowest = chart.total_notes * normal - float(np.sum(naked.combo - naked.ramp[:head])) * naked.base
    return lowest + fewest * naked.base * float(naked.ramp[0]) * (naked.fever - 1.0) - greats * 0.25 * full, chart.total_notes * normal + most * (full - normal)


def _casual_window(play: ShownPlay) -> tuple[float, float] | None:
    """The Casual score a play shows: exactly, or within the rounding of its Gear Multiplier."""
    if play.casual_score is not None:
        return float(play.casual_score), float(play.casual_score)
    if play.gear_multiplier is None:
        return None
    return play.score / (play.gear_multiplier + _MULTIPLIER_ROUNDING), play.score / (play.gear_multiplier - _MULTIPLIER_ROUNDING)


def _casual_evidence(play: ShownPlay, song: ReverseSong, judged: Judged) -> str | None:
    """Why the Casual score cannot come from an honest Compete play, if it cannot. The server fills the bar from each
    event's time offset and scores the result the event states (push_note_sequence), so a Perfect stated on a Great's
    offset keeps a Perfect's points and a Great's fill; that moves the casual fever too, and base stats hide nothing.
    Casual matches are out: their client zeroes Perfect Time and their server does not. Okays and Misses drain fever
    and break combos in ways this span does not hold, and a play whose judgments are not shown proves nothing."""
    window = _casual_window(play)
    shown = play.accuracy is not None or play.perfect is not None
    if window is None or not shown or play.match_mode != "Compete" or judged.okay or judged.miss:
        return None
    low, high = window
    if judged.clean:
        values = _clean_casual_values(song, _honest_time(play, song))
        if any(low <= value <= high for value in values):
            return None
        return f"Casual score {low:.0f}..{high:.0f} is none of the {len(values)} a clean play reaches: {sorted(values)[:6]}"
    lowest, highest = _casual_span(song, judged.great_hi)
    if low <= highest and lowest <= high:
        return None
    return f"Casual score {low:.0f}..{high:.0f} is outside {lowest:.0f}..{highest:.0f}, all a play with these Greats reaches"


def _honest_ceiling(play: ShownPlay, song: ReverseSong, judged: Judged) -> tuple[float, float]:
    """The most an honest play scores with any released loadout at any Perfect window, never under a real score, or the
    first line past the play's score; and the base value there."""
    widest = _widest(song)
    spare = float(_FEVER_NOTES_PER_NOTE * (judged.great_hi + judged.okay + judged.miss))
    ceiling = (song.vertex_values, song.vertex_prices, widest["relief"])
    best, line = score_ceiling(widest["arrays"], song.multipliers[::2], song.notes, ceiling, spare, float(play.score))
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


def reverse_score(play: ShownPlay, song: ReverseSong, *, limit: int = 8) -> Reverse:
    """The sets behind a shown play, ranked; or what it would take; or the verdict that no honest play gives it."""
    judged = judged_play(play, song.chart.total_notes)
    found, count, finished = [], 0, judged.clean
    if judged.can_be_clean:
        found, count, finished = _perfect_sets(play, song, limit)
    found.sort(key=lambda row: row.slack)
    evidence = _casual_evidence(play, song, judged)
    if evidence is not None:
        return Reverse("exploited", tuple(found), count, finished, evidence=(evidence,))
    if found:
        return Reverse("sets", tuple(found), count, finished)
    ceiling, base = _honest_ceiling(play, song, judged)
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling, base)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)
