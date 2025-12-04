#                       !/usr/bin/env python3
"""
Manual Calculator + Iteration Engine + Co-Evolution Finder
(Unified Genome: Optimizes Gear AND Minis simultaneously for perfect synergy)
WITH PERMANENT EVOLUTION DATABASE
"""

import os, re, json, csv, configparser, logging, copy, itertools, time, random, sys, threading
import concurrent.futures
import contextlib
import multiprocessing
from io import StringIO
import numpy as np
from math import floor, ceil

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(_path=None):
        return False

try:
    import requests
except ImportError:
    requests = None

# Force single-core execution for any threaded numerical backends
for _env in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_env, "1")


def cfg_to_dict(cfg):
    """Serialize ConfigParser to a plain dict for safe process transport."""
    return {section: dict(cfg.items(section)) for section in cfg.sections()}


def cfg_from_dict(cfg_dict):
    """Rehydrate ConfigParser from a plain dict copy."""
    cfg = configparser.ConfigParser()
    for section, items in cfg_dict.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for k, v in items.items():
            cfg.set(section, k, v)
    return cfg


class Tee:
    """Writes to multiple targets (e.g., stdout + buffer) for live logging."""

    def __init__(self, *targets):
        self.targets = targets

    def write(self, data):
        for t in self.targets:
            t.write(data)
        return len(data)

    def flush(self):
        for t in self.targets:
            t.flush()

# --- OPTIONAL JIT ACCELERATION ---
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    def jit(nopython=True, cache=True):
        def decorator(func):
            return func
        return decorator


# --- CONFIGURABLE CONSTANTS ---
GEM_SCALE_NORMAL = 2
GEM_SCALE_FEVER  = 3
ELEMENTAL_GEM_SCALE = 6
GEM_STAT_TO_ELEMENT_SCALE = 3

MAX_STAT_INDEX = 160
TOTAL_GEM_BUDGET = 90
TOTAL_ROWS = 160

# --- GA CONSTANTS (Will be overwritten by Config) ---
GA_POPULATION_SIZE = 250
GA_GENERATIONS = 75
GA_MUTATION_RATE = 0.275
GA_ELITISM = 1
GA_MULTI_RUNS_DEFAULT = 3  # Multi-start passes to escape local maxima
GA_MUTATION_RATE_MAX = 0.45  # Cap for adaptive mutation bumps

# --- DATABASE FILE ---
DB_FILE = "evolution_db.json"

# --- Fever timeline cache ---
MAX_TIMELINE_CACHE_PER_SONG = 500000
FEVER_TIMELINE_CACHE = {}

# --- Gem solver cache (per-stat-signature) ---
# Avoids redundant solve_best_fever_combination calls when different gear+mini
# combinations produce the same effective stats for a given song/color context.
GEM_SOLVER_CACHE = {}

# Keys to skip when aggregating gear/mini stats (metadata, not actual stats).
SKIP_ITEM_KEYS = frozenset({"Name", "type"})


def stats_signature(stats, calc_song, selected_color):
    """
    Compute a cache key that captures exactly the inputs influencing the gem
    solver for a given song context. Two loadouts with the same signature will
    produce identical gem allocations and scores.
    
    Key insight: elemental stats only matter if they feed into the song's
    Primary/Secondary/Selected Element paths. Differences in other elements
    are irrelevant and should share the same cache entry.
    """
    meta = calc_song["metadata"]
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    gs = stats.get

    # Mirror the same Beat/Vibe mapping the solver uses.
    base_beat = gs("Beat", 0)
    base_vibe = gs("Vibe", 0)

    def get_val_inline(k):
        if k == "Beat":
            return base_beat
        if k == "Vibe":
            return base_vibe
        return gs(k, 0)

    # Only capture elemental values that actually feed into P/S lanes.
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


# --- Gear Dominance Pruning ---
# DOMINANCE_KEYS is aliased to STAT_KEYS (defined below) since they are identical.

def is_dominated_by(a, b):
    """
    Check if gear 'a' is strictly dominated by gear 'b'.
    
    Returns True if:
      - b[stat] >= a[stat] for ALL stats in DOMINANCE_KEYS, AND
      - b[stat] > a[stat] for AT LEAST ONE stat
    
    This means 'a' can never be optimal if 'b' is available.
    """
    dominated = all(b.get(k, 0) >= a.get(k, 0) for k in DOMINANCE_KEYS)
    if not dominated:
        return False
    strictly_better = any(b.get(k, 0) > a.get(k, 0) for k in DOMINANCE_KEYS)
    return strictly_better


def prune_dominated_gear(gear_list):
    """
    Remove gear items that are strictly dominated by another gear in the list.
    
    For each gear, check if any other gear in the list dominates it.
    Only keep gear that is NOT dominated by any other.
    
    Returns a new list with dominated gear removed.
    """
    if len(gear_list) <= 1:
        return gear_list
    
    pruned = []
    for g in gear_list:
        dominated = False
        for other in gear_list:
            if other is g:
                continue
            if is_dominated_by(g, other):
                dominated = True
                break
        if not dominated:
            pruned.append(g)
    return pruned


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

# Alias for gear dominance pruning (same keys used for dominance comparison).
DOMINANCE_KEYS = STAT_KEYS


def empty_stats():
    """Return a fresh stats dict with all relevant keys initialized to 0."""
    return {k: 0 for k in STAT_KEYS}


# --- Helper Conversion Functions ---
def safe_int(val, default=0):
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs.
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except Exception:
        return default


def safe_float(val, default=0.0):
    try:
        if not val or val == "-":
            return default
        return float(val)
    except Exception:
        return default


# --- Setup Directories and Logging ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
os.makedirs(BIN_DIR, exist_ok=True)
log_file_path = os.path.join(BIN_DIR, "error.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Environment (Discord + external paths) ---
ENV_PATH = os.path.join(SCRIPT_DIR, "Discord.env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOGGING_CHANNEL_ID = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
STATS_CHANNEL_ID = safe_int(os.getenv("STATSCHANNEL"), 0) or None
EVOLUTION_DB_PATH = os.getenv("EVOLUTION_DB_PATH") or os.path.join(SCRIPT_DIR, DB_FILE)


class DiscordReporter:
    """Minimal helper to push log and stat updates to Discord."""

    def __init__(self, token, log_channel_id=None, stats_channel_id=None):
        self.token = token
        self.log_channel_id = log_channel_id
        self.stats_channel_id = stats_channel_id

    def _post(self, channel_id, content):
        if not self.token or not channel_id or not content or requests is None:
            return

        chunks = [content[i:i + 1800] for i in range(0, len(content), 1800)] or [content]
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

        for chunk in chunks:
            payload = {"content": chunk}
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    resp = requests.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                    if resp.status_code == 429:
                        try:
                            retry_after = float(resp.json().get("retry_after", 1))
                        except Exception:
                            retry_after = 1.0
                        time.sleep(max(retry_after, 0.5))
                        continue
                    if resp.status_code >= 300:
                        print(
                            f"[DiscordReporter] Failed to send to {channel_id}: "
                            f"{resp.status_code} {resp.text}"
                        )
                    break
                except Exception as e:
                    print(f"[DiscordReporter] Error sending Discord message: {e}")
                    break

    def send_log(self, content):
        self._post(self.log_channel_id, sanitize_public_message(content))

    def send_stats(self, content):
        self._post(self.stats_channel_id, content)


discord_reporter = DiscordReporter(DISCORD_TOKEN, LOGGING_CHANNEL_ID, STATS_CHANNEL_ID)


def build_stats_summary(res, completed, total):
    """Create a compact Discord-friendly summary for a completed song run."""
    payload = res.get("db_payload") or {}
    details = payload.get("details") or {}

    score = payload.get("score")
    score_txt = "N/A" if score is None else f"{int(score):,}" if isinstance(score, (int, float)) else str(score)
    gear_names = payload.get("gear") or []
    mini_names = payload.get("minis") or []
    element = details.get("SelectedElement") or details.get("Selected Element", "")
    ft = details.get("FT")
    ff = details.get("FF")

    lines = [f"[{completed}/{total}] {res.get('song', 'Unknown Song')}"]
    lines.append(f"Score: {score_txt}")
    attempts_best = payload.get("attempts_first")
    attempt_lifetime = payload.get("attempt_lifetime")
    attempt_parts = []
    if attempts_best is not None:
        attempt_parts.append(f"Best: {attempts_best}")
    if attempt_lifetime is not None:
        attempt_parts.append(f"Lifetime: {attempt_lifetime}")
    if attempt_parts:
        lines.append(f"Attempts: {' | '.join(attempt_parts)}")
    if element:
        lines.append(f"Element: {element}")
    if ft is not None or ff is not None:
        lines.append(f"FT: {ft if ft is not None else 'N/A'} | FF: {ff if ff is not None else 'N/A'}")
    lines.append(f"Gear: {', '.join(gear_names) if gear_names else 'N/A'}")
    lines.append(f"Minis: {', '.join(mini_names) if mini_names else 'N/A'}")
    return "\n".join(lines)


# --- DATABASE FUNCTIONS ---
def get_evolution_db_path():
    """Return the configured evolution DB location (env override supported)."""
    return EVOLUTION_DB_PATH if EVOLUTION_DB_PATH else os.path.join(SCRIPT_DIR, DB_FILE)


def load_evolution_db():
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return {}

    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        # Corrupt JSON; preserve a copy and start fresh.
        print(f"[DB] Failed to load {db_path}: {e}")
        try:
            corrupt_path = f"{db_path}.corrupt.{int(time.time())}"
            os.replace(db_path, corrupt_path)
            print(f"[DB] Moved corrupt DB to {corrupt_path}. Starting with an empty DB.")
        except Exception as move_err:
            print(f"[DB] Could not move corrupt DB: {move_err}. Continuing with empty DB.")
        return {}
    cleaned = sanitize_evolution_db(data)
    if cleaned != data:
        try:
            save_evolution_db(cleaned)
            print("[DB] Detected and removed invalid entries; DB sanitized.")
        except Exception as e:
            print(f"[DB] Failed to sanitize DB: {e}")
    return cleaned


def save_evolution_db(db_data):
    db_path = get_evolution_db_path()
    try:
        with open(db_path, "w", encoding="utf-8") as f:
            # Compact JSON write (separators remove whitespace)
            json.dump(db_data, f, separators=(",", ":"))
    except Exception as e:
        print(f"Failed to save DB: {e}")


def sanitize_evolution_db(db_data):
    """
    Remove malformed or non-serializable entries to avoid DB corruption.
    Keeps only dict values with numeric scores and list-ish gear/minis.
    """
    if not isinstance(db_data, dict):
        return {}
    cleaned = {}
    for k, v in db_data.items():
        if not isinstance(k, str):
            continue
        if not isinstance(v, dict):
            continue
        if "score" in v and not isinstance(v.get("score"), (int, float)):
            continue
        for list_key in ("gear", "minis", "loadout"):
            if list_key in v and not isinstance(v.get(list_key), list):
                v.pop(list_key, None)
        if "details" in v and not isinstance(v.get("details"), dict):
            v.pop("details", None)
        if "second" in v:
            v.pop("second", None)
        cleaned[k] = v
    return cleaned


def sanitize_public_message(content):
    """Strip local filesystem details from messages before posting externally."""
    try:
        text = str(content) if content is not None else ""
    except Exception:
        text = ""
    if not text:
        return ""

    sensitive_paths = set()
    for path_candidate in (
        SCRIPT_DIR,
        BIN_DIR,
        os.getcwd(),
        os.path.expanduser("~"),
        get_evolution_db_path(),
    ):
        if path_candidate:
            normalized = os.path.normcase(os.path.normpath(path_candidate))
            sensitive_paths.add(normalized)

    sanitized = text
    for marker in sensitive_paths:
        variants = {
            marker,
            marker.replace("\\", "/"),
            marker.replace("\\", "\\\\"),
            marker.replace("/", "\\"),
        }
        for variant in variants:
            sanitized = sanitized.replace(variant, "<redacted>")
    return sanitized


# --- Load Cached Paths ---
def load_paths_cache():
    pc = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")
    if os.path.exists(pc):
        with open(pc, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# --- Read Stats Table ---
def read_table(fp):
    if not fp or not os.path.exists(fp):
        return []
    try:
        # Explicit UTF-8-SIG to match other data files and avoid Windows 'charmap' decode issues
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        if not lines:
            return []
        table = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                try:
                    row = [float(x) for x in parts]
                    table.append(row)
                except Exception:
                    pass
        return table
    except Exception:
        return []


def resolve_stats_csv(paths, filename):
    """Resolve Gears/Minis CSV relative to SCRIPT_DIR or Stats.csv folder."""
    csv_path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(csv_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc:
            csv_path = os.path.join(os.path.dirname(stats_loc), filename)
    return csv_path


# --- CSV Parsing Helpers (shared) ---
def parse_gear_rows(filepath):
    """Parse Gears.csv into a list of gear dicts."""
    gear_list = []
    if not os.path.exists(filepath):
        return gear_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return gear_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        def _build_row_map(row):
            mapped = {}
            for idx, col in enumerate(header_lower):
                key = col or f"col_{idx}"
                mapped.setdefault(key, []).append(row[idx].strip() if idx < len(row) else "")
            return mapped

        def _first_val(row_map, keys):
            for key in keys:
                for val in row_map.get(key, []):
                    v = str(val).strip() if val is not None else ""
                    if v:
                        return v
            return ""

        modern_format = "type" in header_lower and any(
            name in header_lower for name in ("gear name", "name", "gear")
        )

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row)
                name = _first_val(row_map, ("gear name", "name", "gear"))
                if not name:
                    continue
                slot = _first_val(row_map, ("type", "slot", "category")) or "Hat"
                stats = {
                    "Name": name,
                    "type": slot,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": safe_int(
                        _first_val(row_map, ("ppoint", "perfect points", "pp", "ppoints"))
                    ),
                    "Combo Multiplier": safe_int(
                        _first_val(row_map, ("cmult", "cbmlt", "combo multiplier", "combo"))
                    ),
                    "Fever Multiplier": safe_int(
                        _first_val(row_map, ("fmult", "fmlt", "fever multiplier"))
                    ),
                }
                # IMPORTANT: Perfect Time (often stored as "PTime") is a
                # completely different mechanic from Fever Time and must
                # NEVER be treated as Fever Time. Do not fall back to
                # any "ptime" column here; only true Fever Time fields
                # ("time" / "fever time" / "ft") are allowed.
                time_val = _first_val(row_map, ("time", "fever time", "ft"))
                stats["Fever Time"] = safe_int(time_val)
                stats["Fever Fill Rate"] = safe_int(
                    _first_val(row_map, ("fill", "fvfil", "fever fill rate", "fever fill"))
                )
                gear_list.append(stats)
        else:
            current_category = "Hat"
            known_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
            for row in rows[1:]:
                if not row:
                    continue
                potential_cat = row[0].strip()
                if potential_cat in known_slots:
                    current_category = potential_cat
                    continue
                if len(row) < 11:
                    continue
                name = row[0].strip()
                if not name:
                    continue
                stats = {
                    "Name": name,
                    "type": current_category,
                    "Chill": safe_int(row[1]),
                    "Flow": safe_int(row[2]),
                    "Rush": safe_int(row[3]),
                    "Beat": safe_int(row[4]),
                    "Vibe": safe_int(row[5]),
                    "Perfect Points": safe_int(row[6]),
                    "Combo Multiplier": safe_int(row[7]),
                    "Fever Multiplier": safe_int(row[8]),
                    "Fever Time": safe_int(row[9]),
                    "Fever Fill Rate": safe_int(row[10]),
                }
                gear_list.append(stats)
    except Exception:
        pass
    return gear_list


def parse_mini_rows(filepath):
    """Parse Minis.csv into a list of mini dicts."""
    minis_list = []
    if not os.path.exists(filepath):
        return minis_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return minis_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        def _build_row_map(row):
            mapped = {}
            for idx, col in enumerate(header_lower):
                key = col or f"col_{idx}"
                mapped.setdefault(key, []).append(row[idx].strip() if idx < len(row) else "")
            return mapped

        def _first_val(row_map, keys):
            for key in keys:
                for val in row_map.get(key, []):
                    v = str(val).strip() if val is not None else ""
                    if v:
                        return v
            return ""

        modern_format = "type" in header_lower and any(
            name in header_lower for name in ("mini name", "name", "mini")
        )

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row)
                name = _first_val(row_map, ("mini name", "name", "mini"))
                if not name or name == "(Empty)":
                    continue
                mini_type = _first_val(row_map, ("type",)) or "Mini"
                stats = {
                    "Name": name,
                    "type": mini_type,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": 0,
                    "Combo Multiplier": safe_int(
                        _first_val(row_map, ("cbmlt", "cmult", "combo multiplier", "combo"))
                    ),
                    "Fever Multiplier": safe_int(
                        _first_val(row_map, ("fmult", "fmlt", "fvmlt", "fever multiplier"))
                    ),
                    "Fever Time": safe_int(
                        _first_val(row_map, ("fvtim", "time", "ft", "fever time"))
                    ),
                    "Fever Fill Rate": safe_int(
                        _first_val(row_map, ("fvfil", "fill", "ff", "fever fill"))
                    ),
                }
                minis_list.append(stats)
        else:
            for row in rows[1:]:
                if len(row) < 12:
                    continue
                name = row[1].strip()
                if not name or name == "(Empty)":
                    continue
                stats = {
                    "Name": name,
                    "type": "Mini",
                    "Chill": safe_int(row[2]),
                    "Flow": safe_int(row[3]),
                    "Rush": safe_int(row[4]),
                    "Beat": safe_int(row[5]),
                    "Vibe": safe_int(row[6]),
                    "Perfect Points": 0,
                    "Combo Multiplier": safe_int(row[8]),
                    "Fever Multiplier": safe_int(row[9]),
                    "Fever Time": safe_int(row[10]),
                    "Fever Fill Rate": safe_int(row[11]),
                }
                minis_list.append(stats)
    except Exception:
        pass
    return minis_list


# --- CSV Data Loading (now using shared parsers) ---
def load_csv_db(filepath, db_type="gear"):
    db = {}
    if not os.path.exists(filepath):
        return db
    try:
        if db_type == "gear":
            gears = parse_gear_rows(filepath)
            db = {g["Name"]: g for g in gears}
        elif db_type == "mini":
            minis = parse_mini_rows(filepath)
            db = {m["Name"]: m for m in minis}
    except Exception:
        pass
    return db


def load_all_minis_list(paths):
    return parse_mini_rows(resolve_stats_csv(paths, "Minis.csv"))


def load_all_gears_list(paths):
    return parse_gear_rows(resolve_stats_csv(paths, "Gears.csv"))


# --- Load Config and Calculate Stats ---
def get_fixed_stats(cfg):
    total_stats = empty_stats()

    gem_perfect = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
    gem_combo = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
    gem_f_mult = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
    gem_f_fill = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
    gem_f_time = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))

    total_stats["Perfect Points"] += gem_perfect * GEM_SCALE_NORMAL
    total_stats["Combo Multiplier"] += gem_combo * GEM_SCALE_NORMAL
    total_stats["Fever Multiplier"] += gem_f_mult * GEM_SCALE_FEVER
    total_stats["Fever Fill Rate"] += gem_f_fill * GEM_SCALE_FEVER
    total_stats["Fever Time"] += gem_f_time * GEM_SCALE_FEVER

    total_stats["Chill"] += gem_perfect * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Flow"] += gem_combo * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Rush"] += gem_f_mult * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Beat"] += gem_f_time * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Vibe"] += gem_f_fill * GEM_STAT_TO_ELEMENT_SCALE

    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    for el in elements:
        gem_val = safe_int(cfg.get("ElementalGems", el, fallback="0"))
        if gem_val > 0:
            total_stats[el] += gem_val * ELEMENTAL_GEM_SCALE

    team_buff = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback="").strip().upper()
    team_color = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip()
    buff_tiers = {
        "T1": {"PP": 25, "Elem": 35},
        "T5": {"PP": 25, "Elem": 30},
        "T10": {"PP": 20, "Elem": 25},
        "T15": {"PP": 15, "Elem": 20},
    }
    if team_buff in buff_tiers:
        buff_data = buff_tiers[team_buff]
        total_stats["Perfect Points"] += buff_data["PP"]
        valid_color_key = next((k for k in elements if k.lower() == team_color.lower()), None)
        if valid_color_key:
            total_stats[valid_color_key] += buff_data["Elem"]
        elif team_color:
            total_stats["Perfect Points"] += buff_data["PP"]
    return total_stats


def get_config_gear_stats(cfg, paths, gears_db=None):
    """
    Returns (gear_stats_dict, gear_list) from config.
    gears_db: optional dict {Name: stats}. If None, load from CSV.
    """
    if gears_db is None:
        gears_db = load_csv_db(resolve_stats_csv(paths, "Gears.csv"), "gear")

    gear_stats = empty_stats()
    gear_list = []
    gear_slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    for slot in gear_slots:
        key = "Pant" if slot == "Pants" else slot
        item_name = cfg.get("Gear", key, fallback=cfg.get("Gear", slot, fallback="")).strip().strip(" .")
        if item_name in gears_db:
            item_data = gears_db[item_name]
            if item_data.get("type", "Hat") == slot:
                gear_list.append(item_data)
                for k in gear_stats:
                    if k in item_data:
                        gear_stats[k] += item_data.get(k, 0)
        else:
            gear_list.append({"Name": "(Empty)", "type": slot})
    return gear_stats, gear_list


def get_config_mini_stats(cfg, paths, minis_db=None):
    """
    Returns (mini_stats_dict, mini_list) from config.
    minis_db: optional dict {Name: stats}. If None, load from CSV.
    """
    if minis_db is None:
        minis_db = load_csv_db(resolve_stats_csv(paths, "Minis.csv"), "mini")

    mini_stats = empty_stats()
    mini_list = []
    for i in range(1, 4):
        item_name = cfg.get("Minis", str(i), fallback="").strip().strip(" .")
        if item_name in minis_db:
            item_data = minis_db[item_name]
            mini_list.append(item_data)
            for k in mini_stats:
                if k in item_data:
                    mini_stats[k] += item_data.get(k, 0)
        else:
            mini_list.append({"Name": "(Empty)", "type": "Mini"})
    return mini_stats, mini_list


def load_force_greats_config(cfg):
    """
    Parse [ForceGreats] options into a list indexed by non-fever section (0-based).
    Keys follow the pattern NonFever{N}; missing values default to zero.
    """
    if not cfg or not cfg.has_section("ForceGreats"):
        return []
    entries = []
    try:
        for opt, raw in cfg.items("ForceGreats"):
            match = re.match(r"nonfever(\d+)", opt.strip().lower())
            if not match:
                continue
            idx = max(0, safe_int(match.group(1)) - 1)
            val = max(0, safe_int(raw, 0))
            entries.append((idx, val))
    except Exception:
        return []

    if not entries:
        return []

    max_idx = max(idx for idx, _ in entries)
    values = [0] * (max_idx + 1)
    for idx, val in entries:
        values[idx] = val
    return values


# --- Song Scanner ---
def scan_song_header(fp):
    meta = {"Song Name": "", "Primary Color": "", "Secondary Color": "", "Difficulty": ""}
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        return meta if meta["Song Name"] else None
    except Exception:
        return None


def read_song_file(fp):
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": [],
    }
    if not fp:
        return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        marker = next((i for i, l in enumerate(lines) if l.strip() == "Song Data"), -1)
        if marker == -1:
            return data
        for l in lines[:marker]:
            if not l.strip():
                continue
            parts = l.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"

        note_lines = []
        for l in lines[marker + 1:]:
            s = l.strip()
            if not s:
                continue
            c = s[0]
            if ("0" <= c <= "9") or c == ".":
                note_lines.append(l)

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
        return data
    except Exception:
        return data


# === JIT CALCULATION LOGIC ===
def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]


@jit(nopython=True, cache=True)
def lookup_reference_jit(value, ref_array, total_rows):
    idx = int(value)
    if idx > total_rows:
        idx = total_rows
    elif idx < 0:
        idx = 0
    return ref_array[idx]


@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    fever_mask_buffer,
):
    """
    Calculate fever timeline using corrected server-matching logic.
    
    Key fixes:
    1. First non-fever section: non_fever_base - 1 notes
       Later sections: non_fever_base notes (1 "wasted" note where fever ends)
    2. Binary search uses side="left" (>=) instead of side="right" (>)
    """
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0

    while current_note_idx < total_notes:
        # Non-fever section
        fever_section += 1
        # First section: -1, Later sections: use base (wasted note effect)
        if fever_section == 1:
            notes_to_fill = non_fever_base - 1
        else:
            notes_to_fill = non_fever_base
        
        end_normal_idx = min(current_note_idx + notes_to_fill, total_notes)
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = song_timestamps[current_note_idx]
            end_time = start_time + real_fever_time
            # Use side="left" to find first note where time >= end_time (not >)
            fever_end_idx = np.searchsorted(song_timestamps, end_time, side="left")
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = fever_end_idx
        else:
            break

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]:
                count_body_fever += 1
            else:
                count_body_normal += 1
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations


@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):
    """
    Fast JIT-compiled score calculation.
    
    NOTE: The old fever_activations_count adjustment has been REMOVED.
    The timeline calculation now correctly handles note allocation per fever cycle,
    so no adjustment is needed.
    """
    combo_val_per_note = floor(base_value * combo_mul)
    fever_val_per_note = floor(base_value * combo_mul * fever_mul)

    body_score = (count_body_fever * fever_val_per_note) + (
        count_body_normal * combo_val_per_note
    )

    # OLD PATCH REMOVED - no longer needed with corrected timeline

    factor = (combo_mul - 1) * base_value / 100.0
    total_head = 0.0
    n_head = len(fever_mask_head)

    for i in range(n_head):
        current_ramp_val = base_value + ((i + 1) * factor)
        if fever_mask_head[i]:
            val = floor(current_ramp_val * fever_mul)
        else:
            val = floor(current_ramp_val)
        total_head += val

    return int(body_score + total_head)


@jit(nopython=True, cache=True)
def optimize_core_jit(
    budget,
    cur_pp,
    cur_cm,
    cur_fm,
    cur_p_val,
    cur_s_val,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    ref_pp,
    ref_cm,
    ref_fm,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
):
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining_budget = budget

    while remaining_budget > 0:
        best_score = -1.0
        best_opt_idx = -1
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0

        # 0: PP
        if cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score >= best_score:
                best_score = score
                best_opt_idx = 0

        # 1: CM
        if cur_cm < MAX_STAT_INDEX:
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 1

        # 2: FM
        if cur_fm < MAX_STAT_INDEX:
            t_fm = cur_fm + GEM_SCALE_FEVER
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 2

        # 3: Overflow
        t_p = cur_p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = cur_s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
        base = (t_p * 2) + t_s + pp_factor
        c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
        score = fast_calculate_score(
            base,
            c_mul,
            f_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )
        if score >= best_score:
            best_score = score
            best_opt_idx = 3

        if best_opt_idx == 0:
            cur_pp += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt_idx == 1:
            cur_cm += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt_idx == 2:
            cur_fm += GEM_SCALE_FEVER
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            cur_p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            cur_s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        remaining_budget -= 1

    return (
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        gems_pp,
        gems_cm,
        gems_fm,
        gems_ov,
    )


# === WORKERS ===
def worker_coevolution_evaluate(args):
    """
    Evaluates a Co-Evolution Individual.
    
    Uses a stat-signature cache: if multiple gear+mini combinations produce
    the same effective stats for the song's Primary/Secondary/Selected paths,
    we reuse the gem solver result instead of recomputing.
    """
    (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays) = args

    current_stats = base_stats_fixed.copy()
    cs = current_stats
    cs_get = cs.get

    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                cs[k] = cs_get(k, 0) + v

    # Check stat-signature cache before calling the expensive gem solver.
    sel_color = cfg_data["selected_color"]
    sig = stats_signature(current_stats, calc_song, sel_color)
    cached = GEM_SOLVER_CACHE.get(sig)

    if cached is None:
        res = solve_best_fever_combination(
            None,
            current_stats,
            calc_song,
            ref_arrays,
            silent=True,
            override_cfg=cfg_data,
        )
        GEM_SOLVER_CACHE[sig] = res
    else:
        res = cached

    gear_part = genome[:6]
    mini_part = genome[6:]
    mini_names = [m["Name"] for m in mini_part]

    return {
        "Score": res["Score"],
        "Genome": genome,
        "Gear": gear_part,
        "Minis": mini_part,
        "MiniNames": mini_names,
        "Data": res,
    }


# === SOLVERS ===
def evaluate_stats_score(
    stats,
    calc_song,
    ref_arrays,
    song_timestamps=None,
    long_notes=None,
    last_note=None,
    fever_mask_buffer=None,
):
    """Return total score for a fixed stats snapshot without reallocations."""
    timestamps = (
        song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    )
    total_notes = len(timestamps)
    long_count = (
        long_notes if long_notes is not None else int(calc_song["metadata"].get("Long Notes", 0))
    )
    last_time = (
        last_note
        if last_note is not None
        else float(calc_song["metadata"].get("Last Note Time", 0))
    )
    mask_buffer = fever_mask_buffer
    if mask_buffer is None or mask_buffer.shape[0] != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ft_factor = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_mask_head, count_body_fever, count_body_normal, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_count,
        last_time,
        mask_buffer,
    )

    base_pp = lookup_reference_py(stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    primary_val = stats.get(p_color, 0)
    secondary_val = stats.get(s_color, 0)
    total_base = (primary_val * 2) + secondary_val + base_pp

    return fast_calculate_score(
        total_base,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )


def _force_greats_counts_to_dict(counts, sections):
    config = {}
    for idx in range(sections):
        val = counts[idx] if idx < len(counts) else 0
        config[f"NonFever{idx + 1}"] = max(0, int(val))
    return config


def build_great_penalty_table(base_value, combo_mul, great_penalty_base, head_limit=100):
    """
    Precompute ramp penalties for the first `head_limit` notes.
    Avoids recalculating scaling when evaluating force-great permutations.
    """
    penalties = [0] * head_limit
    combo_span = combo_mul - 1.0
    for idx in range(head_limit):
        scaling = 1.0 + combo_span * (idx + 1) / 100.0
        perfect_val = floor(base_value * scaling)
        great_val = floor(great_penalty_base * scaling)
        penalties[idx] = max(0, perfect_val - great_val)
    return penalties


def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """
    Recompute fever timeline and penalties when greats are forced in non-fever sections.
    Returns None when prerequisites are missing.
    """
    if not stats or not calc_song:
        return None

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = int(metadata.get("Long Notes", 0))
    last_note_time = float(metadata.get("Last Note Time", timestamps[-1] if total_notes else 0.0))
    primary_color = metadata.get("Primary Color", "")
    secondary_color = metadata.get("Secondary Color", "")
    primary_val = stats.get(primary_color, 0)
    secondary_val = stats.get(secondary_color, 0)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    pp_factor = lookup_reference_py(stats["Perfect Points"], ref_pp, TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_cm, TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_fm, TOTAL_ROWS)
    fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_ft, TOTAL_ROWS)

    base_value = (primary_val * 2) + secondary_val + pp_factor
    combo_value = floor(base_value * combo_mul)
    great_penalty_base = floor(((primary_val * 2) + secondary_val) * (2.0 / 3.0) + 150.0)
    great_combo_value = floor(great_penalty_base * combo_mul)
    penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base)
    body_penalty = max(0, combo_value - great_combo_value)

    non_fever_cas = max(0.0, (total_notes - long_notes) * 0.333)
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    non_fever_great_to_fill = ceil(max(1.0, (non_fever_cas * fever_fill_rate) * 2.0))
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    force_counts = list(forced_counts or [])
    fever_mask = np.zeros(total_notes, dtype=np.bool_)
    current_idx = 0
    non_fever_section = 0
    section_details = []

    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        base_notes = max(0, base_notes)
        forced_val = 0
        if non_fever_section - 1 < len(force_counts):
            forced_val = max(0, int(force_counts[non_fever_section - 1]))
        forced_val = min(forced_val, non_fever_base)
        fill_penalty_notes = ceil(
            max(0.0, (non_fever_base * forced_val) / non_fever_great_to_fill)
        )
        notes_to_fill = base_notes + fill_penalty_notes
        section_start = current_idx
        end_normal = min(section_start + notes_to_fill, total_notes)
        actual_notes = max(0, end_normal - section_start)
        forced_applied = min(forced_val, actual_notes)

        section_details.append(
            {
                "start_idx": section_start,
                "notes": actual_notes,
                "forced": forced_applied,
                "fill_penalty_notes": fill_penalty_notes,
                "skip_wasted": (non_fever_section == 1),
            }
        )
        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_time = timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        fever_mask[current_idx:fever_end_idx] = True
        current_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    fever_mask_head = fever_mask[:head_limit]
    if total_notes > 100:
        body_slice = fever_mask[100:]
        count_body_fever = int(np.count_nonzero(body_slice))
        count_body_normal = max(len(body_slice) - count_body_fever, 0)
    else:
        count_body_fever = 0
        count_body_normal = 0

    base_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )

    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis = {}
    for idx, detail in enumerate(section_details):
        section_key = f"NonFever{idx + 1}"
        fill_penalty_score = detail["fill_penalty_notes"] * combo_value
        total_fill_penalty += fill_penalty_score
        forced = detail["forced"]
        if forced > 0:
            start_idx = detail["start_idx"]
            if detail.get("skip_wasted"):
                start_idx = min(total_notes, start_idx + 1)
            score_penalty = 0
            note_idx = start_idx
            remaining = forced
            while remaining > 0:
                if note_idx < len(penalty_table):
                    score_penalty += penalty_table[note_idx]
                else:
                    score_penalty += body_penalty
                note_idx += 1
                remaining -= 1
        else:
            score_penalty = 0
        total_score_penalty += score_penalty
        penalty_analysis[section_key] = {
            "forced_greats": forced,
            "score_penalty": score_penalty,
            "fill_penalty": fill_penalty_score,
            "total_penalty": score_penalty + fill_penalty_score,
        }

    used_counts = force_counts[:]
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))

    return {
        "base_score": base_score,
        "final_score": max(0, base_score - total_score_penalty),
        "score_penalty": total_score_penalty,
        "fill_penalty": total_fill_penalty,
        "total_penalty": total_score_penalty + total_fill_penalty,
        "num_non_fever_sections": len(section_details),
        "config_counts": used_counts[: len(section_details)],
        "config_dict": _force_greats_counts_to_dict(used_counts, len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": non_fever_base,
    }


def run_force_greats_hill_climb(stats, calc_song, ref_arrays):
    """
    Simple hill-climb optimizer that increments forced greats per section
    while the total score improves.
    """
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, [])
    if not baseline:
        return None

    best_counts = [0] * baseline["num_non_fever_sections"]
    best_result = evaluate_force_greats(stats, calc_song, ref_arrays, best_counts)
    if not best_result or best_result["num_non_fever_sections"] == 0:
        return best_result

    improved = True
    while improved:
        improved = False
        for idx in range(best_result["num_non_fever_sections"]):
            candidate_counts = best_counts[:]
            if idx >= len(candidate_counts):
                candidate_counts.extend([0] * (idx + 1 - len(candidate_counts)))
            candidate_counts[idx] += 1
            candidate = evaluate_force_greats(stats, calc_song, ref_arrays, candidate_counts)
            if candidate and candidate["final_score"] > best_result["final_score"]:
                best_counts = candidate_counts
                best_result = candidate
                improved = True
                break
    return best_result


def apply_force_greats_to_result(
    data_dict,
    calc_song,
    ref_arrays,
    manual_counts=None,
    use_finder=False,
):
    """
    Evaluate forced-great penalties (manual config or hill-climb finder) for a result dict.
    Returns a cloned variant with the adjusted score while leaving the original untouched.
    """
    if not data_dict or "Stats" not in data_dict:
        return None

    stats = data_dict.get("Stats") or {}
    if not stats:
        return None

    if use_finder:
        fg_result = run_force_greats_hill_climb(stats, calc_song, ref_arrays)
    else:
        fg_result = evaluate_force_greats(stats, calc_song, ref_arrays, manual_counts)

    if not fg_result:
        return None

    fg_info = {
        "enabled": True,
        "config": fg_result["config_dict"],
        "base_score": fg_result["base_score"],
        "final_score": fg_result["final_score"],
        "score_penalty": fg_result["score_penalty"],
        "fill_penalty": fg_result["fill_penalty"],
        "total_penalty": fg_result["total_penalty"],
        "num_non_fever_sections": fg_result["num_non_fever_sections"],
        "penalty_analysis": fg_result["penalty_analysis"],
    }

    data_dict["ForceGreats"] = fg_info

    fg_variant = copy.deepcopy(data_dict)
    fg_variant["Score"] = fg_result["final_score"]
    fg_variant["ForceGreats"] = fg_info.copy()
    fg_variant["ForceGreats"]["variant_applied"] = True
    return fg_variant


def solve_best_fever_combination(
    cfg,
    initial_stats,
    calc_song,
    ref_arrays,
    silent=False,
    override_cfg=None,
    skip_optimizer=False,
):
    if override_cfg:
        user_ft = override_cfg["user_ft"]
        user_ff = override_cfg["user_ff"]
        user_pp = override_cfg["user_pp"]
        user_cm = override_cfg["user_cm"]
        user_fm = override_cfg["user_fm"]
        selected_color = override_cfg["selected_color"]
        static_elem_input = override_cfg["static_elem_input"]
    else:
        if not silent:
            print("\n=== STARTING FEVER ITERATION ENGINE (GEM SOLVER) ===")
        user_ft = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))
        user_ff = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
        user_pp = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
        user_cm = safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        )
        user_fm = safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        )
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        static_elem_input = safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        )

    base_stats = initial_stats.copy()

    # OPTIMIZATION: timestamps are already a NumPy array (set in __main__)
    song_timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(song_timestamps)
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note = float(calc_song["metadata"].get("Last Note Time", 0))
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")

    # Reuse mask buffer across FT/FF permutations to avoid repeated allocations.
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ft = ref_arrays["Fever Time"]
    ref_ff = ref_arrays["Fever Fill Rate"]

    if skip_optimizer:
        score = evaluate_stats_score(
            base_stats,
            calc_song,
            ref_arrays,
            song_timestamps=song_timestamps,
            long_notes=long_notes,
            last_note=last_note,
            fever_mask_buffer=fever_mask_buffer,
        )
        return {
            "Score": score,
            "FT": user_ft,
            "FF": user_ff,
            "GemCounts": {
                "Perfect Points": user_pp,
                "Combo Multiplier": user_cm,
                "Fever Multiplier": user_fm,
                "Element Overflow": static_elem_input,
            },
            "Stats": base_stats,
            "Selected Element": selected_color,
        }

    base_stats["Fever Time"] -= user_ft * GEM_SCALE_FEVER
    base_stats["Beat"] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Fill Rate"] -= user_ff * GEM_SCALE_FEVER
    base_stats["Vibe"] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Multiplier"] -= user_fm * GEM_SCALE_FEVER
    base_stats["Rush"] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Combo Multiplier"] -= user_cm * GEM_SCALE_NORMAL
    base_stats["Flow"] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Perfect Points"] -= user_pp * GEM_SCALE_NORMAL
    base_stats["Chill"] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE
    base_stats[selected_color] -= static_elem_input * ELEMENTAL_GEM_SCALE

    remaining_ft_stat = MAX_STAT_INDEX - base_stats["Fever Time"]
    remaining_ff_stat = MAX_STAT_INDEX - base_stats["Fever Fill Rate"]
    max_ft_gems = floor(remaining_ft_stat / GEM_SCALE_FEVER) if remaining_ft_stat > 0 else 0
    max_ff_gems = floor(remaining_ff_stat / GEM_SCALE_FEVER) if remaining_ff_stat > 0 else 0

    if not silent:
        print(f"Max allocatable Gems: FT<={max_ft_gems}, Fill<={max_ff_gems}")
        print("Iterating permutations...")

    best_score = -1
    best_tuple = None

    range_ft = min(TOTAL_GEM_BUDGET, max_ft_gems)

    is_p_pp = 1 if "Chill" == p_color else 0
    is_s_pp = 1 if "Chill" == s_color else 0
    is_p_cm = 1 if "Flow" == p_color else 0
    is_s_cm = 1 if "Flow" == s_color else 0
    is_p_fm = 1 if "Rush" == p_color else 0
    is_s_fm = 1 if "Rush" == s_color else 0
    is_p_ov = 1 if selected_color == p_color else 0
    is_s_ov = 1 if selected_color == s_color else 0

    base_beat = base_stats.get("Beat", 0)
    base_vibe = base_stats.get("Vibe", 0)

    bs_get = base_stats.get

    def get_val_inline(k, b, v):
        if k == "Beat":
            return b
        if k == "Vibe":
            return v
        return bs_get(k, 0)

    cur_pp = base_stats["Perfect Points"]
    cur_cm = base_stats["Combo Multiplier"]
    cur_fm = base_stats["Fever Multiplier"]

    base_ft_stat = base_stats["Fever Time"]
    base_ff_stat = base_stats["Fever Fill Rate"]

    song_cache_key = (
        calc_song["metadata"].get("Song Name", ""),
        total_notes,
        long_notes,
        round(last_note, 5),
    )
    song_timeline_cache = FEVER_TIMELINE_CACHE.setdefault(song_cache_key, {})

    # OPTIMIZATION: precompute FT/FF reference lookups
    ft_stat_table = [
        base_ft_stat + (ft_val * GEM_SCALE_FEVER) for ft_val in range(range_ft + 1)
    ]
    ft_factor_table = [
        lookup_reference_py(stat, ref_ft, TOTAL_ROWS) for stat in ft_stat_table
    ]

    ff_stat_table = [
        base_ff_stat + (ff_val * GEM_SCALE_FEVER) for ff_val in range(max_ff_gems + 1)
    ]
    ff_factor_table = [
        lookup_reference_py(stat, ref_ff, TOTAL_ROWS) for stat in ff_stat_table
    ]

    # Cache timelines per (ft, ff) combo for this song/config to avoid recomputing.

    for ft in range(range_ft + 1):
        remaining_for_ff = TOTAL_GEM_BUDGET - ft
        range_ff = min(remaining_for_ff, max_ff_gems)

        stat_ft_val = ft_stat_table[ft]
        ft_factor = ft_factor_table[ft]
        cur_beat = base_beat + (ft * GEM_STAT_TO_ELEMENT_SCALE)

        for ff in range(range_ff + 1):
            current_budget = TOTAL_GEM_BUDGET - ft - ff
            stat_ff_val = ff_stat_table[ff]
            ff_factor = ff_factor_table[ff]

            cache_key = (stat_ft_val, stat_ff_val)
            cached_timeline = song_timeline_cache.get(cache_key)
            if cached_timeline:
                (
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    fever_activations,
                ) = cached_timeline
            else:
                (
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    fever_activations,
                ) = calculate_fever_timeline_indices(
                    song_timestamps,
                    total_notes,
                    ff_factor,
                    ft_factor,
                    long_notes,
                    last_note,
                    fever_mask_buffer,
                )
                # Copy the head slice so the shared buffer can be reused safely.
                if len(song_timeline_cache) < MAX_TIMELINE_CACHE_PER_SONG:
                    song_timeline_cache[cache_key] = (
                        fever_mask_head.copy(),
                        count_body_fever,
                        count_body_normal,
                        fever_activations,
                    )

            cur_vibe = base_vibe + (ff * GEM_STAT_TO_ELEMENT_SCALE)

            cur_p_val = get_val_inline(p_color, cur_beat, cur_vibe)
            cur_s_val = get_val_inline(s_color, cur_beat, cur_vibe)

            (
                final_pp,
                final_cm,
                final_fm,
                final_p_val,
                final_s_val,
                g_pp,
                g_cm,
                g_fm,
                g_ov,
            ) = optimize_core_jit(
                current_budget,
                cur_pp,
                cur_cm,
                cur_fm,
                cur_p_val,
                cur_s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_pp,
                ref_cm,
                ref_fm,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_ROWS,
                MAX_STAT_INDEX,
            )

            base = (final_p_val * 2) + final_s_val + lookup_reference_py(
                final_pp, ref_pp, TOTAL_ROWS
            )
            c_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)
            total_score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )

            if total_score > best_score:
                best_score = total_score
                best_tuple = (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)

    if best_tuple:
        (score, ft, ff, g_pp, g_cm, g_fm, g_ov) = best_tuple
        final_stats = base_stats.copy()
        final_stats["Fever Time"] += ft * GEM_SCALE_FEVER
        final_stats["Fever Fill Rate"] += ff * GEM_SCALE_FEVER

        final_stats["Perfect Points"] += g_pp * GEM_SCALE_NORMAL
        final_stats["Combo Multiplier"] += g_cm * GEM_SCALE_NORMAL
        final_stats["Fever Multiplier"] += g_fm * GEM_SCALE_FEVER

        final_stats["Chill"] += g_pp * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Flow"] += g_cm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Rush"] += g_fm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Beat"] = base_stats.get("Beat", 0) + (
            ft * GEM_STAT_TO_ELEMENT_SCALE
        )
        final_stats["Vibe"] = base_stats.get("Vibe", 0) + (
            ff * GEM_STAT_TO_ELEMENT_SCALE
        )

        if selected_color in final_stats:
            final_stats[selected_color] += g_ov * ELEMENTAL_GEM_SCALE

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element Overflow": g_ov,
        }
        return {
            "Score": score,
            "FT": ft,
            "FF": ff,
            "GemCounts": gem_counts,
            "Stats": final_stats,
            "Selected Element": selected_color,
        }

    return {}


def solve_coevolution_genetic(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    ga_depth=75,
    db_seed=None,
    status_cb=None,
    executor=None,
):
    # Clear per-song caches to prevent unbounded memory growth across songs.
    GEM_SOLVER_CACHE.clear()

    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    selected_color = p_color

    mini_pool = [m for m in all_minis if m.get(p_color, 0) > 0]
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], []

    # Pre-compute mini name set for faster candidate filtering in crossover/mutation.
    mini_pool_names = frozenset(m["Name"] for m in mini_pool)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)

    # Apply dominance pruning per slot to remove strictly inferior gear.
    total_before = sum(len(gear_pool[s]) for s in slots)
    for s in slots:
        gear_pool[s] = prune_dominated_gear(gear_pool[s])
    total_after = sum(len(gear_pool[s]) for s in slots)
    if total_before > total_after:
        print(f"[Dominance Pruning] Removed {total_before - total_after} dominated gear items.")

    cfg_data = {
        "selected_color": selected_color,
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        ),
        "user_fm": safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        ),
        "static_elem_input": safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        ),
    }

    db_seed_prob = (
        safe_float(cfg.get("IterationEngine", "GA_DBSeedProbability", fallback=0.5))
        if cfg
        else 0.5
    )
    db_seed_prob = min(1.0, max(0.0, db_seed_prob))
    fixed_seed_copies = (
        safe_int(cfg.get("IterationEngine", "GA_FixedSeedCopies", fallback=2))
        if cfg
        else 2
    )
    fixed_seed_copies = max(0, fixed_seed_copies)

    # --- MEMETIC GA PARAMETERS (configurable from [IterationEngine]) ---
    memetic_elites = (
        safe_int(cfg.get("IterationEngine", "GA_MemeticElites", fallback=4))
        if cfg
        else 4
    )
    if memetic_elites < 0:
        memetic_elites = 0

    memetic_steps = (
        safe_int(cfg.get("IterationEngine", "GA_MemeticSteps", fallback=2))
        if cfg
        else 2
    )
    if memetic_steps < 0:
        memetic_steps = 0

    memetic_top_gear = (
        safe_int(cfg.get("IterationEngine", "GA_MemeticTopGear", fallback=4))
        if cfg
        else 4
    )
    if memetic_top_gear <= 0:
        memetic_top_gear = 1

    memetic_top_minis = (
        safe_int(cfg.get("IterationEngine", "GA_MemeticTopMinis", fallback=12))
        if cfg
        else 12
    )
    if memetic_top_minis <= 0:
        memetic_top_minis = 1

    if memetic_elites > 0 and memetic_steps > 0:
        print(
            f"[Memetic GA] Enabled: elites={memetic_elites}, "
            f"steps={memetic_steps}, top_gear={memetic_top_gear}, "
            f"top_minis={memetic_top_minis}"
        )
    else:
        print("[Memetic GA] Disabled (elites or steps <= 0).")

    def score_candidate(x):
        return (
            x.get(p_color, 0) * 3
            + x.get("Perfect Points", 0) * 2
            + x.get("Combo Multiplier", 0) * 2
            + x.get("Fever Multiplier", 0) * 2
        )

    gear_rank_max = 10  # keep gear sweep tight to avoid huge branching
    mini_rank_max = 40  # widen minis to escape local minima
    gear_rank_cache = {
        s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:gear_rank_max]
        for s in slots
    }
    mini_rank_cache = sorted(mini_pool, key=score_candidate, reverse=True)[
        :mini_rank_max
    ]

    def genome_key(genome):
        # Gear (first 6 slots): order matters because slots are positional.
        gear_names = tuple(item.get("Name", "") for item in genome[:6])
        # Minis (last 3 slots): order-invariant - only the set/multiset matters.
        # Sorting canonicalizes permutations so [A,B,C] and [C,B,A] share a key.
        mini_names = tuple(sorted(item.get("Name", "") for item in genome[6:]))
        return gear_names + mini_names

    evaluation_cache = {}

    def evaluate_genome_local(genome):
        k = genome_key(genome)
        if k in evaluation_cache:
            return evaluation_cache[k]
        res = worker_coevolution_evaluate(
            (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        evaluation_cache[k] = res
        return res

    def create_random_genome():
        genome = []
        if optimize_gear:
            for s in slots:
                genome.append(random.choice(gear_pool[s]) if gear_pool[s] else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_pool) >= 3:
                genome.extend(random.sample(mini_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9:
                    genome.append({})
        else:
            genome.extend(fixed_minis)
        return genome

    def create_heuristic_genome():
        genome = []
        if optimize_gear:
            for s in slots:
                candidates = gear_rank_cache.get(s, [])
                genome.append(random.choice(candidates[:5]) if candidates else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_rank_cache) >= 3:
                genome.extend(random.sample(mini_rank_cache[:10], 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    def reconstruct_genome_from_db_list(db_list):
        """Rebuilds full stats from just the names in the DB."""
        r_genome = []
        for i in range(6):
            name = db_list[i] if i < len(db_list) else ""
            if name in gears_by_name:
                r_genome.append(gears_by_name[name])
            else:
                r_genome.append({"Name": "(Empty)", "type": slots[i]})
        for i in range(6, 9):
            if i < len(db_list):
                name = db_list[i]
                if name in minis_by_name:
                    r_genome.append(minis_by_name[name])
                else:
                    r_genome.append({"Name": "(Empty)", "type": "Mini"})
            else:
                r_genome.append({"Name": "(Empty)", "type": "Mini"})
        return r_genome

    def build_seed_list_from_record(record):
        """
        Normalize any stored record into a compact list of names for seeding.
        Priority: legacy loadout -> gear + minis.
        """
        if not record:
            return None
        if "loadout" in record:
            load = record.get("loadout") or []
            if isinstance(load, list):
                return load
        gear_names = record.get("gear") or []
        mini_names = record.get("minis") or []
        if gear_names or mini_names:
            return list(gear_names) + list(mini_names)
        return None

    def mutate_genome_once(genome):
        """Soft mutation around a seed genome for DB seeding."""
        g = list(genome)
        mutate_idx = random.randint(0, 8)

        if mutate_idx < 6 and optimize_gear:
            slot_type = slots[mutate_idx]
            if gear_pool[slot_type]:
                g[mutate_idx] = random.choice(gear_pool[slot_type])
        elif mutate_idx >= 6 and optimize_minis:
            current_mini_names = {m.get("Name") for m in g[6:] if isinstance(m, dict)}
            candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
            if candidates:
                g[mutate_idx] = random.choice(candidates)

        return g

    def build_initial_population():
        population = []
        seed_list = build_seed_list_from_record(db_seed)
        if seed_list and random.random() < db_seed_prob:
            try:
                print(
                    f" >> [Evolution] Injecting previous best (Score: {db_seed.get('score', 0)})"
                )
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                population.append(seed_genome[:])
                population.append(mutate_genome_once(seed_genome))
            except Exception as e:
                print(f" >> [Evolution] Failed to inject seed: {e}")
        elif seed_list:
            print(" >> [Evolution] Skipping DB seed this run (probability gate).")

        if fixed_gear and fixed_minis:
            seed_genome = fixed_gear + fixed_minis
            for _ in range(fixed_seed_copies):
                population.append(seed_genome[:])

        for _ in range(10):
            population.append(create_heuristic_genome())

        while len(population) < GA_POPULATION_SIZE:
            population.append(create_random_genome())
        return population

    def polish_best_genome(best_genome):
        """Local sweep on top candidates per slot/mini to escape near-misses."""
        top_k_gear = 8
        top_k_minis = min(25, len(mini_rank_cache))
        gear_rank = {s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots}
        mini_rank = mini_rank_cache[:top_k_minis]

        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]

        improved = True
        while improved:
            improved = False
            # Gear sweep (one slot at a time)
            if optimize_gear:
                for idx, slot in enumerate(slots):
                    current_name = best_genome[idx].get("Name")
                    for cand in gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            break
                    if improved:
                        break
            if improved:
                continue

            # Mini sweep (respect unique minis)
            if optimize_minis:
                # Compute existing mini names once per sweep iteration.
                existing = {m.get("Name") for m in best_genome[6:] if isinstance(m, dict)}
                for idx in range(6, 9):
                    curr_name = best_genome[idx].get("Name")
                    for cand in mini_rank:
                        c_name = cand.get("Name")
                        if c_name == curr_name:
                            continue
                        if c_name in existing - {curr_name}:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            break
                    if improved:
                        break

        return best_result, best_genome

    # --- MEMETIC LOCAL SEARCH (lightweight) ---
    def memetic_local_search(start_genome, max_steps, top_k_gear, top_k_minis):
        """
        Lightweight local search around a genome.
        Performs up to max_steps improving moves over gear/minis,
        using ranked candidates and the shared evaluation cache.
        """
        if max_steps <= 0:
            return evaluate_genome_local(start_genome)

        best_genome = list(start_genome)
        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]

        # Pre-trim candidate lists for this memetic search
        local_gear_rank = {
            s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
        }
        local_mini_rank = mini_rank_cache[:top_k_minis]

        steps = 0
        while steps < max_steps:
            improved = False

            # Gear neighbourhood (if optimizing gear)
            if optimize_gear:
                for idx, slot in enumerate(slots):
                    current_name = best_genome[idx].get("Name")
                    for cand in local_gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or steps >= max_steps:
                        break

            if steps >= max_steps:
                break

            # Mini neighbourhood (if optimizing minis)
            if not improved and optimize_minis:
                # Compute existing mini names once per neighbourhood iteration.
                existing = {m.get("Name") for m in best_genome[6:] if isinstance(m, dict)}
                for idx in range(6, 9):
                    curr_name = best_genome[idx].get("Name")
                    for cand in local_mini_rank:
                        c_name = cand.get("Name")
                        if c_name == curr_name:
                            continue
                        if c_name in existing - {curr_name}:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or steps >= max_steps:
                        break

            if not improved:
                break

        return best_result

    num_runs = max(
        1,
        safe_int(cfg.get("IterationEngine", "GA_MultiStart", fallback=GA_MULTI_RUNS_DEFAULT))
        if cfg
        else GA_MULTI_RUNS_DEFAULT,
    )
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    print(f"Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

    best_global_score = -1
    best_global_genome = []
    best_global_data = {}

    for run_idx in range(num_runs):
        print(f"\n--- GA Run {run_idx + 1}/{num_runs} ---")
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")
        population = build_initial_population()
        last_improvement_gen = 0
        stagnation_limit = max(8, gens_per_run // 2)
        mutation_rate = GA_MUTATION_RATE

        for generation in range(1, gens_per_run + 1):
            key_to_genome = {}
            pending_keys = []
            tasks = []
            for genome in population:
                k = genome_key(genome)
                if k in key_to_genome:
                    continue
                key_to_genome[k] = genome
                if k not in evaluation_cache:
                    pending_keys.append(k)
                    tasks.append((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))

            if pending_keys:
                if executor:
                    worker_count = getattr(executor, "_max_workers", None) or (
                        os.cpu_count() or 1
                    )
                    chunk = max(1, len(tasks) // (worker_count * 4))
                    for k, res in zip(
                        pending_keys,
                        executor.map(
                            worker_coevolution_evaluate, tasks, chunksize=chunk
                        ),
                    ):
                        evaluation_cache[k] = res
                else:
                    for k, payload in zip(pending_keys, tasks):
                        evaluation_cache[k] = worker_coevolution_evaluate(payload)

            results = [evaluation_cache[genome_key(g)] for g in population]
            results.sort(key=lambda x: x["Score"], reverse=True)

            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if (cand_score > best_global_score) or (
                    cand_score == best_global_score and cand_key != best_key
                ):
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return True
                return False

            promoted = consider_candidate(results[0])

            if promoted:
                m_names = results[0]["MiniNames"]
                print(
                    f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})"
                )
                if status_cb:
                    status_cb(
                        f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}"
                    )
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): Best {results[0]['Score']}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: Best {results[0]['Score']}"
                        )

            # --- MEMETIC GA STEP: local search on top elites ---
            if memetic_elites > 0 and memetic_steps > 0:
                elite_count = min(memetic_elites, len(results))
                for e_idx in range(elite_count):
                    base_res = results[e_idx]
                    improved_res = memetic_local_search(
                        base_res["Genome"],
                        memetic_steps,
                        memetic_top_gear,
                        memetic_top_minis,
                    )
                    if improved_res["Score"] > base_res["Score"]:
                        results[e_idx] = improved_res
                        # Feed improved candidate back into global tracking
                        if consider_candidate(improved_res):
                            m_names = improved_res["MiniNames"]
                            print(
                                f"  >> [Memetic] Gen {generation} "
                                f"(Run {run_idx + 1}): New Best {best_global_score} "
                                f"(Minis: {m_names})"
                            )
                            if status_cb:
                                status_cb(
                                    f"Run {run_idx + 1}/{num_runs} Gen {generation} "
                                    f"Memetic: New Best {best_global_score}"
                                )
                            last_improvement_gen = generation
                            mutation_rate = GA_MUTATION_RATE
                # resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            next_gen = [results[i]["Genome"] for i in range(GA_ELITISM)]

            while len(next_gen) < GA_POPULATION_SIZE:
                if random.random() < 0.18:
                    next_gen.append(create_random_genome())
                    continue

                p1 = random.choice(results[:50])["Genome"]
                p2 = random.choice(results[:50])["Genome"]

                child = []
                L = min(len(p1), len(p2))
                for i in range(L):
                    child.append(p1[i] if random.random() > 0.5 else p2[i])

                child_gear = child[:6]
                child_minis = child[6:]

                seen_names = set()
                unique_minis = []
                for m in child_minis:
                    name = m.get("Name", None) if isinstance(m, dict) else None
                    if name and name not in seen_names and name != "(Empty)":
                        unique_minis.append(m)
                        seen_names.add(name)

                if optimize_minis:
                    while len(unique_minis) < 3:
                        candidates = [m for m in mini_pool if m["Name"] not in seen_names]
                        if candidates:
                            new_m = random.choice(candidates)
                            unique_minis.append(new_m)
                            seen_names.add(new_m["Name"])
                        else:
                            break
                else:
                    # Shallow copy suffices; minis are read-only dicts.
                    unique_minis = list(fixed_minis)

                child = child_gear + unique_minis

                if random.random() < mutation_rate:
                    mutate_idx = random.randint(0, 8)
                    if mutate_idx < 6 and optimize_gear:
                        slot_type = slots[mutate_idx]
                        if gear_pool[slot_type]:
                            child[mutate_idx] = random.choice(gear_pool[slot_type])
                    elif mutate_idx >= 6 and optimize_minis:
                        current_mini_names = {
                            m.get("Name") for m in child[6:] if isinstance(m, dict)
                        }
                        candidates = [
                            m for m in mini_pool if m["Name"] not in current_mini_names
                        ]
                        if candidates:
                            child[mutate_idx] = random.choice(candidates)

                next_gen.append(child)

            population = next_gen

            if generation - last_improvement_gen >= stagnation_limit:
                mutation_rate = min(GA_MUTATION_RATE_MAX, mutation_rate + 0.08)
                print(
                    f"  >> Stagnation detected (Run {run_idx + 1}), mutation -> {mutation_rate:.3f}, injecting diversity"
                )
                elites = [r["Genome"] for r in results[:GA_ELITISM]]
                population = elites[:]
                reinject_target = int(GA_POPULATION_SIZE * 0.4)
                while len(population) < reinject_target:
                    population.append(create_random_genome())
                while len(population) < GA_POPULATION_SIZE:
                    population.append(create_heuristic_genome())
                last_improvement_gen = generation

    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)
        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    best_gear = best_global_genome[:6] if best_global_genome else []
    best_minis = best_global_genome[6:] if best_global_genome else []

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
    )


def process_song_task(args):
    """
    Run a single song end-to-end.
    Optionally spins a local worker pool to parallelize inner GA work.
    """
    (
        fp,
        found_song_name,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        prev_record,
        status_queue,
        parallel_workers,
    ) = args

    # Optional local pool for single-song runs to saturate available cores.
    local_executor = None
    if parallel_workers:
        worker_count = min(parallel_workers, os.cpu_count() or 1)
        if worker_count > 1:
            local_executor = concurrent.futures.ProcessPoolExecutor(
                max_workers=worker_count,
                mp_context=multiprocessing.get_context("spawn"),
            )

    buf = StringIO()
    tee = Tee(sys.stdout, buf)
    try:
        with contextlib.redirect_stdout(tee):
            best_data = None
            best_gear = []
            best_minis = []
            db_payload = None

        cfg = cfg_from_dict(cfg_dict)

        # MetaFinder controls all optimizers collectively.
        meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
        enable_fever = enable_mini = enable_gear = bool(meta_finder)

        force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
        force_greats_config = load_force_greats_config(cfg)
        manual_force_greats = any(force_greats_config)

        song_data = read_song_file(fp)

        # OPTIMIZATION: store timestamps as NumPy array once per song
        song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)

        calc_song = {
            "metadata": song_data["song_details"],
            "song_data": {"timestamps": song_timestamps_np},
        }
        meta_primary_color = calc_song["metadata"].get("Primary Color", "")
        meta_secondary_color = calc_song["metadata"].get("Secondary Color", "")

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

        # --- DB KEY MODIFICATION ---
        # User requested removal of suffix (e.g. _Hard_Vibe).
        # The key is now strictly the Song Name found in the file header.
        db_key = found_song_name

        # Only seed GA if UseEvolutionDB=TRUE
        db_seed = prev_record if use_evo_db else None

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")

        attempt_lifetime_prev = 0
        if prev_record:
            attempt_lifetime_prev = (
                prev_record.get("attempt_lifetime")
                or prev_record.get("attempts")
                or 0
            )
        attempt_lifetime = attempt_lifetime_prev + 1
        prev_attempts_first = prev_record.get("attempts_first", 0) if prev_record else 0

        def emit(msg):
            if status_queue:
                try:
                    status_queue.put(f"[{found_song_name}] {msg}")
                except Exception:
                    pass

        emit("START")

        # --- LOGIC BRANCHING BASED ON FINDERS ---
        if enable_gear or enable_mini:
            # Run Genetic Algorithm (now memetic-enhanced)
            (
                best_data,
                best_gear,
                best_minis,
                _,
                _,
                _,
            ) = solve_coevolution_genetic(
                cfg,
                fixed_stats,
                paths,
                calc_song,
                ref_arrays,
                all_gears,
                all_minis,
                gears_by_name,
                minis_by_name,
                optimize_gear=enable_gear,
                optimize_minis=enable_mini,
                fixed_gear=current_gear_list,
                fixed_minis=current_mini_list,
                ga_depth=ga_depth,
                db_seed=db_seed,
                status_cb=lambda m: emit(m),
                executor=local_executor,
            )

        elif enable_fever:
            # Run ONLY Gem Solver
            combined_stats = fixed_stats.copy()
            for k, v in current_gear_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v
            for k, v in current_mini_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v

            best_data = solve_best_fever_combination(
                cfg,
                combined_stats,
                calc_song,
                ref_arrays,
            )
            best_gear = current_gear_list
            best_minis = current_mini_list
        else:
            # No finders enabled - just calculate score with current config
            print("[Calculate-Only Mode] MetaFinder disabled - calculating score with current config...")
            combined_stats = fixed_stats.copy()
            for k, v in current_gear_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v
            for k, v in current_mini_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v

            best_data = solve_best_fever_combination(
                cfg,
                combined_stats,
                calc_song,
                ref_arrays,
                silent=False,
                skip_optimizer=True,
            )
            best_gear = current_gear_list
            best_minis = current_mini_list

        fg_variants = []
        if manual_force_greats or force_greats_finder:
            manual_counts = (
                force_greats_config if (manual_force_greats and not force_greats_finder) else []
            )
            if best_data:
                fg_variant = apply_force_greats_to_result(
                    best_data,
                    calc_song,
                    ref_arrays,
                    manual_counts=manual_counts,
                    use_finder=force_greats_finder,
                )
                if fg_variant:
                    fg_variants.append(("best", fg_variant))

        # --- REPORTING & DB UPDATE (payload only; saved by coordinator) ---
        if best_data:
            score = best_data.get("Score", 0)
            print("-" * 30)
            print(f"FINAL CONFIGURATION FOR: {found_song_name}")
            print(f"Total Score: {score}")

            prev_score = prev_record.get("score") if prev_record else None
            prev_second = None
            is_first = prev_record is None
            is_better = (prev_score is None) or (score > prev_score)

            def extract_names(record):
                gear_names = record.get("gear") if record else []
                minis_names = record.get("minis") if record else []
                loadout = record.get("loadout") if record else None
                if (not gear_names and not minis_names) and loadout:
                    gear_names = loadout[:6]
                    minis_names = loadout[6:9]
                return list(gear_names or []), list(minis_names or [])

            def build_details(data_dict):
                if not data_dict:
                    return {}
                return {
                    "FT": data_dict.get("FT", 0),
                    "FF": data_dict.get("FF", 0),
                    "GemCounts": data_dict.get("GemCounts", {}),
                    "Stats": data_dict.get("Stats", {}),
                    "SelectedElement": data_dict.get("Selected Element", ""),
                    "PrimaryColor": meta_primary_color,
                    "SecondaryColor": meta_secondary_color,
                    "ForceGreats": data_dict.get("ForceGreats", {}),
                }

            best_gear_names = [g.get("Name") for g in best_gear]
            best_mini_names = [m.get("Name") for m in best_minis]
            best_details = build_details(best_data)

            force_candidates = []
            if prev_record:
                prev_force = prev_record.get("force")
                if prev_force and prev_force.get("score") is not None:
                    force_candidates.append(prev_force)
            for _, fg_variant in fg_variants:
                force_candidates.append(
                    {
                        "score": fg_variant.get("Score", 0),
                        "gear": best_gear_names,
                        "minis": best_mini_names,
                        "details": build_details(fg_variant),
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
                        "details": prev_record.get("details", {}),
                    }
                )

            candidates.append(
                {
                    "score": score,
                    "gear": best_gear_names,
                    "minis": best_mini_names,
                    "details": best_details,
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

            attempts_first = (
                1
                if is_first or is_better
                else (prev_attempts_first + 1 if prev_attempts_first else 1)
            )
            updated_payload = {}
            updated_payload["attempt_lifetime"] = attempt_lifetime
            updated_payload["attempts_first"] = attempts_first
            if top1:
                updated_payload.update(
                    {
                        "score": top1["score"],
                        "gear": top1.get("gear", []),
                        "minis": top1.get("minis", []),
                        "details": top1.get("details", {}),
                    }
                )

            updated_payload.pop("second", None)

            if force_candidates:
                force_candidates = sorted(
                    force_candidates, key=lambda c: c.get("score", -1), reverse=True
                )
                best_force = force_candidates[0]
                updated_payload["force"] = {
                    "score": best_force.get("score"),
                    "gear": best_force.get("gear", []),
                    "minis": best_force.get("minis", []),
                    "details": best_force.get("details", {}),
                }
            else:
                updated_payload.pop("force", None)

            db_payload = updated_payload

            emit(f"DONE | Score={score}")

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
                gc = best_data["GemCounts"]
                sel_el = best_data.get("Selected Element", "Rush")
                print(f"\nGem Allocation -> Fever Time: {best_data.get('FT', 0)}")
                print(f"Gem Allocation -> Fever Fill: {best_data.get('FF', 0)}")
                print(
                    "Gem Allocation -> Fever Multiplier: "
                    f"{gc.get('Fever Multiplier', 0)}"
                )
                print(
                    "Gem Allocation -> Combo Multiplier: "
                    f"{gc.get('Combo Multiplier', 0)}"
                )
                print(
                    "Gem Allocation -> Perfect Points: "
                    f"{gc.get('Perfect Points', 0)}"
                )
                print(
                    f"Gem Allocation -> {sel_el} (Overflow): "
                    f"{gc.get('Element Overflow', 0)}"
                )

            if fg_variants:
                best_fg_variant = max(
                    fg_variants, key=lambda p: p[1].get("Score", -1)
                )[1]
                fg_meta = best_fg_variant.get("ForceGreats", {}) or {}
                print("\n[ForceGreats Optimizer]")
                print(
                    f"Base Score: {fg_meta.get('base_score', best_data.get('Score', 0))} | "
                    f"ForceGreat Score: {best_fg_variant.get('Score', 0)}"
                )
                cfg_map = fg_meta.get("config", {})
                if cfg_map:
                    print(f"Config: {cfg_map}")

        return {
            "song": found_song_name,
            "db_key": db_key,
            "db_payload": db_payload,
            "best_data": best_data,
            "best_gear": best_gear,
            "best_minis": best_minis,
            "log": buf.getvalue(),
        }
    finally:
        if local_executor:
            local_executor.shutdown()
        # Prevent memory leak from unbounded cache growth across thousands of songs
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()

    # Should never reach here; fallback to avoid crashes
    return {
        "song": found_song_name,
        "db_key": found_song_name,
        "db_payload": None,
        "best_data": None,
        "best_gear": [],
        "best_minis": [],
        "log": buf.getvalue(),
    }


# --- Main Execution ---
if __name__ == "__main__":
    multiprocessing.freeze_support()
    while True:
        loop_forever = False
        start_time = time.time()
        try:
            cfg = configparser.ConfigParser()
            # Explicit UTF-8-SIG to avoid Windows default 'charmap' decoding issues
            cfg.read("config.ini", encoding="utf-8-sig")
            paths = load_paths_cache()
            db_display_name = os.path.basename(get_evolution_db_path())
            discord_reporter.send_log(
                f"Gear Optimizer run started. DB file: {db_display_name}"
            )

            # --- DB LOAD (always, independent of UseEvolutionDB) ---
            evo_db = load_evolution_db()

            # --- Configuration Granularity ---
            meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
            enable_fever = enable_mini = enable_gear = bool(meta_finder)
            auto_buff = cfg.getboolean(
                "IterationEngine", "AutoSelectBuffAndColor", fallback=False
            )
            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean(
                "IterationEngine", "UseEvolutionDB", fallback=True
            )
            loop_forever = cfg.getboolean(
                "IterationEngine", "LoopForever", fallback=False
            )
            eval_cpu_limit = safe_int(
                cfg.get("IterationEngine", "EvalCPUCores", fallback=0)
            )

            stats_path = paths.get("Stats", "")
            if not stats_path:
                stats_path = os.path.join(SCRIPT_DIR, "Stats.csv")
            stats_table = read_table(stats_path)

            # --- CRITICAL FIX: PREVENT DB TAINTING ---
            # If any automation is active, FORCE manual gem inputs to 0 in memory.
            # This ensures the solver runs on a clean slate and the DB saves the "Pure" result.
            if enable_fever or enable_mini or enable_gear:
                print(" >> [Auto-Mode] Finders active: Ignoring manual [UserInputStatsGems] & [ElementalGems] to prevent database tainting.")

                if not cfg.has_section("UserInputStatsGems"):
                    cfg.add_section("UserInputStatsGems")
                cfg.set("UserInputStatsGems", "perfect_points", "0")
                cfg.set("UserInputStatsGems", "combo_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_fill", "0")
                cfg.set("UserInputStatsGems", "fever_time", "0")

                if not cfg.has_section("ElementalGems"):
                    cfg.add_section("ElementalGems")
                cfg.set("ElementalGems", "Chill", "0")
                cfg.set("ElementalGems", "Flow", "0")
                cfg.set("ElementalGems", "Rush", "0")
                cfg.set("ElementalGems", "Beat", "0")
                cfg.set("ElementalGems", "Vibe", "0")

            # OPTIMIZATION: Pre-load References as NumPy arrays ONCE
            stat_names = [
                "Perfect Points",
                "Combo Multiplier",
                "Fever Multiplier",
                "Fever Fill Rate",
                "Fever Time",
            ]
            ref_arrays = {}
            for i, name in enumerate(stat_names):
                temp_list = []
                for v in range(TOTAL_ROWS + 1):
                    lookup_index = TOTAL_ROWS - v
                    try:
                        val = stats_table[lookup_index][i] if stats_table else 0
                    except Exception:
                        val = 0
                    temp_list.append(val)
                ref_arrays[name] = np.array(temp_list, dtype=np.float64)

            # OPTIMIZATION: Pre-load Gears and Minis ONCE
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name = {g["Name"]: g for g in all_gears}
            minis_by_name = {m["Name"]: m for m in all_minis}

            diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
            search_dir = paths.get(diff, SCRIPT_DIR)
            diff_lower = diff.strip().lower()
            filter_search = cfg.get("CalculateSong", "Song_Name", fallback="").strip().lower()

            def _parse_color_targets(raw_val):
                tokens = [
                    c.strip().lower()
                    for c in re.split(r"[,\|/]", raw_val or "")
                    if c and c.strip()
                ]
                is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
                return is_all, set() if is_all else set(tokens)

            target_primary_raw = cfg.get("CalculateSong", "TargetPrimary", fallback="")
            target_secondary_raw = cfg.get("CalculateSong", "TargetSecondary", fallback="")
            legacy_target_raw = cfg.get("CalculateSong", "TargetColor", fallback="")
            if not target_primary_raw and legacy_target_raw:
                target_primary_raw = legacy_target_raw
            if not target_secondary_raw:
                target_secondary_raw = "all"

            target_primary_all, target_primary_colors = _parse_color_targets(
                target_primary_raw
            )
            target_secondary_all, target_secondary_colors = _parse_color_targets(
                target_secondary_raw
            )

            diff_dirs = {}
            for key in ("Easy", "Normal", "Hard"):
                base_path = paths.get(key)
                if base_path:
                    norm = os.path.abspath(base_path).lower().rstrip("\\/") + os.sep
                    diff_dirs[key.lower()] = norm

            song_queue = []
            seen_paths = set()

            dirs_to_search = [search_dir]
            if search_dir != SCRIPT_DIR:
                dirs_to_search.append(SCRIPT_DIR)

            for d in dirs_to_search:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(".txt"):
                            fp = os.path.join(root, f)
                            abs_fp = os.path.abspath(fp)
                            if abs_fp in seen_paths:
                                continue

                            meta = scan_song_header(fp)
                            if not meta:
                                continue
                            name = meta["Song Name"].lower()
                            meta_diff = (meta.get("Difficulty") or "").strip().lower()
                            meta_diff_known = meta_diff in ("easy", "normal", "hard")
                            primary_color = (meta.get("Primary Color") or "").strip().lower()
                            secondary_color = (
                                (meta.get("Secondary Color") or "").strip().lower()
                            )
                            abs_fp_lower = abs_fp.lower()
                            file_diff = next(
                                (
                                    tag
                                    for tag, base in diff_dirs.items()
                                    if abs_fp_lower.startswith(base)
                                ),
                                None,
                            )
                            if diff_lower in ("easy", "normal", "hard"):
                                if meta_diff_known and meta_diff != diff_lower:
                                    continue
                                if file_diff and file_diff != diff_lower:
                                    continue
                                if not file_diff and not meta_diff_known and search_dir != SCRIPT_DIR:
                                    continue
                            if diff_lower in ("easy", "normal", "hard"):
                                if any(
                                    diff_lower != tag and f"({tag}" in name
                                    for tag in ("hard", "normal", "easy")
                                ):
                                    continue
                            if (
                                not target_primary_all
                                and (
                                    not primary_color
                                    or primary_color not in target_primary_colors
                                )
                            ):
                                continue
                            if (
                                not target_secondary_all
                                and (
                                    not secondary_color
                                    or secondary_color not in target_secondary_colors
                                )
                            ):
                                continue
                            if filter_search and filter_search not in name:
                                continue

                            song_queue.append((fp, meta["Song Name"]))
                            seen_paths.add(abs_fp)

            if not song_queue:
                print("Error: No matching songs found.")
            else:
                if not filter_search:
                    missing = []
                    completed = []
                    for fp, meta_name in song_queue:
                        if meta_name in evo_db:
                            completed.append((fp, meta_name))
                        else:
                            missing.append((fp, meta_name))
                    if missing:
                        print(f"Auto-selection: {len(missing)} song(s) without DB records found; prioritizing those.")
                        song_queue = missing
                    else:
                        print("All songs have DB records; processing full list.")

                print(f"Found {len(song_queue)} songs to process.")

                discord_reporter.send_log(f"Queued {len(song_queue)} song(s) for processing.")

                status_queue = None
                status_thread = None
                manager = multiprocessing.Manager()
                status_queue = manager.Queue()

                def _status_listener(q):
                    while True:
                        try:
                            msg = q.get()
                        except (EOFError, BrokenPipeError, OSError):
                            break
                        if msg is None:
                            break
                        print(msg, flush=True)
                        discord_reporter.send_log(str(msg))

                status_thread = threading.Thread(
                    target=_status_listener, args=(status_queue,), daemon=True
                )
                status_thread.start()

                cfg_dict = cfg_to_dict(cfg)

                tasks = []
                logical_cpus = os.cpu_count() or 1
                available_cpus = logical_cpus
                if eval_cpu_limit and eval_cpu_limit > 0:
                    available_cpus = max(1, min(logical_cpus, eval_cpu_limit))
                else:
                    available_cpus = max(1, available_cpus)
                if available_cpus != logical_cpus:
                    print(
                        f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores."
                    )
                parallel_workers = 1  # Single-threaded per song to avoid nested pools on Windows

                for fp, found_song_name in song_queue:
                    print(f"[QUEUE] {found_song_name}")
                    prev_for_task = evo_db.get(found_song_name) if use_evo_db else None
                    tasks.append(
                        (
                            fp,
                            found_song_name,
                            cfg_dict,
                            paths,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            use_evo_db,
                            auto_buff,
                            ga_depth,
                            prev_for_task,
                            status_queue,
                            parallel_workers,
                        )
                    )

                def _consume_results(results_iter, future_map=None):
                    total = len(tasks)
                    completed = 0
                    failed = 0
                    for item in results_iter:
                        completed += 1
                        # Handle Future objects (from ProcessPoolExecutor) with exception safety
                        if future_map is not None:
                            future = item
                            song_name = future_map.get(future, "Unknown")
                            try:
                                res = future.result()
                            except Exception as task_err:
                                failed += 1
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                continue  # Skip this song and continue with the queue
                        else:
                            # Sequential processing - item is already the result (or error dict)
                            res = item
                            # Check if this is an error placeholder from _safe_sequential_gen
                            if isinstance(res, dict) and "_error" in res:
                                failed += 1
                                task_err = res["_error"]
                                song_name = res.get("_song_name", "Unknown")
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                continue
                        print(f"[{completed}/{total}] Completed: {res['song']}")
                        print("=" * 60)
                        print(f"PROCESSING SONG: {res['song']}")
                        print("=" * 60)
                        discord_reporter.send_stats(build_stats_summary(res, completed, total))
                        # Logs already streamed live via Tee; buffer retained for completeness
                        db_payload = res.get("db_payload")
                        if use_evo_db and db_payload:
                            evo_db[res["db_key"]] = db_payload
                            save_evolution_db(evo_db)
                        log_content = (res.get("log") or "").strip()
                        if log_content:
                            discord_reporter.send_log(f"Log for {res.get('song', 'Unknown Song')} ({completed}/{total}):")
                            # Avoid Discord spam: keep only the tail of very long logs.
                            tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                            discord_reporter.send_log(tail)
                    if failed > 0:
                        print(f"[SUMMARY] {failed}/{total} songs failed during processing.")

                song_worker_limit = max(1, available_cpus // max(1, parallel_workers))
                max_workers = max(1, min(len(tasks), song_worker_limit))
                print(
                    f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
                )
                print(f"Using {available_cpus} logical CPU cores")
                if len(tasks) > 1 and max_workers > 1:
                    with concurrent.futures.ProcessPoolExecutor(
                        max_workers=max_workers,
                        mp_context=multiprocessing.get_context("spawn"),
                    ) as executor:
                        future_map = {
                            executor.submit(process_song_task, t): t[1] for t in tasks
                        }
                        # Pass futures directly so _consume_results can handle exceptions per-song
                        _consume_results(
                            concurrent.futures.as_completed(future_map),
                            future_map=future_map
                        )
                else:
                    # Sequential processing with per-song exception handling
                    def _safe_sequential_gen():
                        for t in tasks:
                            try:
                                yield process_song_task(t)
                            except Exception as seq_err:
                                yield {"_error": seq_err, "_song_name": t[1]}
                    _consume_results(_safe_sequential_gen(), future_map=None)

                if status_queue:
                    status_queue.put(None)
                    if status_thread:
                        status_thread.join(timeout=2)
                    if manager:
                        manager.shutdown()
                discord_reporter.send_log("All queued songs processed.")

        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            discord_reporter.send_log(f"Error encountered: {e}")
        finally:
            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            print(done_msg)
            discord_reporter.send_log(done_msg)

        if loop_forever:
            wait_time = 3
            print(f"Restarting song scan in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            print("LoopForever=FALSE; exiting after completing queue.")
            discord_reporter.send_log("LoopForever disabled; exiting.")
            break
