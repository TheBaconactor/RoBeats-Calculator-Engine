from __future__ import annotations

import json
import subprocess
import sys

import pytest


def test_cpu_affinity_sizes_frontier_prebuild_to_all_but_one_cpu(monkeypatch) -> None:
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 10)
    monkeypatch.setattr(
        cpu_affinity,
        "timeline_prebuild_worker_count",
        lambda: cpu_affinity.frontier_prebuild_worker_count(),
    )

    assert cpu_affinity.frontier_prebuild_cpu_count() == 9
    assert cpu_affinity.frontier_prebuild_worker_count() == 9
    assert cpu_affinity.timeline_prebuild_worker_count() == 9
    assert cpu_affinity.frontier_prebuild_intra_worker_threads(9) == 1
    assert cpu_affinity.frontier_prebuild_intra_worker_threads(3) == 3


def test_frontier_prebuild_reserves_one_weakest_efficiency_cpu() -> None:
    from gear_optimizer.core import cpu_affinity

    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(
        [(0, 1), (1, 1), (2, 0), (3, 0)],
        4,
    ) == [0, 1, 2]
    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        4,
    ) == [0, 1, 2]
    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(None, 1) == [0]


def test_windows_frontier_worker_pinning_uses_full_set_and_excludes_reserved_cpu(monkeypatch) -> None:
    """Every frontier prebuild worker gets the FULL frontier CPU set (reserved weakest CPU
    excluded) on hybrid silicon. Per-worker bands are gone: with weighted admission the live
    worker count varies with per-song memory weight, and bands degenerated to 1-CPU masks that
    timeshared a giant's reducer threads on a single CPU (measured i9-13900K 2026-07-09:
    37% -> 60% total CPU after re-masking the same workers to the full set, no E-core parking
    at ABOVE_NORMAL priority with EcoQoS cleared)."""
    from gear_optimizer.core import cpu_affinity

    masks: list[int] = []
    monkeypatch.setattr(cpu_affinity.sys, "platform", "win32")
    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 4)
    monkeypatch.setattr(
        cpu_affinity,
        "_windows_logical_cpu_efficiency_classes",
        lambda: [(0, 1), (1, 1), (2, 0), (3, 0)],  # hybrid: P=class1, E=class0; CPU 3 reserved
    )
    monkeypatch.setattr(cpu_affinity, "_apply_affinity_mask", lambda mask: masks.append(int(mask)))

    for _worker in range(3):
        cpu_affinity.pin_frontier_prebuild_worker()

    assert masks == [0b0111, 0b0111, 0b0111]


def test_timeline_prebuild_worker_count_reserves_system_ram(monkeypatch) -> None:
    """Timeline admission must leave commit headroom on the no-pagefile production host."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)  # 31 CPU-budget workers

    import psutil

    class _FakeVM:
        available = int(39.5 * 1e9)

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    # (39.5 - 8 reserve) / 1.75 GB-per-worker -> 18 workers, below the 31-worker CPU budget.
    assert cpu_affinity.timeline_prebuild_worker_count() == 18


def test_timeline_prebuild_worker_count_floor_is_one(monkeypatch) -> None:
    """Even under severe memory pressure at least one worker is scheduled (the guard is a cap, and
    the build must still make progress)."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)

    import psutil

    class _FakeVM:
        available = int(0.5 * 1e9)  # 0.5 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    assert cpu_affinity.timeline_prebuild_worker_count() == 1


def test_fg_response_flat_worker_ram_cap_is_deleted() -> None:
    """The flat FG GB-per-worker cap admitted 12 workers x ~7 GB measured giant commit and crashed
    the machine (2026-07-09). Its one canonical replacement is the weighted admission scheduler;
    the superseded route must not resurface."""
    from gear_optimizer.core import cpu_affinity

    assert not hasattr(cpu_affinity, "fg_response_prebuild_worker_count")
    assert not hasattr(cpu_affinity, "FG_RESPONSE_PREBUILD_GB_PER_WORKER")


def test_windows_frontier_worker_pinning_full_set_on_uniform_cores(monkeypatch) -> None:
    """Uniform silicon (no E-cores): same full-set mask, reserved weakest CPU still excluded."""
    from gear_optimizer.core import cpu_affinity

    masks: list[int] = []
    monkeypatch.setattr(cpu_affinity.sys, "platform", "win32")
    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 4)
    monkeypatch.setattr(
        cpu_affinity,
        "_windows_logical_cpu_efficiency_classes",
        lambda: [(0, 0), (1, 0), (2, 0), (3, 0)],
    )
    monkeypatch.setattr(cpu_affinity, "_apply_affinity_mask", lambda mask: masks.append(int(mask)))

    cpu_affinity.pin_frontier_prebuild_worker()

    assert masks == [0b0111]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows scheduling API contract")
def test_windows_affinity_owner_applies_priority_and_disables_ecoqos() -> None:
    """The native calls must receive a real pointer-sized process handle.

    Without explicit ctypes signatures GetCurrentProcess was truncated to signed ``-1``;
    affinity happened to accept that pseudo-handle, but priority and EcoQoS updates failed with
    ERROR_INVALID_HANDLE while the production owner silently continued.
    """
    probe = r'''
import ctypes
import json
from ctypes import wintypes

import psutil

from gear_optimizer.core.cpu_affinity import _apply_affinity_mask

process = psutil.Process()
mask = sum(1 << int(cpu) for cpu in process.cpu_affinity())
_apply_affinity_mask(mask)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetCurrentProcess.argtypes = []
kernel32.GetPriorityClass.restype = wintypes.DWORD
kernel32.GetPriorityClass.argtypes = [wintypes.HANDLE]

class PowerThrottle(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("ControlMask", wintypes.DWORD),
        ("StateMask", wintypes.DWORD),
    ]

kernel32.GetProcessInformation.restype = wintypes.BOOL
kernel32.GetProcessInformation.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
]
handle = kernel32.GetCurrentProcess()
power = PowerThrottle(1, 0, 0)
if not kernel32.GetProcessInformation(handle, 4, ctypes.byref(power), ctypes.sizeof(power)):
    raise ctypes.WinError(ctypes.get_last_error())
print(json.dumps({
    "priority": int(kernel32.GetPriorityClass(handle)),
    "power_control": int(power.ControlMask),
    "power_state": int(power.StateMask),
}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    payload = json.loads(completed.stdout)

    assert payload["priority"] == 0x00008000
    assert payload["power_control"] & 0x1
    assert not payload["power_state"] & 0x1
