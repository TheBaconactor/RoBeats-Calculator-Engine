from __future__ import annotations

from types import SimpleNamespace

import pytest

from gear_optimizer.solver.taichi_gem.api import ga_operations


class _NoHostReadback:
    def to_numpy(self):
        raise AssertionError("GA unique count must remain on-device")


def test_ga_evaluate_keeps_unique_count_on_device(monkeypatch) -> None:
    calls: list[tuple[str, tuple[int, ...]]] = []

    fake_kernels = SimpleNamespace(
        ga_compute_exact_eval_rep_kernel=lambda *args: calls.append(("rep", args)),
        ga_build_unique_slot_table_kernel=lambda *args: calls.append(("slots", args)),
        ga_find_best_combo_warmstart_kernel=lambda *args: calls.append(("eval", args)),
        ga_finalize_warmstart_lane_best_kernel=lambda *args: calls.append(("finalize", args)),
        ga_scatter_dup_results_kernel=lambda *args: calls.append(("scatter", args)),
    )
    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", fake_kernels)
    monkeypatch.setattr(ga_operations, "_ensure_ftff_combo_tables", lambda *args, **kwargs: 5)
    monkeypatch.setattr(ga_operations, "_ga_eval_budget", lambda: 100)
    monkeypatch.setattr(
        ga_operations.fields,
        "ga_exact_eval_unique_count",
        _NoHostReadback(),
    )

    ga_operations.ga_evaluate_prepared_population(3, total_budget=90)

    assert calls[0] == ("rep", (3,))
    assert calls[1] == ("slots", (3,))
    eval_calls = [args for name, args in calls if name == "eval"]
    assert len(eval_calls) == 1
    assert eval_calls[0][0] == 3
    assert ("finalize", (3,)) in calls
    assert calls[-1] == ("scatter", (3,))


@pytest.mark.parametrize("n_genomes", [0, -1, ga_operations.fields.MAX_GENOMES + 1])
def test_ga_evaluate_rejects_invalid_population_without_dispatch(monkeypatch, n_genomes: int) -> None:
    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)

    with pytest.raises(ValueError, match="n_genomes out of range"):
        ga_operations.ga_evaluate_prepared_population(n_genomes, total_budget=90)
