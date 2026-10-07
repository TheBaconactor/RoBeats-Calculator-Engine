import json
from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.gamedata import MINI_ASCENSION_VERSION, STATS, load_gears, load_minis, load_stat_curves, song_minis
from gear_optimizer.pipeline import canonical
from gear_optimizer.pipeline.canonical import canonical_rows, loadout_identity, row_order, stored_stats
from gear_optimizer.pipeline.results import SolvedFg, SolvedLoadout, SongSolve
from gear_optimizer.settings import paths
from gear_optimizer.solver.scoring.fever_solver import GemSolve
from gear_optimizer.stats import GEM_KINDS, gems, named_loadout_stats
from gear_optimizer.store.records import decode_trace
from tests.items_support import make_gear, make_mini
from tests.songs_support import make_song

SONG = "Song A"
GEARS = {
    "Helmet": make_gear("Helmet", "Hat", **{"Perfect Points": 10, "Flow": 20}),
    "Vest": make_gear("Vest", "Shirt", **{"Combo Multiplier": 7, "Vibe": 15}),
    "Cap": make_gear("Cap", "Hat", **{"Perfect Points": 9, "Flow": 21}),
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
VIEW = {m.name: m for m in song_minis(MINIS.values(), SONG, "Flow", "Vibe")}
META_GEMS = gems(cm=10, fm=10, ft=6, ff=1, element=63)
FG_GEMS = gems(pp=1, cm=9, fm=11, ft=5, ff=2, element=60)


def _gems(allocation) -> tuple[int, ...]:
    return tuple(allocation[k] for k in GEM_KINDS)


def _stats(gear, minis, allocation) -> dict[str, int]:
    return named_loadout_stats(team_buff_effect("T5", "Flow"), gear, minis, GEARS, VIEW, allocation, "Flow")


def test_equivalent_minis_share_one_identity_with_their_group_and_representative():
    twin = loadout_identity(SolvedLoadout(("Helmet", "Vest"), ("Chroma Twin", "Marie")), VIEW, "Flow", "Vibe")
    plain = loadout_identity(SolvedLoadout(("Helmet", "Vest"), ("Chroma", "Marie")), VIEW, "Flow", "Vibe")
    assert twin == plain
    assert sorted(twin.groups) == [("Chroma", "Chroma Twin"), ("Marie",)]
    assert sorted(twin.reps) == ["Chroma", "Marie"]
    other = loadout_identity(SolvedLoadout(("Cap", "Vest"), ("Chroma", "Marie")), VIEW, "Flow", "Vibe")
    assert other.loadout_hash != twin.loadout_hash


def test_stored_stats_come_from_the_representatives_and_must_keep_the_scoring_stats():
    ident = loadout_identity(SolvedLoadout(("Helmet", "Vest"), ("Chroma Twin", "Marie")), VIEW, "Flow", "Vibe")
    solved = _stats(["Helmet", "Vest"], ["Chroma Twin", "Marie"], META_GEMS)  # the GA's names: Rush 9 from the twin
    fixed = team_buff_effect("T5", "Flow")
    got = dict(zip(STATS, stored_stats(fixed, ident, GEARS, VIEW, "Flow", _gems(META_GEMS), solved, ("Flow", "Vibe"))))
    assert got == _stats(["Helmet", "Vest"], ["Chroma", "Marie"], META_GEMS)
    solved["Flow"] += 1
    with pytest.raises(ValueError, match="change scoring stats"):
        stored_stats(fixed, ident, GEARS, VIEW, "Flow", _gems(META_GEMS), solved, ("Flow", "Vibe"))


def test_rows_are_ordered_best_then_fg_results_in_fg_order_then_the_rest():
    assert row_order(5, [3, 0, 1]) == [0, 3, 1, 2, 4]
    assert row_order(3, []) == [0, 1, 2]
    assert row_order(0, []) == []


def _solve(loadouts, fg=(), mode="precise"):
    song = make_song(np.array([1.0, 2.0, 3.0]), mode=mode, name=SONG, primary="Flow", secondary="Vibe")
    return SongSolve(SONG, "T5", song, object(), tuple(loadouts), tuple(fg))


def _fg(score, trace=None, gear=("Helmet", "Vest"), paired=1000, minis=("Chroma", "Marie")) -> SolvedFg:
    stats = _stats(list(gear), list(minis), FG_GEMS)
    return SolvedFg(
        element="Flow",
        gems=_gems(FG_GEMS),
        stats=tuple(stats[s] for s in STATS),
        surface=tuple(range(11)),
        trace=trace if trace is not None else {"frontier_trace": [{"next_state": 2}]},
        score=score,
        paired=paired,
    )


@pytest.fixture
def scored(monkeypatch):
    """Canonicalization with the gem re-solve and the replays replaced: meta scores by loadout (first gear name),
    FG scores by the solved result's score (`scored` lists the meta scores in row order)."""
    meta_scores = []

    def meta_resolve(fixed, items, song, curves, primary):
        return [
            GemSolve(_gems(META_GEMS), _stats([g.name for g in row[:2]], [m.name for m in row[2:]], META_GEMS), 0)
            for row in items
        ]

    monkeypatch.setattr(canonical, "_meta_resolve", meta_resolve)
    monkeypatch.setattr(canonical, "_meta_score", lambda stats, song, curves: (meta_scores.pop(0), {"trace": 1}))
    return meta_scores


def test_an_fg_result_stays_attached_whether_or_not_it_beats_the_meta_score(scored):
    helmet = SolvedLoadout(("Helmet", "Vest"), ("Chroma", "Marie"))
    for meta_score, fg_score in ((1000, 1500), (1500, 1500), (1600, 1500)):
        scored.append(meta_score)
        (row,) = canonical_rows(_solve([helmet], [(0, _fg(fg_score))]), GEARS, MINIS)
        x = row.loadout
        assert (x.score, x.fg_score, x.mini_ascension, x.primary, x.secondary) == (
            meta_score,
            fg_score,
            MINI_ASCENSION_VERSION,
            "Flow",
            "Vibe",
        )
        assert x.meta.gems == _gems(META_GEMS) and x.fg.gems == _gems(FG_GEMS) and x.fg.surface == tuple(range(11))
        assert decode_trace(row.meta_trace) == {"trace": 1}
        assert decode_trace(row.fg_trace) == {"frontier_trace": [{"next_state": 2}]}


def test_rows_follow_the_store_order_and_a_repeated_loadout_fails_loudly(scored):
    a = SolvedLoadout(("Helmet", "Vest"), ("Chroma", "Marie"))
    b = SolvedLoadout(("Cap", "Vest"), ("Chroma", "Marie"))
    c = SolvedLoadout(("Helmet", "Vest"), ("Marie", "Marie"))
    scored.extend([900, 800, 700])
    # c's FG result does not beat the base it was solved against: c keeps its surface place.
    fg = [(1, _fg(1100, gear=c.gear, paired=1200, minis=c.minis)), (2, _fg(1000, gear=b.gear, paired=800))]
    rows = canonical_rows(_solve([a, c, b], fg), GEARS, MINIS)
    assert [r.loadout.loadout_hash for r in rows] == [
        loadout_identity(x, VIEW, "Flow", "Vibe").loadout_hash for x in (a, b, c)
    ]
    scored.extend([900, 800])
    twin = SolvedLoadout(("Helmet", "Vest"), ("Chroma Twin", "Marie"))
    with pytest.raises(ValueError, match="holds loadout"):
        canonical_rows(_solve([a, twin]), GEARS, MINIS)


def test_an_fg_result_without_a_replay_trace_is_rejected():
    solve = _solve([SolvedLoadout(("Helmet", "Vest"), ("Chroma", "Marie"))])
    with pytest.raises(ValueError, match="without a frontier trace"):
        canonical._fg_trace(_fg(1500, trace={"raw_fever_fill": 1.0}), solve.timed)


def test_real_song_base_result_is_the_exhaustive_gem_optimum_scored_by_exact_replay():
    """Be Right There (Hard), T5: the canonical meta result of a frozen loadout (the old persistence contract)."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    frozen = json.loads(
        (Path(__file__).parent / "fixtures" / "persistence_authority_be_right_there_t5.json").read_text()
    )
    song = time_song(load_chart(Path(__file__).resolve().parents[1] / frozen["song_file_rel"]), "precise")
    curves = load_stat_curves(paths().stats_txt)
    build_or_load_timeline_frontier_payload(song, curves)
    base = frozen["base_entry"]
    solve = SongSolve(
        song.chart.name, "T5", song, curves, (SolvedLoadout(tuple(base["gear"]), tuple(base["minis"])),), ()
    )
    (row,) = canonical_rows(solve, load_gears(paths().gears_csv), load_minis(paths().minis_csv))
    x = row.loadout
    assert x.score == base["expected_score"] == 47192170
    assert (x.fg, x.fg_score) == (None, None)
    allocation = dict(zip(GEM_KINDS, x.meta.gems))
    assert (allocation["Fever Multiplier"], allocation["Element"], allocation["Fever Fill Rate"]) == (13, 64, 13)
    assert dict(zip(STATS, x.meta.stats)) == base["details"]["Stats"]
    trace = decode_trace(row.meta_trace)
    assert trace["activation_judgment"] == "perfect"
    assert trace["frontier_trace"] and all(r["activation_judgment"] == "perfect" for r in trace["frontier_trace"])
