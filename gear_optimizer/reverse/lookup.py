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
from math import ceil, floor

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_ORDER, team_buff_effect
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import ELEMENTS, SongMini, StatCurves, empty_stats, song_minis
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT
from gear_optimizer.score import HEAD_NOTES, factors, fg_surface_score
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, named_loadout_stats

from .fever_reach import FeverSurfaces, event_times, fever_span, fever_surfaces, great_times, pattern_words, walk_cell
from .greats import HEAD_LISTED, ROW_COLUMNS, band_surfaces, casual_classes, cell_lines, cell_sums, great_rows, head_witness
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
    gem_gaps,
    loadout_space,
    lowest_at,
    points_conjugate,
    prices_at_gems,
    relaxed_best,
    search_targets,
    time_gem_losses,
    value_tables,
    with_points_stat,
)

_AXIS = MAX_STAT + 1
_STAT_PRICE_SHARES = (1.0, 0.7)
_POINTS_PRICES = (0.6, 1.5)
_SHARPENING_ROUNDS = 6
_BOUND_STEPS = 100
# Stat lines a lookup keeps, and the (CM, FM) pairs it may walk for them.
_TARGET_ROWS = 1 << 14
_LINE_PAIRS = 20_000_000
_SETS_PER_LINE = 16
_TOPS_FROM = 0.9
_SCRATCH_ROWS = 1 << 15
_PREFERRED_TIER = "T5"
# A play with Greats is searched from this share of the song's top: below it far more sets fit than the numbers tell apart.
_GREATS_FROM = 0.9
# The most Greats a lookup searches, the most whose timelines it walks, and past those how far from a walked timeline it looks:
# a dev run's most, 4 notes up to 64 Greats, doubled. The rows it keeps, and the (pair, base) rows it may walk.
_GREATS_SEARCHED = 64
# The most quarters only Greats can cost: an Okay costs three.
_ONLY_GREATS = 2
_GREATS_WALKED = 8
_BAND_NOTES = 8
_GREAT_ROWS = 1 << 18
_GREAT_PAIRS = 3_000_000
_GREAT_SEARCH_ITEMS = 300_000_000
# The loadouts a search rescores exactly, lowest gem gap first, and the rows it tries on each.
_GREAT_SETS_TRIED = 512
_ROWS_PER_SET = 32
# Lines that may hold loadouts before they are ranked.
_HELD_LINES = 256
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
    line_shape: np.ndarray = field(default_factory=lambda: np.empty((0, 4)))  # per cell, its chart-time timeline's shape
    widest: dict = field(default_factory=dict)  # _widest
    budgets: dict = field(default_factory=dict)  # _great_surfaces
    walked: dict = field(default_factory=dict)  # _great_surfaces

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
    surfaces = fever_surfaces(chart, curves, 0)
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


def _chart_shapes(chart: Chart, curves: StatCurves) -> np.ndarray:
    """Per (Fever Time, Fever Fill) cell the bound shape of its chart-time timeline, what a set plain-scores by."""
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)
    fever, normal = np.zeros((_AXIS, _AXIS), np.int32), np.zeros((_AXIS, _AXIS), np.int32)
    words = np.zeros((_AXIS, _AXIS, 4), np.uint32)
    extra = np.zeros((_AXIS, _AXIS), np.int32), np.zeros((_AXIS, _AXIS), np.int32)
    calculate_fever_timeline_surface_grid(chart.timestamps, chart.total_notes, durations, np.ceil(thresholds).astype(np.int64), (fever, normal, words, *extra))
    head = min(chart.total_notes, HEAD_NOTES)
    coeffs = surface_head_coeffs(np.concatenate((words.reshape(-1, 4), np.zeros((_AXIS * _AXIS, 4), np.uint32)), axis=1), head_len=head).astype(np.float64)
    body_fever = fever.reshape(-1).astype(np.float64)
    body_normal = normal.reshape(-1).astype(np.float64)
    ramp_fever, ramp_normal = coeffs[:, 3] * 0.01, coeffs[:, 2] * 0.01
    return np.column_stack((body_fever + ramp_fever, body_normal + ramp_normal, coeffs[:, 1] - ramp_fever, coeffs[:, 0] - ramp_normal))


def _ranked(song: ReverseSong) -> ReverseSong:
    """The song with its surfaces' tops, in a shuffled order: a score that leaves more lines than a lookup keeps keeps
    a sample of every surface, not all of the first few."""
    surfaces = song.surfaces
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    floor = _TOPS_FROM * score_ceiling(arrays, song.multipliers[::2], song.notes, song.ceiling, 0.0, np.inf)[0]
    tops = surface_tops(arrays, song.multipliers[::2], song.notes, song.ceiling, floor)
    order = np.random.default_rng(0).permutation(tops.shape[0])
    return replace(song, surface_order=order, surface_tops=tops[order], line_shape=_chart_shapes(song.chart, song.curves))


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
class PlayInfo:
    """A play as the Top Scores menu shows it, the tool's whole input: a row's accuracy (percent), score, mode and Gear
    Multiplier (score / Casual score, two decimals), and what its View button adds: the Casual Mode Score and Gear Power."""

    score: int
    accuracy: float | None = None
    casual_score: int | None = None
    gear_multiplier: float | None = None
    gear_power: int | None = None
    match_mode: str = "Compete"


def lost_quarters(play: PlayInfo, notes: int) -> tuple[int, int]:
    """The lowest and highest quarters of a note a play's accuracy can have lost: a Great costs one, an Okay three, a Miss
    four, and the two decimals leave a range. A bare score is taken as a clean play."""
    if play.accuracy is None:
        return 0, 0
    middle = (100.0 - play.accuracy) / 100.0 * notes * 4.0
    spread = 0.005 / 100.0 * notes * 4.0
    return max(0, ceil(middle - spread)), max(0, floor(middle + spread))


@dataclass(frozen=True, slots=True)
class FoundSet:
    """A released set that gives the score exactly on `surface`; gem_gap: the share of its score the best one-gem move adds."""

    gear: tuple[str, ...]
    minis: tuple[str, ...]
    gems: dict[str, int]
    element: str
    team_buff: str
    team_color: str
    stats: dict[str, int]
    surface: FgResponseSurface
    gem_gap: float


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


def _found_set(song: ReverseSong, row: np.ndarray, target: np.ndarray, play: PlayInfo, gem_gap: float) -> FoundSet:
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
    return FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, gem_gap)


def _gaps_of(song: ReverseSong, found: np.ndarray) -> np.ndarray:
    """Per found loadout, gem_gaps."""
    gaps = np.empty(found.shape[0])
    tables = song.line_shape, song.multipliers[0], song.multipliers[2], song.curves.f64["Perfect Points"]
    gem_gaps(found, (song.space.items, song.space.gems), song.fixed_rows, tables, gaps)
    return gaps


def _best_lines(found: np.ndarray, gaps: np.ndarray, limit: int) -> list[int]:
    """The found rows of the `limit` targets with the lowest gap, lowest gap first."""
    best: dict[int, float] = {}
    for target, gap in zip(found[:, 16].tolist(), gaps.tolist()):
        best[target] = min(best.get(target, 1.0), gap)
    kept = set(sorted(best, key=best.__getitem__)[:limit])
    return sorted((r for r, target in enumerate(found[:, 16].tolist()) if target in kept), key=lambda r: (best[found[r, 16]], gaps[r]))


def _perfect_sets(play: PlayInfo, song: ReverseSong, limit: int) -> tuple[list[FoundSet], int, bool]:
    """The sets of an all-Perfect play, the ones whose gems a player would leave first, until `limit` stat lines or the search
    budget ends: the sets, the stat lines, and whether every line was searched to its end."""
    surfaces = song.surfaces
    order = song.surface_order[song.surface_tops >= play.score]
    arrays = surfaces.words, surfaces.coeffs, surfaces.pattern, surfaces.body_fever, surfaces.cell_start, surfaces.cells, order
    power = -1 if play.gear_power is None else play.gear_power
    out = np.empty((_TARGET_ROWS, 8), dtype=np.int64)
    count, every_line = perfect_targets(
        int(play.score), arrays, song.multipliers, song.notes, song.ceiling, (song.power_terms, power), _LINE_PAIRS, out
    )
    points = song.curves.f64["Perfect Points"]
    if power < 0:
        targets = np.column_stack((out[:count, :7], np.full(count, -1, dtype=np.int64)))
    else:
        targets = np.empty((2 * count, 8), dtype=np.int64)
        targets = targets[: with_points_stat(out[:count], power, points, targets)]
    found = np.empty((_HELD_LINES * _SETS_PER_LINE, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    query = targets, power, _HELD_LINES, _SEARCH_ITEMS, _ITEMS_PER_TARGET, _ITEMS_PER_SETUP, _SETS_PER_LINE
    vertices = song.vertex_values, song.vertex_prices
    written, complete = search_targets(space, song.tables.arrays, song.fixed_rows, points, vertices, query, found)
    found = found[:written]
    gaps = _gaps_of(song, found)
    sets = [_found_set(song, found[r], targets[found[r, 16]], play, float(gaps[r])) for r in _best_lines(found, gaps, limit)]
    return sets, count, complete and every_line


def _great_surfaces(song: ReverseSong, greats: int) -> tuple:
    """The timelines of a play with this many Greats, the first time a lookup needs them: walked for few Greats, past
    that the band around those walked for _GREATS_WALKED. Returns the walked surfaces, whether any has head fever, and the
    band's arrays (band_surfaces)."""
    walked_for = min(greats, _GREATS_WALKED)
    band = 0 if greats <= _GREATS_WALKED else _BAND_NOTES
    if (walked_for, band) not in song.budgets:
        if ("greats", walked_for) not in song.walked:
            surfaces = fever_surfaces(song.chart, song.curves, 0, walked_for)
            song.walked["greats", walked_for] = surfaces, _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices), cell_sums(surfaces.cell_start, surfaces.cells)
        surfaces, relief, sums = song.walked["greats", walked_for]
        song.budgets[walked_for, band] = surfaces, bool(np.any(surfaces.words[:, :4])), band_surfaces((surfaces.pattern, surfaces.body_fever), relief, sums, band, song.notes[1])
    return song.budgets[walked_for, band]


def _casual_timelines(song: ReverseSong, greats: int, perfect_time: int = 0) -> list[tuple[int, np.ndarray]]:
    """Per Casual timeline of a play with this many Greats: its score with no Greats, what a Great costs at each head note."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, 0, perfect_time)
    scratch = (np.empty((_SCRATCH_ROWS, 7), dtype=np.int64), np.empty((_SCRATCH_ROWS, 7), dtype=np.int64))
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    written = walk_cell(times, great_times(chart, perfect_time), (threshold, greats), duration, scratch, out)
    if written < 0:
        raise ValueError("fever walk: the casual cell outgrew its tables")
    head = min(chart.total_notes, HEAD_NOTES)
    great = float(naked.great_base)
    ramp = naked.ramp[:head]
    normal = np.floor(naked.base * ramp).astype(np.int64) - np.floor(great * ramp).astype(np.int64)
    inside = np.floor(naked.base * ramp * naked.fever).astype(np.int64) - np.floor(great * ramp * naked.fever).astype(np.int64)
    timelines = []
    for words, (lowest, highest, bits) in zip(pattern_words(out[:written, 0], out[:written, 1]).tolist(), out[:written, 2:5].tolist()):
        in_fever = np.unpackbits(np.asarray(words[:4], dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)
        for body_fever in range(lowest, highest + 1):
            if bits < 0 or (bits >> (body_fever - lowest)) & 1:
                timelines.append((fg_surface_score(naked, FgResponseSurface(*words, body_fever, 0, 0), chart.total_notes), np.where(in_fever, inside, normal)))
    return timelines


def _head_of(song: ReverseSong, line: np.ndarray, classes: np.ndarray, words: list[int], stats: dict[str, int]) -> list[int] | None:
    """The head notes a line's class loses its head Greats on, exact to the point, or None: a class that holds only their
    sum finds notes outside fever by a walk."""
    row = classes[line[4]]
    if row[0] == 0 or row[4] >= 0:
        return [note for note in row[4:7].tolist() if note >= 0]
    chart = song.chart
    head = min(chart.total_notes, HEAD_NOTES)
    worn = factors(stats, song.curves, chart.primary, chart.secondary)
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    in_fever = np.unpackbits(np.asarray(words[:4], dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)
    ramp = worn.ramp[:head]
    gear = np.floor(worn.base * ramp).astype(np.int64) - np.floor(float(worn.great_base) * ramp).astype(np.int64)
    casual = np.floor(naked.base * naked.ramp[:head]).astype(np.int64) - np.floor(float(naked.great_base) * naked.ramp[:head]).astype(np.int64)
    gear[in_fever] = -1
    wanted = int(line[8])
    out = np.empty(int(row[0]), dtype=np.int64)
    return out.tolist() if head_witness(gear, casual, int(row[0]), (wanted, int(row[7]), int(row[8])), out) else None


def _great_set(song: ReverseSong, found: np.ndarray, line: np.ndarray, rows: np.ndarray, classes: np.ndarray, surfaces: tuple, gem_gap: float, play: PlayInfo) -> FoundSet | None:
    """A search's loadout, if a row of its line gives the score at the loadout's own Great points."""
    chart = song.chart
    gear = tuple(song.space.names[i] for i in found[:6].tolist())
    minis = tuple(song.space.names[i] for i in found[6:9].tolist())
    pp, cm, fm, ft, ff, element_gems, element_row = found[9:16].tolist()
    colors = {PRIMARY: song.space.primary, SECONDARY: song.space.secondary}
    element = colors.get(element_row, next(color for color in ELEMENTS if color not in colors.values()))
    gems = dict(zip(GEM_KINDS, (pp, cm, fm, ft, ff, element_gems)))
    fixed = song.fixed[found[17]]
    stats = named_loadout_stats(team_buff_effect(fixed.tier, fixed.team_color), gear, minis, song.gears, song.minis, gems, element)
    scored = factors(stats, song.curves, chart.primary, chart.secondary)
    for row in rows[rows[:, 5] == scored.great_base][:_ROWS_PER_SET]:
        u, c, fevered = int(row[0]), int(row[4]), int(row[7])
        words = surfaces[0][surfaces[1][u]].tolist()
        body_fever = int(surfaces[2][u])
        clean = fg_surface_score(scored, FgResponseSurface(*words[:4], 0, 0, 0, 0, body_fever, 0, 0), chart.total_notes)
        body = int(classes[c, 1])
        body_loss = fevered * (floor(scored.base * scored.combo * scored.fever) - floor(float(scored.great_base) * scored.combo * scored.fever))
        body_loss += (body - fevered) * (floor(scored.base * scored.combo) - floor(float(scored.great_base) * scored.combo))
        notes = _head_of(song, (*line[:4], c, 0, 0, 0, clean - play.score - body_loss), classes, words, stats)
        if notes is None:
            continue
        great_words = [0, 0, 0, 0]
        for note in notes:
            great_words[note >> 5] |= 1 << (note & 31)
        surface = FgResponseSurface(*words[:4], *great_words, body_fever, body, fevered)
        if fg_surface_score(scored, surface, chart.total_notes) == play.score:
            return FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, gem_gap)
    return None


def _great_sets(play: PlayInfo, song: ReverseSong, greats: int, limit: int) -> tuple[list[FoundSet], int, bool]:
    """The sets of a full combo with this many Greats, the ones whose gems a player would leave first: the sets, the stat
    lines, and whether every line was searched. It needs the Casual score and Gear Power: what tells a line's Greats apart."""
    window = _casual_window(play)
    if window is None or play.gear_power is None or greats > _GREATS_SEARCHED or play.score < _GREATS_FROM * float(song.surface_tops.max()):
        return [], 0, False
    walked, head_fever, (patterns, bodies, relief, sums, bands) = _great_surfaces(song, greats)
    classes = casual_classes(window, _casual_timelines(song, greats), greats, HEAD_LISTED if head_fever else 0)
    if classes.shape[0] == 0:
        return [], 0, True
    points = song.curves.f64["Perfect Points"]
    chart = song.chart
    rows = np.empty((_GREAT_ROWS, ROW_COLUMNS), dtype=np.int64)
    game = classes, points, chart.primary == chart.secondary, play.gear_power, _GREAT_PAIRS
    arrays = walked.words, walked.coeffs, patterns, bodies, sums
    count = great_rows(play.score, arrays, song.multipliers, song.notes, (song.vertex_values, song.vertex_prices, relief), game, rows)
    every_row = count <= _GREAT_ROWS
    rows = rows[:min(count, _GREAT_ROWS)]
    held = np.empty((_GREAT_ROWS, 8), dtype=np.int64)
    written = cell_lines(rows, play.gear_power, points, (bands, walked.cell_start, walked.cells), (song.vertex_values, song.vertex_prices), held)
    every_row = every_row and written <= _GREAT_ROWS
    lines = np.unique(held[:min(written, _GREAT_ROWS), 1:8], axis=0)
    if lines.shape[0] == 0:
        return [], 0, every_row
    vertex = np.argmin(song.vertex_values[None, :] - lines[:, :4].astype(np.float64) @ song.vertex_prices[:, 1:].T, axis=1)
    targets = np.column_stack((np.zeros(lines.shape[0], dtype=np.int64), lines[:, :5], vertex, lines[:, 6]))
    found = np.empty((_HELD_LINES * _SETS_PER_LINE, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    query = targets, play.gear_power, _HELD_LINES, _GREAT_SEARCH_ITEMS, _ITEMS_PER_TARGET, _ITEMS_PER_SETUP, _SETS_PER_LINE
    done, complete = search_targets(space, song.tables.arrays, song.fixed_rows, points, (song.vertex_values, song.vertex_prices), query, found)
    found = found[:done]
    gaps = _gaps_of(song, found)
    keys = rows[:, 1] * (1 << 32) + rows[:, 2] * (1 << 16) + rows[:, 3]
    sort = np.argsort(keys, kind="stable")
    rows, keys = rows[sort], keys[sort]
    sets: list[FoundSet] = []
    lines_held: set[int] = set()
    for r in np.argsort(gaps, kind="stable")[:_GREAT_SETS_TRIED].tolist():
        target = targets[found[r, 16]]
        key = int(target[1]) * (1 << 32) + int(target[2]) * (1 << 16) + int(target[5])
        span = rows[np.searchsorted(keys, key) : np.searchsorted(keys, key, side="right")]
        made = _great_set(song, found[r], target[1:6], span, classes, (walked.words, patterns, bodies), float(gaps[r]), play)
        if made is not None:
            sets.append(made)
            lines_held.add(int(found[r, 16]))
            if len(lines_held) >= limit:
                break
    return sets, lines.shape[0], every_row and complete


def _widest(song: ReverseSong) -> dict:
    """What the widest Perfect window needs, built when a lookup first does: its surfaces, their relief, the ceiling of a
    build with each count of Perfect Time gems, and the Casual scores found per window."""
    if not song.widest:
        surfaces = fever_surfaces(song.chart, song.curves, _WIDEST_PERFECT_TIME)
        arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
        relief = _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
        losses = time_gem_losses(song.space, song.vertex_prices)
        tops = [
            score_ceiling(arrays, song.multipliers[::2], song.notes, (song.vertex_values - gems * losses, song.vertex_prices, relief), 0.0, np.inf)[0]
            for gems in _TIME_GEM_COUNTS
        ]
        song.widest.update(arrays=arrays, relief=relief, tops=tops, casual={})
    return song.widest


def _honest_time(play: PlayInfo, song: ReverseSong) -> int:
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
    scratch = (np.empty((_SCRATCH_ROWS, 7), dtype=np.int64), np.empty((_SCRATCH_ROWS, 7), dtype=np.int64))
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    written = walk_cell(times, great_times(chart, perfect_time), (threshold, 0), duration, scratch, out)
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


def _casual_highest(song: ReverseSong, quarters: int) -> float:
    """The most a play at this accuracy can score in Casual, at the widest Perfect window: Greats cost the least accuracy
    per note of fever they move, and they move it past what the ceiling of clean plays holds."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, quarters, _WIDEST_PERFECT_TIME)
    most = fever_span(times, (ceil(threshold), ceil(threshold + quarters / 2.0)), duration)[1]
    normal, full = naked.base * naked.combo, naked.base * naked.combo * naked.fever
    return chart.total_notes * normal + most * (full - normal)


def _casual_window(play: PlayInfo) -> tuple[float, float] | None:
    """The Casual score a play shows: exactly, or within the rounding of its Gear Multiplier."""
    if play.casual_score is not None:
        return float(play.casual_score), float(play.casual_score)
    if play.gear_multiplier is None:
        return None
    return play.score / (play.gear_multiplier + _MULTIPLIER_ROUNDING), play.score / (play.gear_multiplier - _MULTIPLIER_ROUNDING)


def _casual_evidence(play: PlayInfo, song: ReverseSong, lost: tuple[int, int]) -> str | None:
    """Why the Casual score cannot come from an honest Compete play, if it cannot. The server fills the bar from each
    event's time offset and scores the result the event states (push_note_sequence), so a Perfect stated on a Great's
    offset keeps a Perfect's points and a Great's fill; that moves the casual fever too, and base stats hide nothing.
    Casual matches are out: their client zeroes Perfect Time and their server does not. Below 100% only a score over what
    the accuracy leaves is proof: Okays and Misses take a Casual score down in ways this span does not hold."""
    window = _casual_window(play)
    if window is None or play.accuracy is None or play.match_mode != "Compete":
        return None
    low, high = window
    if lost[1] == 0:
        values = _clean_casual_values(song, _honest_time(play, song))
        if any(low <= value <= high for value in values):
            return None
        return f"Casual score {low:.0f}..{high:.0f} is none of the {len(values)} a clean play reaches: {sorted(values)[:6]}"
    highest = _casual_highest(song, lost[1])
    if low <= highest:
        return None
    return f"Casual score {low:.0f}..{high:.0f} is over {highest:.0f}, the most a play at this accuracy reaches"


def _no_clean_line(play: PlayInfo, song: ReverseSong) -> str | None:
    """Why no honest clean play gives this score, if none does: no stats under the ceiling reach it on any timeline of the
    widest Perfect window a build at this score wears, at its Gear Power. This holds for any level of gear: it asks for
    stat lines, not sets."""
    perfect_time = _honest_time(play, song)
    if ("window", perfect_time) not in song.walked:
        surfaces = fever_surfaces(song.chart, song.curves, perfect_time)
        song.walked["window", perfect_time] = surfaces, _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
    surfaces, relief = song.walked["window", perfect_time]
    order = np.arange(surfaces.body_fever.shape[0])
    arrays = surfaces.words, surfaces.coeffs, surfaces.pattern, surfaces.body_fever, surfaces.cell_start, surfaces.cells, order
    out = np.empty((1, 8), dtype=np.int64)
    ceiling = song.vertex_values, song.vertex_prices, relief
    count, every_line = perfect_targets(int(play.score), arrays, song.multipliers, song.notes, ceiling, (song.power_terms, play.gear_power), _LINE_PAIRS, out)
    if count or not every_line:
        return None
    return f"no stats at Gear Power {play.gear_power} give {play.score} on any clean timeline up to Perfect Time {perfect_time}"


def _no_great_place(play: PlayInfo, song: ReverseSong, greats: int) -> str | None:
    """Why no honest play with this many Greats gives this Casual score, if none does; only Greats cost so few quarters."""
    window = _casual_window(play)
    if window is None or play.match_mode != "Compete":
        return None
    timelines = _casual_timelines(song, greats, _honest_time(play, song))
    if casual_classes(window, timelines, greats, 0).shape[0]:
        return None
    return f"Casual score {window[0]:.0f}..{window[1]:.0f} is no placement of {greats} Greats on any honest timeline"


def _honest_ceiling(play: PlayInfo, song: ReverseSong, lost: tuple[int, int]) -> tuple[float, float]:
    """The most an honest play scores with any released loadout at any Perfect window, never under a real score, or the
    first line past the play's score; and the base value there."""
    widest = _widest(song)
    spare = float(_FEVER_NOTES_PER_NOTE * lost[1])
    ceiling = (song.vertex_values, song.vertex_prices, widest["relief"])
    best, line = score_ceiling(widest["arrays"], song.multipliers[::2], song.notes, ceiling, spare, float(play.score))
    return best, line[3]


def _unreleased_item(play: PlayInfo, song: ReverseSong, ceiling: float, base: float) -> UnreleasedItem:
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


def reverse_score(play: PlayInfo, song: ReverseSong, *, limit: int = 8) -> Reverse:
    """The sets behind a play, ranked; or what it would take; or the verdict that no honest play gives it."""
    lost = lost_quarters(play, song.chart.total_notes)
    found, count, finished = [], 0, True
    if lost[0] == 0:
        found, count, finished = _perfect_sets(play, song, limit)
    for greats in range(max(lost[0], 1), lost[1] + 1):
        more, lines, done = _great_sets(play, song, greats, limit)
        found, count, finished = found + more, count + lines, finished and done
    found.sort(key=lambda row: row.gem_gap)
    evidence = _casual_evidence(play, song, lost)
    if evidence is None and not found and lost[1] == 0 and count == 0 and finished and play.gear_power is not None and play.accuracy is not None and play.match_mode == "Compete":
        evidence = _no_clean_line(play, song)
    if evidence is None and 0 < lost[0] == lost[1] <= _ONLY_GREATS:
        evidence = _no_great_place(play, song, lost[0])
    if evidence is not None:
        return Reverse("exploited", tuple(found), count, finished, evidence=(evidence,))
    if found:
        return Reverse("sets", tuple(found), count, finished)
    ceiling, base = _honest_ceiling(play, song, lost)
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling, base)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)
