from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from tests.songs_support import make_chart


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "tools" / "db" / "measure_lossless_exact_replay_gap.py"
SPEC = importlib.util.spec_from_file_location("measure_lossless_exact_replay_gap", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_normalize_gem_counts_merges_ft_and_ff():
    payload = {
        "GemCounts": {"Perfect Points": 10, "Combo Multiplier": 2},
        "FT": 3,
        "FF": 4,
    }

    assert MODULE._normalize_gem_counts(payload) == {
        "Perfect Points": 10,
        "Combo Multiplier": 2,
        "Fever Time": 3,
        "Fever Fill Rate": 4,
    }


def test_resolve_color_overrides_preserves_song_primary_for_team_buff_base():
    base_override, target_override, primary, secondary = MODULE._resolve_color_overrides(
        chart=make_chart([0.0], primary="Rush", secondary="Flow"),
        team_buff_color_override="Beat",
        primary_element_override="Flow",
        secondary_element_override="Rush",
    )

    assert base_override == "Rush"
    assert target_override == "Beat"
    assert primary == "Flow"
    assert secondary == "Rush"


def test_resolve_color_overrides_without_overrides_is_noop():
    assert MODULE._resolve_color_overrides(
        chart=make_chart([0.0], primary="Rush", secondary="Flow"),
        team_buff_color_override="",
        primary_element_override="",
        secondary_element_override="",
    ) == (None, None, "Rush", "Flow")


def test_team_buff_color_override_keeps_a_one_color_song_one_color():
    # Only an element override re-colors the song; the deduped palette's empty secondary must not
    # turn a one-color song into a two-color one (the website's on-demand replay rule).
    chart = make_chart([0.0, 0.5], primary="Rush", secondary="Rush")

    song, base_override, target_override = MODULE._prepare_active_song(
        chart,
        timing_mode="zero_ms",
        team_buff_color_override="Beat",
        primary_element_override="",
        secondary_element_override="",
    )

    assert (song.chart.primary, song.chart.secondary) == ("Rush", "Rush")
    assert (base_override, target_override) == ("Rush", "Beat")


def test_replay_payload_for_mode_selects_force_for_fg():
    row = {
        "details": {"GemCounts": {"Perfect Points": 1}},
        "force": {"GemCounts": {"Perfect Points": 2}},
    }

    assert MODULE._replay_payload_for_mode(row, "meta") == {"GemCounts": {"Perfect Points": 1}}
    assert MODULE._replay_payload_for_mode(row, "fg") == {"GemCounts": {"Perfect Points": 2}}
