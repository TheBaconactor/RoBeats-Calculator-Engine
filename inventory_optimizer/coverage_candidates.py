from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from gear_optimizer.data.database import get_db_connection

from .db import (
    fetch_candidates_for_peak,
    fetch_candidates_within_delta_allow_missing,
    fetch_peak_candidates_allow_missing,
    fetch_song_names_limited,
    fetch_song_peak,
)
from .keys import ELEMENT_TO_ID
from .models import SongCandidate

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class CandidateLoadResult:
    candidates_by_song: Dict[str, List[SongCandidate]]
    missing: List[str]
    song_peak_by_name: Optional[Dict[str, int]]
    songs_total_unfiltered: int


_ELEMENT_BY_LOWER: Dict[str, str] = {str(k).strip().lower(): str(k) for k in ELEMENT_TO_ID.keys()}


def normalize_element_filter(value: object) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() == "all":
        return None
    canonical = _ELEMENT_BY_LOWER.get(cleaned.lower())
    if canonical:
        return canonical
    if cleaned in ELEMENT_TO_ID:
        return cleaned
    return None


def _compute_peak_from_candidates(cands: List[SongCandidate]) -> int:
    peak = 0
    for cand in cands:
        peak = max(int(peak), int(getattr(cand, "score", 0) or 0), int(getattr(cand, "fg_score", 0) or 0))
    return int(peak)


def load_candidates_by_song(
    *,
    db_path: str,
    candidates_by_song_override: Optional[Dict[str, List[SongCandidate]]],
    song_limit: Optional[int],
    use_human_mode: bool,
    candidate_score_delta: int,
    candidate_limit_per_song: int,
    log_fn: Optional[LogFn] = None,
) -> CandidateLoadResult:
    if candidates_by_song_override is not None:
        if song_limit is not None:
            raise ValueError("song_limit is incompatible with candidates_by_song_override.")
        if bool(use_human_mode) or int(candidate_score_delta) > 0:
            raise ValueError("Human mode / candidate widening is incompatible with candidates_by_song_override.")
        candidates_by_song = {str(k): list(v) for k, v in candidates_by_song_override.items()}
        missing: List[str] = []
        song_peak_by_name = {name: _compute_peak_from_candidates(cands) for name, cands in candidates_by_song.items()}
        if log_fn is not None:
            log_fn(f"candidates_override_loaded (songs={len(candidates_by_song)})")
        return CandidateLoadResult(
            candidates_by_song=candidates_by_song,
            missing=missing,
            song_peak_by_name=song_peak_by_name,
            songs_total_unfiltered=int(len(candidates_by_song)),
        )

    conn = get_db_connection(db_path)
    try:
        if log_fn is not None:
            log_fn("db_connected")

        if song_limit is not None:
            song_names = fetch_song_names_limited(conn, int(song_limit))
            candidates_by_song: Dict[str, List[SongCandidate]] = {}
            missing = []
            song_peak_by_name: Dict[str, int] = {}
            for name in song_names:
                peak, base_peak, fg_peak = fetch_song_peak(conn, name)
                song_peak_by_name[str(name)] = int(peak)
                cands = fetch_candidates_for_peak(conn, name, peak, base_peak, fg_peak)
                if not cands:
                    missing.append(str(name))
                    continue
                candidates_by_song[str(name)] = cands
        else:
            if bool(use_human_mode) and int(candidate_score_delta) > 0:
                lim = int(candidate_limit_per_song)
                if lim <= 0:
                    lim = 1
                candidates_by_song, missing = fetch_candidates_within_delta_allow_missing(
                    conn,
                    score_delta=int(candidate_score_delta),
                    limit_per_song=int(lim),
                )
            else:
                candidates_by_song, missing = fetch_peak_candidates_allow_missing(conn)
            song_peak_by_name = {
                name: _compute_peak_from_candidates(cands) for name, cands in candidates_by_song.items()
            }
    finally:
        try:
            conn.close()
        finally:
            if log_fn is not None:
                log_fn("db_closed")

    return CandidateLoadResult(
        candidates_by_song=candidates_by_song,
        missing=missing,
        song_peak_by_name=song_peak_by_name,
        songs_total_unfiltered=int(len(candidates_by_song)),
    )


def apply_element_filter(
    *,
    candidates_by_song: Dict[str, List[SongCandidate]],
    song_peak_by_name: Optional[Dict[str, int]],
    element: Optional[str],
    secondary_element: Optional[str],
) -> Tuple[Dict[str, List[SongCandidate]], Optional[Dict[str, int]], int]:
    allowed = {e for e in (element, secondary_element) if e}
    if not allowed:
        return candidates_by_song, song_peak_by_name, 0

    filtered: Dict[str, List[SongCandidate]] = {}
    for song_name, candidates in candidates_by_song.items():
        kept = [cand for cand in candidates if cand.selected_element in allowed]
        if kept:
            filtered[song_name] = kept

    songs_filtered_out = int(len(candidates_by_song) - len(filtered))
    if song_peak_by_name is not None:
        song_peak_by_name = {k: v for k, v in song_peak_by_name.items() if k in filtered}
    return filtered, song_peak_by_name, songs_filtered_out


__all__ = [
    "CandidateLoadResult",
    "apply_element_filter",
    "load_candidates_by_song",
    "normalize_element_filter",
]
