"""The storage of both frontier caches: content-addressed files, version lineage, memory tiers, manifest, prebuild.

Both persistent frontier caches -- the timeline (Perfect-window Base) grid payloads and the Force Great response
bundles -- are directories of files named by a digest of their cache key. The key's first element is the version of
the code that produces the files (a fingerprint of the producer sources). A file written by an explicitly ratified
predecessor version, proven byte-identical, serves the same key while the current version's file is absent; each
version lists its ratified predecessors itself (ratification is never chained).

Each directory keeps a manifest of the files a prebuild verified, keyed by version and chart content, so verifying
the catalog again opens no file it verified before, under the same version or the next ratified one. The startup
prebuild (`prebuild_frontier_cache`) is the same for both caches; what differs stays with each cache: the payload, its
file format and completeness check, how several missing charts are built in worker processes, and directory
maintenance (timeline_cache with timeline_prebuild; fg_cache* with fg_prebuild).
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
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.frontier.cache_scope import frontier_cache_is_ephemeral
from gear_optimizer.solver.timing_envelope import TimedSong, time_song

logger = logging.getLogger(__name__)

V = TypeVar("V")
P = TypeVar("P")

# Manifest entries are keyed by the chart's content, so a chart under a new directory still hits its entry.
_MANIFEST_SCHEMA = 2
# Manifest hits re-derived from their chart to catch a key change that came without a version change.
_DRIFT_SAMPLE_SIZE = 8
_PROGRESS_EVERY = 10  # completed builds between two progress lines

_FRONTIER = Path(__file__).resolve().parent
# The exact frontier producer both caches run (Base with Perfect-only actions, FG with Greats too). Both versions
# fingerprint it, so a producer edit can never leave one cache on stale bytes while the other rotates. The FG scoring
# policy is not in it: Base persists timing geometry and the Perfect-only recurrence, never a Great's value, so a
# Force-Greats-only correction rotates the FG cache alone.
FRONTIER_PRODUCER_SOURCES = (
    _FRONTIER.parent / "rules.py",
    _FRONTIER.parent / "core" / "time_quantize.py",
    _FRONTIER.parent / "solver" / "timing_envelope.py",
    _FRONTIER / "fill_crossing.py",
    _FRONTIER / "types.py",
    _FRONTIER / "producer_batch.py",
    _FRONTIER / "producer_scheduler.py",
    _FRONTIER / "producer_precompute.py",
    _FRONTIER / "producer_reducer.py",
    _FRONTIER / "producer_kernels.py",
    _FRONTIER / "producer_surfaces.py",
)


def cache_version(base_version: str, sources: Iterable[Path]) -> str:
    """A cache version: the hand-kept base version plus a fingerprint (an AST digest, see logic_fingerprint.py) of the
    sources whose logic determines the files, so a logic change there rotates the version by itself."""
    return f"{base_version}+logic-{module_logic_fingerprint(sources)}"


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

    def file_path(self, cache_key: tuple) -> Path:
        """The file of `cache_key`, named by a digest of the key (whose first element is the version that writes it)."""
        digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
        return self.directory() / f"{digest}.npz"

    def readable_path(self, cache_key: tuple) -> Path | None:
        """The existing file that serves `cache_key`: its own, else for a key of the current version a ratified
        predecessor's."""
        versions = self.compatible_versions() if cache_key[0] == self.version() else cache_key[:1]
        for version in versions:
            path = self.file_path((version, *cache_key[1:]))
            if path.exists():
                return path
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

    def _read_manifest(self) -> tuple[str, dict[str, dict]]:
        """(The version the manifest was written for, its entries); ("", {}) unless that version is the current one or
        one of its ratified predecessors."""
        try:
            payload = json.loads(self.manifest_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "", {}
        written_for = payload.get(self.manifest_version_field)
        if payload.get("schema") != _MANIFEST_SCHEMA or written_for not in self.compatible_versions():
            return "", {}
        return written_for, payload["entries"]

    def manifest_entries(self) -> dict[str, dict]:
        """The entries of a manifest written for the current version or a ratified predecessor (each keyed under the
        version that verified its file, see `_manifest_key`)."""
        return self._read_manifest()[1]

    def _save_manifest(self, entries: dict[str, dict]) -> None:
        # An entry stays useful while its (content-addressed) file exists, whichever directory its chart lies in.
        kept = {key: entry for key, entry in entries.items() if os.path.exists(entry["cache_file"])}
        text = json.dumps({"schema": _MANIFEST_SCHEMA, self.manifest_version_field: self.version(), "entries": kept},
                          separators=(",", ":"))
        write_atomically(self.manifest_path(), lambda tmp: tmp.write_text(text, encoding="utf-8"))

    def _manifest_key(self, version: str, timing_mode: str, axes_signature: str, chart_digest: str) -> str:
        """A chart's identity in the manifest under `version`: the version, the timing mode, the FT/FF axes and stat
        keys every file covers, and the chart's bytes."""
        parts = [version, timing_mode, axes_signature]
        if self.manifest_stat_signature is not None:
            parts.append(self.manifest_stat_signature)
        parts.append(chart_digest)
        return hashlib.blake2b("|".join(parts).encode("utf-8"), digest_size=16).hexdigest()

    @staticmethod
    def _verified_by_predecessor(entries: dict[str, dict], predecessor_keys: list[str], verified: dict) -> bool:
        """Whether a ratified predecessor version recorded this very file at this size for the chart. Its files are
        proven byte-identical to the current version's, so its verification stands; the entry is spent."""
        for key in predecessor_keys:
            entry = entries.get(key)
            if (entry and entry["cache_size"] == verified["cache_size"]
                    and os.path.abspath(entry["cache_file"]) == os.path.abspath(verified["cache_file"])):
                del entries[key]
                return True
        return False

    def manifest_plan(
        self, song_paths: list[str], curves: StatCurves, *, timing_mode: str, persist: bool = True
    ) -> FrontierCacheManifestPlan:
        """Split the charts into hits (a complete file serves them) and misses.

        A recorded entry hits on its file's size alone: the path is content-addressed and builds are deterministic, and
        a corrupt file fails loudly where it is read (a file's mtime changes with copies; comparing it cost ~100 s of
        verifying per start). A chart without a usable entry is probed: its file is derived from the chart, and it
        hits when a ratified predecessor version recorded that very file at its present size, else when the file reads
        as complete; its entry is recorded (and saved, with `persist`). So a start after a ratified version change
        parses every chart once and opens no cache file. If a sample of the hits derives other files than the manifest
        recorded, the key derivation changed without a version change and every chart counts as missing.
        """
        entries = self.manifest_entries()
        current, *predecessors = self.compatible_versions()
        axes_signature = bytes(array_sig16(curves.f32["Fever Time"]) + array_sig16(curves.f32["Fever Fill Rate"])).hex()
        hits: list[str] = []
        misses: list[str] = []
        keys: dict[str, str] = {}
        recorded = 0
        for song_path in song_paths:
            try:
                chart_digest = hashlib.blake2b(Path(song_path).read_bytes(), digest_size=16).hexdigest()
            except OSError:
                misses.append(song_path)
                continue
            key = keys[song_path] = self._manifest_key(current, timing_mode, axes_signature, chart_digest)
            entry = entries.get(key)
            if entry and _file_size(entry["cache_file"]) == entry["cache_size"]:
                hits.append(song_path)
                continue
            try:
                cache_file = str(self.chart_file(song_path, curves, timing_mode))
            except (OSError, ValueError) as exc:
                logger.warning("%s Cannot derive the file of %s: %s", self.log_label, song_path, exc)
                misses.append(song_path)
                continue
            verified = {"cache_file": cache_file, "cache_size": _file_size(cache_file)}
            predecessor_keys = [self._manifest_key(version, timing_mode, axes_signature, chart_digest)
                                for version in predecessors]
            if verified["cache_size"] is not None and (
                self._verified_by_predecessor(entries, predecessor_keys, verified) or self.is_complete(cache_file)
            ):
                entries[key] = verified
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

    def __init__(self, cache: FrontierCache, total: int) -> None:
        self.cache = cache
        self.total = total
        self.results: list[FrontierCacheBuildResult] = []
        self.failures = 0

    def collect(
        self, chart_path: str, build: Callable[[], FrontierCacheBuildResult], also: tuple[str, ...] = ()
    ) -> None:
        """Take one chart's build (a call that returns its result or raises); `also` are the charts whose songs its
        file serves too, which succeed or fail with it."""
        try:
            result = build()
        except Exception as exc:  # one chart's failure is counted and logged; the prebuild's caller raises on the count
            self.failures += 1 + len(also)
            logger.warning("%s Failed to prebuild %s: %s", self.cache.log_label, chart_path, exc)
            return
        self.results.append(result)
        self.results.extend(
            FrontierCacheBuildResult(path=path, source="disk", build_ms=0.0, cache_file=result.cache_file) for path in also
        )
        completed = len(self.results)
        if completed == 1 or completed % _PROGRESS_EVERY == 0:
            logger.info("%s %s/%s complete (latest=%s %.1fms)", self.cache.log_label, completed, self.total, result.source,
                        result.build_ms)


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
    # Make sure a song's file exists: (source "built", "disk" or "memory", build ms, the file).
    ensure: Callable[[TimedSong, StatCurves], tuple[str, float, Path]]
    # Several missing charts of one timing mode, built in worker processes: each build is collected by the tally.
    build_in_pool: Callable[[list[str], StatCurves, str, PrebuildTally], None]
    # Under the build lock, once the manifest plan is known: (plan, authorize_destructive_rotation).
    maintain: Callable[[FrontierCacheManifestPlan, bool], None]


def _prebuild_timing_mode(
    prebuild: FrontierCachePrebuild, song_paths: list[str], curves: StatCurves, timing_mode: str, rotate: bool
) -> FrontierCachePrebuildSummary:
    cache = prebuild.cache
    if not song_paths:
        return FrontierCachePrebuildSummary()
    if not rotate and cache._read_manifest()[0] == cache.version():
        # Charts the manifest records are readers, not builders: probe without the lock and without writing the
        # manifest, so they never wait behind another process's build. Files to record go through the lock below
        # (after a version change every chart's entry is recorded again, so the probe would only run twice).
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
        missing = list(plan.missing_paths)
        tally = PrebuildTally(cache, len(missing))
        if len(missing) == 1:  # one chart (an upload) builds in this process
            tally.collect(
                missing[0], lambda: build_frontier_cache_for_chart(missing[0], curves, timing_mode, prebuild.ensure)
            )
        else:
            prebuild.build_in_pool(missing, curves, timing_mode, tally)
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
