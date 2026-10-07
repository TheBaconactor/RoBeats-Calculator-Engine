"""The storage of both frontier caches: content-addressed files, version lineage, memory tiers, manifest, prebuild.

Both persistent frontier caches -- the timeline (Perfect-window Base) grid payloads and the Force Great response
bundles -- are directories of files named by a digest of their cache key. The key's first element is the version of
the code that produces the files (a fingerprint of the producer sources). A file written by an explicitly ratified
predecessor version, proven byte-identical, serves the same key while the current version's file is absent; each
version lists its ratified predecessors itself (ratification is never chained).

Each directory keeps a manifest of the files a prebuild verified, keyed by chart content, so verifying the catalog
again reads no file it verified before. The startup prebuild (`prebuild_frontier_cache`) is the same for both caches;
what differs stays with each cache: the payload, its file format and completeness check, how missing charts are
built, and directory maintenance (taichi_gem.api.timeline with timeline_frontier_cache_prebuild;
taichi_gem.force_greats.response_cache* with fg_response_frontier_cache_prebuild).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import threading
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, Iterable, Mapping, TypeVar

from gear_optimizer.chart import load_chart
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.cpu_affinity import pin_frontier_prebuild_worker
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.settings import DIFFICULTIES, paths
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock
from gear_optimizer.solver.frontier_cache_scope import frontier_cache_is_ephemeral
from gear_optimizer.solver.timing_envelope import CACHE_NAMES, TIMING_MODES, TimedSong, time_song

logger = logging.getLogger(__name__)

V = TypeVar("V")
P = TypeVar("P")

# Manifest entries are keyed by the chart's content, so a chart published under a new directory (each engine deploy
# publishes the charts under frontier_server_sources/<revision>) still hits its entry.
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
    total_paths: int
    hit_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    key_by_norm_path: dict[str, str]
    validated_entry_count: int = 0

    @property
    def hit_count(self) -> int:
        return len(self.hit_paths)


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
    cache_source: str  # "memory", "disk", "built", or "warmup_disposable" for a GPU warmup's own payload
    elapsed_ms: float


@dataclass(frozen=True)
class FrontierCacheBuildResult:
    path: str  # the chart
    source: str  # "built", "disk" or "memory"
    build_ms: float
    cache_file: str


@dataclass(frozen=True)
class FrontierCache:
    """One frontier cache directory: the identity of its files and its manifest."""

    name: str  # its subdirectory in a temporary cache scope and its build lock's label
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

    def manifest_path(self) -> Path:
        return self.directory() / self.manifest_name

    def manifest_records_current_version(self) -> bool:
        """Whether the manifest was written for the current version (its entries are not read)."""
        try:
            payload = json.loads(self.manifest_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return isinstance(payload, dict) and str(payload.get(self.manifest_version_field, "") or "") == self.version()

    def manifest_plan(
        self,
        song_paths: Iterable[str],
        curves: StatCurves,
        *,
        timing_mode: str = "non-precise",
        persist_validated_entries: bool = True,
    ) -> FrontierCacheManifestPlan:
        """Split the charts into hits (a complete file serves them) and misses.

        A recorded entry hits on its file's size alone. A chart without a usable entry is probed: when the file its
        current key derives exists and is complete, it hits and its entry is recorded (written to the manifest
        unless `persist_validated_entries` is False). If a sample of the hits derives other files than the manifest
        recorded, the key derivation changed without a version change and every chart counts as missing.
        """
        song_paths = [str(path) for path in song_paths if str(path or "").strip()]
        if not song_paths:
            return FrontierCacheManifestPlan(0, (), (), {})
        version = self.version()
        entries = _load_manifest(self.manifest_path(), version=version, version_field=self.manifest_version_field)
        ref_sig_hex = _ref_axes_signature(curves)

        def derived_file(song_path: str) -> str:
            return str(self.chart_file(song_path, curves, timing_mode))

        hits: list[str] = []
        misses: list[str] = []
        key_by_norm: dict[str, str] = {}
        recorded_file_by_norm: dict[str, str] = {}
        validated = 0
        for song_path in song_paths:
            identity = _chart_identity(song_path)
            if identity is None:
                misses.append(song_path)
                continue
            abs_path, chart_digest = identity
            key = _manifest_key(
                cache_version=version,
                ref_sig_hex=ref_sig_hex,
                stat_sig_hex=self.manifest_stat_signature,
                timing_mode=timing_mode,
                chart_digest=chart_digest,
            )
            key_by_norm[_normalize_manifest_path(abs_path)] = key
            entry = entries.get(key) or {}
            cache_file = str(entry.get("cache_file", "") or "").strip()
            cache_identity = _path_identity(cache_file) if cache_file else None
            cache_hit = cache_identity is not None
            if cache_hit:
                # The fast path compares the file's SIZE only, never its mtime: external copies and filesystem
                # maintenance change mtimes without changing content, which would force a full re-validation on
                # every startup (measured: FG fast-path hit 0/6704 -> ~100 s warm verify). The path is
                # content-addressed and builds are deterministic, so a same-size file at the same path is the
                # validated file; corruption is still caught loudly by the loader on the real read path.
                _cache_abs_path, _cache_mtime_ns, cache_size = cache_identity
                entry_size = entry.get("cache_size")
                if entry_size is None:
                    cache_hit = False
                else:
                    try:
                        cache_hit = int(entry_size) == int(cache_size)
                    except (TypeError, ValueError):
                        cache_hit = False
            if cache_identity is None:
                try:
                    derived = derived_file(song_path).strip()
                except Exception as exc:
                    logger.debug("frontier_cache:derived_file: %s", exc)
                    derived = ""
                derived_identity = _path_identity(derived) if derived else None
                if derived_identity is not None:
                    cache_file = derived
                    cache_identity = derived_identity
            if cache_identity is not None and not cache_hit:
                try:
                    cache_hit = bool(self.is_complete(cache_file))
                except Exception as exc:
                    logger.debug("frontier_cache:is_complete: %s", exc)
                    cache_hit = False
                if cache_hit:
                    cache_abs_path, cache_mtime_ns, cache_size = cache_identity
                    entries[key] = _manifest_entry(cache_abs_path, cache_mtime_ns, cache_size, abs_path, time.time_ns())
                    validated += 1
            if cache_hit:
                hits.append(song_path)
                recorded_file_by_norm[_normalize_manifest_path(abs_path)] = cache_file
            else:
                misses.append(song_path)

        if persist_validated_entries and validated > 0:
            _save_manifest(
                self.manifest_path(), version=version, version_field=self.manifest_version_field, entries=entries
            )
        if _cache_key_drift(hits, recorded_file_by_norm=recorded_file_by_norm, derived_file=derived_file):
            return FrontierCacheManifestPlan(len(song_paths), (), tuple(song_paths), key_by_norm)
        return FrontierCacheManifestPlan(len(song_paths), tuple(hits), tuple(misses), key_by_norm, validated)

    def record_manifest(self, plan: FrontierCacheManifestPlan, results: Iterable[FrontierCacheBuildResult]) -> int:
        """Record the complete files a build produced for its plan's charts; returns how many."""
        version = self.version()
        entries = _load_manifest(self.manifest_path(), version=version, version_field=self.manifest_version_field)
        recorded = 0
        now_ns = time.time_ns()
        for result in results:
            if result.source not in {"built", "disk", "memory"} or not result.path or not result.cache_file:
                continue
            cache_identity = _path_identity(result.cache_file)
            if cache_identity is None:
                continue
            try:
                if not bool(self.is_complete(result.cache_file)):
                    continue
            except Exception as exc:
                logger.debug("frontier_cache:record_manifest:is_complete: %s", exc)
                continue
            cache_abs_path, cache_mtime_ns, cache_size = cache_identity
            if not os.path.exists(cache_abs_path):
                continue
            key = plan.key_by_norm_path.get(_normalize_manifest_path(result.path))
            if not key:
                continue
            entries[key] = _manifest_entry(
                cache_abs_path, cache_mtime_ns, cache_size, os.path.abspath(result.path), now_ns
            )
            recorded += 1
        if recorded > 0:
            _save_manifest(
                self.manifest_path(), version=version, version_field=self.manifest_version_field, entries=entries
            )
        return recorded


def _normalize_manifest_path(path_text: str) -> str:
    return os.path.abspath(str(path_text or "")).casefold()


def _ref_axes_signature(curves: StatCurves) -> str:
    return bytes(array_sig16(curves.f32["Fever Time"]) + array_sig16(curves.f32["Fever Fill Rate"])).hex()


def _path_identity(path_text: str) -> tuple[str, int, int] | None:
    try:
        abs_path = os.path.abspath(str(path_text))
        st = os.stat(abs_path)
    except OSError as exc:
        logger.debug("frontier_cache:_path_identity: %s", exc)
        return None
    return abs_path, int(st.st_mtime_ns), int(st.st_size)


def _chart_identity(path_text: str) -> tuple[str, str] | None:
    """(absolute path, digest of the chart's bytes), None when it cannot be read."""
    try:
        abs_path = os.path.abspath(str(path_text))
        content = Path(abs_path).read_bytes()
    except OSError as exc:
        logger.debug("frontier_cache:_chart_identity: %s", exc)
        return None
    return abs_path, hashlib.blake2b(content, digest_size=16).hexdigest()


def _manifest_key(
    *,
    cache_version: str,
    ref_sig_hex: str,
    stat_sig_hex: str | None,
    timing_mode: str,
    chart_digest: str,
) -> str:
    parts = [str(cache_version), CACHE_NAMES[str(timing_mode or "non-precise").strip().lower()], str(ref_sig_hex)]
    if stat_sig_hex is not None:
        parts.append(str(stat_sig_hex))
    parts.append(str(chart_digest))
    return hashlib.blake2b("|".join(parts).encode("utf-8"), digest_size=16).hexdigest()


def _manifest_entry(cache_file: str, mtime_ns: int, size: int, song_path: str, updated_at_ns: int) -> dict:
    # The chart path is informational: where the chart was when its file was verified.
    return {
        "cache_file": str(cache_file),
        "cache_mtime_ns": int(mtime_ns),
        "cache_size": int(size),
        "updated_at_ns": int(updated_at_ns),
        "song_path": str(song_path),
    }


def _load_manifest(path: Path, *, version: str, version_field: str) -> dict[str, dict]:
    with _MANIFEST_LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("frontier_cache:_load_manifest: %s", exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        try:
            schema = int(payload.get("schema", 0) or 0)
        except (TypeError, ValueError) as exc:
            logger.debug("frontier_cache:_load_manifest_schema: %s", exc)
            return {}
        if schema != _MANIFEST_SCHEMA or str(payload.get(version_field, "") or "") != str(version):
            return {}
        entries = payload.get("entries", {})
        if not isinstance(entries, dict):
            return {}
        return {str(k): dict(v) for k, v in entries.items() if isinstance(k, str) and isinstance(v, dict)}


def _save_manifest(path: Path, *, version: str, version_field: str, entries: dict[str, dict]) -> None:
    # An entry stays useful while its (content-addressed) file exists, whichever directory its chart is published
    # under; entries whose file is gone are dropped.
    entries = {
        key: entry
        for key, entry in entries.items()
        if isinstance(entry.get("cache_file"), str) and os.path.exists(entry["cache_file"])
    }
    text = json.dumps(
        {"schema": _MANIFEST_SCHEMA, version_field: str(version), "entries": entries},
        separators=(",", ":"),
        ensure_ascii=True,
    )
    with _MANIFEST_LOCK:
        write_atomically(path, lambda tmp: tmp.write_text(text, encoding="utf-8"))


def _cache_key_drift(
    hit_paths: list[str],
    *,
    recorded_file_by_norm: dict[str, str],
    derived_file: Callable[[str], str],
) -> bool:
    """Whether a sample of the hits derives other files than the manifest recorded for them.

    The manifest's identity (version, chart content, FT/FF and stat signatures) cannot see a change of the key
    derivation itself: if the key inputs change without a version change, every recorded entry silently points at a
    file runtime never asks for (the 2026-07-02 incident: changed great_candidates, the fast path kept reporting
    stale bundles as ready, and every affected song failed prep). Deriving a handful of keys costs a few chart parses
    (~50ms each) and turns that into a full re-verify. A chart that fails to parse is not a drift signal (the per-file
    path reports it).
    """
    if not hit_paths:
        return False
    sample_count = max(1, min(_DRIFT_SAMPLE_SIZE, len(hit_paths)))
    step = max(1, len(hit_paths) // sample_count)
    for song_path in hit_paths[::step][:sample_count]:
        recorded = recorded_file_by_norm.get(_normalize_manifest_path(song_path), "")
        if not recorded:
            continue
        try:
            derived = derived_file(song_path)
        except Exception as exc:
            logger.debug("frontier_cache:derived_file: %s", exc)
            continue
        if not derived:
            continue
        if _normalize_manifest_path(derived) != _normalize_manifest_path(recorded):
            logger.warning(
                "[FrontierCacheManifest] Cache-key drift detected: %s derives %s but the manifest "
                "recorded %s. Key-derivation inputs changed without a cache-version bump; dropping "
                "the manifest fast-path for this run (full per-file verify + rebuild).",
                song_path,
                derived,
                recorded,
            )
            return True
    return False


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
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


class PrebuildTally:
    """The results of building one timing mode's missing charts, with progress logs."""

    def __init__(self, cache: FrontierCache, total: int, *, progress_every: int) -> None:
        self.cache = cache
        self.total = int(total)
        self.progress_every = int(progress_every)
        self.started = time.perf_counter()
        self.results: list[FrontierCacheBuildResult] = []
        self.failures = 0
        self.sources: Counter[str] = Counter()

    def add(self, result: FrontierCacheBuildResult) -> None:
        self.results.append(result)
        self.sources[result.source] += 1

    def fail(self, chart_path: str, exc: BaseException, *, songs: int = 1) -> None:
        """A chart's build failed; `songs` counts it with the charts its file would have served too."""
        self.failures += int(songs)
        logger.warning("%s Failed to prebuild %s: %s", self.cache.log_label, chart_path, exc)

    def log_progress(self, latest: FrontierCacheBuildResult) -> None:
        completed = len(self.results)
        if completed == 1 or completed % self.progress_every == 0:
            logger.info(
                "%s %s/%s complete (built=%s disk=%s memory=%s, latest=%s %.1fms)",
                self.cache.log_label,
                completed,
                self.total,
                self.sources["built"],
                self.sources["disk"],
                self.sources["memory"],
                latest.source,
                latest.build_ms,
            )

    def log_ready(self) -> None:
        logger.info(
            "%s Prebuild ready: completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
            self.cache.log_label,
            len(self.results),
            self.total,
            self.failures,
            self.sources["built"],
            self.sources["disk"],
            self.sources["memory"],
            time.perf_counter() - self.started,
        )


def build_frontier_cache_for_chart(
    chart_path: str,
    curves: StatCurves,
    timing_mode: str,
    ensure: Callable[[TimedSong, StatCurves], tuple[str, float, Path]],
) -> FrontierCacheBuildResult:
    """Make sure the chart's song has its cache file; `ensure` returns (source, build ms, file)."""
    source, build_ms, cache_file = ensure(time_song(load_chart(Path(chart_path)), timing_mode), curves)
    return FrontierCacheBuildResult(
        path=str(chart_path), source=str(source), build_ms=float(build_ms), cache_file=str(cache_file)
    )


_prebuild_worker_curves: StatCurves | None = None


def init_prebuild_worker(curves: StatCurves, configure_threads: Callable[[int], object], threads: int) -> None:
    """Process-pool initializer of a prebuild worker: its CPU placement, its build threads and the run's curves."""
    global _prebuild_worker_curves
    pin_frontier_prebuild_worker()
    configure_threads(max(1, int(threads)))
    _prebuild_worker_curves = curves


def prebuild_worker_curves() -> StatCurves:
    if _prebuild_worker_curves is None:
        raise RuntimeError("prebuild worker was not initialized with stat curves")
    return _prebuild_worker_curves


def ordered_frontier_cache_song_paths(
    *,
    queue_paths: Iterable[str],
    data_root: str | os.PathLike[str] | None = None,
) -> list[str]:
    """The queued charts without repeats; every chart under `data_root` (default: the Data directory) when none are
    queued."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(path_text: str) -> None:
        path = str(path_text or "").strip()
        if not path:
            return
        key = os.path.abspath(path).casefold()
        if key in seen:
            return
        seen.add(key)
        ordered.append(path)

    for path in queue_paths:
        add(path)
    if ordered:
        return ordered
    root = Path(data_root) if data_root else paths().data_dir
    charts: list[Path] = []
    for difficulty in DIFFICULTIES:
        folder = root / str(difficulty)
        if folder.exists():
            charts.extend(path for path in folder.rglob("*.txt") if path.is_file())
    for path in sorted(charts, key=lambda item: str(item).lower()):
        add(str(path))
    return ordered


@dataclass(frozen=True)
class FrontierCachePrebuild:
    """How one cache's startup prebuild builds the charts its manifest misses and keeps its directory."""

    cache: FrontierCache
    # The missing charts of one timing mode -> their results (the cache's build scheduler).
    build_songs: Callable[[list[str], StatCurves, str], PrebuildTally]
    # Under the build lock, once the manifest plan is known: (plan, build_missing, authorize_destructive_rotation).
    maintain: Callable[[FrontierCacheManifestPlan, bool, bool], None]
    # After a build's files were recorded in the manifest: the number of files built.
    after_build: Callable[[int], None] | None = None


def prebuild_frontier_cache(
    prebuild: FrontierCachePrebuild,
    *,
    song_queue: Iterable[tuple],
    curves: StatCurves,
    data_root: str | os.PathLike[str] | None = None,
    build_missing: bool = True,
    authorize_destructive_rotation: bool = False,
    timing_modes: Iterable[str] = TIMING_MODES,
) -> FrontierCachePrebuildSummary:
    """Verify the cache files of the queued charts (all charts under `data_root` for an empty queue) in each timing
    mode and build the missing ones; with `build_missing` False a missing file counts as a failure."""
    started = time.perf_counter()
    queue_paths = [str(item[0]) for item in song_queue or () if isinstance(item, tuple) and item]
    song_paths = ordered_frontier_cache_song_paths(queue_paths=queue_paths, data_root=data_root)
    summaries = [
        _prebuild_timing_mode(
            prebuild, song_paths, curves, str(mode or "").strip().lower(), build_missing, authorize_destructive_rotation
        )
        for mode in timing_modes
    ]
    return FrontierCachePrebuildSummary(
        total=sum(summary.total for summary in summaries),
        completed=sum(summary.completed for summary in summaries),
        failures=sum(summary.failures for summary in summaries),
        built=sum(summary.built for summary in summaries),
        disk=sum(summary.disk for summary in summaries),
        memory=sum(summary.memory for summary in summaries),
        elapsed_ms=_elapsed_ms(started),
    )


def _prebuild_timing_mode(
    prebuild: FrontierCachePrebuild,
    song_paths: list[str],
    curves: StatCurves,
    timing_mode: str,
    build_missing: bool,
    authorize_destructive_rotation: bool,
) -> FrontierCachePrebuildSummary:
    cache = prebuild.cache
    started = time.perf_counter()
    if not song_paths:
        return FrontierCachePrebuildSummary()
    if not authorize_destructive_rotation and cache.manifest_records_current_version():
        # Charts the manifest records are readers, not builders: probe without the lock and without writing the
        # manifest, so they never wait behind another process's build. Files to record go through the lock below.
        probe = cache.manifest_plan(song_paths, curves, timing_mode=timing_mode, persist_validated_entries=False)
        if not probe.missing_paths and probe.validated_entry_count == 0:
            return FrontierCachePrebuildSummary(
                total=probe.total_paths,
                completed=probe.hit_count,
                disk=probe.hit_count,
                elapsed_ms=_elapsed_ms(started),
            )

    # One builder per directory: a concurrent process waits here, then its plan hits what this one wrote instead of
    # duplicating the build (and its peak memory).
    with FrontierBuildLock(cache.directory(), label=cache.name):
        plan = cache.manifest_plan(song_paths, curves, timing_mode=timing_mode)
        hits = plan.hit_count
        if hits:
            logger.info(
                "%s Manifest fast-hit skipped %s/%s song(s) before worker parse/build.",
                cache.log_label,
                hits,
                plan.total_paths,
            )
        prebuild.maintain(plan, build_missing, authorize_destructive_rotation)
        if not plan.missing_paths:
            return FrontierCachePrebuildSummary(
                total=plan.total_paths, completed=hits, disk=hits, elapsed_ms=_elapsed_ms(started)
            )
        if not build_missing:
            logger.error(
                "%s Frontier server publication is missing %s required song cache(s).",
                cache.log_label,
                len(plan.missing_paths),
            )
            return FrontierCachePrebuildSummary(
                total=plan.total_paths,
                completed=hits,
                failures=len(plan.missing_paths),
                disk=hits,
                elapsed_ms=_elapsed_ms(started),
            )
        tally = prebuild.build_songs(list(plan.missing_paths), curves, timing_mode)
        cache.record_manifest(plan, tally.results)
        elapsed_ms = _elapsed_ms(started)
        if prebuild.after_build is not None:
            prebuild.after_build(tally.sources["built"])
        return FrontierCachePrebuildSummary(
            total=plan.total_paths,
            completed=hits + len(tally.results),
            failures=tally.failures,
            built=tally.sources["built"],
            disk=hits + tally.sources["disk"],
            memory=tally.sources["memory"],
            elapsed_ms=elapsed_ms,
        )


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0
