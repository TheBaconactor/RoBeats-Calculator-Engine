"""
Utility functions and helpers for the gear optimizer.
Pure functions with no external dependencies.
"""

import configparser

# --- STAT KEYS / HELPERS ---
STAT_KEYS = [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]

def cfg_to_dict(cfg):
    """
    Serialize ConfigParser to a plain dict for safe process transport.

    Args:
        cfg: ConfigParser instance

    Returns:
        dict: Serialized configuration
    """
    return {section: dict(cfg.items(section)) for section in cfg.sections()}


def cfg_from_dict(cfg_dict):
    """
    Rehydrate ConfigParser from a plain dict copy.

    Args:
        cfg_dict: Dictionary with config sections

    Returns:
        ConfigParser: Reconstructed configuration object
    """
    # Use a plain ConfigParser here: this runs on hot paths (per-song/task) where
    # fallback diagnostics would otherwise spam logs and materially hurt throughput.
    # Full fallback diagnostics are still available during top-level config loading.
    cfg = configparser.ConfigParser()
    for section, items in cfg_dict.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for k, v in items.items():
            cfg.set(section, k, v)
    return cfg


def empty_stats():
    """
    Return a fresh stats dict with all relevant keys initialized to 0.

    Returns:
        dict: Stats dictionary with all keys set to 0
    """
    return {k: 0 for k in STAT_KEYS}


def safe_int(val, default=0):
    """
    Safely convert a value to an integer with fallback.

    Args:
        val: Value to convert (str, int, float, or None)
        default: Default value if conversion fails

    Returns:
        int: Converted integer or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 999)
        999
        >>> safe_int(None, 0)
        0
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except (TypeError, ValueError, OverflowError):
        return default


def require_int(value, *, field):
    """Fail-loud int coercion for internal / authoritative state (issue #56 B3).

    Unlike `safe_int`, this RAISES instead of returning a default, so a bad value on an
    internal invariant or an authoritative persistence field is surfaced loudly rather
    than silently masked. Use it on internal authority paths; use `safe_int` at external
    boundaries (config, malformed user/DB input, display).
    """
    try:
        return int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {field}: {value!r}") from exc


def safe_float(val, default=0.0):
    """
    Safely convert a value to a float with fallback.

    Args:
        val: Value to convert
        default: Default value if conversion fails

    Returns:
        float: Converted float or default

    Examples:
        >>> safe_float("3.14")
        3.14
        >>> safe_float("-")
        0.0
    """
    try:
        if not val or val == "-":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def parse_float(val, default=0.0):
    try:
        if val is None:
            return default
        return float(str(val).strip())
    except (TypeError, ValueError):
        return default


def _signature_base(stats, calc_song, selected_color):
    meta = calc_song["metadata"]
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    gs = stats.get

    # Mirror the same Beat/Vibe mapping the solver uses
    base_beat = gs("Beat", 0)
    base_vibe = gs("Vibe", 0)

    def get_val_inline(k):
        if k == "Beat":
            return base_beat
        if k == "Vibe":
            return base_vibe
        return gs(k, 0)

    # Only capture elemental values that actually feed into P/S lanes
    base_p_val = get_val_inline(p_color)
    base_s_val = get_val_inline(s_color)

    return (
        meta.get("Song Name", ""),
        meta.get("Difficulty", ""),
        selected_color,
        p_color,
        s_color,
        gs("Perfect Points", 0),
        gs("Combo Multiplier", 0),
        gs("Fever Multiplier", 0),
        gs("Fever Fill Rate", 0),
        gs("Fever Time", 0),
        base_p_val,
        base_s_val,
    )


def stats_signature(stats, calc_song, selected_color):
    """
    Compute a cache key that captures exactly the inputs influencing the gem
    solver for a given song context. Two loadouts with the same signature will
    produce identical gem allocations and scores.

    Key insight: elemental stats only matter if they feed into the song's
    Primary/Secondary/Selected Element paths. Differences in other elements
    are irrelevant and should share the same cache entry.

    Args:
        stats: Stats dictionary
        calc_song: Song calculation context
        selected_color: Selected element color

    Returns:
        tuple: Hashable signature for caching
    """
    return _signature_base(stats, calc_song, selected_color) + timing_envelope_timing_context(calc_song)


def timing_envelope_timing_context(calc_song):
    """
    Return deterministic timing-envelope settings that affect base timing.
    """
    if not isinstance(calc_song, dict):
        return ("", "", "", 0)

    meta = calc_song.get("metadata", {}) or {}
    if not isinstance(meta, dict) or not meta.get("TimingEnvelopeApplied"):
        return ("", "", "", 0)

    return (
        "TIMING_ENVELOPE",
        str(meta.get("TimingEnvelopeMode", "") or "").strip().lower(),
        str(meta.get("TimingEnvelopeBaselineHash", "") or ""),
        0,
    )


def timing_envelope_full_context(calc_song):
    """
    Return deterministic timing-envelope settings that can affect FG carry.
    """
    if not isinstance(calc_song, dict):
        return ("", "", "", 0)

    meta = calc_song.get("metadata", {}) or {}
    if not isinstance(meta, dict) or not meta.get("TimingEnvelopeApplied"):
        return ("", "", "", 0)

    return (
        "TIMING_ENVELOPE",
        str(meta.get("TimingEnvelopeMode", "") or "").strip().lower(),
        str(meta.get("TimingEnvelopeFGCarry", "") or "").strip().lower(),
        meta.get("TimingEnvelopeBaselineHash", "") or 0,
    )


def full_pipeline_signature(stats, calc_song, selected_color):
    """
    Compute an exact-safe cache key for the full base + FG scoring pipeline.

    This is a sufficient key (not necessarily minimal). Equal signatures imply identical
    scoring results under the repo's semantics for a fixed calc_song.
    """
    return _signature_base(stats, calc_song, selected_color) + timing_envelope_full_context(calc_song)


def get_selected_element(data: object, default: str = "") -> str:
    """
    Normalize the "selected element" field across historical key spellings.

    Runtime payloads typically use "Selected Element" while persisted details
    commonly use "SelectedElement". This helper reads either form.
    """
    if not isinstance(data, dict):
        return str(default or "")

    v = data.get("Selected Element")
    if not v:
        v = data.get("SelectedElement")
    if not v:
        v = default
    return str(v or "")


def _row_stat_value(row, key):
    """Return a row stat as an int, tolerating missing/invalid values."""
    if not key:
        return 0
    try:
        return int(row.get(key, 0) or 0)
    except (AttributeError, TypeError, ValueError):
        return safe_int(row.get(key, 0), 0)


def _relevant_row_projection(row, primary_color, secondary_color=""):
    """
    Project a row onto the exact score-relevant axes for request-local domain construction.

    The current runtime fixes `selected_color = primary_color` before `initialize_pools(...)`
    is used, so only the song's primary/secondary elemental lanes remain score-relevant here.
    """
    return (
        _row_stat_value(row, "Perfect Points"),
        _row_stat_value(row, "Combo Multiplier"),
        _row_stat_value(row, "Fever Multiplier"),
        _row_stat_value(row, "Fever Time"),
        _row_stat_value(row, "Fever Fill Rate"),
        _row_stat_value(row, str(primary_color or "")),
        _row_stat_value(row, str(secondary_color or "")),
    )


def _timing_neutral_relevant_dominates(candidate, other, primary_color, secondary_color=""):
    """
    Return True when `candidate` exactly-safe dominates `other` for the current song context.

    Safe dominance for the live single-song pool build requires:
    - equal timing coordinates `(FT, FF)`, and
    - coordinatewise dominance on the remaining score-relevant axes
      `(PP, CM, FM, val_primary, val_secondary)`,
    - with at least one strict improvement.
    """
    cand_sig = _relevant_row_projection(candidate, primary_color, secondary_color)
    other_sig = _relevant_row_projection(other, primary_color, secondary_color)

    if cand_sig[3] != other_sig[3] or cand_sig[4] != other_sig[4]:
        return False

    strictly_better = False
    for idx in (0, 1, 2, 5, 6):
        if cand_sig[idx] < other_sig[idx]:
            return False
        if cand_sig[idx] > other_sig[idx]:
            strictly_better = True
    return strictly_better


def prune_gear_pool_lossless_for_song(gear_list, primary_color, secondary_color=""):
    """
    Exact-safe gear pruning for request-local exact domain initialization.

    Steps:
    1. Collapse same-slot rows with identical relevant projections (keep the first witness).
    2. Remove rows timing-neutrally dominated in the same song context.
    """
    gear_items = list(gear_list or [])
    if len(gear_items) <= 1:
        return gear_items

    unique_rows = []
    seen_signatures = set()
    for row in gear_items:
        sig = _relevant_row_projection(row, primary_color, secondary_color)
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        unique_rows.append(row)

    pruned = []
    for idx, row in enumerate(unique_rows):
        dominated = False
        for other_idx, other in enumerate(unique_rows):
            if other_idx == idx:
                continue
            if _timing_neutral_relevant_dominates(other, row, primary_color, secondary_color):
                dominated = True
                break
        if not dominated:
            pruned.append(row)
    return pruned


def prune_mini_pool_lossless_for_song(mini_list, primary_color, secondary_color=""):
    """
    Exact-safe Mini pruning for the request-local shared distinct-three domain.

    Safe reductions:
    - cap exact relevant-signature multiplicity at 3 (any legal triple can use at most 3 rows),
    - iteratively remove a row only when 3 distinct dominators still remain in the *current* pool.
    """
    mini_items = list(mini_list or [])
    if len(mini_items) <= 1:
        return mini_items

    capped_rows = []
    multiplicities = {}
    for row in mini_items:
        sig = _relevant_row_projection(row, primary_color, secondary_color)
        seen = multiplicities.get(sig, 0)
        if seen >= 3:
            continue
        multiplicities[sig] = seen + 1
        capped_rows.append(row)

    survivors = list(capped_rows)
    while len(survivors) > 3:
        removed_any = False
        for idx, row in enumerate(survivors):
            dominators = 0
            for other_idx, other in enumerate(survivors):
                if other_idx == idx:
                    continue
                if _timing_neutral_relevant_dominates(other, row, primary_color, secondary_color):
                    dominators += 1
                    if dominators >= 3:
                        break
            if dominators >= 3:
                del survivors[idx]
                removed_any = True
                break
        if not removed_any:
            break

    return survivors
