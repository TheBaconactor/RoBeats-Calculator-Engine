import copy

import pytest

from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.gamedata import MINI_ASCENSION_VERSION, STATS, song_minis
from gear_optimizer.stats import gems, named_loadout_stats
from gear_optimizer.store.entries import candidates_from_entries
from gear_optimizer.store.records import decode_trace
from tests.items_support import make_gear, make_mini

SONG = "Song A"
GEARS = {
    "Helmet": make_gear("Helmet", "Hat", **{"Perfect Points": 10, "Flow": 20}),
    "Vest": make_gear("Vest", "Body", **{"Combo Multiplier": 7, "Vibe": 15}),
}
# Chroma and Chroma Twin differ only in Rush, which this Flow/Vibe song never reads: one equivalence group.
MINIS = {
    "Chroma": make_mini(
        "Chroma", "Flow", level1={"Flow": 10}, song_targets=[SONG], **{"Fever Multiplier": 5, "Flow": 30}
    ),
    "Chroma Twin": make_mini(
        "Chroma Twin",
        "Flow",
        level1={"Flow": 10},
        song_targets=[SONG],
        **{"Fever Multiplier": 5, "Flow": 30, "Rush": 9},
    ),
    "Marie": make_mini("Marie", "Vibe", level1={"Vibe": 8}, **{"Fever Time": 4, "Vibe": 22}),
}
META_GEMS = {"Perfect Points": 0, "Combo Multiplier": 10, "Fever Multiplier": 10, "Element": 63}
FG_GEMS = {"Perfect Points": 1, "Combo Multiplier": 9, "Fever Multiplier": 11, "Element": 60}


def _stats(gem_counts, ft, ff):
    song_view = {m.name: m for m in song_minis(MINIS.values(), SONG, "Flow", "Vibe")}
    allocation = gems(
        pp=gem_counts["Perfect Points"],
        cm=gem_counts["Combo Multiplier"],
        fm=gem_counts["Fever Multiplier"],
        ft=ft,
        ff=ff,
        element=gem_counts["Element"],
    )
    return named_loadout_stats(
        team_buff_effect("T5", "Flow"), ["Helmet", "Vest"], ["Chroma", "Marie"], GEARS, song_view, allocation, "Flow"
    )


def _entry(score=1000, fg_score=1500, **extra):
    entry = {
        "score": score,
        "fg_score": fg_score,
        "fg_base_score": score,
        "gear": ["Helmet", "Vest"],
        "minis": ["Chroma Twin", "Marie"],
        "details": {
            "GemCounts": dict(META_GEMS),
            "FT": 6,
            "FF": 1,
            "SelectedElement": "Flow",
            "PrimaryColor": "Flow",
            "SecondaryColor": "Vibe",
            "Stats": {"stale": 1},
            "TimelineFrontier": {"frontier_trace": [{"next_state": 1}]},
            "ForceGreats": {"final_score": fg_score},
        },
        "force": {
            "Score": fg_score,
            "BaseScore": score,
            "GemCounts": dict(FG_GEMS),
            "FT": 5,
            "FF": 2,
            "SelectedElement": "Flow",
            "Stats": _stats(FG_GEMS, 5, 2),
            "response_surface": list(range(11)),
            "ForceGreats": {"final_score": fg_score, "frontier_trace": [{"next_state": 2}]},
            "GenomeIDs": [1, 2],
        },
    }
    entry.update(extra)
    return entry


def _candidates(entries, **kwargs):
    return candidates_from_entries(
        SONG, "T5", entries, gears=GEARS, minis=MINIS, stored_colors=kwargs.pop("stored", None), now=77, **kwargs
    )


def test_an_entry_becomes_a_loadout_with_both_results_and_recomputed_stats():
    (c,) = _candidates([_entry()])
    x = c.row.loadout
    assert (x.score, x.fg_score, x.primary, x.secondary, x.mini_ascension) == (
        1000,
        1500,
        "Flow",
        "Vibe",
        MINI_ASCENSION_VERSION,
    )
    assert x.gear == ("Helmet", "Vest")
    assert sorted(x.minis) == [("Chroma", "Chroma Twin"), ("Marie",)]
    assert x.meta.gems == (0, 10, 10, 6, 1, 63)
    assert x.meta.stats == tuple(_stats(META_GEMS, 6, 1)[s] for s in STATS)
    assert (x.fg.gems, x.fg.surface) == ((1, 9, 11, 5, 2, 60), tuple(range(11)))
    assert x.fg.stats == tuple(_stats(FG_GEMS, 5, 2)[s] for s in STATS)
    assert decode_trace(c.row.meta_trace) == {"frontier_trace": [{"next_state": 1}]}
    assert decode_trace(c.row.fg_trace) == {"frontier_trace": [{"next_state": 2}]}  # final_score is the fg_score


def test_equivalent_minis_give_one_loadout_and_one_entry_per_score():
    other = _entry()
    other["minis"] = ["Chroma", "Marie"]
    other["details"]["GemCounts"]["Element"] = 70  # more element gems wins among equal scores
    lower = _entry(score=990)
    lower["force"] = None
    candidates = _candidates([_entry(), other, lower])
    assert len({c.row.loadout.loadout_hash for c in candidates}) == 1
    assert [c.row.loadout.score for c in candidates] == [1000, 990]
    assert candidates[0].row.loadout.meta.gems[-1] == 70


def test_a_deferred_fg_update_carries_only_its_fg_result_at_the_paired_base_score():
    entry = _entry(score=950, _deferred_fg_update=True)
    entry.pop("fg_base_score")
    entry["force"]["BaseScore"] = 1000
    (c,) = _candidates([entry])
    assert c.deferred and c.row.loadout.meta is None and c.row.meta_trace is None
    assert (c.row.loadout.score, c.row.loadout.fg_score) == (1000, 1500)


def test_entries_without_colors_use_the_songs_stored_colors():
    entry = _entry()
    for key in ("PrimaryColor", "SecondaryColor"):
        entry["details"].pop(key)
    (c,) = _candidates([entry], stored=("Flow", "Vibe"))
    assert (c.row.loadout.primary, c.row.loadout.loadout_hash) == (
        "Flow",
        _candidates([_entry()])[0].row.loadout.loadout_hash,
    )


def test_canonical_minis_must_not_change_the_fg_scoring_stats():
    entry = _entry()
    entry["force"] = copy.deepcopy(entry["force"])
    entry["force"]["Stats"]["Flow"] += 1
    with pytest.raises(ValueError, match="change FG scoring stats"):
        _candidates([entry])
