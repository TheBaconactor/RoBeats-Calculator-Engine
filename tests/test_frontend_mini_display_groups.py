from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display


def test_normalize_minis_groups_keeps_single_occurrence_group():
    groups = [["BlackY", "Heavy Metal Starlet"], ["Halloween Witch Teresa"]]
    assert normalize_minis_groups_for_display(groups) == [["BlackY", "Heavy Metal Starlet"], ["Halloween Witch Teresa"]]


def test_normalize_minis_groups_expands_repeated_multi_name_group_into_singletons():
    groups = [
        ["BlackY", "Heavy Metal Starlet"],
        ["BlackY", "Heavy Metal Starlet"],
        ["Halloween Witch Teresa"],
    ]
    assert normalize_minis_groups_for_display(groups) == [
        ["BlackY"],
        ["Heavy Metal Starlet"],
        ["Halloween Witch Teresa"],
    ]


def test_normalize_minis_groups_does_not_split_true_duo_name():
    # A single mini whose actual name contains a slash should remain a single slot.
    groups = [["BlackY / Heavy Metal Starlet"], ["Halloween Witch Teresa"]]
    assert normalize_minis_groups_for_display(groups) == [["BlackY / Heavy Metal Starlet"], ["Halloween Witch Teresa"]]
