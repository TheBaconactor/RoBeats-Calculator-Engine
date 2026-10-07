"""TeamBuff tier replays: a song's stored leaderboard re-solved at other TeamBuff tiers and team colors.

The stored entries supply only the loadout set (gear + minis). Each (tier, team color) re-solves the gems on both
surfaces, because a tier or a team color shifts the stat vector and with it the optimal gem split:
- meta: the gem budget re-allocated from the tier-shifted song fixed stats + the loadout's items by the GPU base
  search, scored by the CPU-f64 exact rescore (the per-tier optimum, never the stored T5 gems);
- FG: re-allocated through the canonical FG response frontier, scored exactly. The one carry: at precise
  timing, the baseline tier and no team-color shift, nothing differs from the solve that produced the entry, so its
  stored force payload is that optimum and is served verbatim.
The song's timing mode (song.mode) is the timing the replay answers: non_precise puts every hit at its chart time.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from heapq import nsmallest

from ...chart import Chart
from ...core.gem_defs import build_gem_counts
from ...core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    normalize_team_buff_sequence,
    team_buff_effect,
)
from ...core.utils import get_selected_element, safe_int as _safe_int
from ...data.loadout_equivalence import representative_mini_names
from ...gamedata import Gear, Mini, SongMini, StatCurves, load_gears, load_minis, song_minis
from ...settings import paths
from ...solver.fg_response_scoring.note_graph import UnplayableTrace
from ...solver.timing_envelope import TimedSong
from ...stats import total
from .fg_payload import require_response_surface
from .song_config import baseline_fixed_stats

logger = logging.getLogger(__name__)
_SOURCE_KEYS = ("source_score", "source_fg_base_score", "source_fg_score")


def _norm_text(v: object) -> str:
    return str(v or "").strip()


def _loadout_hash(entry: dict) -> str:
    return _norm_text(entry.get("loadout_hash", ""))


_MINI_LITERAL_RE = re.compile(r"""['"]([^'"]+)['"]""")


def _mini_names_from_text(text: str) -> list[str]:
    s = text.strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        matches = [m.group(1).strip() for m in _MINI_LITERAL_RE.finditer(s)]
        matches = [m for m in matches if m]
        if matches:
            return matches
        inner = s[1:-1].strip()
        if inner:
            parts = [p.strip().strip("'\"") for p in inner.split(",")]
            cleaned = [p for p in parts if p]
            if cleaned:
                return cleaned
    return [s]


def _flat_item_names(items: object) -> list[str]:
    out: list[str] = []
    if not items:
        return out
    for it in items if isinstance(items, (list, tuple)) else [items]:
        if isinstance(it, (list, tuple)):
            out.extend(_flat_item_names(it))
        elif isinstance(it, (Gear, Mini, SongMini)):
            out.append(it.name)
        else:
            name = _norm_text(it)
            if name:
                out.append(name)
    return out


def _mini_groups_from_any(minis: object) -> list[list[str]]:
    """A stored loadout's minis as name groups: a slot is a mini, a name, a variant list, or a list's text."""
    groups: list[list[str]] = []
    for slot in (minis if isinstance(minis, (list, tuple)) else [minis]) if minis else ():
        names = {
            name
            for raw in (slot if isinstance(slot, (list, tuple)) else [slot])
            for name in ([raw.name] if isinstance(raw, (Mini, SongMini)) else _mini_names_from_text(_norm_text(raw)))
            if name
        }
        if names:
            groups.append(sorted(names))
    return groups


def _representative_mini_names_from_any(minis: object) -> list[str]:
    groups = _mini_groups_from_any(minis)
    return representative_mini_names(groups) if groups else []


def _resolve_team_colors_for_tiering(
    chart: Chart,
    *,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
) -> tuple[str, str]:
    """(the stored rows' team color: the song's primary unless overridden, the team color the tiers answer for)."""
    base = _norm_text(chart.primary if base_team_color_override is None else base_team_color_override)
    target = base if target_team_color_override is None else _norm_text(target_team_color_override)
    return base, target


def _entry_origin_priority(entry: dict) -> tuple[int, int, int]:
    force_obj = entry.get("force")
    has_force = 1 if force_obj is not None else 0
    return (
        has_force,
        _safe_int(entry.get("fg_score"), 0),
        _safe_int(entry.get("score"), 0),
    )


def _team_buff_delta_map(
    *,
    base_team_buff: str,
    target_team_buff: str,
    base_team_color: str,
    target_team_color: str,
) -> dict[str, int]:
    base = team_buff_effect(base_team_buff, base_team_color)
    target = team_buff_effect(target_team_buff, target_team_color)
    out: dict[str, int] = {}
    for k in set(base.keys()) | set(target.keys()):
        delta = target.get(k, 0) - base.get(k, 0)
        if delta:
            out[k] = delta
    return out


def _apply_stat_delta(stats: dict, delta: dict[str, int]) -> dict:
    if not isinstance(stats, dict) or not stats:
        return {}
    if not delta:
        return dict(stats)
    out = dict(stats)
    for k, d in delta.items():
        if not d:
            continue
        out[str(k)] = _safe_int(out.get(k, 0), 0) + int(d)
    return out


def _entry_loadout_items(entry: dict, chart: Chart) -> list[Gear | SongMini]:
    """The loadout's 6 gear + 3 minis, the minis as ``chart``'s song sees them (Mini Ascension).

    The serving paths pass entries whose ``gear``/``minis`` are already items (catalog items, or a job's
    custom-pool items, which only the job knows); stored entries keep item NAME STRINGS. Names resolve through
    Gears.csv/Minis.csv, so the per-tier gem re-solve has ONE entry contract regardless of caller. Fails loud when
    the loadout does not resolve to exactly 6 gear + 3 minis.
    """
    entry = entry or {}
    raw_gear = list(entry.get("gear") or [])
    raw_minis = list(entry.get("minis") or [])
    gear = [item for item in raw_gear[:6] if isinstance(item, Gear)]
    minis = [item for item in raw_minis[:3] if isinstance(item, (Mini, SongMini))]
    if len(gear) != 6 or len(minis) != 3:
        gears = load_gears(paths().gears_csv)
        catalog_minis = load_minis(paths().minis_csv)
        gear = [gears[name] for name in _flat_item_names(raw_gear) if name in gears]
        minis = [
            catalog_minis[name]
            for name in _representative_mini_names_from_any(raw_minis)
            if name in catalog_minis
        ]
    if len(gear) != 6 or len(minis) != 3:
        raise ValueError(
            f"tier re-solve needs 6 gear + 3 minis, got {len(gear)} gear + {len(minis)} minis "
            f"(loadout {entry.get('loadout_hash')!r})"
        )
    return gear + [
        song_minis([mini], chart.name, chart.primary, chart.secondary)[0] if isinstance(mini, Mini) else mini
        for mini in minis
    ]


def _pre_gem_loadout_stats(fixed_song_stats: dict, loadout_items: list[Gear | SongMini]) -> dict[str, int]:
    """Stats row the gem solver starts from: song/tier fixed stats + loadout item stats."""
    return total(fixed_song_stats, *(item.stats for item in loadout_items))


def resolve_tier_fg_force(
    *,
    fixed_song_stats: dict,
    loadout_items: list,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
) -> dict:
    """Lossless FG re-solve of ONE loadout at one (tier, color, timing) config: the batch of one (the lossless
    gate's per-loadout path, so gate == served)."""
    (force,) = resolve_tier_fg_force_batch(
        fixed_song_stats=fixed_song_stats,
        loadouts=[loadout_items],
        song=song,
        curves=curves,
        selected_color=selected_color,
    )
    return force


def resolve_tier_fg_force_batch(
    *,
    fixed_song_stats: dict,
    loadouts: list,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
) -> list:
    """Lossless FG re-solve of N loadouts (their items) at one (tier, color, timing) config in ONE response-frontier
    dispatch: the gem allocation at the full budget (GPU search, then the CPU-f64 exact rescore) from the shared
    tier-shifted song fixed stats. Returns the N materialized ``force`` payloads in order (re-solved GemCounts /
    Stats / Score + the frontier trace at the song's timing). Each loadout's search is independent, so its result
    does not depend on the batch."""
    from gear_optimizer.rules import GEM_BUDGET
    from ...solver.fg_response_scoring.fixed_timing import build_fixed_timing_fg_replays

    rows = list(loadouts or [])
    if not rows:
        return []
    pre_gem_rows = [_pre_gem_loadout_stats(fixed_song_stats, items) for items in rows]
    replays = build_fixed_timing_fg_replays(
        fg_stats_list=pre_gem_rows,
        base_stats_list=pre_gem_rows,
        song=song,
        curves=curves,
        selected_color=str(selected_color or ""),
        total_budget=int(GEM_BUDGET),
    )
    if len(replays) != len(rows):
        raise ValueError(f"batched tier FG re-solve returned {len(replays)} != {len(rows)} replays")
    return [r["force"] for r in replays]


def resolve_tier_base(
    *,
    fixed_song_stats: dict,
    loadout_items: list[dict],
    song: TimedSong,
    curves: StatCurves,
    primary_color: str,
    selected_color: str,
) -> tuple[dict, int]:
    """Lossless BASE (meta) re-solve of ONE loadout: the batch of one (the lossless gate's per-loadout path, so
    gate == served). Returns ``(resolved_payload, score)``."""
    (out,) = resolve_tier_base_batch(
        fixed_song_stats=fixed_song_stats,
        loadouts=[loadout_items],
        song=song,
        curves=curves,
        primary_color=primary_color,
        selected_color=selected_color,
    )
    return out


def resolve_tier_base_batch(
    *,
    fixed_song_stats: dict,
    loadouts: list,
    song: TimedSong,
    curves: StatCurves,
    primary_color: str,
    selected_color: str,
) -> list:
    """Lossless BASE re-solve of N loadouts (their items) in ONE GPU dispatch (n_genomes=N): the exhaustive gem
    search from the shared tier-shifted song fixed stats, scored exactly at the song's timing (non_precise: fixed chart
    timing; precise: the timing frontier). Returns N ``(payload, score)`` in order, the payload holding the
    served base fields (Stats, GemCounts, FT, FF). Each loadout's search is independent of the batch."""
    from ...solver.scoring.fever_solver import solve_best_fever_combination_batch

    rows = list(loadouts or [])
    if not rows:
        return []
    pre_gem_rows = [_pre_gem_loadout_stats(fixed_song_stats, items) for items in rows]
    solves = solve_best_fever_combination_batch(
        pre_gem_rows,
        song,
        curves,
        selected_color=str(selected_color or "") or str(primary_color or ""),
    )
    out = []
    for solve in solves:
        pp, cm, fm, ft, ff, element = solve.gems
        resolved = {"Stats": dict(solve.stats), "GemCounts": build_gem_counts(pp, cm, fm, element), "FT": ft, "FF": ff}
        out.append((resolved, solve.score))
    return out


def _fg_identity_details(force_out: object, chart: Chart) -> dict[str, str]:
    """Chart/loadout identity fields required by FG serialization (not meta scoring)."""
    chart_primary = _norm_text(chart.primary)
    chart_secondary = _norm_text(chart.secondary)
    selected = _norm_text(get_selected_element(force_out, "") if isinstance(force_out, dict) else "")
    primary = chart_primary or selected
    secondary = chart_secondary or primary or "General"
    return {
        "SelectedElement": selected or primary,
        "PrimaryColor": primary,
        "SecondaryColor": secondary,
    }


@dataclass(frozen=True, slots=True)
class _ReplayEntry:
    """A stored entry the tiers re-solve (it has stats), with its stored scores."""

    entry: dict
    loadout_hash: str
    gear: list[str]
    minis: list[str]
    source_score: int
    source_fg_base_score: int
    source_fg_score: int
    has_fg: bool  # it carries a valid FG payload (a response surface)


def _replay_entries(entries: list, song: TimedSong) -> list[_ReplayEntry]:
    """The stored entries with stats, parsed once (the website's rows: scores are coerced as stored)."""
    primary, secondary = _norm_text(song.chart.primary), _norm_text(song.chart.secondary)
    out: list[_ReplayEntry] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details") or {}
        if not isinstance(details, dict):
            details = {}
        stats = details.get("Stats") or {}
        if not isinstance(stats, dict) or not stats:
            continue
        gear = _flat_item_names(entry.get("gear") or [])
        minis = _representative_mini_names_from_any(entry.get("minis") or [])
        force = entry.get("force")
        # The store writes force None for meta-only rows; an FG row without its response surface is invalid state.
        has_fg = force is not None
        if has_fg:
            require_response_surface(force)
        if song.mode == "non-precise" and secondary:
            # The non_precise re-solve selects the song's primary for the whole batch, as the native optimizer does for
            # meta loadouts; a loadout stored with another selected element would silently diverge from native.
            stored = _norm_text(get_selected_element(force)) or _norm_text(get_selected_element(details))
            if stored and stored != primary:
                raise ValueError(
                    f"non_precise re-solve invariant violated: loadout {_norm_text(entry.get('loadout_hash'))!r} "
                    f"persists selected element {stored!r} != song primary {primary!r}; the "
                    f"forced-primary re-solve would diverge from native. The re-solve must honor the "
                    f"per-loadout selected element before this can serve."
                )
        score = _safe_int(entry.get("score"), 0)
        out.append(
            _ReplayEntry(
                entry=entry,
                loadout_hash=_norm_text(entry.get("loadout_hash", "")),
                gear=gear,
                minis=minis,
                source_score=score,
                source_fg_base_score=_safe_int(entry.get("fg_base_score"), score),
                source_fg_score=_safe_int(entry.get("fg_score"), 0),
                has_fg=has_fg,
            )
        )
    return out


def _carried_fg_score(row: _ReplayEntry) -> int:
    """The baseline-tier carry's FG score: the stored fg_score, which every producer sets to the force payload's
    positive exact score. A non-positive one beside a valid force is inconsistent; ranking it would silently drop the
    row (fg_score > 0), so it fails loud."""
    if row.source_fg_score <= 0:
        raise ValueError(
            "baseline-tier FG carry: loadout "
            f"{row.loadout_hash!r} carries a valid force payload "
            f"but a non-positive fg_score ({row.source_fg_score}); refusing to silently drop "
            "the row. The persisted fg_score IS the exact surface score and a valid "
            "FG force always scores > 0 -- re-canonicalize the source entry."
        )
    return row.source_fg_score


def _rank_tier(rows: list[_ReplayEntry], meta_scores: list[int], fg_scores: list[int] | None, n: int, *,
               replay_meta: bool, replay_fg: bool) -> dict[str, list[dict]]:
    """A tier's top-N by base score and by FG score (ties by loadout hash). An FG row's paired base is the same
    loadout's re-solved base score, so FG rows need the meta surface."""
    base_ranked: list[dict] = []
    fg_ranked: list[dict] = []
    for i, e in enumerate(rows):
        base_score = meta_scores[i] if replay_meta else 0
        fg_score = (fg_scores[i] or 0) if fg_scores is not None else 0
        if replay_meta:
            base_ranked.append(
                {
                    "loadout_hash": e.loadout_hash,
                    "gear": e.gear,
                    "minis": e.minis,
                    "score": base_score,
                    "source_score": e.source_score,
                }
            )
        if replay_fg and e.has_fg and fg_score > 0:
            if not replay_meta:
                raise ValueError(
                    "FG replay requires the 'meta' surface: the FG paired base is the "
                    "loadout's re-solved base score, computed only when meta is replayed."
                )
            fg_ranked.append(
                {
                    "loadout_hash": e.loadout_hash,
                    "gear": e.gear,
                    "minis": e.minis,
                    "fg_score": fg_score,
                    "fg_base_score": base_score,
                    "source_score": e.source_score,
                    "source_fg_base_score": e.source_fg_base_score,
                    "source_fg_score": e.source_fg_score,
                }
            )
    return {
        "base_top51": nsmallest(n, base_ranked, key=lambda r: (-r["score"], r["loadout_hash"])),
        "fg_top51": nsmallest(n, fg_ranked, key=lambda r: (-r["fg_score"], r["loadout_hash"])),
    }


def compute_team_buff_tier_leaderboards(
    *,
    entries: list[dict],
    song: TimedSong,
    curves: StatCurves,
    limit: int = 51,
    tiers: tuple[str, ...] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
    replay_surfaces: tuple[str, ...] = ("meta", "fg"),
) -> dict:
    """Re-solve each stored entry's loadout at each TeamBuff tier (and team color) and rank per tier.

    Returns {"meta": the colors and buffs, "tiers": {tier: {"base_top51", "fg_top51"}}, and per (tier, loadout hash)
    the re-solved witnesses build_team_buff_tier_db_batches serves: "resolved_base_by_tier_hash" (Stats, GemCounts,
    FT, FF) and "resolved_fg_force_by_tier_hash" (the force payload: the carried stored one at the baseline
    precise tier with no color shift, else the re-solved one with the timing mode's trace)}.
    """
    n = max(0, int(limit))
    if not entries or n <= 0:
        return {"tiers": {}, "meta": {"candidate_count": 0}}
    surfaces = {str(s).strip().lower() for s in (replay_surfaces or ("meta", "fg"))}
    replay_meta, replay_fg = "meta" in surfaces, "fg" in surfaces
    primary_color = _norm_text(song.chart.primary)
    base_team_color, target_team_color = _resolve_team_colors_for_tiering(
        song.chart,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    tier_list = [str(t) for t in normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)]
    rows = _replay_entries(entries, song)
    # Both surfaces, both timing modes and the lossless gate start from the song's baseline fixed stats.
    song_fixed_stats = baseline_fixed_stats(song.chart)

    def tier_fixed_stats(tier: str) -> dict:
        return _apply_stat_delta(
            song_fixed_stats,
            _team_buff_delta_map(
                base_team_buff=OPTIMIZER_BASELINE_TEAM_BUFF,
                target_team_buff=tier,
                base_team_color=base_team_color,
                target_team_color=target_team_color,
            ),
        )

    meta_scores = {t: [0] * len(rows) for t in tier_list}
    base_witnesses: dict[str, dict[str, dict]] = {}
    if replay_meta and rows:
        meta_scores = {}
        loadouts = [_entry_loadout_items(e.entry, song.chart) for e in rows]
        for tier in tier_list:
            batch = resolve_tier_base_batch(
                fixed_song_stats=tier_fixed_stats(tier),
                loadouts=loadouts,
                song=song,
                curves=curves,
                primary_color=primary_color,
                selected_color=primary_color,
            )
            witnesses = base_witnesses.setdefault(tier, {})
            for i, e in enumerate(rows):
                if e.loadout_hash:
                    witnesses[e.loadout_hash] = batch[i][0]
            meta_scores[tier] = [int(score) for _resolved, score in batch]

    fg_scores = {t: [0] * len(rows) for t in tier_list}
    fg_witnesses: dict[str, dict[str, dict]] = {}
    have_fg = replay_fg and any(e.has_fg for e in rows)
    if have_fg:
        fg_rows = [i for i, e in enumerate(rows) if e.has_fg]
        loadouts = [_entry_loadout_items(rows[i].entry, song.chart) for i in fg_rows]
        for tier in tier_list:
            witnesses = fg_witnesses.setdefault(tier, {})
            if song.mode == "precise" and tier == OPTIMIZER_BASELINE_TEAM_BUFF and base_team_color == target_team_color:
                forces = [rows[i].entry["force"] for i in fg_rows]
                scores = [_carried_fg_score(rows[i]) for i in fg_rows]
            else:
                forces = resolve_tier_fg_force_batch(
                    fixed_song_stats=tier_fixed_stats(tier),
                    loadouts=loadouts,
                    song=song,
                    curves=curves,
                    selected_color=primary_color,
                )
                # A loadout without an FG result (its plan is unplayable at this timing) ranks nowhere on the FG board.
                scores = [int((force or {}).get("Score") or 0) for force in forces]
            for i, force, score in zip(fg_rows, forces, scores, strict=True):
                fg_scores[tier][i] = score
                if rows[i].loadout_hash:
                    witnesses[rows[i].loadout_hash] = force

    return {
        "meta": {
            "candidate_count": len(rows),
            "team_color": target_team_color,
            "base_team_color": base_team_color,
            "target_team_color": target_team_color,
            "base_team_buff": OPTIMIZER_BASELINE_TEAM_BUFF,
            "primary_color": primary_color,
            "secondary_color": _norm_text(song.chart.secondary),
        },
        "tiers": {
            tier: _rank_tier(rows, meta_scores.get(tier, []), fg_scores[tier] if have_fg else None, n,
                             replay_meta=replay_meta, replay_fg=replay_fg)
            for tier in tier_list
        },
        "resolved_fg_force_by_tier_hash": fg_witnesses,
        "resolved_base_by_tier_hash": base_witnesses,
    }


def _served_rows(surface: str, tier_payload: dict, originals: dict[str, dict]) -> list[tuple[dict, dict]]:
    """The rows a surface serves at one tier, each as (its scores, the stored entry it re-solves): "meta" / "fg" the
    tier's top-N by base / FG score; "both" their union for persistence canonicalization (the base rows' loadouts,
    then the FG-only ones)."""
    if surface != "both":
        out = []
        for r in tier_payload.get("base_top51" if surface == "meta" else "fg_top51") or []:
            orig = originals.get(_loadout_hash(r))
            if orig is not None:
                scores = {k: r.get(k) or 0 for k in ("score", "fg_score", "fg_base_score")}
                out.append(({**scores, **{k: r[k] or 0 for k in _SOURCE_KEYS if k in r}}, orig))
        return out
    merged: dict[str, dict] = {}
    for r in tier_payload.get("base_top51") or []:
        if h := _loadout_hash(r):
            row = merged.setdefault(h, {})
            row.update(score=r.get("score") or 0, fg_score=r.get("fg_score") or 0)
            row.update((k, r[k] or 0) for k in _SOURCE_KEYS if k in r)
    for r in tier_payload.get("fg_top51") or []:
        if h := _loadout_hash(r):
            row = merged.setdefault(h, {})
            row.update(fg_score=r.get("fg_score") or 0, fg_base_score=r.get("fg_base_score") or 0)
            row.setdefault("score", r.get("score") or 0)
            row.update((k, r[k] or 0) for k in _SOURCE_KEYS if k in r)
    out = []
    for h, row in merged.items():
        orig = originals.get(h)
        if orig is not None:
            row.setdefault("fg_base_score", 0)
            for k in _SOURCE_KEYS:
                row.setdefault(k, int(orig.get(k, 0) or 0))
            out.append((row, orig))
    return out


def _tier_details(orig: dict, witness: object, tier: str, song: TimedSong, curves: StatCurves) -> dict:
    """A served base row's details at a tier: the stored details with the tier's re-solved Stats, GemCounts, FT and FF
    (never the stored T5 allocation or its compact st/gc/gk copies) and a TimelineFrontier recomputed for those Stats.
    non_precise rows carry no TimelineFrontier: the consumer draws the chart-time timeline (every delta 0) from Stats."""
    from ...solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace

    details = orig.get("details")
    out = dict(details) if isinstance(details, dict) else {}
    out.pop("TimelineFrontier", None)  # the stored one is the T5 witness
    if not isinstance(witness, dict):
        raise ValueError(
            f"tier base re-solve missing witness for loadout {_norm_text(orig.get('loadout_hash'))!r} at tier {tier!r}."
        )
    w_stats = witness.get("Stats")
    if isinstance(w_stats, dict) and w_stats:
        out["Stats"] = dict(w_stats)
    w_gems = witness.get("GemCounts")
    if isinstance(w_gems, dict):
        out["GemCounts"] = dict(w_gems)
    # The re-solve's FT/FF replace the stored ones too, or the served gem counts could sum past the budget.
    out["FT"] = int(witness.get("FT") or 0)
    out["FF"] = int(witness.get("FF") or 0)
    for alias in ("st", "gc", "gk"):
        out.pop(alias, None)
    stats = out.get("Stats")
    if song.mode != "non-precise" and isinstance(stats, dict) and stats:
        frontier = score_stats_exact_with_timeline_trace(stats, song, curves).get("TimelineFrontier")
        if isinstance(frontier, dict) and frontier.get("frontier_trace"):
            out["TimelineFrontier"] = frontier
    return out


def build_team_buff_tier_db_batches(
    *,
    entries: list[dict],
    song: TimedSong,
    curves: StatCurves,
    limit: int = 51,
    tiers: tuple[str, ...] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
    replay_surface: str = "both",
) -> dict[str, list[dict]]:
    """DB-ready entry batches per tier: {"T5": [{loadout_hash, gear, minis, score, details, fg_score, fg_base_score,
    force, source_*}, ...], ...}, the fields per `replay_surface`:
    - "meta": the top-N by re-solved base score (details: the re-solved base, see _tier_details);
    - "fg": the top-N by re-solved FG score (force: the tier's witness; details: identity fields only);
    - "both" (any other value): their union, for persistence canonicalization.
    non_precise (song.mode) answers at fixed chart timing: its rankings come from the chart-only response frontier, base
    rows carry no TimelineFrontier and FG rows the re-solved force with its chart-fixed trace; a derived view, never
    persisted to the canonical leaderboards.
    """
    surface = str(replay_surface or "both").strip().lower()
    if surface not in {"meta", "fg"}:
        surface = "both"
    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        song=song,
        curves=curves,
        limit=limit,
        tiers=normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS),
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
        replay_surfaces=("meta", "fg") if surface == "both" else (surface,),
    )
    base_witnesses = payload.get("resolved_base_by_tier_hash") or {}
    fg_witnesses = payload.get("resolved_fg_force_by_tier_hash") or {}
    # Each loadout hash re-solves the stored entry with the most FG evidence (valid force, then FG score, then score).
    originals: dict[str, dict] = {}
    for e in entries or []:
        if isinstance(e, dict) and (h := _loadout_hash(e)):
            if h not in originals or _entry_origin_priority(e) > _entry_origin_priority(originals[h]):
                originals[h] = e

    batches: dict[str, list[dict]] = {}
    for tier, tier_payload in (payload.get("tiers") or {}).items():
        tier = str(tier)
        out_entries: list[dict] = []
        for scores, orig in _served_rows(surface, tier_payload, originals):
            h = _norm_text(orig.get("loadout_hash"))
            row: dict = {
                "loadout_hash": str(orig.get("loadout_hash") or ""),
                "gear": _flat_item_names(orig.get("gear")),
                "minis": _representative_mini_names_from_any(orig.get("minis")),
            }
            if surface != "fg":
                row["score"] = scores["score"]
                try:
                    row["details"] = _tier_details(orig, base_witnesses.get(tier, {}).get(h), tier, song, curves)
                except UnplayableTrace as exc:
                    if song.mode != "frame_robust":
                        raise
                    # As an unplayable FG plan's loadout gets no FG row: no frame timing plays this Base plan.
                    logger.warning("%s: no %s row for %s, its Base plan is unplayable: %s", song.chart.name, tier, h, exc)
                    continue
            if surface != "meta":
                witness = fg_witnesses.get(tier, {}).get(h)
                row["fg_score"] = scores["fg_score"]
                row["fg_base_score"] = scores["fg_base_score"]
                row["force"] = dict(witness) if isinstance(witness, dict) else None
                if surface == "fg":
                    row["details"] = _fg_identity_details(row["force"], song.chart)
            row.update((k, scores[k]) for k in _SOURCE_KEYS if k in scores)
            out_entries.append(row)
        batches[tier] = out_entries
    return batches
