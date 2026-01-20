def test_representative_mini_names_avoids_duplicate_slots_when_possible():
    from gear_optimizer.data.loadout_equivalence import representative_mini_names

    groups = [
        ["BlackY", "Heavy Metal Starlet"],
        ["BlackY", "Heavy Metal Starlet"],
        ["Halloween Witch Teresa"],
    ]

    reps = representative_mini_names(groups)

    assert len(reps) == 3
    assert set(reps[:2]) == {"BlackY", "Heavy Metal Starlet"}
    assert reps[2] == "Halloween Witch Teresa"
