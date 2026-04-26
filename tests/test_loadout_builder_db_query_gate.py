from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.ga_entry_utils import entry_loadout_hash
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


def test_build_loadout_entries_preserves_db_effective_hash(monkeypatch):
    def _fake_get_best_loadouts(*args, **kwargs):
        return [
            {
                "loadout_hash": "effective-db-hash",
                "score": 123,
                "fg_score": 456,
                "gear": ["G1"],
                "minis": ["RepresentativeMini"],
                "details": {"Stats": {"Perfect Points": 1}},
                "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ]

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.loadout_builder.get_best_loadouts",
        _fake_get_best_loadouts,
    )

    out = build_loadout_entries(
        found_song_name="mini-equivalence-song",
        use_evo_db=True,
        ga_candidates=[],
        db_loadouts_limit=51,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
    )

    assert list(out) == ["effective-db-hash"]
    entry = out["effective-db-hash"]
    assert entry["loadout_hash"] == "effective-db-hash"
    assert entry_loadout_hash(entry) == "effective-db-hash"


def test_build_loadout_entries_preserves_ga_effective_hash():
    out = build_loadout_entries(
        found_song_name="mini-equivalence-song",
        use_evo_db=False,
        ga_candidates=[
            {
                "loadout_hash": "effective-ga-hash",
                "BaseScore": 789,
                "Gear": ["G1"],
                "Minis": ["RepresentativeMini"],
                "Data": {"Stats": {"Perfect Points": 7}},
            }
        ],
        db_loadouts_limit=51,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
        allow_db_query=False,
    )

    assert list(out) == ["effective-ga-hash"]
    entry = out["effective-ga-hash"]
    assert entry["loadout_hash"] == "effective-ga-hash"
    assert entry_loadout_hash(entry) == "effective-ga-hash"
