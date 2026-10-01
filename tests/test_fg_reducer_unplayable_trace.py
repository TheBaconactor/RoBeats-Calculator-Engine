from types import SimpleNamespace

import pytest

from gear_optimizer.pipeline.results import SolvedLoadout
from gear_optimizer.solver.fg_response_scoring import reducer as reducer_mod
from gear_optimizer.solver.fg_response_scoring.note_graph import UnplayableTrace


def _plan(monkeypatch, scores, materialize):
    """Five FG jobs (G0..G4, solve scores in `scores`) and a fake materializer; payload Score = the solve score."""
    jobs = [
        SimpleNamespace(loadout=SolvedLoadout((f"G{i}",), ()), selected="Flow", base_stats={}, paired=1, key=i)
        for i in range(len(scores))
    ]
    results = {i: SimpleNamespace(best_score=score) for i, score in enumerate(scores)}
    monkeypatch.setattr(reducer_mod.FgResultReducer, "_result_cache", staticmethod(lambda plan, prepared: results))
    monkeypatch.setattr(reducer_mod, "materialize_force_payload_from_response_frontier", materialize)
    monkeypatch.setattr(
        reducer_mod, "solved_fg", lambda payload, default_element: SimpleNamespace(score=payload["Score"])
    )
    monkeypatch.setattr(reducer_mod, "LOADOUTS_PER_SONG_LIMIT", 3)
    song = SimpleNamespace(fg_inputs=object(), chart=SimpleNamespace(name="Song"))
    return SimpleNamespace(song=song, curves=None, jobs=jobs)


def test_an_unplayable_fg_plan_drops_only_that_loadouts_fg_result_and_the_next_job_takes_its_place(monkeypatch):
    def materialize(*, result, **_kwargs):
        if result.best_score == 99:  # G1's best plan: no legal hit timing plays it
            raise UnplayableTrace(
                "note_graph: exact input order has no legal bounded hit for note 7's Perfect judgment"
            )
        return {"Score": result.best_score}

    plan = _plan(monkeypatch, [100, 99, 98, 97, 96], materialize)
    got = reducer_mod.FgResultReducer.materialize(plan, [])
    assert [(loadout.gear[0], fg.score) for loadout, fg in got] == [("G0", 100), ("G2", 98), ("G3", 97)]


def test_any_other_materialization_error_still_fails_the_song(monkeypatch):
    def materialize(*, result, **_kwargs):
        raise ValueError("ForceGreats response frontier exact surface replay failed")

    plan = _plan(monkeypatch, [100, 99], materialize)
    with pytest.raises(ValueError, match="exact surface replay failed"):
        reducer_mod.FgResultReducer.materialize(plan, [])
