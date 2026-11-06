"""The storage of both frontier caches: content-addressed files, version lineage, memory tiers, manifest, prebuild.

Both persistent frontier caches -- the timeline (Perfect-window Base) grid payloads and the Force Great response
bundles -- are directories of files named by a digest of their cache key. The key's first element is the version of
the code that produces the files (a fingerprint of the producer sources). A file written by an explicitly ratified
predecessor version, proven byte-identical, serves the same key while the current version's file is absent; each
version lists its ratified predecessors itself (ratification is never chained).

Each directory keeps a manifest of the files a prebuild verified, keyed by chart content, so verifying the catalog
again reads no file it verified before. The startup prebuild (`prebuild_frontier_cache`) is the same for both caches;
what differs stays with each cache: the payload, its file format and completeness check, how missing charts are
built, and directory maintenance (timeline_cache with timeline_prebuild; fg_cache* with fg_prebuild).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, Iterable, Mapping, TypeVar

from gear_optimizer.chart import load_chart
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.cpu_affinity import pin_frontier_prebuild_worker
from gear_optimizer.core.file_lock import exclusive_file_lock
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.frontier.cache_scope import frontier_cache_is_ephemeral
from gear_optimizer.solver.timing_envelope import TimedSong, time_song

logger = logging.getLogger(__name__)

V = TypeVar("V")
P = TypeVar("P")

# Manifest entries are keyed by the chart's content, so a chart under a new directory still hits its entry.
_MANIFEST_SCHEMA = 2
_MANIFEST_LOCK = threading.RLock()
# Manifest hits re-derived from their chart to catch a key change that came without a version change.
_DRIFT_SAMPLE_SIZE = 8


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
class FrontierCacheManifestPlan:
    hit_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    key_by_path: dict[str, str]  # the manifest key of each readable chart
    newly_recorded: int = 0  # files the plan verified itself

    @property
    def total_paths(self) -> int:
        return len(self.hit_paths) + len(self.missing_paths)


@dataclass(frozen=True)
class FrontierCacheInfo:
    """Whether a song's file is cached and where, found without loading it."""

    cache_key: tuple
    disk_path: Path
    cache_source: str  # "memory", "disk" or "missing"


@dataclass(frozen=True)
class FrontierCacheLoad(Generic[P]):
    """A song's payload with its key and file, and where it came from."""

    payload: P
    cache_key: tuple
    disk_path: Path
    cache_source: str  # "memory", "disk" or "built"
    elapsed_ms: float


@dataclass(frozen=True)
class FrontierCacheBuildResult:
    path: str  # the chart
    source: str  # "built", "disk" or "memory"
    build_ms: float
    cache_file: str


def _file_size(path: str) -> int | None:
    with contextlib.suppress(OSError):
        return os.stat(path).st_size
    return None


@dataclass(frozen=True)
class FrontierCache:
    """One frontier cache directory: the identity of its files and its manifest."""

    name: str  # its subdirectory in a temporary cache scope
    log_label: str
    directory: Callable[[], Path]
    file_path: Callable[[tuple], Path]
    version: Callable[[], str]
    # version -> the predecessor versions whose files are byte-identical to its own
    predecessors: Mapping[str, tuple[str, ...]]
    is_complete: Callable[[str | Path], bool]  # a complete file of a compatible version
    song_key: Callable[[TimedSong, StatCurves], tuple]  # the key of the file serving a song
    manifest_name: str
    manifest_version_field: str
    manifest_stat_signature: str | None = None  # the FT/FF stat keys every file covers, when part of its identity

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

    def chart_file(self, chart_path: str, curves: StatCurves, timing_mode: str) -> Path:
        """The file serving the chart's song in `timing_mode` (parses the chart)."""
        return self.serving_path(self.song_key(time_song(load_chart(Path(chart_path)), timing_mode), curves))

    def remove_temp_files(self) -> None:
        """Delete the temporary files of interrupted writes."""
        directory = self.directory()
        if directory.exists():
            for path in directory.glob("*.tmp.npz"):
                path.unlink(missing_ok=True)

    def manifest_path(self) -> Path:
        return self.directory() / self.manifest_name

    def manifest_entries(self) -> dict[str, dict]:
        """The manifest's entries: none unless it was written for the current version."""
        try:
            payload = json.loads(self.manifest_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        current = payload.get("schema") == _MANIFEST_SCHEMA and payload.get(self.manifest_version_field) == self.version()
        return payload["entries"] if current else {}

    def _save_manifest(self, entries: dict[str, dict]) -> None:
        # An entry stays useful while its (content-addressed) file exists, whichever directory its chart lies in.
        kept = {key: entry for key, entry in entries.items() if os.path.exists(entry["cache_file"])}
        text = json.dumps({"schema": _MANIFEST_SCHEMA, self.manifest_version_field: self.version(), "entries": kept},
                          separators=(",", ":"))
        with _MANIFEST_LOCK:
            write_atomically(self.manifest_path(), lambda tmp: tmp.write_text(text, encoding="utf-8"))

    def _manifest_key(self, chart_path: str, axes_signature: str, timing_mode: str) -> str | None:
        """The chart's identity in the manifest (None when it cannot be read): the version, the FT/FF axes and stat
        keys every file covers, the timing mode and the chart's bytes."""
        try:
            content = Path(chart_path).read_bytes()
        except OSError:
            return None
        parts = [self.version(), timing_mode, axes_signature]
        if self.manifest_stat_signature is not None:
            parts.append(self.manifest_stat_signature)
        parts.append(hashlib.blake2b(content, digest_size=16).hexdigest())
        return hashlib.blake2b("|".join(parts).encode("utf-8"), digest_size=16).hexdigest()

    def manifest_plan(
        self, song_paths: list[str], curves: StatCurves, *, timing_mode: str, persist: bool = True
    ) -> FrontierCacheManifestPlan:
        """Split the charts into hits (a complete file serves them) and misses.

        A recorded entry hits on its file's size alone: the path is content-addressed and builds are deterministic, and
        a corrupt file fails loudly where it is read (a file's mtime changes with copies; comparing it cost ~100 s of
        verifying per start). A chart without a usable entry is probed: when the file its key derives is complete, it
        hits and its entry is recorded (and saved, with `persist`). If a sample of the hits derives other files than the
        manifest recorded, the key derivation changed without a version change and every chart counts as missing.
        """
        entries = self.manifest_entries()
        axes_signature = bytes(array_sig16(curves.f32["Fever Time"]) + array_sig16(curves.f32["Fever Fill Rate"])).hex()
        hits: list[str] = []
        misses: list[str] = []
        keys: dict[str, str] = {}
        recorded = 0
        for song_path in song_paths:
            key = self._manifest_key(song_path, axes_signature, timing_mode)
            if key is None:
                misses.append(song_path)
                continue
            keys[song_path] = key
            entry = entries.get(key)
            if entry and _file_size(entry["cache_file"]) == entry.get("cache_size"):
                hits.append(song_path)
                continue
            try:
                cache_file = str(self.chart_file(song_path, curves, timing_mode))
            except (OSError, ValueError) as exc:
                logger.warning("%s Cannot derive the file of %s: %s", self.log_label, song_path, exc)
                misses.append(song_path)
                continue
            if _file_size(cache_file) is not None and self.is_complete(cache_file):
                entries[key] = {"cache_file": cache_file, "cache_size": _file_size(cache_file)}
                recorded += 1
                hits.append(song_path)
            else:
                misses.append(song_path)
        if persist and recorded:
            self._save_manifest(entries)
        if self._key_drifted(hits, keys, entries, curves, timing_mode):
            return FrontierCacheManifestPlan((), tuple(song_paths), keys)
        return FrontierCacheManifestPlan(tuple(hits), tuple(misses), keys, recorded)

    def _key_drifted(
        self, hits: list[str], keys: dict[str, str], entries: dict[str, dict], curves: StatCurves, timing_mode: str
    ) -> bool:
        """Whether a sample of the hits derives other files than the manifest recorded for them.

        The manifest's identity cannot see a change of the key derivation itself: if the key inputs change without a
        version change, every entry silently points at a file runtime never asks for (the 2026-07-02 incident: stale
        bundles reported ready, every affected song failed prep). A handful of chart parses turns that into a re-verify.
        """
        for song_path in hits[:: max(1, len(hits) // _DRIFT_SAMPLE_SIZE)][:_DRIFT_SAMPLE_SIZE]:
            recorded = entries[keys[song_path]]["cache_file"]
            try:
                derived = str(self.chart_file(song_path, curves, timing_mode))
            except (OSError, ValueError):  # a chart that does not parse is not a drift signal
                continue
            if os.path.abspath(derived) != os.path.abspath(recorded):
                logger.warning("%s Cache-key drift: %s derives %s, the manifest recorded %s: every chart is verified again.",
                               self.log_label, song_path, derived, recorded)
                return True
        return False

    def record_manifest(self, plan: FrontierCacheManifestPlan, results: Iterable[FrontierCacheBuildResult]) -> None:
        """Record the complete files a build produced for its plan's charts."""
        entries = self.manifest_entries()
        recorded = 0
        for result in results:
            size = _file_size(result.cache_file)
            if size is not None and result.path in plan.key_by_path and self.is_complete(result.cache_file):
                entries[plan.key_by_path[result.path]] = {"cache_file": result.cache_file, "cache_size": size}
                recorded += 1
        if recorded:
            self._save_manifest(entries)


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


# --- the startup prebuild ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FrontierCachePrebuildSummary:
    total: int = 0
    built: int = 0
    failures: int = 0


class PrebuildTally:
    """The results of building one timing mode's missing charts, with progress logs."""

    def __init__(self, cache: FrontierCache, total: int, *, progress_every: int) -> None:
        self.cache = cache
        self.total = total
        self.progress_every = progress_every
        self.results: list[FrontierCacheBuildResult] = []
        self.failures = 0

    def add(self, result: FrontierCacheBuildResult) -> None:
        self.results.append(result)

    def fail(self, chart_path: str, exc: BaseException, *, songs: int = 1) -> None:
        """A chart's build failed; `songs` counts it with the charts its file would have served too."""
        self.failures += songs
        logger.warning("%s Failed to prebuild %s: %s", self.cache.log_label, chart_path, exc)

    def log_progress(self, latest: FrontierCacheBuildResult) -> None:
        completed = len(self.results)
        if completed == 1 or completed % self.progress_every == 0:
            logger.info("%s %s/%s complete (latest=%s %.1fms)", self.cache.log_label, completed, self.total, latest.source,
                        latest.build_ms)


def build_frontier_cache_for_chart(
    chart_path: str,
    curves: StatCurves,
    timing_mode: str,
    ensure: Callable[[TimedSong, StatCurves], tuple[str, float, Path]],
) -> FrontierCacheBuildResult:
    """Make sure the chart's song has its cache file; `ensure` returns (source, build ms, file)."""
    source, build_ms, cache_file = ensure(time_song(load_chart(Path(chart_path)), timing_mode), curves)
    return FrontierCacheBuildResult(path=chart_path, source=source, build_ms=build_ms, cache_file=str(cache_file))


_prebuild_worker_curves: StatCurves | None = None


def init_prebuild_worker(curves: StatCurves, configure_threads: Callable[[int], object], threads: int) -> None:
    """Process-pool initializer of a prebuild worker: its CPU placement, its build threads and the run's curves."""
    global _prebuild_worker_curves
    pin_frontier_prebuild_worker()
    configure_threads(max(1, threads))
    _prebuild_worker_curves = curves


def prebuild_worker_curves() -> StatCurves:
    return _prebuild_worker_curves


def _unique_chart_paths(chart_paths: Iterable[str]) -> list[str]:
    """The charts in order, each path once (paths compared absolute, case-insensitively)."""
    return list({os.path.abspath(path).casefold(): str(path) for path in reversed(list(chart_paths))}.values())[::-1]


@dataclass(frozen=True)
class FrontierCachePrebuild:
    """How one cache's startup prebuild builds the charts its manifest misses and keeps its directory."""

    cache: FrontierCache
    # The missing charts of one timing mode -> their results (the cache's build scheduler).
    build_songs: Callable[[list[str], StatCurves, str], PrebuildTally]
    # Under the build lock, once the manifest plan is known: (plan, authorize_destructive_rotation).
    maintain: Callable[[FrontierCacheManifestPlan, bool], None]


def _prebuild_timing_mode(
    prebuild: FrontierCachePrebuild, song_paths: list[str], curves: StatCurves, timing_mode: str, rotate: bool
) -> FrontierCachePrebuildSummary:
    cache = prebuild.cache
    if not song_paths:
        return FrontierCachePrebuildSummary()
    if not rotate and cache.manifest_entries():
        # Charts the manifest records are readers, not builders: probe without the lock and without writing the
        # manifest, so they never wait behind another process's build. Files to record go through the lock below.
        probe = cache.manifest_plan(song_paths, curves, timing_mode=timing_mode, persist=False)
        if not probe.missing_paths and not probe.newly_recorded:
            return FrontierCachePrebuildSummary(total=probe.total_paths)
    # One builder per directory: a concurrent process waits here, then its plan hits what this one wrote instead of
    # duplicating the build (and its peak memory).
    with exclusive_file_lock(cache.directory() / ".build.lock"):
        plan = cache.manifest_plan(song_paths, curves, timing_mode=timing_mode)
        prebuild.maintain(plan, rotate)
        if not plan.missing_paths:
            return FrontierCachePrebuildSummary(total=plan.total_paths)
        tally = prebuild.build_songs(list(plan.missing_paths), curves, timing_mode)
        cache.record_manifest(plan, tally.results)
        built = sum(result.source == "built" for result in tally.results)
        return FrontierCachePrebuildSummary(total=plan.total_paths, built=built, failures=tally.failures)


def prebuild_frontier_cache(
    prebuild: FrontierCachePrebuild,
    *,
    charts_by_mode: Mapping[str, Iterable[str]],
    curves: StatCurves,
    authorize_destructive_rotation: bool = False,
) -> FrontierCachePrebuildSummary:
    """Verify the cache files of each timing mode's charts and build the missing ones."""
    summaries = [
        _prebuild_timing_mode(prebuild, _unique_chart_paths(charts), curves, mode, authorize_destructive_rotation)
        for mode, charts in charts_by_mode.items()
    ]
    return FrontierCachePrebuildSummary(
        total=sum(summary.total for summary in summaries),
        built=sum(summary.built for summary in summaries),
        failures=sum(summary.failures for summary in summaries),
    )
