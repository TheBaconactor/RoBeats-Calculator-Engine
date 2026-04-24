import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch


def _ref_arrays() -> dict:
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.7, 1.5, rows, dtype=np.float32),
        "Fever Time": np.linspace(0.8, 2.4, rows, dtype=np.float32),
    }


def test_resolved_window_pair_filter_drops_only_all_bad_resolved_rows() -> None:
    ts = np.asarray([i * 0.1 for i in range(30)], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "fg-window-filter-test",
            "Long Notes": 0,
            "Last Note Time": float(ts[-1]),
            "TimelineAnalysisMaxWindows": 1,
        },
        "song_data": {
            "timestamps": ts,
            "chart_timestamps": ts,
            "fg_timestamps": ts,
            "fg_great_candidate_timestamps": ts + np.float32(0.01),
        },
    }

    kept, dropped = gpu_dispatch._filter_ftff_pairs_by_resolved_window_cap(
        ftff_pairs=np.asarray([(0, 0), (0, 90)], dtype=np.int32),
        base_stats_pairs=[(0, 0)],
        calc_song=calc_song,
        ref_arrays=_ref_arrays(),
        max_windows=1,
        gem_scale_fever=3,
    )

    assert kept == [(0, 90)]
    assert dropped == 1


def test_resolved_window_pair_filter_keeps_pair_if_any_base_row_survives() -> None:
    ts = np.asarray([i * 0.1 for i in range(30)], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "fg-window-filter-test",
            "Long Notes": 0,
            "Last Note Time": float(ts[-1]),
        },
        "song_data": {
            "timestamps": ts,
            "chart_timestamps": ts,
            "fg_timestamps": ts,
            "fg_great_candidate_timestamps": ts + np.float32(0.01),
        },
    }

    kept, dropped = gpu_dispatch._filter_ftff_pairs_by_resolved_window_cap(
        ftff_pairs=[(0, 0)],
        base_stats_pairs=[(0, 0), (0, 160)],
        calc_song=calc_song,
        ref_arrays=_ref_arrays(),
        max_windows=1,
        gem_scale_fever=3,
    )

    assert kept == [(0, 0)]
    assert dropped == 0


def test_resolved_window_filter_is_group_level_before_genome_chunks() -> None:
    # Keep the root-cause guard readable by inspecting the module source; constants alone
    # cannot preserve the surrounding control-flow markers we care about.
    import inspect

    body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    filter_pos = body.index("_filter_ftff_pairs_by_resolved_window_cap(")
    pack_pos = body.index("ftff_pairs_packed = _pack_pairs_int32(ftff_pairs)")
    chunk_pos = body.index("while idx0 < n_sig:")

    assert filter_pos < pack_pos < chunk_pos
    assert body.rfind("_filter_ftff_pairs_by_resolved_window_cap(") == filter_pos


def test_base_stat_pairs_from_signature_rows_is_stable_and_unique() -> None:
    sig_rows = {
        "a": {"base_stats": {"Fever Time": 3, "Fever Fill Rate": 9}},
        "b": {"base_stats": {"Fever Time": 3, "Fever Fill Rate": 9}},
        "c": {"base_stats": {"Fever Time": 6, "Fever Fill Rate": 0}},
        "ignored": {},
    }

    assert gpu_dispatch._base_stat_pairs_from_signature_rows(["c", "a", "b", "missing"], sig_rows) == [
        (3, 9),
        (6, 0),
    ]
