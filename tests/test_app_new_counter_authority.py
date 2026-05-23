from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.helpers.song_helpers.persistence import RECORD_UPDATE_SCORE_EPSILON
from gear_optimizer.solver.native_inflight_lifecycle import ProgressTracker, evaluate_fg_progress_record_update
from gear_optimizer.solver.native_inflight_config import make_native_song


def _make_minimal_app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._session_new_records = 0
    app._session_new_record_keys = set()
    app._session_new_record_best_by_song = {}
    app._progress = None
    app._runtime_completed_count = 0
    app._runtime_total_count = 0
    app._runtime_failed_count = 0
    app._run_current_song_label = ""
    app._runtime_status_name = "idle"
    app._tui_progress = None
    app._tui_publish = lambda **_kwargs: None
    app._set_runtime_progress_counts = lambda **_kwargs: None
    return app


def _record(song: str, *, prev_overall: int, best_overall: int, record_update: bool = True) -> dict:
    return {
        "song": str(song),
        "record_update": bool(record_update),
        "prev_overall_score": int(prev_overall),
        "best_overall_score_run": int(best_overall),
        "score": int(best_overall),
        "best_fg_score_run": 0,
    }


def test_new_counter_counts_authoritative_song_once_for_duplicate_progress_events():
    app = _make_minimal_app()
    info = _record("Alpha Song (Run 1/2)", prev_overall=1000, best_overall=1400)

    app._progress_event(completed_delta=0, record_info=info)
    app._progress_event(completed_delta=1, record_info=dict(info))

    assert app._session_new_records == 1
    assert app._session_new_record_keys == {"Alpha Song"}


def test_new_counter_ignores_non_authoritative_delta_within_epsilon():
    app = _make_minimal_app()
    prev_overall = 5000
    best_overall = prev_overall + int(RECORD_UPDATE_SCORE_EPSILON)
    info = _record("Beta Song", prev_overall=prev_overall, best_overall=best_overall)

    app._progress_event(completed_delta=1, record_info=info)

    assert app._session_new_records == 0
    assert app._session_new_record_keys == set()


def test_new_counter_dedupes_duplicate_score_by_normalized_song_name():
    app = _make_minimal_app()
    info1 = _record("Gamma Song (Run 1/3)", prev_overall=100, best_overall=300)
    info2 = _record("Gamma Song (Run 2/3)", prev_overall=100, best_overall=300)

    app._progress_event(completed_delta=0, record_info=info1)
    app._progress_event(completed_delta=0, record_info=info2)

    assert app._session_new_records == 1
    assert app._session_new_record_keys == {"Gamma Song"}
    assert app._session_new_record_best_by_song == {"Gamma Song": 300}


def test_new_counter_counts_later_same_song_record_improvement():
    app = _make_minimal_app()
    info1 = _record("Gamma Song (Run 1/3)", prev_overall=100, best_overall=300)
    info2 = _record("Gamma Song (Run 2/3)", prev_overall=300, best_overall=600)

    app._progress_event(completed_delta=0, record_info=info1)
    app._progress_event(completed_delta=0, record_info=info2)

    assert app._session_new_records == 2
    assert app._session_new_record_keys == {"Gamma Song"}
    assert app._session_new_record_best_by_song == {"Gamma Song": 600}


def test_new_counter_counts_native_fg_record_event_before_tracker_advances():
    app = _make_minimal_app()
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("fg-song", best_score=1000, best_fg=900, baseline_valid=True)
    song = make_native_song(
        db_key="fg-song",
        task_key="FG Song (Hard)",
        best_data={"BaseScore": 1000},
        fg_variants=[
            {
                "base_score": 1000,
                "fg_score": 1050,
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
        db_best_score=1000,
        db_best_fg_score=900,
    )

    info = evaluate_fg_progress_record_update(song, tracker)
    app._progress_event(completed_delta=0, record_info=info)

    assert app._session_new_records == 1
    assert app._session_new_record_keys == {"FG Song (Hard)"}
