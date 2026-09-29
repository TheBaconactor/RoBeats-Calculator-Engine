from gear_optimizer.solver.gpu_tuning_policy import choose_ga_batch_runs


def test_choose_ga_batch_runs_production_shape_batches_all_runs_by_genome_capacity():
    # Production q24 geometry: 6 runs x 705 genomes. With MAX_GENOMES=4608 the
    # genome pool fits all 6 runs (6*705=4230 <= 4608), so the whole multistart
    # batches into a single dispatch. The eval budget is NOT a factor in sizing
    # (combo chunking owns TDR safety downstream).
    plan = choose_ga_batch_runs(
        n_genomes=705,
        num_runs=6,
        max_genomes=4608,
    )

    assert plan.max_runs_by_genomes == 6
    assert plan.batch_runs == 6
    assert plan.num_runs == 6
    assert plan.override_applied is False


def test_choose_ga_batch_runs_clamps_to_genome_capacity_below_num_runs():
    # If the genome pool cannot fit all runs at once, batch width is capped by
    # capacity (the batch loop then iterates the remaining runs sequentially).
    plan = choose_ga_batch_runs(
        n_genomes=705,
        num_runs=6,
        max_genomes=4096,  # only fits 5 runs (5*705=3525 <= 4096 < 4230)
    )

    assert plan.max_runs_by_genomes == 5
    assert plan.batch_runs == 5
    assert plan.override_applied is False


def test_choose_ga_batch_runs_clamps_to_num_runs_when_capacity_exceeds():
    # Genome capacity allows far more than num_runs; never co-batch more runs
    # than the caller actually has.
    plan = choose_ga_batch_runs(
        n_genomes=128,
        num_runs=3,
        max_genomes=65_536,
    )

    assert plan.max_runs_by_genomes == 512
    assert plan.batch_runs == 3
    assert plan.override_applied is False


def test_choose_ga_batch_runs_respects_positive_override():
    plan = choose_ga_batch_runs(
        n_genomes=128,
        num_runs=8,
        max_genomes=4096,
        batch_runs_override=3,
    )

    assert plan.max_runs_by_genomes == 32
    assert plan.batch_runs == 3
    assert plan.override_applied is True
