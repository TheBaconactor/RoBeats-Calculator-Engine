from gear_optimizer.helpers.song_helpers.persistence import build_db_payload


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
        prev_attempts_first=0,
        fg_variants=[fg_variant],
        build_details_fn=build_details,
        db_best_fg_score=0,
    )

    assert payload["gear"] == ["Hat A", "Neck B"]
    assert payload["minis"] == ["Mini 1", "Mini 2", "Mini 3"]

