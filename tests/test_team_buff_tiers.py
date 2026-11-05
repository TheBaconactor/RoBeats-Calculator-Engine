"""TeamBuff tier replays through their entry point: which rows a tier serves, with which fields. The re-solves are
stubbed here; tools/verify/gate.py compares real batches, and the FG and timing tests run the re-solves themselves."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver import team_buff_tiers as tbt
from gear_optimizer.solver.scoring.fever_solver import GemSolve
from tests.items_support import make_gear, make_song_mini
from tests.songs_support import make_song


def _entry(name: str, *, force=None, fg_score=0, **fields) -> dict:
    return {
        "loadout_hash": name,
        "score": 10,
        "fg_score": fg_score,
        "gear": [make_gear(f"{name}-gear-{i}", **{"Perfect Points": i}) for i in range(6)],
        "minis": [make_song_mini(f"{name}-mini-{i}") for i in range(3)],
        "details": {"Stats": {"Perfect Points": 1}, "TimelineFrontier": {"stale": True}, "st": [1], "gc": [2], "FT": 9},
        "force": force,
        **fields,
    }


def _force(score: int = 500, element: str = "Rush") -> dict:
    return {"Score": score, "SelectedElement": element, "response_surface": [0] * 11}


def _install(monkeypatch, base_scores: dict[str, int], fg_scores: dict[str, int] | None = None, *, seen=None) -> None:
    """The re-solves as stubs: a loadout (named by its first gear) gets its listed scores at every tier."""
    fg_scores = fg_scores or {}

    def loadout_of(pre_gem):
        return next(name for name in base_scores if pre_gem["__name__"] == name)

    real_total = tbt.total

    def fake_total(fixed, *stats):
        if seen is not None:
            seen.setdefault("fixed", []).append(fixed)
        names = [stat["__name__"] for stat in stats if "__name__" in stat]
        return {**real_total(fixed, *[{k: v for k, v in s.items() if k != "__name__"} for s in stats]), "__name__": names[0]}

    def fake_solve(rows, song, curves, *, selected_color):
        return [
            GemSolve((1, 2, 3, 4, 5, 6), {"Perfect Points": 7, "__name__": row["__name__"]}, base_scores[loadout_of(row)])
            for row in rows
        ]

    def fake_replays(rows, song, curves, selected_color, trace_cache):
        out = []
        for row in rows:
            score = fg_scores.get(loadout_of(row))
            out.append(None if score is None else {"Score": score})
        return out

    monkeypatch.setattr(tbt, "total", fake_total)
    monkeypatch.setattr(tbt, "solve_best_fever_combination_batch", fake_solve)
    monkeypatch.setattr(tbt, "build_fixed_timing_fg_replays", fake_replays)
    monkeypatch.setattr(tbt, "score_stats_exact_with_timeline_trace",
                        lambda stats, song, curves: {"TimelineFrontier": {"frontier_trace": [{"fresh": True}]}})
    monkeypatch.setattr(tbt, "fg_response_frontier_bundle_cache_key", lambda _song, _curves: ())
    monkeypatch.setattr(tbt, "release_fg_response_song_memory", lambda _key: None)


@pytest.fixture
def song():
    return make_song(np.linspace(0.0, 10.0, 12), name="tiers")


@pytest.fixture(autouse=True)
def _item_names(monkeypatch):
    """Each loadout's first gear carries its name through the stat sum, for the stubs."""
    real = tbt._entry_loadout_items

    def items(entry, chart):
        first, *rest = real(entry, chart)
        return [SimpleNamespace(stats={**first.stats, "__name__": entry["loadout_hash"]}), *rest]

    monkeypatch.setattr(tbt, "_entry_loadout_items", items)


def test_a_meta_replay_serves_the_top_n_by_base_score_ties_by_hash(monkeypatch, song):
    _install(monkeypatch, {"b": 30, "a": 30, "c": 10})
    entries = [_entry("c"), _entry("b"), _entry("a")]

    rows = tbt.build_team_buff_tier_db_batches(entries=entries, song=song, curves=None, limit=2, tiers=("T1",),
                                               replay_surface="meta")["T1"]

    assert [row["loadout_hash"] for row in rows] == ["a", "b"]
    assert set(rows[0]) == {"loadout_hash", "gear", "minis", "score", "details", "source_score"}
    assert rows[0]["score"] == 30 and rows[0]["source_score"] == 10
    assert rows[0]["gear"] == [f"a-gear-{i}" for i in range(6)]


def test_details_carry_the_tiers_solve_never_the_stored_allocation(monkeypatch, song):
    _install(monkeypatch, {"a": 30})

    (row,) = tbt.build_team_buff_tier_db_batches(entries=[_entry("a")], song=song, curves=None, tiers=("T1",),
                                                 replay_surface="meta")["T1"]

    details = row["details"]
    assert details["FT"] == 4 and details["FF"] == 5
    assert details["TimelineFrontier"] == {"frontier_trace": [{"fresh": True}]}
    assert "st" not in details and "gc" not in details


def test_a_tier_without_a_fresh_trace_drops_the_stored_one(monkeypatch, song):
    _install(monkeypatch, {"a": 30})
    monkeypatch.setattr(tbt, "score_stats_exact_with_timeline_trace",
                        lambda stats, song, curves: {"TimelineFrontier": {"frontier_trace": []}})

    (row,) = tbt.build_team_buff_tier_db_batches(entries=[_entry("a")], song=song, curves=None, tiers=("T1",),
                                                 replay_surface="meta")["T1"]

    assert "TimelineFrontier" not in row["details"]


def test_a_both_replay_appends_fg_only_rows_and_zeroes_the_board_a_row_is_not_on(monkeypatch, song):
    _install(monkeypatch, {"a": 30, "b": 20, "c": 10}, {"b": 90, "c": 80})
    entries = [_entry("a"), _entry("b", force=_force(), fg_score=5, fg_base_score=4), _entry("c", force=_force(), fg_score=6)]

    rows = tbt.build_team_buff_tier_db_batches(entries=entries, song=song, curves=None, limit=2, tiers=("T1",))["T1"]

    assert [row["loadout_hash"] for row in rows] == ["a", "b", "c"]
    a, b, c = rows
    assert (a["fg_score"], a["fg_base_score"], a["force"], a["source_fg_score"]) == (0, 0, None, 0)
    assert (b["score"], b["fg_score"], b["fg_base_score"]) == (20, 90, 20)
    assert (b["source_score"], b["source_fg_base_score"], b["source_fg_score"]) == (10, 4, 5)
    assert (c["score"], c["fg_score"], c["fg_base_score"], c["source_fg_base_score"]) == (0, 80, 10, 10)
    assert b["force"] == {"Score": 90}


def test_an_unplayable_fg_plan_ranks_nowhere_on_the_fg_board(monkeypatch, song):
    _install(monkeypatch, {"a": 30}, {})

    (row,) = tbt.build_team_buff_tier_db_batches(entries=[_entry("a", force=_force())], song=song, curves=None,
                                                 tiers=("T1",))["T1"]

    assert (row["fg_score"], row["force"]) == (0, None)


def test_the_baseline_tier_carries_the_stored_force(monkeypatch, song):
    _install(monkeypatch, {"a": 30}, {"a": 999})
    force = _force()

    (row,) = tbt.build_team_buff_tier_db_batches(entries=[_entry("a", force=force, fg_score=500)], song=song, curves=None,
                                                 tiers=("T5",))["T5"]

    assert row["force"] == force and row["fg_score"] == 500


def test_a_baseline_carry_with_a_non_positive_fg_score_fails_loud(monkeypatch, song):
    _install(monkeypatch, {"a": 30})

    with pytest.raises(ValueError, match="non-positive"):
        tbt.build_team_buff_tier_db_batches(entries=[_entry("a", force=_force(), fg_score=0)], song=song, curves=None,
                                            tiers=("T5",))


def test_an_fg_row_needs_its_persisted_response_surface(monkeypatch, song):
    _install(monkeypatch, {"a": 30})

    with pytest.raises(ValueError, match="response_surface"):
        tbt.build_team_buff_tier_db_batches(entries=[_entry("a", force={"Score": 1})], song=song, curves=None)


def test_a_non_precise_replay_refuses_a_loadout_stored_with_another_element(monkeypatch):
    song = make_song(np.linspace(0.0, 10.0, 12), name="tiers", mode="non-precise", primary="Rush", secondary="Flow")
    _install(monkeypatch, {"a": 30})

    with pytest.raises(ValueError, match="invariant violated"):
        tbt.build_team_buff_tier_db_batches(entries=[_entry("a", force=_force(element="Flow"))], song=song, curves=None)


def test_a_tiers_fixed_stats_move_the_baseline_buff_to_the_tier_and_target_color():
    from gear_optimizer.gamedata import empty_stats

    stats = {**empty_stats(), "Perfect Points": 25, "Rush": 30}  # the baseline T5 on Rush

    assert tbt._tier_fixed_stats(stats, "NONE", "Rush", "Rush") == empty_stats()
    moved = tbt._tier_fixed_stats(stats, "T1", "Rush", "Flow")
    assert (moved["Perfect Points"], moved["Rush"], moved["Flow"]) == (25, 0, 35)


def test_no_entries_or_no_limit_serve_nothing(song):
    assert tbt.build_team_buff_tier_db_batches(entries=[], song=song, curves=None) == {}
    assert tbt.build_team_buff_tier_db_batches(entries=[_entry("a")], song=song, curves=None, limit=0) == {}
