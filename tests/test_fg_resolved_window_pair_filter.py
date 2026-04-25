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


def test_resolved_stat_pair_reducer_parallel_matches_serial(monkeypatch) -> None:
    pairs = [(ft, ff) for ft in range(40) for ff in range(40) if ft + ff <= 90]
    base_stat_pairs = [(159, 159), (120, 130), (40, 80)]

    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "1")
    serial = gpu_dispatch._reduce_ftff_pairs_by_resolved_stat_cost(
        ftff_pairs=pairs,
        base_stat_pairs=base_stat_pairs,
        gem_scale_fever=3,
        is_p_ft=1,
        is_s_ff=1,
    )

    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "4")
    monkeypatch.setenv("METAFINDER_CPU_WORK_MODE", "thread")
    monkeypatch.setenv("METAFINDER_CPU_PARALLEL_MIN_PAIRS", "1")
    monkeypatch.setenv("METAFINDER_CPU_PARALLEL_ITEMS_PER_WORKER", "32")
    parallel = gpu_dispatch._reduce_ftff_pairs_by_resolved_stat_cost(
        ftff_pairs=pairs,
        base_stat_pairs=base_stat_pairs,
        gem_scale_fever=3,
        is_p_ft=1,
        is_s_ff=1,
    )

    assert parallel == serial


def test_resolved_window_pair_filter_parallel_matches_serial(monkeypatch) -> None:
    ts = np.asarray([i * 0.075 for i in range(80)], dtype=np.float32)
    pairs = [(ft, ff) for ft in range(35) for ff in range(35) if ft + ff <= 90]
    base_stat_pairs = [(0, 0), (60, 80), (120, 120)]
    calc_song = _calc_song(ts)
    refs = _ref_arrays()

    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "1")
    serial = gpu_dispatch._filter_ftff_pairs_by_resolved_window_max(
        ftff_pairs=pairs,
        base_stat_pairs=base_stat_pairs,
        calc_song=calc_song,
        ref_arrays=refs,
        max_windows=2,
        gem_scale_fever=3,
    )

    monkeypatch.setenv("METAFINDER_CPU_WORKERS", "4")
    monkeypatch.setenv("METAFINDER_CPU_WORK_MODE", "thread")
    monkeypatch.setenv("METAFINDER_CPU_PARALLEL_MIN_PAIRS", "1")
    monkeypatch.setenv("METAFINDER_CPU_PARALLEL_ITEMS_PER_WORKER", "32")
    parallel = gpu_dispatch._filter_ftff_pairs_by_resolved_window_max(
        ftff_pairs=pairs,
        base_stat_pairs=base_stat_pairs,
        calc_song=calc_song,
        ref_arrays=refs,
        max_windows=2,
        gem_scale_fever=3,
    )

    assert parallel == serial


def test_resolved_window_filter_streams_inside_genome_chunks_before_first_payload() -> None:
    import inspect

    body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    chunk_pos = body.index("while idx0 < n_sig:")
    reducer_pos = body.index("_reduce_ftff_pairs_by_resolved_stat_cost(", chunk_pos)
    filter_pos = body.index("_filter_ftff_pairs_by_resolved_window_max(", chunk_pos)
    payload_pos = body.index("fused_payload_batch.append(fused_payload)", chunk_pos)

    assert chunk_pos < reducer_pos < filter_pos < payload_pos
    assert "fg_resolved_pair_reduction_cache.get" in body
    assert body.find("_reduce_ftff_pairs_by_resolved_stat_cost(") == reducer_pos
    assert body.rfind("_filter_ftff_pairs_by_resolved_window_max(") == filter_pos
    assert "not first_gpu_submit_emitted" in body
    assert "FGFirstSubmitDelayMs" in body


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
