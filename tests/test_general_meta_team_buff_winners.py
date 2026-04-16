import configparser

import general_meta.app as gm_app


def test_run_general_meta_emits_team_buff_winners(monkeypatch):
    # Avoid filesystem/Data dependencies by stubbing song scan + DB readers + gear/minis loaders.
    monkeypatch.setattr(
        gm_app,
        "get_songs_by_elemental_combo",
        lambda _paths: {
            ("Chill", "Vibe"): [
                {"song_name": "Song A", "primary": "Chill", "secondary": "Vibe"},
                {"song_name": "Song B", "primary": "Chill", "secondary": "Vibe"},
            ]
        },
    )
    monkeypatch.setattr(gm_app, "read_table", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        gm_app,
        "load_all_gears_list",
        lambda _paths: [
            {"Name": "Hat A", "Slot": "Hat"},
            {"Name": "Neck A", "Slot": "Neck"},
            {"Name": "Face A", "Slot": "Face"},
            {"Name": "Shirt A", "Slot": "Shirt"},
            {"Name": "Back A", "Slot": "Back"},
            {"Name": "Pants A", "Slot": "Pants"},
            {"Name": "Hat T1", "Slot": "Hat"},
            {"Name": "Neck T1", "Slot": "Neck"},
            {"Name": "Face T1", "Slot": "Face"},
            {"Name": "Shirt T1", "Slot": "Shirt"},
            {"Name": "Back T1", "Slot": "Back"},
            {"Name": "Pants T1", "Slot": "Pants"},
        ],
    )
    monkeypatch.setattr(gm_app, "load_all_minis_list", lambda _paths: [{"Name": "Mini A"}, {"Name": "Mini T1"}])

    baseline_gears = ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]

    monkeypatch.setattr(
        gm_app,
        "get_all_loadouts_from_db",
        lambda **_kwargs: [
            {
                "song_name": "Song A",
                "score": 100,
                "fg_score": 0,
                "gear": list(baseline_gears),
                "mini_groups": [["Mini A"]],
                "details_json": None,
            },
            {
                "song_name": "Song B",
                "score": 100,
                "fg_score": 0,
                "gear": list(baseline_gears),
                "mini_groups": [["Mini A"]],
                "details_json": None,
            },
        ],
    )

    results = gm_app.run_general_meta(configparser.ConfigParser(), {})
    assert "Chill/All" not in results["results"]
    combo = results["results"]["Chill/Vibe"]

    assert combo["team_buff_tiers"] == ["None", "T1", "T5", "T10", "T20", "T50", "T51"]
    winners = combo["team_buff_winners"]
    assert set(winners.keys()) == {"None", "T1", "T5", "T10", "T20", "T50", "T51"}

    assert winners["T5"]["songs_count_with_data"] == 2
    assert winners["T5"]["winner"]["gear"] == baseline_gears
    assert winners["T5"]["winner"]["team_buff"] == "T5"
    assert winners["T5"]["winner"]["stats"]["Perfect Points"] == 25
    assert winners["T5"]["winner"]["stats"]["Chill"] == 30

    assert winners["T1"]["songs_count_with_data"] == 0
    assert winners["T1"]["winner"] is None

    assert winners["T20"]["songs_count_with_data"] == 0
    assert winners["T20"]["winner"] is None

    assert winners["T50"]["songs_count_with_data"] == 0
    assert winners["T50"]["winner"] is None

    assert winners["T51"]["songs_count_with_data"] == 0
    assert winners["T51"]["winner"] is None

    assert winners["None"]["songs_count_with_data"] == 0
    assert winners["None"]["winner"] is None
