import json
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
    monkeypatch.setattr(gm_app.EvolutionDbManager, "from_env", lambda: object())
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
    t1_gears = ["Hat T1", "Neck T1", "Face T1", "Shirt T1", "Back T1", "Pants T1"]

    def _tier_rows(song_name: str, gear_names: list[str], mini_name: str, score: int) -> list[dict]:
        return [
            {
                "song_name": song_name,
                "score": score,
                "fg_score": 0,
                "gear": list(gear_names),
                "mini_groups": [[mini_name]],
                "details_json": json.dumps({"GemCounts": {}}),
            }
        ]

    def _build_rows_for_song(song, **_kwargs):
        song_name = str(song.get("song_name") or "")
        return (
            {},
            {},
            {
                "None": [],
                "T1": _tier_rows(song_name, t1_gears, "Mini T1", 120),
                "T5": _tier_rows(song_name, baseline_gears, "Mini A", 100),
                "T10": [],
                "T20": [],
                "T50": [],
                "T51": [],
            },
        )

    monkeypatch.setattr(gm_app, "_build_replayed_loadout_rows_for_song", _build_rows_for_song)

    results = gm_app.run_general_meta(configparser.ConfigParser(), {})
    assert "Chill/All" not in results["results"]
    combo = results["results"]["Chill/Vibe"]

    assert combo["default_team_buff_tier"] == "T5"
    assert combo["team_buff_tiers"] == ["None", "T1", "T5", "T10", "T20", "T50", "T51"]
    assert combo["top_loadouts"][0]["gear"] == baseline_gears
    assert combo["top_loadouts"][0]["team_buff"] == "T5"
    assert combo["top_loadouts"][0]["stats_base"]["Perfect Points"] == 0
    assert combo["top_loadouts"][0]["stats_base"]["Chill"] == 0

    tiered = combo["loadouts_by_team_buff"]
    assert tiered["T1"][0]["gear"] == t1_gears
    assert tiered["T1"][0]["team_buff"] == "T1"
    assert tiered["T1"][0]["stats"]["Perfect Points"] == 25
    assert tiered["T1"][0]["stats"]["Chill"] == 35

    winners = combo["team_buff_winners"]
    assert set(winners.keys()) == {"None", "T1", "T5", "T10", "T20", "T50", "T51"}

    assert winners["T5"]["songs_count_with_data"] == 2
    assert winners["T5"]["winner"]["gear"] == baseline_gears
    assert winners["T5"]["winner"]["team_buff"] == "T5"
    assert winners["T5"]["winner"]["stats"]["Perfect Points"] == 25
    assert winners["T5"]["winner"]["stats"]["Chill"] == 30

    assert winners["T1"]["songs_count_with_data"] == 2
    assert winners["T1"]["winner"]["gear"] == t1_gears
    assert winners["T1"]["winner"]["team_buff"] == "T1"
    assert winners["T1"]["winner"]["stats"]["Perfect Points"] == 25
    assert winners["T1"]["winner"]["stats"]["Chill"] == 35

    assert winners["T20"]["songs_count_with_data"] == 0
    assert winners["T20"]["winner"] is None

    assert winners["T50"]["songs_count_with_data"] == 0
    assert winners["T50"]["winner"] is None

    assert winners["T51"]["songs_count_with_data"] == 0
    assert winners["T51"]["winner"] is None

    assert winners["None"]["songs_count_with_data"] == 0
    assert winners["None"]["winner"] is None
