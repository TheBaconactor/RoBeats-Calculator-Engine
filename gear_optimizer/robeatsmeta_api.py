from __future__ import annotations

from typing import Any, Sequence

from .core.parsing import env_flag


class RoBeatsMetaOptimizerApi:
    """
    Minimal no-op bridge for local optimizer runs.

    The main optimizer path does not require backend queue orchestration or
    runtime-status push plumbing. Keep this surface tiny and deterministic.
    """

    @classmethod
    def service_mode_enabled(cls, *, song_meta_index_path: str | None = None) -> bool:
        _ = song_meta_index_path
        return env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE")

    @classmethod
    def benchmark_mode_enabled(cls) -> bool:
        return env_flag("ROBEATSMETA_OPTIMIZER_BENCHMARK_MODE")

    @classmethod
    def priority_queue_enabled(cls) -> bool:
        return False

    def backend_mode_enabled(self) -> bool:
        return False

    def service_defaults_enabled(self) -> bool:
        return False

    def apply_service_defaults(self, cfg: Any) -> bool:
        _ = cfg
        return False

    def pending_song_ids(self) -> list[str]:
        return []

    def prioritize_song_queue(
        self,
        song_queue: Sequence[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        return list(song_queue or [])

    def recently_computed_bundle_keys(self) -> set[str]:
        return set()

    def mark_song_computed(self, *, song_id: str, now: int | None = None) -> bool:
        _ = song_id, now
        return False

    def mark_song_started(self, *, song_id: str) -> None:
        _ = song_id

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
        _ = available, status, current_song, completed, total, failed, now
        return {}

    def clear_runtime_status(
        self,
        *,
        status: str = "idle",
        now: int | None = None,
        available: bool = True,
    ) -> dict[str, Any]:
        _ = status, now, available
        return {}

    def flush_runtime_status(self, *, timeout: float = 5.0) -> bool:
        _ = timeout
        return True

    def stop_runtime_status_loop(self, *, timeout: float = 1.0) -> None:
        _ = timeout

    def _bundle_key_for_song_id(self, song_id: str) -> str:
        return str(song_id or "")


__all__ = ["RoBeatsMetaOptimizerApi"]
