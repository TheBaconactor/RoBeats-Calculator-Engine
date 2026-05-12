from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PersistenceBatch:
    song: str
    db_key: str
    db_payload: dict[str, Any]
    persist_entries: list[dict[str, Any]]
    log: str = ""

    def as_result_payload(self) -> dict[str, Any]:
        return {
            "song": self.song,
            "db_key": self.db_key,
            "db_payload": self.db_payload,
            "persist_entries": self.persist_entries,
            "log": self.log,
        }
