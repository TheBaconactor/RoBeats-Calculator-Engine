from __future__ import annotations

from typing import Any

from gear_optimizer.domain.results import PersistenceBatch


def build_persistence_batch(
    *,
    song: str,
    db_key: str,
    db_payload: dict[str, Any],
    persist_entries: list[dict[str, Any]],
    log: str = "",
) -> PersistenceBatch:
    return PersistenceBatch(
        song=str(song),
        db_key=str(db_key),
        db_payload=db_payload,
        persist_entries=persist_entries,
        log=str(log or ""),
    )


def build_persistence_result_payload(
    *,
    song: str,
    db_key: str,
    db_payload: dict[str, Any],
    persist_entries: list[dict[str, Any]],
    log: str = "",
) -> dict[str, Any]:
    return build_persistence_batch(
        song=song,
        db_key=db_key,
        db_payload=db_payload,
        persist_entries=persist_entries,
        log=log,
    ).as_result_payload()
