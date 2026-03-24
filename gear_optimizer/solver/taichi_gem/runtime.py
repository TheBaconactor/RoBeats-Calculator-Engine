"""
Taichi Runtime - Initialization and configuration for GPU backend.

This module handles:
- Taichi initialization with auto-detected backend (Metal on macOS, Vulkan elsewhere)
- Environment variable configuration (kernel profiler, block dim)
- Global initialization state
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from ...core.fallback_monitor import warn_fallback
from ...core.output import (
    restore_native_stdio,
    restore_stderr,
    restore_stdout,
    suppress_native_stdio,
    suppress_stderr,
    suppress_stdout,
)

# ============================================================================
# INITIALIZATION STATE
# ============================================================================

_ti_initialized = False
_ti_lock = threading.RLock()
_printed_vulkan_device_hint = False
logger = logging.getLogger(__name__)


_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


def _taichi_verbose_enabled() -> bool:
    # Keep Taichi banners in explicit verbose mode only.
    try:
        if str(os.environ.get("METAFINDER_OUTPUT", "") or "").strip().lower() in _TRUTHY_ENV_VALUES:
            return True
        if str(os.environ.get("METAFINDER_VERBOSE", "") or "").strip().lower() in _TRUTHY_ENV_VALUES:
            return True
    except Exception:
        return False
    return False


# Taichi prints a version banner at import-time, and it bypasses Python-level stdout swapping.
# Import it under OS-level stdio suppression unless the user explicitly asked for verbose output.
_ti_import_guard = suppress_native_stdio(not _taichi_verbose_enabled())
try:
    import taichi as ti  # noqa: E402
finally:
    restore_native_stdio(_ti_import_guard)


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
        warn_fallback(
            "taichi_runtime.vulkan_visible_device",
            "ignoring invalid TAICHI_VULKAN_VISIBLE_DEVICE value",
            context={"value": raw},
        )
        return

    try:
        import taichi._lib.core as ti_core

        ti_core.set_vulkan_visible_device(raw)
    except Exception as exc:
        warn_fallback(
            "taichi_runtime.vulkan_visible_device",
            "failed to set TAICHI_VULKAN_VISIBLE_DEVICE",
            context={"value": raw},
            exc=exc,
        )


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
    logger.debug(
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

    def _sanitize_cache_token(token: str) -> str:
        cleaned = str(token or "").strip()
        if not cleaned:
            return ""
        # Keep directory names portable and predictable.
        cleaned = "".join((c if (c.isalnum() or c in "._-") else "_") for c in cleaned)
        # Defensive cap: avoid accidental extremely long paths.
        return cleaned[:64]

    def _read_taichi_gem_signature_short(repo_root: str) -> str:
        """
        Compute a stable signature for the Taichi kernel sources.

        Why not git HEAD?
        - Using HEAD invalidates the cache on every commit, even for doc-only changes,
          causing repeated ~minute-long Taichi/Vulkan warmup compiles.
        - Hashing the Taichi sources invalidates only when the kernel-related code changes,
          while still avoiding reuse of stale caches after kernel edits.
        """
        try:
            import hashlib

            taichi_root = os.path.join(repo_root, "gear_optimizer", "solver", "taichi_gem")
            if not os.path.isdir(taichi_root):
                return "nogit"

            # Hash file contents for stability across git checkouts (mtime changes are noisy on Windows).
            h = hashlib.blake2b(digest_size=16)
            paths: list[str] = []
            for root, dirs, files in os.walk(taichi_root):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    paths.append(os.path.join(root, f))
            for abs_path in sorted(paths):
                rel = os.path.relpath(abs_path, repo_root).replace("\\", "/")
                h.update(rel.encode("utf-8", errors="replace"))
                with open(abs_path, "rb") as fp:
                    for chunk in iter(lambda: fp.read(64 * 1024), b""):
                        h.update(chunk)
            return h.hexdigest()[:12]
        except Exception:
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
        env_key = _sanitize_cache_token(os.environ.get("TAICHI_OFFLINE_CACHE_KEY", ""))
        cache_key = env_key or _read_taichi_gem_signature_short(repo_root)
        cache_dir = os.path.join(repo_root, "bin", "taichi_cache", cache_schema, f"ti_{ti_ver}", cache_key)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    except Exception:
        # Fallback: let Taichi pick a default location.
        return "taichi_cache"


def _init_taichi_quietly(init_kwargs: dict) -> None:
    """Run `ti.init()` without leaking backend banners to the console."""
    if _taichi_verbose_enabled():
        ti.init(**init_kwargs)
        return
    old_stdout = suppress_stdout(True)
    old_stderr = suppress_stderr(True)
    native_guard = suppress_native_stdio(True)
    try:
        ti.init(**init_kwargs)
    finally:
        restore_native_stdio(native_guard)
        restore_stderr(old_stderr)
        restore_stdout(old_stdout)


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
            _init_taichi_quietly(init_kwargs)
        except Exception as e:
            # Be robust: if offline cache init fails for any reason, fall back to normal init.
            warn_fallback(
                "taichi_runtime.offline_cache",
                "offline-cache init failed; retrying Taichi init without offline cache",
                context={"backend": backend_name},
                exc=e,
            )
            init_kwargs.pop("offline_cache", None)
            init_kwargs.pop("offline_cache_file_path", None)
            _init_taichi_quietly(init_kwargs)
        _ti_initialized = True
        logger.debug(
            "[Taichi] Initialized with %s backend - f32 precision (kernel_profiler=%s, block_dim=%s)",
            backend_name,
            "on" if kernel_profiler else "off",
            block_dim,
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
            logger.debug("[Taichi] Resetting runtime: %s", reason)

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
