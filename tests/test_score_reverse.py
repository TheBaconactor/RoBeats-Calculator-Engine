"""The score reverse-lookup, through its public entry point, on an official chart and the game's catalog."""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import STATS, empty_stats, stat_curves
from gear_optimizer.reverse.fever_reach import event_times, fever_surfaces
from gear_optimizer.reverse.lookup import ShownPlay, judged_play, prepare_song, reverse_score
from gear_optimizer.score import factors, fg_surface_score
from gear_optimizer.settings import paths
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.store.records import FgResult, Loadout

CHART = "Aether (Easy) by Geoxor.txt"


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
    stored = dict(zip(STATS, (85, 59, 71, 66, 63, 35, 135, 73, 34, 707)))
    chart = song.chart

    def power(stats):
        five = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
        return 5 * sum(stats[key] for key in five) + 4 * stats[chart.primary] + 2 * stats[chart.secondary]

    reply = reverse_score(ShownPlay(score=4_666_274, gear_power=power(stored)), song)
    assert reply.sets and all(power(row.stats) == power(stored) for row in reply.sets)


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
