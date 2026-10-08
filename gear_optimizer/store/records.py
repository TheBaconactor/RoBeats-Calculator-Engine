"""Leaderboard records: one Loadout per loadout of a song, timing mode and TeamBuff tier.

A loadout keeps its results for as long as it is stored: its meta result (the best gem allocation without Force
Greats, scored `score`) and its Force Greats result (scored `fg_score`). Two boards list loadouts by those
results: the meta board by score, the Force Greats board by FG score among FG results that beat the loadout's
score; a loadout is stored while it is on at least one board. The replay witnesses (frontier traces) are stored
beside the results and loaded only on request (see store.db.load_traces).
"""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from typing import Any

from ..core.team_buff import CANONICAL_TEAM_BUFF_TIERS
from ..core.timing_modes import TIMING_MODES
from ..gamedata import ELEMENTS, STATS
from ..stats import GEM_KINDS

# FgResponseSurface has 11 fields (solver/taichi_gem/force_greats/response_types.py; importing it loads Taichi).
SURFACE_SIZE = 11


@dataclass(frozen=True, slots=True)
class MetaResult:
    """The loadout's best gem allocation without Force Greats."""

    element: str  # the selected element (element gems raise it)
    gems: tuple[int, ...]  # counts per stats.GEM_KINDS
    stats: tuple[int, ...]  # per gamedata.STATS, gems applied
    updated: int  # unix seconds of the last write
    seq: int  # the database's entry number: when the result was stored (earlier first among exact ties)

    def __post_init__(self) -> None:
        _check_result(self.element, self.gems, self.stats)


@dataclass(frozen=True, slots=True)
class FgResult:
    """The loadout's best Force Greats result; its score is the Loadout's fg_score."""

    element: str
    gems: tuple[int, ...]
    stats: tuple[int, ...]
    surface: tuple[int, ...]  # the response surface the FG score replays from
    updated: int
    seq: int

    def __post_init__(self) -> None:
        _check_result(self.element, self.gems, self.stats)
        if len(self.surface) != SURFACE_SIZE:
            raise ValueError(f"an FG result needs a {SURFACE_SIZE}-value response surface, got {self.surface!r}")


@dataclass(frozen=True, slots=True)
class Loadout:
    mode: str  # the timing mode the song was solved in (core.timing_modes)
    song: str
    tier: str
    loadout_hash: str
    gear: tuple[str, ...]  # gear names in slot order
    minis: tuple[tuple[str, ...], ...]  # per equipped mini, the names equivalent for this song (display order)
    primary: str  # the song colors the result was solved for
    secondary: str
    mini_ascension: str | None  # Mini Ascension version the minis were resolved with; None: an older row
    score: int  # the base (meta) score
    fg_score: int | None  # the best known Force Greats score (its FG result's, when it has one); None: never evaluated
    meta: MetaResult | None
    fg: FgResult | None
    on_meta: bool = False  # on the meta board (set by the store when it ranks the boards)
    on_fg: bool = False  # on the Force Greats board

    def __post_init__(self) -> None:
        if self.mode not in TIMING_MODES:
            raise ValueError(f"timing mode must be one of {TIMING_MODES}, got {self.mode!r}")
        if self.tier not in CANONICAL_TEAM_BUFF_TIERS:
            raise ValueError(f"TeamBuff tier must be one of {sorted(CANONICAL_TEAM_BUFF_TIERS)}, got {self.tier!r}")
        if self.primary not in ELEMENTS or self.secondary not in ELEMENTS:
            raise ValueError(f"song colors must be elements, got {self.primary!r}/{self.secondary!r}")
        if self.meta is None and self.fg is None:
            raise ValueError(f"loadout {self.loadout_hash} has no result")
        if self.fg is not None and self.fg_score is None:
            raise ValueError(f"loadout {self.loadout_hash} has an FG result without an FG score")
        if self.on_meta and self.meta is None:
            raise ValueError(f"loadout {self.loadout_hash} is on the meta board without a meta result")
        if self.on_fg and (self.fg is None or self.fg_score <= self.score):
            raise ValueError(f"loadout {self.loadout_hash} is on the FG board without an FG result that beats its score")


@dataclass(frozen=True, slots=True)
class Traces:
    """Replay witnesses of one loadout: the timeline frontier payload and the Force Greats payload."""

    meta: dict[str, Any] | None
    fg: dict[str, Any] | None


def _check_result(element: str, gems: tuple[int, ...], stats: tuple[int, ...]) -> None:
    if element not in ELEMENTS:
        raise ValueError(f"selected element must be an element, got {element!r}")
    if len(gems) != len(GEM_KINDS) or len(stats) != len(STATS):
        raise ValueError(f"a result needs {len(GEM_KINDS)} gem counts and {len(STATS)} stats")


def encode_meta(result: MetaResult) -> str:
    return _dumps({"element": result.element, "gems": result.gems, "stats": result.stats})


def decode_meta(text: str, updated: int, seq: int) -> MetaResult:
    obj = json.loads(text)
    return MetaResult(obj["element"], tuple(obj["gems"]), tuple(obj["stats"]), int(updated), int(seq))


def encode_fg(result: FgResult) -> str:
    return _dumps({"element": result.element, "gems": result.gems, "stats": result.stats, "surface": result.surface})


def decode_fg(text: str, updated: int, seq: int) -> FgResult:
    obj = json.loads(text)
    return FgResult(
        obj["element"], tuple(obj["gems"]), tuple(obj["stats"]), tuple(obj["surface"]), int(updated), int(seq)
    )


def encode_trace(trace: dict[str, Any] | None) -> bytes | None:
    return None if trace is None else zlib.compress(_dumps(trace).encode(), 6)


def decode_trace(blob: bytes | None) -> dict[str, Any] | None:
    return None if blob is None else json.loads(zlib.decompress(blob))


def encode_names(gear: tuple[str, ...]) -> str:
    return _dumps(gear)


def encode_groups(minis: tuple[tuple[str, ...], ...]) -> str:
    return _dumps(minis)


def decode_names(text: str) -> tuple[str, ...]:
    return tuple(json.loads(text))


def decode_groups(text: str) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(group) for group in json.loads(text))


def _dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
