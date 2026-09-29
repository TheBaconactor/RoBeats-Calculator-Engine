import psutil
import pytest

import gear_optimizer.core.memory as memory
from gear_optimizer.core.memory import compute_memory_guard_limit
from gear_optimizer.settings import RunSettings


def test_detect_total_physical_memory_reads_psutil_once(monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_WATCHDOG_TOTAL_RAM_BYTES", None)

    total = memory.detect_total_physical_memory()
    assert total == psutil.virtual_memory().total

    monkeypatch.setattr(psutil, "virtual_memory", lambda: pytest.fail("physical RAM must be cached"))
    assert memory.detect_total_physical_memory() == total


def test_compute_memory_guard_limit_defaults_to_percent_of_physical_ram(monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_WATCHDOG_TOTAL_RAM_BYTES", None)

    limit = compute_memory_guard_limit(RunSettings())

    assert 0 < limit < psutil.virtual_memory().total
