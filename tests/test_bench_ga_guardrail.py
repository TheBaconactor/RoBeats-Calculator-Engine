from __future__ import annotations

from tools.bench.bench_ga_guardrail import compare_payloads


def _payload(
    *,
    base_mean: float = 100.0,
    fg_mean: float = 120.0,
    dup_mean: float = 0.01,
    fg_debt_max: float = 0.0,
    error_runs: int = 0,
    elapsed_mean: float = 5.0,
) -> dict:
    return {
        "song_name": "00 (Hard) by garlagan",
        "difficulty": "Hard",
        "depths": [6],
        "summary_by_depth": {
            "6": {
                "base_score": {"mean": base_mean},
                "fg_score": {"mean": fg_mean},
                "duplicate_genome_ratio": {"mean": dup_mean},
                "pending_fg_jobs_song_delta": {"max": fg_debt_max},
                "error_runs": error_runs,
                "elapsed_wall_sec": {"mean": elapsed_mean},
            }
        },
    }


def test_compare_payloads_passes_for_identical_metrics():
    baseline = _payload()
    candidate = _payload()

    result = compare_payloads(
        baseline,
        candidate,
        max_base_score_drop=0.0,
        max_fg_score_drop=0.0,
        max_duplicate_ratio_increase=0.0,
        max_fg_debt_increase=0.0,
        max_error_run_increase=0,
        max_elapsed_increase_pct=0.10,
    )

    assert result["pass"] is True
    assert result["findings"] == []


def test_compare_payloads_flags_base_score_regression():
    baseline = _payload(base_mean=100.0)
    candidate = _payload(base_mean=98.0)

    result = compare_payloads(
        baseline,
        candidate,
        max_base_score_drop=1.0,
        max_fg_score_drop=0.0,
        max_duplicate_ratio_increase=0.0,
        max_fg_debt_increase=0.0,
        max_error_run_increase=0,
        max_elapsed_increase_pct=0.10,
    )

    assert result["pass"] is False
    assert any(f["metric"] == "base_score.mean" for f in result["findings"])


def test_compare_payloads_flags_fg_debt_and_duplicate_regressions():
    baseline = _payload(dup_mean=0.01, fg_debt_max=0.0)
    candidate = _payload(dup_mean=0.03, fg_debt_max=2.0)

    result = compare_payloads(
        baseline,
        candidate,
        max_base_score_drop=0.0,
        max_fg_score_drop=0.0,
        max_duplicate_ratio_increase=0.005,
        max_fg_debt_increase=0.0,
        max_error_run_increase=0,
        max_elapsed_increase_pct=0.10,
    )

    assert result["pass"] is False
    metrics = {f["metric"] for f in result["findings"]}
    assert "duplicate_genome_ratio.mean" in metrics
    assert "pending_fg_jobs_song_delta.max" in metrics
