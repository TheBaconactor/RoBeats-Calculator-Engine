from gear_optimizer.pipeline.post_processor_fg_variants import (
    best_fg_improving_score_from_variants,
)


def test_best_fg_improving_score_requires_forced_greats_and_improvement():
    variants = [
        {"data": {}, "score": 10, "fg_score": 999},
        {"data": {"ForceGreats": {"config": {"early": 0, "late": 0}}}, "score": 10, "fg_score": 999},
        {"data": {"ForceGreats": {"config": {"early": 1}}}, "score": 100, "fg_score": 100},
        {"data": {"ForceGreats": {"config": {"early": 1}}}, "score": 10, "base_score": 200, "fg_score": 150},
        {"data": {"ForceGreats": {"config": {"early": 1}}}, "score": 100, "fg_score": 180},
        {"data": {"ForceGreats": {"config": {"early": 2}}}, "score": 100, "fg_score": 170},
    ]

    assert best_fg_improving_score_from_variants(variants) == 180
