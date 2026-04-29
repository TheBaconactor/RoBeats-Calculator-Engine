from __future__ import annotations

import configparser

from tools.bench.bench_cem_hybrid_ab import compare_payloads, write_mode_config


def _payload(*, base: float, fg: float, dup: float, debt: float) -> dict:
    return {
        "depths": [25],
        "summary_by_depth": {
            "25": {
                "base_score": {"mean": base},
                "fg_score": {"mean": fg},
                "duplicate_genome_ratio": {"mean": dup},
                "pending_fg_jobs_song_delta": {"max": debt},
            }
        },
    }


def test_compare_payloads_reports_cem_score_and_duplicate_deltas() -> None:
    rows = compare_payloads(
        _payload(base=100.0, fg=120.0, dup=0.20, debt=0.0),
        _payload(base=105.0, fg=119.0, dup=0.12, debt=1.0),
    )

    assert rows == [
        {
            "depth": 25,
            "standard_base_mean": 100.0,
            "cem_base_mean": 105.0,
            "base_delta": 5.0,
            "best_observed_base_mean": 105.0,
            "standard_base_gap_to_best_observed": 5.0,
            "cem_base_gap_to_best_observed": 0.0,
            "standard_fg_mean": 120.0,
            "cem_fg_mean": 119.0,
            "fg_delta": -1.0,
            "best_observed_fg_mean": 120.0,
            "standard_fg_gap_to_best_observed": 0.0,
            "cem_fg_gap_to_best_observed": 1.0,
            "standard_duplicate_genome_ratio_mean": 0.2,
            "cem_duplicate_genome_ratio_mean": 0.12,
            "duplicate_genome_ratio_delta": -0.08000000000000002,
            "standard_pending_fg_debt_max": 0.0,
            "cem_pending_fg_debt_max": 1.0,
            "pending_fg_debt_delta": 1.0,
            "base_not_worse": True,
            "cem_closer_to_best_base": True,
            "fg_not_worse": False,
            "cem_closer_to_best_fg": False,
            "duplicates_lower": True,
            "fg_debt_not_worse": False,
        }
    ]


def test_write_mode_config_sets_cem_keys(tmp_path) -> None:
    base = tmp_path / "base.ini"
    base.write_text("[IterationEngine]\nGPU_GA_SearchMode = standard\n", encoding="utf-8")

    out = write_mode_config(
        base_config_path=base,
        out_dir=tmp_path / "out",
        mode="cem_hybrid",
        cem_tail_replace_frac=0.15,
        cem_refresh_every=10,
        cem_elite_frac=0.2,
        cem_smoothing=0.5,
        cem_min_prob=0.01,
        trash_suppression=True,
        breakpoint_mutation_bias=True,
    )

    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(out, encoding="utf-8")

    assert cfg.get("IterationEngine", "GPU_GA_SearchMode") == "cem_hybrid"
    assert cfg.get("IterationEngine", "GPU_GA_CEMTailReplaceFrac") == "0.15"
    assert cfg.get("IterationEngine", "GPU_GA_CEMRefreshEvery") == "10"
    assert cfg.get("IterationEngine", "GPU_GA_TrashSuppression") == "true"
    assert cfg.get("IterationEngine", "GPU_GA_BreakpointMutationBias") == "true"
