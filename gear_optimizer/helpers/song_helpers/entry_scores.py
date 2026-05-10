from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


def entry_fg_score(entry: dict) -> int:
    try:
        return int(entry.get("fg_score", 0) or 0)
    except Exception as e:
        logger.debug(f"entry_scores:entry_fg_score: {e}")
        return 0


def entry_base_score(entry: dict) -> int:
    try:
        return int(entry.get("base_score") or entry.get("score", 0) or 0)
    except Exception as e:
        logger.debug(f"entry_scores:entry_base_score: {e}")
        return 0
