import json

from general_meta.analysis import find_most_common_loadout


def test_general_meta_merges_mini_variants_when_irrelevant_to_category():
    minis_by_name = {
        "MiniA": {
            "Name": "MiniA",
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
        "MiniB": {
            "Name": "MiniB",
            "Chill": 0,
            "Flow": 0,
            "Rush": 35,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
    }

    songs = [
        {"song_name": "Song1", "primary": "Vibe", "secondary": "Vibe"},
        {"song_name": "Song2", "primary": "Vibe", "secondary": "Vibe"},
    ]
    all_loadouts = [
        {
            "song_name": "Song1",
            "score": 100,
            "gear_json": json.dumps(["Gear1"]),
            "minis_json": json.dumps(["MiniA"]),
            "details_json": None,
        },
        {
            "song_name": "Song2",
            "score": 100,
            "gear_json": json.dumps(["Gear1"]),
            "minis_json": json.dumps(["MiniB"]),
            "details_json": None,
        },
    ]

    results = find_most_common_loadout(songs, all_loadouts, minis_by_name, top_n=1)
    assert len(results) == 1
    result = results[0]

    assert result["win_frequency"] == 2
    assert result["songs_with_set"] == 2
    assert result["peak_in_songs"] == ["Song1", "Song2"]
    assert result["minis_json"] in ([["MiniA"]], [["MiniB"]])


def test_general_meta_does_not_merge_mini_variants_when_secondary_varies():
    minis_by_name = {
        "MiniA": {
            "Name": "MiniA",
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
        "MiniB": {
            "Name": "MiniB",
            "Chill": 0,
            "Flow": 0,
            "Rush": 35,
            "Beat": 0,
            "Vibe": 55,
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": 0,
        },
    }

    songs = [
        {"song_name": "Song1", "primary": "Vibe", "secondary": "Vibe"},
        {"song_name": "Song2", "primary": "Vibe", "secondary": "Rush"},
    ]
    all_loadouts = [
        {
            "song_name": "Song1",
            "score": 100,
            "gear_json": json.dumps(["Gear1"]),
            "minis_json": json.dumps(["MiniA"]),
            "details_json": None,
        },
        {
            "song_name": "Song2",
            "score": 100,
            "gear_json": json.dumps(["Gear1"]),
            "minis_json": json.dumps(["MiniB"]),
            "details_json": None,
        },
    ]

    results = find_most_common_loadout(songs, all_loadouts, minis_by_name, top_n=None)
    assert len(results) == 2
    assert [r["win_frequency"] for r in results] == [1, 1]
    assert sorted([r["peak_in_songs"] for r in results]) == [["Song1"], ["Song2"]]
    assert sorted([r["minis_json"] for r in results]) == [[["MiniA"]], [["MiniB"]]]
