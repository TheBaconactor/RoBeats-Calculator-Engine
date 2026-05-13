from types import SimpleNamespace

import pytest

from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.solver.song_db_context import PreparedSongDbContext
from gear_optimizer.solver import song_preparation
from gear_optimizer.solver.song_preparation import PreparedSongConfig


def _common_cfg(**iteration_engine: str) -> dict:
    return {
        "IterationEngine": {
            **iteration_engine,
        },
        "UserInputStatsGems": {
            "perfect_points": "0",
            "combo_multiplier": "0",
            "fever_multiplier": "0",
            "fever_fill": "0",
            "fever_time": "0",
        },
        "ElementalGems": {
            "Chill": "0",
            "Flow": "0",
            "Rush": "0",
            "Beat": "0",
            "Vibe": "0",
        },
    }


def _common_args(cfg_dict: dict, *, song_name: str) -> tuple:
    preloaded_calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"},
        "song_data": {"timestamps": [0.0], "note_types": [1]},
    }
    return (
        "fake_song.txt",
        song_name,
        "Hard",
        cfg_dict,
        {},
        {},
        [],
        [],
        {},
        {},
        False,
        False,
        1,
        None,
        0,
        False,
        preloaded_calc_song,
        True,
    )


def _patch_common(monkeypatch, song_processor) -> dict[str, object]:
    prepared = {"pre_prune_mode": None}

    monkeypatch.delenv("METAFINDER_OUTER_SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("OUTER_SEARCH_ENGINE", raising=False)
    monkeypatch.setattr(
        song_preparation,
        "load_prepared_song_db_context",
        lambda *args, **kwargs: PreparedSongDbContext(
            baseline_team_buff="T5",
            db_key="pytest",
            prev_record=None,
            known_loadouts={},
            db_best_score=0,
            db_best_fg_score=0,
            attempt_lifetime=0,
            attempts_first=1,
            prev_attempts_first=0,
            db_baseline_valid=True,
            allow_db_seed=True,
        ),
    )
    monkeypatch.setattr(
        song_preparation,
        "build_prepared_song_config",
        lambda *args, **kwargs: PreparedSongConfig(
            ga_settings=SimpleNamespace(multi_start=1),
            fixed_stats={},
            current_gear_stats={},
            current_gear_list=[],
            current_mini_stats={},
            current_mini_list=[],
            meta_finder=True,
            enable_fever=True,
            enable_mini=True,
            enable_gear=True,
            force_greats_mode=False,
            force_greats_finder=False,
            force_greats_config=[],
            manual_force_greats=False,
        ),
    )
    def _fake_prepare_solver_context(*args, **kwargs):
        prepared["pre_prune_mode"] = kwargs.get("pre_prune_mode")
        return SimpleNamespace(registry=None)

    monkeypatch.setattr(song_processor, "prepare_solver_context", _fake_prepare_solver_context)
    return prepared


def test_process_song_task_uses_canonical_ga_route_and_pre_prune(monkeypatch):
    from gear_optimizer.legacy import song_processor_adapter as legacy_song_processor

    song_processor = legacy_song_processor.legacy_song_processor_module()
    prepared = _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0}

    def _fake_ga(*args, **kwargs):
        calls["ga"] += 1
        assert kwargs.get("solver_ctx") is not None
        return ({"BaseScore": 123, "Score": 123}, [], [], None, None, None, [])

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)

    cfg = _common_cfg(PrePruneMode="marginal")
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest main guard"))

    assert calls["ga"] == 1
    assert prepared["pre_prune_mode"] == "none"
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 123


def test_process_song_task_routes_fg_through_finder(monkeypatch):
    from gear_optimizer.legacy import song_processor_adapter as legacy_song_processor

    song_processor = legacy_song_processor.legacy_song_processor_module()
    _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0}

    def _fake_ga(*args, **kwargs):
        calls["ga"] += 1
        assert kwargs.get("solver_ctx") is not None
        return (
            {"BaseScore": 789, "Score": 789, "Stats": {}},
            [],
            [],
            None,
            None,
            None,
            [{"Score": 789, "BaseScore": 789, "Gear": [], "Minis": [], "Data": {"Stats": {}}}],
        )

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)

    cfg = _common_cfg()
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest ga exact-fg routing"))

    assert calls["ga"] == 1
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 789
