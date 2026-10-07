import pytest

from gear_optimizer.gamedata import STATS
from gear_optimizer.pipeline.results import solved_fg

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
