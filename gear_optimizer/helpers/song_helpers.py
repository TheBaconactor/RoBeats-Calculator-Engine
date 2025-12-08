"""
Song processing helper functions.

Extracted from song_processor.py to reduce monolithic function size.
Contains functions for:
- Database context loading
- Song configuration setup
- Loadout entry building
- Force greats processing
- Database payload construction
- Persistence entry building
- Results printing
"""
import json

from ..database import (
    get_db_connection,
    get_best_loadouts,
    get_loadout_hash,
    LOADOUTS_PER_SONG_LIMIT,
)
from ..models import WarnOnce, GASettings
from ..csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats
from ..scoring import apply_force_greats_to_result
from ..utils import stats_signature

# Global warn-once instance
WARN_ONCE = WarnOnce()


def load_database_context(found_song_name, use_evo_db, gears_by_name, minis_by_name):
    """
    Load database seeds and known loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (prev_record, known_loadouts)
    """
    db_seed = None
    prev_record = None
    known_loadouts = {}

    if use_evo_db:
        # Load previous best for seeding
        best_loadouts = get_best_loadouts(
            found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name
        )
        if best_loadouts:
            prev_record = best_loadouts[0]
            db_seed = prev_record

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")

        # Fetch known loadouts for persistent caching
        try:
            conn = get_db_connection()
            cursor = conn.execute(
                """SELECT loadout_hash, score, fg_score, force_details_json
                   FROM loadouts
                   WHERE song_name = ?
                   ORDER BY score DESC
                   LIMIT ?""",
                (found_song_name, LOADOUTS_PER_SONG_LIMIT),
            )
            for row in cursor:
                force_blob = row["force_details_json"]
                force_data = None
                if force_blob:
                    try:
                        force_data = json.loads(force_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "force-loadout-json",
                            f"Invalid force JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        force_data = None
                known_loadouts[row["loadout_hash"]] = (
                    row["score"],
                    row["fg_score"],
                    force_data,
                )
            # Memory leak fix #2: Checkpoint WAL before closing connection
            # Prevents WAL file growth (5-50 MB per 1000 songs)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.execute("PRAGMA optimize")
            except Exception as e:
                # CRITICAL FIX: Log checkpoint failures (was silently suppressed)
                import logging
                logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
            conn.close()
        except Exception as e:
            print(f"[DB] Error fetching known loadouts: {e}")

    return prev_record, known_loadouts


def setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name):
    """
    Setup configuration, auto-buff, load current stats.

    Args:
        cfg: Configuration object
        calc_song: Song calculation data
        auto_buff: Whether to enable auto buff
        paths: Path configuration
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (ga_settings, fixed_stats, current_gear_stats, current_gear_list,
                current_mini_stats, current_mini_list, meta_finder, enable_fever,
                enable_mini, enable_gear, force_greats_mode, force_greats_finder,
                manual_force_greats)
    """
    ga_settings = GASettings.from_cfg(cfg)

    # MetaFinder controls all optimizers collectively.
    meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
    enable_fever = enable_mini = enable_gear = bool(meta_finder)

    force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
    force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
    # ForceGreatsMode must be enabled for ForceGreatsFinder to work
    if not force_greats_mode:
        force_greats_finder = False

    # Import here to avoid circular dependency
    from ..config import load_force_greats_config
    force_greats_config = load_force_greats_config(cfg)
    manual_force_greats = force_greats_mode and any(force_greats_config)

    # --- Auto Select Buff & Color Logic ---
    if auto_buff:
        p_col = calc_song["metadata"].get("Primary Color", "Rush")
        if not cfg.has_section("TeamContributionBuffConstant"):
            cfg.add_section("TeamContributionBuffConstant")
        cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
        cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
        print(f"[Auto-Config] Set Team Buff: T5 | Team Color: {p_col}")

    fixed_stats = get_fixed_stats(cfg)

    # Load Current Config for Seeding / Fallback
    current_gear_stats, current_gear_list = get_config_gear_stats(
        cfg, paths, gears_by_name
    )
    current_mini_stats, current_mini_list = get_config_mini_stats(
        cfg, paths, minis_by_name
    )

    return (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    )


def build_loadout_entries(
    found_song_name,
    use_evo_db,
    ga_candidates,
    db_loadouts_limit,
    gears_by_name,
    minis_by_name,
    build_details_fn,
):
    """
    Build union of DB + GA loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        ga_candidates: List of GA candidate loadouts
        db_loadouts_limit: Maximum number of DB loadouts to fetch
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name
        build_details_fn: Function to build details dict from data dict

    Returns:
        dict: Dictionary of loadout entries by hash
    """
    loadout_entries = {}

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    def _add_entry(gear_items, mini_items, score_val, details_obj, fg_score_val=0, force_obj=None, eval_data=None):
        h = get_loadout_hash(gear_items, mini_items)
        existing = loadout_entries.get(h)
        # Prefer the entry with actual eval_data (from GA) over DB-only details
        if existing:
            if existing.get("eval_data") is None and eval_data is not None:
                pass
            elif existing.get("score", 0) >= (score_val or 0):
                return
        loadout_entries[h] = {
            "gear": gear_items,
            "minis": mini_items,
            "score": score_val or 0,
            "details": details_obj or {},
            "fg_score": fg_score_val or 0,
            "force": force_obj,
            "eval_data": eval_data,
        }

    # DB loadouts (up to the configured limit) for this song
    db_loadouts_full = []
    if use_evo_db:
        try:
            db_loadouts_full = get_best_loadouts(
                found_song_name, limit=db_loadouts_limit, gears_by_name=gears_by_name, minis_by_name=minis_by_name
            )
        except Exception:
            db_loadouts_full = []
    for rec in db_loadouts_full or []:
        _add_entry(
            rec.get("gear", []),
            rec.get("minis", []),
            rec.get("score", 0),
            rec.get("details", {}),
            rec.get("fg_score", 0),
            rec.get("force"),
            None,
        )

    # Current GA evaluated loadouts (only add if not already present)
    for eval_result in ga_candidates:
        eval_data = eval_result.get("Data")
        eval_score = eval_result.get("Score", 0)
        gear_items = eval_result.get("Gear", [])
        mini_items = eval_result.get("Minis", [])
        eval_details = build_details_fn(eval_data) if eval_data else {}
        _add_entry(
            gear_items,
            mini_items,
            eval_score,
            eval_details,
            0,
            None,
            eval_data,
        )

    return loadout_entries


def process_force_greats(
    loadout_entries,
    manual_force_greats,
    force_greats_finder,
    force_greats_config,
    calc_song,
    ref_arrays,
    meta_primary_color,
    build_details_fn,
    db_loadouts_full_count,
):
    """
    Apply force greats to loadouts.

    Args:
        loadout_entries: Dictionary of loadout entries
        manual_force_greats: Whether manual force greats is enabled
        force_greats_finder: Whether force greats finder is enabled
        force_greats_config: Force greats configuration
        calc_song: Song calculation data
        ref_arrays: Reference arrays for calculation
        meta_primary_color: Primary color from metadata
        build_details_fn: Function to build details dict from data dict
        db_loadouts_full_count: Number of DB loadouts (for budget)

    Returns:
        list: List of force greats variants
    """
    fg_variants = []

    manual_counts = (
        force_greats_config if (manual_force_greats and not force_greats_finder) else []
    )

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    # FG processing budget: number of DB loadouts (dynamic). Skip (reuse) does NOT consume budget.
    unique_stats_seen = set()
    max_fg_compute = db_loadouts_full_count if db_loadouts_full_count else len(loadout_entries)
    computed = 0
    print(f"[ForceGreats] Processing {len(loadout_entries)} unique loadouts (DB + GA)...")
    for entry in loadout_entries.values():
        if computed >= max_fg_compute:
            break

        cached_force = entry.get("force")
        if cached_force and (cached_force.get("score") or entry.get("fg_score")):
            fg_variants.append({
                "data": cached_force.get("details", {}),
                "gear": entry.get("gear", []),
                "minis": entry.get("minis", []),
                "score": cached_force.get("score", entry.get("fg_score", 0)),
            })
            # Skipped entries do not consume compute budget
            continue

        eval_data = entry.get("eval_data")
        if not eval_data:
            det = entry.get("details") or {}
            stats = det.get("Stats") or {}
            if not stats:
                continue
            eval_data = {
                "Stats": stats,
                "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                "FT": det.get("FT", 0),
                "FF": det.get("FF", 0),
                "GemCounts": det.get("GemCounts", {}),
            }

        stats = eval_data.get("Stats", {})
        sel_color = eval_data.get("Selected Element", meta_primary_color)
        sig = stats_signature(stats, calc_song, sel_color)
        unique_stats_seen.add(sig)

        fg_variant = apply_force_greats_to_result(
            eval_data,
            calc_song,
            ref_arrays,
            manual_counts=manual_counts,
            use_finder=force_greats_finder,
        )
        computed += 1
        if fg_variant:
            fg_variants.append({
                "data": fg_variant,
                "gear": entry.get("gear", []),
                "minis": entry.get("minis", []),
                "score": fg_variant.get("Score", 0),
            })
            entry["force"] = {
                "score": fg_variant.get("Score", 0),
                "gear": _names_list(entry.get("gear", [])),
                "minis": _names_list(entry.get("minis", [])),
                "details": build_details_fn(fg_variant),
            }
            entry["fg_score"] = fg_variant.get("Score", 0)
    print(f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed}, budget {max_fg_compute})")

    return fg_variants


def build_db_payload(
    best_data,
    best_gear,
    best_minis,
    prev_record,
    attempt_lifetime,
    prev_attempts_first,
    fg_variants,
    build_details_fn,
):
    """
    Build database persistence payload.

    Args:
        best_data: Best optimization data
        best_gear: Best gear loadout
        best_minis: Best mini loadout
        prev_record: Previous database record
        attempt_lifetime: Lifetime attempt counter
        prev_attempts_first: Previous attempts_first counter
        fg_variants: Force greats variants
        build_details_fn: Function to build details dict from data dict

    Returns:
        dict: Database payload
    """
    score = best_data.get("Score", 0)

    prev_score = prev_record.get("score") if prev_record else None
    is_first = prev_record is None
    is_better = (prev_score is None) or (score > prev_score)

    def extract_names(record):
        """Extract names from record, handling both dict and string formats."""
        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        gear_items = record.get("gear") if record else []
        minis_items = record.get("minis") if record else []
        loadout = record.get("loadout") if record else None
        if (not gear_items and not minis_items) and loadout:
            gear_items = loadout[:6]
            minis_items = loadout[6:9]

        gear_names = [get_name(g) for g in (gear_items or [])]
        minis_names = [get_name(m) for m in (minis_items or [])]
        return gear_names, minis_names

    best_gear_names = [g.get("Name") for g in best_gear]
    best_mini_names = [m.get("Name") for m in best_minis]
    best_details = build_details_fn(best_data)

    attempts_first = (
        1
        if is_first or is_better
        else (prev_attempts_first + 1 if prev_attempts_first else 1)
    )

    def attach_attempt_meta(details):
        """Copy details dict and tag attempt counters for DB persistence."""
        merged = dict(details or {})
        merged["attempt_lifetime"] = attempt_lifetime
        merged["attempts_first"] = attempts_first
        return merged

    # Build FG candidates from CURRENT RUN ONLY (not prev_record)
    # We always save the best FG from this run, regardless of whether it beats the old one.
    current_run_fg_candidates = []
    for fg_entry in fg_variants:
        fg_gear = fg_entry.get("gear", [])
        fg_minis = fg_entry.get("minis", [])
        fg_data = fg_entry.get("data", {})
        fg_gear_names = [g.get("Name") for g in fg_gear] if fg_gear else []
        fg_mini_names = [m.get("Name") for m in fg_minis] if fg_minis else []
        current_run_fg_candidates.append(
            {
                "score": fg_entry.get("score", 0),
                "gear": fg_gear_names,
                "minis": fg_mini_names,
                "details": build_details_fn(fg_data),
            }
        )

    if is_first:
        print(
            " >> NEW RECORD! (First entry for this song/context). "
            "Saving to Evolution Database..."
        )
    elif is_better:
        print(
            f" >> NEW RECORD! Previous: {prev_score} | New: {score} "
            f"- Updating Evolution Database..."
        )
    else:
        print(f" >> No improvement over DB Record ({prev_score})")

    # Aggregate candidates (best + second from previous DB and current run) and pick top two.
    candidates = []

    if prev_record and prev_score is not None:
        prev_gear_names, prev_mini_names = extract_names(prev_record)
        candidates.append(
            {
                "score": prev_score,
                "gear": prev_gear_names,
                "minis": prev_mini_names,
                "details": attach_attempt_meta(prev_record.get("details", {})),
            }
        )

    candidates.append(
        {
            "score": score,
            "gear": best_gear_names,
            "minis": best_mini_names,
            "details": attach_attempt_meta(best_details),
        }
    )

    candidates = sorted(
        candidates, key=lambda c: c.get("score", -1), reverse=True
    )

    def _sig(cand):
        gear_key = tuple(cand.get("gear") or [])
        minis_key = tuple(cand.get("minis") or [])
        details = cand.get("details") or {}
        try:
            details_key = json.dumps(details, sort_keys=True)
        except Exception:
            details_key = str(details)
        return (gear_key, minis_key, details_key)

    top1 = candidates[0] if candidates else None

    updated_payload = {}
    updated_payload["attempt_lifetime"] = attempt_lifetime
    updated_payload["attempts_first"] = attempts_first
    if top1:
        updated_payload.update(
            {
                "score": top1["score"],
                "gear": top1.get("gear", []),
                "minis": top1.get("minis", []),
                "details": attach_attempt_meta(top1.get("details", {})),
            }
        )

    updated_payload.pop("second", None)

    # Always save the best FG from the CURRENT RUN
    # This ensures we always record the FG result from this GA's evaluated loadouts,
    # even if it doesn't beat the previous best FG score.
    if current_run_fg_candidates:
        current_run_fg_candidates = sorted(
            current_run_fg_candidates, key=lambda c: c.get("score", -1), reverse=True
        )
        best_force = current_run_fg_candidates[0]
        fg_score_val = best_force.get("score", 0) or 0
        updated_payload["force"] = {
            "score": best_force.get("score"),
            "gear": best_force.get("gear", []),
            "minis": best_force.get("minis", []),
            "details": best_force.get("details", {}),
        }
    # If no FG candidates from current run, keep the old one from prev_record (if any)
    elif prev_record and prev_record.get("force"):
        updated_payload["force"] = prev_record.get("force")
        fg_score_val = (prev_record.get("force") or {}).get("score", 0) or 0
    else:
        updated_payload.pop("force", None)
        fg_score_val = 0

    updated_payload["fg_score"] = fg_score_val

    return updated_payload


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
):
    """
    Build all persistence entries.

    Args:
        db_payload: Database payload
        ga_candidates: List of GA candidate loadouts
        loadout_entries: Dictionary of loadout entries (or None)
        build_details_fn: Function to build details dict from data dict

    Returns:
        list: List of persistence entries
    """
    persist_entries = []

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    def _append_entry(score_val, gear_items, mini_items, details_obj, fg_score_val=0, force_obj=None):
        # Extract attempt metadata from details for tagging
        attempt_lifetime = details_obj.get("attempt_lifetime", 0) if details_obj else 0
        attempts_first = details_obj.get("attempts_first", 0) if details_obj else 0

        # Tag attempts metadata so downstream displays (Best/Lifetime) can advance.
        details_with_meta = dict(details_obj or {})
        details_with_meta["attempt_lifetime"] = attempt_lifetime
        details_with_meta["attempts_first"] = attempts_first

        persist_entries.append({
            "score": score_val or 0,
            "fg_score": fg_score_val or 0,
            "gear": _names_list(gear_items),
            "minis": _names_list(mini_items),
            "details": details_with_meta,
            "force": force_obj,
        })

    # Top 1 (base)
    _append_entry(
        db_payload.get("score", 0),
        db_payload.get("gear", []),
        db_payload.get("minis", []),
        db_payload.get("details", {}),
        db_payload.get("fg_score", 0),
        db_payload.get("force"),
    )

    # Top 1 FG (store as its own row)
    force_block = db_payload.get("force")
    if force_block:
        _append_entry(
            force_block.get("score", 0),
            force_block.get("gear", []),
            force_block.get("minis", []),
            force_block.get("details", {}),
            force_block.get("score", 0),
            force_block,
        )

    # GA candidates (capped to DB limit)
    if ga_candidates:
        for eval_result in ga_candidates:
            eval_data = eval_result.get("Data") or {}
            eval_score = eval_result.get("Score", 0)
            eval_gear = eval_result.get("Gear", [])
            eval_minis = eval_result.get("Minis", [])
            eval_details = build_details_fn(eval_data)
            _append_entry(
                eval_score,
                eval_gear,
                eval_minis,
                eval_details,
                0,
                None,
            )

    # Include DB+GA union entries (with updated FG) if available
    if loadout_entries is not None:
        for entry in loadout_entries.values():
            _append_entry(
                entry.get("score", 0),
                entry.get("gear", []),
                entry.get("minis", []),
                entry.get("details", {}),
                entry.get("fg_score", 0),
                entry.get("force"),
            )

    return persist_entries


def print_results(
    found_song_name,
    best_data,
    best_gear,
    best_minis,
    current_gear_list,
    current_mini_list,
    enable_gear,
    enable_mini,
    fg_variants,
    status_emit_fn,
):
    """
    Print final results.

    Args:
        found_song_name: Name of the song
        best_data: Best optimization data
        best_gear: Best gear loadout
        best_minis: Best mini loadout
        current_gear_list: Current gear list (if gear not optimized)
        current_mini_list: Current mini list (if minis not optimized)
        enable_gear: Whether gear optimization is enabled
        enable_mini: Whether mini optimization is enabled
        fg_variants: Force greats variants
        status_emit_fn: Function to emit status messages

    Returns:
        None
    """
    score = best_data.get("Score", 0)
    print("-" * 30)
    print(f"FINAL CONFIGURATION FOR: {found_song_name}")
    print(f"Total Score: {score}")

    status_emit_fn(f"DONE | Score={score}")

    if enable_gear:
        print("\n[Best Gear Loadout]")
        for g in best_gear:
            print(f"{g.get('type')}: {g.get('Name')}")
    else:
        print("\n[Gear Loadout (Fixed)]")
        for g in current_gear_list:
            print(f"{g.get('type')}: {g.get('Name')}")

    if enable_mini:
        print("\n[Best Mini Team]")
        for m in best_minis:
            print(f"{m.get('Name', 'Unknown')}")
    else:
        print("\n[Mini Team (Fixed)]")
        for m in current_mini_list:
            print(f"{m.get('Name', 'Unknown')}")

    if "GemCounts" in best_data:
        gem_counts = best_data["GemCounts"]
        sel_el = best_data.get("Selected Element", "Rush")
        print(f"\nGem Allocation -> Fever Time: {best_data.get('FT', 0)}")
        print(f"Gem Allocation -> Fever Fill: {best_data.get('FF', 0)}")
        print(
            "Gem Allocation -> Fever Multiplier: "
            f"{gem_counts.get('Fever Multiplier', 0)}"
        )
        print(
            "Gem Allocation -> Combo Multiplier: "
            f"{gem_counts.get('Combo Multiplier', 0)}"
        )
        print(
            "Gem Allocation -> Perfect Points: "
            f"{gem_counts.get('Perfect Points', 0)}"
        )
        print(
            f"Gem Allocation -> {sel_el} (Overflow): "
            f"{gem_counts.get('Element Overflow', 0)}"
        )

    if fg_variants:
        best_fg_entry = max(
            fg_variants, key=lambda p: p.get("score", -1)
        )
        best_fg_variant = best_fg_entry.get("data", {})
        fg_meta = best_fg_variant.get("ForceGreats", {}) or {}
        best_fg_gear = best_fg_entry.get("gear", [])
        best_fg_minis = best_fg_entry.get("minis", [])
        fg_gear_names = [g.get("Name") for g in best_fg_gear] if best_fg_gear else []
        fg_mini_names = [m.get("Name") for m in best_fg_minis] if best_fg_minis else []
        print("\n[ForceGreats Optimizer]")
        print(
            f"Base Score: {fg_meta.get('base_score', best_data.get('Score', 0))} | "
            f"ForceGreat Score: {best_fg_entry.get('score', 0)}"
        )
        print(f"Best FG Gear: {fg_gear_names}")
        print(f"Best FG Minis: {fg_mini_names}")
        cfg_map = fg_meta.get("config", {})
        if cfg_map:
            print(f"Config: {cfg_map}")
