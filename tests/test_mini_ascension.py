import pytest

from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_CACHE_VERSION,
    materialize_mini_for_song,
    materialize_minis_for_song,
    mini_ascension_match_quality,
)
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools


TARGET_SONG = "Ascension Target by Artist"


@pytest.mark.parametrize(
    ("pet_color", "is_pet_primary", "expected"),
    [
        ("Rush", True, 1.0),
        ("Rush", False, 0.75),
        ("Flow", True, 0.75),
        ("Flow", False, 1.0),
        ("Chill", True, 0.5),
    ],
)
def test_mini_ascension_match_quality_tiers(pet_color, is_pet_primary, expected):
    assert (
        mini_ascension_match_quality(
            pet_color,
            is_pet_primary=is_pet_primary,
            song_primary_color="Rush",
            song_secondary_color="Flow",
        )
        == expected
    )


def test_materialize_mini_applies_base_pp_and_targeted_primary_secondary_bonus():
    mini = {
        "Name": "Target Mini",
        "type": "Mini",
        "Rush": 50,
        "Flow": 40,
        "Perfect Points": 3,
        "Song Target": [TARGET_SONG],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }

    materialized = materialize_mini_for_song(
        mini,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert materialized["Perfect Points"] == 23
    assert materialized["Rush"] == 350
    assert materialized["Flow"] == 190
    assert materialized["Mini Ascension Source Version"] == MINI_ASCENSION_CACHE_VERSION
    assert materialized["Mini Ascension Song Target Applied"] is True


def test_provisional_export_distribution_nonmatch_budget_adds_to_song_elements():
    mini = {
        "Name": "Nonmatch Mini",
        "type": "Mini",
        "Beat": 50,
        "Vibe": 40,
        "Perfect Points": 0,
        "Song Target": [TARGET_SONG],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }

    materialized = materialize_mini_for_song(
        mini,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    # Issue #127: both Mini colors no-match the song (Beat/Vibe vs Rush/Flow) -> quality 0.5 each.
    # weighted budget = floor(50*5*0.5) + floor(40*5*0.5) = 125 + 100 = 225; 2/3+1/3 -> 150 / 75.
    assert materialized["Rush"] == 150
    assert materialized["Flow"] == 75
    assert materialized["Beat"] == 50
    assert materialized["Vibe"] == 40


def test_provisional_export_distribution_cross_primary_to_song_secondary_uses_element_budget():
    mini = {
        "Name": "Cross Mini",
        "type": "Mini",
        "Flow": 40,
        "Perfect Points": 0,
        "Song Target": [TARGET_SONG],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }

    materialized = materialize_mini_for_song(
        mini,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    # Issue #127: Flow is the Mini's primary and cross-matches the song secondary -> quality 0.75.
    # weighted budget = floor(40*5*0.75) = 150; 2/3+1/3 -> Rush 100, Flow 50 (+40 base = 90).
    assert materialized["Rush"] == 100
    assert materialized["Flow"] == 90


def test_materialize_mini_non_target_gets_base_pp_only():
    mini = {
        "Name": "Base Only Mini",
        "type": "Mini",
        "Rush": 50,
        "Perfect Points": 1,
        "Song Target": ["Other Song by Artist"],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }

    materialized = materialize_mini_for_song(
        mini,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert materialized["Perfect Points"] == 21
    assert materialized["Rush"] == 50
    assert materialized["Mini Ascension Song Target Applied"] is False


def test_old_mini_data_without_ascension_enabled_is_unchanged():
    mini = {
        "Name": "Old Mini",
        "type": "Mini",
        "Rush": 50,
        "Perfect Points": 1,
        "Song Target": [TARGET_SONG],
    }

    materialized = materialize_mini_for_song(
        mini,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert materialized == mini


def test_materialize_minis_is_idempotent_for_same_song_and_loud_for_different_song():
    mini = {
        "Name": "Target Mini",
        "type": "Mini",
        "Rush": 50,
        "Perfect Points": 0,
        "Song Target": [TARGET_SONG],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }

    materialized, by_name, context = materialize_minis_for_song(
        [mini],
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Rush",
    )
    rematerialized, _by_name, _context = materialize_minis_for_song(
        materialized,
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Rush",
    )

    assert by_name["Target Mini"]["Perfect Points"] == 20
    assert by_name["Target Mini"]["Rush"] == 300
    assert context.applied_mini_names == ("Target Mini",)
    assert rematerialized[0]["Perfect Points"] == 20

    with pytest.raises(ValueError, match="different song context"):
        materialize_minis_for_song(
            materialized,
            song_name="Other Song by Artist",
            primary_color="Rush",
            secondary_color="Rush",
        )


def test_targeted_nonmatching_mini_survives_initial_pool_filter():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gears = [{"Name": slot, "type": slot, "Rush": 1} for slot in slots]
    minis, _by_name, _context = materialize_minis_for_song(
        [
            {
                "Name": "Targeted Chill Mini",
                "type": "Mini",
                "Chill": 50,
                "Perfect Points": 0,
                "Song Target": [TARGET_SONG],
                "Mini Ascension Enabled": True,
                "Mini Ascension Level": 10,
            },
            {
                "Name": "Untargeted Chill Mini",
                "type": "Mini",
                "Chill": 50,
                "Perfect Points": 0,
                "Song Target": ["Other Song by Artist"],
                "Mini Ascension Enabled": True,
                "Mini Ascension Level": 10,
            },
        ],
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    pools = initialize_pools(gears, minis, "Rush", slots, s_color="Flow")

    assert pools is not None
    _gear_pool, mini_pool, _before, _after, _whitelist = pools
    assert [mini["Name"] for mini in mini_pool] == ["Targeted Chill Mini"]


def test_fixed_mini_constraints_resolve_materialized_song_aware_minis():
    from gear_optimizer.solver.solver_common import _apply_fixed_pool_constraints

    raw_mini = {
        "Name": "Fixed Target Mini",
        "type": "Mini",
        "Rush": 50,
        "Perfect Points": 1,
        "Song Target": [TARGET_SONG],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }
    materialized_minis, _by_name, _context = materialize_minis_for_song(
        [raw_mini],
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    _gear_pool, fixed_pool = _apply_fixed_pool_constraints(
        {},
        materialized_minis,
        optimize_gear=True,
        optimize_minis=False,
        fixed_gear=None,
        fixed_minis=[raw_mini],
        materialized_mini_catalog=materialized_minis,
    )

    assert fixed_pool == materialized_minis
    assert fixed_pool[0]["Perfect Points"] == 21
    assert fixed_pool[0]["Rush"] == 216
    assert fixed_pool[0]["Flow"] == 83
    assert fixed_pool[0]["Mini Ascension Materialized"] is True


def test_real_export_8_bit_alien_flagged_song_gets_base_pp_and_elemental_bonus():
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "8-Bit Alien")

    materialized = materialize_mini_for_song(
        mini,
        song_name="Farewell, My Friend by Chroma",
        primary_color="Chill",
        secondary_color="Beat",
    )

    assert materialized["Perfect Points"] == 20
    assert materialized["Mini Ascension Song Target Applied"] is True
    # Issue #127: 8-Bit Alien L1 = Rush 12 / Chill 7. On a Chill/Beat song, Rush no-matches (0.5)
    # and Chill cross-matches the song primary as the Mini secondary (0.75).
    # weighted budget = floor(12*5*0.5) + floor(7*5*0.75) = 30 + 26 = 56; 2/3+1/3 -> Chill 37, Beat 18.
    assert materialized["Rush"] == 60
    assert materialized["Chill"] == 72
    assert materialized["Beat"] == 18
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 37, "Beat": 18}


def test_real_export_ringmaster_roxie_clouds_in_blue_uses_ascension_half_scale():
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "Ringmaster Roxie")

    materialized = materialize_mini_for_song(
        mini,
        song_name="Clouds in the Blue (Hard) by Camellia",
        primary_color="Chill",
        secondary_color="Chill",
    )

    assert materialized["Perfect Points"] == 20
    assert materialized["Mini Ascension Song Target Applied"] is True
    # Issue #127: Roxie L1 = Vibe 13 / Rush 7; both no-match a one-color Chill song -> quality 0.5.
    # weighted budget = floor(13*5*0.5) + floor(7*5*0.5) = 32 + 17 = 49; one-color -> +49 Chill.
    assert materialized["Vibe"] == 65
    assert materialized["Rush"] == 35
    assert materialized["Chill"] == 49
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 49}
    assert materialized["Mini Ascension Match Qualities"] == [
        ("Vibe", True, 0.5, "Element Budget", 32),
        ("Rush", False, 0.5, "Element Budget", 17),
    ]


def test_real_export_8_bit_alien_non_flagged_song_gets_base_pp_only():
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "8-Bit Alien")

    materialized = materialize_mini_for_song(
        mini,
        song_name="You & I by RiraN",
        primary_color="Beat",
        secondary_color="Chill",
    )

    assert materialized["Perfect Points"] == 20
    assert materialized["Mini Ascension Song Target Applied"] is False
    assert materialized["Chill"] == 35
    assert materialized["Rush"] == 60


def test_fixed_mini_constraints_resolve_materialized_minis_pruned_from_pool():
    from gear_optimizer.solver.solver_common import _apply_fixed_pool_constraints

    raw_mini = {
        "Name": "Pruned Fixed Mini",
        "type": "Mini",
        "Chill": 50,
        "Perfect Points": 2,
        "Song Target": ["Other Song by Artist"],
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": 10,
    }
    materialized_minis, _by_name, _context = materialize_minis_for_song(
        [raw_mini],
        song_name=TARGET_SONG,
        primary_color="Rush",
        secondary_color="Flow",
    )

    _gear_pool, fixed_pool = _apply_fixed_pool_constraints(
        {},
        [],
        optimize_gear=True,
        optimize_minis=False,
        fixed_gear=None,
        fixed_minis=[raw_mini],
        materialized_mini_catalog=materialized_minis,
    )

    assert fixed_pool == materialized_minis
    assert fixed_pool[0]["Perfect Points"] == 22
    assert fixed_pool[0]["Chill"] == 50
    assert fixed_pool[0]["Mini Ascension Materialized"] is True
    assert fixed_pool[0]["Mini Ascension Song Target Applied"] is False


def test_issue_127_zara_canon_weighted_budget_matches_ingame_62_vibe():
    """Confirmed real fixture (issue #127): the in-game menu reports +62 Vibe.

    Trailblazing Trance Zara L1 = Chill 13 / Vibe 8. Canon In D Major is a one-color Vibe song.
    Chill no-matches (0.5): floor(13*10*0.5*0.5) = 32. Vibe cross-matches the song primary as the
    Mini secondary (0.75): floor(8*10*0.5*0.75) = 30. Weighted budget = 62 -> one-color +62 Vibe.
    The pre-#127 unweighted code pooled 65 + 40 = 105 and returned +105 Vibe.
    """
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "Trailblazing Trance Zara")

    materialized = materialize_mini_for_song(
        mini,
        song_name="Canon In D Major (EduTry Remix) by Pachelbel (Remixed by EduTry)",
        primary_color="Vibe",
        secondary_color="Vibe",
    )

    assert materialized["Perfect Points"] == 20
    assert materialized["Mini Ascension Song Target Applied"] is True
    assert materialized["Chill"] == 65
    assert materialized["Vibe"] == 102
    assert materialized["Mini Ascension Elemental Bonus"] == {"Vibe": 62}
    assert materialized["Mini Ascension Match Qualities"] == [
        ("Chill", True, 0.5, "Element Budget", 32),
        ("Vibe", False, 0.75, "Element Budget", 30),
    ]


def test_issue_127_monstercat_perfect_match_control_stays_unchanged():
    """Perfect-match control (issue #127): both qualities are 1.0, so the fix must not change it.

    Monstercat L1 = Chill 13 / Flow 7 on a Chill-primary / Flow-secondary song at Ascension 10:
    floor(13*10*0.5*1.0) = 65, floor(7*10*0.5*1.0) = 35; weighted budget = 100 -> 2/3 Chill, 1/3 Flow.
    """
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "Monstercat")

    materialized = materialize_mini_for_song(
        mini,
        song_name="From Here by CloudNone [Monstercat]",
        primary_color="Chill",
        secondary_color="Flow",
    )

    assert materialized["Perfect Points"] == 20
    assert materialized["Mini Ascension Song Target Applied"] is True
    assert materialized["Chill"] == 131
    assert materialized["Flow"] == 68
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 66, "Flow": 33}
