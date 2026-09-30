from gear_optimizer.helpers.song_helpers.loadout_hashing import compact_mini_names
from tests.items_support import make_song_mini


def test_compact_minis_handles_nested_variant_groups_and_corrupt_list_literals():
    minis = [
        ["Electroman"],
        ["Fusq", "Santa's Helper Marsha"],
        make_song_mini("Trailblazing Trance Zara"),
        "['BlackY', 'Heavy Metal Starlet']",
    ]
    # Representative-per-slot behavior: take first item from each group / list literal.
    assert compact_mini_names(minis) == [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara",
        "BlackY",
    ]
