from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.domain.jobs import SharedRunContext, SongTask

_CONTEXT = SharedRunContext(multi_start=4, curves=None, gears={}, minis={}, ga_depth=125)


def test_a_repeated_song_task_is_labelled_with_its_mode_and_run():
    task = SongTask("Data/Hard/FakeSong.txt", "Fake Song (Hard) by Tester", PRECISE, _CONTEXT, 987, 2, 3)

    assert task.label == "Fake Song (Hard) by Tester (precise, Run 2/3)"


def test_a_single_run_task_is_labelled_with_the_song_name_and_mode():
    assert SongTask("x.txt", "Fake Song", PRECISE, _CONTEXT, 1, 1, 1).label == "Fake Song (precise)"
    assert SongTask("x.txt", "Fake Song", PRECISE, _CONTEXT).label == "Fake Song (precise)"
    assert SongTask("x.txt", "", PRECISE, _CONTEXT, 1, 2, 3).label == "Unknown"
