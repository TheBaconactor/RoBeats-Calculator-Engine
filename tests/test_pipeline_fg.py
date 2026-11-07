"""The FG stage's result rule: FG results are materialized best solve score first, at most LOADOUTS_PER_SONG_LIMIT,
and a loadout whose FG plan no legal hit timing plays goes back in line with its next best surface, until it runs out of
tries and keeps no FG result."""

from types import SimpleNamespace

import pytest

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.pipeline.fg import FG_PLAN_TRIES, best_fg_results
from gear_optimizer.trace.reconstruct import UnplayableTrace


def _jobs(scores):
    return [(index, SimpleNamespace(best_score=score)) for index, score in enumerate(scores)]


def _materialize(unplayable=()):
    def materialize(index, result):
        if index in unplayable:
            raise UnplayableTrace("note_graph: exact input order has no legal bounded hit for note 7's Perfect judgment")
        return SimpleNamespace(score=result.best_score)

    return materialize


def _lower_surface(_index, result):
    return SimpleNamespace(best_score=result.best_score - 10)


def test_results_come_best_first_and_stop_at_the_board_size():
    scores = [1000 + (7 * i) % 97 for i in range(LOADOUTS_PER_SONG_LIMIT + 9)]
    got = best_fg_results(_jobs(scores), _materialize(), _lower_surface, "Song")
    assert [fg.score for _index, fg in got] == sorted(scores, reverse=True)[:LOADOUTS_PER_SONG_LIMIT]


def test_an_unplayable_fg_plan_goes_back_in_line_with_its_next_best_surface():
    scores = [1000, 999, 985]

    def materialize(index, result):
        if index == 0 and result.best_score == 1000:
            raise UnplayableTrace("note_graph: note 7's input has no frame of its own at any rate")
        return SimpleNamespace(score=result.best_score)

    got = best_fg_results(_jobs(scores), materialize, _lower_surface, "Song")
    assert [(index, fg.score) for index, fg in got] == [(1, 999), (0, 990), (2, 985)]


def test_a_loadout_out_of_tries_keeps_no_fg_result_and_the_next_takes_its_place():
    scores = [1000 - 100 * i for i in range(LOADOUTS_PER_SONG_LIMIT + 1)]
    tried = []

    def next_best(index, result):
        tried.append(index)
        return _lower_surface(index, result)

    got = best_fg_results(_jobs(scores), _materialize(unplayable={1}), next_best, "Song")
    assert [index for index, _fg in got] == [0, *range(2, LOADOUTS_PER_SONG_LIMIT + 1)]
    assert tried == [1] * (FG_PLAN_TRIES - 1)


def test_any_other_materialization_error_still_fails_the_song():
    def materialize(index, result):
        raise ValueError("ForceGreats response frontier exact surface replay failed")

    with pytest.raises(ValueError, match="exact surface replay failed"):
        best_fg_results(_jobs([100, 99]), materialize, _lower_surface, "Song")
