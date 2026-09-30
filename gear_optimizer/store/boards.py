"""Board orders and the merge of new results into a song's boards.

Meta board: loadouts with a meta result, by score, then FG score (a loadout without one last), then the
newest write, then the earliest to enter the board. Force Greats board: loadouts with an FG result, by FG
score, then score, then the newest write, then the earliest entry. Each board keeps LOADOUTS_PER_SONG_LIMIT
loadouts.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from ..domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from .records import FgResult, Loadout, MetaResult

META_ORDER = "score DESC, fg_score DESC, meta_updated DESC, meta_seq"
FG_ORDER = "fg_score DESC, score DESC, fg_updated DESC, fg_seq"


def meta_key(loadout: Loadout) -> tuple:
    return (-loadout.score, -_fg_or_lowest(loadout), -loadout.meta.updated, loadout.meta.seq)


def fg_key(loadout: Loadout) -> tuple:
    return (-loadout.fg_score, -loadout.score, -loadout.fg.updated, loadout.fg.seq)


def _fg_or_lowest(loadout: Loadout) -> int:
    # SQLite sorts NULL below every value; stored FG scores are positive.
    return -1 if loadout.fg_score is None else loadout.fg_score


@dataclass(frozen=True, slots=True)
class Row:
    """A stored loadout with its encoded replay witnesses (carried byte for byte through merges)."""

    loadout: Loadout
    meta_trace: bytes | None
    fg_trace: bytes | None


@dataclass(frozen=True, slots=True)
class Candidate:
    """One loadout result of a solve (or of another database) to merge into a song's boards.

    `row.loadout.meta` is its meta result and `row.loadout.fg` its FG result (either may be None). A
    deferred candidate is an FG update posted after its GA result: its score is the base score its FG
    result was paired with, and it carries no meta result.
    """

    row: Row
    deferred: bool = False


@dataclass(slots=True)
class _Work:
    """A loadout while merging: its meta side (score, the best FG score seen with it) and FG side."""

    source: Loadout  # items, colors and Mini Ascension of the last result that was stored
    score: int | None  # meta score (None: no meta result)
    fg_seen: int  # the best FG score seen on the meta side (0: none)
    meta: MetaResult | None
    meta_trace: bytes | None
    paired: int | None  # the base score the FG result was solved against
    fg_score: int | None  # FG side score (None: no FG result)
    fg: FgResult | None
    fg_trace: bytes | None


def merge(rows: Iterable[Row], candidates: Sequence[Candidate], *, now: int) -> list[Row]:
    """The song's rows after storing `candidates` (one song and tier).

    Meta side: a new loadout takes the candidate's meta result; a higher score replaces a stored one; a
    deferred candidate (an FG update) only refreshes a stored one. FG side: a candidate whose FG score beats its paired base
    score is stored when new, and replaces a stored FG result with an equal or lower FG score. Every
    touched side is stamped `now`; a result entering a board gets the next entry number. Then an FG
    result is kept only while its FG score beats the loadout's score, each board keeps the
    LOADOUTS_PER_SONG_LIMIT best scores (the earliest entries among equal scores), a loadout without an
    FG result keeps an FG score no higher than its score, and a loadout on neither board is dropped.
    """
    rows = list(rows)
    work = {row.loadout.loadout_hash: _lift(row) for row in rows}
    seqs = _Seqs(
        meta=1 + max((r.loadout.meta.seq for r in rows if r.loadout.meta is not None), default=0),
        fg=1 + max((r.loadout.fg.seq for r in rows if r.loadout.fg is not None), default=0),
    )
    # The meta side stores GA results before deferred FG updates; the FG side keeps the given order.
    ordered = [c for c in candidates if not c.deferred] + [c for c in candidates if c.deferred]
    for candidate in ordered:
        _merge_meta(work, candidate, now, seqs)
    for candidate in candidates:
        _merge_fg(work, candidate, now, seqs)
    loadouts = [_project(w) for w in work.values()]
    return _normalize([row for row in loadouts if row is not None])


@dataclass(slots=True)
class _Seqs:
    meta: int
    fg: int


def _lift(row: Row) -> _Work:
    loadout = row.loadout
    has_meta = loadout.meta is not None
    has_fg = loadout.fg is not None
    return _Work(
        source=loadout,
        score=loadout.score if has_meta else None,
        fg_seen=(loadout.fg_score or 0) if has_meta else 0,
        meta=loadout.meta,
        meta_trace=row.meta_trace,
        paired=loadout.score if has_fg else None,
        fg_score=loadout.fg_score if has_fg else None,
        fg=loadout.fg,
        fg_trace=row.fg_trace,
    )


def _merge_meta(work: dict[str, _Work], candidate: Candidate, now: int, seqs: _Seqs) -> None:
    new = candidate.row.loadout
    current = work.get(new.loadout_hash)
    if candidate.deferred:
        # An FG update posted after its GA result touches a stored meta result and never adds one: its
        # gems are the FG allocation (version 18 stored them as a meta result with a lower base score).
        if current is not None and current.meta is not None:
            current.fg_seen = max(current.fg_seen, new.fg_score or 0)
            current.meta = replace(current.meta, updated=now)
        return
    if new.meta is None:
        return
    if current is None:
        current = work[new.loadout_hash] = _Work(new, None, 0, None, None, None, None, None, None)
    if current.meta is None:
        seq, seqs.meta = seqs.meta, seqs.meta + 1
    elif new.score > current.score:
        seq = current.meta.seq
    else:
        seq = None
    if seq is not None:
        current.source = new
        current.score = new.score
        current.meta = replace(new.meta, seq=seq)
        current.meta_trace = candidate.row.meta_trace
    current.fg_seen = max(current.fg_seen, new.fg_score or 0)
    current.meta = replace(current.meta, updated=now)


def _merge_fg(work: dict[str, _Work], candidate: Candidate, now: int, seqs: _Seqs) -> None:
    new = candidate.row.loadout
    if new.fg is None or new.fg_score <= new.score:
        return
    current = work.get(new.loadout_hash)
    if current is None:
        current = work[new.loadout_hash] = _Work(new, None, 0, None, None, None, None, None, None)
    if current.fg is None:
        seq, seqs.fg = seqs.fg, seqs.fg + 1
    elif new.fg_score >= current.fg_score:
        seq = current.fg.seq
    else:
        seq = None
    if seq is not None:
        if current.meta is None:
            current.source = new
        current.paired = new.score
        current.fg = replace(new.fg, seq=seq)
        current.fg_trace = candidate.row.fg_trace
        current.fg_score = new.fg_score if current.fg_score is None else max(current.fg_score, new.fg_score)
    current.fg = replace(current.fg, updated=now)


def _project(work: _Work) -> Row | None:
    """One loadout row: the meta side's score is the loadout's score (else the FG side's paired base)."""
    score = work.score if work.meta is not None else work.paired
    fg = work.fg if work.fg is not None and work.fg_score > score else None
    if work.meta is None and fg is None:
        return None
    if fg is not None:
        fg_score = work.fg_score
    elif work.meta is not None and work.fg_seen:
        fg_score = work.fg_seen
    else:
        fg_score = None
    loadout = replace(work.source, score=score, fg_score=fg_score, meta=work.meta, fg=fg)
    return Row(loadout, work.meta_trace if work.meta is not None else None, work.fg_trace if fg is not None else None)


def _normalize(rows: list[Row]) -> list[Row]:
    """Prune both boards to the limit, then settle FG scores of loadouts that left the FG board."""
    on_meta = sorted((r.loadout for r in rows if r.loadout.meta is not None), key=lambda x: (-x.score, x.meta.seq))
    on_fg = sorted((r.loadout for r in rows if r.loadout.fg is not None), key=lambda x: (-x.fg_score, x.fg.seq))
    off_meta = {x.loadout_hash for x in on_meta[LOADOUTS_PER_SONG_LIMIT:]}
    off_fg = {x.loadout_hash for x in on_fg[LOADOUTS_PER_SONG_LIMIT:]}
    out: list[Row] = []
    for row in rows:
        loadout = row.loadout
        keep_meta = loadout.meta is not None and loadout.loadout_hash not in off_meta
        keep_fg = loadout.fg is not None and loadout.loadout_hash not in off_fg
        if not keep_meta and not keep_fg:
            continue
        fg_score = loadout.fg_score
        if not keep_fg and fg_score is not None and fg_score > loadout.score:
            fg_score = loadout.score
        out.append(
            Row(
                replace(
                    loadout,
                    meta=loadout.meta if keep_meta else None,
                    fg=loadout.fg if keep_fg else None,
                    fg_score=fg_score,
                ),
                row.meta_trace if keep_meta else None,
                row.fg_trace if keep_fg else None,
            )
        )
    return out


def boards(rows: Iterable[Row]) -> tuple[list[Loadout], list[Loadout]]:
    """(meta board, FG board) of a song's rows, in board order."""
    loadouts = [row.loadout for row in rows]
    meta = sorted((x for x in loadouts if x.meta is not None), key=meta_key)
    fg = sorted((x for x in loadouts if x.fg is not None), key=fg_key)
    return meta, fg


def by_hash(rows: Iterable[Row]) -> Mapping[str, Row]:
    return {row.loadout.loadout_hash: row for row in rows}
