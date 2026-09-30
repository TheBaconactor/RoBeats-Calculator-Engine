import numpy as np
import pytest

from gear_optimizer.chart import load_chart, read_chart, read_header
from gear_optimizer.solver.song_preparation import prepare_song


def _write_song(path):
    path.write_text(
        "\n".join(
            [
                "Song Name\tShared IO Song",
                "Difficulty\tHard",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Last Note Time\t0.4",
                "Total Notes\t3",
                "Long Notes\t1",
                "Song Data",
                "0.0 0 0 1",
                "0.2 0 0 3",
                "0.4 0 0 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_prepared_song_is_the_shared_chart_timed_in_its_default_mode(tmp_path):
    song_path = tmp_path / "shared_io_song.txt"
    _write_song(song_path)

    song = prepare_song(str(song_path))

    assert song.chart is load_chart(song_path)
    assert song.chart.name == "Shared IO Song"
    assert song.mode == "perfect_window"
    assert np.array_equal(song.chart.note_types, np.asarray([1, 3, 1], dtype=np.int16))
    assert np.array_equal(song.hit_timestamps, song.chart.timestamps)
    assert song.perfect_candidates is not None and song.great_floor is not None


def test_read_header_reads_the_fields_without_the_notes(tmp_path):
    song_path = tmp_path / "shared_io_song.txt"
    _write_song(song_path)

    header = read_header(song_path)

    assert header == dict(read_chart(song_path).header)
    assert header["Song Name"] == "Shared IO Song"


def test_read_header_rejects_a_line_without_a_tab(tmp_path):
    song_path = tmp_path / "bad_header.txt"
    song_path.write_text("Song Name\tBad\nPrimary Color: Rush\nSong Data\n0.0 0 0 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="key<TAB>value"):
        read_header(song_path)


def _write_song_loggerprod_order(path):
    """Chart in the live game-export (SongLoggerProd) note order: HitObjects array order,
    NOT chronological. A hold's synthesized tail (type 3) is emitted right after its head
    (type 2) at head_time + duration, so a later note in array order sits earlier in time.
    """
    path.write_text(
        "\n".join(
            [
                "Song Name\tArray Order Song",
                "Difficulty\tHard",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Last Note Time\t0.3",
                "Total Notes\t5",
                "Long Notes\t2",
                "Song Data",
                "0.000\t1\t1\t2",  # hold head @0.000
                "0.300\t1\t1\t3",  # its tail @0.300 -- emitted next, jumps ahead in time
                "0.100\t2\t2\t1",  # normal @0.100 -- earlier than the tail above
                "0.200\t3\t3\t1",  # normal @0.200 (chord with the tail below)
                "0.200\t4\t3\t3",  # another hold's tail @0.200, same timestamp as the normal
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_non_time_sorted_export_is_canonicalized_to_nondecreasing_time(tmp_path):
    """The optimizer's fever model requires nondecreasing timestamps (the FG response builder
    fails loudly otherwise). Game exports are NOT time-sorted, so chart ingest must stable-sort
    by time with note_types kept aligned -- ties (true chords) keep export order."""
    song_path = tmp_path / "array_order_song.txt"
    _write_song_loggerprod_order(song_path)

    chart = read_chart(song_path)
    ts = chart.timestamps
    nt = chart.note_types

    # Stable sort by time: [0.0, 0.3, 0.1, 0.2, 0.2] -> [0.0, 0.1, 0.2, 0.2, 0.3]
    assert np.allclose(ts, np.asarray([0.0, 0.1, 0.2, 0.2, 0.3], dtype=np.float32))
    # note_types follow the same permutation; the 0.200 chord keeps export order (normal, tail).
    assert np.array_equal(nt, np.asarray([2, 1, 1, 3, 3], dtype=np.int16))
    # The invariant the FG builder validates: nondecreasing timestamps.
    assert bool(np.all(ts[1:] >= ts[:-1]))

    # Same canonical order flows through the production song preparation.
    song = prepare_song(str(song_path))
    assert np.array_equal(song.chart.timestamps, ts)
    assert np.array_equal(song.chart.note_types, nt)
