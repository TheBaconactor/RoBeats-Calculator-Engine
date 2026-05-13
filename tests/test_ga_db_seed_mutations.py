from __future__ import annotations

import configparser

import numpy as np
import pytest


def test_ga_evolution_settings_reads_db_seed_mutations():
    from gear_optimizer.data.models import GAEvolutionSettings

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GA_DBSeedProbability", "0.5")
    cfg.set("IterationEngine", "GA_FixedSeedCopies", "2")
    cfg.set("IterationEngine", "GA_DBSeedMutations", "3")

    settings = GAEvolutionSettings.from_cfg(cfg)
    assert settings.db_seed_mutations == 3


@pytest.mark.gpu
def test_gpu_initial_population_db_seed_mutations_controls_injection_count():
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.taichi_gem.api import ga_generate_initial_populations, ga_upload_item_stats

    orig_max_runs = gpu_fields.MAX_GA_RUNS
    orig_max_genomes = gpu_fields.MAX_GA_RUN_GENOMES
    try:
        gpu_fields.configure_ga_run_buffers(max_runs=2, max_genomes=16)

        # Build a minimal fake registry layout:
        # - 6 gear slots, 4 items each
        # - 3 mini slots share a pool of 5 items
        slot_start = np.zeros((9,), dtype=np.int32)
        slot_count = np.zeros((9,), dtype=np.int32)
        next_id = 1
        for s in range(6):
            slot_start[s] = next_id
            slot_count[s] = 4
            next_id += 4
        mini_start = next_id
        mini_count = 5
        for s in range(6, 9):
            slot_start[s] = mini_start
            slot_count[s] = mini_count
        n_items = int(mini_start + mini_count)
        item_stats = np.zeros((n_items, 10), dtype=np.int32)

        ga_upload_item_stats(item_stats, slot_start, slot_count)

        seed_ids = np.zeros((9,), dtype=np.int32)
        for s in range(6):
            seed_ids[s] = slot_start[s]
        seed_ids[6] = mini_start
        seed_ids[7] = mini_start + 1
        seed_ids[8] = mini_start + 2

        ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=2,
            n_genomes=16,
            n_slots=9,
            seed=123,
            heuristic_prob=0.0,
            heuristic_k=0,
            seed_prob=1.0,
            seed_copies=1,
            seed_mutations=3,
            heuristic_copies=0,
            seed_ids=seed_ids,
        )

        out = gpu_fields.ga_initial_populations.to_numpy()
        for r in range(2):
            assert np.array_equal(out[r, 0, :9], seed_ids)
            for g in range(1, 4):
                assert int(np.count_nonzero(out[r, g, :9] != seed_ids)) >= 1
    finally:
        gpu_fields.MAX_GA_RUNS = orig_max_runs
        gpu_fields.MAX_GA_RUN_GENOMES = orig_max_genomes
        gpu_fields.reset_fields_state()
