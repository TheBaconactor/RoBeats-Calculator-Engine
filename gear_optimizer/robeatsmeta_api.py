from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .core.constants import BIN_DIR, PATHS

_TRUTHY = {"1", "true", "yes", "on"}
_DEFAULT_VISIT_TTL_SECONDS = 60 * 60 * 24
_DEFAULT_SONG_REPEATS = 25


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

    def __init__(
        self,
        *,
        state_path: str | os.PathLike[str] | None = None,
        song_meta_index_path: str | os.PathLike[str] | None = None,
        visit_ttl_seconds: int | None = None,
    ) -> None:
        self._state_path = Path(state_path) if state_path else self._resolve_state_path()
        self._lock_path = self._state_path.with_suffix(self._state_path.suffix + ".lock")
        self._song_meta_index_path = (
            Path(song_meta_index_path) if song_meta_index_path else self._resolve_song_meta_index_path()
        )
        ttl_override = visit_ttl_seconds
        if ttl_override is None:
            ttl_override = _safe_int(os.environ.get("ROBEATSMETA_OPTIMIZER_VISIT_TTL_SECONDS"), _DEFAULT_VISIT_TTL_SECONDS)
        self._visit_ttl_seconds = max(60, int(ttl_override))
        self._song_meta_mtime_ns: int | None = None
        self._bundle_by_song_id: dict[str, SongBundleRef] = {}
        self._last_task_priority_signature: tuple[tuple[str, int, int], ...] | None = None

    @staticmethod
    def service_mode_enabled() -> bool:
        return _env_truthy("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", default=False)

    @classmethod
    def priority_queue_enabled(cls) -> bool:
        if _env_truthy("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", default=False):
            return True
        return cls.service_mode_enabled()

    def apply_service_defaults(self, cfg: Any) -> bool:
        if not self.service_mode_enabled() or cfg is None:
            return False

        if not cfg.has_section("IterationEngine"):
            cfg.add_section("IterationEngine")
        if not cfg.has_section("CalculateSong"):
            cfg.add_section("CalculateSong")

        cfg.set("IterationEngine", "LoopForever", "true")
        cfg.set("IterationEngine", "SongRepeats", str(int(_DEFAULT_SONG_REPEATS)))
        cfg.set("IterationEngine", "UseEvolutionDB", "true")
        cfg.set("IterationEngine", "InFlightSongs", "1")

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

            last_computed_at = _safe_int(entry.get("last_computed_at"), 0)
            entry.update(
                {
                    "song_id": bundle.song_id,
                    "title": bundle.title,
                    "artist": bundle.artist,
                    "bundle_key": bundle.bundle_key,
                }
            )

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
            if next_entry != entry or changed:
                entries[bundle.bundle_key] = next_entry
                self._write_state_unlocked(state)
            self._last_task_priority_signature = None
            return True

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

    def _resolve_bundle(self, *, song_id: str, title: str | None = None, artist: str | None = None) -> SongBundleRef:
        cleaned_song_id = str(song_id or "").strip()
        cleaned_title = str(title or "").strip()
        cleaned_artist = str(artist or "").strip()

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
                    bundle_by_song_id[song_id] = SongBundleRef(
                        song_id=song_id,
                        title=title,
                        artist=artist,
                        bundle_key=_build_bundle_key(title=title, artist=artist, song_id=song_id),
                    )

        self._bundle_by_song_id = bundle_by_song_id
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
        return {"version": 1, "entries": entries}

    def _write_state_unlocked(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=True)
        tmp_path = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        os.replace(tmp_path, self._state_path)

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

    @staticmethod
    def _task_song_name(task: tuple) -> str:
        if not isinstance(task, tuple) or len(task) < 2:
            return ""
        return str(task[1] or "").strip()


__all__ = ["RoBeatsMetaOptimizerApi"]
