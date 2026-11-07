"""The score reverse-lookup, through its public entry point, on an official chart and the game's catalog."""

from __future__ import annotations

import random
from math import ceil

import numpy as np
import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import STATS, empty_stats, stat_curves
from gear_optimizer.reverse.fever_reach import event_times, fever_surfaces
from gear_optimizer.reverse.lookup import ShownPlay, judged_play, prepare_song, reverse_score
from gear_optimizer.score import best_timeline_score, factors, fg_surface_score
from gear_optimizer.settings import paths
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid, fixed_timeline_cell
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.store.records import FgResult, Loadout
from tools.verify.frame_play import Plan, frame_clock, play
from tools.verify.score_reverse_benchmark import _build, _hacked

CHART = "Aether (Easy) by Geoxor.txt"
STORED = dict(zip(STATS, (85, 59, 71, 66, 63, 35, 135, 73, 34, 707)))


@pytest.fixture(scope="module")
def song():
    chart = load_chart(paths().chart_dir("Easy") / CHART)
    return prepare_song(chart, load_catalog(paths().game_export), stat_curves())


def test_chart_time_timelines_are_among_the_reachable(song):
    """Every cell's timeline at chart time (solver.fever_timeline) is one the walk reaches."""
    chart, surfaces = song.chart, song.surfaces
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    fills = np.ceil(thresholds).astype(np.int64)
    fever, normal = np.zeros((161, 161), np.int32), np.zeros((161, 161), np.int32)
    words = np.zeros((161, 161, 4), np.uint32)
    extra = np.zeros((161, 161), np.int32), np.zeros((161, 161), np.int32)
    calculate_fever_timeline_surface_grid(chart.timestamps, chart.total_notes, durations, fills, (fever, normal, words, *extra))
    reached = set()
    for u in range(surfaces.body_fever.shape[0]):
        for cell in surfaces.cells[surfaces.cell_start[u] : surfaces.cell_start[u + 1]].tolist():
            reached.add((cell, tuple(surfaces.words[surfaces.pattern[u], :4].tolist()), int(surfaces.body_fever[u])))
    for ft, ff in ((0, 0), (11, 73), (63, 66), (160, 160)):
        assert (ft * 161 + ff, tuple(words[ft, ff].tolist()), int(fever[ft, ff])) in reached


def test_wider_windows_reach_every_timeline_of_narrower_ones(song):
    wider = fever_surfaces(song.chart, song.curves, event_times(song.chart, 13))
    assert wider.body_fever.shape[0] >= song.surfaces.body_fever.shape[0]


def test_a_stored_meta_build_is_found_from_its_score_alone(song):
    """Precise Meta #1 of the chart, from a results database: a known set and its score."""
    reply = reverse_score(ShownPlay(score=4_666_274), song, limit=64)
    assert reply.verdict == "sets"
    line = ("Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
    found = [row for row in reply.sets if tuple(row.stats[stat] for stat in line) == (59, 71, 66, 63)]
    assert found and all(row.gear[0] == "The Games: Hidden Shine" for row in found)
    assert {"Shaii", "Electroman", "Doppelganger Roxie"} == set(found[0].minis)
    chart = song.chart
    for row in reply.sets:
        scored = factors(row.stats, song.curves, chart.primary, chart.secondary)
        assert fg_surface_score(scored, row.surface, chart.total_notes) == 4_666_274


def test_gear_power_keeps_only_the_sets_that_show_it(song):
    chart = song.chart

    def power(stats):
        five = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
        return 5 * sum(stats[key] for key in five) + 4 * stats[chart.primary] + 2 * stats[chart.secondary]

    reply = reverse_score(ShownPlay(score=4_666_274, gear_power=power(STORED)), song)
    assert reply.sets and all(power(row.stats) == power(STORED) for row in reply.sets)


def test_a_score_past_every_released_set_is_not_given_a_set(song):
    reply = reverse_score(ShownPlay(score=10**9), song)
    assert reply.verdict in ("unreleased", "exploited")
    assert reply.ceiling is not None and reply.ceiling < 10**9


def test_a_casual_score_no_clean_play_reaches_is_exploited(song):
    casual = fg_surface_score(
        factors(empty_stats(), song.curves, song.chart.primary, song.chart.secondary),
        FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), song.chart.total_notes,
    )
    reply = reverse_score(ShownPlay(score=4_666_274, casual_score=casual, accuracy=100.0), song)
    assert reply.verdict == "exploited" and reply.evidence


def test_a_casual_score_without_shown_judgments_proves_nothing(song):
    assert reverse_score(ShownPlay(score=4_666_274, casual_score=1), song).verdict == "sets"


def test_a_casual_match_is_never_called_exploited_on_its_casual_score(song):
    reply = reverse_score(ShownPlay(score=4_666_274, casual_score=1, accuracy=100.0, match_mode="Casual"), song)
    assert reply.verdict == "sets"


def _simulated(song, stats, plan, seed=1):
    frames = frame_clock(np.random.default_rng(seed), float(song.chart.timestamps[-1]) * 1000.0, 60.0, 0.0)
    return play(song.chart, stats, 0, plan, frames)


def test_the_frame_simulator_at_a_1_ms_clock_is_the_chart_time_replay(song):
    """Nothing to judge late at a 1 ms clock: an autoplay is the engine's Non-Precise timeline, note for note."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    fill = ceil(thresholds[STORED["Fever Fill Rate"]])
    cell = fixed_timeline_cell(chart.timestamps, fill_notes=fill, fever_duration=float(durations[STORED["Fever Time"]]))
    expected = best_timeline_score(factors(STORED, song.curves, chart.primary, chart.secondary), cell, chart.total_notes)[0]
    clock = np.arange(-1000.0, float(chart.timestamps[-1]) * 1000.0 + 2000.0, 1.0)
    assert play(chart, STORED, 0, Plan(np.zeros(chart.total_notes)), clock).score == expected


def test_a_set_far_below_the_top_gets_sets_that_give_its_score_exactly(song):
    build = _build(random.Random(4), "colored", song)
    played = _simulated(song, build.stats, Plan(np.zeros(song.chart.total_notes)))
    reply = reverse_score(ShownPlay(score=played.score), song)
    assert reply.verdict == "sets"
    chart = song.chart
    for row in reply.sets:
        scored = factors(row.stats, song.curves, chart.primary, chart.secondary)
        assert fg_surface_score(scored, row.surface, chart.total_notes) == played.score


def test_a_fever_hack_shows_in_its_casual_score_and_an_honest_play_does_not(song):
    """Presses in Great windows stated Perfect: a Perfect's points, a Great's fill."""
    chart = song.chart
    hacked_plan = Plan(_hacked(0.5)(np.random.default_rng(2), chart), states_perfect=True)
    hacked = _simulated(song, STORED, hacked_plan)
    assert (hacked.great, hacked.okay, hacked.miss) == (0, 0, 0)
    honest = _simulated(song, STORED, Plan(np.zeros(chart.total_notes)))
    for played, verdicts in ((hacked, ("exploited",)), (honest, ("sets", "unresolved"))):
        shown = ShownPlay(score=played.score, casual_score=played.casual, accuracy=100.0)
        assert reverse_score(shown, song).verdict in verdicts


def test_a_play_near_the_top_leaves_no_room_for_a_wide_perfect_window(song):
    """A Casual score only a Perfect Time past 13 reaches: honest far below the song's top, where gems can buy that window."""
    casual = 153_285
    assert reverse_score(ShownPlay(score=4_666_274, casual_score=casual, accuracy=100.0), song).verdict == "exploited"
    assert reverse_score(ShownPlay(score=2_000_000, casual_score=casual, accuracy=100.0), song).verdict != "exploited"


def test_a_gear_multiplier_stands_in_for_the_casual_score(song):
    honest = _simulated(song, STORED, Plan(np.zeros(song.chart.total_notes)))
    multiplier = round(honest.score / honest.casual, 2)
    assert reverse_score(ShownPlay(score=honest.score, gear_multiplier=multiplier, accuracy=100.0), song).evidence == ()
    reply = reverse_score(ShownPlay(score=honest.score, gear_multiplier=multiplier * 1.3, accuracy=100.0), song)
    assert reply.verdict == "exploited" and reply.evidence


def test_a_copied_force_great_plan_is_found_on_the_board(song):
    """Precise FG #1 of the chart: 2 Greats in the head, from a results database."""
    surface = (4294443008, 4294967295, 4294967295, 15, 524289, 0, 0, 0, 112, 0, 0)
    stats = (85, 59, 71, 69, 63, 35, 135, 73, 34, 704)
    result = FgResult("Vibe", (0, 1, 11, 0, 23, 55), stats, surface, 0, 0)
    gear = ("The Games: Hidden Shine", "Legendary Vibe Ringleader's Necktie")
    row = Loadout(
        "precise", song.chart.name, "T5", "hash", gear, (("Shaii",), ("Electroman",), ("Doppelganger Roxie",)), "Vibe", "Rush", None,
        4_666_274, 4_666_978, None, result,
    )
    reply = reverse_score(ShownPlay(score=4_666_978, accuracy=99.87), song, board=[row])
    assert reply.verdict == "sets" and reply.sets[0].gems["Fever Fill Rate"] == 23


def test_accuracy_leaves_its_rounding_of_greats():
    judged = judged_play(ShownPlay(score=1, accuracy=99.5), 2000)
    assert judged.great_lo <= 40 <= judged.great_hi
    assert judged_play(ShownPlay(score=1, accuracy=100.0), 6000).great_hi == 1


def test_counts_come_whole():
    with pytest.raises(ValueError):
        judged_play(ShownPlay(score=1, perfect=10), 10)
