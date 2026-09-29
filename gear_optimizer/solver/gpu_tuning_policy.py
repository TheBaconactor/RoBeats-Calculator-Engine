from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GaBatchRunsPlan:
    batch_runs: int
    max_runs_by_genomes: int
    num_runs: int
    override_applied: bool


def choose_ga_batch_runs(
    *,
    n_genomes: int,
    num_runs: int,
    max_genomes: int,
    batch_runs_override: int = 0,
) -> GaBatchRunsPlan:
    """Decide how many GA runs to co-batch into one dispatch.

    Batch width is sized by GENOME CAPACITY ONLY: the active population is
    ``batch_runs * n_genomes`` genomes, which must fit the ``MAX_GENOMES`` field
    pool. The eval-budget (``MAX_EVALS_PER_DISPATCH``) is intentionally NOT a
    factor here -- TDR/dispatch-length safety is owned downstream by the combo
    chunking inside ``ga_evaluate_prepared_population`` (``compute_ga_combo_chunk``
    + ``ga_finalize_warmstart_lane_best_kernel`` accumulating across combo chunks
    via ``chunk_best_key``, verified bit-exact across chunks). Folding the eval
    budget in here just splits one batch into smaller sequential dispatches that
    re-feed the prepare->evaluate window per generation, with no TDR benefit.

    The result is clamped to ``num_runs`` so we never co-batch more runs than the
    caller actually has. ``batch_runs_override`` (>0) forces a fixed batch width
    for tests/diagnostics; production passes 0 (auto).
    """
    n_genomes = int(n_genomes)
    num_runs = max(1, int(num_runs))
    max_genomes = max(1, int(max_genomes))
    batch_runs_override = int(batch_runs_override)

    max_runs_by_genomes = int(max_genomes // int(n_genomes)) if int(n_genomes) > 0 else 1
    if max_runs_by_genomes < 1:
        max_runs_by_genomes = 1

    batch_runs = min(int(num_runs), int(max_runs_by_genomes))
    if batch_runs < 1:
        batch_runs = 1

    override_applied = batch_runs_override > 0
    if override_applied:
        batch_runs = int(batch_runs_override)

    return GaBatchRunsPlan(
        batch_runs=int(batch_runs),
        max_runs_by_genomes=int(max_runs_by_genomes),
        num_runs=int(num_runs),
        override_applied=bool(override_applied),
    )


