"""The score reverse-lookup, through its public entry point, on an official chart and the game's catalog."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.frontier.types import FgResponseSurface
from gear_optimizer.gamedata import empty_stats, stat_curves, song_minis
from gear_optimizer.reverse.fever_reach import event_times, fever_surfaces
from gear_optimizer.reverse.lookup import ShownPlay, judged_play, prepare_song, reverse_score
from gear_optimizer.score import factors, fg_surface_score
from gear_optimizer.settings import paths
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.solver.timing_envelope import fever_axes
from gear_optimizer.stats import GEM_KINDS, apply_gems, total
from gear_optimizer.core.team_buff import team_buff_effect

CHART = "Aether (Easy) by Geoxor.txt"


@pytest.fixture(scope="module")
def song():
    chart = load_chart(paths().chart_dir("Easy") / CHART)
    return prepare_song(chart, load_catalog(paths().game_export), stat_curves())


def _build(song):
    """A released build: the first three minis of the song, the catalog's first gear per slot, its gems on the primary."""
    chart = song.chart
    gears = {}
    for gear in song.gears.values():
        gears.setdefault(gear.slot, gear)
    minis = list(song.minis.values())[:3]
    parts = [team_buff_effect("T5", chart.primary), *(gear.stats for gear in gears.values()), *(mini.stats for mini in minis)]
    gems = dict(zip(GEM_KINDS, (0, 10, 10, 5, 5, 60)))
    return apply_gems(total(*parts), gems, chart.primary), [gear.name for gear in gears.values()], [mini.name for mini in minis]


def _chart_time_score(song, stats):
    """The all-Perfect score at chart time, from the engine's own timeline and scorer."""
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    head, body_fever, _normal, _activations, _end = calculate_fever_timeline_indices(
        chart.timestamps, chart.total_notes, int(np.ceil(thresholds[stats["Fever Fill Rate"]])),
        float(durations[stats["Fever Time"]]), np.zeros(chart.total_notes, np.bool_),
    )
    words = [0, 0, 0, 0]
    for note in np.flatnonzero(head).tolist():
        words[note // 32] |= 1 << (note % 32)
    surface = FgResponseSurface(*words, 0, 0, 0, 0, int(body_fever), 0, 0)
    return fg_surface_score(factors(stats, song.curves, chart.primary, chart.secondary), surface, chart.total_notes)


def test_chart_time_timelines_are_among_the_reachable(song):
    surfaces = song.surfaces
    assert surfaces.body_fever.shape[0] > 0
    wider = fever_surfaces(song.chart, song.curves, event_times(song.chart, 13))
    assert wider.body_fever.shape[0] >= surfaces.body_fever.shape[0]


def test_a_released_build_is_found_from_its_score(song):
    stats, gear, minis = _build(song)
    score = _chart_time_score(song, stats)
    reply = reverse_score(ShownPlay(score=score), song, limit=64)
    assert reply.verdict == "sets"
    assert any(
        all(row.stats[stat] == stats[stat] for stat in ("Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"))
        for row in reply.sets
    )
    for row in reply.sets:
        surface = row.surface
        assert fg_surface_score(factors(row.stats, song.curves, song.chart.primary, song.chart.secondary), surface, song.chart.total_notes) == score


def test_gear_power_narrows_the_answer(song):
    stats, _gear, _minis = _build(song)
    chart = song.chart
    power = 5 * sum(stats[key] for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"))
    power += 4 * stats[chart.primary] + 2 * stats[chart.secondary]
    reply = reverse_score(ShownPlay(score=_chart_time_score(song, stats), gear_power=power), song, limit=64)
    assert reply.sets and all(row.stats["Combo Multiplier"] + row.stats["Fever Multiplier"] >= 0 for row in reply.sets)


def test_a_score_past_every_released_set_is_not_given_a_set(song):
    reply = reverse_score(ShownPlay(score=10**9), song)
    assert reply.verdict in ("unreleased", "exploited")
    assert reply.ceiling is not None and reply.ceiling < 10**9


def test_a_casual_score_no_clean_play_reaches_is_exploited(song):
    stats, _gear, _minis = _build(song)
    casual = fg_surface_score(
        factors(empty_stats(), song.curves, song.chart.primary, song.chart.secondary),
        FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), song.chart.total_notes,
    )
    reply = reverse_score(ShownPlay(score=_chart_time_score(song, stats), casual_score=casual, accuracy=100.0), song)
    assert reply.verdict == "exploited" and reply.evidence


def test_a_casual_match_is_never_called_exploited_on_its_casual_score(song):
    stats, _gear, _minis = _build(song)
    reply = reverse_score(ShownPlay(score=_chart_time_score(song, stats), casual_score=1, match_mode="Casual"), song)
    assert reply.verdict != "exploited"


def test_accuracy_leaves_its_rounding_of_greats():
    judged = judged_play(ShownPlay(score=1, accuracy=99.5), 2000)
    assert judged.great_lo <= 40 <= judged.great_hi
    assert judged_play(ShownPlay(score=1, accuracy=100.0), 6000).great_hi == 1


def test_counts_come_whole():
    with pytest.raises(ValueError):
        judged_play(ShownPlay(score=1, perfect=10), 10)
