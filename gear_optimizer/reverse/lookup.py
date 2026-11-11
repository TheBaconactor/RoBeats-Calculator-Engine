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
from functools import cached_property
from math import ceil, comb, floor

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_ORDER, team_buff_effect
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import ELEMENTS, Mini, SongMini, StatCurves, empty_stats, perfect_time_of, song_minis, worn_mini_stats
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT
from gear_optimizer.score import HEAD_NOTES, Factors, factors, fg_surface_score
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, apply_gems, named_loadout_stats, total

from .fever_reach import FeverSurfaces, event_times, fever_span, fever_surfaces, great_times, pattern_words, walk_cell, walk_scratch
from .gpu_lines import MAX_CLASSES, MAX_ROWS, LineQuery, SongTables, SurfaceTables, line_rows, scan_order, surface_tables
from .greats import (
    CLASS_COLUMNS,
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
from . import partial_sets
from .partial_sets import PartialSpace, guess_set, partial_space
from .replay import play_offsets
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
    likeliest_loadouts,
    line_gaps,
    loadout_space,
    lowest_at,
    points_conjugate,
    prices_at_gems,
    relaxed_best,
    search_targets,
    shortfalls,
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
# A listed line's sets come likeliest first: of the _SETS_WEIGHED whose items give up least at the line's prices, found band by
# band of shortfall from _FIRST_BAND of the base, by gem gap + _SHORTFALL_COST x that shortfall over the base. A player wears
# their best items, and a lower TeamBuff needs better ones for the same line, so this needs no guess at the tier. Dev split:
# a true line holds a median of 520 max-level sets, and the true gear is among its first 16 on 42 of 119 top players' rows in
# walk order, 49 by gem gap, 65 by shortfall, 72 by both at 0.5 (0.5, 1, 2 and 4 tried); the benchmark names 60 sets at 64
# weighed against 39 in walk order, 2 more at 256 for 3% more CPU.
_SETS_WEIGHED = 64
_FIRST_BAND = 0.005
_SHORTFALL_COST = 0.5
_SCRATCH_ROWS = 1 << 15
_PREFERRED_TIER = "T5"
# The most Greats a lookup searches: a row that lost more quarters of accuracy has too many lines to tell its own (of 220 such
# dev rows up to 64 quarters none had its true line listed, 79 showed sets and 39 lines, for a third of all lookup time). The
# most whose timelines it walks, and past those how far from a walked timeline it looks: a dev run's most, 4 notes up to 64
# Greats, doubled.
_GREATS_SEARCHED = 16
_GREATS_WALKED = 8
# The gear combinations partial_sets may visit per Great count of a lookup and per line, ~1 us each: most guesses that fit take
# under 30,000, and a line no guess fits takes all of its share.
_GUESS_WORK = 1_200_000
_GUESS_LINE_WORK = 150_000
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
_HEAD_CHANCE = 0.01  # and leaves out head Greats beyond what chance gives this share of plays
# What a gem gap costs a line, in nats per share of the score; half that on a play with Greats, whose play cost already holds how
# likely its Greats lie where they do: tuned on the dev split (with the true line found, the first 8 hold it on 21 of 76 Great plays
# at 100, 15 at 200; the benchmark lists 2 more), 14 more true lines listed held out. A plan that moves its fever on purpose (a
# Force Great plan) fits any timeline and needs no chance in its Greats: it costs this, on a build whose gem gap costs more; at this
# share of a song's top a search always looks at every timeline, since such plans live there.
_GAP_COST = 200.0
_GREAT_GAP_COST = 100.0
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
_NO_CLASSES = np.empty((0, CLASS_COLUMNS), dtype=np.int64)  # a clean play's
_LOG_FACTORIAL = np.concatenate(([0.0], np.cumsum(np.log(np.arange(1, _GREATS_SEARCHED + 2)))))


# --- a song, prepared once ---------------------------------------------------


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


@dataclass(frozen=True, eq=False)
class ReverseSong:
    """A song prepared for lookups: its loadouts and their ceiling over every TeamBuff, each cell's timeline at chart time, and
    what its lookups walked so far, each kept once."""

    chart: Chart
    curves: StatCurves
    gears: dict
    minis: dict[str, SongMini]
    catalog_minis: dict[str, Mini]  # the catalog's minis, for a guess's minis below max
    space: LoadoutSpace
    fixed: tuple[FixedStats, ...]
    fixed_rows: np.ndarray
    tables: ValueTables
    partial: PartialSpace  # what partial_sets' guess reads
    vertex_values: np.ndarray
    vertex_prices: np.ndarray
    top: float  # the most any line under the ceiling scores
    line_shape: np.ndarray  # per cell, its chart-time timeline's shape
    chart_fever: np.ndarray  # and its body fever
    chart_head: np.ndarray  # and its head mask
    naked: Factors  # a play's factors with no gear: its Casual score's
    gpu: SongTables
    walks: dict[tuple[int, int], FeverSurfaces]  # _walked
    timelines: dict[tuple, Timelines] = field(default_factory=dict)  # _timelines_of
    casual: dict[tuple, list | None] = field(default_factory=dict)  # _casual_timelines

    @property
    def notes(self) -> tuple[int, int]:
        return min(self.chart.total_notes, HEAD_NOTES), max(0, self.chart.total_notes - HEAD_NOTES)

    @property
    def multipliers(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.curves.f64["Combo Multiplier"], self.curves.combo_ramp, self.curves.f64["Fever Multiplier"]

    @cached_property
    def widest(self) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray, list[float]]:
        """What the widest Perfect window needs, built when a prepare or a lookup first asks: its walk as score_ceiling reads
        it, its surfaces' relief, and the ceiling of a build with each count of _TIME_GEM_COUNTS Perfect Time gems."""
        surfaces = _walked(self, _WIDEST_PERFECT_TIME)
        arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
        relief = _cell_relief(surfaces.cell_start, surfaces.cells, self.vertex_prices)
        losses = time_gem_losses(self.space, self.vertex_prices)
        return arrays, relief, [
            score_ceiling(arrays, self.multipliers[::2], self.notes, (self.vertex_values - gems * losses, self.vertex_prices, relief), 0.0, np.inf)[0]
            for gems in _TIME_GEM_COUNTS
        ]


def prepare_song(chart: Chart, catalog: Catalog, curves: StatCurves) -> ReverseSong:
    surfaces = fever_surfaces(chart, curves, 0)
    arrays = surfaces.coeffs, surfaces.pattern, surfaces.body_fever
    space = loadout_space(catalog, chart.name, chart.primary, chart.secondary)
    items = space.items, space.starts, space.gems
    fixed = sorted(fixed_stats(space, TEAM_BUFF_TIER_ORDER), key=lambda row: row.tier != _PREFERRED_TIER)
    fixed_rows = np.stack([row.row for row in fixed])
    points = curves.f64["Perfect Points"]
    combo, fever = curves.f64["Combo Multiplier"], curves.f64["Fever Multiplier"]
    notes = min(chart.total_notes, HEAD_NOTES), max(0, chart.total_notes - HEAD_NOTES)
    # The ceiling's first vertices: a grid of prices, up to those a stat cannot pass while a gem buys it.
    caps = prices_at_gems(space)
    grid = np.meshgrid(_POINTS_PRICES, *(caps[d] * np.asarray(_STAT_PRICE_SHARES) for d in range(1, 5)), indexing="ij")
    prices = np.stack([axis.ravel() for axis in grid], axis=1)
    used = np.zeros(5)
    gifts = np.asarray([[2.0 * row.row[5] + row.row[6] + price * row.row[0] for row in fixed] for price in prices[:, 0]])
    values = BOUND_ROUNDING + gifts.max(axis=1) + np.asarray([
        relaxed_best(*items, vertex, used) + points_conjugate(points, vertex[0])[0] for vertex in prices
    ])
    relief = _cell_relief(surfaces.cell_start, surfaces.cells, prices)
    # More vertices at the song's best lines: the lowest prices there stay tight for the lines around them, where most lookups
    # land (a cutting plane over the whole song).
    for _ in range(_SHARPENING_ROUNDS):
        _best, (u, cm, fm, _base) = score_ceiling(arrays, (combo, fever), notes, (values, prices, relief), 0.0, np.inf)
        cells = surfaces.cells[surfaces.cell_start[u] : surfaces.cell_start[u + 1]]
        stats = np.column_stack((np.full(cells.shape, cm), np.full(cells.shape, fm), cells // _AXIS, cells % _AXIS))
        bounds = (values[None, :] - stats @ prices[:, 1:].T).min(axis=1)
        cell = cells[int(np.argmax(bounds))]
        at = np.asarray([0.0, cm, fm, cell // _AXIS, cell % _AXIS])
        vertex = prices[np.argmin(values - prices[:, 1:] @ at[1:])].copy()
        bound = lowest_at(items, fixed_rows, points, at, vertex, _BOUND_STEPS)
        values = np.append(values, bound + float(vertex[1:] @ at[1:]))
        prices = np.vstack((prices, vertex))
        relief = np.hstack((relief, _cell_relief(surfaces.cell_start, surfaces.cells, vertex[None, :])))
    top = score_ceiling(arrays, (combo, fever), notes, (values, prices, relief), 0.0, np.inf)[0]
    shapes, chart_fever, chart_head = _chart_timelines(chart, curves)
    return ReverseSong(
        chart, curves, dict(catalog.gears),
        {mini.name: mini for mini in song_minis(catalog.minis.values(), chart.name, chart.primary, chart.secondary)}, dict(catalog.minis),
        space, tuple(fixed), fixed_rows, value_tables(space), partial_space(catalog, space, fixed_rows, chart.name),
        values, prices, top, shapes, chart_fever, chart_head, factors(empty_stats(), curves, chart.primary, chart.secondary),
        SongTables(combo, curves.combo_ramp, fever, points, values, prices[:, 1:3], *notes, chart.primary == chart.secondary),
        {(0, 0): surfaces},
    )


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


# --- the timelines a search walks ----------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class Timelines:
    """The surfaces a search walks, likeliest first: by the fewest notes their body fever lies off a cell's chart-time timeline, so
    a search its budget cuts keeps the timelines a play is likeliest to have taken. tables: the GPU's tables of them, each one's
    head mask and body fever among them; bands: per surface the first and last + 1 walked surface in its band, whose cells are
    cells[cell_start[w] : cell_start[w + 1]], sorted by FT + FF."""

    tables: SurfaceTables
    bands: np.ndarray
    cell_start: np.ndarray
    cells: np.ndarray


def _walked(song: ReverseSong, perfect_time: int, greats: int = 0) -> FeverSurfaces:
    """The timelines of a play at this Perfect Time with at most this many Greats: walked the first time a lookup needs them."""
    if (perfect_time, greats) not in song.walks:
        song.walks[perfect_time, greats] = fever_surfaces(song.chart, song.curves, perfect_time, greats)
    return song.walks[perfect_time, greats]


def _near_chart_time(song: ReverseSong, surfaces: FeverSurfaces, same_head: bool) -> FeverSurfaces:
    """The surfaces with only the cells whose chart-time timeline they lie within _NEAR_NOTES of; same_head: and share its head."""
    owner = np.repeat(np.arange(surfaces.cell_start.shape[0] - 1), np.diff(surfaces.cell_start))
    near = np.abs(surfaces.body_fever[owner] - song.chart_fever[surfaces.cells]) <= _NEAR_NOTES
    if same_head:
        near &= (surfaces.words[surfaces.pattern[owner], :4] == song.chart_head[surfaces.cells]).all(axis=1)
    alive = np.bincount(owner[near], minlength=surfaces.body_fever.shape[0])
    kept = alive > 0
    return replace(surfaces, pattern=surfaces.pattern[kept], body_fever=surfaces.body_fever[kept], cell_start=np.concatenate(([0], np.cumsum(alive[kept]))), cells=surfaces.cells[near])


def _timelines_of(song: ReverseSong, greats: int, near: bool, perfect_time: int = 0) -> Timelines:
    """The timelines of a play with this many Greats at this Perfect Time, built the first time a lookup needs them: walked for
    few Greats, past _GREATS_WALKED the band around those walked for that many; near: only those near a cell's chart-time
    timeline, up to _GREATS_WALKED Greats with its head."""
    walked_for, past = min(greats, _GREATS_WALKED), greats > _GREATS_WALKED
    key = perfect_time, walked_for, past, near
    if key not in song.timelines:
        surfaces = _walked(song, perfect_time, walked_for)
        if near:
            surfaces = _near_chart_time(song, surfaces, not past)
        relief = _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
        sums = cell_sums(surfaces.cell_start, surfaces.cells)
        walk = surfaces.pattern, surfaces.body_fever, surfaces.cell_start, surfaces.cells, song.chart_fever
        pattern, body, wide_relief, wide_sums, bands, off = band_surfaces(walk, relief, sums, _BAND_NOTES if past and not near else 0, song.notes[1])
        first = np.argsort(off, kind="stable")
        tables = surface_tables((surfaces.words, surfaces.coeffs), (pattern[first], body[first]), wide_sums[first], wide_relief[first], song.notes[1])
        owner = np.repeat(np.arange(surfaces.cell_start.shape[0] - 1), np.diff(surfaces.cell_start))
        by_sum = np.lexsort((surfaces.cells // _AXIS + surfaces.cells % _AXIS, owner))
        song.timelines[key] = Timelines(tables, bands[first], surfaces.cell_start, surfaces.cells[by_sum])
    return song.timelines[key]


def warm_song(song: ReverseSong, accuracy: float | None) -> None:
    """Ahead of a lookup, the walks it may need at this accuracy: the widest Perfect window's, which its verdict reads, and
    each Great count's timelines near chart time and on every timeline (_sets_of), so the lookup itself only searches. It
    changes no answer: lookups walk the same timelines, once per song."""
    song.widest  # cached: built here, the first time
    lost = lost_quarters(PlayInfo(1, accuracy), song.chart.total_notes)
    for greats in range(lost[0], min(lost[1], _GREATS_SEARCHED) + 1):
        for near in (True, False) if greats else (False,):
            _timelines_of(song, greats, near)


# --- a play, and what its Casual score tells of its Greats -------------------------


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


def _casual_window(play: PlayInfo) -> tuple[float, float] | None:
    """The Casual score a play shows: exactly, or within the rounding of its Gear Multiplier."""
    if play.casual_score is not None:
        return float(play.casual_score), float(play.casual_score)
    if play.gear_multiplier is None:
        return None
    return play.score / (play.gear_multiplier + _MULTIPLIER_ROUNDING), play.score / (play.gear_multiplier - _MULTIPLIER_ROUNDING)


def _casual_cell(song: ReverseSong) -> tuple[float, float]:
    """Cell (0, 0), where a play's Casual score is played: its Perfect-only fill and its fever ms."""
    durations, thresholds = fever_axes(song.chart.total_notes, song.chart.long_notes, song.chart.last_note_time, song.curves)
    return float(thresholds[0]), float(durations[0]) * 1000.0


def _great_losses(scored: Factors, head: int, fever: float = 1.0) -> np.ndarray:
    """What a Great costs a set at each head note, in fever at that multiplier."""
    ramp = scored.ramp[:head]
    return np.floor(scored.base * ramp * fever).astype(np.int64) - np.floor(float(scored.great_base) * ramp * fever).astype(np.int64)


def _casual_timelines(song: ReverseSong, greats: int, perfect_time: int = 0) -> list[tuple[int, np.ndarray]] | None:
    """Per Casual timeline of a play with this many Greats: its score with no Greats, what a Great costs at each head note.
    Past _GREATS_WALKED the band around the timelines walked for those, as in _timelines_of. None when the walk's tables
    cannot hold them. Worked out once per song, walk, band and Perfect Time."""
    key = min(greats, _GREATS_WALKED), _BAND_NOTES if greats > _GREATS_WALKED else 0, perfect_time
    if key not in song.casual:
        song.casual[key] = _casual_walk(song, *key)
    return song.casual[key]


def _casual_walk(song: ReverseSong, walked: int, band: int, perfect_time: int) -> list[tuple[int, np.ndarray]] | None:
    chart, naked = song.chart, song.naked
    head, body = song.notes
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    ends = np.full((chart.total_notes, 6), -1, dtype=np.int64)
    threshold, duration = _casual_cell(song)
    scratch = walk_scratch(chart.total_notes, walked, _SCRATCH_ROWS)
    written = walk_cell(event_times(chart, perfect_time), great_times(chart, perfect_time), (threshold, walked), duration, scratch, out, ends)
    if written < 0:
        return None
    normal, inside = _great_losses(naked, head), _great_losses(naked, head, naked.fever)
    fever_gain = floor(naked.base * naked.combo * naked.fever) - floor(naked.base * naked.combo)  # of a body note in fever
    timelines = []
    for words, (lowest, highest, bits) in zip(pattern_words(out[:written, 0], out[:written, 1]).tolist(), out[:written, 2:5].tolist()):
        in_fever = np.unpackbits(np.asarray(words[:4], dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)
        losses = np.where(in_fever, inside, normal)
        clean = fg_surface_score(naked, FgResponseSurface(*words, 0, 0, 0), chart.total_notes)
        for body_fever in range(max(lowest - band, 0), min(highest + band, body) + 1):
            if band or bits < 0 or (bits >> (body_fever - lowest)) & 1:
                timelines.append((clean + body_fever * fever_gain, losses))
    return timelines


def _classes_of(play: PlayInfo, song: ReverseSong, greats: int) -> np.ndarray | None:
    """Where a play's Greats can lie, empty for a clean play; None when the row cannot tell: Greats need the Casual score and Gear
    Power, what tells a line's Greats apart. Head Greats are listed note by note only where some timeline has head fever."""
    if greats == 0:
        return _NO_CLASSES
    window = _casual_window(play)
    casual = None if window is None or play.gear_power is None else _casual_timelines(song, greats)
    if casual is None:
        return None
    head_fever = np.any(_walked(song, 0, min(greats, _GREATS_WALKED)).words[:, :4])
    return casual_classes(window, casual, greats, HEAD_LISTED if head_fever else 0)


# --- the stat lines of a score ---------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class FoundLines:
    """Every stat line of a search, a query on timelines: targets (search_targets rows), most plausible first, with what their
    plays cost alone and with the line's gem gap; held[spans[t, 0] : spans[t, 1]] the rows of line t; and the surfaces found so
    far by row and Great points (_played_set)."""

    timelines: Timelines
    query: LineQuery
    targets: np.ndarray
    plays: np.ndarray
    costs: np.ndarray
    rows: np.ndarray
    held: np.ndarray
    spans: np.ndarray
    complete: bool
    surfaces: dict = field(default_factory=dict)


def _line_costs(plays: np.ndarray, gaps: np.ndarray, greats: int) -> np.ndarray:
    """How far-fetched lines of a play with this many Greats are at these gem gaps, the likelier of an honest play and a plan."""
    return np.minimum(plays + (_GREAT_GAP_COST if greats else _GAP_COST) * gaps, _PLAN_COST + _PLAN_GAP_COST * gaps)


def _stat_lines(song: ReverseSong, timelines: Timelines, query: LineQuery) -> FoundLines:
    """The lines of a query, the plausible first: a play near chart time, gems a player would leave alone."""
    points = song.curves.f64["Perfect Points"]
    packed, complete = line_rows(song.gpu, timelines.tables, query)
    # The GPU appends rows in the order its threads race; each thread owns one (surface, CM, FM, base), so a sort by that, then
    # by a thread's scan (scan_order), makes every later step repeat run for run, and a cut below keep the surfaces the search
    # walked first.
    thread = (packed[:, 0].astype(np.int64) << 36) | (packed[:, 1].astype(np.int64) << 20) | packed[:, 2]
    packed = packed[scan_order(packed, thread, query.classes, points)]
    rows = np.empty((packed.shape[0], ROW_COLUMNS), dtype=np.int64)
    rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3] = packed[:, 0], packed[:, 1] >> 8, packed[:, 1] & 255, packed[:, 2]
    rows[:, 4], rows[:, 5], rows[:, 6], rows[:, 7] = packed[:, 3] >> 16, packed[:, 4], packed[:, 5], packed[:, 3] & 65535
    held = np.empty((MAX_ROWS, 8), dtype=np.int64)
    written = cell_lines(rows, query.power, points, (timelines.bands, timelines.cell_start, timelines.cells), (song.vertex_values, song.vertex_prices), held)
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
    explanation_costs(held, rows, query.classes, (song.chart_fever, timelines.tables.body_fever, *song.notes[::-1], _LOG_FACTORIAL), spans, plays)
    costs = _line_costs(plays, gaps, query.greats)
    shuffled = np.random.default_rng(0).permutation(costs.shape[0])
    plausible = shuffled[np.argsort(costs[shuffled], kind="stable")]
    return FoundLines(timelines, query, targets[plausible], plays[plausible], costs[plausible], rows, held, spans[plausible], complete)


# --- the sets that reach a line ------------------------------------------------------


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
    hits: dict[int, float] | None = None  # the play's hit offsets in ms, per note off its chart time (replay.play_offsets)
    mini_states: tuple[tuple[int, int, int], ...] = ()  # per mini (rank, level, ascension) of a guessed set; none at max


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


def _head_of(song: ReverseSong, line: tuple[int, int, int, int], worn: Factors, words: list[int]) -> list[int] | None:
    """The head notes a class loses its head Greats on, exact to the point, or None: a class that holds only their sum finds
    notes outside fever by a walk. line: (class's head Greats, its lowest and highest Casual loss, the score they lose)."""
    held, casual_low, casual_high, wanted = line
    head = song.notes[0]
    gear = _great_losses(worn, head)
    gear[np.unpackbits(np.asarray(words, dtype="<u4").view(np.uint8), bitorder="little")[:head].astype(bool)] = -1
    out = np.empty(held, dtype=np.int64)
    return out.tolist() if head_witness(gear, _great_losses(song.naked, head), held, (wanted, casual_low, casual_high), out) else None


def _played_surface(song: ReverseSong, scored: Factors, row: np.ndarray, lines: FoundLines) -> FgResponseSurface | None:
    """The surface of a row at a loadout's own stats, if its class gives the score: a play's timeline and Greats."""
    u, c, fevered = int(row[0]), int(row[4]), int(row[7])
    tables, classes = lines.timelines.tables, lines.query.classes
    words = tables.words[u].tolist()
    body_fever = int(tables.body_fever[u])
    if classes.shape[0] == 0:
        return FgResponseSurface(*words, 0, 0, 0, 0, body_fever, 0, 0)
    clean = fg_surface_score(scored, FgResponseSurface(*words, 0, 0, 0, 0, body_fever, 0, 0), song.chart.total_notes)
    spec = classes[c].tolist()
    held, body = spec[0], spec[1]
    body_loss = fevered * (floor(scored.base * scored.combo * scored.fever) - floor(float(scored.great_base) * scored.combo * scored.fever))
    body_loss += (body - fevered) * (floor(scored.base * scored.combo) - floor(float(scored.great_base) * scored.combo))
    notes = [note for note in spec[4:7] if note >= 0]
    if held and spec[4] < 0:
        notes = _head_of(song, (held, spec[7], spec[8], clean - lines.query.score - body_loss), scored, words)
    if notes is None:
        return None
    great_words = [0, 0, 0, 0]
    for note in notes:
        great_words[note >> 5] |= 1 << (note & 31)
    return FgResponseSurface(*words, *great_words, body_fever, body, fevered)


def _played_set(song: ReverseSong, worn: FoundSet, lines: FoundLines, t: int) -> FoundSet | None:
    """A set with its surface, if a row of line t gives the score at the set's own stats and Great points: every loadout of a
    line with the same Great points has the same surfaces, found once."""
    chart = song.chart
    scored = factors(worn.stats, song.curves, chart.primary, chart.secondary)
    rows = lines.rows[lines.held[lines.spans[t, 0] : lines.spans[t, 1], 0]]
    fitting = rows if lines.query.classes.shape[0] == 0 else rows[rows[:, 5] == scored.great_base]
    for row in fitting[:_ROWS_PER_SET]:
        key = (*row.tolist(), scored.great_base)
        if key not in lines.surfaces:
            lines.surfaces[key] = _played_surface(song, scored, row, lines)
        surface = lines.surfaces[key]
        if surface is not None and fg_surface_score(scored, surface, chart.total_notes) == lines.query.score:
            return replace(worn, surface=surface)
    return None


def _named_set(song: ReverseSong, found: np.ndarray, lines: FoundLines, gem_gap: float) -> FoundSet | None:
    """A search's loadout (a search_targets row), if a row of its line gives the score at the loadout's own Great points."""
    gear = tuple(song.space.names[i] for i in found[:6].tolist())
    minis = tuple(song.space.names[i] for i in found[6:9].tolist())
    pp, cm, fm, ft, ff, element_gems, element_row = found[9:16].tolist()
    colors = {PRIMARY: song.space.primary, SECONDARY: song.space.secondary}
    element = colors.get(element_row, next(color for color in ELEMENTS if color not in colors.values()))
    gems = dict(zip(GEM_KINDS, (pp, cm, fm, ft, ff, element_gems)))
    fixed = song.fixed[found[17]]
    stats = named_loadout_stats(team_buff_effect(fixed.tier, fixed.team_color), gear, minis, song.gears, song.minis, gems, element)
    return _played_set(song, FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, None, gem_gap), lines, int(found[16]))


def _guessed_set(song: ReverseSong, lines: FoundLines, t: int, budget: int) -> tuple[FoundSet | None, int]:
    """partial_sets' guess at line t, one no max-level set reaches, within `budget` gear combinations, and how many it visited;
    None without the line's Perfect Points stat (a row with no Gear Power) or a guess that fits."""
    chart, space, line = song.chart, song.partial, lines.targets[t]
    stat = int(line[7])
    if stat < 0:
        return None, 0
    elements = int(line[5]) - int(song.curves.f64["Perfect Points"][stat])
    row, used = guess_set(space, np.asarray([stat, *line[1:5].tolist(), elements], dtype=np.int64), budget)
    if row is None:
        return None, used
    gear = tuple(space.names[i] for i in row[partial_sets.GEAR].tolist() if i >= 0)
    minis = tuple(space.mini_names[i] for i in row[partial_sets.MINIS].tolist())
    worn = tuple(zip(row[partial_sets.RANKS].tolist(), row[partial_sets.LEVELS].tolist(), row[partial_sets.ASCENSIONS].tolist()))
    gems = dict(zip(GEM_KINDS, (*row[partial_sets.GEMS].tolist(), int(row[partial_sets.ELEMENT_GEMS]))))
    element = chart.primary if row[partial_sets.ELEMENT_ROW] == PRIMARY else song.space.secondary
    fixed = song.fixed[int(row[partial_sets.FIXED])]
    items = [song.gears[name].stats for name in gear] + [worn_mini_stats(song.catalog_minis[name], state, chart.name, chart.primary, chart.secondary) for name, state in zip(minis, worn)]
    stats = apply_gems(total(team_buff_effect(fixed.tier, fixed.team_color), *items), gems, element)
    guess = FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, None, 0.0, mini_states=worn)
    return _played_set(song, guess, lines, t), used


def _likeliest_sets(song: ReverseSong, lines: FoundLines, t: int) -> list[FoundSet]:
    """The sets of line t a player is likeliest to wear, likeliest first, each with the play that gives the score."""
    target = lines.targets[t]
    found = np.empty((_SETS_WEIGHED, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    points = song.curves.f64["Perfect Points"]
    query = target, lines.query.power, _FIRST_BAND * float(target[5]), _ITEMS_PER_TARGET
    found = found[: likeliest_loadouts(space, song.tables.arrays, song.fixed_rows, points, (song.vertex_values, song.vertex_prices), query, found)]
    found[:, 16] = t
    gaps, great_points = np.empty(found.shape[0]), np.empty(found.shape[0], dtype=np.int64)
    shapes = song.line_shape, song.multipliers[0], song.multipliers[2], points
    gem_gaps(found, (song.space.items, song.space.gems), song.fixed_rows, shapes, song.chart.primary == song.chart.secondary, gaps, great_points)
    given = shortfalls(song.space.items, song.space.starts, song.vertex_prices[target[6]])[0][found[:, :9]].sum(axis=1)
    sets: list[FoundSet] = []
    for r in np.argsort(gaps + _SHORTFALL_COST * given / float(target[5]), kind="stable").tolist():
        made = _named_set(song, found[r], lines, float(gaps[r]))
        if made is not None:
            sets.append(made)
            if len(sets) == _SETS_PER_LINE:
                break
    return sets


def _named_costs(lines: FoundLines, found: np.ndarray, gaps: np.ndarray, reached: int, unnamed: float) -> np.ndarray:
    """What lines cost once the search has walked `reached` of them: a loadout's own gem gap, less what it tells that a released
    set reaches a line, the rarer among the lines walked the more. A line no set reaches costs `unnamed` more."""
    best = np.full(lines.targets.shape[0], np.inf)
    np.minimum.at(best, found[:, 16], gaps)
    named = np.isfinite(best)
    costs = lines.costs + unnamed
    costs[named] = _line_costs(lines.plays[named], best[named], lines.query.greats) - np.log((reached + 1.0) / (np.count_nonzero(named) + 1.0))
    return costs


def _sets_of(play: PlayInfo, song: ReverseSong, greats: int, limit: int) -> tuple[list[FoundSet], list[StatLine], int, bool]:
    """The likeliest lines of a full combo with this many Greats and the sets that reach them: sets, lines, how many lines there
    are, and whether every line was searched."""
    power = -1 if play.gear_power is None else play.gear_power
    at_top = play.score >= _PLAN_HEIGHT * song.top
    bases = _TOP_LINE_BASES if at_top else _LINE_BASES
    classes = every = _classes_of(play, song, greats)
    # A play with Greats is searched near chart time first, with only as many Greats in the head as chance leaves _HEAD_CHANCE of
    # more; with fewer lines than _WIDE_UNDER there, or at a song's top where Force Great plans move their fever on purpose, on
    # every timeline, whose lines replace the near ones unless they are fewer. Past MAX_CLASSES places a row's numbers tell nothing.
    near = greats > 0 and not at_top
    if near and every is not None:
        share = song.notes[0] / max(song.chart.total_notes, 1)
        chance = np.cumsum([comb(greats, held) * share**held * (1.0 - share) ** (greats - held) for held in range(greats + 1)])
        classes = every[every[:, 0] <= int(np.searchsorted(chance, 1.0 - _HEAD_CHANCE))]
    if classes is None or classes.shape[0] > MAX_CLASSES:
        return [], [], 0, False
    lines = _stat_lines(song, _timelines_of(song, greats, near), LineQuery(play.score, power, greats, classes, bases))
    if near and lines.targets.shape[0] < _WIDE_UNDER and every.shape[0] <= MAX_CLASSES:
        wider = _stat_lines(song, _timelines_of(song, greats, False), LineQuery(play.score, power, greats, every, bases))
        if wider.targets.shape[0] >= lines.targets.shape[0]:
            lines, near = wider, False
    if lines.targets.shape[0] == 0:
        return [], [], 0, lines.complete and not near
    found = np.empty((_LINES_HELD * _SETS_PER_LINE, 18), dtype=np.int64)
    space = song.space.items, song.space.starts, song.space.gems
    points = song.curves.f64["Perfect Points"]
    search = lines.targets, power, _LINES_HELD, _PLAN_SEARCH_ITEMS if at_top else _SEARCH_ITEMS, _ITEMS_PER_TARGET, _ITEMS_PER_SETUP, _SETS_PER_LINE
    done, reached, complete = search_targets(space, song.tables.arrays, song.fixed_rows, points, (song.vertex_values, song.vertex_prices), search, found)
    found = found[:done]
    gaps, great_points = np.empty(done), np.empty(done, dtype=np.int64)
    shapes = song.line_shape, song.multipliers[0], song.multipliers[2], points
    gem_gaps(found, (song.space.items, song.space.gems), song.fixed_rows, shapes, song.chart.primary == song.chart.secondary, gaps, great_points)
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
        # A line the search found loadouts for is listed when one of them plays the score; its sets are then its likeliest, or
        # the search's own where that walk's budget found none.
        searched = (row for row in (_named_set(song, found[r], lines, float(gaps[r])) for r in tries[first[t] : last[t]].tolist()) if row is not None)
        played = next(searched, None)
        if played is not None:
            named[t] = [replace(row, cost=float(final[t])) for row in _likeliest_sets(song, lines, t) or (played, *searched)]
        if played is not None or last[t] == first[t]:
            listed.append(t)
        if len(listed) >= limit:
            break
    # With no line a max-level set reaches, lines get a guess, likeliest first, until one fits; at a song's top such a line is not
    # real.
    budget = 0 if at_top or named else _GUESS_WORK
    for t in [t for t in listed if t not in named]:
        if budget <= 0:
            break
        guess, used = _guessed_set(song, lines, t, min(budget, _GUESS_LINE_WORK))
        budget -= used
        if guess is not None:
            named[t] = [replace(guess, cost=float(final[t]))]
            break
    stat_lines = [
        StatLine(*lines.targets[t, 1:5].tolist(), int(lines.targets[t, 7]), int(lines.targets[t, 5]), float(final[t]), t in named)
        for t in listed
    ]
    return [row for t in listed for row in named.get(t, ())], stat_lines, lines.targets.shape[0], lines.complete and complete and not near


# --- the verdict ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnreleasedItem:
    """What a set would need beyond the released items: the slot, the item it would beat, the extra primary points."""

    slot: str
    beats: str
    extra_primary: int
    plausible: bool


@dataclass(frozen=True, slots=True)
class Reverse:
    verdict: str  # sets, lines (stats fit, no set reaches or guess fits them), unresolved, unreleased or exploited
    sets: tuple[FoundSet, ...]
    lines: int  # the exact stat lines under the ceiling that the lookup kept
    finished: bool  # every line was kept and searched to its end
    ceiling: float | None = None  # past the score: the first line found that reaches it
    unreleased: UnreleasedItem | None = None
    evidence: tuple[str, ...] = ()
    stat_lines: tuple[StatLine, ...] = ()  # the likeliest lines, likeliest first


def _honest_time(play: PlayInfo, song: ReverseSong) -> int:
    """The most Perfect Time a build can wear that reaches this score: the strongest gear of each slot, and the gems the
    ceiling leaves room for. A gem spent on it gives up a color gem, so near a song's top there is none."""
    gems = next((count - 1 for count, top in zip(_TIME_GEM_COUNTS, song.widest[2]) if play.score > top), GEM_BUDGET)
    strongest: dict[str, int] = {}
    for gear in song.gears.values():
        strongest[gear.slot] = max(strongest.get(gear.slot, 0), gear.perfect_time)
    return min(sum(strongest.values()) + _TIME_PER_GEM * gems, _WIDEST_PERFECT_TIME)


def _casual_highest(song: ReverseSong, quarters: int) -> float:
    """The most a play at this accuracy can score in Casual, at the widest Perfect window: Greats cost the least accuracy
    per note of fever they move, and they move it past what the ceiling of clean plays holds."""
    naked = song.naked
    threshold, duration = _casual_cell(song)
    times = event_times(song.chart, _WIDEST_PERFECT_TIME, quarters)
    most = fever_span(times, (ceil(threshold), ceil(threshold + quarters / 2.0)), duration)[1]
    normal, full = naked.base * naked.combo, naked.base * naked.combo * naked.fever
    return song.chart.total_notes * normal + most * (full - normal)


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
        # Every Casual score of a clean play: base stats, any timing inside the widest Perfect window a build at this score wears.
        timelines = _casual_timelines(song, 0, _honest_time(play, song))
        if timelines is None:
            raise ValueError("fever walk: the casual cell outgrew its tables")
        values = {score for score, _losses in timelines}
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
    query = LineQuery(int(play.score), play.gear_power, 0, _NO_CLASSES, _LINE_BASES)
    lines = _stat_lines(song, _timelines_of(song, 0, False, perfect_time), query)
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
    arrays, relief, _tops = song.widest
    spare = float(_FEVER_NOTES_PER_NOTE * lost[1])
    best, line = score_ceiling(arrays, song.multipliers[::2], song.notes, (song.vertex_values, song.vertex_prices, relief), spare, float(play.score))
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
    """The sets behind a play, ranked, each with its play's hit offsets; or what it would take; or the verdict that no honest
    play gives it."""
    lost = lost_quarters(play, song.chart.total_notes)
    found, listed, count, finished = [], [], 0, True
    for greats in range(lost[0], min(lost[1], _GREATS_SEARCHED) + 1):
        more, stat_lines, lines, done = _sets_of(play, song, greats, limit)
        found, listed, count, finished = found + more, listed + stat_lines, count + lines, finished and done
    found.sort(key=lambda row: row.cost)
    plays: dict[tuple, dict[int, float] | None] = {}  # sets of one line share their play
    for at, row in enumerate(found):
        play_key = row.surface, row.stats["Fever Time"], row.stats["Fever Fill Rate"], perfect_time_of(row.gear, song.gears)
        if play_key not in plays:
            plays[play_key] = play_offsets(song.chart, song.curves, *play_key)
        found[at] = replace(row, hits=plays[play_key])
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
    ceiling, base = _honest_ceiling(play, song, lost)
    if listed:
        return Reverse("lines", (), count, finished, ceiling, stat_lines=tuple(listed))
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling, base)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)


# --- one player's rows on several songs ------------------------------------------------


def _row_keys(play: PlayInfo, song: ReverseSong) -> tuple[np.ndarray, bool]:
    """Every (CM, FM, FT, FF, Perfect Points) that gives a row at its Gear Power, under the ceiling, as one number each, and whether
    they are all."""
    lost = lost_quarters(play, song.chart.total_notes)
    keys = []
    every_line = lost[1] <= _GREATS_SEARCHED
    for greats in range(lost[0], min(lost[1], _GREATS_SEARCHED) + 1):
        classes = _classes_of(play, song, greats)
        if classes is None or classes.shape[0] > MAX_CLASSES:
            every_line = False
        elif greats == 0 or classes.shape[0]:
            lines = _stat_lines(song, _timelines_of(song, greats, False), LineQuery(int(play.score), play.gear_power, greats, classes, _SHARED_BASES))
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
