"""
Shared helpers for the in-flight orchestrators.

These functions are intentionally kept in one place to avoid copy/paste drift
between in-flight implementations.
"""

from __future__ import annotations

from typing import Any
import logging

from gear_optimizer.core.parsing import truthy
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_item_names, compact_prev_record

logger = logging.getLogger(__name__)
__all__ = ["_compact_items", "_compact_prev_record", "_truthy"]


def _truthy(v: Any) -> bool:
    return truthy(v)


def _compact_items(items: list) -> list[str]:
    return compact_item_names(items, drop_empty=True)


def _compact_prev_record(record: dict | None) -> dict | None:
    return compact_prev_record(record, drop_empty_item_names=True)
