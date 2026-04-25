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


def _calc_song(ts: np.ndarray) -> dict:
    return {
        "metadata": {
            "Song Name": "fg-window-filter-test",
            "Long Notes": 0,
            "Last Note Time": float(ts[-1]),
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
        },
        "song_data": {
            "timestamps": ts,
            "chart_timestamps": ts,
            "fg_timestamps": ts,
            "fg_great_candidate_timestamps": ts + np.float32(0.01),
        },
    }


def test_resolved_window_pair_filter_drops_only_all_bad_resolved_rows() -> None:
    ts = np.asarray([i * 0.1 for i in range(30)], dtype=np.float32)

    kept, dropped = gpu_dispatch._filter_ftff_pairs_by_resolved_window_max(
        ftff_pairs=np.asarray([(0, 0), (0, 90)], dtype=np.int32),
        base_stat_pairs=[(0, 0)],
        calc_song=_calc_song(ts),
        ref_arrays=_ref_arrays(),
        max_windows=1,
        gem_scale_fever=3,
    )

    assert kept == [(0, 90)]
    assert dropped == 1


def test_resolved_window_pair_filter_keeps_pair_if_any_base_row_survives() -> None:
    ts = np.asarray([i * 0.1 for i in range(30)], dtype=np.float32)

    kept, dropped = gpu_dispatch._filter_ftff_pairs_by_resolved_window_max(
        ftff_pairs=[(0, 0)],
        base_stat_pairs=[(0, 0), (0, 160)],
        calc_song=_calc_song(ts),
        ref_arrays=_ref_arrays(),
        max_windows=1,
        gem_scale_fever=3,
    )

    assert kept == [(0, 0)]
    assert dropped == 0


def test_resolved_stat_pair_reducer_drops_cost_dominated_saturated_pairs() -> None:
    pairs = [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0)]
    base_stat_pairs = [(159, 159)]

    kept, dropped = gpu_dispatch._reduce_ftff_pairs_by_resolved_stat_cost(
        ftff_pairs=pairs,
        base_stat_pairs=base_stat_pairs,
        gem_scale_fever=3,
    )

    assert kept == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert dropped == 2

    kept_signatures = {
        gpu_dispatch._resolved_ftff_pair_signature(
            ft_gems=ft,
            ff_gems=ff,
            base_stat_pairs=base_stat_pairs,
            gem_scale_fever=3,
        ): ft + ff
        for ft, ff in kept
    }
    for ft, ff in set(pairs) - set(kept):
        signature = gpu_dispatch._resolved_ftff_pair_signature(
            ft_gems=ft,
            ff_gems=ff,
            base_stat_pairs=base_stat_pairs,
            gem_scale_fever=3,
        )
        assert kept_signatures[signature] <= ft + ff


def test_resolved_stat_pair_reducer_keeps_pairs_when_any_base_row_differs() -> None:
    kept, dropped = gpu_dispatch._reduce_ftff_pairs_by_resolved_stat_cost(
        ftff_pairs=[(0, 1), (0, 2)],
        base_stat_pairs=[(159, 159), (0, 0)],
        gem_scale_fever=3,
    )

    assert kept == [(0, 1), (0, 2)]
    assert dropped == 0


def test_resolved_stat_pair_reducer_keeps_elemental_tradeoff_pairs() -> None:
    kept, dropped = gpu_dispatch._reduce_ftff_pairs_by_resolved_stat_cost(
        ftff_pairs=[(1, 0), (2, 0), (0, 1), (0, 2)],
        base_stat_pairs=[(159, 159)],
        gem_scale_fever=3,
        total_budget=90,
        is_p_ft=1,
    )

    # (1,0) and (2,0) resolve to the same FT/FF timing cell, but (2,0)
    # trades one remaining gem for more primary elemental value. Neither state
    # dominates the other, so dropping either would not be lossless.
    assert (1, 0) in kept
    assert (2, 0) in kept
    # FF has no elemental value in this setup, so the cheaper saturated FF pair
    # still dominates the more expensive one.
    assert (0, 1) in kept
    assert (0, 2) not in kept
    assert dropped == 1


def test_resolved_window_filter_is_group_level_before_genome_chunks() -> None:
    import inspect

    body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    reducer_pos = body.index("_reduce_ftff_pairs_by_resolved_stat_cost(")
    filter_pos = body.index("_filter_ftff_pairs_by_resolved_window_max(")
    pack_pos = body.index("ftff_pairs_packed = _pack_pairs_int32(ftff_pairs)")
    chunk_pos = body.index("while idx0 < n_sig:")

    assert reducer_pos < filter_pos < pack_pos < chunk_pos
    assert "fg_resolved_pair_reduction_cache.get" in body
    assert body.rfind("_filter_ftff_pairs_by_resolved_window_max(") == filter_pos


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
