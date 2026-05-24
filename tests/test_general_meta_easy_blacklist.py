import json

from general_meta.analysis import find_most_common_loadout


def _row(song_name, gear, score, *, gems, mini="Mini", difficulty=None):
    return {
        "song_name": song_name,
        "score": score,
        "fg_score": 0,
        "gear": list(gear),
        "mini_groups": [[mini]],
        "details_json": json.dumps(
            {
                "GemCounts": {
                    "PP": int(gems.get("PP", 0)),
                    "CM": int(gems.get("CM", 0)),
                    "FM": int(gems.get("FM", 0)),
                    "Element": int(gems.get("Element", 0)),
                },
                "FT": int(gems.get("FT", 0)),
                "FF": int(gems.get("FF", 0)),
            }
        ),
        **({"difficulty": difficulty} if difficulty else {}),
    }


def test_general_meta_ranks_by_non_easy_peaks_but_keeps_easy_gems_in_average():
    rank_one_gears = ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]
    rank_two_gears = ["Hat B", "Neck B", "Face B", "Shirt B", "Back B", "Pants B"]

    songs = [
        {"song_name": "Normal 1", "primary": "Beat", "secondary": "Beat", "difficulty": "Normal"},
        {"song_name": "Normal 2", "primary": "Beat", "secondary": "Beat", "difficulty": "Normal"},
        {"song_name": "Easy 1", "primary": "Beat", "secondary": "Beat", "difficulty": "Easy"},
        {"song_name": "Easy 2", "primary": "Beat", "secondary": "Beat", "difficulty": "Easy"},
        {"song_name": "Easy 3", "primary": "Beat", "secondary": "Beat", "difficulty": "Easy"},
    ]
    loadouts_by_song = {
        "Normal 1": [_row("Normal 1", rank_one_gears, 100, gems={"PP": 90})],
        "Normal 2": [_row("Normal 2", rank_one_gears, 100, gems={"PP": 90})],
        "Easy 1": [_row("Easy 1", rank_two_gears, 200, gems={"CM": 90})],
        "Easy 2": [_row("Easy 2", rank_two_gears, 200, gems={"CM": 90})],
        "Easy 3": [_row("Easy 3", rank_one_gears, 100, gems={"CM": 90}, mini="Easy Mini")],
    }

    results = find_most_common_loadout(
        songs,
        [],
        {"Mini": {"Name": "Mini"}, "Easy Mini": {"Name": "Easy Mini"}},
        top_n=None,
        loadouts_by_song=loadouts_by_song,
    )

    assert [result["gear_names"] for result in results] == [sorted(rank_one_gears)]
    assert results[0]["rank"] == 1
    assert results[0]["win_frequency"] == 2
    assert results[0]["songs_with_set"] == 2
    assert results[0]["peak_in_songs"] == ["Normal 1", "Normal 2"]
    assert [win["song_name"] for win in results[0]["song_wins"]] == ["Normal 1", "Normal 2"]
    assert results[0]["mini_groups"] == [["Mini"]]
    assert results[0]["avg_gems"]["PP"] == 60
    assert results[0]["avg_gems"]["CM"] == 30
