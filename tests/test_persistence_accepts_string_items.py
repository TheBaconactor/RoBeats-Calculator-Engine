from gear_optimizer.helpers.song_helpers.persistence import build_db_payload, build_persistence_entries, make_build_details_fn


def test_build_db_payload_accepts_string_items():
    best_data = {
        "Score": 123,
        "BaseScore": 123,
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": {},
        "Selected Element": "Rush",
        "ForceGreats": {"config": {}},
    }

    def build_details(data_dict: dict) -> dict:
        return {
            "FT": data_dict.get("FT", 0),
            "FF": data_dict.get("FF", 0),
            "GemCounts": data_dict.get("GemCounts", {}),
            "Stats": data_dict.get("Stats", {}),
            "SelectedElement": data_dict.get("Selected Element", ""),
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
            "Difficulty": "Hard",
            "ForceGreats": data_dict.get("ForceGreats", {}),
        }

    fg_variant = {
        "fg_score": 100,
        "gear": ["Hat A", "Neck B"],
        "minis": ["Mini 1", "Mini 2", "Mini 3"],
        "data": {
            "Score": 100,
            "FT": 0,
            "FF": 0,
            "GemCounts": {},
            "Stats": {},
            "Selected Element": "Rush",
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    payload = build_db_payload(
        best_data,
        best_gear=["Hat A", "Neck B"],
        best_minis=["Mini 1", "Mini 2", "Mini 3"],
        prev_record=None,
        attempt_lifetime=1,
        attempts_first=1,
        fg_variants=[fg_variant],
        build_details_fn=build_details,
        db_best_fg_score=0,
    )

    assert payload["gear"] == ["Hat A", "Neck B"]
    assert payload["minis"] == ["Mini 1", "Mini 2", "Mini 3"]


def test_build_db_payload_normalizes_force_payload_stats():
    build_details = make_build_details_fn("Vibe", "Chill", "Hard")

    best_data = {
        "Score": 100,
        "BaseScore": 100,
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": {},
        "Selected Element": "Vibe",
        "ForceGreats": {"config": {}},
    }

    base_stats = {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Fever Fill Rate": 40,
        "Fever Time": 50,
        "Chill": 0,
        "Vibe": 0,
        "Beat": 0,
        "Flow": 0,
        "Rush": 0,
    }

    fg_data = {
        "BaseStats": base_stats,
        "GemCounts": {
            "Perfect Points": 1,
            "Combo Multiplier": 1,
            "Fever Multiplier": 1,
            "Element": 2,
        },
        "FT": 1,
        "FF": 2,
        "Selected Element": "Vibe",
        "ForceGreats": {"config": {"NonFever1": 1}},
    }

    fg_variant = {
        "fg_score": 150,
        "score": 100,
        "base_score": 100,
        "gear": ["Hat A", "Neck B"],
        "minis": ["Mini 1", "Mini 2", "Mini 3"],
        "data": fg_data,
    }

    payload = build_db_payload(
        best_data,
        best_gear=["Hat A", "Neck B"],
        best_minis=["Mini 1", "Mini 2", "Mini 3"],
        prev_record=None,
        attempt_lifetime=1,
        attempts_first=1,
        fg_variants=[fg_variant],
        build_details_fn=build_details,
        db_best_fg_score=0,
    )

    force = payload.get("force") or {}
    stats = force.get("Stats")
    assert isinstance(stats, dict)
    assert stats.get("Perfect Points", 0) >= base_stats["Perfect Points"]
    assert force.get("SelectedElement") == "Vibe"
    assert force.get("Selected Element") == "Vibe"


def test_normalize_force_payload_materializes_stats_from_base_stats():
    from gear_optimizer.helpers.song_helpers.persistence import _normalize_force_payload

    base_stats = {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Fever Fill Rate": 40,
        "Fever Time": 50,
        "Chill": 0,
        "Vibe": 0,
        "Beat": 0,
        "Flow": 0,
        "Rush": 0,
    }
    force_in = {
        "BaseStats": base_stats,
        "GemCounts": {
            "Perfect Points": 1,
            "Combo Multiplier": 1,
            "Fever Multiplier": 1,
            "Element": 2,
        },
        "FT": 1,
        "FF": 2,
        "Selected Element": "Vibe",
        "ForceGreats": {"config": {"NonFever1": 1}},
    }

    force_out = _normalize_force_payload(force_in)
    stats = force_out.get("Stats")
    assert isinstance(stats, dict)
    assert stats.get("Perfect Points", 0) >= base_stats["Perfect Points"]
    assert stats.get("Vibe", 0) >= base_stats["Vibe"]


def test_make_build_details_fn_materializes_stats_from_base_stats():
    build_details = make_build_details_fn("Rush", "Flow", "Hard")
    details = build_details(
        {
            "BaseStats": {
                "Perfect Points": 10,
                "Combo Multiplier": 20,
                "Fever Multiplier": 30,
                "Fever Time": 5,
                "Fever Fill Rate": 6,
                "Rush": 7,
                "Flow": 8,
            },
            "GemCounts": {
                "Perfect Points": 1,
                "Combo Multiplier": 1,
                "Fever Multiplier": 1,
                "Element": 1,
            },
            "FT": 1,
            "FF": 2,
            "Selected Element": "Rush",
        }
    )

    stats = details.get("Stats") or {}
    assert stats["Perfect Points"] > 10
    assert stats["Fever Time"] > 5
    assert stats["Rush"] > 7


def test_build_persistence_entries_materializes_lazy_ga_entry_names():
    from gear_optimizer.helpers.song_helpers.persistence_canon import assemble_without_replay

    class _FakeRegistry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    build_details = make_build_details_fn("Rush", "Flow", "Hard")
    persist_entries = assemble_without_replay(
        db_payload={
            "score": 999,
            "gear": ["Top Hat"],
            "minis": ["Mini A", "Mini B", "Mini C"],
            "details": {"Stats": {}, "ForceGreats": {}},
            "fg_score": 0,
        },
        ga_candidates=[],
        loadout_entries={
            "ga:1,2,3,4,5,6,7,8,9": {
                "score": 999,
                "base_score": 999,
                "fg_score": 0,
                "gear": [],
                "minis": [],
                "details": {"Stats": {}, "ForceGreats": {}},
                "force": None,
                "eval_data": {"Selected Element": "Rush"},
                "_source": "ga",
                "ga_genome_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "_ga_registry": _FakeRegistry(),
            }
        },
        build_details_fn=build_details,
    )

    lazy_row = next((row for row in persist_entries if row.get("gear") == ["I1", "I2", "I3", "I4", "I5", "I6"]), None)
    assert lazy_row is not None
    assert lazy_row.get("minis") == ["I7", "I8", "I9"]
