from __future__ import annotations

import concurrent.futures
import threading
from collections import OrderedDict
from types import SimpleNamespace

import numpy as np

from gear_optimizer.core import singleflight as singleflight_module
from gear_optimizer.solver import fg_effective_dedup
from gear_optimizer.solver import native_inflight_lifecycle_prepare as lifecycle_prepare


def _track_waiter(monkeypatch):
    waiter_joined = threading.Event()
    original_future = concurrent.futures.Future

    class TrackingFuture(original_future):
        def result(self, timeout=None):
            waiter_joined.set()
            return super().result(timeout=timeout)

    monkeypatch.setattr(singleflight_module, "Future", TrackingFuture)
    return waiter_joined


def test_prep_cache_singleflight_builds_exact_key_once(monkeypatch):
    waiter_joined = _track_waiter(monkeypatch)
    cache = OrderedDict()
    started = threading.Event()
    release = threading.Event()
    value = object()
    build_calls = 0

    def _build():
        nonlocal build_calls
        build_calls += 1
        started.set()
        assert release.wait(timeout=5.0)
        return value

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(
            lifecycle_prepare._prep_cache_get_or_build,
            cache,
            ("same",),
            _build,
            cache_name="pools",
            maxsize=2,
        )
        assert started.wait(timeout=5.0)
        waiter = executor.submit(
            lifecycle_prepare._prep_cache_get_or_build,
            cache,
            ("same",),
            _build,
            cache_name="pools",
            maxsize=2,
        )
        assert waiter_joined.wait(timeout=5.0)
        release.set()

        assert owner.result(timeout=5.0) is value
        assert waiter.result(timeout=5.0) is value

    assert build_calls == 1


def test_prep_cache_singleflight_shares_failure_and_clears_for_retry(monkeypatch):
    waiter_joined = _track_waiter(monkeypatch)
    cache = OrderedDict()
    started = threading.Event()
    release = threading.Event()
    failure = RuntimeError("cold build failed")

    def _fail():
        started.set()
        assert release.wait(timeout=5.0)
        raise failure

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(
            lifecycle_prepare._prep_cache_get_or_build,
            cache,
            ("same",),
            _fail,
            cache_name="registry",
            maxsize=2,
        )
        assert started.wait(timeout=5.0)
        waiter = executor.submit(
            lifecycle_prepare._prep_cache_get_or_build,
            cache,
            ("same",),
            _fail,
            cache_name="registry",
            maxsize=2,
        )
        assert waiter_joined.wait(timeout=5.0)
        release.set()

        assert owner.exception(timeout=5.0) is failure
        assert waiter.exception(timeout=5.0) is failure

    retry_value = object()
    assert (
        lifecycle_prepare._prep_cache_get_or_build(
            cache,
            ("same",),
            lambda: retry_value,
            cache_name="registry",
            maxsize=2,
        )
        is retry_value
    )


def test_fg_effective_tables_singleflight_builds_once_and_shares_arrays(monkeypatch):
    waiter_joined = _track_waiter(monkeypatch)
    registry = SimpleNamespace()
    started = threading.Event()
    release = threading.Event()
    gear_rank = np.asarray([0, 1], dtype=np.int32)
    mini_sig_id = np.asarray([2, 3], dtype=np.int32)
    build_calls = 0
    with fg_effective_dedup._CONTEXT_TABLES_LOCK:
        fg_effective_dedup._CONTEXT_TABLES_CACHE.clear()

    def _build_gear(_registry):
        nonlocal build_calls
        build_calls += 1
        started.set()
        assert release.wait(timeout=5.0)
        return gear_rank

    monkeypatch.setattr(fg_effective_dedup, "build_gear_name_rank", _build_gear)
    monkeypatch.setattr(
        fg_effective_dedup,
        "build_mini_sig_id",
        lambda *_args, **_kwargs: SimpleNamespace(sig_id=mini_sig_id),
    )
    kwargs = {
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "selected_color": "Rush",
    }

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            owner = executor.submit(fg_effective_dedup.effective_tables_for_context, registry, **kwargs)
            assert started.wait(timeout=5.0)
            waiter = executor.submit(fg_effective_dedup.effective_tables_for_context, registry, **kwargs)
            assert waiter_joined.wait(timeout=5.0)
            release.set()
            owner_tables = owner.result(timeout=5.0)
            waiter_tables = waiter.result(timeout=5.0)

        assert owner_tables is waiter_tables
        assert owner_tables[0] is gear_rank
        assert owner_tables[1] is mini_sig_id
        assert build_calls == 1
    finally:
        release.set()
        with fg_effective_dedup._CONTEXT_TABLES_LOCK:
            fg_effective_dedup._CONTEXT_TABLES_CACHE.clear()
