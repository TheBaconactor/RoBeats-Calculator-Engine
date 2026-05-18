from gear_optimizer.solver.native_inflight_orchestrator import build_ga_candidates_for_post


def test_build_ga_candidates_for_post_compacts_and_materializes_names():
    calls = {}

    def _selector(candidates, **kwargs):
        calls["selector_kwargs"] = kwargs
        return list(candidates)

    def _materializer(candidate, *, registry=None, mutate=False):
        calls["materializer_registry"] = registry
        calls["materializer_mutate"] = mutate
        return list(candidate.get("Gear") or []), list(candidate.get("Minis") or [])

    candidates = [
        {
            "Score": 10,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Stats": {"Perfect Points": 1}},
            "_fg_priority": 4,
            "loadout_hash": "hash-1",
            "Drop": "large",
        }
    ]

    out = build_ga_candidates_for_post(
        candidates,
        registry={"gear": "registry"},
        minis_by_name={"M1": {}},
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        limit=5,
        selector=_selector,
        materializer=_materializer,
    )

    assert calls["selector_kwargs"]["limit"] == 5
    assert calls["selector_kwargs"]["primary_color"] == "Rush"
    assert calls["materializer_registry"] == {"gear": "registry"}
    assert calls["materializer_mutate"] is False
    assert out == [
        {
            "Score": 10,
            "BaseScore": 10,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Stats": {"Perfect Points": 1}},
            "_fg_priority": 4,
            "loadout_hash": "hash-1",
        }
    ]


def test_build_ga_candidates_for_post_ignores_non_dict_candidates():
    out = build_ga_candidates_for_post(
        [{"Score": 1, "Data": {}}, "bad"],
        registry=None,
        minis_by_name=None,
        primary_color="",
        secondary_color="",
        selected_color="",
        selector=lambda candidates, **_kwargs: list(candidates),
        materializer=lambda candidate, **_kwargs: ([], []),
    )

    assert out == [
        {
            "Score": 1,
            "BaseScore": 1,
            "Gear": [],
            "Minis": [],
            "Data": {},
            "_fg_priority": 0,
            "loadout_hash": None,
        }
    ]
