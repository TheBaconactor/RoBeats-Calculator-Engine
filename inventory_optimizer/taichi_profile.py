from __future__ import annotations

from gear_optimizer.core.parsing import env_flag


def maybe_print_kernel_profile(*, label: str, enabled: bool) -> None:
    """
    Print and clear Taichi kernel profiler info when TAICHI_KERNEL_PROFILER=1.

    This is intentionally best-effort: profiling should never crash a run.
    """
    if not enabled:
        return
    if not env_flag("TAICHI_KERNEL_PROFILER"):
        return

    try:
        import taichi as ti

        ti.sync()
        print(f"\n[Taichi][KernelProfiler] {label}", flush=True)
        ti.profiler.print_kernel_profiler_info()
        try:
            ti.profiler.clear_kernel_profiler_info()
        except Exception:
            pass
    except Exception:
        pass
