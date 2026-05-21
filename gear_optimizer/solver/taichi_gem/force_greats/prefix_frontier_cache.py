from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)

FG_PREFIX_FRONTIER_CACHE_VERSION = "fg-prefix-frontier-v1"
_FG_PREFIX_FRONTIER_CACHE_MAX = max(1, int(env_get("FG_PREFIX_FRONTIER_CACHE_MAX", "128") or "128"))
_FG_PREFIX_FRONTIER_CACHE: "OrderedDict[tuple, FgPrefixFrontierPayload]" = OrderedDict()
_FG_PREFIX_FRONTIER_LOCK = threading.RLock()


@dataclass(frozen=True)
class FgPrefixFrontierPayload:
    signatures: np.ndarray
    forced_counts: np.ndarray
    count: int
    n_sections: int


def fg_prefix_frontier_cache_dir() -> Path:
    override = str(env_get("FG_PREFIX_FRONTIER_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "bin" / "fg_prefix_frontier_cache"


def fg_prefix_frontier_base_cache_key(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any,
    total_notes: int,
    long_notes: int,
    n_sections: int,
    ref_arrays: dict,
) -> tuple:
    ref_ft = np.asarray((ref_arrays or {}).get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray((ref_arrays or {}).get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return (
        FG_PREFIX_FRONTIER_CACHE_VERSION,
        bytes(array_sig16(np.asarray(timestamps, dtype=np.float32).reshape(-1))),
        bytes(array_sig16(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))),
        int(total_notes),
        int(long_notes),
        int(n_sections),
        bytes(array_sig16(ref_ft)),
        bytes(array_sig16(ref_ff)),
    )


def fg_prefix_frontier_cache_key(base_key: tuple, *, ft_idx: int, ff_idx: int) -> tuple:
    return tuple(base_key) + (int(ft_idx), int(ff_idx))


def fg_prefix_frontier_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(tuple(cache_key)).encode("utf-8"), digest_size=16).hexdigest()
    return fg_prefix_frontier_cache_dir() / f"{digest}.npz"


def _payload_from_arrays(
    *,
    signatures: Any,
    forced_counts: Any,
    count: int,
    n_sections: int,
) -> FgPrefixFrontierPayload | None:
    try:
        count_i = int(count)
        n_sections_i = int(n_sections)
    except Exception as e:
        logger.debug(f"prefix_frontier_cache:_payload_from_arrays: {e}")
        return None
    if count_i < 0 or n_sections_i <= 0:
        return None
    sig = np.ascontiguousarray(np.asarray(signatures, dtype=np.int32))
    counts = np.ascontiguousarray(np.asarray(forced_counts, dtype=np.int32))
    if sig.ndim != 2 or counts.ndim != 2:
        return None
    if sig.shape[1] != 11:
        return None
    if counts.shape[1] < n_sections_i:
        return None
    if sig.shape[0] < count_i or counts.shape[0] < count_i:
        return None
    return FgPrefixFrontierPayload(
        signatures=sig[:count_i, :11],
        forced_counts=counts[:count_i, :n_sections_i],
        count=count_i,
        n_sections=n_sections_i,
    )


def load_fg_prefix_frontier_payload(cache_key: tuple) -> FgPrefixFrontierPayload | None:
    key = tuple(cache_key)
    with _FG_PREFIX_FRONTIER_LOCK:
        cached = _FG_PREFIX_FRONTIER_CACHE.get(key)
        if isinstance(cached, FgPrefixFrontierPayload):
            _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
            return cached

    path = fg_prefix_frontier_cache_path(key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != FG_PREFIX_FRONTIER_CACHE_VERSION:
                return None
            payload = _payload_from_arrays(
                signatures=np.asarray(data["signatures"], dtype=np.int32),
                forced_counts=np.asarray(data["forced_counts"], dtype=np.int32),
                count=int(np.asarray(data["count"]).item()),
                n_sections=int(np.asarray(data["n_sections"]).item()),
            )
    except Exception as e:
        logger.debug(f"prefix_frontier_cache:load_fg_prefix_frontier_payload: {e}")
        try:
            path.unlink(missing_ok=True)
        except Exception as unlink_error:
            logger.debug(f"prefix_frontier_cache:load_fg_prefix_frontier_payload: {unlink_error}")
        return None
    if payload is None:
        return None
    with _FG_PREFIX_FRONTIER_LOCK:
        _FG_PREFIX_FRONTIER_CACHE[key] = payload
        _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
        while len(_FG_PREFIX_FRONTIER_CACHE) > int(_FG_PREFIX_FRONTIER_CACHE_MAX):
            _FG_PREFIX_FRONTIER_CACHE.popitem(last=False)
    return payload


def save_fg_prefix_frontier_payload(cache_key: tuple, payload: FgPrefixFrontierPayload) -> None:
    if not isinstance(payload, FgPrefixFrontierPayload):
        return
    key = tuple(cache_key)
    path = fg_prefix_frontier_cache_path(key)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        np.savez_compressed(
            tmp,
            version=np.asarray(FG_PREFIX_FRONTIER_CACHE_VERSION),
            count=np.asarray(int(payload.count), dtype=np.int32),
            n_sections=np.asarray(int(payload.n_sections), dtype=np.int32),
            signatures=np.asarray(payload.signatures[: int(payload.count), :11], dtype=np.int32),
            forced_counts=np.asarray(
                payload.forced_counts[: int(payload.count), : int(payload.n_sections)],
                dtype=np.int32,
            ),
        )
        tmp.replace(path)
    except Exception as e:
        logger.debug(f"prefix_frontier_cache:save_fg_prefix_frontier_payload: {e}")
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception as unlink_error:
                logger.debug(f"prefix_frontier_cache:save_fg_prefix_frontier_payload: {unlink_error}")
        return

    with _FG_PREFIX_FRONTIER_LOCK:
        _FG_PREFIX_FRONTIER_CACHE[key] = payload
        _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
        while len(_FG_PREFIX_FRONTIER_CACHE) > int(_FG_PREFIX_FRONTIER_CACHE_MAX):
            _FG_PREFIX_FRONTIER_CACHE.popitem(last=False)
