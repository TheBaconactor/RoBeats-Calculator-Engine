from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_entry_names


def test_build_loadout_entries_can_skip_db_query(monkeypatch):
    calls = {"n": 0}

    def _fake_get_best_loadouts(*args, **kwargs):
        calls["n"] += 1
        return []

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.loadout_builder.get_best_loadouts",
        _fake_get_best_loadouts,
    )

    ga_candidates = [
        {
            "Score": 777,
            "BaseScore": 888,
            "Gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
            "Minis": ["M1", "M2", "M3"],
            "Data": {"Stats": {"Perfect Points": 1}},
        }
    ]

    out = build_loadout_entries(
        found_song_name="db-query-gate-song",
        use_evo_db=True,
        ga_candidates=ga_candidates,
        db_loadouts_limit=51,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
        allow_db_query=False,
    )

    assert calls["n"] == 0
    assert len(out) == 1
    entry = next(iter(out.values()))
    assert int(entry["score"]) == 888


def test_build_loadout_entries_can_defer_ga_details():
    class _FakeRegistry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    ga_candidates = [
        {
            "Score": 777,
            "BaseScore": 888,
            "GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 8, 7],
            "_ga_registry": _FakeRegistry(),
            "Data": {
                "BaseStats": {"Perfect Points": 5, "Rush": 7},
                "GemCounts": {"Perfect Points": 1},
                "FT": 1,
                "FF": 2,
                "Selected Element": "Rush",
            },
        }
    ]

    out = build_loadout_entries(
        found_song_name="ga-details-deferred-song",
        use_evo_db=False,
        ga_candidates=ga_candidates,
        db_loadouts_limit=51,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
        materialize_ga_details=False,
    )

    assert len(out) == 1
    entry = next(iter(out.values()))
    assert entry["details"] == {}
    assert entry["selected_element"] == "Rush"
    assert entry["eval_data"]["BaseStats"]["Perfect Points"] == 5
    assert entry["ga_genome_ids"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert entry.get("gear") == []
    assert entry.get("minis") == []
    gear_names, mini_names = materialize_entry_names(entry, mutate=True)
    assert gear_names == ["I1", "I2", "I3", "I4", "I5", "I6"]
    assert mini_names == ["I7", "I8", "I9"]
