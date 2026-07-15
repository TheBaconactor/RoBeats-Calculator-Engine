import numpy as np

from gear_optimizer.data.song_io import get_base_calc_song, read_song_file
from gear_optimizer.solver.song_preparation import build_prepared_calc_song


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


def test_native_calc_song_uses_shared_base_song_io_and_clones_before_timing_envelope(tmp_path):
    song_path = tmp_path / "shared_io_song.txt"
    _write_song(song_path)
    cfg_dict = {"IterationEngine": {"InFlightSongs": "12"}}

    base_calc_song = get_base_calc_song(str(song_path), cfg_dict)
    native_calc_song = build_prepared_calc_song(fp=str(song_path), cfg_dict=cfg_dict).calc_song

    assert native_calc_song is not base_calc_song
    assert native_calc_song["metadata"]["Song Name"] == "Shared IO Song"
    assert native_calc_song["metadata"]["TimingEnvelopeApplied"] is True
    assert "TimingEnvelopeApplied" not in base_calc_song["metadata"]

    assert np.array_equal(
        native_calc_song["song_data"]["timestamps"],
        base_calc_song["song_data"]["timestamps"],
    )
    assert np.array_equal(
        native_calc_song["song_data"]["note_types"],
        np.asarray([1, 3, 1], dtype=np.int16),
    )
    assert np.array_equal(
        native_calc_song["song_data"]["fg_timestamps"],
        native_calc_song["song_data"]["chart_timestamps"],
    )
    assert "fg_timestamps" not in base_calc_song["song_data"]


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

    raw = read_song_file(str(song_path))
    ts = np.asarray(raw["timestamps"], dtype=np.float32)
    nt = np.asarray(raw["note_types"], dtype=np.int16)

    # Stable sort by time: [0.0, 0.3, 0.1, 0.2, 0.2] -> [0.0, 0.1, 0.2, 0.2, 0.3]
    assert np.allclose(ts, np.asarray([0.0, 0.1, 0.2, 0.2, 0.3], dtype=np.float32))
    # note_types follow the same permutation; the 0.200 chord keeps export order (normal, tail).
    assert np.array_equal(nt, np.asarray([2, 1, 1, 3, 3], dtype=np.int16))
    # The invariant the FG builder validates: nondecreasing timestamps.
    assert bool(np.all(ts[1:] >= ts[:-1]))

    # Same canonical order flows through the production calc_song builder.
    calc_song = get_base_calc_song(str(song_path), {})
    cs_ts = np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32)
    cs_nt = np.asarray(calc_song["song_data"]["note_types"], dtype=np.int16)
    assert np.array_equal(cs_ts, ts)
    assert np.array_equal(cs_nt, nt)
