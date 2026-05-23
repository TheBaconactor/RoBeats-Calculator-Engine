from __future__ import annotations


def warmup_force_greats_response_frontier_runtime_imports() -> None:
    """
    Load the ForceGreats response-frontier runtime module before per-song FG prep starts.

    Kernel compilation still happens on the first real response-frontier solve.
    """
    from gear_optimizer.solver.taichi_gem.force_greats import FgResponseFrontierSolveResult
    from gear_optimizer.solver.taichi_gem.force_greats import solve_force_greats_response_frontier_batch_gpu

    _ = (
        FgResponseFrontierSolveResult,
        solve_force_greats_response_frontier_batch_gpu,
    )
