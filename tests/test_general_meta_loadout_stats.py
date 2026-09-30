from __future__ import annotations

import pytest

from general_meta.loadout_stats import build_general_meta_loadout_stats
from tests.items_support import make_mini, make_song_mini


def test_general_meta_loadout_stats_apply_unconditional_ascension_once_per_mini() -> None:
    minis = {name: make_mini(name) for name in ("Mini A", "Mini B", "Mini C")}

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
    assert all(mini.stats["Perfect Points"] == 0 for mini in minis.values())


def test_general_meta_loadout_stats_reject_already_ascended_minis() -> None:
    with pytest.raises(TypeError, match="base minis"):
        build_general_meta_loadout_stats(
            gear_names=[],
            mini_names=["Mini A"],
            gem_counts={},
            selected_element="Chill",
            gears_by_name={},
            minis_by_name={"Mini A": make_song_mini("Mini A", **{"Perfect Points": 20})},
            team_buff_stats={},
        )
