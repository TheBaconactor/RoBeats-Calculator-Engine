"""Board orders and the merge of new results into a song's boards.

Meta board: loadouts with a meta result, by score, then FG score (a loadout without one last), then the
newest write, then the earliest stored result. Force Greats board: loadouts with an FG result that beats their
score, by FG score, then score, then the newest write, then the earliest stored result. Each board lists
LOADOUTS_PER_SONG_LIMIT loadouts; a loadout keeps both of its results while it is on at least one board.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from .records import FgResult, Loadout, MetaResult

META_ORDER = "score DESC, fg_score DESC, meta_updated DESC, meta_seq"
FG_ORDER = "fg_score DESC, score DESC, fg_updated DESC, fg_seq"


@dataclass(frozen=True, slots=True)
class Boards:
    meta: list[Loadout]
    fg: list[Loadout]


@dataclass(frozen=True, slots=True)
class Row:
    """A stored loadout with its encoded replay witnesses (carried byte for byte through merges)."""

    loadout: Loadout
    meta_trace: bytes | None
    fg_trace: bytes | None


def served_rows(boards: Boards, limit: int = LOADOUTS_PER_SONG_LIMIT) -> tuple[list[Loadout], list[Loadout]]:
    """The rows best_loadouts serves, in the version 18 reader's orders (its query plans'): the meta board's best
    `limit` by score, then FG score, then entry; the FG board's best `limit` by FG score, then loadout hash."""
    meta = sorted(boards.meta, key=lambda x: (-x.score, -(x.fg_score or 0), x.meta.seq))[:limit]
    fg = sorted(boards.fg, key=lambda x: (-x.fg_score, x.loadout_hash))[:limit]
    return meta, fg


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


def merge(rows: Iterable[Row], results: Sequence[Row], *, now: int, next_seq: tuple[int, int]) -> list[Row]:
    """The song's rows after storing `results` (one song and tier): a solve's (or another database's) loadouts
    with their meta and FG results (either may be None; board membership is ignored).

    Meta side: a new loadout takes the result's meta result; a higher score replaces a stored one. FG side: an
    FG result is stored when new, and replaces a stored FG result with an equal or lower FG score. Every touched side is stamped
    `now`; a newly stored result gets the next entry number of the database (`next_seq`: the next (meta, FG)
    numbers, so entries number in insertion order across songs). Then each board takes the
    LOADOUTS_PER_SONG_LIMIT best scores (the earliest entries among equal scores; the FG board only FG results
    that beat their loadout's score), and a loadout on neither board is dropped with its results.
    """
    work = {row.loadout.loadout_hash: _lift(row) for row in rows}
    seqs = _Seqs(meta=next_seq[0], fg=next_seq[1])
    for result in results:
        _merge_meta(work, result, now, seqs)
    for result in results:
        _merge_fg(work, result, now, seqs)
    return _normalize(work.values())


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


def _merge_meta(work: dict[str, _Work], result: Row, now: int, seqs: _Seqs) -> None:
    new = result.loadout
    current = work.get(new.loadout_hash)
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
        m = new.meta
        current.meta = MetaResult(m.element, m.gems, m.stats, now, seq)
        current.meta_trace = result.meta_trace
    else:
        m = current.meta
        current.meta = MetaResult(m.element, m.gems, m.stats, now, m.seq)
    current.fg_seen = max(current.fg_seen, new.fg_score or 0)


def _merge_fg(work: dict[str, _Work], result: Row, now: int, seqs: _Seqs) -> None:
    new = result.loadout
    if new.fg is None:
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
        f = new.fg
        current.fg = FgResult(f.element, f.gems, f.stats, f.surface, now, seq)
        current.fg_trace = result.fg_trace
        current.fg_score = new.fg_score if current.fg_score is None else max(current.fg_score, new.fg_score)
    else:
        f = current.fg
        current.fg = FgResult(f.element, f.gems, f.stats, f.surface, now, f.seq)


def _normalize(works: Iterable[_Work]) -> list[Row]:
    """Rank both boards to the limit and construct surviving rows once; a loadout on neither board is dropped."""
    active = [w for w in works if w.meta is not None or w.fg is not None]
    meta = sorted((w for w in active if w.meta is not None), key=lambda w: (-w.score, w.meta.seq))
    fg = sorted(
        (w for w in active if w.fg is not None and w.fg_score > (w.score if w.meta is not None else w.paired)),
        key=lambda w: (-w.fg_score, w.fg.seq),
    )
    on_meta = {w.source.loadout_hash for w in meta[:LOADOUTS_PER_SONG_LIMIT]}
    on_fg = {w.source.loadout_hash for w in fg[:LOADOUTS_PER_SONG_LIMIT]}
    out: list[Row] = []
    for w in active:
        s = w.source
        key = s.loadout_hash
        in_meta = key in on_meta
        in_fg = key in on_fg
        if in_meta or in_fg:
            score = w.score if w.meta is not None else w.paired
            fg_score = w.fg_score if w.fg is not None else (w.fg_seen or None)
            loadout = Loadout(
                mode=s.mode,
                song=s.song,
                tier=s.tier,
                loadout_hash=key,
                gear=s.gear,
                minis=s.minis,
                primary=s.primary,
                secondary=s.secondary,
                mini_ascension=s.mini_ascension,
                score=score,
                fg_score=fg_score,
                meta=w.meta,
                fg=w.fg,
                on_meta=in_meta,
                on_fg=in_fg,
            )
            out.append(Row(loadout, w.meta_trace if w.meta is not None else None, w.fg_trace))
    return out
