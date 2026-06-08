"""ForceGreats response-frontier helpers."""

from __future__ import annotations

__all__ = [
    "FgResponseFrontierPreparedBatch",
    "FgResponseFrontierPreparedPlan",
    "materialize_force_greats_response_frontier_plan_results",
    "prepare_force_greats_response_frontier_plan_for_ga_candidates",
    "run_force_greats_response_frontier_for_ga_candidates",
]


def __getattr__(name: str):
    if name in __all__:
        from . import response_frontier_adapter

        return getattr(response_frontier_adapter, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
