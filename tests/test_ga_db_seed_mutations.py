from __future__ import annotations

import configparser
import random


def test_ga_settings_reads_db_seed_mutations():
    from gear_optimizer.data.models import GASettings

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GA_DBSeedProbability", "0.5")
    cfg.set("IterationEngine", "GA_FixedSeedCopies", "2")
    cfg.set("IterationEngine", "GA_DBSeedMutations", "3")

    settings = GASettings.from_cfg(cfg)
    assert settings.db_seed_mutations == 3


def test_build_initial_population_db_seed_mutations_controls_injection_count():
    from gear_optimizer.data.models import GASettings
    from gear_optimizer.helpers.ga_helpers.population import build_initial_population

    random.seed(0)

    def create_random_genome():
        return ["R"]

    def create_heuristic_genome():
        return ["H"]

    def reconstruct_genome_from_db_list(seed_list):
        return list(seed_list)

    def build_seed_list_from_record(_db_seed):
        return [1, 2, 3]

    mut_counter = {"i": 0}

    def mutate_genome_once(genome):
        mut_counter["i"] += 1
        return list(genome) + [mut_counter["i"]]

    ga_settings = GASettings(
        db_seed_prob=1.0,
        fixed_seed_copies=0,
        memetic_elites=0,
        memetic_steps=0,
        memetic_top_gear=1,
        memetic_top_minis=1,
        multi_start=1,
        deep_mining_enabled=False,
        db_seed_mutations=3,
    )

    pop = build_initial_population(
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
        db_seed={"score": 123},
        ga_settings=ga_settings,
        fixed_gear=[],
        fixed_minis=[],
        force_db_seed=False,
    )

    assert pop[0] == [1, 2, 3]
    assert pop[1] == [1, 2, 3, 1]
    assert pop[2] == [1, 2, 3, 2]
    assert pop[3] == [1, 2, 3, 3]

