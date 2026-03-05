"""
Taichi Runtime - Initialization and configuration for GPU backend.

This module handles:
- Taichi initialization with auto-detected backend (Metal on macOS, Vulkan elsewhere)
- Environment variable configuration (kernel profiler, block dim)
- Global initialization state
"""

from __future__ import annotations

import os
import sys
import threading
import taichi as ti
from ...core.fallback_monitor import warn_fallback

# ============================================================================
# INITIALIZATION STATE
# ============================================================================

_ti_initialized = False
_ti_lock = threading.RLock()
_printed_vulkan_device_hint = False


def is_initialized() -> bool:
    """Check if Taichi has been initialized."""
    return _ti_initialized


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception as exc:
        warn_fallback(
            "taichi_runtime.env_int",
            "invalid integer environment variable; using default",
            context={"key": name, "default": default},
            exc=exc,
        )
        return default


def _clamp_block_dim(x: int) -> int:
    # Conservative clamp; GPU backends typically like 64-512.
    if x < 1:
        return 1
    if x > 1024:
        return 1024
    return x


def _detect_backend() -> tuple:
    """
    Auto-detect the best GPU backend based on platform.

    Returns:
        tuple: (taichi_arch, backend_name)
    """
    if sys.platform == "darwin":
        return ti.metal, "Metal"
    else:
        return ti.vulkan, "Vulkan"


def _maybe_set_vulkan_visible_device() -> None:
    """
    Optional Vulkan device selection for hybrid/dual-GPU systems.

    Taichi's Vulkan backend will pick a default device if multiple adapters are present.
    You can force a specific device index (as seen by Taichi) via:
      - `TAICHI_VULKAN_VISIBLE_DEVICE=1`

    Notes:
    - This must run before `ti.init()`.
    - We intentionally only accept simple comma-separated integer lists to avoid
      crashing Taichi with unexpected strings.
    """
    raw = str(os.environ.get("TAICHI_VULKAN_VISIBLE_DEVICE", "") or "").strip()
    if not raw:
        return

    # Allow: "0", "1", "0,1"
    ok = True
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok.isdigit():
            ok = False
            break
    if not ok:
        print(f"[Taichi] Ignoring TAICHI_VULKAN_VISIBLE_DEVICE={raw!r} (expected device index like '1')")
        return

    try:
        import taichi._lib.core as ti_core

        ti_core.set_vulkan_visible_device(raw)
        print(f"[Taichi] Vulkan visible device override: {raw}")
    except Exception as exc:
        print(f"[Taichi] Failed to set Vulkan visible device ({type(exc).__name__}): {exc}")


def _maybe_print_vulkan_device_hint() -> None:
    """
    Best-effort hint for hybrid/dual-GPU systems where Taichi may pick an iGPU by default.

    We don't have a portable way to enumerate adapters from Taichi's public API, so we only
    suggest the existing env var and avoid changing behavior automatically.
    """
    global _printed_vulkan_device_hint
    if _printed_vulkan_device_hint:
        return
    _printed_vulkan_device_hint = True
    if str(os.environ.get("TAICHI_VULKAN_VISIBLE_DEVICE", "") or "").strip():
        return
    print(
        "[Taichi] Tip: on hybrid/dual-GPU systems, set TAICHI_VULKAN_VISIBLE_DEVICE=1 (or another index) "
        "to force the discrete GPU."
    )


# IMPORTANT: These are read when init_taichi() is called, so callers can
# set env vars before initialization.
def get_kernel_profiler_enabled() -> bool:
    return bool(_env_int("TAICHI_KERNEL_PROFILER", 0))


def get_block_dim() -> int:
    # Empirically good defaults for this workload are 256.
    return _clamp_block_dim(_env_int("TAICHI_BLOCK_DIM", 256))


def _get_offline_cache_dir() -> str:
    """
    Return a stable on-disk cache directory for Taichi's offline cache.

    Keeping this inside the repo `bin/` avoids writing into user profile
    locations and makes cache cleanup straightforward.
    """

    def _read_git_head_short(repo_root: str) -> str:
        """
        Best-effort read of current git commit short hash.

        We use this to avoid reusing stale/invalid offline caches across code changes
        (Taichi offline cache can occasionally get into a bad state after kernel edits).
        """
        try:
            head_path = os.path.join(repo_root, ".git", "HEAD")
            if not os.path.isfile(head_path):
                return "nogit"
            head = (open(head_path, "r", encoding="utf-8", errors="replace").read() or "").strip()
            if head.startswith("ref:"):
                ref = head.split(":", 1)[1].strip()
                ref_path = os.path.join(repo_root, ".git", *ref.split("/"))
                if os.path.isfile(ref_path):
                    sha = (open(ref_path, "r", encoding="utf-8", errors="replace").read() or "").strip()
                else:
                    packed = os.path.join(repo_root, ".git", "packed-refs")
                    sha = ""
                    if os.path.isfile(packed):
                        for line in open(packed, "r", encoding="utf-8", errors="replace"):
                            line = line.strip()
                            if not line or line.startswith("#") or line.startswith("^"):
                                continue
                            parts = line.split()
                            if len(parts) == 2 and parts[1] == ref:
                                sha = parts[0]
                                break
                sha = sha.strip()
            else:
                sha = head.strip()
            if len(sha) >= 7:
                return sha[:7]
        except Exception:
            pass
        return "nogit"

    try:
        # `.../gear_optimizer/solver/taichi_gem/runtime.py` -> repo root is 3 levels up.
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        cache_schema = "v2"
        raw_ver = getattr(ti, "__version__", "unknown") or "unknown"
        if isinstance(raw_ver, tuple):
            raw_ver = ".".join(str(x) for x in raw_ver)
        ti_ver = str(raw_ver)
        ti_ver = "".join((c if (c.isalnum() or c in "._-") else "_") for c in ti_ver).replace(".", "_")
        head = _read_git_head_short(repo_root)
        cache_dir = os.path.join(repo_root, "bin", "taichi_cache", cache_schema, f"ti_{ti_ver}", head)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    except Exception:
        # Fallback: let Taichi pick a default location.
        return "taichi_cache"


def init_taichi():
    """
    Initialize Taichi with auto-detected GPU backend.

    Called once by gpu_executor.py on the GPU thread, or lazily on first use.
    Uses f32 precision for performance (sufficient for score accuracy).

    Backend selection:
    - macOS: Metal
    - Windows/Linux: Vulkan
    """
    global _ti_initialized
    with _ti_lock:
        if _ti_initialized:
            return
        kernel_profiler = get_kernel_profiler_enabled()
        block_dim = get_block_dim()
        arch, backend_name = _detect_backend()

        if arch == ti.vulkan:
            _maybe_set_vulkan_visible_device()
            _maybe_print_vulkan_device_hint()

        init_kwargs = dict(
            arch=arch,
            default_fp=ti.f32,
            default_ip=ti.i32,
            kernel_profiler=kernel_profiler,
            default_gpu_block_dim=block_dim,
            # Huge win for repeated runs: avoid recompiling kernels each process.
            # This does not change algorithm results; it only caches compiled kernels on disk.
            offline_cache=True,
            offline_cache_file_path=_get_offline_cache_dir(),
        )
        try:
            ti.init(**init_kwargs)
        except Exception as e:
            # Be robust: if offline cache init fails for any reason, fall back to normal init.
            warn_fallback(
                "taichi_runtime.offline_cache",
                "offline-cache init failed; retrying Taichi init without offline cache",
                context={"backend": backend_name},
                exc=e,
            )
            try:
                print(f"[Taichi] Offline cache init failed ({type(e).__name__}: {e}); retrying without offline cache.")
            except Exception:
                pass
            init_kwargs.pop("offline_cache", None)
            init_kwargs.pop("offline_cache_file_path", None)
            ti.init(**init_kwargs)
        _ti_initialized = True
        kp = "on" if kernel_profiler else "off"
        print(
            f"[Taichi] Initialized with {backend_name} backend - f32 precision (kernel_profiler={kp}, block_dim={block_dim})"
        )

        if kernel_profiler:
            try:
                ti.profiler.clear_kernel_profiler_info()
            except Exception:
                pass


def reset_taichi(*, reason: str | None = None) -> None:
    """
    Hard-reset Taichi runtime (frees Vulkan/Metal resources).

    This is intended as a recovery path for backend/driver failures (e.g. Vulkan
    semaphore allocation failures) and for long-running sessions where driver
    resources may leak.
    """
    global _ti_initialized
    with _ti_lock:
        if reason:
            print(f"[Taichi] Resetting runtime: {reason}")

        if not _ti_initialized:
            return

        try:
            ti.sync()
        except Exception:
            pass

        try:
            ti.reset()
        except Exception:
            # If reset fails, we'll still mark as uninitialized and let callers try
            # to re-init; worst case they crash again but with a clearer log path.
            pass

        _ti_initialized = False
