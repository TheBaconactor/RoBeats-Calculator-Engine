"""The Taichi runtime: Vulkan device selection, initialization, the runtime lock, reset and its hooks."""

from __future__ import annotations

import hashlib
import logging
import os
import struct
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator
from ...core.output import quiet_stdio
from gear_optimizer import settings

_ti_initialized = False
# Whether THIS process has ever completed a Taichi materialization. Distinct from
# `_ti_initialized`, which `reset_taichi()` clears: the GLFW/Cocoa context that the first
# materialization acquires is process-global, so only that first one carries the macOS
# main-thread requirement. See `_assert_darwin_main_thread_materialization()`.
_ti_materialized_once = False
_ti_lock = threading.RLock()
_offline_cache_dir: str | None = None
logger = logging.getLogger(__name__)

# Taichi prints a version banner at import time. On Windows, spawned child processes can inherit an invalid console
# handle that makes print() raise OSError [WinError 1]; quiet_stdio covers both Python-level and native writes.
with quiet_stdio(not settings.output_enabled()):
    import taichi as ti  # noqa: E402


def is_initialized() -> bool:
    """Check if Taichi has been initialized."""
    return _ti_initialized


def _assert_darwin_main_thread_materialization() -> None:
    """Refuse a process's FIRST Taichi materialization off the macOS main thread.

    Required OS/GPU dispatch-safety boundary. On darwin ``ti.vulkan`` lowers through MoltenVK,
    and Taichi acquires a GLFW/Cocoa context inside ``VulkanProgramImpl::materialize_runtime``.
    AppKit hard-traps that off the OS main thread (``EXC_BREAKPOINT`` /
    "NSUpdateCycleInitialize() is called off the main thread"), which kills the WHOLE process --
    a lazy first-use from one request thread takes down every other in-flight request with it.

    Raising here converts that unrecoverable trap into an ordinary exception the caller can shed
    on. Hosts that want in-process GPU on darwin materialize on the main thread first (see
    ``app.py::_materialize_gpu_runtime_on_main_thread``); once that has run, ``init_taichi()``
    short-circuits on ``_ti_initialized`` and every thread proceeds normally.

    Scoped to the first materialization only: the GLFW context is process-global and refcounted,
    so a ``reset_taichi()`` recovery re-init does not necessarily re-enter GLFW init. That path
    has never been observed to trap, so it keeps its existing behaviour rather than being
    speculatively broken.
    """
    if sys.platform != "darwin":
        return
    if _ti_materialized_once:
        return
    if threading.current_thread() is threading.main_thread():
        return
    raise RuntimeError(
        "Taichi's GPU runtime must be materialized on the OS main thread on macOS; got thread "
        f"'{threading.current_thread().name}'. Taichi/MoltenVK acquires a GLFW/Cocoa context "
        "during materialize_runtime, which traps off the main thread and kills the process. "
        "Materialize on the main thread during startup before dispatching GPU work to threads."
    )


def taichi_runtime_lock() -> threading.RLock:
    """The lock that serializes access to Taichi's global runtime state.

    Anything that allocates SNode trees or launches kernels against the module-level scratch
    fields is global state: two threads inside it interleave FieldsBuilder placement
    (``TaichiRuntimeError: Field builder ... is not finalized``) and, worse, share per-candidate
    scratch, so a surviving pair of requests can read each other's rows. Callers outside the
    optimizer's own single-GPU-thread executor -- including host applications that call FG
    scoring through a thread pool -- must hold this while they are the owner.

    Reentrant on purpose: Vulkan recovery calls ``reset_taichi`` from inside owner work.
    """
    return _ti_lock


@contextmanager
def _file_lock(lock_path: Path, *, timeout_sec: float | None = None) -> Iterator[None]:
    """Cross-process exclusive file lock (Windows + POSIX); waits forever when `timeout_sec` is None."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    deadline = None if timeout_sec is None else time.monotonic() + max(0.0, float(timeout_sec))
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if not handle.read(1):
                handle.write("0")
                handle.flush()
            handle.seek(0)
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
                    time.sleep(0.01)
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
                    time.sleep(0.01)
        locked = True
        yield
    finally:
        if locked and os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        elif locked:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


@contextmanager
def offline_cache_lock(*, timeout_sec: float | None = None) -> Iterator[str]:
    """Cross-process lock keyed by the Taichi offline-cache directory, which it yields."""
    cache_dir = _offline_cache_dir or _get_offline_cache_dir()
    with _file_lock(Path(cache_dir) / ".metafinder_offline_cache.lock", timeout_sec=timeout_sec):
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


def get_block_dim() -> int:
    """The GPU block size: 256 is the benchmark-validated choice for these kernels (Vulkan allows 1..1024)."""
    return 256


def _get_offline_cache_dir() -> str:
    """<engine>/bin/taichi_cache/v2/ti_<version>/<key>, created; the key hashes the taichi_gem sources (paths and
    contents), so only a change there (not every commit) pays the ~minute Vulkan warm-up compile."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    taichi_root = os.path.join(repo_root, "gear_optimizer", "solver", "taichi_gem")
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
    """
    Initialize Taichi on the Vulkan backend, once per process.

    Called by gpu_executor.py on the GPU thread, or lazily on first use.
    Uses f32 precision for performance (sufficient for score accuracy).
    """
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
            # Cross-vendor determinism: the per-note score is floor(f32*f32) (kernels_helpers
            # `_calc_body_score`/`_calc_head_score_*`). With fast_math on, the backend may
            # contract `a*b+c` into an FMA or reassociate products, and Metal (MoltenVK) vs
            # Vulkan/AMD then round the last bit differently -> the per-note floor flips +/-1 on
            # boundary notes -> the integer gem argmax selects a different allocation on each
            # vendor (the ~0.4-0.7% base "near-tie flip"). fast_math=False forces IEEE-strict
            # +,-,*,/ (correctly rounded, no contraction/reassociation), so the score is
            # bit-identical across Metal and Vulkan and the pick is deterministic. Stays on GPU
            # (search remains batched); negligible cost for this add/mul arithmetic.
            fast_math=False,
            default_gpu_block_dim=get_block_dim(),
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
        logger.debug("[Taichi] Initialized with the Vulkan backend - f32 precision (block_dim=%s)", get_block_dim())


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


# Module state built on the runtime above `fields` (device-derived caches, warmup flags) registers its reset here on
# import; api.initialization.hard_reset_taichi runs them after resetting the runtime and the fields. Keyed by the
# function's qualified name, so a re-imported module replaces its reset instead of adding a second one.
_HARD_RESET_HOOKS: dict[str, Callable[[], None]] = {}


def on_hard_reset(reset: Callable[[], None]) -> Callable[[], None]:
    """Decorator: run `reset` on every hard reset of the Taichi runtime."""
    _HARD_RESET_HOOKS[f"{reset.__module__}.{reset.__qualname__}"] = reset
    return reset


def run_hard_reset_hooks() -> None:
    for reset in list(_HARD_RESET_HOOKS.values()):
        reset()
