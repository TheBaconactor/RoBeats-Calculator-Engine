from gear_optimizer.data import database


def test_compact_minis_handles_nested_variant_groups_and_corrupt_list_literals():
    minis = [
        ["Electroman"],
        ["Fusq", "Santa's Helper Marsha"],
        {"Name": "Trailblazing Trance Zara"},
        "['BlackY', 'Heavy Metal Starlet']",
    ]
    # Representative-per-slot behavior: take first item from each group / list literal.
    assert database._compact_minis_for_db(minis) == [
        "Electroman",
        "Fusq",
        "Trailblazing Trance Zara",
        "BlackY",
    ]

