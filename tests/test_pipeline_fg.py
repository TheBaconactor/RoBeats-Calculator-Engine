"""The FG stage's result rule: FG results are materialized best solve score first, at most LOADOUTS_PER_SONG_LIMIT,
and a loadout whose FG plan no legal hit timing plays keeps no FG result while the next takes its place."""

from types import SimpleNamespace

import pytest

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.pipeline.fg import best_fg_results
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import UnplayableTrace


def _jobs(scores):
    return [(index, SimpleNamespace(best_score=score)) for index, score in enumerate(scores)]


def _materialize(unplayable=()):
    def materialize(index, result):
        if index in unplayable:
            raise UnplayableTrace("note_graph: exact input order has no legal bounded hit for note 7's Perfect judgment")
        return SimpleNamespace(score=result.best_score)

    return materialize


def test_results_come_best_first_and_stop_at_the_board_size():
    scores = [1000 + (7 * i) % 97 for i in range(LOADOUTS_PER_SONG_LIMIT + 9)]
    got = best_fg_results(_jobs(scores), _materialize(), "Song")
    assert [fg.score for _index, fg in got] == sorted(scores, reverse=True)[:LOADOUTS_PER_SONG_LIMIT]


def test_an_unplayable_fg_plan_drops_only_that_loadouts_fg_result_and_the_next_takes_its_place():
    scores = [1000 - i for i in range(LOADOUTS_PER_SONG_LIMIT + 1)]
    got = best_fg_results(_jobs(scores), _materialize(unplayable={1}), "Song")
    assert [index for index, _fg in got] == [0, *range(2, LOADOUTS_PER_SONG_LIMIT + 1)]


def test_any_other_materialization_error_still_fails_the_song():
    def materialize(index, result):
        raise ValueError("ForceGreats response frontier exact surface replay failed")

    with pytest.raises(ValueError, match="exact surface replay failed"):
        best_fg_results(_jobs([100, 99]), materialize, "Song")
