from __future__ import annotations

import configparser

import numpy as np

from gear_optimizer.helpers.ga_helpers.cem_hybrid import (
    CEMHybridSettings,
    apply_cem_config_to_cfg_data,
    build_cem_prior_tables,
    learn_cem_probability_tables,
    sample_cem_tail_population,
)


def _slot_layout() -> tuple[np.ndarray, np.ndarray, int]:
    slot_start = np.zeros((9,), dtype=np.int32)
    slot_count = np.zeros((9,), dtype=np.int32)
    next_id = 1
    for slot_idx in range(6):
        slot_start[slot_idx] = next_id
        slot_count[slot_idx] = 4
        next_id += 4
    for slot_idx in range(6, 9):
        slot_start[slot_idx] = next_id
        slot_count[slot_idx] = 6
    return slot_start, slot_count, next_id + 6


def test_cem_settings_default_to_standard_mode() -> None:
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg_data: dict[str, object] = {}

    apply_cem_config_to_cfg_data(cfg_data, cfg)
    settings = CEMHybridSettings.from_cfg_data(cfg_data)

    assert settings.search_mode == "standard"
    assert not settings.enabled
    assert settings.rare_item_protection is True


def test_cem_probability_update_keeps_floor_for_non_elite_items() -> None:
    slot_start, slot_count, n_items = _slot_layout()
    item_stats = np.zeros((n_items, 10), dtype=np.int32)
    settings = CEMHybridSettings(
        search_mode="cem_hybrid",
        elite_frac=0.25,
        smoothing=1.0,
        min_prob=0.05,
        refresh_every=1,
        tail_replace_frac=0.30,
        rare_item_protection=True,
    )
    prior = build_cem_prior_tables(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        settings=settings,
        primary_color="Rush",
        secondary_color="",
    )

    population = np.zeros((8, 9), dtype=np.int32)
    scores = np.arange(800, 0, -100, dtype=np.int32)
    for row_idx in range(population.shape[0]):
        for slot_idx in range(6):
            population[row_idx, slot_idx] = slot_start[slot_idx] + (0 if row_idx < 2 else row_idx % 4)
        population[row_idx, 6:9] = [slot_start[6], slot_start[6] + 1, slot_start[6] + 2]

    learned = learn_cem_probability_tables(
        population_indices=population,
        scores=scores,
        slot_start=slot_start,
        slot_count=slot_count,
        settings=settings,
        previous_tables=prior,
        prior_tables=prior,
        n_runs=1,
        n_genomes_per_run=8,
    )

    assert learned[0][0] > learned[0][1]
    assert float(np.min(learned[0])) > 0.0
    assert np.isclose(float(np.sum(learned[0])), 1.0)


def test_trash_suppression_is_weighting_not_deletion() -> None:
    slot_start, slot_count, n_items = _slot_layout()
    item_stats = np.zeros((n_items, 10), dtype=np.int32)
    best_hat = int(slot_start[0] + 3)
    item_stats[best_hat, 0] = 100
    settings = CEMHybridSettings(
        search_mode="cem_hybrid",
        min_prob=0.02,
        trash_suppression=True,
        rare_item_protection=True,
    )

    prior = build_cem_prior_tables(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        settings=settings,
        primary_color="Rush",
        secondary_color="",
    )

    assert prior[0][3] > prior[0][0]
    assert float(np.min(prior[0])) > 0.0
    assert np.isclose(float(np.sum(prior[0])), 1.0)


def test_cem_tail_sampling_preserves_minis_unique_when_possible() -> None:
    slot_start, slot_count, n_items = _slot_layout()
    item_stats = np.zeros((n_items, 10), dtype=np.int32)
    settings = CEMHybridSettings(
        search_mode="cem_hybrid",
        min_prob=0.01,
        tail_replace_frac=0.50,
        rare_item_protection=True,
    )
    tables = build_cem_prior_tables(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        settings=settings,
        primary_color="Rush",
        secondary_color="",
    )
    population = np.zeros((2, 12, 9), dtype=np.int32)
    for run_idx in range(2):
        for row_idx in range(12):
            for slot_idx in range(6):
                population[run_idx, row_idx, slot_idx] = slot_start[slot_idx]
            population[run_idx, row_idx, 6:9] = [slot_start[6], slot_start[6] + 1, slot_start[6] + 2]
    flat_population = population.reshape(24, 9)

    sampled, stats = sample_cem_tail_population(
        population_indices=flat_population,
        probability_tables=tables,
        slot_start=slot_start,
        slot_count=slot_count,
        settings=settings,
        rng=np.random.default_rng(123),
        n_runs=2,
        n_genomes_per_run=12,
        elite_preserve_count=2,
    )

    assert stats["replaced"] == 12
    for row in sampled.reshape(2, 12, 9)[:, -6:, :]:
        for genome in row:
            minis = [int(x) for x in genome[6:9]]
            assert len(set(minis)) == 3
