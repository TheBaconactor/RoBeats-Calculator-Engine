from __future__ import annotations

import pytest

from gear_optimizer.data.mini_ascension import materialize_mini_for_song
from general_meta.loadout_stats import build_general_meta_loadout_stats


def _ascended_mini(name: str) -> dict:
    return {
        "Name": name,
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 0,
        "Beat": 0,
        "Vibe": 0,
        "Song Target": [],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }


def test_general_meta_loadout_stats_apply_unconditional_ascension_once_per_mini() -> None:
    minis = {name: _ascended_mini(name) for name in ("Mini A", "Mini B", "Mini C")}

    stats_base, stats = build_general_meta_loadout_stats(
        gear_names=[],
        mini_names=["Mini A", "Mini B", "Mini C"],
        gem_counts={},
        selected_element="Chill",
        gears_by_name={},
        minis_by_name=minis,
        team_buff_stats={"Perfect Points": 25, "Chill": 35},
    )

    assert stats_base["Perfect Points"] == 60
    assert stats["Perfect Points"] == 85
    assert stats_base.get("Chill", 0) == 0
    assert stats["Chill"] == 35
    assert all(mini["Perfect Points"] == 0 for mini in minis.values())


def test_general_meta_loadout_stats_reject_already_materialized_minis() -> None:
    materialized = materialize_mini_for_song(
        _ascended_mini("Mini A"),
        song_name="Song A",
        primary_color="Chill",
        secondary_color="",
    )

    with pytest.raises(ValueError, match="unmaterialized mini row"):
        build_general_meta_loadout_stats(
            gear_names=[],
            mini_names=["Mini A"],
            gem_counts={},
            selected_element="Chill",
            gears_by_name={},
            minis_by_name={"Mini A": materialized},
            team_buff_stats={},
        )
