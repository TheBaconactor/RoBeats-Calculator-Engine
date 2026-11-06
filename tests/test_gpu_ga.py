"""The GPU GA through gpu.ga.run_ga, and its kernels' invariants. Everything here is checked to the bit: the gate proves
equality across commits, these prove what it does not (no comparison against a former self)."""

import numpy as np
import pytest
import taichi as ti

from gear_optimizer.gpu import device, fields, ga, kernels
from gear_optimizer.gpu.kernels import _solve_combo
from gear_optimizer.gpu.scoring import GpuColorFlags, exact_gem_search, gpu_color_flags
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX
from gear_optimizer.solver.ga_selection import select_ga_loadouts
from tests.gpu_support import PRIMARY, SECONDARY, ga_inputs, registry, song

pytestmark = pytest.mark.gpu


def _run(inputs, seed: int = 7) -> np.ndarray:
    return ga.run_ga(inputs, seed, lambda: False)


def test_a_table_repeats_exactly_and_holds_what_the_host_computes():
    inputs = ga_inputs(num_runs=3)
    table = _run(inputs)
    np.testing.assert_array_equal(_run(inputs), table)
    assert table.shape == (3, fields.GA_FG_CANDIDATES_PER_RUN + 1, fields.GA_FG_CANDIDATE_COLS)
    columns = [0, 1, 2, COLOR_TO_STAT_INDEX[PRIMARY], COLOR_TO_STAT_INDEX[SECONDARY], 3, 4]
    rows = table.reshape(-1, table.shape[-1])
    rows = rows[rows[:, 0] > 0]
    assert len(rows) > 3
    np.testing.assert_array_equal(rows[:, 10], rows[:, 0])  # the result row's score
    np.testing.assert_array_equal(
        rows[:, 17:24], (inputs.base_fixed_stats_arr + inputs.item_stats[rows[:, 1:10]].sum(axis=1))[:, columns]
    )
    assert np.all(np.diff(rows[:, 7:10], axis=1) >= 0), "minis sorted"
    assert np.all(rows[:, 11:17].sum(axis=1) == GEM_BUDGET), "every gem spent"
    for run in table:
        assert run[0, 0] >= run[1:, 0].max(), "row 0 is the run's best"
        assert np.all(np.diff(run[1:, 0]) <= 0), "the population rows go down in score"


def test_a_polished_best_has_no_better_neighbor():
    inputs = ga_inputs(num_runs=1, generations=2)
    best = _run(inputs)[0, 0]
    polished = best[1:10]
    from gear_optimizer.solver.genetic_pipeline import one_swap_neighborhood

    neighbors = one_swap_neighborhood(polished, inputs.slot_start, inputs.slot_count, 9)
    n = min(len(neighbors), fields.MAX_GENOMES)
    flags = gpu_color_flags(inputs.color_flags)
    kernels.load_population_kernel(np.ascontiguousarray(neighbors[:n], dtype=np.int32), n)
    ga._evaluate(n, flags, device.upload_shortlist(inputs.ftff_shortlist))
    scores = (fields.chunk_best_key.to_numpy()[:n] >> np.uint64(32)).astype(np.int64) - 1
    assert scores.max() <= best[0]


def test_the_batch_width_changes_nothing(monkeypatch):
    inputs = ga_inputs(num_runs=6, n_genomes=32)
    monkeypatch.setattr(ga, "_BATCH_GENOMES", 6 * 32)
    whole = _run(inputs)
    monkeypatch.setattr(ga, "_BATCH_GENOMES", 2 * 32)
    np.testing.assert_array_equal(_run(inputs), whole)


def test_a_seed_changes_the_search():
    inputs = ga_inputs()
    assert not np.array_equal(_run(inputs, seed=1), _run(inputs, seed=2))


def test_the_memo_serves_a_repeated_population_and_ends_with_the_song():
    first, second = ga_inputs(song(name="First")), ga_inputs(song(n_notes=80, name="Second"))
    device.ensure_ready()
    fields.ga_eval_cache_key.fill(0)
    device.hard_reset("a fresh memo")
    fresh = _run(second)
    _run(first)
    np.testing.assert_array_equal(_run(second), fresh)
    flags = gpu_color_flags(second.color_flags)
    shortlist = device.upload_shortlist(second.ftff_shortlist)
    ga._evaluate(16, flags, shortlist)
    ga._evaluate(16, flags, shortlist)
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 0


def test_a_clone_population_breeds_children_and_keeps_its_elite():
    device.ensure_ready()
    n_genomes = 32
    row = np.asarray([1, 10, 20, 30, 40, 50, 60, 61, 62], dtype=np.int32)
    device.upload_items(
        np.zeros((128, fields.ITEM_STAT_DIM), dtype=np.int32),
        np.asarray([1, 10, 20, 30, 40, 50, 60, 60, 60], dtype=np.int32),
        np.asarray([8, 8, 8, 8, 8, 8, 20, 20, 20], dtype=np.int32),
        np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32),
    )
    kernels.start_batch_kernel(0, 1, n_genomes, 123, 0)
    kernels.load_population_kernel(np.tile(row, (n_genomes, 1)), n_genomes)
    keys = np.zeros(fields.MAX_GENOMES, dtype=np.uint64)
    keys[:n_genomes] = np.arange(n_genomes + 1, 1, -1, dtype=np.uint64) << np.uint64(32)
    fields.chunk_best_key.from_numpy(keys)
    fields.ga_run_best.fill(0)
    kernels.next_generation_kernel(0, 1, n_genomes)
    population = fields.population_indices.to_numpy()[:n_genomes]
    np.testing.assert_array_equal(population[0], row)
    assert len({tuple(genome) for genome in population.tolist()}) > 1


def _prepare_memo(stats):
    device.ensure_ready()
    values = np.zeros((fields.MAX_GENOMES, 7), dtype=np.int16)
    values[: len(stats)] = stats
    fields.genome_base_stats.from_numpy(values)
    fields.chunk_best_key.fill(0)
    fields.chunk_best_results.fill(0)
    kernels.find_representatives_kernel(len(stats))
    kernels.list_unique_rows_kernel(len(stats))
    return fields.ga_exact_eval_rep_idx.to_numpy()[: len(stats)]


def _publish(n):
    keys = np.zeros(fields.MAX_GENOMES, dtype=np.uint64)
    keys[:n] = ((np.arange(n, dtype=np.uint64) + 123) << 32) | np.arange(n, dtype=np.uint64)
    gems = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    gems[:n] = np.arange(n * 4).reshape(n, 4)
    fields.chunk_best_key.from_numpy(keys)
    fields.chunk_best_results.from_numpy(gems)
    kernels.scatter_results_kernel(n)
    return fields.chunk_best_key.to_numpy()[:n], fields.chunk_best_results.to_numpy()[:n]


def _unique_rows() -> int:
    return int(fields.ga_exact_eval_unique_count.to_numpy()[0])


def _empty_memo():
    device.ensure_ready()
    fields.ga_eval_cache_key.fill(0)


def test_all_seven_stats_tell_misses_from_duplicates():
    _empty_memo()
    stats = np.tile(np.array([-10, 0, 160, 32767, -32768, 19, 80]), (9, 1))
    for col in range(7):
        stats[col + 1, col] += -1 if col == 3 else 1
    np.testing.assert_array_equal(_prepare_memo(stats), [0, 1, 2, 3, 4, 5, 6, 7, 0])
    keys, gems = _publish(9)
    assert keys[8] == keys[0]
    np.testing.assert_array_equal(gems[8], gems[0])
    _prepare_memo(stats[[0, 8]])
    assert _unique_rows() == 0
    np.testing.assert_array_equal(fields.chunk_best_key.to_numpy()[:2], keys[[0, 8]])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[:2], gems[[0, 8]])


def test_a_memo_collision_never_reuses_another_stat_tuple():
    _empty_memo()
    a, b = [0] * 7, [0] * 6 + [16384]  # FNV's low 14 bits collide when the final input differs by 2**14.
    _prepare_memo([a])
    a_keys, a_gems = _publish(1)
    _prepare_memo([b])
    assert _unique_rows() == 1
    assert int(fields.chunk_best_key.to_numpy()[0]) == 0
    # Simultaneous colliding misses publish exactly one coherent winner.
    fields.ga_eval_cache_key.fill(0)
    _prepare_memo([a, b])
    _publish(2)
    _prepare_memo([b, a])
    assert _unique_rows() == 1
    assert int(fields.chunk_best_key.to_numpy()[0]) == 0
    assert int(fields.chunk_best_key.to_numpy()[1]) == int(a_keys[0])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[1], a_gems[0])


def test_a_missing_winner_is_never_cached():
    _empty_memo()
    _prepare_memo([[0] * 7])
    kernels.scatter_results_kernel(1)
    _prepare_memo([[0] * 7])
    assert _unique_rows() == 1


def test_a_full_population_of_collisions_keeps_keys_and_gems_together():
    _empty_memo()
    n = fields.MAX_GENOMES
    indices = np.arange(n)
    stats = np.zeros((n, 7), dtype=np.int16)
    stats[:, 6] = indices // 2 + (indices % 2) * 16384  # Every adjacent pair shares a bucket.
    np.testing.assert_array_equal(_prepare_memo(stats), indices)
    keys, gems = _publish(n)
    _prepare_memo(stats[::-1])
    restored = fields.chunk_best_key.to_numpy()[:n]
    hits = restored != 0
    assert int(hits.sum()) == (n + 1) // 2
    assert _unique_rows() == n // 2
    np.testing.assert_array_equal(restored[hits], keys[::-1][hits])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[:n][hits], gems[::-1][hits])


def test_a_runtime_reset_discards_the_memo():
    _prepare_memo([[0] * 7])
    _publish(1)
    assert np.any(fields.ga_eval_cache_key.to_numpy())
    device.hard_reset("test")
    _prepare_memo([[0] * 7])
    assert _unique_rows() == 1
    assert not np.any(fields.ga_eval_cache_key.to_numpy())


def _exhaustive_winners(n_genomes: int, flags) -> tuple[np.ndarray, np.ndarray]:
    """Every combo within the genome's gem limits, without a cull: the winners search_combos_kernel must find."""
    n_combos = fields.MAX_FTFF_COMBOS
    lanes = fields.GA_FTFF_LANES

    @ti.kernel
    def exhaustive(n_genomes: ti.i32, n_combos: ti.i32, flags: GpuColorFlags):
        for tid in range(n_genomes * lanes):
            genome = tid // lanes
            lane = tid - genome * lanes
            fields.ga_lane_best_key[genome, lane] = ti.u64(0)
            stats = ti.cast(fields.genome_base_stats[genome], ti.i32)
            max_ft: ti.i32 = ti.max(0, (MAX_STAT - stats[5]) // 3)
            max_ff: ti.i32 = ti.max(0, (MAX_STAT - stats[6]) // 3)
            best_key = ti.u64(0)
            best = ti.Vector([0, 0, 0, 0, 0], dt=ti.i32)
            combo: ti.i32 = lane
            while combo < n_combos:
                if fields.ftff_combo_ft[combo] <= max_ft and fields.ftff_combo_ff[combo] <= max_ff:
                    result = _solve_combo(combo, flags, stats, 0)
                    if result[0] >= 0:
                        key = (ti.cast(result[0] + 1, ti.u64) << 32) | ti.cast(combo, ti.u64)
                        if key > best_key:
                            best_key = key
                            best = result
                combo += lanes
            fields.ga_lane_best_key[genome, lane] = best_key
            for i in ti.static(range(4)):
                fields.ga_lane_best_results[genome, lane, i] = best[1 + i]

    exhaustive(n_genomes, n_combos, flags)
    keys, gems = fields.ga_lane_best_key.to_numpy()[:n_genomes], fields.ga_lane_best_results.to_numpy()[:n_genomes]
    winners = keys.argmax(axis=1)
    rows = np.arange(n_genomes)
    return keys[rows, winners], gems[rows, winners]


def test_the_culled_shortlist_search_finds_the_exhaustive_winners_every_time():
    inputs = ga_inputs()
    n_genomes = 64
    device.ensure_ready()
    device.upload_timeline(inputs.timed_song.timeline_key, ga.build_or_load_timeline_frontier_payload(inputs.timed_song, inputs.curves).payload)
    device.upload_items(inputs.item_stats, inputs.slot_start, inputs.slot_count, inputs.base_fixed_stats_arr)
    fields.ga_init_heuristic_topk.from_numpy(np.ascontiguousarray(inputs.init_heuristic_topk, dtype=np.int32))
    kernels.start_batch_kernel(0, 1, n_genomes, 20260612, 0)
    flags = gpu_color_flags(inputs.color_flags)
    shortlist = device.upload_shortlist(inputs.ftff_shortlist)

    def search() -> tuple[np.ndarray, np.ndarray]:
        fields.ga_eval_cache_key.fill(0)
        ga._evaluate(n_genomes, flags, shortlist)
        return fields.chunk_best_key.to_numpy()[:n_genomes].copy(), fields.chunk_best_results.to_numpy()[:n_genomes].copy()

    keys, gems = search()
    assert np.count_nonzero(keys) == n_genomes
    again = search()  # the shared incumbent's atomic order must not reach the winner
    np.testing.assert_array_equal(again[0], keys)
    np.testing.assert_array_equal(again[1], gems)
    expected_keys, expected_gems = _exhaustive_winners(n_genomes, flags)
    np.testing.assert_array_equal(keys, expected_keys)
    np.testing.assert_array_equal(gems, expected_gems)


def test_a_table_selects_like_the_stored_surface_would():
    inputs = ga_inputs(num_runs=3)
    table = _run(inputs)
    from gear_optimizer.solver.ga_selection import effective_tables

    rank, sig = effective_tables(registry(), PRIMARY, SECONDARY)
    selection = select_ga_loadouts(table, rank, sig, 51)
    assert selection.best_score == selection.scores.max()
    assert len(selection.scores) == len({
        (tuple(sorted(rank[row[:6]].tolist())), tuple(sorted(sig[row[6:9]].tolist()))) for row in selection.genomes
    })


@ti.kernel
def _surface_rows(result: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    result[0] = exact_gem_search(0, 0, 0, 0, 0, 0, GpuColorFlags(*[0] * 12), 0, 0, 0, 0)[0]


def test_the_score_of_a_cell_is_its_best_surface():
    """Two retained surfaces of one cell: normal head + normal body is 2 x the first's; the second's fever body wins."""
    device.ensure_ready()
    fields.grid_head_len[0, 0] = 0
    fields.grid_frontier_count[0, 0] = 2
    fields.grid_frontier_offset[0, 0] = 0
    fields.grid_frontier_body_fever_pool[0] = 0
    fields.grid_frontier_body_normal_pool[0] = 1
    fields.grid_frontier_body_fever_pool[1] = 1
    fields.grid_frontier_body_normal_pool[1] = 0
    out = np.zeros(1, dtype=np.int32)
    _surface_rows(out)
    curves = ga.stat_curves().f32
    base = float(curves["Perfect Points"][0])
    combo, fever = float(curves["Combo Multiplier"][0]), float(curves["Fever Multiplier"][0])
    assert out[0] == int(np.float32(np.float32(base * combo) * fever))
    fields.grid_frontier_count[0, 0] = 0
