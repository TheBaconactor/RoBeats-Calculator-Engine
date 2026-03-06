from __future__ import annotations

import atexit
import http.client
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from .core.constants import BIN_DIR, PATHS
from .data.database import get_evolution_db_path

_TRUTHY = {"1", "true", "yes", "on"}
_DEFAULT_VISIT_TTL_SECONDS = 60 * 60 * 24
_DEFAULT_SONG_REPEATS = 25
_DEFAULT_INFLIGHT_SONGS = 30
_DEFAULT_MAX_PENDING_VISITS = 10
_VISIT_SCOPE_ENV = "ROBEATSMETA_OPTIMIZER_VISIT_SCOPE"


def _env_bool_override(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    return str(raw or "").strip().lower() in _TRUTHY


def _runtime_timestamp(now: int | float | None = None) -> int:
    if now is None:
        return int(time.time_ns() // 1_000_000)
    try:
        return int(now)
    except Exception:
        return int(time.time_ns() // 1_000_000)


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return str(raw or "").strip().lower() in _TRUTHY


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _build_bundle_key(*, title: str = "", artist: str = "", song_id: str = "") -> str:
    normalized_title = _normalize_text(title)
    normalized_artist = _normalize_text(artist)
    if normalized_title or normalized_artist:
        return f"{normalized_title}|{normalized_artist}"
    return f"song:{_normalize_text(song_id)}"


def _normalize_visit_scope(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"family", "bundle", "song-family", "song_family", "all-difficulties", "all_difficulties"}:
        return "family"
    return "song"


def _strip_run_suffix(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"\s*\(Run\s+\d+\s*/\s*\d+\)\s*$", "", text).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


@dataclass(frozen=True)
class SongBundleRef:
    song_id: str
    title: str
    artist: str
    bundle_key: str


@contextmanager
def _file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt

            try:
                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                handle.seek(0)
            except Exception:
                pass
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            handle.close()
        except Exception:
            pass


class RoBeatsMetaOptimizerApi:
    """
    Small file-backed bridge between the website backend and the long-running optimizer.

    The backend records song visits here. The optimizer polls the same state and
    moves requested song bundles (all difficulties for the same title/artist) to
    the front of the next work slice.
    """

    _backend_compat_cache: dict[tuple[str, str], bool] = {}

    @staticmethod
    def _resolve_song_meta_index_path_static() -> Path:
        configured = str(os.environ.get("ROBEATSMETA_SONG_META_INDEX_PATH", "") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()

        candidates = [
            Path(PATHS.script_dir).resolve().parent / "RoBeatsMeta" / "Data" / "song_meta_index.json",
            Path(PATHS.script_dir).resolve() / "Data" / "song_meta_index.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def __init__(
        self,
        *,
        state_path: str | os.PathLike[str] | None = None,
        song_meta_index_path: str | os.PathLike[str] | None = None,
        status_path: str | os.PathLike[str] | None = None,
        visit_ttl_seconds: int | None = None,
        publish_runtime_status: bool = True,
    ) -> None:
        self._state_path = Path(state_path) if state_path else self._resolve_state_path()
        self._lock_path = self._state_path.with_suffix(self._state_path.suffix + ".lock")
        self._status_path = Path(status_path) if status_path else self._resolve_status_path()
        self._status_lock_path = self._status_path.with_suffix(self._status_path.suffix + ".lock")
        self._song_meta_index_path = (
            Path(song_meta_index_path) if song_meta_index_path else self._resolve_song_meta_index_path()
        )
        ttl_override = visit_ttl_seconds
        if ttl_override is None:
            ttl_override = _safe_int(os.environ.get("ROBEATSMETA_OPTIMIZER_VISIT_TTL_SECONDS"), _DEFAULT_VISIT_TTL_SECONDS)
        self._visit_ttl_seconds = max(60, int(ttl_override))
        self._max_pending_visits = max(
            1,
            _safe_int(os.environ.get("ROBEATSMETA_OPTIMIZER_MAX_PENDING_VISITS"), _DEFAULT_MAX_PENDING_VISITS),
        )
        self._song_meta_mtime_ns: int | None = None
        self._bundle_by_song_id: dict[str, SongBundleRef] = {}
        self._song_ids_by_bundle_key: dict[str, set[str]] = {}
        self._last_task_priority_signature: tuple[tuple[str, int, int], ...] | None = None
        self._visit_scope = _normalize_visit_scope(os.environ.get(_VISIT_SCOPE_ENV, "song"))
        self._visit_family_mode = self._visit_scope == "family"
        try:
            self._backend_mode_enabled = bool(
                self.service_mode_enabled(song_meta_index_path=self._song_meta_index_path)
            )
        except Exception:
            self._backend_mode_enabled = False
        self._publish_runtime_status = bool(publish_runtime_status)
        self._runtime_status_push_url = self._resolve_runtime_status_push_url() if self._publish_runtime_status else ""
        self._runtime_status_push_token = str(os.environ.get("ROBEATSMETA_OPTIMIZER_STATUS_PUSH_TOKEN", "") or "").strip()
        self._runtime_status_push_fail_until = 0.0
        self._runtime_status_push_failure_count = 0
        self._last_runtime_status_snapshot: dict[str, Any] | None = None
        self._runtime_status_state_lock = threading.Lock()
        self._runtime_status_pending_event = threading.Event()
        self._runtime_status_flushed_event = threading.Event()
        self._runtime_status_flushed_event.set()
        self._runtime_status_stop = False
        self._runtime_status_pending: dict[str, Any] | None = None
        self._runtime_status_current: dict[str, Any] | None = None
        self._runtime_status_http_conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None
        self._runtime_status_http_conn_key: tuple[str, str, int] | None = None
        self._runtime_status_heartbeat_interval_sec = (
            5.0 if str(self._runtime_status_push_url or "").strip() else 0.0
        )
        self._runtime_status_last_push_monotonic = 0.0
        self._runtime_status_current = self.read_runtime_status()
        self._runtime_status_thread = threading.Thread(
            target=self._runtime_status_loop,
            name="RoBeatsMetaStatusWriter",
            daemon=True,
        )
        self._runtime_status_thread.start()
        if self._publish_runtime_status:
            atexit.register(self._publish_runtime_status_unavailable_at_exit)
        try:
            self._runtime_status_push_timeout_sec = max(
                0.05,
                float(os.environ.get("ROBEATSMETA_OPTIMIZER_STATUS_PUSH_TIMEOUT_SEC", "0.35") or "0.35"),
            )
        except Exception:
            self._runtime_status_push_timeout_sec = 0.35
        if self._publish_runtime_status:
            # Advertise liveness immediately so the website can show the optimizer bar
            # even before the first song queue is prepared.
            self.update_runtime_status(
                available=True,
                status="idle",
                current_song="",
                completed=0,
                total=0,
                failed=0,
            )
            try:
                self.flush_runtime_status(timeout=1.0)
            except Exception:
                pass

    @classmethod
    def _backend_compatible_detected(cls, *, song_meta_index_path: str | os.PathLike[str] | None = None) -> bool:
        try:
            index_path = (
                Path(song_meta_index_path).expanduser().resolve()
                if song_meta_index_path is not None
                else cls._resolve_song_meta_index_path_static()
            )
        except Exception:
            index_path = None

        if index_path is None or not index_path.exists():
            return False

        try:
            canonical_db_path = Path(get_evolution_db_path()).expanduser().resolve()
        except Exception:
            canonical_db_path = None

        if canonical_db_path is None or not canonical_db_path.exists():
            return False
        key = (str(index_path), str(canonical_db_path))
        cached = cls._backend_compat_cache.get(key)
        if cached is not None:
            return bool(cached)
        cls._backend_compat_cache[key] = True
        return True

    @classmethod
    def service_mode_enabled(cls, *, song_meta_index_path: str | os.PathLike[str] | None = None) -> bool:
        forced = _env_bool_override("ROBEATSMETA_OPTIMIZER_SERVICE_MODE")
        if forced is not None:
            return bool(forced)
        return cls._backend_compatible_detected(song_meta_index_path=song_meta_index_path)

    @classmethod
    def benchmark_mode_enabled(cls) -> bool:
        return _env_truthy("ROBEATSMETA_OPTIMIZER_BENCHMARK_MODE")

    @classmethod
    def priority_queue_enabled(cls) -> bool:
        forced = _env_bool_override("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE")
        if forced is not None:
            return bool(forced)
        return cls.service_mode_enabled()

    def backend_mode_enabled(self) -> bool:
        return bool(getattr(self, "_backend_mode_enabled", False))

    def service_defaults_enabled(self) -> bool:
        if not self.backend_mode_enabled():
            return False
        forced = _env_bool_override("ROBEATSMETA_OPTIMIZER_SERVICE_DEFAULTS")
        if forced is not None:
            return bool(forced)
        return True

    def apply_service_defaults(self, cfg: Any) -> bool:
        if not self.backend_mode_enabled() or cfg is None or not self.service_defaults_enabled():
            return False

        if not cfg.has_section("IterationEngine"):
            cfg.add_section("IterationEngine")
        if not cfg.has_section("CalculateSong"):
            cfg.add_section("CalculateSong")

        # Backend-special behavior: keep the optimizer in continuous service mode and
        # evaluate full song families so live backend overlays can update during runtime.
        cfg.set("IterationEngine", "LoopForever", "false" if self.benchmark_mode_enabled() else "true")
        cfg.set("IterationEngine", "SongRepeats", str(int(_DEFAULT_SONG_REPEATS)))
        cfg.set("IterationEngine", "UseEvolutionDB", "true")
        cfg.set("IterationEngine", "InFlightSongs", str(int(_DEFAULT_INFLIGHT_SONGS)))

        # Backend-special behavior: process all difficulties for the selected song family.
        cfg.set("CalculateSong", "Difficulty", "All")
        cfg.set("CalculateSong", "Song_Name", "")
        cfg.set("CalculateSong", "TargetPrimary", "all")
        cfg.set("CalculateSong", "TargetSecondary", "all")
        return True

    def record_song_visit(
        self,
        *,
        song_id: str,
        title: str | None = None,
        artist: str | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        bundle = self._resolve_bundle(song_id=song_id, title=title, artist=artist)
        if not bundle.bundle_key:
            return {"queued": False, "reason": "invalid_song"}

        ts = _safe_int(now if now is not None else time.time())
        with _file_lock(self._lock_path):
            state = self._load_state_unlocked()
            changed = self._prune_state_unlocked(state, ts)
            entries = state.setdefault("entries", {})
            entry = entries.get(bundle.bundle_key)
            if not isinstance(entry, dict):
                entry = {}
            active_bundle_key = str(state.get("active_bundle_key") or "").strip()

            last_computed_at = _safe_int(entry.get("last_computed_at"), 0)
            last_requested_at = _safe_int(entry.get("last_requested_at"), 0)
            entry.update(
                {
                    "song_id": bundle.song_id,
                    "title": bundle.title,
                    "artist": bundle.artist,
                    "bundle_key": bundle.bundle_key,
                }
            )

            if active_bundle_key == str(bundle.bundle_key or "").strip():
                entries[bundle.bundle_key] = entry
                if changed:
                    self._write_state_unlocked(state)
                return {
                    "queued": False,
                    "reason": "already_processing",
                    "bundle_key": bundle.bundle_key,
                }

            # Family mode optimization: if this family already exists in DB and the state file was
            # reset, avoid re-queueing all difficulties immediately.
            if self._visit_family_mode and last_computed_at <= 0:
                try:
                    from .data.database import get_song_names_present_in_db
                except Exception:
                    get_song_names_present_in_db = None
                if get_song_names_present_in_db is not None:
                    try:
                        song_ids: set[str] = set()
                        cached_ids = self._song_ids_by_bundle_key.get(str(bundle.bundle_key or "").strip())
                        if isinstance(cached_ids, set):
                            song_ids.update(str(s or "").strip() for s in cached_ids if str(s or "").strip())
                        if str(bundle.song_id or "").strip():
                            song_ids.add(str(bundle.song_id).strip())
                        present = get_song_names_present_in_db(song_ids)
                        if present:
                            entry["last_computed_at"] = ts
                            entries[bundle.bundle_key] = entry
                            self._write_state_unlocked(state)
                            self._last_task_priority_signature = None
                            return {
                                "queued": False,
                                "reason": "fresh_compute",
                                "bundle_key": bundle.bundle_key,
                                "last_computed_at": ts,
                                "db_present": True,
                            }
                    except Exception:
                        pass

            if last_computed_at > 0 and ts - last_computed_at < self._visit_ttl_seconds:
                entries[bundle.bundle_key] = entry
                if changed:
                    self._write_state_unlocked(state)
                return {
                    "queued": False,
                    "reason": "fresh_compute",
                    "bundle_key": bundle.bundle_key,
                    "last_computed_at": last_computed_at,
                }

            if last_requested_at > last_computed_at:
                entries[bundle.bundle_key] = entry
                if changed:
                    self._write_state_unlocked(state)
                return {
                    "queued": False,
                    "reason": "already_queued",
                    "bundle_key": bundle.bundle_key,
                }

            pending_count = 0
            for raw_entry in entries.values():
                if not isinstance(raw_entry, dict):
                    continue
                requested_at = _safe_int(raw_entry.get("last_requested_at"), 0)
                computed_at = _safe_int(raw_entry.get("last_computed_at"), 0)
                if requested_at > computed_at:
                    pending_count += 1
            if pending_count >= int(self._max_pending_visits):
                if changed:
                    self._write_state_unlocked(state)
                return {
                    "queued": False,
                    "reason": "queue_full",
                    "bundle_key": bundle.bundle_key,
                    "max_pending_visits": int(self._max_pending_visits),
                }

            entry["last_requested_at"] = ts
            entries[bundle.bundle_key] = entry
            self._write_state_unlocked(state)
            return {
                "queued": True,
                "bundle_key": bundle.bundle_key,
                "song_id": bundle.song_id,
                "title": bundle.title,
                "artist": bundle.artist,
            }

    def mark_song_computed(self, *, song_id: str, now: int | None = None) -> bool:
        bundle = self._resolve_bundle(song_id=song_id)
        if not bundle.bundle_key:
            return False

        ts = _safe_int(now if now is not None else time.time())
        with _file_lock(self._lock_path):
            state = self._load_state_unlocked()
            changed = self._prune_state_unlocked(state, ts)
            entries = state.setdefault("entries", {})
            entry = entries.get(bundle.bundle_key)
            if not isinstance(entry, dict):
                if changed:
                    self._write_state_unlocked(state)
                self._last_task_priority_signature = None
                return False

            next_entry = dict(entry)
            next_entry.update(
                {
                    "song_id": bundle.song_id or str(entry.get("song_id") or ""),
                    "title": bundle.title or str(entry.get("title") or ""),
                    "artist": bundle.artist or str(entry.get("artist") or ""),
                    "bundle_key": bundle.bundle_key,
                    "last_computed_at": ts,
                }
            )
            if str(state.get("active_bundle_key") or "").strip() == str(bundle.bundle_key or "").strip():
                state["active_bundle_key"] = ""
            if next_entry != entry or changed:
                entries[bundle.bundle_key] = next_entry
                self._write_state_unlocked(state)
            self._last_task_priority_signature = None
            return True

    def recently_computed_bundle_keys(self, *, now: int | None = None) -> set[str]:
        ts = _safe_int(now if now is not None else time.time())
        with _file_lock(self._lock_path):
            state = self._load_state_unlocked()
            changed = self._prune_state_unlocked(state, ts)
            entries = state.get("entries", {})
            recent: set[str] = set()
            if isinstance(entries, dict):
                for bundle_key, raw_entry in entries.items():
                    if not isinstance(raw_entry, dict):
                        continue
                    requested_at = _safe_int(raw_entry.get("last_requested_at"), 0)
                    computed_at = _safe_int(raw_entry.get("last_computed_at"), 0)
                    if computed_at <= 0:
                        continue
                    if computed_at < requested_at:
                        continue
                    if ts - computed_at >= self._visit_ttl_seconds:
                        continue
                    recent.add(str(bundle_key or "").strip())
            if changed:
                self._write_state_unlocked(state)
        return {key for key in recent if key}

    def prioritize_song_queue(
        self,
        song_queue: Sequence[tuple[str, str, str]],
        *,
        now: int | None = None,
    ) -> list[tuple[str, str, str]]:
        if not song_queue:
            return []

        pending, _signature = self._pending_bundle_state(now=now)
        if not pending:
            return list(song_queue)

        order = {bundle_key: idx for idx, bundle_key in enumerate(pending)}
        grouped: list[list[tuple[str, str, str]]] = [[] for _ in pending]
        remainder: list[tuple[str, str, str]] = []
        for item in song_queue:
            if not isinstance(item, tuple) or len(item) < 2:
                remainder.append(item)
                continue
            song_name = str(item[1] or "").strip()
            bundle_key = self._bundle_key_for_song_id(song_name)
            position = order.get(bundle_key)
            if position is None:
                remainder.append(item)
                continue
            grouped[position].append(item)
        prioritized = [item for bucket in grouped for item in bucket]
        prioritized.extend(remainder)
        return prioritized

    def reprioritize_pending_tasks(
        self,
        tasks: list[tuple],
        *,
        start_index: int = 0,
        now: int | None = None,
    ) -> bool:
        if not tasks:
            self._last_task_priority_signature = None
            return False

        safe_start = max(0, min(int(start_index), len(tasks)))
        pending, signature = self._pending_bundle_state(now=now)
        if signature == self._last_task_priority_signature:
            return False
        self._last_task_priority_signature = signature

        if not pending or safe_start >= len(tasks):
            return False

        order = {bundle_key: idx for idx, bundle_key in enumerate(pending)}
        remaining = list(tasks[safe_start:])
        grouped: list[list[tuple]] = [[] for _ in pending]
        remainder: list[tuple] = []
        for task in remaining:
            song_name = self._task_song_name(task)
            bundle_key = self._bundle_key_for_song_id(song_name)
            position = order.get(bundle_key)
            if position is None:
                remainder.append(task)
                continue
            grouped[position].append(task)

        reordered = [task for bucket in grouped for task in bucket]
        reordered.extend(remainder)
        if reordered == remaining:
            return False
        tasks[safe_start:] = reordered
        return True

    def mark_song_started(self, *, song_id: str) -> None:
        bundle = self._resolve_bundle(song_id=song_id)
        with _file_lock(self._lock_path):
            state = self._load_state_unlocked()
            state["active_bundle_key"] = str(bundle.bundle_key or "").strip()
            self._write_state_unlocked(state)

    def _pending_bundle_state(self, *, now: int | None = None) -> tuple[list[str], tuple[tuple[str, int, int], ...]]:
        ts = _safe_int(now if now is not None else time.time())
        with _file_lock(self._lock_path):
            state = self._load_state_unlocked()
            changed = self._prune_state_unlocked(state, ts)
            entries = state.get("entries", {})
            pending_rows: list[tuple[str, int, int]] = []
            if isinstance(entries, dict):
                for bundle_key, raw_entry in entries.items():
                    if not isinstance(raw_entry, dict):
                        continue
                    requested_at = _safe_int(raw_entry.get("last_requested_at"), 0)
                    computed_at = _safe_int(raw_entry.get("last_computed_at"), 0)
                    if requested_at <= 0:
                        continue
                    if ts - requested_at >= self._visit_ttl_seconds:
                        continue
                    if requested_at <= computed_at:
                        continue
                    pending_rows.append((str(bundle_key or ""), requested_at, computed_at))
            pending_rows.sort(key=lambda row: (-row[1], row[0]))
            if changed:
                self._write_state_unlocked(state)
        bundle_keys = [row[0] for row in pending_rows if row[0]]
        signature = tuple((row[0], int(row[1]), int(row[2])) for row in pending_rows if row[0])
        return bundle_keys, signature

    def _resolve_state_path(self) -> Path:
        configured = str(os.environ.get("ROBEATSMETA_OPTIMIZER_PRIORITY_STATE_PATH", "") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        return Path(BIN_DIR).resolve() / "robeatsmeta_song_priority_queue.json"

    def _resolve_song_meta_index_path(self) -> Path:
        return self._resolve_song_meta_index_path_static()

    def _resolve_status_path(self) -> Path:
        configured = str(os.environ.get("ROBEATSMETA_OPTIMIZER_STATUS_PATH", "") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        return Path(BIN_DIR).resolve() / "robeatsmeta_optimizer_status.json"

    def _resolve_runtime_status_push_url(self) -> str:
        configured = str(os.environ.get("ROBEATSMETA_OPTIMIZER_STATUS_PUSH_URL", "") or "").strip()
        if configured:
            return configured
        if self.backend_mode_enabled():
            return "http://127.0.0.1:8000/robeatsmeta/internal/optimizer/status"
        return ""

    def _push_runtime_status_direct(self, state: dict[str, Any]) -> None:
        push_url = str(self._runtime_status_push_url or "").strip()
        if not push_url:
            return
        now_ts = float(time.time())
        if now_ts < float(self._runtime_status_push_fail_until or 0.0):
            return

        try:
            parsed = urlsplit(push_url)
            scheme = str(parsed.scheme or "http").strip().lower()
            host = str(parsed.hostname or "").strip()
            if not host:
                return
            port = int(parsed.port or (443 if scheme == "https" else 80))
            path = str(parsed.path or "/").strip() or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            body = json.dumps(
                {
                    "available": bool(state.get("available", True)),
                    "status": str(state.get("status") or ""),
                    "current_song": str(state.get("current_song") or ""),
                    "completed": _safe_int(state.get("completed"), 0),
                    "total": _safe_int(state.get("total"), 0),
                    "failed": _safe_int(state.get("failed"), 0),
                    "updated_at": _safe_int(state.get("updated_at"), 0),
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            }
            if self._runtime_status_push_token:
                headers["X-RoBeatsMeta-Optimizer-Token"] = self._runtime_status_push_token

            headers["Connection"] = "close"
            connection_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
            conn = connection_cls(host, port, timeout=float(self._runtime_status_push_timeout_sec))
            try:
                conn.request("POST", path, body=body, headers=headers)
                response = conn.getresponse()
                response.read()
                if int(response.status) < 200 or int(response.status) >= 300:
                    raise RuntimeError(f"optimizer status push HTTP {int(response.status)}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

            self._runtime_status_push_failure_count = 0
            self._runtime_status_push_fail_until = 0.0
        except Exception as exc:
            self._runtime_status_push_failure_count = min(8, int(self._runtime_status_push_failure_count) + 1)
            backoff = min(10.0, 0.5 * (2 ** max(0, self._runtime_status_push_failure_count - 1)))
            self._runtime_status_push_fail_until = float(time.time()) + float(backoff)
            logging.getLogger(__name__).warning(
                "Failed to push optimizer runtime status directly: %s: %s",
                type(exc).__name__,
                exc,
            )

    def _runtime_status_loop(self) -> None:
        while True:
            heartbeat = float(self._runtime_status_heartbeat_interval_sec or 0.0)
            signaled = self._runtime_status_pending_event.wait(timeout=heartbeat if heartbeat > 0.0 else None)
            if self._runtime_status_stop:
                return
            if not signaled:
                if heartbeat <= 0.0:
                    continue
                with self._runtime_status_state_lock:
                    state = dict(self._runtime_status_current or {})
                if not state:
                    continue
                # Keep heartbeat timestamps moving during long GPU-bound spans so
                # backend/UI can observe liveness even without song/progress deltas.
                state["updated_at"] = _safe_int(time.time() * 1000.0)
                with self._runtime_status_state_lock:
                    self._runtime_status_current = dict(state)
                try:
                    self._push_runtime_status_direct(state)
                    self._runtime_status_last_push_monotonic = time.monotonic()
                except Exception:
                    pass
                continue
            while True:
                with self._runtime_status_state_lock:
                    state = dict(self._runtime_status_pending or {}) if self._runtime_status_pending is not None else None
                    self._runtime_status_pending = None
                    if state is None:
                        self._runtime_status_pending_event.clear()
                        self._runtime_status_flushed_event.set()
                        break
                    self._runtime_status_flushed_event.clear()
                try:
                    self._push_runtime_status_direct(state)
                    self._runtime_status_last_push_monotonic = time.monotonic()
                except Exception:
                    pass
                with self._runtime_status_state_lock:
                    self._runtime_status_current = dict(state)
                    if self._runtime_status_pending is None:
                        self._runtime_status_pending_event.clear()
                        self._runtime_status_flushed_event.set()
                        break

    def _resolve_bundle(self, *, song_id: str, title: str | None = None, artist: str | None = None) -> SongBundleRef:
        cleaned_song_id = _strip_run_suffix(str(song_id or "").strip())
        cleaned_title = str(title or "").strip()
        cleaned_artist = str(artist or "").strip()

        if not self._visit_family_mode:
            return SongBundleRef(
                song_id=cleaned_song_id,
                title=cleaned_title,
                artist=cleaned_artist,
                bundle_key=_build_bundle_key(song_id=cleaned_song_id),
            )

        self._refresh_song_meta_cache()
        cached = self._bundle_by_song_id.get(cleaned_song_id)
        if cached is not None:
            title_value = cleaned_title or cached.title
            artist_value = cleaned_artist or cached.artist
            return SongBundleRef(
                song_id=cleaned_song_id or cached.song_id,
                title=title_value,
                artist=artist_value,
                bundle_key=_build_bundle_key(title=title_value, artist=artist_value, song_id=cleaned_song_id or cached.song_id),
            )

        return SongBundleRef(
            song_id=cleaned_song_id,
            title=cleaned_title,
            artist=cleaned_artist,
            bundle_key=_build_bundle_key(title=cleaned_title, artist=cleaned_artist, song_id=cleaned_song_id),
        )

    def _bundle_key_for_song_id(self, song_id: str) -> str:
        return self._resolve_bundle(song_id=song_id).bundle_key

    def _refresh_song_meta_cache(self) -> None:
        path = self._song_meta_index_path
        try:
            mtime_ns = int(path.stat().st_mtime_ns)
        except OSError:
            mtime_ns = -1
        if self._song_meta_mtime_ns == mtime_ns:
            return

        bundle_by_song_id: dict[str, SongBundleRef] = {}
        song_ids_by_bundle_key: dict[str, set[str]] = {}
        if mtime_ns >= 0:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                payload = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    song_id = str(item.get("id") or "").strip()
                    if not song_id:
                        continue
                    title = str(item.get("title") or "").strip()
                    artist = str(item.get("artist") or "").strip()
                    bundle = SongBundleRef(
                        song_id=song_id,
                        title=title,
                        artist=artist,
                        bundle_key=_build_bundle_key(title=title, artist=artist, song_id=song_id),
                    )
                    bundle_by_song_id[song_id] = bundle
                    song_ids_by_bundle_key.setdefault(str(bundle.bundle_key or "").strip(), set()).add(song_id)

        self._bundle_by_song_id = bundle_by_song_id
        self._song_ids_by_bundle_key = song_ids_by_bundle_key
        self._song_meta_mtime_ns = mtime_ns

    def _load_state_unlocked(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        entries = raw.get("entries")
        if not isinstance(entries, dict):
            entries = {}
        active_bundle_key = str(raw.get("active_bundle_key") or "").strip()
        return {"version": 1, "entries": entries, "active_bundle_key": active_bundle_key}

    def _load_status_unlocked(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._status_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        return {
            "version": 1,
            "available": bool(raw.get("available", False)),
            "status": str(raw.get("status") or "idle"),
            "current_song": str(raw.get("current_song") or ""),
            "completed": _safe_int(raw.get("completed"), 0),
            "total": _safe_int(raw.get("total"), 0),
            "failed": _safe_int(raw.get("failed"), 0),
            "updated_at": _safe_int(raw.get("updated_at"), 0),
        }

    def _write_state_unlocked(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=True)
        tmp_path = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        os.replace(tmp_path, self._state_path)

    def _write_status_unlocked(self, state: dict[str, Any]) -> None:
        self._status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=True)
        tmp_path = self._status_path.with_suffix(self._status_path.suffix + ".tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        os.replace(tmp_path, self._status_path)

    def _prune_state_unlocked(self, state: dict[str, Any], now: int) -> bool:
        entries = state.get("entries")
        if not isinstance(entries, dict):
            state["entries"] = {}
            return True

        changed = False
        cutoff = int(now) - int(self._visit_ttl_seconds)
        keep: dict[str, Any] = {}
        for bundle_key, raw_entry in entries.items():
            if not isinstance(raw_entry, dict):
                changed = True
                continue
            requested_at = _safe_int(raw_entry.get("last_requested_at"), 0)
            computed_at = _safe_int(raw_entry.get("last_computed_at"), 0)
            last_activity = max(requested_at, computed_at)
            if last_activity > 0 and last_activity < cutoff:
                changed = True
                continue
            keep[str(bundle_key)] = raw_entry
        if keep != entries:
            state["entries"] = keep
            changed = True
        return changed

    def update_runtime_status(
        self,
        *,
        available: bool | None = None,
        status: str | None = None,
        current_song: str | None = None,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
        now: int | None = None,
    ) -> dict[str, Any]:
        ts = _runtime_timestamp(now)
        with self._runtime_status_state_lock:
            state = dict(self._runtime_status_current or {})
            if not state:
                state = self._load_status_unlocked()
            if available is None:
                state["available"] = True
            else:
                state["available"] = bool(available)
            if status is not None:
                state["status"] = str(status or "").strip() or state.get("status") or "idle"
            if current_song is not None:
                state["current_song"] = str(current_song or "").strip()
            if completed is not None:
                state["completed"] = max(0, int(completed))
            if total is not None:
                state["total"] = max(0, int(total))
            if failed is not None:
                state["failed"] = max(0, int(failed))
            comparable_state = {
                "available": bool(state.get("available", True)),
                "status": str(state.get("status") or ""),
                "current_song": str(state.get("current_song") or ""),
                "completed": _safe_int(state.get("completed"), 0),
                "total": _safe_int(state.get("total"), 0),
                "failed": _safe_int(state.get("failed"), 0),
            }
            if comparable_state == (self._last_runtime_status_snapshot or {}):
                return dict(state)
            state["updated_at"] = ts
            self._last_runtime_status_snapshot = dict(comparable_state)
            self._runtime_status_current = dict(state)
            self._runtime_status_pending = dict(state)
            self._runtime_status_flushed_event.clear()
            self._runtime_status_pending_event.set()
            return dict(state)

    def clear_runtime_status(
        self,
        *,
        status: str = "idle",
        now: int | None = None,
        available: bool = True,
    ) -> dict[str, Any]:
        return self.update_runtime_status(
            available=available,
            status=status,
            current_song="",
            completed=0,
            total=0,
            failed=0,
            now=now,
        )

    def _publish_runtime_status_unavailable_at_exit(self) -> None:
        state = {
            "available": False,
            "status": "unavailable",
            "current_song": "",
            "completed": 0,
            "total": 0,
            "failed": 0,
            "updated_at": _runtime_timestamp(None),
        }
        try:
            with self._runtime_status_state_lock:
                self._runtime_status_current = dict(state)
                self._runtime_status_pending = None
            self._push_runtime_status_direct(state)
        except Exception:
            pass
        try:
            self._runtime_status_stop = True
            self._runtime_status_pending_event.set()
        except Exception:
            pass

    def stop_runtime_status_loop(self, *, timeout: float = 1.0) -> None:
        try:
            self._runtime_status_stop = True
            self._runtime_status_pending_event.set()
        except Exception:
            pass
        try:
            if self._runtime_status_thread.is_alive():
                self._runtime_status_thread.join(timeout=max(0.0, float(timeout)))
        except Exception:
            pass
        try:
            conn = self._runtime_status_http_conn
            if conn is not None:
                conn.close()
        except Exception:
            pass
        finally:
            self._runtime_status_http_conn = None
            self._runtime_status_http_conn_key = None

    def read_runtime_status(self) -> dict[str, Any]:
        with self._runtime_status_state_lock:
            if self._runtime_status_current:
                return dict(self._runtime_status_current)
        return {
            "version": 1,
            "available": False,
            "status": "idle",
            "current_song": "",
            "completed": 0,
            "total": 0,
            "failed": 0,
            "updated_at": 0,
        }

    def flush_runtime_status(self, *, timeout: float = 5.0) -> bool:
        return bool(self._runtime_status_flushed_event.wait(timeout=max(0.0, float(timeout))))

    @staticmethod
    def _task_song_name(task: tuple) -> str:
        if not isinstance(task, tuple) or len(task) < 2:
            return ""
        return str(task[1] or "").strip()


__all__ = ["RoBeatsMetaOptimizerApi"]
