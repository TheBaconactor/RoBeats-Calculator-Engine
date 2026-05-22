from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)

FG_PREFIX_FRONTIER_CACHE_VERSION = "fg-prefix-frontier-v2"
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


def _digest_key(key: tuple) -> str:
    return hashlib.blake2b(repr(tuple(key)).encode("utf-8"), digest_size=16).hexdigest()


def _split_cache_key(cache_key: tuple) -> tuple[tuple, int, int]:
    key = tuple(cache_key)
    if len(key) < 3:
        raise ValueError("FG prefix frontier cache key is missing FT/FF indices")
    return key[:-2], int(key[-2]), int(key[-1])


def fg_prefix_frontier_shard_path(base_key: tuple) -> Path:
    digest = _digest_key(tuple(base_key))
    return fg_prefix_frontier_cache_dir() / f"{digest}.sqlite3"


def fg_prefix_frontier_cache_path(cache_key: tuple) -> Path:
    base_key, _ft_idx, _ff_idx = _split_cache_key(cache_key)
    return fg_prefix_frontier_shard_path(base_key)


def _connect_shard(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS payloads (
            ft_idx INTEGER NOT NULL,
            ff_idx INTEGER NOT NULL,
            count INTEGER NOT NULL,
            n_sections INTEGER NOT NULL,
            signatures BLOB NOT NULL,
            forced_counts BLOB NOT NULL,
            PRIMARY KEY (ft_idx, ff_idx)
        )
        """
    )
    return conn


def fg_prefix_frontier_existing_cells(base_key: tuple, *, stat_max: int) -> set[tuple[int, int]]:
    path = fg_prefix_frontier_shard_path(tuple(base_key))
    if not path.exists():
        return set()
    max_i = int(stat_max)
    with sqlite3.connect(str(path)) as conn:
        try:
            rows = conn.execute(
                "SELECT ft_idx, ff_idx FROM payloads WHERE ft_idx BETWEEN 0 AND ? AND ff_idx BETWEEN 0 AND ?",
                (max_i, max_i),
            ).fetchall()
        except sqlite3.Error:
            return set()
    return {(int(ft), int(ff)) for ft, ff in rows}


def fg_prefix_frontier_cache_files() -> list[Path]:
    root = fg_prefix_frontier_cache_dir()
    if not root.exists():
        return []
    return sorted(root.glob("*.sqlite3"))


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

    base_key, ft_idx, ff_idx = _split_cache_key(key)
    path = fg_prefix_frontier_shard_path(base_key)
    if not path.exists():
        return None
    try:
        with sqlite3.connect(str(path)) as conn:
            row = conn.execute(
                "SELECT count, n_sections, signatures, forced_counts FROM payloads WHERE ft_idx = ? AND ff_idx = ?",
                (int(ft_idx), int(ff_idx)),
            ).fetchone()
        if row is None:
            return None
        count_i, n_sections_i, sig_blob, counts_blob = row
        payload = _payload_from_arrays(
            signatures=np.frombuffer(sig_blob, dtype=np.int32).copy().reshape(int(count_i), 11),
            forced_counts=np.frombuffer(counts_blob, dtype=np.int32).copy().reshape(int(count_i), int(n_sections_i)),
            count=int(count_i),
            n_sections=int(n_sections_i),
        )
    except Exception as e:
        logger.debug(f"prefix_frontier_cache:load_fg_prefix_frontier_payload: {e}")
        return None
    if payload is None:
        return None
    with _FG_PREFIX_FRONTIER_LOCK:
        _FG_PREFIX_FRONTIER_CACHE[key] = payload
        _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
        while len(_FG_PREFIX_FRONTIER_CACHE) > int(_FG_PREFIX_FRONTIER_CACHE_MAX):
            _FG_PREFIX_FRONTIER_CACHE.popitem(last=False)
    return payload


def load_fg_prefix_frontier_payloads(cache_keys: list[tuple | None]) -> list[FgPrefixFrontierPayload | None]:
    out: list[FgPrefixFrontierPayload | None] = [None for _ in cache_keys]
    grouped: dict[tuple, list[tuple[int, int, int, tuple]]] = {}
    with _FG_PREFIX_FRONTIER_LOCK:
        for idx, cache_key in enumerate(cache_keys):
            if cache_key is None:
                continue
            key = tuple(cache_key)
            cached = _FG_PREFIX_FRONTIER_CACHE.get(key)
            if isinstance(cached, FgPrefixFrontierPayload):
                _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
                out[idx] = cached
                continue
            base_key, ft_idx, ff_idx = _split_cache_key(key)
            grouped.setdefault(base_key, []).append((idx, int(ft_idx), int(ff_idx), key))
    for base_key, entries in grouped.items():
        path = fg_prefix_frontier_shard_path(base_key)
        if not path.exists():
            continue
        wanted: dict[tuple[int, int], list[tuple[int, tuple]]] = {}
        for idx, ft, ff, key in entries:
            wanted.setdefault((int(ft), int(ff)), []).append((idx, key))
        try:
            with sqlite3.connect(str(path)) as conn:
                for ft_idx, ff_idx, count_i, n_sections_i, sig_blob, counts_blob in conn.execute(
                    "SELECT ft_idx, ff_idx, count, n_sections, signatures, forced_counts FROM payloads"
                ):
                    items = wanted.get((int(ft_idx), int(ff_idx)))
                    if not items:
                        continue
                    payload = _payload_from_arrays(
                        signatures=np.frombuffer(sig_blob, dtype=np.int32).copy().reshape(int(count_i), 11),
                        forced_counts=np.frombuffer(counts_blob, dtype=np.int32)
                        .copy()
                        .reshape(int(count_i), int(n_sections_i)),
                        count=int(count_i),
                        n_sections=int(n_sections_i),
                    )
                    if payload is None:
                        continue
                    for out_idx, key in items:
                        out[out_idx] = payload
                    with _FG_PREFIX_FRONTIER_LOCK:
                        for _out_idx, key in items:
                            _FG_PREFIX_FRONTIER_CACHE[key] = payload
                            _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
                        while len(_FG_PREFIX_FRONTIER_CACHE) > int(_FG_PREFIX_FRONTIER_CACHE_MAX):
                            _FG_PREFIX_FRONTIER_CACHE.popitem(last=False)
        except Exception as e:
            logger.debug(f"prefix_frontier_cache:load_fg_prefix_frontier_payloads: {e}")
    return out


def save_fg_prefix_frontier_payload(cache_key: tuple, payload: FgPrefixFrontierPayload) -> None:
    save_fg_prefix_frontier_payloads([(cache_key, payload)])


def save_fg_prefix_frontier_payloads(items: list[tuple[tuple, FgPrefixFrontierPayload]]) -> None:
    items = [(tuple(cache_key), payload) for cache_key, payload in items if isinstance(payload, FgPrefixFrontierPayload)]
    if not items:
        return
    grouped: dict[tuple, list[tuple[tuple, int, int, FgPrefixFrontierPayload]]] = {}
    for key, payload in items:
        base_key, ft_idx, ff_idx = _split_cache_key(key)
        grouped.setdefault(base_key, []).append((key, int(ft_idx), int(ff_idx), payload))
    for base_key, entries in grouped.items():
        path = fg_prefix_frontier_shard_path(base_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with _connect_shard(path) as conn:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO payloads
                    (ft_idx, ff_idx, count, n_sections, signatures, forced_counts)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            int(ft_idx),
                            int(ff_idx),
                            int(payload.count),
                            int(payload.n_sections),
                            sqlite3.Binary(
                                np.ascontiguousarray(
                                    payload.signatures[: int(payload.count), :11], dtype=np.int32
                                ).tobytes()
                            ),
                            sqlite3.Binary(
                                np.ascontiguousarray(
                                    payload.forced_counts[: int(payload.count), : int(payload.n_sections)],
                                    dtype=np.int32,
                                ).tobytes()
                            ),
                        )
                        for _key, ft_idx, ff_idx, payload in entries
                    ],
                )
        except Exception as e:
            logger.debug(f"prefix_frontier_cache:save_fg_prefix_frontier_payloads: {e}")
            return
        with _FG_PREFIX_FRONTIER_LOCK:
            for key, _ft_idx, _ff_idx, payload in entries:
                _FG_PREFIX_FRONTIER_CACHE[key] = payload
                _FG_PREFIX_FRONTIER_CACHE.move_to_end(key)
            while len(_FG_PREFIX_FRONTIER_CACHE) > int(_FG_PREFIX_FRONTIER_CACHE_MAX):
                _FG_PREFIX_FRONTIER_CACHE.popitem(last=False)
