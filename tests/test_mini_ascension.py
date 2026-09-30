"""Mini Ascension (gamedata): the flat Perfect Points every mini gains and the song-target elemental bonus.

Every mini ascends at level 10. The in-game fixtures below (issue #127) pin the two-component model.
"""

from gear_optimizer.gamedata import ascended_mini_stats, ascension_element_bonus, load_minis, song_minis
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
from gear_optimizer.settings import paths
from tests.items_support import make_gear, make_mini

TARGET_SONG = "Ascension Target by Artist"


def _target_mini(name, **stats):
    level1 = {color: value for color, value in stats.items() if color in ("Chill", "Flow", "Rush", "Beat", "Vibe")}
    return make_mini(name, level1=level1, song_targets=[TARGET_SONG], **stats)


def _real_mini(name):
    return load_minis(paths().minis_csv)[name]


def test_targeted_mini_gains_base_pp_and_the_primary_secondary_bonus():
    stats = ascended_mini_stats(
        _target_mini("Target Mini", Rush=50, Flow=40, **{"Perfect Points": 3}), TARGET_SONG, "Rush", "Flow"
    )
    # Two-component (issue #127): pool floor(50*10*0.5)=250 + floor(40*10*0.5)=200 -> 450 -> Rush 300 /
    # Flow 150; plus same-position match extras (both quality 1.0) Rush +250 / Flow +200 -> bonus 550 / 350.
    assert stats["Perfect Points"] == 23
    assert stats["Rush"] == 600
    assert stats["Flow"] == 390


def test_nonmatching_colors_only_feed_the_pool():
    stats = ascended_mini_stats(_target_mini("Nonmatch Mini", Beat=50, Vibe=40), TARGET_SONG, "Rush", "Flow")
    # Both Mini colors no-match the song (Beat/Vibe vs Rush/Flow) -> no match extra.
    # pool = floor(50*10*0.5) + floor(40*10*0.5) = 250 + 200 = 450; 2/3+1/3 -> Rush 300 / Flow 150.
    assert (stats["Rush"], stats["Flow"], stats["Beat"], stats["Vibe"]) == (300, 150, 50, 40)


def test_cross_position_match_gets_the_quarter_extra():
    stats = ascended_mini_stats(_target_mini("Cross Mini", Flow=40), TARGET_SONG, "Rush", "Flow")
    # Flow (Mini primary) cross-matches the song secondary Flow. pool = floor(40*10*0.5)=200
    # -> Rush floor(200*2/3)=133, Flow floor(200/3)=66; plus cross extra floor(40*10*0.25)=100 -> Flow.
    # bonus Rush 133 / Flow 166; +40 base Flow -> total Flow 206.
    assert (stats["Rush"], stats["Flow"]) == (133, 206)


def test_untargeted_mini_gains_base_pp_only():
    mini = make_mini("Base Only Mini", song_targets=["Other Song by Artist"], level1={"Rush": 10}, Rush=50,
                     **{"Perfect Points": 1})
    stats = ascended_mini_stats(mini, TARGET_SONG, "Rush", "Flow")
    assert (stats["Perfect Points"], stats["Rush"]) == (21, 50)


def test_one_color_song_perfect_match_and_the_targeting_flag():
    (ascended,) = song_minis([_target_mini("Target Mini", Rush=50)], TARGET_SONG, "Rush", "Rush")
    # One-color Rush song, perfect match: pool floor(50*10*0.5)=250 (all to Rush) + same-position
    # extra floor(50*10*0.5)=250 -> bonus 500; +50 base -> 550.
    assert ascended.targets_song is True
    assert (ascended.stats["Perfect Points"], ascended.stats["Rush"]) == (20, 550)


def test_targeted_nonmatching_mini_survives_initial_pool_filter():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gears = {slot: make_gear(slot, slot, Rush=1) for slot in slots}
    minis = song_minis(
        [
            _target_mini("Targeted Chill Mini", Chill=50),
            make_mini("Untargeted Chill Mini", level1={"Chill": 50}, song_targets=["Other Song by Artist"], Chill=50),
        ],
        TARGET_SONG,
        "Rush",
        "Flow",
    )
    _gear_pool, mini_pool = initialize_pools(gears, minis, "Rush", slots, s_color="Flow")
    assert [mini.name for mini in mini_pool] == ["Targeted Chill Mini"]


def test_real_export_8_bit_alien_flagged_song_gets_base_pp_and_elemental_bonus():
    mini = _real_mini("8-Bit Alien")
    stats = ascended_mini_stats(mini, "Farewell, My Friend by Chroma", "Chill", "Beat")
    # 8-Bit Alien L1 = Rush 12 / Chill 7 on a Chill/Beat song.
    # pool = floor(12*10*0.5)+floor(7*10*0.5) = 60+35 = 95 -> Chill floor(95*2/3)=63, Beat floor(95/3)=31.
    # Chill (Mini secondary) cross-matches the song primary Chill -> extra floor(7*10*0.25)=17 -> Chill.
    # bonus Chill 80 / Beat 31; +35 base Chill -> total Chill 115.
    assert stats["Perfect Points"] == 20
    assert (stats["Rush"], stats["Chill"], stats["Beat"]) == (60, 115, 31)
    assert ascension_element_bonus(mini, "Chill", "Beat") == {"Chill": 80, "Beat": 31}


def test_real_export_ringmaster_roxie_clouds_in_blue_uses_ascension_half_scale():
    mini = _real_mini("Ringmaster Roxie")
    stats = ascended_mini_stats(mini, "Clouds in the Blue (Hard) by Camellia", "Chill", "Chill")
    # Roxie L1 = Vibe 13 / Rush 7; both no-match a one-color Chill song -> no match extra.
    # pool = floor(13*10*0.5) + floor(7*10*0.5) = 65 + 35 = 100; one-color -> +100 Chill.
    assert stats["Perfect Points"] == 20
    assert (stats["Vibe"], stats["Rush"], stats["Chill"]) == (65, 35, 100)
    assert ascension_element_bonus(mini, "Chill", "Chill") == {"Chill": 100}


def test_real_export_8_bit_alien_non_flagged_song_gets_base_pp_only():
    stats = ascended_mini_stats(_real_mini("8-Bit Alien"), "You & I by RiraN", "Beat", "Chill")
    assert (stats["Perfect Points"], stats["Chill"], stats["Rush"]) == (20, 35, 60)


def test_issue_127_zara_canon_a10_two_component_bonus_matches_ingame_125_vibe():
    """In game, Zara on Canon at Ascension 10 shows +125 Vibe.

    Universal pool floor(10*13*0.5)=65 + floor(10*8*0.5)=40 = 105 -> one-color +105 Vibe; plus Vibe (Mini
    secondary) cross-matches the song primary Vibe -> extra floor(10*8*0.25)=20 -> Vibe. Bonus +125 Vibe
    (final Vibe = 40 + 125 = 165). Earlier builds returned +62 (quality-weighted pool, no extra) or +105.
    """
    mini = _real_mini("Trailblazing Trance Zara")
    song = "Canon In D Major (EduTry Remix) by Pachelbel (Remixed by EduTry)"
    stats = ascended_mini_stats(mini, song, "Vibe", "Vibe")
    assert stats["Perfect Points"] == 20
    assert (stats["Chill"], stats["Vibe"]) == (65, 165)
    assert ascension_element_bonus(mini, "Vibe", "Vibe") == {"Vibe": 125}


def test_issue_127_monstercat_perfect_match_doubles_via_pool_plus_extra():
    """Both colors are same-position matches -> pool + full extra; the in-game training UI shows +131/+68.

    Monstercat L1 = Chill 13 / Flow 7 on a Chill/Flow song: pool floor(13*10*0.5)=65 + floor(7*10*0.5)=35
    = 100 -> Chill 66, Flow 33; plus same-position extras Chill +65 / Flow +35 -> bonus +131 / +68.
    """
    mini = _real_mini("Monstercat")
    stats = ascended_mini_stats(mini, "From Here by CloudNone [Monstercat]", "Chill", "Flow")
    assert stats["Perfect Points"] == 20
    assert (stats["Chill"], stats["Flow"]) == (196, 103)
    assert ascension_element_bonus(mini, "Chill", "Flow") == {"Chill": 131, "Flow": 68}
