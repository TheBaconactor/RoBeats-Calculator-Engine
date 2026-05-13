from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries


def test_build_loadout_entries_prefers_base_score_over_score():
    def build_details_fn(data_dict: dict) -> dict:
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

    ga_candidates = [
        {
            "Score": 900,
            "BaseScore": 1000,
            "Gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
            "Minis": ["M1", "M2", "M3"],
            "Data": {"FT": 1, "FF": 2, "Stats": {"Perfect Points": 10}, "Selected Element": "Rush"},
        }
    ]

    out = build_loadout_entries(
        found_song_name="Loadout Builder BaseScore Song",
        ga_candidates=ga_candidates,
        gears_by_name={},
        minis_by_name={},
        build_details_fn=build_details_fn,
    )

    assert len(out) == 1
    entry = next(iter(out.values()))
    assert int(entry["score"]) == 1000
    assert entry["gear"] == ["G1", "G2", "G3", "G4", "G5", "G6"]
    assert entry["minis"] == ["M1", "M2", "M3"]
