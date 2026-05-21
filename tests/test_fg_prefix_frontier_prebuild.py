import numpy as np


def _ref_arrays():
    rows = 161
    return {
        "Perfect Points": np.ones((rows,), dtype=np.float32),
        "Combo Multiplier": np.ones((rows,), dtype=np.float32),
        "Fever Multiplier": np.ones((rows,), dtype=np.float32),
        "Fever Fill Rate": np.ones((rows,), dtype=np.float32),
        "Fever Time": np.ones((rows,), dtype=np.float32),
    }


def _calc_song():
    return {
        "metadata": {"Song Name": "prebuild-test", "Long Notes": 0, "Last Note Time": 4.0},
        "song_data": {"timestamps": np.linspace(0.0, 4.0, 12, dtype=np.float32)},
    }


def test_fg_prefix_frontier_prebuild_builds_complete_grid_and_skips_disk_hits(tmp_path, monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import prefix_frontier_cache as cache
    from gear_optimizer.solver.taichi_gem.force_greats.prefix_frontier_prebuild import (
        _FG_PREFIX_FRONTIER_PREBUILD_DONE,
        prebuild_fg_prefix_frontier_cache,
    )

    monkeypatch.setenv("FG_PREFIX_FRONTIER_CACHE_DIR", str(tmp_path))
    with cache._FG_PREFIX_FRONTIER_LOCK:
        cache._FG_PREFIX_FRONTIER_CACHE.clear()
    _FG_PREFIX_FRONTIER_PREBUILD_DONE.clear()

    calc_song = _calc_song()
    refs = _ref_arrays()
    calls = []

    def fake_solve(genome_stats_arr, timestamps, great_candidates, long_notes, last_note_time, *, fg_tasks, n_sections, ref_arrays, **_kwargs):
        calls.append(np.asarray(genome_stats_arr, dtype=np.int32)[:, 5:7].copy())
        base_key = cache.fg_prefix_frontier_base_cache_key(
            timestamps=timestamps,
            great_candidate_timestamps=timestamps if great_candidates is None else great_candidates,
            total_notes=len(timestamps),
            long_notes=long_notes,
            n_sections=n_sections,
            ref_arrays=ref_arrays,
        )
        for row in np.asarray(genome_stats_arr, dtype=np.int32):
            key = cache.fg_prefix_frontier_cache_key(base_key, ft_idx=int(row[5]), ff_idx=int(row[6]))
            cache.save_fg_prefix_frontier_payload(
                key,
                cache.FgPrefixFrontierPayload(
                    signatures=np.zeros((1, 11), dtype=np.int32),
                    forced_counts=np.zeros((1, int(n_sections)), dtype=np.int32),
                    count=1,
                    n_sections=int(n_sections),
                ),
            )

    first = prebuild_fg_prefix_frontier_cache(
        calc_song,
        refs,
        n_sections_values=(1,),
        stat_max=2,
        chunk_size=4,
        solve_tasks_fn=fake_solve,
    )

    assert first.total == 9
    assert first.built == 9
    assert first.disk == 0
    assert [len(call) for call in calls] == [4, 4, 1]
    built_cells = {(int(row[0]), int(row[1])) for call in calls for row in call}
    assert built_cells == {(ft, ff) for ft in range(3) for ff in range(3)}

    calls.clear()
    _FG_PREFIX_FRONTIER_PREBUILD_DONE.clear()
    second = prebuild_fg_prefix_frontier_cache(
        calc_song,
        refs,
        n_sections_values=(1,),
        stat_max=2,
        chunk_size=4,
        solve_tasks_fn=fake_solve,
    )

    assert second.total == 9
    assert second.built == 0
    assert second.disk == 9
    assert calls == []
