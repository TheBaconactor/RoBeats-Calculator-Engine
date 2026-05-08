from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar
import logging

import numpy as np

from ..song_helpers.ga_entry_utils import canonicalize_genome_ids


logger = logging.getLogger(__name__)
PayloadT = TypeVar("PayloadT")


@dataclass(frozen=True)
class ExactUniqueEvalStats:
    seen: int
    unique: int
    duplicate_hits: int
    replacements: int
    skipped_non_exact: int
    invalid_keys: int


@dataclass
class _ExactUniqueEvalEntry(Generic[PayloadT]):
    score: int
    payload: PayloadT


class GlobalUniqueEvalTable(Generic[PayloadT]):
    """
    Per-song exact-evaluation memo table.

    Important contract:
    - Keys are canonicalized gear IDs + sorted mini IDs.
    - Only exact evaluations may be inserted. Approx / warm-start results must not be reused.
    - First-seen order is preserved, but higher exact scores replace the stored payload for that slot.
    """

    def __init__(self) -> None:
        self._order: list[tuple[object, ...]] = []
        self._entries: dict[tuple[object, ...], _ExactUniqueEvalEntry[PayloadT]] = {}
        self._seen = 0
        self._duplicate_hits = 0
        self._replacements = 0
        self._skipped_non_exact = 0
        self._invalid_keys = 0
        self._invalid_seq = 0

    def _normalize_key(self, genome_ids: Any) -> tuple[object, ...]:
        canon = canonicalize_genome_ids(genome_ids)
        if canon is not None:
            return tuple(int(x) for x in canon)
        self._invalid_keys += 1
        key = ("__invalid__", self._invalid_seq)
        self._invalid_seq += 1
        return key

    def upsert(self, *, genome_ids: Any, score: int, payload: PayloadT, exact: bool = True) -> bool:
        self._seen += 1
        if not exact:
            self._skipped_non_exact += 1
            return False

        try:
            score_i = int(score)
        except Exception as e:
            logger.debug(f"unique_eval:upsert: {e}")
            score_i = 0

        key = self._normalize_key(genome_ids)
        prev = self._entries.get(key)
        if prev is None:
            self._order.append(key)
            self._entries[key] = _ExactUniqueEvalEntry(score=score_i, payload=payload)
            return True

        self._duplicate_hits += 1
        if score_i > int(prev.score):
            self._entries[key] = _ExactUniqueEvalEntry(score=score_i, payload=payload)
            self._replacements += 1
            return True
        return False

    def upsert_candidate(self, candidate: Any, *, exact: bool = True) -> bool:
        if not isinstance(candidate, dict):
            return False
        genome_ids = candidate.get("GenomeIDs")
        if genome_ids is None:
            data = candidate.get("Data")
            if isinstance(data, dict):
                genome_ids = data.get("GenomeIDs")
        score = candidate.get("BaseScore")
        if score is None:
            score = candidate.get("Score", 0)
        return self.upsert(genome_ids=genome_ids, score=int(score or 0), payload=candidate, exact=exact)

    def ordered_payloads(self) -> list[PayloadT]:
        return [self._entries[key].payload for key in self._order]

    @property
    def stats(self) -> ExactUniqueEvalStats:
        return ExactUniqueEvalStats(
            seen=int(self._seen),
            unique=int(len(self._order)),
            duplicate_hits=int(self._duplicate_hits),
            replacements=int(self._replacements),
            skipped_non_exact=int(self._skipped_non_exact),
            invalid_keys=int(self._invalid_keys),
        )


def select_exact_unique_row_indices(
    *,
    genome_ids_mat: Any,
    scores: Any,
    exact: bool = True,
) -> tuple[np.ndarray, ExactUniqueEvalStats]:
    table: GlobalUniqueEvalTable[int] = GlobalUniqueEvalTable()
    ids_mat = np.asarray(genome_ids_mat, dtype=np.int32)
    scores_arr = np.asarray(scores)
    for idx in range(int(ids_mat.shape[0])):
        score_val = int(scores_arr[idx]) if idx < int(scores_arr.shape[0]) else 0
        table.upsert(genome_ids=ids_mat[idx], score=score_val, payload=int(idx), exact=exact)
    return np.asarray(table.ordered_payloads(), dtype=np.int32), table.stats
