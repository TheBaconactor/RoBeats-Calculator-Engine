from gear_optimizer.persistence.entries import (
    filter_valid_persistence_entries,
    force_score_hint,
)


def test_filter_valid_persistence_entries_requires_loadout_and_base_score_by_default():
    entries = [
        {"score": 100, "fg_score": 0, "gear": ["G"], "minis": []},
        {"score": 0, "fg_score": 200, "gear": ["G"], "minis": []},
        {"score": 300, "fg_score": 0, "gear": [], "minis": []},
        "not-entry",
    ]

    assert filter_valid_persistence_entries(entries) == [entries[0]]


def test_filter_valid_persistence_entries_can_accept_fg_or_force_score_hint():
    fg_entry = {"score": 0, "fg_score": 200, "gear": ["G"], "minis": []}
    force_entry = {
        "score": 0,
        "fg_score": 0,
        "gear": [],
        "minis": ["M"],
        "force": {"details": {"ForceGreats": {"final_score": 345}}},
    }

    assert force_score_hint(force_entry) == 345
    assert filter_valid_persistence_entries(
        [fg_entry, force_entry],
        require_base_score=False,
        accept_force_score_hint=True,
    ) == [fg_entry, force_entry]
