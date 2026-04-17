from types import SimpleNamespace

import pytest

from gear_optimizer.core.config import read_outer_search_engine
from gear_optimizer.core.utils import cfg_from_dict


def _common_cfg(**iteration_engine: str) -> dict:
    return {
        "IterationEngine": {
            "GPU_Mode": "true",
            "GPU_Native_GA": "true",
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
    monkeypatch.setattr(song_processor, "load_database_progress_baseline", lambda *args, **kwargs: (None, [], 0, 0, 0, 0, True))
    monkeypatch.setattr(
        song_processor,
        "setup_song_config",
        lambda *args, **kwargs: (
            SimpleNamespace(multi_start=1),
            {},
            {},
            [],
            {},
            [],
            True,
            True,
            True,
            True,
            False,
            False,
            [],
            False,
        ),
    )
    monkeypatch.setattr("gear_optimizer.solver.hit_simulation.apply_human_hit_sim", lambda *args, **kwargs: None)

    def _fake_prepare_solver_context(*args, **kwargs):
        prepared["pre_prune_mode"] = kwargs.get("pre_prune_mode")
        return SimpleNamespace(registry=None)

    monkeypatch.setattr(song_processor, "prepare_solver_context", _fake_prepare_solver_context)
    return prepared


@pytest.mark.parametrize("requested_mode", ["ga", "genetic", "genetic_algorithm", "geneticalgorithm", "unsupported"])
def test_read_outer_search_engine_forces_ga_on_main(requested_mode):
    cfg = cfg_from_dict(_common_cfg(OuterSearchEngine=requested_mode))
    assert read_outer_search_engine(cfg, default="ga") == "ga"


def test_process_song_task_ignores_unsupported_outer_engine_and_pre_prune(monkeypatch):
    from gear_optimizer.pipeline import song_processor

    prepared = _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0}

    def _fake_ga(*args, **kwargs):
        calls["ga"] += 1
        assert kwargs.get("solver_ctx") is not None
        return ({"BaseScore": 123, "Score": 123}, [], [], None, None, None, [])

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)

    cfg = _common_cfg(OuterSearchEngine="unsupported", PrePruneMode="marginal")
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest main guard"))

    assert calls["ga"] == 1
    assert prepared["pre_prune_mode"] == "none"
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 123


def test_process_song_task_keeps_fg_exact_dp_with_ga_outer(monkeypatch):
    from gear_optimizer.pipeline import song_processor

    _patch_common(monkeypatch, song_processor)
    calls = {"ga": 0, "fg_exact": 0}

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

    def _fake_fg_exact(*args, **kwargs):
        calls["fg_exact"] += 1
        assert kwargs.get("use_gpu") is True
        assert kwargs.get("song_slot") == 0
        assert kwargs.get("loadout_entries") is None
        assert kwargs.get("force_greats_finder") is False
        assert kwargs.get("build_details_fn") is None
        return []

    monkeypatch.setattr(song_processor, "solve_coevolution_genetic", _fake_ga)
    monkeypatch.setattr("gear_optimizer.solver.fg_exact_dp_pipeline.process_fg_exact_dp", _fake_fg_exact)

    cfg = _common_cfg(OuterSearchEngine="ga", FG_SolverMode="exact_dp")
    result = song_processor.process_song_task(_common_args(cfg, song_name="pytest ga exact-fg routing"))

    assert calls["ga"] == 1
    assert calls["fg_exact"] == 1
    assert result.get("_deferred_post") is True
    assert (result.get("best_data") or {}).get("BaseScore") == 789
