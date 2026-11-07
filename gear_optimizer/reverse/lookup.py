"""Score reverse-lookup: a shown score and what the game's UI shows beside it, to the sets that give it.

The score equation leaves a few stat lines per surface; a loadout bound over the released items keeps the few a loadout
can still reach, a walk over the items finds the loadouts themselves, and gear_optimizer.score confirms each.
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
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.score import HEAD_NOTES, Factors, factors, fg_surface_score
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, named_loadout_stats

from .fever_reach import FeverSurfaces, event_times, fever_surfaces, pattern_words, walk_cell
from .invert import band_lines, line_targets, perfect_lines, score_ceiling
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
_LINE_ROWS = 1 << 18
_TARGET_ROWS = 1 << 16
_BOUND_STEPS = 200
_WALK_NODES = 1_000_000
_FOUND_ROWS = 16
_PREFERRED_TIER = "T5"
# The most a build's gems and gear can widen the Perfect window: no honest play is judged wider than this stat.
_WIDEST_PERFECT_TIME = MAX_STAT
# Measured on the dev rows: a Force Great moves fever by at most 12 notes; the worst share of a fever note's points one
# judgment can lose, a Miss with the combo ramp it restarts counted at a note's worth.
_FEVER_NOTES_PER_GREAT = 12
_LOST_PER_GREAT, _LOST_PER_OKAY, _LOST_PER_MISS = 0.42, 0.72, 2.0
# An unreleased item is plausible while it stands this share over the best the slot has.
_PLAUSIBLE_SHARE = 0.25
_TARGET_WALKS = 256
_SHARPENING_ROUNDS = 6
_SCRATCH_ROWS = 1 << 15


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
    honest: dict = field(default_factory=dict)


def prepare_song(chart: Chart, catalog: Catalog, curves: StatCurves) -> ReverseSong:
    surfaces = fever_surfaces(chart, curves, event_times(chart, 0))
    space = loadout_space(catalog, chart.name, chart.primary, chart.secondary)
    fixed = sorted(fixed_stats(space, TEAM_BUFF_TIER_ORDER), key=lambda row: row.tier != _PREFERRED_TIER)
    caps = prices_at_gems(space)
    shares = np.asarray(_STAT_PRICE_SHARES)
    grid = np.meshgrid(_POINTS_PRICES, *(caps[d] * shares for d in range(1, 5)), indexing="ij")
    prices = np.stack([axis.ravel() for axis in grid], axis=1)
    points = curves.f64["Perfect Points"]
    used = np.zeros(5)
    gifts = np.asarray([[2.0 * row.row[5] + row.row[6] + price * row.row[0] for row in fixed] for price in prices[:, 0]])
    values = gifts.max(axis=1) + np.asarray([
        relaxed_best(space.items, space.starts, space.gems, vertex, used) + points_conjugate(points, vertex[0])[0]
        for vertex in prices
    ])
    minis = {mini.name: mini for mini in song_minis(catalog.minis.values(), chart.name, chart.primary, chart.secondary)}
    song = ReverseSong(
        chart, curves, dict(catalog.gears), minis, surfaces, space, tuple(fixed), values, prices,
        _cell_relief(surfaces.cell_start, surfaces.cells, prices), max(int(row.row[0]) for row in fixed),
    )
    return _sharpened(song)


def _sharpened(song: ReverseSong) -> ReverseSong:
    """The song with vertices added at its best lines: the bound's lowest prices there stay tight for the lines around
    them, where most lookups land (a cutting plane over the whole song)."""
    surfaces = song.surfaces
    for _ in range(_SHARPENING_ROUNDS):
        ceiling = (song.vertex_values, song.vertex_prices, song.relief)
        _best, (u, cm, fm) = score_ceiling(
            (surfaces.coeffs, surfaces.pattern, surfaces.body_fever), _multipliers(song)[::2], _note_split(song.chart), ceiling, 0.0
        )
        cells = surfaces.cells[surfaces.cell_start[u] : surfaces.cell_start[u + 1]]
        stats = np.column_stack((np.full(cells.shape, cm), np.full(cells.shape, fm), cells // _AXIS, cells % _AXIS))
        cell = cells[int(np.argmax((song.vertex_values[None, :] - stats @ song.vertex_prices[:, 1:].T).min(axis=1)))]
        value, prices = _lowest_at(song, np.asarray([-song.top_pp, cm, fm, cell // _AXIS, cell % _AXIS], dtype=np.float64))
        relief = _cell_relief(surfaces.cell_start, surfaces.cells, prices[None, :])
        song = replace(
            song,
            vertex_values=np.append(song.vertex_values, value),
            vertex_prices=np.vstack((song.vertex_prices, prices)),
            relief=np.hstack((song.relief, relief)),
        )
    return song


def _lowest_at(song: ReverseSong, stats: np.ndarray) -> tuple[float, np.ndarray]:
    """The lowest bound the steps find at these stats (place 0: minus the top fixed Perfect Points), over every TeamBuff:
    as a vertex value (the bound before the stats' prices) and its prices."""
    prices = song.vertex_prices[np.argmin(song.vertex_values - song.vertex_prices[:, 1:] @ stats[1:])].copy()
    space = song.space
    bound = lowest_bound(space.items, space.starts, space.gems, song.curves.f64["Perfect Points"], stats, prices, _BOUND_STEPS)
    gift = max(2.0 * fixed.row[5] + fixed.row[6] + prices[0] * (fixed.row[0] - song.top_pp) for fixed in song.fixed)
    return bound + gift + float(prices[1:] @ stats[1:]), prices


@dataclass(frozen=True, slots=True)
class ShownPlay:
    """What a player can read of a play: the tool's input contract. Score: the Compete score of the results screen and
    every leaderboard; casual_score: Play Info's Casual Mode Score; accuracy: percent as shown; the four counts: the
    results screen's, all or none; gear_power: Play Info's; match_mode: Play Info's; team_buff: a tier, when known."""

    score: int
    casual_score: int | None = None
    accuracy: float | None = None
    perfect: int | None = None
    great: int | None = None
    okay: int | None = None
    miss: int | None = None
    gear_power: int | None = None
    match_mode: str = "Compete"
    team_buff: str | None = None


@dataclass(frozen=True, slots=True)
class Judged:
    """A play's judgments: Greats between great_lo and great_hi (accuracy leaves a range), Okays and Misses."""

    great_lo: int
    great_hi: int
    okay: int
    miss: int

    @property
    def clean(self) -> bool:
        return self.great_hi == 0 and self.okay == 0 and self.miss == 0


@dataclass(frozen=True, slots=True)
class FoundSet:
    """A released set that gives the score: exact, or (a play with Okays or Misses) in reach of it."""

    gear: tuple[str, ...]
    minis: tuple[str, ...]
    gems: dict[str, int]
    element: str
    team_buff: str
    team_color: str
    stats: dict[str, int]
    surface: FgResponseSurface
    slack: float
    exact: bool = True


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
    lines: int
    finished: bool
    ceiling: float | None = None
    unreleased: UnreleasedItem | None = None
    evidence: tuple[str, ...] = ()


def _multipliers(song: ReverseSong) -> tuple:
    return song.curves.f64["Combo Multiplier"], song.curves.combo_ramp, song.curves.f64["Fever Multiplier"]


def _note_split(chart: Chart) -> tuple[int, int]:
    return min(chart.total_notes, HEAD_NOTES), max(0, chart.total_notes - HEAD_NOTES)


def _final_stats(song: ReverseSong, row: np.ndarray, fixed: FixedStats) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, int], str, dict[str, int]]:
    """A found row as (gear, minis, gems, selected element, final stats)."""
    gear = tuple(song.space.names[i] for i in row[:6].tolist())
    minis = tuple(song.space.names[i] for i in row[6:9].tolist())
    pp, cm, fm, ft, ff, element_gems, element_row = row[9:].tolist()
    colors = {5: song.space.primary, 6: song.space.secondary}
    element = colors.get(element_row, next(c for c in ELEMENTS if c not in colors.values()))
    allocation = dict(zip(GEM_KINDS, (pp, cm, fm, ft, ff, element_gems)))
    base = team_buff_effect(fixed.tier, fixed.team_color)
    return gear, minis, allocation, element, named_loadout_stats(base, gear, minis, song.gears, song.minis, allocation, element)


def _surface_row(song: ReverseSong, u: int) -> FgResponseSurface:
    words = song.surfaces.words[song.surfaces.pattern[u]].tolist()
    return FgResponseSurface(*words, int(song.surfaces.body_fever[u]), 0, 0)


def _on_cells(song: ReverseSong, lines: np.ndarray, play: ShownPlay) -> np.ndarray:
    """The lines (surface, CM, FM, base, base) on their cells: target rows (surface, CM, FM, FT, FF, lowest base, highest
    base) under the vertices and in reach of the Gear Power, nearest their bound first."""
    surfaces = song.surfaces
    points = song.curves.f64["Perfect Points"]
    terms = np.sort(5.0 * np.arange(points.shape[0]) - 2.0 * points)
    power = -1 if play.gear_power is None else play.gear_power
    out = np.empty((_TARGET_ROWS, 8), dtype=np.int64)
    ceiling = (song.vertex_values, song.vertex_prices, song.relief)
    count = line_targets(lines, surfaces.cell_start, surfaces.cells, ceiling, terms, power, out)
    rows = out[: min(count, _TARGET_ROWS)]
    return rows[np.argsort(rows[:, 7], kind="stable"), :7]


def _tight_bound(song: ReverseSong, target: np.ndarray, cuts: list[tuple[float, np.ndarray]]) -> tuple[float, np.ndarray] | None:
    """The bound and prices of a target row of _on_cells, None when a bound already found rules it out; a new bound is
    kept in `cuts`: its prices stay nearly as tight for the rows beside it."""
    stats = np.asarray([-song.top_pp, *target[1:5].tolist()], dtype=np.float64)
    for value, prices in cuts:
        if value - prices[1:] @ stats[1:] < target[5]:
            return None
    value, prices = _lowest_at(song, stats)
    cuts.append((value, prices))
    bound = value - float(prices[1:] @ stats[1:])
    return (bound, prices) if bound >= target[5] else None


def _loadouts_of(song: ReverseSong, target: np.ndarray, tight: tuple[float, np.ndarray]) -> tuple[list[tuple], bool]:
    """The released sets of a target row: (gear, minis, gems, element, stats, fixed row, slack), and whether the walk
    could finish."""
    bound, prices = tight
    gift = max(2.0 * fixed.row[5] + fixed.row[6] + prices[0] * (fixed.row[0] - song.top_pp) for fixed in song.fixed)
    cm, fm, ft, ff, lowest, highest = target[1:].tolist()
    rows = np.empty((_FOUND_ROWS, 16), dtype=np.int64)
    walk_target = np.asarray([0, cm, fm, ft, ff], dtype=np.int64)
    bases = np.asarray([lowest, highest], dtype=np.int64)
    space = song.space
    found: list[tuple] = []
    finished = True
    for fixed in song.fixed:
        slack = bound - gift + prices[0] * (fixed.row[0] - song.top_pp) + 2.0 * fixed.row[5] + fixed.row[6] - lowest
        if slack < 0.0:
            continue
        query = (walk_target, bases, slack, prices, fixed.row)
        count, complete = walk_loadouts(space.items, space.starts, space.gems, song.curves.f64["Perfect Points"], query, rows, _WALK_NODES)
        finished = finished and complete
        found += [(*_final_stats(song, row, fixed), fixed, float(slack)) for row in rows[:count]]
    return found, finished


def _power_of(stats: dict[str, int], song: ReverseSong) -> int:
    """PlayerBlobAvatar statsdict_get_gear_power at the song's colors."""
    primary, secondary = stats[song.chart.primary], stats[song.chart.secondary]
    five = sum(stats[stat] for stat in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"))
    return 5 * five + 4 * primary + 2 * secondary


def _surface_arrays(surfaces: FeverSurfaces) -> tuple:
    return surfaces.words, surfaces.coeffs, surfaces.pattern, surfaces.body_fever


def _found_of(song: ReverseSong, rows: list[tuple], play: ShownPlay) -> list[tuple]:
    if play.gear_power is None:
        return rows
    return [row for row in rows if _power_of(row[4], song) == play.gear_power]


def _perfect_sets(play: ShownPlay, song: ReverseSong, limit: int) -> tuple[list[FoundSet], int, bool]:
    chart = song.chart
    out = np.empty((_LINE_ROWS, 4), dtype=np.int64)
    ceiling = (song.vertex_values, song.vertex_prices, song.relief)
    count = perfect_lines(int(play.score), _surface_arrays(song.surfaces), _multipliers(song), _note_split(chart), ceiling, out)
    lines = out[: min(count, _LINE_ROWS)]
    targets = _on_cells(song, np.column_stack((lines, lines[:, 3])), play)
    found: list[FoundSet] = []
    finished = count <= _LINE_ROWS
    cuts: list[tuple[float, np.ndarray]] = []
    for target in targets:
        tight = _tight_bound(song, target, cuts)
        if tight is None:
            continue
        rows, complete = _loadouts_of(song, target, tight)
        finished = finished and complete
        surface = _surface_row(song, int(target[0]))
        for gear, minis, gems, element, stats, fixed, slack in _found_of(song, rows, play):
            value = fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)
            if value != play.score:
                raise ValueError(f"reverse lookup: a set of line {target.tolist()} scores {value}, not {play.score}")
            found.append(FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, slack))
        if len(found) >= limit:
            finished = False
            break
    return found, count, finished


def _timelines(song: ReverseSong, cell: tuple[int, int], greats: int, perfect_time: int) -> tuple[np.ndarray, np.ndarray]:
    """The timelines of one cell a play with these Greats reaches: (pattern words, rows (.., .., lowest, highest, bits))."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    ft, ff = cell
    scratch = (np.empty((_SCRATCH_ROWS, 6), dtype=np.int64), np.empty((_SCRATCH_ROWS, 6), dtype=np.int64))
    out = np.empty((_SCRATCH_ROWS, 5), dtype=np.int64)
    fills = (ceil(thresholds[ff]), ceil(thresholds[ff] + greats / 2))
    written = walk_cell(event_times(chart, perfect_time, greats), fills, float(durations[ft]) * 1000.0, scratch, out)
    if written < 0:
        raise ValueError(f"fever walk: cell {cell} outgrew its tables")
    rows = out[:written]
    return pattern_words(rows[:, 0], rows[:, 1]), rows


def _body_counts(row: np.ndarray) -> list[int]:
    lowest, highest, bits = row[2:5].tolist()
    return [count for count in range(lowest, highest + 1) if bits < 0 or (bits >> (count - lowest)) & 1]


def _great_placement(f: Factors, surface: FgResponseSurface, greats: int, score: int, notes: tuple[int, int]) -> FgResponseSurface | None:
    """The surface with `greats` Great notes placed to lose exactly what the all-Perfect surface scores over `score`.

    Body notes lose one of two amounts; a head note its own, by its combo: subset sums per Great count, as bit sets."""
    head_len, body_total = notes
    fever_bits = [(surface[note // 32] >> (note % 32)) & 1 for note in range(head_len)]
    lost = fg_surface_score(f, surface, head_len + body_total) - score
    if lost < 0:
        return None
    combo_value = int(np.floor(f.base * f.combo))
    fever_value = int(np.floor(f.base * f.combo * f.fever))
    normal_loss = combo_value - int(np.floor(float(f.great_base) * f.combo))
    fever_loss = fever_value - int(np.floor(float(f.great_base) * f.combo * f.fever))
    window = (1 << (lost + 1)) - 1
    sums = [[0] * (greats + 1) for _ in range(head_len + 1)]
    sums[0][0] = 1
    for note in range(head_len):
        scaling = float(f.ramp[note])
        keep = f.fever if fever_bits[note] else 1.0
        loss = int(np.floor(f.base * scaling * keep)) - int(np.floor(float(f.great_base) * scaling * keep))
        sums[note + 1] = list(sums[note])
        for count in range(greats):
            sums[note + 1][count + 1] |= (sums[note][count] << loss) & window
    for head in range(min(greats, head_len) + 1):
        body = greats - head
        for in_fever in range(min(body, surface.body_fever) + 1):
            left = lost - in_fever * fever_loss - (body - in_fever) * normal_loss
            if body - in_fever > body_total - surface.body_fever or left < 0 or not (sums[head_len][head] >> left) & 1:
                continue
            words = [0, 0, 0, 0]
            count = head
            for note in range(head_len - 1, -1, -1):
                if count and not (sums[note][count] >> left) & 1:
                    scaling = float(f.ramp[note])
                    keep = f.fever if fever_bits[note] else 1.0
                    left -= int(np.floor(f.base * scaling * keep)) - int(np.floor(float(f.great_base) * scaling * keep))
                    count -= 1
                    words[note // 32] |= 1 << (note % 32)
            return FgResponseSurface(*surface[:4], *words, surface.body_fever, body, in_fever)
    return None


def _great_fit(song: ReverseSong, stats: dict[str, int], judged: Judged, score: int) -> FgResponseSurface | None:
    """A surface with this play's Greats that scores `score` at these stats exactly."""
    chart = song.chart
    f = factors(stats, song.curves, chart.primary, chart.secondary)
    notes = _note_split(chart)
    cell = (stats["Fever Time"], stats["Fever Fill Rate"])
    for greats in range(judged.great_lo, judged.great_hi + 1):
        words, rows = _timelines(song, cell, greats, 0)
        for pattern, row in zip(words.tolist(), rows):
            for body_fever in _body_counts(row):
                surface = FgResponseSurface(*pattern, body_fever, 0, 0)
                placed = _great_placement(f, surface, greats, score, notes)
                if placed is not None:
                    return placed
    return None


def _band_sets(play: ShownPlay, song: ReverseSong, judged: Judged, limit: int) -> tuple[list[FoundSet], int, bool]:
    """The sets of a play that left the surfaces: lines in reach of the score, then each set's own test."""
    chart = song.chart
    out = np.empty((_LINE_ROWS, 5), dtype=np.int64)
    spare = float(_FEVER_NOTES_PER_GREAT * judged.great_hi)
    lost = _LOST_PER_GREAT * judged.great_hi + _LOST_PER_OKAY * judged.okay + _LOST_PER_MISS * judged.miss
    ceiling = (song.vertex_values, song.vertex_prices, song.relief)
    count = band_lines(int(play.score), _surface_arrays(song.surfaces)[1:], _multipliers(song)[::2], _note_split(chart), ceiling, (spare, lost), out)
    lines = out[: min(count, _LINE_ROWS)]
    targets = _on_cells(song, lines, play)
    found: list[FoundSet] = []
    finished = count <= _LINE_ROWS and len(targets) <= _TARGET_WALKS
    cuts: list[tuple[float, np.ndarray]] = []
    exact_only = judged.okay == 0 and judged.miss == 0
    walked: set[tuple[int, ...]] = set()
    for target in targets:
        key = tuple(target[1:].tolist())
        if key in walked:
            continue
        walked.add(key)
        if len(walked) > _TARGET_WALKS:
            finished = False
            break
        tight = _tight_bound(song, target, cuts)
        if tight is None:
            continue
        rows, complete = _loadouts_of(song, target, tight)
        finished = finished and complete
        for gear, minis, gems, element, stats, fixed, slack in _found_of(song, rows, play):
            surface = _great_fit(song, stats, judged, int(play.score)) if exact_only else FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            if surface is None:
                continue
            if exact_only:
                value = fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)
                if value != play.score:
                    raise ValueError(f"reverse lookup: a placed surface scores {value}, not {play.score}")
            found.append(FoundSet(gear, minis, gems, element, fixed.tier, fixed.team_color, stats, surface, slack, exact_only))
        if len(found) >= limit:
            finished = False
            break
    return found, count, finished


def judged_play(play: ShownPlay, notes: int) -> Judged:
    """The judgments a shown play can have. Accuracy alone leaves its rounding's Greats (each costs 0.25 of a note);
    with neither, a clean play is assumed."""
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


def _casual_reach(song: ReverseSong, judged: Judged) -> tuple[int, int, set[int]]:
    """The Casual score of an honest play with these judgments: its lowest and highest, and every value of a clean play.
    The casual bar fills from base stats and the widest Perfect window any build can wear."""
    chart = song.chart
    naked = factors(empty_stats(), song.curves, chart.primary, chart.secondary)
    words, rows = _timelines(song, (0, 0), judged.great_hi, _WIDEST_PERFECT_TIME)
    values = {
        fg_surface_score(naked, FgResponseSurface(*pattern, body_fever, 0, 0), chart.total_notes)
        for pattern, row in zip(words.tolist(), rows)
        for body_fever in _body_counts(row)
    }
    full = naked.base * naked.combo * naked.fever
    # A note loses at most its fever value; a break also restarts the combo ramp (at most 50 notes' worth of a fever note).
    worst = judged.great_hi * 0.25 * full + judged.okay * (2.0 / 3.0) * full + judged.miss * 51.0 * full
    return int(min(values) - worst), max(values), values


def _casual_evidence(play: ShownPlay, song: ReverseSong, judged: Judged) -> str | None:
    """Why the Casual score cannot come from an honest Compete play, if it cannot. The server fills the bar from each
    event's time offset and scores the result the event states (push_note_sequence), so a Perfect stated on a Great's
    offset keeps a Perfect's points and a Great's fill; that moves the casual fever too, and base stats hide nothing.
    Casual matches are out: their client zeroes Perfect Time and their server does not."""
    if play.casual_score is None or play.match_mode != "Compete":
        return None
    lowest, highest, values = _casual_reach(song, judged)
    if judged.clean and play.casual_score not in values:
        return f"Casual score {play.casual_score} is not one of the {len(values)} a clean play reaches: {sorted(values)[:6]}"
    if not lowest <= play.casual_score <= highest:
        return f"Casual score {play.casual_score} is outside {lowest}..{highest}, all an honest play with these judgments reaches"
    return None


def _honest_ceiling(song: ReverseSong, judged: Judged) -> float:
    """The most an honest play scores with any released loadout at any Perfect window: never under a real score."""
    chart = song.chart
    surfaces = song.honest.get("surfaces")
    if surfaces is None:
        surfaces = fever_surfaces(chart, song.curves, event_times(chart, _WIDEST_PERFECT_TIME))
        song.honest["surfaces"] = surfaces
        song.honest["relief"] = _cell_relief(surfaces.cell_start, surfaces.cells, song.vertex_prices)
    return score_ceiling(
        (surfaces.coeffs, surfaces.pattern, surfaces.body_fever), _multipliers(song)[::2], _note_split(chart),
        (song.vertex_values, song.vertex_prices, song.honest["relief"]), float(_FEVER_NOTES_PER_GREAT * judged.great_hi),
    )[0]


def _unreleased_item(play: ShownPlay, song: ReverseSong, ceiling: float) -> UnreleasedItem:
    """The item that would close the gap to the ceiling, in the slot where it stands least over the slot's best."""
    space = song.space
    prices = song.vertex_prices[0]
    used = np.zeros(5)
    weight = float(2 * space.gems[5, 5] + space.gems[5, 6]) / float(space.gems[5, 5])
    top_base = float(song.vertex_values.min())
    excess = (float(play.score) / ceiling - 1.0) * top_base
    extra = ceil(excess / weight)
    relaxed_best(space.items, space.starts, space.gems, prices, used)
    best_slot, best_share, best_item = "", float("inf"), ""
    for slot, name in enumerate((*GEAR_SLOTS, "Mini")):
        rows = space.items[space.starts[slot] : space.starts[slot + 1]]
        weights = rows[:, 5:7].sum(axis=1) + rows[:, 1:5].sum(axis=1)
        strongest = int(np.argmax(weights))
        share = extra / max(float(weights[strongest]), 1.0)
        if share < best_share:
            best_slot, best_share, best_item = name, share, space.names[int(space.starts[slot]) + strongest]
    return UnreleasedItem(best_slot, best_item, extra, best_share <= _PLAUSIBLE_SHARE)


def reverse_score(play: ShownPlay, song: ReverseSong, *, limit: int = 8) -> Reverse:
    """The sets behind a shown play, ranked; or what it would take; or the verdict that no honest play gives it."""
    judged = judged_play(play, song.chart.total_notes)
    if judged.great_lo == 0 and judged.okay == 0 and judged.miss == 0:
        found, count, finished = _perfect_sets(play, song, limit)
    else:
        found, count, finished = [], 0, True
    if not found and not judged.clean:
        found, count, finished = _band_sets(play, song, judged, limit)
    found.sort(key=lambda row: row.slack)
    evidence = _casual_evidence(play, song, judged)
    if evidence is not None:
        return Reverse("exploited", tuple(found), count, finished, evidence=(evidence,))
    if found:
        return Reverse("sets", tuple(found), count, finished)
    ceiling = _honest_ceiling(song, judged)
    if play.score <= ceiling:
        return Reverse("unresolved", (), count, finished, ceiling)
    item = _unreleased_item(play, song, ceiling)
    return Reverse("unreleased" if item.plausible else "exploited", (), count, finished, ceiling, item)
