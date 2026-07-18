from gear_optimizer.pipeline.post_processor_fg_variants import (
    best_fg_improving_score_from_persist_entries,
    best_fg_improving_score_from_variants,
    fg_variants_from_persist_entries,
)

SURFACE = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def test_best_fg_improving_score_requires_forced_greats_and_improvement():
    variants = [
        {"data": {}, "score": 10, "fg_score": 999},
        {"data": {"ForceGreats": {"config": {"early": 0, "late": 0}}}, "score": 10, "fg_score": 999},
        {"data": {"response_surface": SURFACE}, "score": 100, "fg_score": 100},
        {"data": {"response_surface": SURFACE}, "score": 10, "base_score": 200, "fg_score": 150},
        {"data": {"response_surface": SURFACE}, "score": 100, "fg_score": 180},
        {"data": {"response_surface": SURFACE}, "score": 100, "fg_score": 170},
    ]

    assert best_fg_improving_score_from_variants(variants) == 180


def test_fg_variants_from_persist_entries_preserves_replay_shape():
    variants = fg_variants_from_persist_entries(
        [
            {
                "details": {"ForceGreats": {"config": {"early": 1}}, "Stats": {"Rush": 5}},
                "gear": ["G1"],
                "minis": ["M1"],
                "score": 100,
                "fg_score": 130,
                "_is_ga": True,
            },
            {
                "details": {"Stats": {"Rush": 4}},
                "gear": ["G2"],
                "minis": [],
                "score": 90,
                "fg_score": 0,
            },
            "not an entry",
        ]
    )

    assert variants == [
        {
            "data": {"ForceGreats": {"config": {"early": 1}}, "Stats": {"Rush": 5}, "Score": 130},
            "gear": ["G1"],
            "minis": ["M1"],
            "score": 100,
            "fg_score": 130,
            "_is_ga": True,
        },
        {
            "data": {"Stats": {"Rush": 4}, "Score": 90},
            "gear": ["G2"],
            "minis": [],
            "score": 90,
            "fg_score": 0,
            "_is_ga": False,
        },
    ]


def test_best_fg_improving_score_from_persist_entries_requires_force_payload():
    entries = [
        {"score": 100, "fg_score": 200, "force": None},
        {"score": 100, "fg_score": 100, "force": {"response_surface": SURFACE}},
        {"score": 100, "fg_score": 175, "force": {"ForceGreats": {"config": {"early": 1}}}},
        {"score": 100, "fg_score": 190, "force": {"response_surface": SURFACE}},
        "not an entry",
    ]

    assert best_fg_improving_score_from_persist_entries(entries) == 190
