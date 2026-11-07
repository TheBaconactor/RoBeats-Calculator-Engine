"""Score reverse-lookup: what the Top Scores menu shows of a play, to the sets that give it.

The input is a row and its View popup, what a user reads off the game, and nothing stored: the answer is worked out from the
chart, the released catalog and the stat curves, the same score math run backwards. The score equation leaves a few stat lines
near a song's top and thousands far below it, every one of them found on the GPU (gpu_lines). A ceiling over the released items
keeps those a loadout can reach, value tables and a walk over the items find the loadouts, the lines a player's gems would
leave first, and gear_optimizer.score confirms every one. A play with Greats has its Casual score say where they lie (greats.py).
Sets rank by how little one gem move would add, since players place their gems; nothing public tells two sets of one stat line
apart, and far below the top nothing tells the lines apart.

Cost in the song's real sizes: prepare O(C E log n) for the walk of C = 25,921 cells, O(P J) for the ceiling over P
(surface, cell) pairs (~60,000) and J vertices, ~0.1 s once per song. A lookup: see gpu_lines for
the lines, O(L) over L lines to rank them, then the walks, a fixed budget. The first lookup at a Great count walks the cells,
0.1 to 4 s.
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
from gear_optimizer.score import HEAD_NOTES, Factors, factors, fg_surface_score
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, named_loadout_stats

from .fever_reach import FeverSurfaces, event_times, fever_span, fever_surfaces, great_times, pattern_words, walk_cell
from .gpu_lines import MAX_CLASSES, MAX_ROWS, LineQuery, SongTables, line_rows, surface_tables
from .greats import (
    HEAD_LISTED,
    ROW_COLUMNS,
    band_surfaces,
    casual_classes,
    cell_lines,
    cell_sums,
    explanation_costs,
    great_points_fit,
    head_witness,
)
from .invert import score_ceiling
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
    line_gaps,
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
# The base values of (surface, CM, FM) pairs a search may walk: ~35 ns each. Past them a score has more lines than a row can tell
# apart.
_LINE_BASES = 5_000_000
_TOP_LINE_BASES = 30_000_000
_SHARED_BASES = 100_000_000
_SETS_PER_LINE = 16
_SCRATCH_ROWS = 1 << 15
_PREFERRED_TIER = "T5"
# The most Greats a lookup searches, the most whose timelines it walks, and past those how far from a walked timeline it looks:
# a dev run's most, 4 notes up to 64 Greats, doubled.
_GREATS_SEARCHED = 64
_GREATS_WALKED = 8
_BAND_NOTES = 8
# The most quarters only Greats can cost: an Okay costs three.
_ONLY_GREATS = 2
# The loadouts rescored exactly, most plausible first, and the rows of a line each one tries.
_SETS_TRIED = 512
_ROWS_PER_SET = 32
# How far from a cell's chart-time body fever a first search looks, in notes: 41 of 43 dev plays of up to 8 Greats lie within
# one. With fewer lines than this it looks at every timeline: a Force Great plan moves its fever on purpose.
_NEAR_NOTES = 2
_WIDE_UNDER = 4096
# What a gem gap costs a line, in nats per share of the score. A plan that moves its fever on purpose (a Force Great plan) fits any
# timeline and needs no chance in its Greats: it costs this, on a build whose gem gap costs more; at this share of a song's top a
# search always looks at every timeline, since such plans live there.
_GAP_COST = 200.0
_PLAN_COST = 1.0
_PLAN_GAP_COST = 1000.0
_PLAN_HEIGHT = 0.95
_UNNAMED_AT_TOP = 50.0  # up there a line no released max-level set reaches comes last: gear below max does not get there
# Lines of a search that may hold loadouts; items a search may try, a target may try, and what opening a target counts for: 5 ns
# an item.
_LINES_HELD = 1024
_SEARCH_ITEMS = 8_000_000
_PLAN_SEARCH_ITEMS = 80_000_000  # at a song's top few lines have a loadout, and the one a plan wears can lie anywhere among them
_ITEMS_PER_TARGET = 500_000
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
# The game saves accuracy to 5 decimals and prints that to 2 (PlayerSongPlay.lua:251, SongDisplayElement.lua:656).
_ACCURACY_ROUNDING = 0.0055


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
    top: float = 0.0  # the most any line under the ceiling scores
    line_shape: np.ndarray = field(default_factory=lambda: np.empty((0, 4)))  # per cell, its chart-time timeline's shape
    chart_fever: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))  # and its body fever
    chart_head: np.ndarray = field(default_factory=lambda: np.empty((0, 4), dtype=np.uint32))  # and its head mask
    widest: dict = field(default_factory=dict)  # _widest
    timelines: dict = field(default_factory=dict)  # _timelines_of
    gpu: SongTables | None = None

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


@dataclass(frozen=True, slots=True, eq=False)
class Timelines:
    """The surfaces a search walks: per surface its head pattern, body fever, relief, FT + FF bits and the first and last + 1
    walked surface in its band. walked.cells are sorted by FT + FF within a surface."""

    walked: FeverSurfaces
    head_fever: bool
    pattern: np.ndarray
    body_fever: np.ndarray
    relief: np.ndarray
    sums: np.ndarray
    bands: np.ndarray


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


def _chart_timelines(chart: Chart, curves: StatCurves) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per (Fever Time, Fever Fill) cell its chart-time timeline: the bound shape a set plain-scores by, body fever, head mask."""
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
    shapes = np.column_stack((body_fever + ramp_fever, body_normal + ramp_normal, coeffs[:, 1] - ramp_fever, coeffs[:, 0] - ramp_normal))
    return shapes, fever.reshape(-1).astype(np.int64), words.reshape(-1, 4)


def _ranked(song: ReverseSong) -> ReverseSong:
    """The song with its top, and what its searches read."""
    surfaces = song.surfaces
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    top = score_ceiling(arrays, song.multipliers[::2], song.notes, song.ceiling, 0.0, np.inf)[0]
    combo, ramp, fever = song.multipliers
    head, body = song.notes
    gpu = SongTables(combo, ramp, fever, song.curves.f64["Perfect Points"], song.vertex_values, song.vertex_prices[:, 1:3], head, body, song.chart.primary == song.chart.secondary)
    shapes, chart_fever, chart_head = _chart_timelines(song.chart, song.curves)
    return replace(song, top=top, line_shape=shapes, chart_fever=chart_fever, chart_head=chart_head, gpu=gpu)


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
    spread = _ACCURACY_ROUNDING / 100.0 * notes * 4.0
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
    cost: float = 0.0  # how far-fetched its line is, lower first


@dataclass(frozen=True, slots=True)
class StatLine:
    """Final stats that give the score; cost: how far-fetched the likeliest play behind them is, lower first; named: a released
    max-level set reaches them."""

    combo_multiplier: int
    fever_multiplier: int
    fever_time: int
    fever_fill_rate: int
    perfect_points: int  # negative when the row shows no Gear Power
    base: int
    cost: float
    named: bool


@dataclass(frozen=True, slots=True)
class UnreleasedItem:
    """What a set would need beyond the released items: the slot, the item it would beat, the extra primary points."""

    slot: str
    beats: str
    extra_primary: int
    plausible: bool


@dataclass(frozen=True, slots=True)
class Reverse:
    verdict: str  # sets, lines (stats fit, no released max-level set), unresolved, unreleased or exploited
    sets: tuple[FoundSet, ...]
    lines: int  # the exact stat lines under the ceiling that the lookup kept
    finished: bool  # every line was kept and searched to its end
    ceiling: float | None = None  # past the score: the first line found that reaches it
    unreleased: UnreleasedItem | None = None
    evidence: tuple[str, ...] = ()
    stat_lines: tuple[StatLine, ...] = ()  # the likeliest lines, likeliest first


def _gaps_of(song: ReverseSong, found: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per found loadout, gem_gaps: its gap and Great points."""
    gaps = np.empty(found.shape[0])
    greats = np.empty(found.shape[0], dtype=np.int64)
    tables = song.line_shape, song.multipliers[0], song.multipliers[2], song.curves.f64["Perfect Points"], song.chart.primary == song.chart.secondary
    gem_gaps(found, (song.space.items, song.space.gems), song.fixed_rows, tables, gaps, greats)
    return gaps, greats


def _sorted_cells(surfaces: FeverSurfaces) -> FeverSurfaces:
    """The surfaces with each one's cells by FT + FF."""
    owner = np.repeat(np.arange(surfaces.cell_start.shape[0] - 1), np.diff(surfaces.cell_start))
    order = np.lexsort((surfaces.cells // _AXIS + surfaces.cells % _AXIS, owner))
    return replace(surfaces, cells=surfaces.cells[order])


def _near_chart_time(song: ReverseSong, surfaces: FeverSurfaces, same_head: bool) -> FeverSurfaces:
    """The surfaces with only the cells whose chart-time timeline they lie within _NEAR_NOTES of; same_head: and share its head."""
    owner = np.repeat(np.arange(surfaces.cell_start.shape[0] - 1), np.diff(surfaces.cell_start))
    near = np.abs(surfaces.body_fever[owner] - song.chart_fever[surfaces.cells]) <= _NEAR_NOTES
    if same_head:
        near &= (surfaces.words[surfaces.pattern[owner], :4] == song.chart_head[surfaces.cells]).all(axis=1)
    alive = np.bincount(owner[near], minlength=surfaces.body_fever.shape[0])
    kept = alive > 0
    return replace(surfaces, pattern=surfaces.pattern[kept], body_fever=surfaces.body_fever[kept], cell_start=np.concatenate(([0], np.cumsum(alive[kept]))), cells=surfaces.cells[near])


def _with_cells(song: ReverseSong, surfaces: FeverSurfaces, band: int) -> Timelines:
    relief = _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
    sums = cell_sums(surfaces.cell_start, surfaces.cells)
    pattern, body, wide_relief, wide_sums, bands = band_surfaces((surfaces.pattern, surfaces.body_fever), relief, sums, band, song.notes[1])
    return Timelines(_sorted_cells(surfaces), bool(np.any(surfaces.words[:, :4])), pattern, body, wide_relief, wide_sums, bands)


def _timelines_of(song: ReverseSong, greats: int, near: bool) -> Timelines:
    """The timelines of a play with this many Greats, the first time a lookup needs them: walked for few Greats, past that the
    band around those walked for _GREATS_WALKED; near: only those near a cell's chart-time timeline."""
    walked_for = min(greats, _GREATS_WALKED)
    band = 0 if near or greats <= _GREATS_WALKED else _BAND_NOTES
    if (walked_for, band, near) not in song.timelines:
        if ("walked", walked_for) not in song.timelines:
            song.timelines["walked", walked_for] = song.surfaces if walked_for == 0 else fever_surfaces(song.chart, song.curves, 0, walked_for)
        surfaces = song.timelines["walked", walked_for]
        song.timelines[walked_for, band, near] = _with_cells(song, _near_chart_time(song, surfaces, greats <= _GREATS_WALKED) if near else surfaces, band)
    return song.timelines[walked_for, band, near]


def _window_timelines(song: ReverseSong, perfect_time: int) -> Timelines:
    """The clean timelines of a Perfect window."""
    if ("window", perfect_time) not in song.timelines:
        song.timelines["window", perfect_time] = _with_cells(song, fever_surfaces(song.chart, song.curves, perfect_time), 0)
    return song.timelines["window", perfect_time]


def _casual_timelines(song: ReverseSong, greats: int, perfect_time: int = 0) -> list[tuple[int, np.ndarray]] | None:
    """Per Casual timeline of a play with this many Greats: its score with no Greats, what a Great costs at each head note.
    Past _GREATS_WALKED the band around the timelines walked for those, as in _timelines_of. None when the walk's tables
    cannot hold them."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    times, threshold, duration = _casual_axes(song, 0, perfect_time)
    scratch = (np.empty((_SCRATCH_ROWS, 7), dtype=np.int64), np.empty((_SCRATCH_ROWS, 7), dtype=np.int64))
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    written = walk_cell(times, great_times(chart, perfect_time), (threshold, min(greats, _GREATS_WALKED)), duration, scratch, out)
    if written < 0:
        return None
    band = _BAND_NOTES if greats > _GREATS_WALKED else 0
    head = min(chart.total_notes, HEAD_NOTES)
    great = float(naked.great_base)
    ramp = naked.ramp[:head]
    normal = np.floor(naked.base * ramp).astype(np.int64) - np.floor(great * ramp).astype(np.int64)
    inside = np.floor(naked.base * ramp * naked.fever).astype(np.int64) - np.floor(great * ramp * naked.fever).astype(np.int64)
    timelines = []
    for words, (lowest, highest, bits) in zip(pattern_words(out[:written, 0], out[:written, 1]).tolist(), out[:written, 2:5].tolist()):
        in_fever = np.unpackbits(np.asarray(words[:4], dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)
        for body_fever in range(max(lowest - band, 0), min(highest + band, song.notes[1]) + 1):
            if band or bits < 0 or (bits >> (body_fever - lowest)) & 1:
                timelines.append((fg_surface_score(naked, FgResponseSurface(*words, body_fever, 0, 0), chart.total_notes), np.where(in_fever, inside, normal)))
    return timelines


def _head_of(song: ReverseSong, line: tuple[int, int, int, int], worn: Factors, words: list[int]) -> list[int] | None:
    """The head notes a class loses its head Greats on, exact to the point, or None: a class that holds only their sum finds
    notes outside fever by a walk. line: (class's head Greats, its lowest and highest Casual loss, the score they lose)."""
    held, casual_low, casual_high, wanted = line
    chart = song.chart
    head = min(chart.total_notes, HEAD_NOTES)
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    in_fever = np.unpackbits(np.asarray(words[:4], dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)
    ramp = worn.ramp[:head]
    gear = np.floor(worn.base * ramp).astype(np.int64) - np.floor(float(worn.great_base) * ramp).astype(np.int64)
    casual = np.floor(naked.base * naked.ramp[:head]).astype(np.int64) - np.floor(float(naked.great_base) * naked.ramp[:head]).astype(np.int64)
    gear[in_fever] = -1
    out = np.empty(held, dtype=np.int64)
    return out.tolist() if head_witness(gear, casual, held, (wanted, casual_low, casual_high), out) else None


def _played_surface(song: ReverseSong, scored: Factors, row: np.ndarray, classes: np.ndarray, timelines: Timelines, score: int) -> FgResponseSurface | None:
    """The surface of a row at a loadout's own stats, if its class gives the score: a play's timeline and Greats."""
    u, c, fevered = int(row[0]), int(row[4]), int(row[7])
    words = timelines.walked.words[timelines.pattern[u]].tolist()
    body_fever = int(timelines.body_fever[u])
    if classes.shape[0] == 0:
        return FgResponseSurface(*words[:4], 0, 0, 0, 0, body_fever, 0, 0)
    total = song.chart.total_notes
    clean = fg_surface_score(scored, FgResponseSurface(*words[:4], 0, 0, 0, 0, body_fever, 0, 0), total)
    spec = classes[c].tolist()
    held, body = spec[0], spec[1]
    body_loss = fevered * (floor(scored.base * scored.combo * scored.fever) - floor(float(scored.great_base) * scored.combo * scored.fever))
    body_loss += (body - fevered) * (floor(scored.base * scored.combo) - floor(float(scored.great_base) * scored.combo))
    notes = [note for note in spec[4:7] if note >= 0]
    if held and spec[4] < 0:
        notes = _head_of(song, (held, spec[7], spec[8], clean - score - body_loss), scored, words)
    if notes is None:
        return None
    great_words = [0, 0, 0, 0]
    for note in notes:
        great_words[note >> 5] |= 1 << (note & 31)
    return FgResponseSurface(*words[:4], *great_words, body_fever, body, fevered)


def _named_set(song: ReverseSong, found: np.ndarray, rows: np.ndarray, classes: np.ndarray, timelines: Timelines, gem_gap: float, score: int) -> FoundSet | None:
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
    fitting = rows if classes.shape[0] == 0 else rows[rows[:, 5] == scored.great_base]
    for row in fitting[:_ROWS_PER_SET]:
        surface = _played_surface(song, scored, row, classes, timelines, score)
        if surface is not None and fg_surface_score(scored, surface, chart.total_notes) == score:
            return FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, gem_gap)
    return None


@dataclass(frozen=True, slots=True, eq=False)
class FoundLines:
    """Every stat line of a score: targets (search_targets rows), most plausible first, with what their plays cost alone and with
    the line's gem gap; held[spans[t, 0] : spans[t, 1]] the rows of line t."""

    targets: np.ndarray
    plays: np.ndarray
    costs: np.ndarray
    rows: np.ndarray
    held: np.ndarray
    spans: np.ndarray
    complete: bool


def _line_costs(plays: np.ndarray, gaps: np.ndarray) -> np.ndarray:
    """How far-fetched lines are at these gem gaps, the likelier of an honest play and a plan."""
    return np.minimum(plays + _GAP_COST * gaps, _PLAN_COST + _PLAN_GAP_COST * gaps)


def _stat_lines(song: ReverseSong, timelines: Timelines, query: LineQuery) -> FoundLines:
    """The lines of a query, the plausible first: a play near chart time, gems a player would leave alone. Surfaces go to the GPU
    in a shuffle, so a score that leaves more than a search may walk keeps a sample of them all."""
    walked = timelines.walked
    order = np.random.default_rng(0).permutation(timelines.pattern.shape[0])
    tables = surface_tables(order, (walked.words, walked.coeffs), (timelines.pattern, timelines.body_fever), timelines.sums, timelines.relief, song.notes[1])
    packed, complete = line_rows(song.gpu, tables, query)
    rows = np.empty((packed.shape[0], ROW_COLUMNS), dtype=np.int64)
    rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3] = packed[:, 0], packed[:, 1] >> 8, packed[:, 1] & 255, packed[:, 2]
    rows[:, 4], rows[:, 5], rows[:, 6], rows[:, 7] = packed[:, 3] >> 16, packed[:, 4], packed[:, 5], packed[:, 3] & 65535
    points = song.curves.f64["Perfect Points"]
    held = np.empty((MAX_ROWS, 8), dtype=np.int64)
    written = cell_lines(rows, query.power, points, (timelines.bands, walked.cell_start, walked.cells), (song.vertex_values, song.vertex_prices), held)
    complete = complete and written <= MAX_ROWS
    held = held[: min(written, MAX_ROWS)]
    keys = held[:, 1] * _AXIS**4 + held[:, 2] * _AXIS**3 + held[:, 3] * _AXIS**2 + held[:, 4] * _AXIS + held[:, 7] + 1
    keys = keys * (1 << 16) + held[:, 5]
    ordered = np.argsort(keys, kind="stable")
    held, keys = held[ordered], keys[ordered]
    first = np.flatnonzero(np.concatenate(([True], keys[1:] != keys[:-1])))[: None if keys.shape[0] else 0]
    targets = np.column_stack((rows[held[first, 0], 0], held[first, 1:8]))
    spans = np.column_stack((first, np.concatenate((first[1:], [keys.shape[0]]))[: first.shape[0]]))
    gaps = np.empty(targets.shape[0])
    line_gaps(targets, song.space.gems, (song.line_shape, song.multipliers[0], song.multipliers[2], points), gaps)
    plays = np.empty(targets.shape[0])
    log_factorial = np.concatenate(([0.0], np.cumsum(np.log(np.arange(1, _GREATS_SEARCHED + 2)))))
    explanation_costs(held, rows, query.classes, (song.chart_fever, timelines.body_fever, *song.notes[::-1], log_factorial), spans, plays)
    costs = _line_costs(plays, gaps)
    shuffled = np.random.default_rng(0).permutation(costs.shape[0])
    plausible = shuffled[np.argsort(costs[shuffled], kind="stable")]
    return FoundLines(targets[plausible], plays[plausible], costs[plausible], rows, held, spans[plausible], complete)


def _named_costs(lines: FoundLines, found: np.ndarray, gaps: np.ndarray, reached: int, unnamed: float) -> np.ndarray:
    """What lines cost once the search has walked `reached` of them: a loadout's own gem gap, less what it tells that a released
    set reaches a line, the rarer among the lines walked the more. A line no set reaches costs `unnamed` more."""
    best = np.full(lines.targets.shape[0], np.inf)
    np.minimum.at(best, found[:, 16], gaps)
    named = np.isfinite(best)
    costs = lines.costs + unnamed
    costs[named] = _line_costs(lines.plays[named], best[named]) - np.log((reached + 1.0) / (np.count_nonzero(named) + 1.0))
    return costs


def _classes_of(play: PlayInfo, song: ReverseSong, greats: int, timelines: Timelines) -> np.ndarray | None:
    """Where a play's Greats can lie, empty for a clean play; None when the row cannot tell: Greats need the Casual score and Gear
    Power, what tells a line's Greats apart, and past MAX_CLASSES places those tell nothing."""
    if greats == 0:
        return np.empty((0, 9), dtype=np.int64)
    window = _casual_window(play)
    casual = None if window is None or play.gear_power is None else _casual_timelines(song, greats)
    if casual is None:
        return None
    classes = casual_classes(window, casual, greats, HEAD_LISTED if timelines.head_fever else 0)
    return None if classes.shape[0] > MAX_CLASSES else classes


def _sets_of(play: PlayInfo, song: ReverseSong, greats: int, limit: int) -> tuple[list[FoundSet], list[StatLine], int, bool]:
    """The likeliest lines of a full combo with this many Greats and the sets that reach them: sets, lines, how many lines there
    are, and whether every line was searched."""
    timelines = _timelines_of(song, greats, greats > 0)
    classes = _classes_of(play, song, greats, timelines)
    if classes is None:
        return [], [], 0, False
    if greats and classes.shape[0] == 0:
        return [], [], 0, True
    power = -1 if play.gear_power is None else play.gear_power
    at_top = play.score >= _PLAN_HEIGHT * song.top
    query = LineQuery(play.score, power, greats, classes, _TOP_LINE_BASES if at_top else _LINE_BASES)
    lines = _stat_lines(song, timelines, query)
    every_timeline = greats == 0 or lines.targets.shape[0] < _WIDE_UNDER or at_top
    if greats and every_timeline:
        timelines = _timelines_of(song, greats, False)
        lines = _stat_lines(song, timelines, query)
    if lines.targets.shape[0] == 0:
        return [], [], 0, lines.complete
    found = np.empty((_LINES_HELD * _SETS_PER_LINE, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    search = lines.targets, power, _LINES_HELD, _PLAN_SEARCH_ITEMS if at_top else _SEARCH_ITEMS, _ITEMS_PER_TARGET, _ITEMS_PER_SETUP, _SETS_PER_LINE
    done, reached, complete = search_targets(space, song.tables.arrays, song.fixed_rows, song.curves.f64["Perfect Points"], (song.vertex_values, song.vertex_prices), search, found)
    found = found[:done]
    gaps, great_points = _gaps_of(song, found)
    if greats:
        fits = np.empty(found.shape[0], dtype=bool)
        great_points_fit(found, great_points, lines.held, lines.rows, lines.spans, fits)
        found, gaps = found[fits], gaps[fits]
    final = _named_costs(lines, found, gaps, reached, _UNNAMED_AT_TOP if at_top else 0.0)
    named: dict[int, list[FoundSet]] = {}
    tries = np.lexsort((gaps, found[:, 16]))
    first = np.searchsorted(found[tries, 16], np.arange(lines.targets.shape[0]))
    last = np.searchsorted(found[tries, 16], np.arange(lines.targets.shape[0]), side="right")
    listed: list[int] = []
    for t in np.argsort(final, kind="stable")[:_SETS_TRIED].tolist():
        span = lines.held[lines.spans[t, 0] : lines.spans[t, 1], 0]
        made = (_named_set(song, found[r], lines.rows[span], classes, timelines, float(gaps[r]), play.score) for r in tries[first[t] : last[t]].tolist())
        sets = [replace(row, cost=float(final[t])) for row in made if row is not None]
        if sets:
            named[t] = sets
        if sets or last[t] == first[t]:
            listed.append(t)
        if len(listed) >= limit:
            break
    stat_lines = [
        StatLine(*lines.targets[t, 1:5].tolist(), int(lines.targets[t, 7]), int(lines.targets[t, 5]), float(final[t]), t in named)
        for t in listed
    ]
    return [row for t in listed for row in named.get(t, ())], stat_lines, lines.targets.shape[0], lines.complete and complete and every_timeline


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
    timelines = _window_timelines(song, perfect_time)
    query = LineQuery(int(play.score), play.gear_power, 0, np.empty((0, 9), dtype=np.int64), _LINE_BASES)
    lines = _stat_lines(song, timelines, query)
    if lines.targets.shape[0] or not lines.complete:
        return None
    return f"no stats at Gear Power {play.gear_power} give {play.score} on any clean timeline up to Perfect Time {perfect_time}"


def _no_great_place(play: PlayInfo, song: ReverseSong, greats: int) -> str | None:
    """Why no honest play with this many Greats gives this Casual score, if none does; only Greats cost so few quarters."""
    window = _casual_window(play)
    if window is None or play.match_mode != "Compete":
        return None
    timelines = _casual_timelines(song, greats, _honest_time(play, song))
    if timelines is None or casual_classes(window, timelines, greats, 0).shape[0]:
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


def _row_keys(play: PlayInfo, song: ReverseSong) -> tuple[np.ndarray, bool]:
    """Every (CM, FM, FT, FF, Perfect Points) that gives a row at its Gear Power, under the ceiling, as one number each, and whether
    they are all."""
    lost = lost_quarters(play, song.chart.total_notes)
    keys = []
    every_line = lost[1] <= _GREATS_SEARCHED
    for greats in range(lost[0], min(lost[1], _GREATS_SEARCHED) + 1):
        timelines = _timelines_of(song, greats, False)
        classes = _classes_of(play, song, greats, timelines)
        if classes is None:
            every_line = False
        elif greats == 0 or classes.shape[0]:
            lines = _stat_lines(song, timelines, LineQuery(int(play.score), play.gear_power, greats, classes, _SHARED_BASES))
            every_line = every_line and lines.complete
            found = lines.targets
            keys.append(found[:, 1] * _AXIS**4 + found[:, 2] * _AXIS**3 + found[:, 3] * _AXIS**2 + found[:, 4] * _AXIS + found[:, 7])
    return (np.unique(np.concatenate(keys)) if keys else np.empty(0, dtype=np.int64)), every_line


def shared_lines(rows: list[tuple[PlayInfo, ReverseSong]]) -> np.ndarray:
    """The stats one player's rows on several songs can share: (CM, FM, FT, FF, Perfect Points) rows. One row leaves thousands far
    below a song's top, and each more leaves a sliver of them, so this names arbitrary gear where a row cannot, if the player wore
    one set for all of them. Every row needs its Gear Power. A row whose lines are not all known cannot rule any out: it counts
    for nothing."""
    shared = None
    for play, song in rows:
        keys, every_line = _row_keys(play, song)
        if every_line:
            shared = keys if shared is None else np.intersect1d(shared, keys)
    shared = np.empty(0, dtype=np.int64) if shared is None else shared
    return np.column_stack(((shared // _AXIS**4), (shared // _AXIS**3) % _AXIS, (shared // _AXIS**2) % _AXIS, (shared // _AXIS) % _AXIS, shared % _AXIS))


def reverse_score(play: PlayInfo, song: ReverseSong, *, limit: int = 8) -> Reverse:
    """The sets behind a play, ranked; or what it would take; or the verdict that no honest play gives it."""
    lost = lost_quarters(play, song.chart.total_notes)
    found, listed, count, finished = [], [], 0, True
    for greats in range(lost[0], min(lost[1], _GREATS_SEARCHED) + 1):
        more, stat_lines, lines, done = _sets_of(play, song, greats, limit)
        found, listed, count, finished = found + more, listed + stat_lines, count + lines, finished and done
    found.sort(key=lambda row: row.cost)
    listed = sorted(listed, key=lambda line: line.cost)[:limit]
    evidence = _casual_evidence(play, song, lost)
    if evidence is None and not found and lost[1] == 0 and count == 0 and finished and play.gear_power is not None and play.accuracy is not None and play.match_mode == "Compete":
        evidence = _no_clean_line(play, song)
    if evidence is None and 0 < lost[0] == lost[1] <= _ONLY_GREATS:
        evidence = _no_great_place(play, song, lost[0])
    if evidence is not None:
        return Reverse("exploited", tuple(found), count, finished, evidence=(evidence,), stat_lines=tuple(listed))
    if found:
        return Reverse("sets", tuple(found), count, finished, stat_lines=tuple(listed))
    if listed:
        return Reverse("lines", (), count, finished, stat_lines=tuple(listed))
    ceiling, base = _honest_ceiling(play, song, lost)
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling, base)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)
