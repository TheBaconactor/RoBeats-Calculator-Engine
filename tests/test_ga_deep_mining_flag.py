import os
import sys

import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_compute_dynamic_mutation_respects_deep_mining_flag():
    """
    Regression test: DeepMining must control BOTH:
    - generation extension (current_run_gens)
    - cache-hit driven mutation boost (current_mutation_rate)
    """
    from gear_optimizer.helpers.ga_helpers import compute_dynamic_mutation
    from gear_optimizer.data.models import GASettings
    from gear_optimizer.core.constants import GA_POPULATION_SIZE

    base_mutation = 0.275
    generation = 1
    gens_per_run = 25
    current_run_gens = gens_per_run
    cache_hits = GA_POPULATION_SIZE  # hit_ratio=1 -> exploration_boost should saturate

    settings_on = GASettings(
        db_seed_prob=0.5,
        fixed_seed_copies=0,
        memetic_elites=0,
        memetic_steps=0,
        memetic_top_gear=1,
        memetic_top_minis=1,
        multi_start=1,
        deep_mining_enabled=True,
        heuristic_mode="modern",
    )
    settings_off = GASettings(
        db_seed_prob=0.5,
        fixed_seed_copies=0,
        memetic_elites=0,
        memetic_steps=0,
        memetic_top_gear=1,
        memetic_top_minis=1,
        multi_start=1,
        deep_mining_enabled=False,
        heuristic_mode="modern",
    )

    mut_on, gens_on = compute_dynamic_mutation(
        base_mutation,
        cache_hits,
        generation,
        current_run_gens,
        gens_per_run,
        settings_on,
    )
    mut_off, gens_off = compute_dynamic_mutation(
        base_mutation,
        cache_hits,
        generation,
        current_run_gens,
        gens_per_run,
        settings_off,
    )

    assert gens_on == gens_per_run + cache_hits
    assert gens_off == gens_per_run

    assert mut_on > base_mutation
    assert mut_off == pytest.approx(base_mutation)


