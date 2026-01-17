from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class SongCandidate:
    song_name: str
    source_table: str
    rowid: int
    score: int
    fg_score: int
    gear_names: Tuple[str, ...]
    mini_groups: Tuple[Tuple[str, ...], ...]
    gem_totals: Tuple[int, ...]
    selected_element: str


@dataclass(frozen=True)
class CandidateSpec:
    candidate: SongCandidate
    gear_ids: Tuple[int, ...]
    mini_group_ids: Tuple[Tuple[int, ...], ...]
    element_id: int


@dataclass
class SongSpec:
    name: str
    candidates: List[CandidateSpec]
