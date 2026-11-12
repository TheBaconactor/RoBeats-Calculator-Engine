"""The standalone loop's console (gear_optimizer.ui): the NEW-record counter, the stop hotkey, when the bar draws."""

import io
import sys

from gear_optimizer.app_stop_control import StopController
from gear_optimizer.ui.progress import progress_bar_enabled
from gear_optimizer.ui.runtime_ui import RunConsole


def _console(tmp_path, *, progress: bool = False) -> RunConsole:
    return RunConsole(StopController(bin_dir=str(tmp_path)), progress=progress)


def test_a_record_needs_the_boards_best_to_rise_by_more_than_two_points(tmp_path):
    console = _console(tmp_path)
    console.song_stored("Alpha Song (precise)", 1000, 1002)  # scoring noise
    console.song_stored("Beta Song (precise)", 1000, 1000)  # no improvement
    assert console.new_records == 0
    console.song_stored("Gamma Song (precise)", 1000, 1003)
    assert console.new_records == 1
    assert console.completed == 3


def test_a_songs_runs_count_as_one_song_and_only_a_higher_record_counts_again(tmp_path):
    console = _console(tmp_path)
    console.song_stored("Delta Song (precise, Run 1/3)", 1000, 1100)
    console.song_stored("Delta Song (precise, Run 2/3)", 1000, 1100)  # the same best: not a new record
    assert console.new_records == 1
    console.song_stored("Delta Song (precise, Run 3/3)", 1100, 1200)
    assert console.new_records == 2
    console.song_stored("Delta Song (precise)", 1000, 1150)  # below the song's 1200 of this session
    assert console.new_records == 2


def test_the_modes_of_a_song_are_separate_records(tmp_path):
    console = _console(tmp_path)
    console.song_stored("Epsilon Song (precise)", 0, 500)
    console.song_stored("Epsilon Song (non-precise)", 0, 500)
    assert console.new_records == 2


def test_the_bar_counts_tasks_records_and_failures(tmp_path):
    console, stream = _console(tmp_path, progress=True), io.StringIO()
    console.start(2, stream)
    console.song_stored("Zeta Song (precise)", 0, 500)
    console.song_failed("Eta Song (precise)")
    console.stop()
    last = stream.getvalue().rsplit("\r", 1)[-1]
    assert "2/2" in last and "New: \x1b[92m1" in last and "Failed: \x1b[91m1" in last and last.endswith("\n")


class _FakeMsvcrt:
    def __init__(self) -> None:
        self._read = False

    def kbhit(self) -> bool:
        return not self._read

    def getwch(self) -> str:
        self._read = True
        return "q"


def test_the_q_hotkey_asks_for_a_graceful_stop(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "msvcrt", _FakeMsvcrt())
    stop_control = StopController(bin_dir=str(tmp_path))
    RunConsole(stop_control, progress=False).start(1, io.StringIO())
    assert stop_control.stop_requested_event.wait(timeout=1.0)
    assert not stop_control.force_exit_requested_event.is_set()


def test_the_progress_bar_follows_the_setting_else_draws_on_a_quiet_terminal():
    assert progress_bar_enabled(None, verbose=False, tty=False) is False
    assert progress_bar_enabled(True, verbose=False, tty=False) is True
    assert progress_bar_enabled(None, verbose=True, tty=True) is False
    assert progress_bar_enabled(None, verbose=False, tty=True) is True
    assert progress_bar_enabled(False, verbose=False, tty=True) is False
