from __future__ import annotations

import pytest

from general_meta.app import _assert_no_stats_only_duplicate_loadouts


def _base_loadout() -> dict:
    return {
        "loadout_key": "abc123",
        "team_buff": "T5",
        "gear": ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"],
        "mini_groups": [["Mini A"], ["Mini B"], ["Mini C"]],
        "gems": {"PP": 0, "CM": 0, "FM": 1, "FT": 2, "FF": 1, "Element": 86},
        "stats": {"Fever Fill Rate": 54, "Fever Time": 36},
        "stats_base": {"Fever Fill Rate": 54, "Fever Time": 36},
    }


def test_duplicate_identity_with_different_stats_raises() -> None:
    first = _base_loadout()
    second = _base_loadout()
    second["stats"] = {"Fever Fill Rate": 18, "Fever Time": 36}
    second["stats_base"] = {"Fever Fill Rate": 18, "Fever Time": 36}

    with pytest.raises(AssertionError, match="manual review required"):
        _assert_no_stats_only_duplicate_loadouts(
            [first, second],
            context="Chill/Chill tier=T5",
        )


def test_duplicate_identity_with_same_stats_is_allowed() -> None:
    first = _base_loadout()
    second = _base_loadout()

    _assert_no_stats_only_duplicate_loadouts(
        [first, second],
        context="Chill/Chill tier=T5",
    )
