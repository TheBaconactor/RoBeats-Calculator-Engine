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
import time

from ..data.database import (
    get_db_connection,
    get_best_loadouts,
    get_evolution_db_path,
    get_loadout_hash,
    LOADOUTS_PER_SONG_LIMIT,
)
from ..data.models import WarnOnce, GASettings
from ..data.csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats
from ..solver.scoring import apply_force_greats_to_result
from ..core.utils import stats_signature

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
        # Always print DB path + exact lookup key to make seeding issues obvious.
        # (repr shows hidden whitespace / mismatched suffixes that would otherwise be invisible.)
        try:
            print(f"[DB] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
        except Exception:
            print(f"[DB] Using DB: (unknown) | lookup key: {found_song_name!r}")

        # Load previous best for seeding
        best_loadouts = get_best_loadouts(
            found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name
        )
        if best_loadouts:
            prev_record = best_loadouts[0]
            db_seed = prev_record

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")
        else:
            # If we expected a DB seed but didn't find one, show nearby candidates.
            # This catches cases where the song key differs by suffix/spacing.
            try:
                conn = get_db_connection()
                rows = conn.execute(
                    "SELECT DISTINCT song_name FROM loadouts WHERE song_name LIKE ? LIMIT 8",
                    (f"%{found_song_name.split('(')[0].strip()}%",),
                ).fetchall()
                conn.close()
                if rows:
                    print("[DB] No exact seed found. Similar keys in DB:")
                    for r in rows:
                        # sqlite3.Row supports index access in this connection setup
                        print(f"  - {str(r[0])!r}")
            except Exception:
                pass

        # Fetch known loadouts for persistent caching
        try:
            conn = get_db_connection()
            cursor = conn.execute(
                """SELECT loadout_hash, score, fg_score, force_details_json, details_json
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
                
                details_blob = row["details_json"]
                details_data = None
                if details_blob:
                    try:
                        details_data = json.loads(details_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "details-loadout-json",
                            f"Invalid details JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        details_data = None

                known_loadouts[row["loadout_hash"]] = (
                    row["score"],
                    row["fg_score"],
                    force_data,
                    details_data,
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
    from ..core.config import load_force_greats_config
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
        # Use BaseScore (true base score) for persistence, not Score (heuristic)
        eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
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
    use_gpu: bool = False,
    perf_timing: bool = False,
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
        perf_timing: If True, prints a detailed breakdown of FG grouping/caching/GPU calls.

    Returns:
        list: List of force greats variants
    """
    fg_variants = []
    perf = bool(perf_timing)

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

    # ------------------------------------------------------------------
    # GPU Finder Fast Path:
    # When ForceGreatsFinder is enabled and GPU mode is on, batch/dedupe
    # across loadouts and run the full FG finder on the GPU.
    # ------------------------------------------------------------------
    if use_gpu and force_greats_finder:
        try:
            from ..core.constants import (
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_GEM_BUDGET,
            )
            from ..solver.scoring import _extract_base_stats, fg_baseline_params, FG_CACHE, _force_greats_counts_to_dict
            from ..solver.taichi_gem_solver import solve_force_greats_finder_gpu

            meta = calc_song.get("metadata", {}) or {}
            p_color = meta.get("Primary Color", "")
            s_color = meta.get("Secondary Color", "")

            # Helper: apply gem allocations to base stats to produce a final Stats dict
            def _apply_gems_to_base(base: dict, sel_color: str, ft: int, ff: int, gem_counts: dict) -> dict:
                out = dict(base or {})
                g_pp = int((gem_counts or {}).get("Perfect Points", 0))
                g_cm = int((gem_counts or {}).get("Combo Multiplier", 0))
                g_fm = int((gem_counts or {}).get("Fever Multiplier", 0))
                g_ov = int((gem_counts or {}).get("Element Overflow", 0))

                out["Perfect Points"] = out.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
                out["Combo Multiplier"] = out.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
                out["Fever Multiplier"] = out.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
                out["Fever Time"] = out.get("Fever Time", 0) + int(ft) * GEM_SCALE_FEVER
                out["Fever Fill Rate"] = out.get("Fever Fill Rate", 0) + int(ff) * GEM_SCALE_FEVER

                # Stat-to-element contributions
                out["Chill"] = out.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
                out["Flow"] = out.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
                out["Rush"] = out.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
                out["Beat"] = out.get("Beat", 0) + int(ft) * GEM_STAT_TO_ELEMENT_SCALE
                out["Vibe"] = out.get("Vibe", 0) + int(ff) * GEM_STAT_TO_ELEMENT_SCALE

                # Overflow gems
                if sel_color:
                    out[sel_color] = out.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
                return out

            def _is_cached_force_valid_for_finder(cached_force_obj, expected_selected_element, center_ft, center_ff):
                if not isinstance(cached_force_obj, dict):
                    return False
                details = cached_force_obj.get("details") or {}
                if not isinstance(details, dict):
                    return False
                fg_meta = details.get("ForceGreats") or {}
                if not isinstance(fg_meta, dict):
                    return False
                algo_ver = fg_meta.get("algo_version")
                if int(algo_ver or 0) != 3:
                    return False
                if not fg_meta.get("finder") or not fg_meta.get("gpu"):
                    return False
                cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
                if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                    return False
                # Require same FT/FF center to ensure same search window assumptions
                try:
                    if int(fg_meta.get("center_ft", -999)) != int(center_ft):
                        return False
                    if int(fg_meta.get("center_ff", -999)) != int(center_ff):
                        return False
                except Exception:
                    return False
                return True

            # Group work by (selected_element, n_sections, max_per_section)
            groups = {}
            group_centers = {} # key -> set of (center_ft, center_ff)
            group_items = []

            # PERF counters (opt-in; enabled via caller)
            t_collect_sec = 0.0
            t_cfg_build_sec = 0.0
            t_gpu_calls_sec = 0.0
            t_cache_check_sec = 0.0
            t_genome_build_sec = 0.0
            t_result_apply_sec = 0.0
            n_gpu_calls = 0
            fg_cache_hits = 0
            fg_cache_misses = 0
            db_cached_reuse = 0
            no_eval_skips = 0
            gpu_call_shapes = []  # sample a few: (n_genomes, n_cfg, n_ftff, n_sections)

            # Collect candidates up to compute budget
            _t_collect0 = time.perf_counter() if perf else 0.0
            for entry in loadout_entries.values():
                if computed >= max_fg_compute:
                    break

                cached_force = entry.get("force")
                expected_sel = None
                try:
                    det0 = entry.get("details") or {}
                    expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
                except Exception:
                    expected_sel = meta_primary_color

                # Keep legacy cache reuse behavior for non-finder only. Finder recomputes for correctness.
                if (
                    cached_force
                    and (cached_force.get("score") or entry.get("fg_score"))
                    and (not force_greats_finder)
                ):
                    fg_variants.append({
                        "data": cached_force.get("details", {}),
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": cached_force.get("score", entry.get("fg_score", 0)),
                    })
                    continue

                eval_data = entry.get("eval_data")
                if not eval_data:
                    det = entry.get("details") or {}
                    stats = det.get("Stats") or {}
                    if not stats:
                        no_eval_skips += 1
                        continue
                    eval_data = {
                        "Stats": stats,
                        "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                        "FT": det.get("FT", 0),
                        "FF": det.get("FF", 0),
                        "GemCounts": det.get("GemCounts", {}),
                    }

                stats = eval_data.get("Stats", {}) or {}
                sel_color = eval_data.get("Selected Element", meta_primary_color)
                center_ft = int(eval_data.get("FT", 0) or 0)
                center_ff = int(eval_data.get("FF", 0) or 0)

                # Reuse DB cached FG finder results when compatible (major compute savings)
                if cached_force and _is_cached_force_valid_for_finder(cached_force, expected_sel, center_ft, center_ff):
                    db_cached_reuse += 1
                    fg_variants.append({
                        "data": cached_force.get("details", {}),
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": cached_force.get("score", entry.get("fg_score", 0)),
                    })
                    continue
                gem_counts_existing = eval_data.get("GemCounts", {}) or {}

                # Extract base stats (pre-gem) so the GPU solver can allocate gems correctly
                base_stats = _extract_base_stats(stats, gem_counts_existing, sel_color, center_ft, center_ff)

                # Determine how many non-fever sections exist and the notes-to-fill baseline
                n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
                if n_sections <= 0:
                    continue
                max_per_section = min(int(non_fever_base or 0), 15)

                key = (str(sel_color), int(n_sections), int(max_per_section))
                sig = stats_signature(base_stats, calc_song, sel_color)
                unique_stats_seen.add(sig)
                
                groups.setdefault(key, {}).setdefault(sig, []).append((entry, eval_data, base_stats))
                group_centers.setdefault(key, set()).add((int(center_ft), int(center_ff)))
                computed += 1

            if perf:
                t_collect_sec = time.perf_counter() - _t_collect0

            # Caches for config generation
            _cache_counts = {}

            # Process each group in GPU batches
            for (sel_color, n_sections, max_per_section), sig_map in groups.items():
                _t_cfg0 = time.perf_counter() if perf else 0.0
                
                # Build Union of FT/FF windows
                centers = group_centers.get((sel_color, n_sections, max_per_section), [])
                needed_pairs = set()
                for c_ft, c_ff in centers:
                    start_ft = max(0, c_ft - 5)
                    end_ft = min(TOTAL_GEM_BUDGET, c_ft + 5)
                    start_ff = max(0, c_ff - 5)
                    end_ff = min(TOTAL_GEM_BUDGET, c_ff + 5)
                    for ft in range(start_ft, end_ft + 1):
                        for ff in range(start_ff, end_ff + 1):
                            if ft + ff <= TOTAL_GEM_BUDGET:
                                needed_pairs.add((ft, ff))
                
                ftff_pairs = sorted(list(needed_pairs))
                # Safety cap (should fit in 1024, but if not, we truncate to avoid crash)
                # Ideally we'd split batches, but for now just cap.
                # Since gems concentrate, 1024 is plenty for even diverse populations.
                if len(ftff_pairs) > 1024:
                    print(f"[ForceGreats][GPU] Warning: FT/FF union size {len(ftff_pairs)} > 1024. Truncating.")
                    ftff_pairs = ftff_pairs[:1024]

                # Build FG configs list (Cached)
                counts_key = (n_sections, max_per_section)
                if counts_list is None:
                    counts_list = []
                    # Per-section caps requested by user
                    cap_s0 = min(int(non_fever_base or 0), 50)
                    cap_s1 = min(int(non_fever_base or 0), 25)
                    cap_s2 = min(int(non_fever_base or 0), 15)
                    
                    if n_sections == 1:
                        for s0 in range(cap_s0 + 1):
                            counts_list.append((s0,))
                    elif n_sections == 2:
                        for s0 in range(cap_s0 + 1):
                            for s1 in range(cap_s1 + 1):
                                counts_list.append((s0, s1))
                    elif n_sections == 3:
                        for s0 in range(cap_s0 + 1):
                            for s1 in range(cap_s1 + 1):
                                for s2 in range(cap_s2 + 1):
                                    counts_list.append((s0, s1, s2))
                    else:
                        # Same cap strategy as the legacy CPU path for 4+ sections
                        from itertools import product
                        cap = min(int(non_fever_base or 0), 5)
                        for counts in product(range(cap + 1), repeat=n_sections):
                            counts_list.append(tuple(counts))
                    _cache_counts[counts_key] = counts_list

                if perf:
                    t_cfg_build_sec += time.perf_counter() - _t_cfg0

                # Color flags for GPU
                is_p_pp = 1 if "Chill" == p_color else 0
                is_s_pp = 1 if "Chill" == s_color else 0
                is_p_cm = 1 if "Flow" == p_color else 0
                is_s_cm = 1 if "Flow" == s_color else 0
                is_p_fm = 1 if "Rush" == p_color else 0
                is_s_fm = 1 if "Rush" == s_color else 0
                is_p_ft = 1 if "Beat" == p_color else 0
                is_s_ft = 1 if "Beat" == s_color else 0
                is_p_ff = 1 if "Vibe" == p_color else 0
                is_s_ff = 1 if "Vibe" == s_color else 0
                is_p_ov = 1 if str(sel_color) == p_color else 0
                is_s_ov = 1 if str(sel_color) == s_color else 0

                sig_list = list(sig_map.keys())

                # Chunk unique genomes to fit GPU MAX_GENOMES (1024)
                idx0 = 0
                while idx0 < len(sig_list):
                    chunk_sigs = sig_list[idx0:idx0 + 1024]
                    idx0 += 1024

                    # Check in-memory FG_CACHE first
                    _t_cache0 = time.perf_counter() if perf else 0.0
                    pending = []
                    pending_sigs = []
                    pending_sigs = []
                    for sig in chunk_sigs:
                        # Cache key no longer includes center gems because we batch across centers.
                        # Wait, the RESULT depends on the center because it defines the search window.
                        # But now we search a UNION window.
                        # The cache entry should represent the BEST valid result.
                        # However, to be safe/correct with existing cache keys, we might need to skip 
                        # checking strict cache keys here or synthesise a checking logic.
                        # Actually, we can just compute and then cache the specific result 
                        # associated with each loadout's center.
                        
                        # Optimization: We can't easily check cache by key here because 'center' varies
                        # per-entry within the same signature group.
                        # So we assume MISS for simplicity in this batch mode, 
                        # or check per-entry (which is expensive).
                        # Let's just collect pending work. Uncached GPU is fast enough.
                        
                        # representative base_stats for sig
                        rep = sig_map[sig][0][2]
                        pending.append(rep)
                        pending_sigs.append(sig)

                    if perf:
                        t_cache_check_sec += time.perf_counter() - _t_cache0

                    if not pending:
                        continue

                    _t_genome0 = time.perf_counter() if perf else 0.0
                    genome_stats_list = []
                    for bs in pending:
                        genome_stats_list.append({
                            "base_pp": int(bs.get("Perfect Points", 0)),
                            "base_cm": int(bs.get("Combo Multiplier", 0)),
                            "base_fm": int(bs.get("Fever Multiplier", 0)),
                            "base_ft_stat": int(bs.get("Fever Time", 0)),
                            "base_ff_stat": int(bs.get("Fever Fill Rate", 0)),
                            "base_p_val": int(bs.get(p_color, 0)),
                            "base_s_val": int(bs.get(s_color, 0)),
                        })

                    timestamps = calc_song["song_data"]["timestamps"]
                    long_notes = int(calc_song.get("metadata", {}).get("Long Notes", 0) or 0)
                    last_note_time = float(calc_song.get("metadata", {}).get("Last Note Time", 0) or 0.0)
                    if perf:
                        t_genome_build_sec += time.perf_counter() - _t_genome0

                    _t_gpu0 = time.perf_counter() if perf else 0.0
                    gpu_results = solve_force_greats_finder_gpu(
                        genome_stats_list,
                        timestamps,
                        long_notes,
                        last_note_time,
                        counts_list,
                        ftff_pairs,
                        n_sections=n_sections,
                        is_p_ft=is_p_ft, is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff, is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
                        ref_arrays=ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                    )
                    if perf:
                        t_gpu_calls_sec += time.perf_counter() - _t_gpu0
                        n_gpu_calls += 1
                        if len(gpu_call_shapes) < 12:
                            gpu_call_shapes.append(
                                (len(genome_stats_list), len(counts_list), len(ftff_pairs), int(n_sections))
                            )

                    # Apply results back to all entries sharing the same signature
                    _t_apply0 = time.perf_counter() if perf else 0.0
                    for sig, bs, res in zip(pending_sigs, pending, gpu_results):
                        # The GPU result assumes the wide union window.
                        # We must map map this back to each entry's specific constraints if needed.
                        # Actually, finding a better result outside the +/-5 window is GOOD. 
                        # So we blindly accept the result.
                        
                        cfg_idx = int(res.get("cfg_idx", -1))
                        cfg_counts = list(counts_list[cfg_idx]) if 0 <= cfg_idx < len(counts_list) else []

                        final_stats = _apply_gems_to_base(
                            bs,
                            str(sel_color),
                            int(res.get("FT", 0)),
                            int(res.get("FF", 0)),
                            res.get("gem_counts") or {},
                        )

                        fg_info = {
                            "enabled": True,
                            "algo_version": 3,
                            "config": _force_greats_counts_to_dict(cfg_counts, max(2, len(cfg_counts))),
                            "base_score": int(res.get("base_score", 0)),
                            "final_score": int(res.get("final_score", 0)),
                            "score_penalty": int(res.get("score_penalty", 0)),
                            "fill_penalty": int(res.get("fill_penalty", 0)),
                            "total_penalty": int(res.get("score_penalty", 0)) + int(res.get("fill_penalty", 0)),
                            "num_non_fever_sections": int(n_sections),
                            "penalty_analysis": {},
                            "finder": True,
                            "gpu": True,
                            "center_ft": int(center_ft),
                            "center_ff": int(center_ff),
                            "search_radius": 5,
                        }

                        fg_variant = {
                            "Score": int(res.get("final_score", 0)),
                            "FT": int(res.get("FT", 0)),
                            "FF": int(res.get("FF", 0)),
                            "GemCounts": res.get("gem_counts") or {},
                            "Stats": final_stats,
                            "Selected Element": str(sel_color),
                            "ForceGreats": {**fg_info, "variant_applied": True},
                        }

                        # Store in in-memory cache for reuse within the session
                        # Store in in-memory cache for reuse within the session
                        # We cache using the FOUND result's metrics, or maybe just key by sig?
                        # To cooperate with single-item lookups, we should store it under keys 
                        # matching the entry's expectations if possible.
                        # But strictly, we can just not write to cache here to avoid complexity
                        # since batch mode is the primary path.
                        
                        for entry, eval_data, _ in sig_map.get(sig, []):
                            # Update entry
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
                            
                            # Cache under the entry's specific requirements so future single lookups find it
                            c_ft = int(eval_data.get("FT", 0) or 0)
                            c_ff = int(eval_data.get("FF", 0) or 0)
                            FG_CACHE[(sig, str(sel_color), c_ft, c_ff, int(n_sections), int(max_per_section))] = fg_variant
                    if perf:
                        t_result_apply_sec += time.perf_counter() - _t_apply0

            print(f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed}, budget {max_fg_compute})")
            if perf:
                try:
                    print(
                        "[PERF] ForceGreatsFinder(GPU): "
                        f"collect={t_collect_sec:.3f}s cfg_build={t_cfg_build_sec:.3f}s "
                        f"gpu_calls={t_gpu_calls_sec:.3f}s n_gpu_calls={n_gpu_calls} "
                        f"FG_CACHE(hit={fg_cache_hits},miss={fg_cache_misses}) "
                        f"db_reuse={db_cached_reuse} no_eval_skips={no_eval_skips} "
                        f"groups={len(groups)} unique_sigs={len(unique_stats_seen)}"
                    )
                    print(
                        "[PERF] FG Detailed: "
                        f"cache_check={t_cache_check_sec*1000:.1f}ms "
                        f"genome_build={t_genome_build_sec*1000:.1f}ms "
                        f"result_apply={t_result_apply_sec*1000:.1f}ms"
                    )
                    if gpu_call_shapes:
                        print(
                            "[PERF] FG GPU call shapes (n_genomes,n_cfg,n_ftff,n_sections): "
                            f"{gpu_call_shapes}"
                        )
                except Exception:
                    pass
            return fg_variants
        except Exception as e:
            print(f"[ForceGreats][GPU] Batch FG finder failed; falling back to CPU per-loadout: {e}")
            # Reset state to allow CPU manual loop to run from scratch
            fg_variants = []
            computed = 0
            unique_stats_seen = set()
    for entry in loadout_entries.values():
        if computed >= max_fg_compute:
            break

        def _is_cached_force_valid(cached_force_obj, expected_selected_element, center_ft, center_ff, finder_enabled):
            """
            Validate that a DB-cached ForceGreats payload is compatible with the current code/config.
            This prevents stale FG results (from older algorithms or wrong overflow target) from
            presenting as score inflation.
            """
            if not isinstance(cached_force_obj, dict):
                return False
            details = cached_force_obj.get("details") or {}
            if not isinstance(details, dict):
                return False
            fg_meta = details.get("ForceGreats") or {}
            if not isinstance(fg_meta, dict):
                return False
            # Require version tag to avoid trusting old/broken FG payloads
            algo_ver = fg_meta.get("algo_version")
            if algo_ver is None:
                return False
            if int(algo_ver or 0) != 3:
                return False
            if finder_enabled:
                # Finder results must be from finder path to be reused safely
                if not fg_meta.get("finder"):
                    return False
                try:
                    if int(fg_meta.get("center_ft", -999)) != int(center_ft):
                        return False
                    if int(fg_meta.get("center_ff", -999)) != int(center_ff):
                        return False
                except Exception:
                    return False
            # Guard against overflow-target mismatch (affects gem optimization and score)
            cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
            if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
                return False
            return True

        cached_force = entry.get("force")
        expected_sel = None
        expected_center_ft = 0
        expected_center_ff = 0
        try:
            det0 = entry.get("details") or {}
            expected_sel = det0.get("SelectedElement") or det0.get("Selected Element") or meta_primary_color
            expected_center_ft = det0.get("FT", 0) or 0
            expected_center_ff = det0.get("FF", 0) or 0
        except Exception:
            expected_sel = meta_primary_color

        # Reuse cached force results if they are compatible with current algo/version.
        if (
            cached_force
            and (cached_force.get("score") or entry.get("fg_score"))
            and _is_cached_force_valid(cached_force, expected_sel, expected_center_ft, expected_center_ff, force_greats_finder)
        ):
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
            use_gpu=use_gpu,
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
    # Use BaseScore if available (true base score).
    # Fall back to Score if BaseScore not present (backwards compatibility).
    score = best_data.get("BaseScore") or best_data.get("Score", 0)

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
        msg = f" >> NEW RECORD! Previous: {prev_score} | New: {score} - Updating Evolution Database..."
        print(msg)
    else:
        msg = f" >> No improvement over DB Record ({prev_score})"
        if is_first: # Edge case coverage
            msg = " >> Record exists but no improvement found."
        print(msg)

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

    # Find FG result for TOP1's specific loadout (not global best)
    # This ensures force_details_json matches the loadout's gear/minis
    fg_score_val = 0
    top1_gear = tuple(top1.get("gear", [])) if top1 else ()
    top1_minis = tuple(top1.get("minis", [])) if top1 else ()
    
    matching_fg = None
    for fg_cand in current_run_fg_candidates:
        fg_gear = tuple(fg_cand.get("gear", []))
        fg_minis = tuple(fg_cand.get("minis", []))
        if fg_gear == top1_gear and fg_minis == top1_minis:
            matching_fg = fg_cand
            break
    
    if matching_fg:
        fg_score_val = matching_fg.get("score", 0) or 0
        updated_payload["force"] = {
            "score": matching_fg.get("score"),
            "gear": matching_fg.get("gear", []),
            "minis": matching_fg.get("minis", []),
            "details": matching_fg.get("details", {}),
        }
    # If no matching FG from current run, keep the old one from prev_record (if gear matches)
    elif prev_record and prev_record.get("force"):
        prev_force = prev_record.get("force")
        prev_force_gear = tuple(prev_force.get("gear", []))
        prev_force_minis = tuple(prev_force.get("minis", []))
        if prev_force_gear == top1_gear and prev_force_minis == top1_minis:
            updated_payload["force"] = prev_force
            fg_score_val = prev_force.get("score", 0) or 0
        else:
            updated_payload.pop("force", None)
    else:
        updated_payload.pop("force", None)

    updated_payload["fg_score"] = fg_score_val

    # Track BEST FG entry separately (may be a different loadout than best base)
    # This ensures we always persist the highest-scoring FG loadout
    best_fg_entry = None
    if current_run_fg_candidates:
        best_fg_entry = max(current_run_fg_candidates, key=lambda x: x.get("score", 0))
        best_fg_score = best_fg_entry.get("score", 0)
        # Only include if it's actually better than top1's FG score
        if best_fg_score > fg_score_val:
            updated_payload["best_fg"] = {
                "score": best_fg_score,
                "gear": best_fg_entry.get("gear", []),
                "minis": best_fg_entry.get("minis", []),
                "details": best_fg_entry.get("details", {}),
            }

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

    # Top 1 (base) - store with its OWN fg_score and force data (if available)
    # This ensures the force_details_json matches the loadout gear
    _append_entry(
        db_payload.get("score", 0),
        db_payload.get("gear", []),
        db_payload.get("minis", []),
        db_payload.get("details", {}),
        db_payload.get("fg_score", 0),
        db_payload.get("force"),  # This comes from top1's own FG, not global best
    )

    # BEST FG ENTRY: If a different loadout has the best FG score, include it as a priority entry
    # This ensures we always persist the highest-scoring FG loadout
    best_fg = db_payload.get("best_fg")
    if best_fg:
        best_fg_gear = best_fg.get("gear", [])
        best_fg_minis = best_fg.get("minis", [])
        best_fg_details = best_fg.get("details", {})
        best_fg_score = best_fg.get("score", 0)
        
        # Build force object for the best FG entry
        best_fg_force = {
            "score": best_fg_score,
            "gear": best_fg_gear,
            "minis": best_fg_minis,
            "details": best_fg_details,
        }
        
        _append_entry(
            best_fg_details.get("ForceGreats", {}).get("base_score", 0),  # Use FG's base_score as the loadout's score
            best_fg_gear,
            best_fg_minis,
            best_fg_details,
            best_fg_score,  # fg_score
            best_fg_force,  # force object
        )

    # NOTE: Removed separate "Top 1 FG" row creation that used to store FG data
    # with potentially different gear. Each loadout now stores its OWN FG via
    # the loadout_entries loop below.

    # GA candidates (capped to DB limit)
    if ga_candidates:
        for eval_result in ga_candidates:
            eval_data = eval_result.get("Data") or {}
            # Use BaseScore (true score) for DB storage; fall back for older payloads.
            eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
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
        print(f"ForceGreat Score: {best_fg_entry.get('score', 0)}")
        print(f"Best FG Gear: {fg_gear_names}")
        print(f"Best FG Minis: {fg_mini_names}")
        cfg_map = fg_meta.get("config", {})
        if cfg_map:
            print(f"Config: {cfg_map}")
