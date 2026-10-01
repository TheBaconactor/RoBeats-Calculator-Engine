"""The storage layer of the frontier caches: content-addressed files, their version lineage, memory tiers, writes.

Both persistent frontier caches -- the timeline (Perfect-window Base) grid payloads and the Force Great response
bundles -- are directories of files named by a digest of their cache key. The key's first element is the version of
the code that produces the files (a fingerprint of the producer sources). A file written by an explicitly ratified
predecessor version, proven byte-identical, serves the same key while the current version's file is absent; each
version lists its ratified predecessors itself (ratification is never chained). File formats, payload producers and
completeness checks stay with each cache (taichi_gem.api.timeline; taichi_gem.force_greats.response_cache*).
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, Mapping, TypeVar

from gear_optimizer.solver.frontier_cache_scope import frontier_cache_is_ephemeral

logger = logging.getLogger(__name__)

V = TypeVar("V")


def content_addressed_path(directory: Path, cache_key: tuple) -> Path:
    """The file of `cache_key` in `directory`, named by a digest of the key."""
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return directory / f"{digest}.npz"


def write_atomically(path: Path, write: Callable[[Path], None]) -> None:
    """Create `path` through `write(temporary sibling)` and a rename: readers see the old file or the complete new
    one, and a failed write leaves no temporary file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp{path.suffix}")
    try:
        write(tmp)
        tmp.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class FrontierCache:
    """One frontier cache directory and the identity of its files."""

    name: str  # its subdirectory in a temporary cache scope and its build lock's label
    log_label: str
    directory: Callable[[], Path]
    file_path: Callable[[tuple], Path]
    version: Callable[[], str]
    # version -> the predecessor versions whose files are byte-identical to its own
    predecessors: Mapping[str, tuple[str, ...]]

    def compatible_versions(self) -> tuple[str, ...]:
        """The current version followed by its ratified predecessors."""
        current = self.version()
        return (current, *self.predecessors.get(current, ()))

    def readable_path(self, cache_key: tuple) -> Path | None:
        """The existing file that serves `cache_key`: the current version's, else a ratified predecessor's."""
        path = self.file_path(cache_key)
        if path.exists():
            return path
        if cache_key and str(cache_key[0]) == self.version():
            for predecessor in self.predecessors.get(str(cache_key[0]), ()):
                predecessor_path = self.file_path((predecessor, *cache_key[1:]))
                if predecessor_path.exists():
                    return predecessor_path
        return None

    def serving_path(self, cache_key: tuple) -> Path:
        """`readable_path`, else the path the current version's file is written to."""
        return self.readable_path(cache_key) or self.file_path(cache_key)

    def remove_temp_files(self) -> int:
        """Delete the temporary files of interrupted writes; returns how many."""
        directory = self.directory()
        if not directory.exists():
            return 0
        removed = 0
        for path in directory.glob("*.tmp.npz"):
            path.unlink(missing_ok=True)
            removed += 1
        if removed:
            logger.info("%s Removed %s stale temporary cache file(s).", self.log_label, removed)
        return removed


class MemoryLru(Generic[V]):
    """A process-local least-recently-used map of cache entries. Inside a temporary cache scope it neither serves nor
    keeps anything, so a scoped (uploaded) chart leaves no entry behind."""

    def __init__(self, max_entries: int) -> None:
        self._max_entries = int(max_entries)
        self._entries: OrderedDict[tuple, V] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: tuple) -> V | None:
        if frontier_cache_is_ephemeral():
            return None
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def __contains__(self, key: object) -> bool:
        """Membership; unlike `get` it leaves the entry's recency as it is."""
        if frontier_cache_is_ephemeral():
            return False
        with self._lock:
            return key in self._entries

    def put(self, key: tuple, value: V) -> None:
        if frontier_cache_is_ephemeral():
            return
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def pop(self, key: tuple) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def pop_prefix(self, prefix: tuple) -> int:
        """Drop every entry whose key starts with `prefix`; returns how many."""
        with self._lock:
            stale = [key for key in self._entries if key[: len(prefix)] == prefix]
            for key in stale:
                del self._entries[key]
            return len(stale)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
