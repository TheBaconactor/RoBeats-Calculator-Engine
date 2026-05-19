from __future__ import annotations


class RoBeatsMetaOptimizerApi:
    @classmethod
    def service_mode_enabled(cls, *, song_meta_index_path: str | None = None) -> bool:
        _ = song_meta_index_path
        return False


__all__ = ["RoBeatsMetaOptimizerApi"]
