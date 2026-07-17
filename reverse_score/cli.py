"""CLI endpoint for the reverse score engine.

Usage (from the repo root):
    python -m reverse_score tables     [--webport PATH]
    python -m reverse_score generate   --song "NAME|Difficulty" --n 50 --seed 1 [--out FILE]
    python -m reverse_score invert     --song "NAME|Difficulty" --score S --naked N --gear-power P
    python -m reverse_score roundtrip  --song "NAME|Difficulty" --n 20 --seed 1
    python -m reverse_score bench      --song "NAME|Difficulty" --n 20 --spec production
    python -m reverse_score invert-row --dump robeats_top1_song_leaderboards.json --title "Step Forward"

``roundtrip``/``bench`` are the acceptance commands: synthesize labeled plays
through the forward oracle, invert their observables (exactly the fields the
client UI exposes for another player), and verify the true loadout is
recovered with production-speed latency. ``invert-row`` runs a real
leaderboard row: the chart is located by title and confirmed by the
naked-score fingerprint (exact version-match check) before inversion.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

from .domain import GEAR_SLOTS, MiniState, Tables, build_tables
from .engine import (
    DomainSpec,
    DomainMismatch,
    EngineError,
    canonical_form,
    contains_loadout,
    invert,
    invert_progressive,
)
from .game_model import GEARPOWER_MAIN_KEYS
from .oracle import Observables, SongOracle, resolve_chart
from .synthetic import generate, to_json_rows
from .webport_extract import UPGRADES_PER_PIECE_MAX, extract_pets, extract_upgrades

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEBPORT = Path.home() / "Desktop" / "[REDACTED PRIVATE REPOSITORY]"


def start_ram_watchdog(min_available_gib: float = 6.0) -> None:
    """Abort the process loudly if available RAM sinks below the floor.

    The target box has no pagefile; an unnoticed allocation spiral would
    hard-freeze it. The engine bounds its own allocations, but heavy commands
    run under this belt-and-suspenders guard anyway."""
    import psutil

    def _watch() -> None:
        while True:
            if psutil.virtual_memory().available / 2**30 < min_available_gib:
                print(
                    f"RAM WATCHDOG ABORT: available memory below "
                    f"{min_available_gib:.1f} GiB",
                    flush=True,
                )
                os._exit(97)
            time.sleep(0.25)

    threading.Thread(target=_watch, daemon=True).start()


def _webport_path(arg: str | None) -> Path:
    path = Path(arg) if arg else DEFAULT_WEBPORT
    if not path.is_dir():
        raise SystemExit(
            f"WebPort checkout not found at {path}; pass --webport PATH "
            "(the decompiled game repo is required for pet/upgrade tables)"
        )
    return path


def _load_tables(webport: Path) -> Tables:
    return build_tables(
        gears_csv=REPO_ROOT / "Data" / "Gear" / "Gears.csv",
        minis_csv=REPO_ROOT / "Data" / "Gear" / "Minis.csv",
        pets=extract_pets(webport),
        upgrades=extract_upgrades(webport),
    )


def _load_oracle(song_arg: str) -> SongOracle:
    if "|" not in song_arg:
        raise SystemExit(f'--song must be "NAME|Difficulty", got {song_arg!r}')
    name, difficulty = song_arg.rsplit("|", 1)
    chart = resolve_chart(REPO_ROOT / "Data", name, difficulty)
    print(f"chart: {chart.name}")
    return SongOracle(chart)


def build_spec(
    profile: str,
    oracle: SongOracle,
    tables: Tables,
    *,
    mini_levels: tuple[int, ...] | None = None,
    upgrade_cap: int | None = None,
    gem_cap: int | None = None,
) -> DomainSpec:
    """Named domain profiles. ``small`` keeps round-trips fast; ``default``
    widens toward the live domain; ``production`` covers unmaxed AND maxed
    builds with explicit knobs (still capped -- caps are reported)."""
    pet_names = sorted(tables.pets)
    targeted = [
        name
        for name in pet_names
        if oracle.song_display in tables.pet_song_targets.get(name, ())
    ]
    if profile == "small":
        base_names = pet_names[:3]
        mini_options: list[MiniState] = []
        for name in base_names:
            mini_options.append(MiniState(name=name, level=1, rank=1))
            mini_options.append(MiniState(name=name, level=30, rank=2))
            mini_options.append(MiniState(name=name, level=50, rank=4))
        for name in targeted[:1]:
            mini_options.append(MiniState(name=name, level=50, rank=4, ascension=10))
        upgrade_ids = _visible_upgrade_ids(oracle, tables)[:2]
        return DomainSpec(
            mini_options=tuple(mini_options),
            mini_max_equipped=2,
            upgrade_type_ids=upgrade_ids,
            upgrade_max_per_type=2,
            upgrade_total_max=4,
            gem_max_per_type=3,
            elemental_gem_max=2,
            team_buff_options=(None, ("T5", oracle.primary_color)),
        )
    if profile == "default":
        relevant = [
            name
            for name in pet_names
            if any(
                tables.pets[name].color_mods.get(c, 0) > 0 for c in oracle.song_colors
            )
        ][:8]
        mini_options = []
        for name in dict.fromkeys([*relevant, *targeted[:2]]):
            for level, rank in ((1, 1), (20, 1), (30, 2), (40, 3), (50, 4)):
                mini_options.append(MiniState(name=name, level=level, rank=rank))
            if name in targeted:
                mini_options.append(MiniState(name=name, level=50, rank=4, ascension=10))
        upgrade_ids = _visible_upgrade_ids(oracle, tables)[:5]
        return DomainSpec(
            mini_options=tuple(mini_options),
            mini_max_equipped=3,
            upgrade_type_ids=upgrade_ids,
            upgrade_max_per_type=3,
            upgrade_total_max=9,
            gem_max_per_type=6,
            elemental_gem_max=3,
            team_buff_options=DomainSpec.default_team_buffs(),
        )
    if profile == "meta":
        # Progressive-search first pass for real top-1 rows: maxed minis
        # (rank 4 / level 50, ascended variants for targeted pets), every
        # visible upgrade type to the per-piece ceiling, full gear, full
        # buffs. Real leaderboard toppers are maxed builds; a miss here is
        # loud and the caller widens to 'production'.
        mini_options = []
        for name in pet_names:
            mini_options.append(MiniState(name=name, level=50, rank=4))
        for name in targeted:
            mini_options.append(MiniState(name=name, level=50, rank=4, ascension=10))
            mini_options.append(MiniState(name=name, level=50, rank=4, ascension=5))
        return DomainSpec(
            mini_options=tuple(dict.fromkeys(mini_options)),
            mini_max_equipped=3,
            upgrade_type_ids=_visible_upgrade_ids(oracle, tables),
            upgrade_max_per_type=upgrade_cap or 15,
            # Joint ceiling is the GAME LAW (6 pieces x 15 slots), never a
            # per-type-cap multiple: totals past it can never assemble.
            upgrade_total_max=len(GEAR_SLOTS) * UPGRADES_PER_PIECE_MAX,
            gem_max_per_type=gem_cap or 15,
            elemental_gem_max=8,
            team_buff_options=DomainSpec.default_team_buffs(),
        )
    if profile == "production":
        # Full gear table; every pet at every rank-boundary level (unmaxed AND
        # maxed) plus ascended variants for song-targeted pets; every upgrade
        # type visible on this song up to the real per-type ceiling (six
        # pieces x 15 slots); gem caps stated below. Caps are explicit knobs
        # (--mini-levels/--upgrade-cap/--gem-cap) -- a real row whose build
        # exceeds a cap comes back NO PREIMAGE with that guidance, never a
        # silently wrong answer.
        level_steps = mini_levels or (1, 20, 30, 40, 50)
        upgrade_cap = upgrade_cap or 90
        gem_cap = gem_cap or 20
        mini_options = []
        for name in pet_names:
            for level in level_steps:
                mini_options.append(
                    MiniState(name=name, level=level, rank=_min_rank_for_level(level))
                )
        for name in targeted:
            mini_options.append(MiniState(name=name, level=50, rank=4, ascension=10))
            mini_options.append(MiniState(name=name, level=50, rank=4, ascension=5))
        return DomainSpec(
            mini_options=tuple(dict.fromkeys(mini_options)),
            mini_max_equipped=3,
            upgrade_type_ids=_visible_upgrade_ids(oracle, tables),
            upgrade_max_per_type=upgrade_cap,
            # Joint ceiling is the GAME LAW (6 pieces x 15 slots), never a
            # per-type-cap multiple: totals past it can never assemble, and
            # carrying them through the join is what blew the mid-band
            # lattice past every row cap.
            upgrade_total_max=len(GEAR_SLOTS) * UPGRADES_PER_PIECE_MAX,
            gem_max_per_type=gem_cap,
            elemental_gem_max=8,
            team_buff_options=DomainSpec.default_team_buffs(),
        )
    raise SystemExit(f"unknown spec profile {profile!r} (small|default|production)")


def _min_rank_for_level(level: int) -> int:
    if level > 40:
        return 4
    if level > 30:
        return 3
    if level > 20:
        return 2
    return 1


def _spec_from_args(args: argparse.Namespace, oracle: SongOracle, tables: Tables) -> DomainSpec:
    mini_levels = None
    if getattr(args, "mini_levels", None):
        mini_levels = tuple(int(x) for x in str(args.mini_levels).split(","))
    spec = build_spec(
        args.spec,
        oracle,
        tables,
        mini_levels=mini_levels,
        upgrade_cap=getattr(args, "upgrade_cap", None),
        gem_cap=getattr(args, "gem_cap", None),
    )
    force = getattr(args, "archetype", None)
    if force:
        spec = replace(spec, force_archetype=force)
    return spec


def _visible_upgrade_ids(oracle: SongOracle, tables: Tables) -> tuple[int, ...]:
    """Upgrade types whose stats project onto this song's observables.
    Invisible types (pure off-color / Perfect Time trades) are unrecoverable
    in principle and stay out of the enumerated domain.

    Negative-stat types (PerfectTime trades: -1 PP / -2 CM) are also
    excluded: they strictly reduce score, so score-grind loadouts do not run
    them, and their exclusion is what makes the engine's clamp-collapsed
    state transform exact (non-negative deltas commute with the 160 cap)."""
    visible_keys = set(oracle.song_colors) | set(GEARPOWER_MAIN_KEYS)
    return tuple(
        uid
        for uid, up in sorted(tables.upgrades_by_id.items())
        if any(k in visible_keys and v != 0 for k, v in up.stats.items())
        and all(v >= 0 for v in up.stats.values())
    )


def _describe_loadout(loadout) -> str:
    gear = ", ".join(
        f"{slot}={loadout.gear.get(slot) or '-'}" for slot in loadout.gear
    )
    ups = (
        "; upgrades " + ", ".join(f"{s}:{list(v)}" for s, v in loadout.upgrades.items())
        if loadout.upgrades
        else ""
    )
    minis = (
        "; minis "
        + ", ".join(
            f"{m.name}(L{m.level} R{m.rank}" + (f" A{m.ascension})" if m.ascension else ")")
            for m in loadout.minis
        )
        if loadout.minis
        else ""
    )
    gems = loadout.gems
    gem_bits = [
        f"{k}={v}"
        for k, v in (
            ("PP", gems.perfect_points),
            ("CM", gems.combo_multiplier),
            ("FM", gems.fever_multiplier),
            ("FT", gems.fever_time),
            ("FF", gems.fever_fill),
        )
        if v
    ]
    if gems.elemental:
        gem_bits.append(f"elem[{gems.selected_element}]={gems.elemental}")
    gem_str = "; gems " + ",".join(gem_bits) if gem_bits else ""
    buff = f"; buff {loadout.team_buff}" if loadout.team_buff else ""
    return gear + ups + minis + gem_str + buff


def cmd_tables(args: argparse.Namespace) -> int:
    webport = _webport_path(args.webport)
    tables = _load_tables(webport)
    n_gear = sum(len(v) for v in tables.gear_by_slot.values())
    print(f"gear: {n_gear} items across {len(tables.gear_by_slot)} slots")
    print(f"pets: {len(tables.pets)} (targets known for {len(tables.pet_song_targets)})")
    print(f"upgrades: {len(tables.upgrades_by_id)} types")
    for uid, up in sorted(tables.upgrades_by_id.items()):
        print(f"  upgrade {uid:>2}: {up.stats}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    tables = _load_tables(_webport_path(args.webport))
    oracle = _load_oracle(args.song)
    spec = _spec_from_args(args, oracle, tables)
    samples = generate(oracle, tables, spec, n=args.n, seed=args.seed)
    rows = list(to_json_rows(samples, str(oracle.song_file)))
    if args.out:
        Path(args.out).write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"wrote {len(rows)} samples to {args.out}")
    else:
        for row in rows:
            print(row)
    return 0


def cmd_invert(args: argparse.Namespace) -> int:
    tables = _load_tables(_webport_path(args.webport))
    oracle = _load_oracle(args.song)
    spec = _spec_from_args(args, oracle, tables)
    observed = Observables(
        score=args.score, naked_score=args.naked, gear_power=args.gear_power
    )
    t0 = time.perf_counter()
    try:
        result = invert(observed, oracle, tables, spec)
    except DomainMismatch as exc:
        print(f"DOMAIN MISMATCH: {exc}")
        return 2
    dt = time.perf_counter() - t0
    print(
        f"P-slice candidates: {result.candidates_after_p:,}  scored: "
        f"{result.candidates_scored:,}  lattice peak: {result.lattice_peak_rows:,}  "
        f"({dt:.2f}s)"
    )
    if not result.matches:
        print("no loadout in the modeled domain reproduces these observables")
        return 1
    for i, match in enumerate(result.matches):
        note = " (witness list truncated)" if match.truncated else ""
        print(f"match {i + 1}: stats {match.stats_vec}, {len(match.loadouts)} loadout(s){note}")
        for loadout in match.loadouts[: args.max_print]:
            print(f"  - {_describe_loadout(loadout)}")
        if len(match.loadouts) > args.max_print:
            print(f"  ... {len(match.loadouts) - args.max_print} more")
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    tables = _load_tables(_webport_path(args.webport))
    oracle = _load_oracle(args.song)
    spec = _spec_from_args(args, oracle, tables)
    samples = generate(oracle, tables, spec, n=args.n, seed=args.seed)
    failures = 0
    class_sizes: list[int] = []
    t0 = time.perf_counter()
    for i, sample in enumerate(samples):
        result = invert(sample.observables, oracle, tables, spec)
        recovered = contains_loadout(result, sample.loadout)
        class_sizes.append(result.witness_count)
        status = "ok" if recovered else "MISS"
        if not recovered:
            failures += 1
        print(
            f"[{i + 1:>3}/{len(samples)}] {status}  S={sample.observables.score:>10,} "
            f"P={sample.observables.gear_power:>5}  candidates={result.candidates_after_p:>7,} "
            f"witnesses={result.witness_count}"
        )
        if not recovered:
            print(f"      truth: {_describe_loadout(sample.loadout)}")
            print(f"      truth key: {canonical_form(sample.loadout)}")
    dt = time.perf_counter() - t0
    n = len(samples)
    print(
        f"\nround-trip: {n - failures}/{n} recovered; class sizes "
        f"min/med/max = {min(class_sizes)}/{sorted(class_sizes)[n // 2]}/{max(class_sizes)}; "
        f"{dt:.1f}s total ({dt / max(1, n):.2f}s/query)"
    )
    return 1 if failures else 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Production-speed acceptance: synthesize client-visible rows on the
    given chart at the given spec, invert each, report recovery + latency."""
    start_ram_watchdog(args.ram_floor)
    tables = _load_tables(_webport_path(args.webport))
    oracle = _load_oracle(args.song)
    spec = _spec_from_args(args, oracle, tables)
    samples = generate(oracle, tables, spec, n=args.n, seed=args.seed)
    print(
        f"spec={args.spec} n={args.n} "
        f"P range in samples: {min(s.observables.gear_power for s in samples)}"
        f"..{max(s.observables.gear_power for s in samples)}",
        flush=True,
    )
    latencies: list[float] = []
    class_sizes: list[int] = []
    recovered_n = 0
    cap_misses = 0
    for i, sample in enumerate(samples):
        t0 = time.perf_counter()
        try:
            result = invert(
                sample.observables,
                oracle,
                tables,
                spec,
                max_rows=args.max_lattice,
            )
        except EngineError as exc:
            dt = time.perf_counter() - t0
            cap_misses += 1
            print(f"[{i + 1:>3}/{args.n}] CAP  {dt:6.2f}s  {exc}", flush=True)
            continue
        dt = time.perf_counter() - t0
        latencies.append(dt)
        class_sizes.append(result.witness_count)
        ok = contains_loadout(result, sample.loadout)
        recovered_n += int(ok)
        print(
            f"[{i + 1:>3}/{args.n}] {'ok  ' if ok else 'MISS'} {dt:6.2f}s  "
            f"S={sample.observables.score:>11,} P={sample.observables.gear_power:>5} "
            f"cand={result.candidates_after_p:>9,} scored={result.candidates_scored:>8,} "
            f"corners={result.corner_evals:>6,} wit={result.witness_count}",
            flush=True,
        )
        if not ok:
            print(f"      truth: {_describe_loadout(sample.loadout)}")
    if cap_misses:
        print(f"cap-limited queries: {cap_misses} (loud, no answer returned)")
    if not latencies:
        print("no queries completed within caps")
        return 1
    lat = sorted(latencies)
    n = len(lat)
    ks = sorted(class_sizes)
    unique_n = sum(1 for k in ks if k == 1)
    print(
        f"\nbench: {recovered_n}/{n} recovered | latency p50={lat[n // 2]:.2f}s "
        f"p95={lat[int(n * 0.95) if int(n * 0.95) < n else n - 1]:.2f}s max={lat[-1]:.2f}s"
    )
    print(
        f"uniqueness: K=1 on {unique_n}/{n} queries; class size "
        f"p50={ks[n // 2]} max={ks[-1]} (K>1 = honest ambiguity, reported as a "
        "class -- soundness gate guarantees zero unsound witnesses)"
    )
    return 0 if recovered_n == n else 1


def cmd_identify_player(args: argparse.Namespace) -> int:
    """Identify a player's loadout by intersecting several of their rows.

    A player's loadout persists across songs; inverting one tractable row and
    forward-filtering the surviving class against their other rows collapses
    the ambiguity toward a single answer -- the primary lever for maxed rows
    (no single row need be individually fast/unique)."""
    from .identify import RowQuery, identify_player

    start_ram_watchdog(args.ram_floor)
    tables = _load_tables(_webport_path(args.webport))
    rows_data = _load_dump_rows(Path(args.dump))
    player_rows = [
        r
        for r in rows_data
        if r.get("playerName") == args.player
        and r.get("accuracy") == 1
        and int(r.get("gearPower", 0)) > 0
    ]
    if not player_rows:
        raise SystemExit(
            f"no FC rows with gearPower>0 for player {args.player!r} in {args.dump}"
        )
    # Prefer lower gear power as the seed (fewer gem fillings -> smaller class).
    player_rows.sort(key=lambda r: int(r["gearPower"]))
    player_rows = player_rows[: args.max_rows]
    print(f"player {args.player}: {len(player_rows)} FC rows (seed-first by gear power)")

    oracle_cache: dict = {}
    queries: list = []
    spec = None
    for r in player_rows:
        oracle = _resolve_row_chart(
            oracle_cache, str(r.get("title", "")), int(r["nakedScore"])
        )
        if oracle is None:
            print(f"  [skip] {r.get('title')!r}: no chart fingerprint match")
            continue
        observed = Observables(
            score=int(r["bestScore"]),
            naked_score=int(r["nakedScore"]),
            gear_power=int(r["gearPower"]),
        )
        queries.append(RowQuery(oracle=oracle, observed=observed, label=str(r.get("title", ""))))
        if spec is None:
            spec = _spec_from_args(args, oracle, tables)
    if not queries:
        print("no rows resolved to local charts; cannot identify")
        return 1

    t0 = time.perf_counter()
    result = identify_player(queries, tables, spec, max_rows=args.max_lattice)
    dt = time.perf_counter() - t0
    print(f"\nidentification: {dt:.1f}s  seed={result.seed_label}")
    print("  class-size trace: " + " -> ".join(
        f"{lbl}:{k}" for lbl, k in result.class_size_trace
    ))
    for lbl, why in result.rows_skipped:
        print(f"  [skipped] {lbl}: {why}")
    if not result.loadouts:
        print("  NO CONSISTENT LOADOUT across rows (seed capped, drift, or "
              "cross-row inconsistency -- see skips)")
        return 1
    print(
        f"  RESULT: {result.class_size} loadout(s) consistent with "
        f"{len(result.rows_used)} rows"
        + ("  <-- UNIQUELY IDENTIFIED" if result.identified else "")
    )
    for lo in result.loadouts[: args.max_print]:
        print(f"  - {_describe_loadout(lo)}")
    return 0


def _load_dump_rows(dump_path: Path) -> list[dict]:
    with open(dump_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"no rows in dump {dump_path}")
    return rows


def _resolve_row_chart(oracle_cache: dict, title: str, naked: int) -> SongOracle | None:
    """Find the chart whose all-Perfect naked score equals the row's
    nakedScore -- an exact chart-and-version fingerprint. Charts are located
    by title substring across all difficulty folders."""
    from gear_optimizer.data.song_io import scan_song_header

    query = title.strip().lower()
    for diff in ("Easy", "Normal", "Hard"):
        root = REPO_ROOT / "Data" / diff
        if not root.is_dir():
            continue
        for fp in sorted(root.glob("*.txt")):
            header = scan_song_header(str(fp)) or {}
            song_name = str(header.get("Song Name", "") or "")
            if query not in song_name.lower():
                continue
            key = str(fp)
            if key not in oracle_cache:
                try:
                    oracle_cache[key] = SongOracle(fp)
                except Exception as exc:  # chart load is an external boundary
                    print(f"  [skip] {fp.name}: {exc}")
                    oracle_cache[key] = None
                    continue
            oracle = oracle_cache[key]
            if oracle is None:
                continue
            if oracle.naked_score() == naked:
                print(f"  fingerprint match: {fp.name} (naked={naked:,})")
                return oracle
            # A BELOW-ceiling naked score on a true-FC row is the coupled
            # press-timing signature (user-confirmed 2026-07-17): the play's
            # presses are timed against the COMPOSITE fever bar, and the
            # naked score object replays those same presses on the NAKED
            # fever bar, landing under the naked all-Perfect ceiling. The
            # oracle models independent per-bar maxima, so these rows are
            # refused (never guessed) until the coupled two-bar frontier
            # ships.
            delta = naked - oracle.naked_score()
            hint = (
                " (below ceiling: coupled naked-fever timing play -- needs "
                "the two-bar frontier)"
                if delta < 0
                else " (ABOVE ceiling: wrong chart or version drift)"
            )
            print(
                f"  [no-fingerprint] {fp.name}: chart naked={oracle.naked_score():,} "
                f"!= row naked={naked:,} [{delta:+,}]{hint}"
            )
    return None


def _analyze_non_fc_row(oracle_cache: dict, row: dict) -> None:
    """Non-FC rows (accuracy < 1): recover the exact feasible judgment-count
    multisets (layer 1). The note-level sequence DP is the pending layer, so
    no loadout inversion is attempted -- never a guessed answer."""
    from gear_optimizer.data.song_io import scan_song_header

    from .judgments import feasible_judgment_counts

    title = str(row.get("title", "")).strip().lower()
    charts: list[Path] = []
    for diff in ("Easy", "Normal", "Hard"):
        root = REPO_ROOT / "Data" / diff
        if not root.is_dir():
            continue
        for fp in sorted(root.glob("*.txt")):
            header = scan_song_header(str(fp)) or {}
            if title in str(header.get("Song Name", "") or "").lower():
                charts.append(fp)
    if not charts:
        print("  non-FC: no chart candidates found by title")
        return
    for fp in charts[:3]:
        key = str(fp)
        if key not in oracle_cache:
            try:
                oracle_cache[key] = SongOracle(fp)
            except Exception as exc:
                print(f"  [skip] {fp.name}: {exc}")
                oracle_cache[key] = None
                continue
        oracle = oracle_cache[key]
        if oracle is None:
            continue
        counts = feasible_judgment_counts(float(row["accuracy"]), oracle.hit_count)
        shown = ", ".join(
            f"(P{c.perfect}/G{c.great}/O{c.okay}/M{c.miss})" for c in counts[:6]
        )
        more = f" +{len(counts) - 6} more" if len(counts) > 6 else ""
        print(
            f"  non-FC vs {fp.name} ({oracle.hit_count} events): "
            f"{len(counts)} feasible judgment multiset(s): {shown}{more}"
        )
    print(
        "  loadout inversion for non-FC rows awaits the sequence layer "
        "(exact-N judgment-placement DP); counts above are exact and complete"
    )


def cmd_invert_row(args: argparse.Namespace) -> int:
    """Invert real leaderboard rows (the exact client-visible fields)."""
    start_ram_watchdog(args.ram_floor)
    tables = _load_tables(_webport_path(args.webport))
    rows = _load_dump_rows(Path(args.dump))
    query = args.title.strip().lower()
    picked = [
        r
        for r in rows
        if query in str(r.get("title", "")).lower()
        and int(r.get("gearPower", 0)) > 0
    ]
    if args.player:
        picked = [r for r in picked if r.get("playerName") == args.player]
    if not picked:
        raise SystemExit(
            "no dump rows match (need gearPower>0; "
            f"title~{args.title!r}"
            + (f", player={args.player!r})" if args.player else ")")
        )
    picked = picked[: args.max_rows]
    oracle_cache: dict = {}
    exit_code = 0
    for row in picked:
        print(
            f"\nrow: {row.get('title')!r} player={row.get('playerName')} "
            f"S={row['bestScore']:,} N={row['nakedScore']:,} P={row['gearPower']} "
            f"acc={row.get('accuracy')}"
        )
        if row.get("accuracy") != 1:
            _analyze_non_fc_row(oracle_cache, row)
            continue
        oracle = _resolve_row_chart(oracle_cache, str(row.get("title", "")), int(row["nakedScore"]))
        if oracle is None:
            print(
                "  NO CHART FINGERPRINT MATCH -- wrong chart title mapping or "
                "game-version drift (chart/scoring changed since this play)"
            )
            exit_code = 2
            continue
        spec = _spec_from_args(args, oracle, tables)
        observed = Observables(
            score=int(row["bestScore"]),
            naked_score=int(row["nakedScore"]),
            gear_power=int(row["gearPower"]),
        )
        t0 = time.perf_counter()
        try:
            result, rung_spec, trace = invert_progressive(
                observed,
                oracle,
                tables,
                spec,
                max_rows=args.max_lattice,
            )
        except DomainMismatch as exc:
            print(f"  DOMAIN MISMATCH: {exc}")
            exit_code = 2
            continue
        except EngineError as exc:
            print(f"  CAP: {exc}")
            exit_code = max(exit_code, 1)
            continue
        dt = time.perf_counter() - t0
        ladder = " -> ".join(f"gems>={fl}:{note.split(':')[0]}" for fl, note in trace)
        print(
            f"  {dt:.2f}s  candidates={result.candidates_after_p:,} "
            f"scored={result.candidates_scored:,} corners={result.corner_evals:,} "
            f"witnesses={result.witness_count}"
        )
        print(f"  ladder: {ladder}")
        if not result.matches:
            print(
                "  NO PREIMAGE in the modeled domain -- the player's build "
                "exceeds a spec cap or uses drifted/unmodeled items"
            )
            exit_code = max(exit_code, 1)
        elif rung_spec.gem_min_per_type > 0:
            print(
                f"  class is complete WITHIN gems>={rung_spec.gem_min_per_type}"
                "/type; lower-gem preimages were not searched (confirm across "
                "the player's rows via identify-player)"
            )
        for match in result.matches:
            for loadout in match.loadouts[: args.max_print]:
                print(f"  - {_describe_loadout(loadout)}")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reverse_score", description=__doc__)
    parser.add_argument("--webport", help="path to the [REDACTED PRIVATE REPOSITORY] checkout")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("tables", help="extract and summarize domain tables")
    p.set_defaults(fn=cmd_tables)

    p = sub.add_parser("generate", help="generate synthetic labeled samples")
    p.add_argument("--song", required=True)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out")
    p.add_argument("--spec", default="small")
    p.set_defaults(fn=cmd_generate)

    p = sub.add_parser("invert", help="reverse-lookup observables to loadouts")
    p.add_argument("--song", required=True)
    p.add_argument("--score", type=int, required=True)
    p.add_argument("--naked", type=int, required=True)
    p.add_argument("--gear-power", type=int, required=True)
    p.add_argument("--spec", default="small")
    p.add_argument("--max-print", type=int, default=10)
    p.set_defaults(fn=cmd_invert)

    p = sub.add_parser("roundtrip", help="synthetic round-trip acceptance run")
    p.add_argument("--song", required=True)
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--spec", default="small")
    p.set_defaults(fn=cmd_roundtrip)

    p = sub.add_parser("bench", help="production-speed synthetic benchmark")
    p.add_argument("--song", required=True)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--spec", default="production")
    p.add_argument("--ram-floor", type=float, default=6.0)
    p.add_argument("--mini-levels", help="comma list, e.g. 1,20,30,40,50")
    p.add_argument("--upgrade-cap", type=int)
    p.add_argument("--gem-cap", type=int)
    p.add_argument("--archetype", choices=("light", "mid", "stacked"),
                   help="force synthetic build archetype (stacked = maxed, tail-P)")
    p.add_argument("--max-lattice", type=int, default=5_000_000,
                   help="retained-row cap; chunked int32 keeps RAM ~40B/row")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("invert-row", help="invert real leaderboard dump rows")
    p.add_argument("--dump", default=str(REPO_ROOT / "robeats_top1_song_leaderboards.json"))
    p.add_argument("--title", required=True)
    p.add_argument("--player")
    p.add_argument("--spec", default="production")
    p.add_argument("--max-rows", type=int, default=3)
    p.add_argument("--max-print", type=int, default=5)
    p.add_argument("--ram-floor", type=float, default=6.0)
    p.add_argument("--mini-levels", help="comma list, e.g. 1,20,30,40,50")
    p.add_argument("--upgrade-cap", type=int)
    p.add_argument("--gem-cap", type=int)
    p.add_argument("--max-lattice", type=int, default=5_000_000)
    p.set_defaults(fn=cmd_invert_row)

    p = sub.add_parser("identify-player", help="intersect a player's rows to their loadout")
    p.add_argument("--dump", default=str(REPO_ROOT / "robeats_top1_song_leaderboards.json"))
    p.add_argument("--player", required=True)
    p.add_argument("--spec", default="production")
    p.add_argument("--max-rows", type=int, default=8)
    p.add_argument("--max-print", type=int, default=10)
    p.add_argument("--max-lattice", type=int, default=5_000_000)
    p.add_argument("--ram-floor", type=float, default=6.0)
    p.add_argument("--mini-levels", help="comma list, e.g. 1,20,30,40,50")
    p.add_argument("--upgrade-cap", type=int)
    p.add_argument("--gem-cap", type=int)
    p.set_defaults(fn=cmd_identify_player)

    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
