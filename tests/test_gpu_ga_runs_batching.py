import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_load_initial_populations_batch_roundtrip():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_initial_populations,
        ga_load_initial_populations_batch,
        ga_download_population_indices,
    )

    n_runs = 4
    n_genomes = 32
    n_slots = 9
    rng = np.random.default_rng(123)
    pops = rng.integers(0, 1000, size=(n_runs, n_genomes, n_slots), dtype=np.int32)

    ga_upload_initial_populations(pops, n_runs=n_runs, n_genomes=n_genomes, n_slots=n_slots)

    # Load runs [1, 2] into a contiguous active population.
    n_total = ga_load_initial_populations_batch(run_idx_start=1, n_runs=2, n_genomes_per_run=n_genomes, n_slots=n_slots)
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    expected = np.concatenate([pops[1], pops[2]], axis=0)
    assert np.array_equal(out, expected)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_run_buffer_config_restores_defaults_after_hard_reset():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready, hard_reset_taichi

    default_runs = int(fields.DEFAULT_MAX_GA_RUNS)
    default_genomes = int(fields.DEFAULT_MAX_GA_RUN_GENOMES)

    try:
        hard_reset_taichi(reason="test shrink ga run buffers")
        fields.configure_ga_run_buffers(max_runs=1, max_genomes=250)
        ensure_ready()

        assert int(fields.MAX_GA_RUNS) == 1
        assert int(fields.ga_fg_candidates_packed.shape[1]) == 1

        hard_reset_taichi(reason="test restore ga run buffers")
        ensure_ready()

        assert int(fields.MAX_GA_RUNS) == default_runs
        assert int(fields.MAX_GA_RUN_GENOMES) == default_genomes
        assert int(fields.ga_fg_candidates_packed.shape[1]) == default_runs
    finally:
        hard_reset_taichi(reason="test cleanup ga run buffers")


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_next_generation_fused_runs_matches_sequential():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_island_boundaries,
        ga_upload_population_indices,
        ga_seed_rng,
        ga_seed_rng_runs,
        ga_set_scores,
        ga_next_generation_fused,
        ga_next_generation_fused_runs,
        ga_download_population_indices,
    )

    n_runs = 2
    n_genomes = 32
    n_slots = 9
    n_total = n_runs * n_genomes
    n_islands = 4
    elites_per_island = 2

    rng = np.random.default_rng(123)

    # Build two disjoint populations (so cross-run mixing is detectable).
    pop0 = rng.integers(0, 10_000, size=(n_genomes, n_slots), dtype=np.int32)
    pop1 = rng.integers(100_000, 110_000, size=(n_genomes, n_slots), dtype=np.int32)

    # Ensure minis [6:9] are unique per genome (avoid uniqueness repair re-rolls).
    for g in range(n_genomes):
        pop0[g, 6] = 50_000 + (g * 3 + 0)
        pop0[g, 7] = 50_000 + (g * 3 + 1)
        pop0[g, 8] = 50_000 + (g * 3 + 2)

        pop1[g, 6] = 150_000 + (g * 3 + 0)
        pop1[g, 7] = 150_000 + (g * 3 + 1)
        pop1[g, 8] = 150_000 + (g * 3 + 2)

    scores0 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)
    scores1 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)

    island_boundaries = np.array([0, 8, 16, 24, 32], dtype=np.int32)

    # Sequential per-run execution.
    seq_out = []
    for pop, scores in [(pop0, scores0), (pop1, scores1)]:
        ga_upload_population_indices(pop, n_slots=n_slots)
        ga_set_scores(scores, n_genomes=n_genomes)
        ga_seed_rng(n_genomes, seed=42)
        ga_upload_island_boundaries(island_boundaries)
        ga_next_generation_fused(
            n_genomes=n_genomes,
            n_slots=n_slots,
            mutation_rate=0.0,
            immigrant_rate=0.0,
            tournament_k=3,
            n_islands=n_islands,
            elites_per_island=elites_per_island,
        )
        seq_out.append(ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots))

    # Batched execution.
    batched_pop = np.concatenate([pop0, pop1], axis=0)
    batched_scores = np.concatenate([scores0, scores1], axis=0)
    ga_upload_population_indices(batched_pop, n_slots=n_slots)
    ga_set_scores(batched_scores, n_genomes=n_total)
    ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=n_genomes, seed=42)
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=3,
        n_islands=n_islands,
        elites_per_island=elites_per_island,
    )
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    assert np.array_equal(out[:n_genomes], seq_out[0])
    assert np.array_equal(out[n_genomes:], seq_out[1])


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_next_generation_fused_runs_repairs_parent_clones():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_download_population_indices,
        ga_next_generation_fused_runs,
        ga_seed_rng_runs,
        ga_set_scores,
        ga_upload_item_stats,
        ga_upload_population_indices,
    )

    n_genomes = 32
    n_slots = 9
    row = np.asarray([1, 10, 20, 30, 40, 50, 60, 61, 62], dtype=np.int32)
    pop = np.tile(row, (n_genomes, 1)).astype(np.int32, copy=False)
    scores = np.arange(n_genomes, 0, -1, dtype=np.int32)
    item_stats = np.zeros((128, 10), dtype=np.int32)
    slot_start = np.asarray([1, 10, 20, 30, 40, 50, 60, 60, 60], dtype=np.int32)
    slot_count = np.asarray([8, 8, 8, 8, 8, 8, 20, 20, 20], dtype=np.int32)

    ga_upload_item_stats(item_stats, slot_start, slot_count)
    ga_upload_population_indices(pop, n_slots=n_slots)
    ga_set_scores(scores, n_genomes=n_genomes)
    ga_seed_rng_runs(n_runs=1, n_genomes_per_run=n_genomes, seed=123)
    ga_next_generation_fused_runs(
        n_runs=1,
        n_genomes_per_run=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=3,
        n_islands=1,
        elites_per_island=1,
        novelty_repair_attempts=2,
    )

    out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    unique_rows = {tuple(int(x) for x in out[i].tolist()) for i in range(n_genomes)}
    assert tuple(int(x) for x in out[0].tolist()) == tuple(int(x) for x in row.tolist())
    assert len(unique_rows) > 1


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_refresh_next_fused_runs_matches_separate_transition():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import (
        ga_download_population_indices,
        ga_next_generation_fused_runs,
        ga_refresh_scores_and_update_runs_best,
        ga_refresh_scores_update_runs_best_and_next_generation_fused_runs,
        ga_seed_rng_runs,
        ga_upload_population_indices,
    )
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready

    ensure_ready()
    if fields.chunk_best_key is None:
        pytest.skip("packed key path requires Vulkan-style chunk_best_key")

    n_runs = 2
    n_genomes = 32
    n_slots = 9
    n_total = n_runs * n_genomes
    n_islands = 4
    elites_per_island = 2

    rng = np.random.default_rng(321)
    pop0 = rng.integers(0, 10_000, size=(n_genomes, n_slots), dtype=np.int32)
    pop1 = rng.integers(100_000, 110_000, size=(n_genomes, n_slots), dtype=np.int32)
    for g in range(n_genomes):
        pop0[g, 6:9] = np.asarray([50_000 + g * 3, 50_001 + g * 3, 50_002 + g * 3], dtype=np.int32)
        pop1[g, 6:9] = np.asarray([150_000 + g * 3, 150_001 + g * 3, 150_002 + g * 3], dtype=np.int32)

    pop = np.concatenate([pop0, pop1], axis=0)
    scores = rng.integers(1, 1_000_000, size=(n_total,), dtype=np.int32)
    keys = (scores.astype(np.uint64) + np.uint64(1)) << np.uint64(32)

    def _stage_identical_inputs() -> None:
        ga_upload_population_indices(pop, n_slots=n_slots)
        ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=n_genomes, seed=99)

        key_buf = np.zeros((int(fields.MAX_GENOMES),), dtype=np.uint64)
        key_buf[:n_total] = keys
        fields.chunk_best_key.from_numpy(key_buf)

        payload = fields.ga_runs_payload_packed.to_numpy()
        payload[:n_runs, 0, 0] = np.iinfo(np.int32).max
        fields.ga_runs_payload_packed.from_numpy(payload)

    refresh_kwargs = {
        "run_idx_start": 0,
        "n_runs": n_runs,
        "n_genomes_per_run": n_genomes,
        "n_slots": n_slots,
        "total_budget": 90,
        "gem_scale_fever": 3,
    }
    next_kwargs = {
        "mutation_rate": 0.0,
        "immigrant_rate": 0.0,
        "tournament_k": 3,
        "n_islands": n_islands,
        "elites_per_island": elites_per_island,
    }

    _stage_identical_inputs()
    ga_refresh_scores_and_update_runs_best(**refresh_kwargs)
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes,
        n_slots=n_slots,
        **next_kwargs,
    )
    separate = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    _stage_identical_inputs()
    ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(**refresh_kwargs, **next_kwargs)
    fused = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    assert np.array_equal(fused, separate)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_island_migration_runs_matches_sequential():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_island_boundaries,
        ga_upload_population_indices,
        ga_set_scores,
        ga_island_migration,
        ga_island_migration_runs,
        ga_download_population_indices,
    )

    n_runs = 2
    n_genomes = 32
    n_slots = 9
    n_total = n_runs * n_genomes
    n_islands = 4
    migrate_count = 2

    rng = np.random.default_rng(123)

    pop0 = rng.integers(0, 10_000, size=(n_genomes, n_slots), dtype=np.int32)
    pop1 = rng.integers(100_000, 110_000, size=(n_genomes, n_slots), dtype=np.int32)
    scores0 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)
    scores1 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)

    island_boundaries = np.array([0, 8, 16, 24, 32], dtype=np.int32)

    # Sequential per-run migration.
    seq_out = []
    for pop, scores in [(pop0, scores0), (pop1, scores1)]:
        ga_upload_population_indices(pop, n_slots=n_slots)
        ga_set_scores(scores, n_genomes=n_genomes)
        ga_upload_island_boundaries(island_boundaries)
        ga_island_migration(n_genomes, n_islands, migrate_count, n_slots)
        seq_out.append(ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots))

    # Batched migration.
    batched_pop = np.concatenate([pop0, pop1], axis=0)
    batched_scores = np.concatenate([scores0, scores1], axis=0)
    ga_upload_population_indices(batched_pop, n_slots=n_slots)
    ga_set_scores(batched_scores, n_genomes=n_total)
    ga_island_migration_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes,
        n_islands=n_islands,
        migrate_count=migrate_count,
        n_slots=n_slots,
    )
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    assert np.array_equal(out[:n_genomes], seq_out[0])
    assert np.array_equal(out[n_genomes:], seq_out[1])
