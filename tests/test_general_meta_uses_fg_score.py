from general_meta.analysis import find_most_common_loadout


def test_general_meta_counts_top1_by_effective_fg_score():
    songs = [
        {"song_name": "Song A", "primary": "Chill", "secondary": "Vibe"},
        {"song_name": "Song B", "primary": "Chill", "secondary": "Vibe"},
    ]

    target_gears = ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]
    target_minis = ["Mini 1", "Mini 2", "Mini 3"]

    # Per-song best differs by base score, but the target wins when considering fg_score.
    all_loadouts = [
        {
            "song_name": "Song A",
            "score": 100,
            "fg_score": 500,
            "gear": list(target_gears),
            "mini_groups": [[m] for m in target_minis],
            "details_json": None,
        },
        {
            "song_name": "Song A",
            "score": 300,
            "fg_score": 300,
            "gear": ["Hat X"],
            "mini_groups": [["Mini X"]],
            "details_json": None,
        },
        {
            "song_name": "Song B",
            "score": 400,
            "fg_score": 400,
            "gear": list(target_gears),
            "mini_groups": [[m] for m in target_minis],
            "details_json": None,
        },
        {
            "song_name": "Song B",
            "score": 350,
            "fg_score": 350,
            "gear": ["Hat Y"],
            "mini_groups": [["Mini Y"]],
            "details_json": None,
        },
    ]

    minis_by_name = {name: {"Name": name} for name in target_minis}

    results = find_most_common_loadout(songs, all_loadouts, minis_by_name, top_n=None)

    assert results
    top = results[0]
    assert top["gear_names"] == sorted(target_gears)
    assert sorted([min(g) for g in (top["mini_groups"] or []) if g]) == sorted(target_minis)
    assert top["win_frequency"] == 2
    assert top["songs_with_set"] == 2
    assert top["peak_in_songs"] == ["Song A", "Song B"]
