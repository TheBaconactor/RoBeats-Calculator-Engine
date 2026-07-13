"""
Database operations for the gear optimizer.
Handles all SQLite interactions for loadout persistence and retrieval.

This package is the canonical public import surface `gear_optimizer.data.database`.
It was split out of a single 1743-LOC module into cohesive submodules; this
``__init__`` is the facade that preserves the exact prior public + private name
surface (module identity), so existing imports and monkeypatches keep working:

    connection      -- DB path resolution + connection factories + schema init
    songs           -- per-song counter reads/writes
    loadout_io      -- gear/mini compaction, expansion, hashing
    force_normalize -- Force-Greats payload normalization + stats reconstruction
    persistence     -- batch leaderboard writes
    leaderboards    -- top base/FG loadout reads

Monkeypatch contract: tests patch names on THIS namespace
(`gear_optimizer.data.database.<name>`). Submodules resolve the patchable names
(`get_minis_by_name_cached`, `get_gears_by_name_cached`, `_loadout_hash_from_names`,
`LOADOUTS_PER_SONG_LIMIT`) through this facade at call time, so a patch here is
honored by both persistence and leaderboards.
"""
import logging

logger = logging.getLogger(__name__)

# --- Re-exported constants / shared collaborators (full prior module surface) ---
# Note: this facade is one package level deeper than the old `data/database.py`
# module, so every relative import that was anchored at `data/` gains one dot
# (`..core` -> `...core`, `.migrations` -> `..migrations`, sibling data modules
# `.database_codecs` -> `..database_codecs`, etc.). Absolute imports are unchanged.
from ...core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS
from ...core.fallback_monitor import warn_fallback
from ...core.gem_defs import element_gem_count, fg_score_from_force
from ...core.parsing import env_flag
from ...core.utils import safe_int as _safe_int_for_db
from ...core.team_buff import (
    canonicalize_team_buff,
    normalize_team_buff,
    team_buff_effect,
    team_buff_query_values,
)
from ...core.types import PersistenceEntry
from ..migrations import ensure_schema
from ..database_fg_summary import (
    normalize_details_for_persistence as _normalize_details_for_persistence,
    repair_base_loadout_fg_summaries as _repair_base_loadout_fg_summaries,
)
from ..database_codecs import (
    _json_dumps_compact,
    _json_loads,
    _pack_id_groups,
    _pack_id_list,
    _pack_stats_for_storage,
    _strip_computed_details_fields,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
)
from ..piece_encoding_store import (
    _GEAR_NAME_ENCODING_TABLE,
    _MINI_NAME_ENCODING_TABLE,
    _initialize_piece_name_encodings,
    _insert_missing_piece_names,
    _load_piece_name_encoding_maps,
)
from ..loadout_equivalence import (
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    get_gears_by_name_cached,
    get_minis_by_name_cached,
    canonical_minis_groups_from_names,
    representative_mini_names,
    rotate_mini_groups_for_slot_display,
)
from gear_optimizer.core.parsing import env_get

# --- Connection layer ---
from . import connection
from .connection import (
    get_evolution_db_path,
    get_db_connection,
    get_db_connection_with_timeout,
    _db_path_to_uri,
    get_db_connection_readonly,
    get_db_connection_cached,
    init_db,
)

# `_DB_TLS` is re-bound BY IDENTITY: a test mutates `database._DB_TLS.__dict__`
# directly, so the facade name and the connection module name must be the same
# thread-local object (never a fresh instance).
_DB_TLS = connection._DB_TLS

# --- Songs counters + per-song presence queries ---
from .songs import (
    get_song_counters,
    get_song_names_present_in_db,
    get_song_names_with_persisted_loadouts,
    update_song_counters,
)

# --- Loadout IO (compaction / expansion / hashing) ---
from .loadout_io import (
    _compact_gear_for_db,
    _compact_minis_for_db,
    _expand_gear_from_db,
    _expand_minis_from_db,
    _loadout_hash_from_names,
    get_loadout_hash,
)

# --- Force-Greats normalization + stats reconstruction ---
from .force_normalize import (
    _get_overflow_from_details,
    _ensure_stats_in_details,
    _force_payload_base_score,
    _base_details_from_force_payload,
    _compact_force_details_for_storage,
    _coerce_db_int,
    _normalize_force_for_persistence,
    _normalize_force_base_score_for_persistence,
    _assert_force_score_pairing,
)

# --- Persistence + leaderboards ---
from .persistence import (
    configure_persistent_writer_connection,
    save_loadouts_batch,
    save_optimizer_song_result,
    save_team_buff_loadouts_batch,
)
from .leaderboards import get_best_loadouts

__all__ = [
    # constants / collaborators
    "LOADOUTS_PER_SONG_LIMIT",
    "PATHS",
    "warn_fallback",
    "element_gem_count",
    "fg_score_from_force",
    "env_flag",
    "env_get",
    "_safe_int_for_db",
    "canonicalize_team_buff",
    "normalize_team_buff",
    "team_buff_effect",
    "team_buff_query_values",
    "PersistenceEntry",
    "ensure_schema",
    "_normalize_details_for_persistence",
    "_repair_base_loadout_fg_summaries",
    # codecs
    "_json_dumps_compact",
    "_json_loads",
    "_pack_id_groups",
    "_pack_id_list",
    "_pack_stats_for_storage",
    "_strip_computed_details_fields",
    "_unpack_id_groups",
    "_unpack_id_list",
    "_unpack_stats_after_load",
    # piece encoding
    "_GEAR_NAME_ENCODING_TABLE",
    "_MINI_NAME_ENCODING_TABLE",
    "_initialize_piece_name_encodings",
    "_insert_missing_piece_names",
    "_load_piece_name_encoding_maps",
    # loadout equivalence
    "effective_loadout_hash_from_names",
    "effective_mini_signature_for_name",
    "extract_song_colors",
    "get_gears_by_name_cached",
    "get_minis_by_name_cached",
    "canonical_minis_groups_from_names",
    "representative_mini_names",
    "rotate_mini_groups_for_slot_display",
    # connection
    "get_evolution_db_path",
    "get_db_connection",
    "get_db_connection_with_timeout",
    "_db_path_to_uri",
    "get_db_connection_readonly",
    "get_db_connection_cached",
    "init_db",
    "_DB_TLS",
    # songs
    "get_song_counters",
    "get_song_names_present_in_db",
    "get_song_names_with_persisted_loadouts",
    "update_song_counters",
    # loadout io
    "_compact_gear_for_db",
    "_compact_minis_for_db",
    "_expand_gear_from_db",
    "_expand_minis_from_db",
    "_loadout_hash_from_names",
    "get_loadout_hash",
    # force normalize
    "_get_overflow_from_details",
    "_ensure_stats_in_details",
    "_force_payload_base_score",
    "_base_details_from_force_payload",
    "_compact_force_details_for_storage",
    "_coerce_db_int",
    "_normalize_force_for_persistence",
    "_normalize_force_base_score_for_persistence",
    "_assert_force_score_pairing",
    # persistence + leaderboards
    "configure_persistent_writer_connection",
    "save_loadouts_batch",
    "save_optimizer_song_result",
    "save_team_buff_loadouts_batch",
    "get_best_loadouts",
]
