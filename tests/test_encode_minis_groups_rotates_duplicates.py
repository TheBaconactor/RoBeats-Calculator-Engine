import json


def test_encode_minis_groups_rotates_repeated_groups_for_unique_first_elements():
    from gear_optimizer.data.loadout_equivalence import encode_minis_groups

    groups = [
        ["BlackY", "Heavy Metal Starlet"],
        ["BlackY", "Heavy Metal Starlet"],
        ["Halloween Witch Teresa"],
    ]
    decoded = json.loads(encode_minis_groups(groups))
    assert decoded[0][0] != decoded[1][0]
    assert set(decoded[0]) == {"BlackY", "Heavy Metal Starlet"}
    assert set(decoded[1]) == {"BlackY", "Heavy Metal Starlet"}


def test_encode_minis_groups_rotates_overlapping_groups_to_avoid_duplicate_firsts_when_possible():
    from gear_optimizer.data.loadout_equivalence import encode_minis_groups

    groups = [
        ["A", "B"],
        ["A", "C"],
        ["D"],
    ]
    decoded = json.loads(encode_minis_groups(groups))
    assert decoded[0][0] == "A"
    assert decoded[1][0] != "A"
