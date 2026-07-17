"""Forward oracle: loadout -> the observables a leaderboard row exposes.

Scoring reuses the optimizer's canonical exact implementation
(``score_stats_exact`` / ``score_stats_exact_batch``); this module only owns
song-context setup, statsdict composition (via ``domain``), and the gear
power formula (``game_model``). No scoring semantics are duplicated.

All-Perfect semantics: v1 targets accuracy == 1.0 rows (the optimizer's
``best_score`` meaning). Naked score is the same chart scored with the
all-zero statsdict -- gear-independent by construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import (
    score_stat_arrays_exact_batch,
    score_stats_exact,
    score_stats_exact_batch,
)
from gear_optimizer.solver.scoring.fg_policy import extract_song_meta
from gear_optimizer.solver.taichi_gem.api.timeline import (
    build_or_load_timeline_frontier_payload,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope

from .domain import Loadout, Tables, compose_stats
from .game_model import gear_power

_ORACLE_CFG: dict = {"IterationEngine": {}}


class OracleError(RuntimeError):
    pass


@dataclass(frozen=True)
class Observables:
    """What a leaderboard row exposes for one play (accuracy == 1 tier)."""

    score: int
    naked_score: int
    gear_power: int
    accuracy: float = 1.0

    @property
    def gear_mult(self) -> float:
        return 1.0 if self.naked_score == 0 else self.score / self.naked_score


class SongOracle:
    """Loaded song context + forward evaluation."""

    def __init__(self, song_file: Path):
        song_file = Path(song_file)
        if not song_file.is_file():
            raise OracleError(f"chart file not found: {song_file}")
        base = get_base_calc_song(str(song_file), _ORACLE_CFG)
        if not base:
            raise OracleError(f"failed to load chart: {song_file}")
        calc_song = clone_calc_song(base)
        apply_timing_envelope(calc_song, mode="perfect_window")
        ref_arrays = _get_team_buff_ref_arrays_cached()
        if not isinstance(ref_arrays, dict) or not ref_arrays:
            raise OracleError("team buff ref arrays unavailable")
        build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        self.song_file = song_file
        self.calc_song = calc_song
        self.ref_arrays = ref_arrays
        meta = extract_song_meta(calc_song)
        if not meta.primary_color:
            raise OracleError(f"chart has no Primary Color metadata: {song_file}")
        self.primary_color: str = meta.primary_color
        self.secondary_color: str = meta.secondary_color or ""
        md = calc_song.get("metadata", {}) or {}
        name = str(md.get("Song Name", "") or "").strip()
        artist = str(md.get("Artist", "") or "").strip()
        if not name:
            raise OracleError(f"chart has no Song Name metadata: {song_file}")
        # Mini Song Target entries use the "<Song Name> by <Artist>" identity.
        self.song_display: str = f"{name} by {artist}" if artist else name
        self._naked_score: int | None = None
        self._score_memo: dict[tuple, int] = {}
        self._SCORE_MEMO_MAX = 2_000_000  # ~300MB ceiling, then reset
        self._fever_body_grids: tuple[np.ndarray, np.ndarray] | None = None

    @property
    def song_colors(self) -> tuple[str, ...]:
        if self.secondary_color and self.secondary_color != self.primary_color:
            return (self.primary_color, self.secondary_color)
        return (self.primary_color,)

    @property
    def hit_count(self) -> int:
        """Judgeable events on this chart (hold heads and tails separately)."""
        song_data = self.calc_song.get("song_data", {}) or {}
        timestamps = song_data.get("chart_timestamps")
        if timestamps is None:
            timestamps = song_data.get("timestamps", ())
        n = len(timestamps)
        if n <= 0:
            raise OracleError(f"chart has no judgeable events: {self.song_file}")
        return int(n)

    def naked_score(self) -> int:
        if self._naked_score is None:
            self._naked_score = int(score_stats_exact({}, self.calc_song, self.ref_arrays))
        return self._naked_score

    def compose(self, loadout: Loadout, tables: Tables) -> dict[str, int]:
        return compose_stats(
            loadout,
            tables,
            song_name=self.song_display,
            primary_color=self.primary_color,
            secondary_color=self.secondary_color,
        )

    def score_stats(self, stats: Mapping[str, int]) -> int:
        # Routed through the batch path to share the exact-score memo
        # (corner evaluations repeat heavily across boxes and gate arms).
        return self.score_stats_batch([stats])[0]

    def score_stats_batch(self, stats_rows: Sequence[Mapping[str, int]]) -> list[int]:
        if not stats_rows:
            return []
        # Bounded exact-score memo: inversion pipelines (and the equivalence
        # gate's two arms) evaluate heavily overlapping vector sets; repeat
        # evaluations are dictionary hits. Keys are the sorted item tuple of
        # the stats dict.
        memo = self._score_memo
        keys = [tuple(sorted(r.items())) for r in stats_rows]
        missing = {k: r for r, k in zip(stats_rows, keys) if k not in memo}
        # If admitting this batch's misses would overflow the cap, reset FIRST
        # -- then every key in THIS batch is missing and must be recomputed.
        # (The earlier code cleared AFTER computing missing_idx, which wiped
        # the batch's cache HITS and KeyError'd on the final lookup.)
        if missing and len(memo) + len(missing) > self._SCORE_MEMO_MAX:
            memo.clear()
            missing = {k: r for r, k in zip(stats_rows, keys)}
        if missing:
            fresh = score_stats_exact_batch(
                [dict(r) for r in missing.values()],
                self.calc_song,
                self.ref_arrays,
            )
            for k, score in zip(missing.keys(), fresh):
                memo[k] = int(score)
        return [memo[k] for k in keys]

    def score_stats_matrix(self, mat: np.ndarray, keys: Sequence[str]) -> np.ndarray:
        """Exact scores (int64 array) for projected stat rows, array-native.

        ``mat`` columns follow ``keys`` (the engine's observable projection).
        Bypasses the per-row dict/memo layer entirely: the canonical batch
        scorer collapses rows on the scorer's derived key (curve plateaus,
        color-line equivalence) and replays each (FT, FF) frontier cell once,
        vectorized. Bit-identical to the dict path -- same scorer."""
        n = int(mat.shape[0])
        key_list = list(keys)

        def col(name: str) -> "np.ndarray":
            if name and name in key_list:
                return np.ascontiguousarray(mat[:, key_list.index(name)]).astype(np.int64)
            return np.zeros(n, dtype=np.int64)

        return score_stat_arrays_exact_batch(
            col(self.primary_color),
            col(self.secondary_color),
            col("Perfect Points"),
            col("Combo Multiplier"),
            col("Fever Multiplier"),
            col("Fever Time"),
            col("Fever Fill Rate"),
            self.calc_song,
            self.ref_arrays,
        )

    def fever_body_range_grids(self) -> tuple[np.ndarray, np.ndarray]:
        """(bf_min, bf_max) int64 grids over the (FT, FF) frontier cells: the
        range of body fever-hit counts across each cell's legal fever
        surfaces. Cells without a replayable surface carry the loosest sound
        bounds (0, body_total) -- a reachability rectangle may brush them.

        These are the engine's pool-aware S-corridor walls: every legal
        completion plays SOME lane of its own cell, so its body fever count
        lies inside [bf_min(cell), bf_max(cell)]."""
        if self._fever_body_grids is not None:
            return self._fever_body_grids
        from gear_optimizer.core.constants import TOTAL_ROWS
        from gear_optimizer.solver.scoring.exact_rescore import _frontier_replay_refs
        from gear_optimizer.solver.taichi_gem.api.timeline import (
            load_timeline_frontier_payload,
        )

        refs = _frontier_replay_refs(self.ref_arrays)
        payload = load_timeline_frontier_payload(self.calc_song, refs).payload
        counts = np.asarray(payload.grid_frontier_count[0], dtype=np.int64)
        offsets = np.asarray(payload.grid_frontier_offset[0], dtype=np.int64)
        used = int(payload.frontier_pool_used)
        bf_pool = np.asarray(
            payload.grid_frontier_body_fever_pool[0][:used], dtype=np.int64
        )
        body_total = max(0, self.hit_count - 100)
        n = TOTAL_ROWS + 1
        bf_min = np.zeros((n, n), dtype=np.int64)
        bf_max = np.full((n, n), body_total, dtype=np.int64)
        for ft in range(n):
            for ff in range(n):
                c = int(counts[ft, ff])
                if c <= 0:
                    continue
                o = int(offsets[ft, ff])
                seg = bf_pool[o : o + c]
                bf_min[ft, ff] = int(seg.min())
                bf_max[ft, ff] = int(seg.max())
        self._fever_body_grids = (bf_min, bf_max)
        return self._fever_body_grids

    def gear_power_of(self, stats: Mapping[str, int]) -> int:
        return gear_power(stats, include_base=True, song_colors=self.song_colors)

    def forward(self, loadout: Loadout, tables: Tables) -> Observables:
        stats = self.compose(loadout, tables)
        return Observables(
            score=self.score_stats(stats),
            naked_score=self.naked_score(),
            gear_power=self.gear_power_of(stats),
        )


def resolve_chart(data_root: Path, name_query: str, difficulty: str) -> Path:
    """Resolve a loose song name to exactly one chart file under
    ``Data/<Difficulty>/`` (fails loud on 0 or >1 matches)."""
    from gear_optimizer.data.song_io import scan_song_header

    diff = difficulty.strip().capitalize()
    if diff not in ("Easy", "Normal", "Hard"):
        raise OracleError(f"difficulty must be Easy|Normal|Hard, got {difficulty!r}")
    root = Path(data_root) / diff
    if not root.is_dir():
        raise OracleError(f"chart directory not found: {root}")
    query = name_query.strip().lower()
    matches: list[tuple[Path, str]] = []
    for fp in sorted(root.glob("*.txt")):
        header = scan_song_header(str(fp)) or {}
        song_name = str(header.get("Song Name", "") or "")
        if query in song_name.lower():
            matches.append((fp, song_name))
    if len(matches) == 1:
        return matches[0][0]
    if not matches:
        raise OracleError(f"no chart under {root} matches {name_query!r}")
    listing = "\n".join(f"  {name} ({fp.name})" for fp, name in matches[:20])
    raise OracleError(
        f"{len(matches)} charts match {name_query!r}; disambiguate:\n{listing}"
    )


def forward_many(
    oracle: SongOracle, tables: Tables, loadouts: Iterable[Loadout]
) -> list[Observables]:
    items = list(loadouts)
    stats_rows = [oracle.compose(lo, tables) for lo in items]
    scores = oracle.score_stats_batch(stats_rows)
    naked = oracle.naked_score()
    return [
        Observables(score=s, naked_score=naked, gear_power=oracle.gear_power_of(st))
        for s, st in zip(scores, stats_rows)
    ]
