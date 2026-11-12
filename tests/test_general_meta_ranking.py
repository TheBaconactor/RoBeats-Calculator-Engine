"""General Meta's ranking of a category's sets (general_meta.analysis.ranked_sets) from typed songs and rows."""

from general_meta.analysis import Row, Song, ranked_sets
from tests.items_support import make_gear, minis_from_dicts

_STATS = ("Chill", "Flow", "Rush", "Beat", "Vibe", "Perfect Points", "Combo Multiplier", "Fever Multiplier",
          "Fever Time", "Fever Fill Rate")


def _row(gear, score, *, fg_score=0, minis=("Mini",), gems=(0, 0, 0, 0, 0, 0), loadout_hash="h"):
    return Row(loadout_hash, score, fg_score, tuple(gear), tuple((name,) for name in minis), tuple(gems))


def _gears(*names):
    """Gear named "<Slot> <X>" in that slot."""
    return {name: make_gear(name, slot=name.split()[0]) for name in names}


def _vibe_minis(**extra):
    return {name: {"Name": name, **dict.fromkeys(_STATS, 0), "Vibe": 55, **fields} for name, fields in extra.items()}


def test_easy_songs_count_in_the_averages_but_not_in_the_ranking():
    rank_one = ["Pants A", "Hat A", "Neck A", "Face A", "Shirt A", "Back A"]  # stored out of slot order
    rank_two = ["Hat B", "Neck B", "Face B", "Shirt B", "Back B", "Pants B"]
    songs = [Song("Normal 1", "Normal", "Beat", "Beat"), Song("Normal 2", "Normal", "Beat", "Beat"),
             Song("Easy 1", "Easy", "Beat", "Beat"), Song("Easy 2", "Easy", "Beat", "Beat"),
             Song("Easy 3", "Easy", "Beat", "Beat")]
    rows = {
        "Normal 1": [_row(rank_one, 100, gems=(90, 0, 0, 0, 0, 0))],
        "Normal 2": [_row(rank_one, 100, gems=(90, 0, 0, 0, 0, 0))],
        "Easy 1": [_row(rank_two, 200, gems=(0, 90, 0, 0, 0, 0))],
        "Easy 2": [_row(rank_two, 200, gems=(0, 90, 0, 0, 0, 0))],
        "Easy 3": [_row(rank_one, 100, gems=(0, 90, 0, 0, 0, 0), minis=("Easy Mini",))],
    }
    minis = minis_from_dicts({"Mini": {"Name": "Mini"}, "Easy Mini": {"Name": "Easy Mini"}})

    results = ranked_sets(songs, rows, minis, _gears(*rank_one, *rank_two))

    # Only sets with ranked wins are listed; "Easy Mini" has the same effect as "Mini", so Easy 3 joins rank one.
    assert [(result.rank, result.gear) for result in results] == [
        (1, ("Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"))
    ]
    top = results[0]
    assert top.wins == 2
    assert top.peak_in_songs == ["Normal 1", "Normal 2"]
    assert [win["song_name"] for win in top.song_wins] == ["Normal 1", "Normal 2"]
    assert top.mini_groups == (("Mini",),)
    assert top.avg_gems["PP"] == 60 and top.avg_gems["CM"] == 30


def test_averaged_gems_sum_to_the_budget():
    # Independent per-kind rounding of FT 3.0, FF 3.5, Element 83.5 would give 91.
    songs = [Song("Song 1", "Hard", "Vibe", "Vibe"), Song("Song 2", "Hard", "Vibe", "Vibe")]
    rows = {"Song 1": [_row(["Gear1"], 100, gems=(0, 0, 0, 3, 3, 84))],
            "Song 2": [_row(["Gear1"], 100, gems=(0, 0, 0, 3, 4, 83))]}
    (result,) = ranked_sets(songs, rows, minis_from_dicts({"Mini": {"Name": "Mini"}}), {})
    assert sum(result.avg_gems.values()) == 90
    assert all(count >= 0 for count in result.avg_gems.values())


def test_one_songs_gems_are_its_average():
    songs = [Song("Song 1", "Hard", "Vibe", "Vibe")]
    rows = {"Song 1": [_row(["Gear1"], 100, gems=(1, 2, 3, 4, 5, 75))]}
    (result,) = ranked_sets(songs, rows, minis_from_dicts({"Mini": {"Name": "Mini"}}), {})
    assert result.avg_gems == {"PP": 1, "CM": 2, "FM": 3, "FT": 4, "FF": 5, "Element": 75}


def test_mini_variants_merge_when_the_difference_cannot_score_in_the_category():
    minis = minis_from_dicts(_vibe_minis(MiniA={}, MiniB={"Rush": 35}))
    songs = [Song("Song1", "Hard", "Vibe", "Vibe"), Song("Song2", "Hard", "Vibe", "Vibe")]
    rows = {"Song1": [_row(["Gear1"], 100, minis=("MiniA",))], "Song2": [_row(["Gear1"], 100, minis=("MiniB",))]}

    (result,) = ranked_sets(songs, rows, minis, {})

    assert result.wins == 2
    assert result.peak_in_songs == result.peak_in_songs_meta == ["Song1", "Song2"]
    assert result.peak_in_songs_fg == []
    assert result.mini_groups == (("MiniA",),)  # equally frequent variants: the first by name


def test_mini_variants_stay_apart_when_a_song_scores_the_difference():
    minis = minis_from_dicts(_vibe_minis(MiniA={}, MiniB={"Rush": 35}))
    songs = [Song("Song1", "Hard", "Vibe", "Vibe"), Song("Song2", "Hard", "Vibe", "Rush")]
    rows = {"Song1": [_row(["Gear1"], 100, minis=("MiniA",))], "Song2": [_row(["Gear1"], 100, minis=("MiniB",))]}

    results = ranked_sets(songs, rows, minis, {})

    assert [(r.wins, r.peak_in_songs, r.peak_in_songs_meta, r.mini_groups) for r in results] == [
        (1, ["Song1"], ["Song1"], (("MiniA",),)),
        (1, ["Song2"], ["Song2"], (("MiniB",),)),
    ]


def test_minis_with_different_ascension_targets_stay_apart():
    ascension = {"Mini Ascension Base Vibe": 11, "Mini Ascension Enabled": True, "Mini Ascension Level": 10}
    minis = minis_from_dicts(_vibe_minis(MiniA={**ascension, "Song Target": ["Song1"]},
                                         MiniB={**ascension, "Song Target": ["Song2"]}))
    songs = [Song("Song1", "Hard", "Vibe", "Vibe"), Song("Song2", "Hard", "Vibe", "Vibe")]
    rows = {"Song1": [_row(["Gear1"], 100, minis=("MiniA",))], "Song2": [_row(["Gear1"], 100, minis=("MiniB",))]}

    results = ranked_sets(songs, rows, minis, {})

    assert sorted((r.wins, r.mini_groups) for r in results) == [(1, (("MiniA",),)), (1, (("MiniB",),))]


def test_a_song_counts_for_the_set_with_its_best_score_force_greats_included():
    target = ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]
    target_minis = ("Mini 1", "Mini 2", "Mini 3")
    songs = [Song("Song A", "Hard", "Chill", "Vibe"), Song("Song B", "Hard", "Chill", "Vibe")]
    rows = {
        # Song A: another row has the higher base score, the target's FG score is higher still.
        "Song A": [_row(target, 100, fg_score=500, minis=target_minis, loadout_hash="target-song-a"),
                   _row(["Hat X"], 300, fg_score=300, minis=("Mini X",), loadout_hash="other-song-a")],
        "Song B": [_row(target, 400, fg_score=400, minis=target_minis, loadout_hash="target-song-b"),
                   _row(["Hat Y"], 350, fg_score=350, minis=("Mini Y",), loadout_hash="other-song-b")],
    }
    minis = minis_from_dicts({name: {"Name": name} for name in target_minis})

    top = ranked_sets(songs, rows, minis, _gears(*target, "Hat X", "Hat Y"))[0]

    assert top.gear == tuple(target)
    assert top.mini_groups == tuple((name,) for name in target_minis)
    assert top.wins == 2
    assert top.peak_in_songs == ["Song A", "Song B"]
    assert top.peak_in_songs_meta == ["Song B"]
    assert top.peak_in_songs_fg == ["Song A"]
    win = {"team_buff": "T5", "rank_index": 0, "rank": 1}
    assert top.song_wins == [
        {**win, "song_id": "Song A", "song_name": "Song A", "mode": "fg", "score": 500, "base_score": 100,
         "fg_score": 500, "loadout_hash": "target-song-a"},
        {**win, "song_id": "Song B", "song_name": "Song B", "mode": "meta", "score": 400, "base_score": 400,
         "fg_score": 400, "loadout_hash": "target-song-b"},
    ]
