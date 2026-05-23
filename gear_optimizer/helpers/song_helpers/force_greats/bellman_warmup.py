from __future__ import annotations


def warmup_force_greats_bellman_runtime_imports() -> None:
    """
    Load the ForceGreats Bellman runtime module before per-song FG prep starts.

    Bellman warmup only imports the Bellman module; kernel compilation still
    happens on the first real fixed-stats solve.
    """
    from gear_optimizer.solver.taichi_gem.force_greats import FgBellmanFixedStatsResult
    from gear_optimizer.solver.taichi_gem.force_greats import solve_force_greats_bellman_fixed_stats_gpu

    _ = (
        FgBellmanFixedStatsResult,
        solve_force_greats_bellman_fixed_stats_gpu,
    )
