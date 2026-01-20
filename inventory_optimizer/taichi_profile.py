from __future__ import annotations

import os


def _truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "0") or "").strip().lower() in {"1", "true", "yes", "on"}


def maybe_print_kernel_profile(*, label: str, enabled: bool) -> None:
    """
    Print and clear Taichi kernel profiler info when TAICHI_KERNEL_PROFILER=1.

    This is intentionally best-effort: profiling should never crash a run.
    """
    if not enabled:
        return
    if not _truthy_env("TAICHI_KERNEL_PROFILER"):
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
