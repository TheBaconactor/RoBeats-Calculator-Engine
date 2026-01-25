from gear_optimizer.helpers.song_helpers.persistence import build_db_payload, make_build_details_fn


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
