from gear_optimizer.helpers.song_helpers.database_context import build_db_key


def test_build_db_key_without_human_hit_sim_is_identity():
    assert build_db_key("Skystrike (Hard) by Hinkik", None) == "Skystrike (Hard) by Hinkik"
    assert (
        build_db_key("Skystrike (Hard) by Hinkik", {"metadata": {"HumanHitSimApplied": False}})
        == "Skystrike (Hard) by Hinkik"
    )


def test_build_db_key_includes_human_hit_sim_context():
    base = "Skystrike (Hard) by Hinkik"
    calc_song = {
        "metadata": {
            "HumanHitSimApplied": True,
            "HumanHitSimSeed": 12345,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        }
    }
    key = build_db_key(base, calc_song)
    assert key != base
    assert base in key
    assert "seed=12345" in key
    assert "apply=ALL" in key


def test_build_db_key_changes_with_seed_and_mode():
    base = "Skystrike (Hard) by Hinkik"
    a = {
        "metadata": {
            "HumanHitSimApplied": True,
            "HumanHitSimSeed": 1,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        }
    }
    b = {
        "metadata": {
            "HumanHitSimApplied": True,
            "HumanHitSimSeed": 2,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        }
    }
    c = {
        "metadata": {
            "HumanHitSimApplied": True,
            "HumanHitSimSeed": 1,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        }
    }
    assert build_db_key(base, a) != build_db_key(base, b)
    assert build_db_key(base, a) != build_db_key(base, c)

