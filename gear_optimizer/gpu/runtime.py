"""The Taichi runtime: Vulkan device selection, initialization, the runtime lock, reset and its hooks."""

from __future__ import annotations

import hashlib
import logging
import os
import struct
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from gear_optimizer.core.file_lock import exclusive_file_lock
from gear_optimizer.core.output import quiet_stdio
from gear_optimizer import settings

_ti_initialized = False
# Whether THIS process has ever completed a Taichi materialization. Distinct from
# `_ti_initialized`, which `reset_taichi()` clears: the GLFW/Cocoa context that the first
# materialization acquires is process-global, so only that first one carries the macOS
# main-thread requirement. See `_assert_darwin_main_thread_materialization()`.
_ti_materialized_once = False
_ti_lock = threading.RLock()
_offline_cache_dir: str | None = None
_GPU_BLOCK_DIM = 256  # The benchmark-validated choice for these kernels (Vulkan allows 1..1024).
logger = logging.getLogger(__name__)

# Taichi prints a version banner at import time. On Windows, spawned child processes can inherit an invalid console
# handle that makes print() raise OSError [WinError 1]; quiet_stdio covers both Python-level and native writes.
with quiet_stdio(not settings.output_enabled()):
    import taichi as ti  # noqa: E402


def _assert_darwin_main_thread_materialization() -> None:
    """Refuse a process's first Taichi materialization off the macOS main thread: on darwin ti.vulkan lowers through
    MoltenVK, whose GLFW/Cocoa context AppKit hard-traps off the main thread, which kills the whole process. Later
    materializations (a reset's recovery) share that process-global context."""
    if sys.platform == "darwin" and not _ti_materialized_once and threading.current_thread() is not threading.main_thread():
        raise RuntimeError(
            "Taichi's GPU runtime must be materialized on the OS main thread on macOS, got thread "
            f"{threading.current_thread().name!r}: materialize during startup, before dispatching GPU work to threads."
        )


@contextmanager
def offline_cache_lock(*, timeout_sec: float | None = None) -> Iterator[str]:
    """Cross-process lock keyed by the Taichi offline-cache directory, which it yields."""
    cache_dir = _offline_cache_dir or _get_offline_cache_dir()
    with exclusive_file_lock(Path(cache_dir) / ".metafinder_offline_cache.lock", timeout_sec=timeout_sec):
        yield cache_dir


def _vulkan_device_types() -> list[int]:
    """Each Vulkan physical device's VkPhysicalDeviceType, in device-index order; empty without a system Vulkan
    loader (macOS reaches the GPU through Taichi's MoltenVK)."""
    import ctypes

    try:
        lib = ctypes.WinDLL("vulkan-1.dll") if os.name == "nt" else ctypes.CDLL("libvulkan.so.1")  # noqa: S404
    except OSError:
        return []

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

    create_instance = lib.vkCreateInstance
    create_instance.restype = ctypes.c_int32
    create_instance.argtypes = [ctypes.POINTER(VkInstanceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    destroy_instance = lib.vkDestroyInstance
    destroy_instance.restype = None
    destroy_instance.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    enumerate_devices = lib.vkEnumeratePhysicalDevices
    enumerate_devices.restype = ctypes.c_int32
    enumerate_devices.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    device_properties = lib.vkGetPhysicalDeviceProperties
    device_properties.restype = None
    device_properties.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    # sType 0/1 = VK_STRUCTURE_TYPE_APPLICATION_INFO / VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO; 0 = VK_SUCCESS.
    app = VkApplicationInfo(
        sType=0, pApplicationName=b"robeats-metafinder", applicationVersion=1, pEngineName=b"metafinder", engineVersion=1
    )
    create_info = VkInstanceCreateInfo(sType=1, pApplicationInfo=ctypes.cast(ctypes.pointer(app), ctypes.c_void_p))
    instance = ctypes.c_void_p()
    if create_instance(ctypes.byref(create_info), None, ctypes.byref(instance)) != 0 or not instance:
        return []
    try:
        count = ctypes.c_uint32(0)
        if enumerate_devices(instance, ctypes.byref(count), None) != 0 or count.value <= 0:
            return []
        devices = (ctypes.c_void_p * count.value)()
        if enumerate_devices(instance, ctypes.byref(count), ctypes.cast(devices, ctypes.c_void_p)) != 0:
            return []
        types = []
        for device in devices:
            properties = ctypes.create_string_buffer(4096)
            device_properties(device, ctypes.cast(properties, ctypes.c_void_p))
            # VkPhysicalDeviceProperties starts apiVersion, driverVersion, vendorID, deviceID, deviceType.
            types.append(struct.unpack_from("<I", properties.raw, 16)[0])
        return types
    finally:
        destroy_instance(instance, None)


def _select_vulkan_device() -> None:
    """Point Taichi's Vulkan backend at a device before ti.init().

    TAICHI_VULKAN_VISIBLE_DEVICE takes device indices ("1", "0,1"; anything else is ignored with a warning). Unset,
    "discrete", "dgpu" or "auto" select the first discrete GPU on hybrid/dual-GPU boxes, where Taichi's default
    device may be the integrated one.
    """
    raw = settings.vulkan_device()
    auto_discrete = not raw or raw.lower() in {"discrete", "dgpu", "auto"}
    if auto_discrete:
        # VkPhysicalDeviceType 2 = VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
        discrete = next((index for index, kind in enumerate(_vulkan_device_types()) if kind == 2), None)
        if discrete is None:
            if raw:
                logger.warning("[Taichi] TAICHI_VULKAN_VISIBLE_DEVICE=%s: no discrete GPU found; using the default", raw)
            return
        target = os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = str(discrete)
    elif all(token.strip().isdigit() for token in raw.split(",")):
        target = raw
    else:
        logger.warning("[Taichi] Ignoring invalid TAICHI_VULKAN_VISIBLE_DEVICE=%r", raw)
        return
    try:
        import taichi._lib.core as ti_core

        ti_core.set_vulkan_visible_device(target)
        if auto_discrete:
            print(f"[Taichi] Using TAICHI_VULKAN_VISIBLE_DEVICE={target}", flush=True)
    except Exception:
        # Device selection only steers hybrid-GPU boxes; Taichi falls back to its default device.
        logger.warning("[Taichi] Could not select Vulkan device %s", target, exc_info=True)


def _get_offline_cache_dir() -> str:
    """<engine>/bin/taichi_cache/v2/ti_<version>/<key>, created; the key hashes this package's sources (paths and
    contents), so only a change here (not every commit) pays the ~minute Vulkan warm-up compile."""
    taichi_root = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(taichi_root))
    sources = sorted(
        os.path.join(root, name) for root, _dirs, files in os.walk(taichi_root) for name in files if name.endswith(".py")
    )
    digest = hashlib.blake2b(digest_size=16)
    for path in sources:
        digest.update(os.path.relpath(path, repo_root).replace("\\", "/").encode("utf-8", errors="replace"))
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
    raw_ver = getattr(ti, "__version__", "unknown") or "unknown"
    if isinstance(raw_ver, tuple):
        raw_ver = ".".join(str(x) for x in raw_ver)
    ti_ver = "".join((c if (c.isalnum() or c in "._-") else "_") for c in str(raw_ver)).replace(".", "_")
    cache_dir = os.path.join(repo_root, "bin", "taichi_cache", "v2", f"ti_{ti_ver}", digest.hexdigest()[:12])
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _init_taichi_quietly(init_kwargs: dict) -> None:
    """`ti.init()` without its console banners. Windows reports ERROR_INVALID_FUNCTION (1) when a library queries
    console properties (terminal size/mode) while stdout/stderr are redirected: retry once with them attached."""
    try:
        with quiet_stdio(not settings.output_enabled()):
            ti.init(**init_kwargs)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1 or settings.output_enabled():
            raise
        ti.init(**init_kwargs)


def init_taichi():
    """Initialize Taichi on the Vulkan backend, once per process, in f32 precision."""
    global _ti_initialized
    global _ti_materialized_once
    global _offline_cache_dir
    with _ti_lock:
        if _ti_initialized:
            return
        _assert_darwin_main_thread_materialization()
        _select_vulkan_device()
        _offline_cache_dir = _get_offline_cache_dir()
        init_kwargs = dict(
            arch=ti.vulkan,
            default_fp=ti.f32,
            default_ip=ti.i32,
            # Cross-vendor determinism: the per-note score is floor(f32*f32) (scoring.py). With fast_math on, the backend may
            # contract `a*b+c` into an FMA or reassociate products, and Metal (MoltenVK) vs
            # Vulkan/AMD then round the last bit differently -> the per-note floor flips +/-1 on
            # boundary notes -> the integer gem argmax selects a different allocation on each
            # vendor (the ~0.4-0.7% base "near-tie flip"). fast_math=False forces IEEE-strict
            # +,-,*,/ (correctly rounded, no contraction/reassociation), so the score is
            # bit-identical across Metal and Vulkan and the pick is deterministic. Stays on GPU
            # (search remains batched); negligible cost for this add/mul arithmetic.
            fast_math=False,
            default_gpu_block_dim=_GPU_BLOCK_DIM,
            # Compiled kernels persist on disk across processes (no recompiles; results unchanged).
            offline_cache=True,
            offline_cache_file_path=_offline_cache_dir,
        )
        # ti.init() is serialized per offline-cache directory across processes: some Windows/Vulkan stacks race in
        # the loader/driver and the on-disk cache setup when several processes initialize at once.
        try:
            with offline_cache_lock():
                _init_taichi_quietly(init_kwargs)
        except Exception:
            # The offline kernel cache only saves compile time: retry once without it.
            logger.warning("[Taichi] Init with the offline kernel cache failed; retrying without it", exc_info=True)
            init_kwargs.pop("offline_cache", None)
            init_kwargs.pop("offline_cache_file_path", None)
            with offline_cache_lock():
                _init_taichi_quietly(init_kwargs)
        _ti_initialized = True
        _ti_materialized_once = True
        logger.debug("[Taichi] Initialized with the Vulkan backend - f32 precision")


def reset_taichi(*, reason: str | None = None) -> None:
    """Reset Taichi (frees its Vulkan resources): the recovery path of a driver failure, and the executor's shutdown."""
    global _ti_initialized
    with _ti_lock:
        if reason:
            logger.debug("[Taichi] Resetting runtime: %s", reason)

        if not _ti_initialized:
            return

        # Best effort: this also runs after a lost device, where sync and even reset can fail.
        # The runtime is marked uninitialized regardless so the caller's retry re-inits it.
        try:
            ti.sync()
        except Exception:
            logger.warning("[Taichi] sync before reset failed", exc_info=True)
        try:
            ti.reset()
        except Exception:
            logger.warning("[Taichi] reset failed", exc_info=True)

        _ti_initialized = False
