"""
Taichi Runtime - Initialization and configuration for GPU backend.

This module handles:
- Taichi initialization with the Vulkan backend
- Environment variable configuration (kernel profiler, block dim)
- Global initialization state
"""

from __future__ import annotations

import logging
import os
import struct
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Iterator
from ...core.fallback_monitor import warn_fallback
from ...core.output import (
    restore_native_stdio,
    restore_stderr,
    restore_stdout,
    suppress_native_stdio,
    suppress_stderr,
    suppress_stdout,
)
from ...core.parsing import env_flag, env_int

# ============================================================================
# INITIALIZATION STATE
# ============================================================================

from gear_optimizer.core.parsing import env_get
_ti_initialized = False
_ti_lock = threading.RLock()
_printed_vulkan_device_hint = False
_offline_cache_dir: str | None = None
logger = logging.getLogger(__name__)


def _taichi_verbose_enabled() -> bool:
    # Keep Taichi banners in explicit verbose mode only.
    try:
        if env_flag("METAFINDER_OUTPUT"):
            return True
        if env_flag("METAFINDER_VERBOSE"):
            return True
    except Exception as e:
        logger.debug(f"runtime:_taichi_verbose_enabled: {e}")
        return False
    return False


# Taichi prints a version banner at import-time via Python's print().
# On Windows, spawned child processes can inherit an invalid console handle that makes
# print() raise OSError [WinError 1].  Suppress both the Python-level sys.stdout/stderr
# AND the OS-level fd 1/2 to cover both WindowsConsoleIO and native C writes.
_ti_suppress = not _taichi_verbose_enabled()
_ti_saved_stdout = suppress_stdout(_ti_suppress)
_ti_saved_stderr = suppress_stderr(_ti_suppress)
_ti_import_guard = suppress_native_stdio(_ti_suppress)
try:
    import taichi as ti  # noqa: E402
finally:
    restore_native_stdio(_ti_import_guard)
    restore_stderr(_ti_saved_stderr)
    restore_stdout(_ti_saved_stdout)
del _ti_suppress, _ti_saved_stdout, _ti_saved_stderr, _ti_import_guard


def is_initialized() -> bool:
    """Check if Taichi has been initialized."""
    return _ti_initialized




@contextmanager
def _file_lock(lock_path: Path, *, timeout_sec: float | None = None, poll_interval_sec: float = 0.01) -> Iterator[None]:
    """
    Best-effort cross-process file lock (Windows + POSIX).

    This is intentionally lightweight and only used for Taichi offline-cache
    warmup coordination during startup.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    timeout = None if timeout_sec is None else max(0.0, float(timeout_sec))
    deadline = time.monotonic() + timeout if timeout is not None else None
    try:
        if os.name == "nt":
            import msvcrt

            try:
                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                handle.seek(0)
            except Exception as e:
                logger.debug(f"runtime:_file_lock: {e}")
            while True:
                try:
                    # `msvcrt.locking(..., LK_LOCK, ...)` is not reliably blocking on Windows and can raise
                    # `EDEADLK` ("Resource deadlock avoided") under contention. Use a non-blocking lock and
                    # implement the wait loop ourselves for both bounded and unbounded cases.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring file lock for {lock_path}") from None
                    time.sleep(max(0.001, float(poll_interval_sec)))
        else:
            import fcntl

            while True:
                try:
                    flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if deadline is not None else 0)
                    fcntl.flock(handle.fileno(), flags)
                    break
                except BlockingIOError:
                    if deadline is None:
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring file lock for {lock_path}") from None
                    time.sleep(max(0.001, float(poll_interval_sec)))
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.debug(f"runtime:_file_lock: {e}")
        try:
            handle.close()
        except Exception as e:
            logger.debug(f"runtime:_file_lock: {e}")


@contextmanager
def offline_cache_lock(
    *,
    timeout_sec: float | None = None,
    poll_interval_sec: float = 0.01,
) -> Iterator[str]:
    """
    Cross-process lock keyed by the current Taichi offline-cache directory.

    Yields the resolved offline cache directory path.
    """
    cache_dir = str(_offline_cache_dir or _get_offline_cache_dir() or "").strip()
    if not cache_dir:
        # Nothing to lock; still yield a stable string for callers.
        yield ""
        return
    lock_path = Path(cache_dir) / ".metafinder_offline_cache.lock"
    with _file_lock(lock_path, timeout_sec=timeout_sec, poll_interval_sec=poll_interval_sec):
        yield cache_dir

def _clamp_block_dim(x: int) -> int:
    # Conservative clamp; GPU backends typically like 64-512.
    if x < 1:
        return 1
    if x > 1024:
        return 1024
    return x


def _detect_backend() -> tuple:
    """
    Return the production GPU backend.

    Returns:
        tuple: (taichi_arch, backend_name)
    """
    return ti.vulkan, "Vulkan"


def _maybe_set_vulkan_visible_device() -> None:
    """
    Optional Vulkan device selection for hybrid/dual-GPU systems.

    Taichi's Vulkan backend will pick a default device if multiple adapters are present.
    You can force a specific device index (as seen by Taichi) via:
      - `TAICHI_VULKAN_VISIBLE_DEVICE=1`
    Or ask RoBeats MetaFinder to auto-select the first discrete GPU via:
      - `TAICHI_VULKAN_VISIBLE_DEVICE=discrete`

    Notes:
    - This must run before `ti.init()`.
    - We intentionally only accept simple comma-separated integer lists to avoid
      crashing Taichi with unexpected strings.
    """

    def _enumerate_vulkan_physical_devices() -> list[dict[str, object]]:
        try:
            import ctypes

            if os.name == "nt":
                lib = ctypes.WinDLL("vulkan-1.dll")  # noqa: S404
            else:
                lib = ctypes.CDLL("libvulkan.so.1")  # noqa: S404
        except Exception as e:
            logger.debug(f"runtime:_enumerate_vulkan_physical_devices: {e}")
            return []

        VK_SUCCESS = 0
        VK_STRUCTURE_TYPE_APPLICATION_INFO = 0
        VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO = 1

        VkInstance = ctypes.c_void_p
        VkPhysicalDevice = ctypes.c_void_p

        class VkApplicationInfo(ctypes.Structure):
            _fields_ = [
                ("sType", ctypes.c_uint32),
                ("pNext", ctypes.c_void_p),
                ("pApplicationName", ctypes.c_char_p),
                ("applicationVersion", ctypes.c_uint32),
                ("pEngineName", ctypes.c_char_p),
                ("engineVersion", ctypes.c_uint32),
                ("apiVersion", ctypes.c_uint32),
            ]

        class VkInstanceCreateInfo(ctypes.Structure):
            _fields_ = [
                ("sType", ctypes.c_uint32),
                ("pNext", ctypes.c_void_p),
                ("flags", ctypes.c_uint32),
                ("pApplicationInfo", ctypes.c_void_p),
                ("enabledLayerCount", ctypes.c_uint32),
                ("ppEnabledLayerNames", ctypes.c_void_p),
                ("enabledExtensionCount", ctypes.c_uint32),
                ("ppEnabledExtensionNames", ctypes.c_void_p),
            ]

        try:
            vkCreateInstance = lib.vkCreateInstance
            vkCreateInstance.restype = ctypes.c_int32
            vkCreateInstance.argtypes = [
                ctypes.POINTER(VkInstanceCreateInfo),
                ctypes.c_void_p,
                ctypes.POINTER(VkInstance),
            ]

            vkDestroyInstance = lib.vkDestroyInstance
            vkDestroyInstance.restype = None
            vkDestroyInstance.argtypes = [VkInstance, ctypes.c_void_p]

            vkEnumeratePhysicalDevices = lib.vkEnumeratePhysicalDevices
            vkEnumeratePhysicalDevices.restype = ctypes.c_int32
            vkEnumeratePhysicalDevices.argtypes = [VkInstance, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]

            vkGetPhysicalDeviceProperties = lib.vkGetPhysicalDeviceProperties
            vkGetPhysicalDeviceProperties.restype = None
            vkGetPhysicalDeviceProperties.argtypes = [VkPhysicalDevice, ctypes.c_void_p]
        except Exception as e:
            logger.debug(f"runtime:_enumerate_vulkan_physical_devices: {e}")
            return []

        app = VkApplicationInfo(
            sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
            pNext=None,
            pApplicationName=b"robeats-metafinder",
            applicationVersion=1,
            pEngineName=b"metafinder",
            engineVersion=1,
            apiVersion=0,
        )
        ci = VkInstanceCreateInfo(
            sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            pNext=None,
            flags=0,
            pApplicationInfo=ctypes.cast(ctypes.pointer(app), ctypes.c_void_p),
            enabledLayerCount=0,
            ppEnabledLayerNames=None,
            enabledExtensionCount=0,
            ppEnabledExtensionNames=None,
        )

        inst = VkInstance()
        res = int(vkCreateInstance(ctypes.byref(ci), None, ctypes.byref(inst)))
        if res != VK_SUCCESS or not inst:
            return []

        try:
            count = ctypes.c_uint32(0)
            res = int(vkEnumeratePhysicalDevices(inst, ctypes.byref(count), None))
            if res != VK_SUCCESS or int(count.value) <= 0:
                return []
            n = int(count.value)
            arr = (VkPhysicalDevice * n)()
            res = int(vkEnumeratePhysicalDevices(inst, ctypes.byref(count), ctypes.cast(arr, ctypes.c_void_p)))
            if res != VK_SUCCESS:
                return []

            out: list[dict[str, object]] = []
            for i in range(n):
                buf = ctypes.create_string_buffer(4096)
                try:
                    vkGetPhysicalDeviceProperties(arr[i], ctypes.cast(buf, ctypes.c_void_p))
                except Exception as e:
                    logger.debug(f"runtime:_enumerate_vulkan_physical_devices: {e}")
                    continue

                try:
                    # VkPhysicalDeviceProperties starts with:
                    # apiVersion, driverVersion, vendorID, deviceID, deviceType, ...
                    api_v, drv_v, vendor_id, device_id, device_type = struct.unpack_from("<IIIII", buf.raw, 0)
                except Exception as e:
                    logger.debug(f"runtime:_enumerate_vulkan_physical_devices: {e}")
                    continue

                name_raw = bytes(buf.raw[20 : 20 + 256])
                name = name_raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
                out.append(
                    {
                        "index": int(i),
                        "name": str(name),
                        "device_type": int(device_type),
                        "vendor_id": int(vendor_id),
                        "device_id": int(device_id),
                        "api_version": int(api_v),
                        "driver_version": int(drv_v),
                    }
                )
            return out
        finally:
            try:
                vkDestroyInstance(inst, None)
            except Exception as e:
                logger.debug(f"runtime:_enumerate_vulkan_physical_devices: {e}")

    def _pick_first_discrete_index(devs: list[dict[str, object]]) -> int | None:
        # VkPhysicalDeviceType: 2 = DISCRETE_GPU
        for d in devs:
            try:
                if int(d.get("device_type", -1) or -1) == 2:
                    return int(d.get("index", 0) or 0)
            except Exception as e:
                logger.debug(f"runtime:_pick_first_discrete_index: {e}")
                continue
        return None

    raw = str(env_get("TAICHI_VULKAN_VISIBLE_DEVICE", "") or "").strip()
    auto_discrete = (not raw) or (raw.strip().lower() in {"discrete", "dgpu", "auto"})

    target = ""
    if auto_discrete:
        devs = _enumerate_vulkan_physical_devices()
        idx = _pick_first_discrete_index(devs)
        if idx is None:
            if raw:
                warn_fallback(
                    "taichi_runtime.vulkan_visible_device",
                    "TAICHI_VULKAN_VISIBLE_DEVICE requested discrete GPU but none were found; using default device",
                    context={"value": raw, "devices": devs},
                    fatal=False,
                )
            return
        target = str(idx)
        os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = target
    else:
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
                fatal=False,
            )
            return
        target = raw

    try:
        import taichi._lib.core as ti_core

        ti_core.set_vulkan_visible_device(target)
        if auto_discrete:
            try:
                print(f"[Taichi] Using TAICHI_VULKAN_VISIBLE_DEVICE={target}", flush=True)
            except Exception as e:
                logger.debug(f"runtime:_pick_first_discrete_index: {e}")
    except Exception as exc:
        warn_fallback(
            "taichi_runtime.vulkan_visible_device",
            "failed to set TAICHI_VULKAN_VISIBLE_DEVICE",
            context={"value": target},
            exc=exc,
            fatal=False,
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
    if str(env_get("TAICHI_VULKAN_VISIBLE_DEVICE", "") or "").strip():
        return
    logger.debug(
        "[Taichi] Tip: on hybrid/dual-GPU systems, set TAICHI_VULKAN_VISIBLE_DEVICE=discrete "
        "(or a specific index like 1) to force the discrete GPU."
    )


# IMPORTANT: These are read when init_taichi() is called, so callers can
# set env vars before initialization.
def get_kernel_profiler_enabled() -> bool:
    return bool(env_int("TAICHI_KERNEL_PROFILER", 0))


def get_block_dim() -> int:
    # Hardwired (was TAICHI_BLOCK_DIM): 256 is the worklog-proven best for this
    # workload; _clamp_block_dim keeps the Vulkan [1,1024] dispatch bound.
    return _clamp_block_dim(256)


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
        except Exception as e:
            logger.debug(f"runtime:_read_taichi_gem_signature_short: {e}")
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
        env_key = _sanitize_cache_token(env_get("TAICHI_OFFLINE_CACHE_KEY", ""))
        cache_key = env_key or _read_taichi_gem_signature_short(repo_root)
        cache_dir = os.path.join(repo_root, "bin", "taichi_cache", cache_schema, f"ti_{ti_ver}", cache_key)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    except Exception as e:
        # Fallback: let Taichi pick a default location.
        logger.debug(f"runtime:_read_taichi_gem_signature_short: {e}")
        return "taichi_cache"


def _init_taichi_quietly(init_kwargs: dict, *, force_verbose: bool = False) -> None:
    """Run `ti.init()` without leaking backend banners to the console."""
    if force_verbose or _taichi_verbose_enabled():
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
    global _offline_cache_dir
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
            _offline_cache_dir = str(init_kwargs.get("offline_cache_file_path") or "").strip() or None
        except Exception as e:
            logger.debug(f"runtime:init_taichi: {e}")
            _offline_cache_dir = None

        # Some Windows/Vulkan stacks are sensitive to concurrent Taichi/Vulkan initialization across
        # multiple spawned processes (dual-process in-flight). Serialize `ti.init()` per offline-cache
        # directory to avoid races in the Vulkan loader/driver and on-disk cache setup.
        def _taichi_init_lock():
            try:
                return offline_cache_lock(timeout_sec=None)
            except Exception as e:
                logger.debug(f"runtime:_taichi_init_lock: {e}")
                return nullcontext("")

        def _init_with_winerror_retry(kwargs: dict) -> None:
            try:
                _init_taichi_quietly(kwargs)
            except OSError as exc:
                # Windows ERROR_INVALID_FUNCTION (1) is commonly surfaced when a library attempts to query
                # console properties (e.g., terminal size/mode) while stdout/stderr are redirected. In that
                # case, retry once without stdio suppression so Taichi can perform any console checks.
                if int(getattr(exc, "winerror", 0) or 0) == 1 and not _taichi_verbose_enabled():
                    _init_taichi_quietly(kwargs, force_verbose=True)
                    return
                raise

        try:
            with _taichi_init_lock():
                _init_with_winerror_retry(init_kwargs)
        except Exception as e:
            # Be robust: if offline cache init fails for any reason, fall back to normal init.
            warn_fallback(
                "taichi_runtime.offline_cache",
                "offline-cache init failed; retrying Taichi init without offline cache",
                context={"backend": backend_name},
                exc=e,
                fatal=False,
            )
            init_kwargs.pop("offline_cache", None)
            init_kwargs.pop("offline_cache_file_path", None)
            with _taichi_init_lock():
                _init_with_winerror_retry(init_kwargs)
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
            except Exception as e:
                logger.debug(f"runtime:_init_with_winerror_retry: {e}")


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
        except Exception as e:
            logger.debug(f"runtime:reset_taichi: {e}")

        try:
            ti.reset()
        except Exception as e:
            # If reset fails, we'll still mark as uninitialized and let callers try
            # to re-init; worst case they crash again but with a clearer log path.
            logger.debug(f"runtime:reset_taichi: {e}")

        _ti_initialized = False
