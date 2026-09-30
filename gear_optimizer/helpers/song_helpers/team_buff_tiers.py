from __future__ import annotations

from heapq import nsmallest
import re

from ...core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    OPTIMIZER_BASELINE_TEAM_BUFF,
    normalize_team_buff_sequence,
    team_buff_effect,
)
from ...core.utils import get_selected_element, safe_int as _safe_int
from ...data.loadout_equivalence import representative_mini_names
from ...chart import Chart
from ...gamedata import Gear, Mini, SongMini, StatCurves, load_gears, load_minis, song_minis
from ...settings import paths
from ...stats import total
from ...solver.timing_envelope import TimedSong
from .fg_payload import has_valid_fg_payload, require_response_surface
from .song_config import baseline_fixed_stats


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
    groups: list[list[str]] = []
    if not minis:
        return groups
    for slot in minis if isinstance(minis, (list, tuple)) else [minis]:
        # Slot can be:
        # - "Name" (str)
        # - {"Name": "..."} (dict)
        # - ["A", "B"] (variant group)
        if isinstance(slot, (list, tuple)):
            names: list[str] = []
            for raw in slot:
                if isinstance(raw, (Mini, SongMini)):
                    names.append(raw.name)
                    continue
                if isinstance(raw, str):
                    for name in _mini_names_from_text(raw):
                        if name:
                            names.append(name)
                    continue
                s = _norm_text(raw)
                for name in _mini_names_from_text(s):
                    if name:
                        names.append(name)
            names = sorted(set(n for n in names if n))
            if names:
                groups.append(names)
            continue

        if isinstance(slot, (Mini, SongMini)):
            groups.append([slot.name])
            continue

        if isinstance(slot, str):
            names = _mini_names_from_text(slot)
            if names:
                groups.append(sorted(set(n for n in names if n)))
            continue

        s = _norm_text(slot)
        names = _mini_names_from_text(s)
        if names:
            groups.append(sorted(set(n for n in names if n)))
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
    """
    Resolve source/target TeamColor for tier delta computation.

    - source/base color: color used by persisted baseline rows (the song's primary color).
    - target color: color to evaluate output tiers against.
    """
    if base_team_color_override is None:
        base_team_color = _norm_text(chart.primary)
    else:
        base_team_color = _norm_text(base_team_color_override)

    if target_team_color_override is None:
        target_team_color = base_team_color
    else:
        target_team_color = _norm_text(target_team_color_override)

    return str(base_team_color), str(target_team_color)


def _entry_origin_priority(entry: dict) -> tuple[int, int, int]:
    force_obj = entry.get("force")
    has_force = 1 if isinstance(force_obj, dict) and has_valid_fg_payload(force_obj) else 0
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
    keys = set(base.keys()) | set(target.keys())
    out: dict[str, int] = {}
    for k in keys:
        delta = int(target.get(k, 0) or 0) - int(base.get(k, 0) or 0)
        if delta:
            out[str(k)] = int(delta)
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

    Two callers feed entries here. The serving paths pass entries whose ``gear``/``minis`` are
    already items (catalog items, or a job's custom-pool items, which only the job knows); the
    persistence canonicalizer keeps them as item NAME STRINGS (the loadout hash is derived from
    names). Names resolve through Gears.csv/Minis.csv, minis as the per-entry "minis" field does,
    so the per-tier gem re-solve has ONE entry contract regardless of caller. Fail loud if the
    loadout does not resolve to exactly 6 gear + 3 minis.
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
    loadout_items: list[dict],
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
) -> dict:
    """Lossless FG re-solve for ONE loadout at one (tier·color·timing) config.

    ``fixed_song_stats`` is the tier-adjusted song fixed-stats row; ``loadout_items`` is the
    loadout's 6 gear + 3 mini stat dicts before gems. Re-solves the gem allocation
    at ``total_budget=GEM_BUDGET`` via the canonical FG response frontier (GPU search on the
    fp-gated kernel -- f32 on MoltenVK / f64 on AMD -- then CPU-f64 exact rescore), and returns the
    materialized ``force`` payload (re-solved GemCounts/Stats/Score + frontier_trace). The FG solve
    + paired-base score follow the ``song`` timing, so one recipe serves zero_ms and perfect_window. Shared by serving and the lossless-exact gate, so
    served == native.
    """
    from gear_optimizer.rules import GEM_BUDGET
    from ...solver.fg_response_scoring.fixed_timing import build_fixed_timing_fg_replays

    pre_gem_stats = _pre_gem_loadout_stats(fixed_song_stats, loadout_items)
    replays = build_fixed_timing_fg_replays(
        fg_stats_list=[pre_gem_stats],
        base_stats_list=[pre_gem_stats],
        song=song,
        curves=curves,
        selected_color=str(selected_color or ""),
        total_budget=int(GEM_BUDGET),
    )
    if len(replays) != 1:
        raise ValueError(f"tier FG re-solve expected exactly one replay, got {len(replays)}")
    return replays[0]["force"]


def resolve_tier_fg_force_batch(
    *,
    fixed_song_stats: dict,
    loadouts: list,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
) -> list:
    """Batched lossless FG re-solve: all N loadouts of a (tier·color·timing) in ONE call.

    ``build_fixed_timing_fg_replays`` already packs its stat list into one GPU response-frontier
    dispatch, so this re-solves a full leaderboard's FG in one shot instead of N sequential calls.
    ``fixed_song_stats`` is the shared tier-adjusted song fixed-stats row; ``loadouts`` is the list
    of N loadout item-stat rows; the FG solve + paired-base score follow the ``song`` timing.
    Returns N ``force`` payloads in order. Each loadout's surface/gem search
    is independent, so the per-loadout result equals ``resolve_tier_fg_force`` (the gate's
    per-loadout path) -> served == native (delta=0)."""
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
    """Lossless BASE (meta) re-solve for ONE loadout at one (tier·color·timing) config: the batch of one.

    ``fixed_song_stats`` is the tier-adjusted song fixed-stats row; ``loadout_items`` is the loadout's 6 gear + 3
    mini stat dicts before gems. Returns ``(resolved_payload, score)``. The lossless gate's per-loadout path, so
    gate == served (delta=0)."""
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
    """Batched lossless BASE re-solve: all N loadouts of a (tier·color·timing) in ONE GPU dispatch.

    The per-song serving path -- a full leaderboard re-solves in one skyline dispatch
    (``n_genomes=N``) instead of N sequential solves. ``fixed_song_stats`` is the shared
    tier-adjusted song fixed-stats row; ``loadouts`` is the list of N loadout item-stat rows. The
    score is the gem search's exact score at ``song``'s timing (zero_ms -> fixed-0ms; perfect_window
    -> the timing frontier). Returns N ``(resolved_payload, score)`` in order. Each loadout's gem
    search is independent, so a loadout's result does not depend on the batch it is solved in."""
    from ...solver.scoring.fever_solver import solve_best_fever_combination_batch

    rows = list(loadouts or [])
    if not rows:
        return []
    pre_gem_rows = [_pre_gem_loadout_stats(fixed_song_stats, items) for items in rows]
    results = solve_best_fever_combination_batch(
        pre_gem_rows,
        song,
        curves,
        selected_color=str(selected_color or "") or str(primary_color or ""),
    )
    if len(results) != len(rows):
        raise ValueError(f"batched tier base re-solve returned {len(results)} != {len(rows)} results")
    return [(resolved, int(resolved["Score"])) for resolved in results]


def _ensure_stats_include_base_effect(stats: dict, base_effect: dict[str, int]) -> dict:
    if not isinstance(stats, dict) or not stats or not isinstance(base_effect, dict) or not base_effect:
        return stats if isinstance(stats, dict) else {}
    base_pp = _safe_int(base_effect.get("Perfect Points", 0), 0)
    if base_pp <= 0:
        return dict(stats)
    pp0 = _safe_int(stats.get("Perfect Points", 0), 0)
    if pp0 < base_pp:
        return _apply_stat_delta(stats, base_effect)
    return dict(stats)


def _apply_details_delta(details: object, delta: dict[str, int]) -> dict:
    if not isinstance(details, dict) or not details:
        return {}
    if not delta:
        return dict(details)
    out = dict(details)
    stats = out.get("Stats")
    if isinstance(stats, dict) and stats:
        out["Stats"] = _apply_stat_delta(stats, delta)
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
    """
    Re-solve each persisted entry's loadout under TeamBuff tiers and return per-tier
    leaderboards.

    The persisted entries supply only the loadout SET (gear + minis). The gem allocation is
    RE-SOLVED per (tier, color) on BOTH surfaces -- the persisted T5 gems are never reused
    as-is, because a different tier or team color shifts the stat vector (a color selects
    which element stat is buffed; the tier sets the magnitude) and therefore the optimal gem
    split. Base and FG scoring use CPU-f64 exact replay for retained rows; GPU remains the
    search path and replay/canonicalization is the final user-visible score authority.

    Per tier (and per team color):
    - BASE: re-allocate the full gem budget from the tier/color-shifted song fixed stats +
      loadout item stats via the canonical GPU base exhaustive search, then CPU-f64 exact
      rescore (see the base re-solve loop below). The meta leaderboard always shows the
      per-tier optimum, never inherited T5 gems.
    - FG: re-allocate the 90-gem budget from pre-gem stats via the canonical FG response
      frontier, then CPU-f64 exact rescore. ONE exception -- an EXACT identical-context
      carry: when ``song.mode == "perfect_window"`` AND the tier is the baseline team buff
      AND there is no team-color shift, no re-solve variable differs from the solve that
      produced the entry, so the persisted force payload already IS this (tier, color,
      timing) optimum and is carried verbatim (exact, not an approximation).
    - Produces top-N lists by base score and FG score per tier.

    ``song.mode`` is the timing model the replay answers:
    - "perfect_window" (default): envelope-optimal exact replay (the baseline-tier FG carry
      above applies only here).
    - "zero_ms" (issue #51): every hit at chart time. BOTH surfaces still re-solve gems per
      tier -- the persisted Perfect-window surface is not valid at 0ms -- so no carry applies
      here. Base scores on the fixed chart-time fever timeline; FG re-optimizes each loadout's
      surface at chart timing. Forcing greats still helps at 0ms (it shifts fever activation
      via fill length), so FG 0ms is not base 0ms.
    """
    n = max(0, int(limit))
    if not entries or n <= 0:
        return {"tiers": {}, "meta": {"candidate_count": 0}}
    replay_meta = "meta" in {str(s).strip().lower() for s in (replay_surfaces or ("meta", "fg"))}
    replay_fg = "fg" in {str(s).strip().lower() for s in (replay_surfaces or ("meta", "fg"))}

    primary_color = _norm_text(song.chart.primary)
    secondary_color = _norm_text(song.chart.secondary)

    base_team_color, target_team_color = _resolve_team_colors_for_tiering(
        song.chart,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    base_team_buff = OPTIMIZER_BASELINE_TEAM_BUFF
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)

    per_entry: list[dict] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details") or {}
        if not isinstance(details, dict):
            details = {}
        stats_base_raw = details.get("Stats") or {}
        if not isinstance(stats_base_raw, dict) or not stats_base_raw:
            continue

        gear = _flat_item_names(entry.get("gear") or [])
        minis = _representative_mini_names_from_any(entry.get("minis") or [])

        force_obj = entry.get("force")
        fg_snapshot = None
        if isinstance(force_obj, dict) and has_valid_fg_payload(force_obj):
            # Fail loud: an FG row must carry a valid response surface. The empty marker only
            # records presence; the exact witness remains on the force payload.
            require_response_surface(force_obj)
            fg_snapshot = {}

        if song.mode == "zero_ms" and secondary_color:
            # Defensive (review #1/#2): team-buff meta loadouts are always primary-selected -- the
            # native optimizer fixes the selected element to the song primary, which is why the 0ms
            # re-solve forces selected_color=primary_color (one color for the whole batch). If a
            # persisted loadout ever carries a different selected element on a multi-color song,
            # forcing primary would silently diverge from native; fail loud instead of serving a
            # wrong card. (Empty/absent -> skip; single-color -> skip; so this never false-fires.)
            persisted_se = _norm_text(
                get_selected_element(force_obj, "") if isinstance(force_obj, dict) else ""
            ) or _norm_text(get_selected_element(details, ""))
            if persisted_se and persisted_se != primary_color:
                raise ValueError(
                    f"zero_ms re-solve invariant violated: loadout {_norm_text(entry.get('loadout_hash'))!r} "
                    f"persists selected element {persisted_se!r} != song primary {primary_color!r}; the "
                    f"forced-primary re-solve would diverge from native. The re-solve must honor the "
                    f"per-loadout selected element before this can serve."
                )

        per_entry.append(
            {
                "loadout_hash": _norm_text(entry.get("loadout_hash", "")),
                "gear": gear,
                "minis": minis,
                "source_score": _safe_int(entry.get("score"), 0),
                "source_fg_base_score": _safe_int(entry.get("fg_base_score"), _safe_int(entry.get("score"), 0)),
                "source_fg_score": _safe_int(entry.get("fg_score"), 0),
                "fg": fg_snapshot,
                # Raw entry keeps the loadout item stats needed by the zero_ms gem re-solve.
                "_entry": entry,
            }
        )

    # The song's baseline fixed stats, shared by BOTH the base (meta) and FG re-solves, for BOTH timing
    # modes, so they (and the lossless gate) start from the same stats. The gem search reads timing
    # from the song, so the SAME re-solve serves zero_ms and perfect_window; only the final exact
    # rescore differs.
    tier_song_fixed_stats = baseline_fixed_stats(song.chart)

    meta_scores_by_tier: dict[str, list[int]] = {}
    # Per (tier, loadout_hash) RE-SOLVED base payloads (re-solved Stats/GemCounts/Score) -- for BOTH
    # timing modes. The meta leaderboard always shows the per-tier optimum, never inherited T5 gems.
    resolved_base_by_tier_hash: dict[str, dict[str, dict]] = {}
    if replay_meta and per_entry:
        # Lossless BASE re-solve: per (loadout, tier), re-allocate the gem budget from song fixed
        # stats + loadout item stats via the canonical GPU base exhaustive search + CPU-f64 exact
        # rescore at the mode's timing. Both zero_ms and perfect_window re-solve per tier -- the
        # persisted gems are a T5 allocation that is NOT the per-tier optimum at either timing.
        base_loadouts = [_entry_loadout_items(e.get("_entry") or {}, song.chart) for e in per_entry]
        for tier in tier_list:
            delta_map = _team_buff_delta_map(
                base_team_buff=base_team_buff,
                target_team_buff=str(tier),
                base_team_color=base_team_color,
                target_team_color=target_team_color,
            )
            tier_fixed_stats = _apply_stat_delta(tier_song_fixed_stats, delta_map)
            # Batched: ALL loadouts of this tier re-solve in ONE GPU dispatch (n_genomes=N is the
            # low-level solver batch dimension). Per-loadout result is identical to the
            # single-loadout path (independent gem searches) -> delta=0.
            batch = resolve_tier_base_batch(
                fixed_song_stats=tier_fixed_stats,
                loadouts=base_loadouts,
                song=song,
                curves=curves,
                primary_color=primary_color,
                selected_color=primary_color,
            )
            witness_for_tier = resolved_base_by_tier_hash.setdefault(str(tier), {})
            for i, e in enumerate(per_entry):
                h = _norm_text(e.get("loadout_hash"))
                if h:
                    witness_for_tier[h] = batch[i][0]
            meta_scores_by_tier[str(tier)] = [int(score) for (_resolved, score) in batch]
    else:
        meta_scores_by_tier = {str(t): [0] * len(per_entry) for t in tier_list}

    fg_scores_by_tier: dict[str, list[int]] = {str(t): [0] * len(per_entry) for t in tier_list}
    # Per (tier, loadout_hash) FG force payloads consumed by build_team_buff_tier_db_batches for
    # BOTH timing modes: the baseline perfect_window tier carries the persisted force verbatim
    # (identical-context carry below); every other (tier, mode) stores the re-solved witness
    # (re-solved GemCounts/Stats/Score + the mode's note-graph trace).
    resolved_fg_force_by_tier_hash: dict[str, dict[str, dict]] = {}
    have_fg = replay_fg and any(isinstance(e.get("fg"), dict) for e in per_entry)
    if have_fg:
        fg_indices = [idx for idx, e in enumerate(per_entry) if isinstance(e.get("fg"), dict)]
        # Lossless FG re-solve: per (loadout, tier), re-allocate the 90-gem budget from song fixed
        # stats + loadout item stats at the mode's timing, via the canonical GPU FG kernel (fp-gated
        # f32/f64) + CPU-f64 exact rescore -> served == native optimum. Both modes re-solve per tier:
        # the persisted FG surface + gems are a T5 allocation, NOT the per-tier optimum at either
        # timing (the tier shifts stats -> the optimal great placement + gems shift too).
        fg_loadouts = [_entry_loadout_items(per_entry[idx].get("_entry") or {}, song.chart) for idx in fg_indices]
        for tier in tier_list:
            out_list = fg_scores_by_tier[str(tier)]
            witness_for_tier = resolved_fg_force_by_tier_hash.setdefault(str(tier), {})
            if (
                song.mode == "perfect_window"
                and str(tier) == str(base_team_buff)
                and base_team_color == target_team_color
            ):
                # Identical-context carry (carry-don't-recompute doctrine): at the baseline
                # tier, perfect_window timing, and no team-color shift, NO re-solve variable
                # differs from the solve that produced the entry — the persisted force payload
                # IS this (tier, timing, color)'s exact frontier optimum (the fused FG owner +
                # materializer derived it from the same response frontier this re-solve would
                # re-derive, and the persistence gateway exact-verifies it downstream via
                # canonicalize_authoritative_fg_entries, fail-loud). Re-solving here re-paid
                # the response-frontier bundle load + per-loadout surface re-solve + trace
                # re-search per song — the measured post-processor burner on heavy songs.
                # Any differing variable keeps the full re-solve below: a tier shift
                # re-allocates gems, zero_ms rebuilds surfaces, color overrides shift stats.
                for idx in fg_indices:
                    raw_force = (per_entry[idx].get("_entry") or {}).get("force")
                    if not isinstance(raw_force, dict):
                        raise ValueError(
                            "baseline-tier FG carry requires the persisted force payload "
                            f"(loadout {per_entry[idx].get('loadout_hash')!r})"
                        )
                    # The entry-level fg_score is the canonical exact surface score
                    # (surface-authority doctrine); carry it verbatim. Every producer of an
                    # FG-candidate entry (fused materializer, persistence canonicalizer) sets
                    # fg_score to the force payload's positive exact score, so an entry that
                    # reached fg_indices (valid FG config + response surface, gated above) with a
                    # non-positive fg_score is internally inconsistent (a stale/missing top-level
                    # fg_score against a valid force). The re-solve branch below would have RANKED
                    # such a row from its freshly recomputed force Score (> 0); the carry does NOT
                    # recompute, so ranking by a non-positive fg_score would silently DROP the row
                    # via the `fg_score > 0` filter. Fail loud instead of losing a valid FG loadout.
                    carried_fg = _safe_int(per_entry[idx].get("source_fg_score"), 0)
                    if carried_fg <= 0:
                        raise ValueError(
                            "baseline-tier FG carry: loadout "
                            f"{per_entry[idx].get('loadout_hash')!r} carries a valid force payload "
                            f"but a non-positive fg_score ({carried_fg}); refusing to silently drop "
                            "the row. The persisted fg_score IS the exact surface score and a valid "
                            "FG force always scores > 0 -- re-canonicalize the source entry."
                        )
                    out_list[idx] = carried_fg
                    h = _norm_text(per_entry[idx].get("loadout_hash"))
                    if h:
                        witness_for_tier[h] = raw_force
                continue
            delta_map = _team_buff_delta_map(
                base_team_buff=base_team_buff,
                target_team_buff=str(tier),
                base_team_color=base_team_color,
                target_team_color=target_team_color,
            )
            tier_fixed_stats = _apply_stat_delta(tier_song_fixed_stats, delta_map)
            # Batched: all FG loadouts of this tier re-solve in ONE response-frontier dispatch
            # (build_fixed_timing_fg_replays packs the stat list), so a full leaderboard's FG is
            # one solve instead of N. Per-loadout result is identical (independent searches).
            fg_forces = resolve_tier_fg_force_batch(
                fixed_song_stats=tier_fixed_stats,
                loadouts=fg_loadouts,
                song=song,
                curves=curves,
                selected_color=primary_color,
            )
            for idx, force in zip(fg_indices, fg_forces, strict=True):
                out_list[idx] = int(force.get("Score") or 0)
                h = _norm_text(per_entry[idx].get("loadout_hash"))
                if h:
                    witness_for_tier[h] = force

    tiers_out: dict[str, dict] = {}
    for tier in tier_list:
        base_scores = meta_scores_by_tier.get(str(tier), [])
        fg_scores_for_tier = fg_scores_by_tier.get(str(tier)) if have_fg else None

        base_ranked: list[dict] = []
        fg_ranked: list[dict] = []

        for i, e in enumerate(per_entry):
            base_score = int(base_scores[i]) if replay_meta and i < len(base_scores) else 0
            fg_score = 0
            if fg_scores_for_tier is not None and i < len(fg_scores_for_tier):
                fg_score = int(fg_scores_for_tier[i] or 0)
            fg = e.get("fg")

            if replay_meta:
                base_ranked.append(
                    {
                        "loadout_hash": e.get("loadout_hash") or "",
                        "gear": e.get("gear") or [],
                        "minis": e.get("minis") or [],
                        "score": int(base_score),
                        "source_score": int(e.get("source_score") or 0),
                    }
                )

            if replay_fg and isinstance(fg, dict) and int(fg_score) > 0:
                # The FG row's paired base IS the same loadout's base score, already computed
                # losslessly by the per-tier base re-solve above (== base_score) for whichever
                # timing mode is active. Carry it verbatim. A separate paired-base recompute
                # is what drifted before: it scored the loadout's pre-gem stats (FeverFill 0,
                # no element gems), yielding ~30-45% of the real base. Because the FG paired
                # base is the meta base, FG replay requires the meta surface.
                if not replay_meta:
                    raise ValueError(
                        "FG replay requires the 'meta' surface: the FG paired base is the "
                        "loadout's re-solved base score, computed only when meta is replayed."
                    )
                fg_ranked.append(
                    {
                        "loadout_hash": e.get("loadout_hash") or "",
                        "gear": e.get("gear") or [],
                        "minis": e.get("minis") or [],
                        "fg_score": int(fg_score),
                        "fg_base_score": int(base_score),
                        "source_score": int(e.get("source_score") or 0),
                        "source_fg_base_score": int(e.get("source_fg_base_score") or 0),
                        "source_fg_score": int(e.get("source_fg_score") or 0),
                    }
                )

        base_top = nsmallest(
            int(n),
            base_ranked,
            key=lambda r: (-int(r.get("score", 0) or 0), str(r.get("loadout_hash") or "")),
        )
        fg_top = nsmallest(
            int(n),
            fg_ranked,
            key=lambda r: (-int(r.get("fg_score", 0) or 0), str(r.get("loadout_hash") or "")),
        )
        tiers_out[str(tier)] = {"base_top51": base_top, "fg_top51": fg_top}

    return {
        "meta": {
            "candidate_count": int(len(per_entry)),
            "team_color": target_team_color,
            "base_team_color": base_team_color,
            "target_team_color": target_team_color,
            "base_team_buff": base_team_buff,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
        },
        "tiers": tiers_out,
        # Per (tier, hash) FG force payloads consumed by build_team_buff_tier_db_batches for BOTH
        # timing modes (baseline perfect_window = the carried persisted force; every other
        # (tier, mode) = the re-solved witness carrying the mode's note-graph trace).
        "resolved_fg_force_by_tier_hash": resolved_fg_force_by_tier_hash,
        # Per (tier, hash) RE-SOLVED base payloads (re-solved Stats/GemCounts/Score) consumed by
        # build_team_buff_tier_db_batches for BOTH timing modes.
        "resolved_base_by_tier_hash": resolved_base_by_tier_hash,
    }


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
    """
    Return DB-ready entry batches per tier.

    Output format:
        { "T5": [ {score, fg_score, gear, minis, details, force}, ... ], ... }

    Selection:
    - meta: top-N by replayed base score only
    - fg: top-N by replayed FG score only
    - both: union(top-N base, top-N FG) for persistence canonicalization

    ``song.mode`` is the timing model (see ``compute_team_buff_tier_leaderboards``):
    - "perfect_window" (default): envelope-optimal exact replay. Persistence
      canonicalization always uses this.
    - "zero_ms" (issue #51): every hit at chart time. Scores come from the 0ms
      leaderboards; the base note graph is the chart-fixed timeline (no Perfect-window
      ``TimelineFrontier`` is attached, so the renderer draws delta=0 from ``Stats``), and
      each FG row carries the rebuilt 0ms ``force`` (chart-fixed ``frontier_trace``) rather
      than the persisted Perfect-window one. zero_ms rankings use the prebuilt chart-only
      response frontier; tier materialization remains a derived view and is not persisted to
      the canonical leaderboards.
    """
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)
    is_zero_ms = song.mode == "zero_ms"
    surface = str(replay_surface or "both").strip().lower()
    if surface not in {"meta", "fg", "both"}:
        surface = "both"
    replay_surfaces = ("meta", "fg") if surface == "both" else (surface,)

    from ...solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace

    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        song=song,
        curves=curves,
        limit=limit,
        tiers=tier_list,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
        replay_surfaces=replay_surfaces,
    )
    resolved_fg_force_by_tier_hash = payload.get("resolved_fg_force_by_tier_hash") or {}
    resolved_base_by_tier_hash = payload.get("resolved_base_by_tier_hash") or {}

    payload_meta = payload.get("meta") or {}
    base_team_buff = _norm_text(payload_meta.get("base_team_buff")) or OPTIMIZER_BASELINE_TEAM_BUFF
    base_team_color = _norm_text(payload_meta.get("base_team_color"))
    target_team_color = _norm_text(payload_meta.get("target_team_color"))
    if not base_team_color or not target_team_color:
        base_team_color, target_team_color = _resolve_team_colors_for_tiering(
            song.chart,
            base_team_color_override=base_team_color_override,
            target_team_color_override=target_team_color_override,
        )
    base_effect = team_buff_effect(base_team_buff, base_team_color)

    orig_by_hash: dict[str, dict] = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        h = _loadout_hash(e)
        if not h:
            continue
        current = orig_by_hash.get(h)
        if not isinstance(current, dict) or _entry_origin_priority(e) > _entry_origin_priority(current):
            orig_by_hash[h] = e

    batches: dict[str, list[dict]] = {}
    for tier, tier_payload in (payload.get("tiers") or {}).items():
        delta_map = _team_buff_delta_map(
            base_team_buff=base_team_buff,
            target_team_buff=str(tier),
            base_team_color=base_team_color,
            target_team_color=target_team_color,
        )
        base_top = tier_payload.get("base_top51") or []
        fg_top = tier_payload.get("fg_top51") or []

        if surface == "meta":
            selected_rows = [r for r in base_top if isinstance(r, dict)]
        elif surface == "fg":
            selected_rows = [r for r in fg_top if isinstance(r, dict)]
        else:
            base_score_by_hash: dict[str, int] = {}
            fg_score_by_hash: dict[str, int] = {}
            fg_base_score_by_hash: dict[str, int] = {}
            source_score_by_hash: dict[str, int] = {}
            source_fg_base_score_by_hash: dict[str, int] = {}
            source_fg_score_by_hash: dict[str, int] = {}
            ordered_hashes: list[str] = []
            ordered_hash_set: set[str] = set()

            for r in base_top:
                if not isinstance(r, dict):
                    continue
                h = _loadout_hash(r)
                if not h:
                    continue
                base_score_by_hash[h] = _safe_int(r.get("score"), 0)
                fg_score_by_hash[h] = _safe_int(r.get("fg_score"), 0)
                if "source_score" in r:
                    source_score_by_hash[h] = _safe_int(r.get("source_score"), 0)
                if "source_fg_base_score" in r:
                    source_fg_base_score_by_hash[h] = _safe_int(r.get("source_fg_base_score"), 0)
                if "source_fg_score" in r:
                    source_fg_score_by_hash[h] = _safe_int(r.get("source_fg_score"), 0)
                if h not in ordered_hash_set:
                    ordered_hashes.append(h)
                    ordered_hash_set.add(h)

            for r in fg_top:
                if not isinstance(r, dict):
                    continue
                h = _loadout_hash(r)
                if not h:
                    continue
                fg_score_by_hash[h] = _safe_int(r.get("fg_score"), 0)
                fg_base_score_by_hash[h] = _safe_int(r.get("fg_base_score"), 0)
                if h not in base_score_by_hash:
                    base_score_by_hash[h] = _safe_int(r.get("score"), 0)
                if "source_score" in r:
                    source_score_by_hash[h] = _safe_int(r.get("source_score"), 0)
                if "source_fg_base_score" in r:
                    source_fg_base_score_by_hash[h] = _safe_int(r.get("source_fg_base_score"), 0)
                if "source_fg_score" in r:
                    source_fg_score_by_hash[h] = _safe_int(r.get("source_fg_score"), 0)
                if h not in ordered_hash_set:
                    ordered_hashes.append(h)
                    ordered_hash_set.add(h)

            selected_hashes = set(base_score_by_hash.keys()) | set(fg_score_by_hash.keys())
            if len(ordered_hash_set) < len(selected_hashes):
                ordered_hashes.extend(sorted(selected_hashes - ordered_hash_set))
            selected_rows = []
            for h in ordered_hashes:
                orig = orig_by_hash.get(h)
                if not isinstance(orig, dict):
                    continue
                selected_rows.append(
                    {
                        "_hash": h,
                        "_orig": orig,
                        "score": int(base_score_by_hash.get(h, 0) or 0),
                        "fg_score": int(fg_score_by_hash.get(h, 0) or 0),
                        "fg_base_score": int(fg_base_score_by_hash.get(h, 0) or 0),
                        "source_score": int(source_score_by_hash.get(h, orig.get("source_score", 0)) or 0),
                        "source_fg_base_score": int(
                            source_fg_base_score_by_hash.get(h, orig.get("source_fg_base_score", 0)) or 0
                        ),
                        "source_fg_score": int(source_fg_score_by_hash.get(h, orig.get("source_fg_score", 0)) or 0),
                    }
                )

        out_entries: list[dict] = []
        for r in selected_rows:
            if surface == "both":
                orig = r.get("_orig")
                if not isinstance(orig, dict):
                    continue
                score_out = int(r.get("score") or 0)
                fg_score_out = int(r.get("fg_score") or 0)
                fg_base_score_out = int(r.get("fg_base_score") or 0)
            else:
                h = _loadout_hash(r)
                orig = orig_by_hash.get(h)
                if not isinstance(orig, dict):
                    continue
                score_out = _safe_int(r.get("score"), 0)
                fg_score_out = _safe_int(r.get("fg_score"), 0)
                fg_base_score_out = _safe_int(r.get("fg_base_score"), 0)

            details_out: dict = {}
            force_out: object = None
            if surface in {"meta", "both"}:
                details_base = orig.get("details") or {}
                if not isinstance(details_base, dict):
                    details_base = {}
                if isinstance(details_base, dict):
                    stats0 = details_base.get("Stats")
                    if isinstance(stats0, dict) and stats0:
                        details_base = dict(details_base)
                        details_base["Stats"] = _ensure_stats_include_base_effect(stats0, base_effect)
                details_out = _apply_details_delta(details_base, delta_map)
                # `_apply_details_delta` copies the baseline (T5) details verbatim except for
                # Stats, so `details_out` inherits the baseline TimelineFrontier — a per-note
                # trace that is WRONG for this (shifted) tier. Drop it unconditionally: the
                # per-tier graph must come from the fresh exact recompute below, never from the
                # stale baseline witness. Fail safe — any TimelineFrontier a consumer sees is
                # guaranteed to be for THIS tier; if the recompute cannot produce one, the row
                # carries none and the consumer omits the graph rather than drawing another
                # tier's timing (issue #38, base surface).
                if isinstance(details_out, dict):
                    details_out.pop("TimelineFrontier", None)
                if isinstance(details_out, dict):
                    # Lossless tier base re-solve (BOTH timing modes): replace the inherited
                    # Stats/GemCounts with the RE-SOLVED (at-tier) witness so the served base card
                    # shows the per-tier-optimal gems + score (the meta leaderboard score already
                    # comes from the same re-solve). No tier delta -- the witness is already at-tier.
                    h_base = _norm_text(orig.get("loadout_hash"))
                    base_witness = resolved_base_by_tier_hash.get(str(tier), {}).get(h_base)
                    # Fail loud (mirrors the FG witness path): a hashed base row MUST have its
                    # re-solved witness. Silently keeping the inherited T5 Stats/GemCounts would serve
                    # a wrong (suboptimal / mis-scored) card.
                    if h_base and not isinstance(base_witness, dict):
                        raise ValueError(
                            f"tier base re-solve missing witness for loadout {h_base!r} at tier {tier!r}."
                        )
                    if isinstance(base_witness, dict):
                        w_stats = base_witness.get("Stats")
                        if isinstance(w_stats, dict) and w_stats:
                            details_out["Stats"] = dict(w_stats)
                        w_gems = base_witness.get("GemCounts")
                        if isinstance(w_gems, dict):
                            details_out["GemCounts"] = dict(w_gems)
                        # The witness is the COMPLETE at-tier re-solve, so its FT/FF MUST replace the
                        # inherited (T5) FT/FF too. The re-solved core gems fill budget = 90 - re-solved
                        # ft - ff; pairing them with the baseline's ft/ff lets the served gemCounts sum
                        # past the 90-gem budget (an impossible build / false card -- the served score is
                        # the legal re-solve, only the displayed FT/FF were stale). build_processing reads
                        # details["FT"]/["FF"] for the served Fever Time/Fill gem counts.
                        details_out["FT"] = int(base_witness.get("FT") or 0)
                        details_out["FF"] = int(base_witness.get("FF") or 0)
                        # Drop the stale compact aliases of the inherited Stats/GemCounts: unpack prefers
                        # the long keys we just grafted, but _pack_stats_for_storage only regenerates
                        # st/gc when ABSENT, so leaving the baseline arrays here would re-persist the wrong
                        # allocation. One canonical at-tier representation per row.
                        for _stale_alias in ("st", "gc", "gk"):
                            details_out.pop(_stale_alias, None)
                # Recompute the per-note timeline trace for the tier-shifted stats so the
                # base note graph reflects this tier rather than the frozen baseline
                # witnesses (issue #38, point 4 — base surface). Additive only: the row's
                # `score` already comes from the leaderboard; this attaches a TimelineFrontier
                # whose frontier_trace the consumer uses to draw an exact per-tier graph.
                # zero_ms (issue #51): the Perfect-window timing frontier does not apply at fixed
                # 0ms timing, so attach NO TimelineFrontier — the row carries Stats only and the
                # consumer reconstructs the deterministic chart-time timeline (every note delta=0)
                # from those stats. Fail safe: never a Perfect-window trace under a 0ms score.
                trace_stats = details_out.get("Stats") if isinstance(details_out, dict) else None
                if not is_zero_ms and isinstance(trace_stats, dict) and trace_stats:
                    timeline_frontier = score_stats_exact_with_timeline_trace(
                        trace_stats, song, curves
                    ).get("TimelineFrontier")
                    if isinstance(timeline_frontier, dict) and timeline_frontier.get("frontier_trace"):
                        details_out["TimelineFrontier"] = timeline_frontier

            if surface in {"fg", "both"}:
                # Lossless tier FG re-solve (BOTH timing modes): the served FG force IS the re-solved
                # witness for this (tier, loadout) -- re-solved GemCounts/Stats/Score + the mode's
                # note-graph frontier_trace, already at this tier. Use it directly (it is NOT the
                # persisted force, and the tier delta does not apply). No witness -> drop the FG card.
                witness = resolved_fg_force_by_tier_hash.get(str(tier), {}).get(_norm_text(orig.get("loadout_hash")))
                force_out = dict(witness) if isinstance(witness, dict) else None

            out_row: dict = {
                "loadout_hash": str(orig.get("loadout_hash") or ""),
                "gear": _flat_item_names(orig.get("gear")),
                "minis": _representative_mini_names_from_any(orig.get("minis")),
            }
            if surface in {"meta", "both"}:
                out_row["score"] = score_out
                out_row["details"] = details_out
            if surface in {"fg", "both"}:
                out_row["fg_score"] = fg_score_out
                out_row["fg_base_score"] = fg_base_score_out
                out_row["force"] = force_out
                if surface == "fg":
                    out_row["details"] = _fg_identity_details(force_out, song.chart)
            if surface == "both":
                for src_key in ("source_score", "source_fg_base_score", "source_fg_score"):
                    out_row[src_key] = int(r.get(src_key, 0) or 0)
            else:
                for src_key in ("source_score", "source_fg_base_score", "source_fg_score"):
                    if src_key in r:
                        out_row[src_key] = _safe_int(r.get(src_key), 0)

            out_entries.append(out_row)
        batches[str(tier)] = out_entries

    return batches
