from gear_optimizer.domain.jobs import SharedRunContext, SongTask

_CONTEXT = SharedRunContext(multi_start=4, curves=None, gears={}, minis={}, ga_depth=125)


def test_a_repeated_song_task_is_labelled_with_its_run():
    task = SongTask("Data/Hard/FakeSong.txt", "Fake Song (Hard) by Tester", _CONTEXT, 987, 2, 3)

    assert task.label == "Fake Song (Hard) by Tester (Run 2/3)"


def test_a_single_run_task_is_labelled_with_the_song_name():
    assert SongTask("x.txt", "Fake Song", _CONTEXT, 1, 1, 1).label == "Fake Song"
    assert SongTask("x.txt", "Fake Song", _CONTEXT).label == "Fake Song"
    assert SongTask("x.txt", "", _CONTEXT, 1, 2, 3).label == "Unknown"
