import pytest

from gear_optimizer.gamedata import STATS
from gear_optimizer.pipeline.results import SolvedLoadout, solved_fg, song_solve
from tests.native_song_factory import make_native_song

GEAR_A = ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]
GEAR_B = ["Hat B", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"]
MINIS = ["Mini 1", "Mini 2", "Mini 3"]
FG_STATS = {s: i for i, s in enumerate(STATS)}


def _payload(score=1500):
    return {
        "Score": score,
        "BaseScore": 1000,
        "GemCounts": {"Perfect Points": 1, "Combo Multiplier": 9, "Fever Multiplier": 11, "Element": 60},
        "FT": 5,
        "FF": 2,
        "Selected Element": "Flow",
        "Stats": dict(FG_STATS),
        "BaseStats": {s: 0 for s in STATS},
        "response_surface": list(range(11)),
        "ForceGreats": {
            "final_score": score,
            "frontier_trace": [{"next_state": 2}],
            "raw_fever_fill": 1.5,
            "forced_counts": [1, 2],
            "config": {"old": True},
        },
        "_ga_gpu_run_idx": 0,
    }


def _song(**kwargs):
    fields = dict(
        db_key="Song A",
        task_key="song-a",
        meta_primary_color="Flow",
        timed_song="timed",
        curves="curves",
        fg_surface_prepared=True,
        ga_candidates=[{"Gear": GEAR_A, "Minis": MINIS, "Score": 1000}, {"Gear": GEAR_B, "Minis": MINIS}],
        fg_results=((SolvedLoadout(tuple(GEAR_B), tuple(MINIS)), solved_fg(_payload(), default_element="Flow")),),
    )
    fields.update(kwargs)
    return make_native_song(**fields)


def test_a_solved_song_is_its_ga_surface_with_the_fg_results_it_published():
    solve = song_solve(_song())
    assert (solve.song, solve.tier, solve.timed, solve.curves) == ("Song A", "T5", "timed", "curves")
    assert solve.loadouts == (SolvedLoadout(tuple(GEAR_A), tuple(MINIS)), SolvedLoadout(tuple(GEAR_B), tuple(MINIS)))
    assert solve.fg == ((1, solved_fg(_payload(), default_element="Flow")),)


def test_an_fg_payload_is_read_as_the_result_it_describes():
    fg = solved_fg(_payload(), default_element="Beat")
    assert (fg.element, fg.score, fg.paired, fg.surface) == ("Flow", 1500, 1000, tuple(range(11)))
    assert fg.gems == (1, 9, 11, 5, 2, 60)  # stats.GEM_KINDS: PP, CM, FM, FT, FF, Element
    assert fg.stats == tuple(FG_STATS[s] for s in STATS)
    # The replay witness without its score and the retired FG configuration fields.
    assert fg.trace == {"frontier_trace": [{"next_state": 2}], "raw_fever_fill": 1.5}
    # A payload that names no element is the song's primary element.
    unnamed = {k: v for k, v in _payload().items() if k != "Selected Element"}
    assert solved_fg(unnamed, default_element="Beat").element == "Beat"


def test_results_are_read_only_after_the_fg_stage():
    with pytest.raises(RuntimeError, match="after the FG stage"):
        song_solve(_song(fg_results=None))
    with pytest.raises(RuntimeError, match="after the FG stage"):
        song_solve(_song(fg_surface_prepared=False))


def test_an_fg_result_must_belong_to_a_surface_loadout():
    stray = (SolvedLoadout(("Other",) * 6, tuple(MINIS)), solved_fg(_payload(), default_element="Flow"))
    with pytest.raises(RuntimeError, match="outside the GA surface"):
        song_solve(_song(fg_results=(stray,)))
