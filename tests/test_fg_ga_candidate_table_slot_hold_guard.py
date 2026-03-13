import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_ga_candidate_table_staging_requires_held_slot(monkeypatch):
    """
    Regression guard:
    In GPU-native in-flight mode the GA song slot can be released before FG runs. When released,
    GA->FG candidate table staging becomes unsafe because the slot's candidate table can be
    overwritten by other in-flight songs.

    The FG GPU dispatch path should only attempt GA candidate-table staging when the slot is
    known to be held continuously from GA through FG.
    """
    from gear_optimizer.helpers.song_helpers.force_greats.core import process_force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch as fg_gpu_dispatch
    from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
    from gear_optimizer.solver.taichi_gem import api as taichi_api
    from gear_optimizer.core.constants import TOTAL_ROWS

    monkeypatch.setenv("FG_INPROCESS_EXECUTOR", "0")
    monkeypatch.setattr(fg_gpu_dispatch, "_FG_GA_CANDIDATE_TABLE_ENABLED", True, raising=False)

    class _StageCalled(BaseException):
        pass

    def _boom(*_args, **_kwargs):
        raise _StageCalled()

    monkeypatch.setattr(taichi_api, "ga_stage_genome_base_stats_from_fg_candidates_table", _boom, raising=True)

    # Synthetic minimal chart + refs (same style used across existing FG GPU tests).
    timestamps = np.linspace(0.0, 120.0, 100, dtype=np.float32)
    calc_song_base = {
        "metadata": {
            "Song Name": "FG GA Table Guard Test",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
        "_gpu_song_slot": 0,
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }

    eval_data = {
        "BaseStats": dict(base_stats),
        "Selected Element": "Rush",
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "_ga_gpu_run_idx": 0,
        "_ga_gpu_row_idx": 1,
    }

    def _loadout_entries():
        return {
            "h0": {
                "gear": [],
                "minis": [],
                "score": 123,
                "details": {},
                "fg_score": 0,
                "force": None,
                "eval_data": dict(eval_data),
                "_source": "ga",
                "selected_element": "Rush",
            }
        }

    build_details_fn = make_build_details_fn("Rush", "Flow", "Hard")

    # If the GA slot is marked held, staging is allowed and should be attempted.
    calc_song_held = dict(calc_song_base)
    calc_song_held["_fg_ga_candidate_table_slot_held"] = True
    with pytest.raises(_StageCalled):
        process_force_greats(
            _loadout_entries(),
            False,
            True,
            [],
            calc_song_held,
            ref_arrays,
            "Rush",
            build_details_fn,
            use_gpu=True,
        )

    # If the GA slot is NOT held (released and later reacquired), staging must be skipped.
    calc_song_released = dict(calc_song_base)
    calc_song_released["_fg_ga_candidate_table_slot_held"] = False
    out = process_force_greats(
        _loadout_entries(),
        False,
        True,
        [],
        calc_song_released,
        ref_arrays,
        "Rush",
        build_details_fn,
        use_gpu=True,
    )
    assert isinstance(out, list)
