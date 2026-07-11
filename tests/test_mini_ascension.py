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

    # Two-component (issue #127): pool floor(50*10*0.5)=250 + floor(40*10*0.5)=200 -> 450 -> Rush 300 /
    # Flow 150; plus same-position match extras (both quality 1.0) Rush +250 / Flow +200 -> bonus 550 / 350.
    assert materialized["Perfect Points"] == 23
    assert materialized["Rush"] == 600
    assert materialized["Flow"] == 390
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

    # Issue #127: both Mini colors no-match the song (Beat/Vibe vs Rush/Flow) -> no match extra.
    # pool = floor(50*10*0.5) + floor(40*10*0.5) = 250 + 200 = 450; 2/3+1/3 -> Rush 300 / Flow 150.
    assert materialized["Rush"] == 300
    assert materialized["Flow"] == 150
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

    # Issue #127: Flow (Mini primary) cross-matches the song secondary Flow. pool = floor(40*10*0.5)=200
    # -> Rush floor(200*2/3)=133, Flow floor(200/3)=66; plus cross extra floor(40*10*0.25)=100 -> Flow.
    # bonus Rush 133 / Flow 166; +40 base Flow -> total Flow 206.
    assert materialized["Rush"] == 133
    assert materialized["Flow"] == 206


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

    # One-color Rush song, perfect match: pool floor(50*10*0.5)=250 (all to Rush) + same-position
    # extra floor(50*10*0.5)=250 -> bonus 500; +50 base -> 550.
    assert by_name["Target Mini"]["Perfect Points"] == 20
    assert by_name["Target Mini"]["Rush"] == 550
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
    # Rush (perfect match) on Rush/Flow: pool 250 -> Rush 166 / Flow 83; + same-position extra Rush +250
    # -> bonus Rush 416 / Flow 83; +50 base Rush -> Rush 466.
    assert fixed_pool[0]["Perfect Points"] == 21
    assert fixed_pool[0]["Rush"] == 466
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
    # Issue #127 (two-component): 8-Bit Alien L1 = Rush 12 / Chill 7 on a Chill/Beat song.
    # pool = floor(12*10*0.5)+floor(7*10*0.5) = 60+35 = 95 -> Chill floor(95*2/3)=63, Beat floor(95/3)=31.
    # Chill (Mini secondary) cross-matches the song primary Chill -> extra floor(7*10*0.25)=17 -> Chill.
    # bonus Chill 80 / Beat 31; +35 base Chill -> total Chill 115.
    assert materialized["Rush"] == 60
    assert materialized["Chill"] == 115
    assert materialized["Beat"] == 31
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 80, "Beat": 31}


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
    # Issue #127: Roxie L1 = Vibe 13 / Rush 7; both no-match a one-color Chill song -> no match extra.
    # pool = floor(13*10*0.5) + floor(7*10*0.5) = 65 + 35 = 100; one-color -> +100 Chill.
    # Match Qualities row = (color, is_primary, quality, pool_base_contribution, match_extra).
    assert materialized["Vibe"] == 65
    assert materialized["Rush"] == 35
    assert materialized["Chill"] == 100
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 100}
    assert materialized["Mini Ascension Match Qualities"] == [
        ("Vibe", True, 0.5, 65, 0),
        ("Rush", False, 0.5, 35, 0),
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


def test_issue_127_zara_canon_a10_two_component_bonus_matches_ingame_125_vibe():
    """Canonical fixture (issue #127): Zara on Canon at Ascension 10 shows +125 Vibe in-game.

    Two-component: universal pool floor(10*13*0.5)=65 + floor(10*8*0.5)=40 = 105 -> one-color +105 Vibe;
    plus Vibe (Mini secondary) cross-matches the song primary Vibe -> extra floor(10*8*0.25)=20 -> Vibe.
    Ascension bonus = +125 Vibe (final level-50 Vibe = 40 + 125 = 165). Earlier builds returned +62
    (quality-weighted pool, no extra) or +105 (pool only) -- both wrong.
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
    assert materialized["Vibe"] == 165
    assert materialized["Mini Ascension Elemental Bonus"] == {"Vibe": 125}
    assert materialized["Mini Ascension Match Qualities"] == [
        ("Chill", True, 0.5, 65, 0),
        ("Vibe", False, 0.75, 40, 20),
    ]


def test_issue_127_zara_canon_a5_two_component_bonus_matches_ingame_62_vibe():
    """Canonical fixture (issue #127): Zara on Canon at Ascension 5 shows +62 Vibe in-game.

    pool floor(5*13*0.5)=32 + floor(5*8*0.5)=20 = 52 -> +52 Vibe; Vibe cross extra floor(5*8*0.25)=10.
    Ascension bonus = +62 Vibe (final Vibe = 40 + 62 = 102); base PP = 2*5 = 10.
    """
    from gear_optimizer.data.csv_parser import parse_mini_rows

    mini = dict(next(m for m in parse_mini_rows("Data/Gear/Minis.csv") if m["Name"] == "Trailblazing Trance Zara"))
    mini["Mini Ascension Level"] = 5

    materialized = materialize_mini_for_song(
        mini,
        song_name="Canon In D Major (EduTry Remix) by Pachelbel (Remixed by EduTry)",
        primary_color="Vibe",
        secondary_color="Vibe",
    )

    assert materialized["Perfect Points"] == 10
    assert materialized["Chill"] == 65
    assert materialized["Vibe"] == 102
    assert materialized["Mini Ascension Elemental Bonus"] == {"Vibe": 62}


def test_issue_127_monstercat_perfect_match_doubles_via_pool_plus_extra():
    """Perfect-match fixture (issue #127): both colors are same-position matches -> pool + full extra.

    Monstercat L1 = Chill 13 / Flow 7 on a Chill/Flow song at A10: pool floor(13*10*0.5)=65 +
    floor(7*10*0.5)=35 = 100 -> Chill floor(100*2/3)=66, Flow floor(100/3)=33; plus same-position extras
    Chill +65 / Flow +35 -> bonus +131 Chill / +68 Flow (final level-50 = 196 Chill / 103 Flow). These
    +131/+68 are the values the in-game training UI shows.
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
    assert materialized["Chill"] == 196
    assert materialized["Flow"] == 103
    assert materialized["Mini Ascension Elemental Bonus"] == {"Chill": 131, "Flow": 68}
