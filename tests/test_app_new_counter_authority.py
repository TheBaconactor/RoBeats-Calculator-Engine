"""The NEW-record counter: a stored song whose board's best rose by more than the epsilon counts once per song and
session improvement (a song's runs count as the song)."""

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.ui.runtime_ui import RECORD_UPDATE_SCORE_EPSILON


def _app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._session_new_records = 0
    app._session_new_record_best_by_song = {}
    app._progress = None
    app._completed_tasks = 0
    return app


def test_a_record_needs_the_boards_best_to_rise_by_more_than_the_epsilon():
    app = _app()
    app._song_stored("Alpha Song (precise)", 1000, 1000 + RECORD_UPDATE_SCORE_EPSILON)  # scoring noise
    app._song_stored("Beta Song (precise)", 1000, 1000)  # no improvement
    assert app._session_new_records == 0
    app._song_stored("Gamma Song (precise)", 1000, 1000 + RECORD_UPDATE_SCORE_EPSILON + 1)
    assert app._session_new_records == 1
    assert app._completed_tasks == 3


def test_a_songs_runs_count_as_one_song_and_only_a_higher_record_counts_again():
    app = _app()
    app._song_stored("Delta Song (precise, Run 1/3)", 1000, 1100)
    app._song_stored("Delta Song (precise, Run 2/3)", 1000, 1100)  # the same best: not a new record
    assert app._session_new_records == 1
    app._song_stored("Delta Song (precise, Run 3/3)", 1100, 1200)
    assert app._session_new_records == 2
    assert app._session_new_record_best_by_song == {"Delta Song (precise)": 1200}


def test_the_modes_of_a_song_are_separate_records():
    app = _app()
    app._song_stored("Epsilon Song (precise)", 0, 500)
    app._song_stored("Epsilon Song (non-precise)", 0, 500)
    assert app._session_new_records == 2
