from __future__ import annotations

import configparser
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from gear_optimizer.core.config import get_config_path, load_config
from gear_optimizer.core.utils import safe_float, safe_int


def _repo_root() -> Path:
    # inventory_optimizer/ -> repo root
    return Path(__file__).resolve().parents[1]


def default_inventory_meta_config_path() -> str:
    return str(_repo_root() / "configs" / "inventory_meta_coverage.ini")


def _truthy(val: object) -> bool:
    s = str(val or "").strip().lower()
    if not s:
        return False
    return s in {"1", "true", "yes", "on"}


def _get_str(cfg: configparser.ConfigParser, section: str, key: str, fallback: str) -> str:
    try:
        if cfg.has_option(section, key):
            return str(cfg.get(section, key)).strip()
    except Exception:
        pass
    return str(fallback)


def _get_int(cfg: configparser.ConfigParser, section: str, key: str, fallback: int) -> int:
    return safe_int(_get_str(cfg, section, key, str(fallback)), fallback)


def _get_float(cfg: configparser.ConfigParser, section: str, key: str, fallback: float) -> float:
    return safe_float(_get_str(cfg, section, key, str(fallback)), fallback)


def _get_bool(cfg: configparser.ConfigParser, section: str, key: str, fallback: bool) -> bool:
    raw = _get_str(cfg, section, key, "true" if fallback else "false")
    return _truthy(raw)


def _apply_set_overrides(cfg: configparser.ConfigParser, overrides: Iterable[str]) -> List[str]:
    """
    Apply `--set Section.Key=Value` overrides into the provided ConfigParser.

    Returns a list of warnings for malformed entries.
    """
    warnings: List[str] = []
    for raw in overrides:
        raw = str(raw or "").strip()
        if not raw:
            continue
        if "=" not in raw:
            warnings.append(f"Invalid --set (missing '='): {raw}")
            continue
        lhs, rhs = raw.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        if "." not in lhs:
            warnings.append(f"Invalid --set (expected Section.Key=Value): {raw}")
            continue
        section, key = lhs.split(".", 1)
        section = section.strip()
        key = key.strip()
        if not section or not key:
            warnings.append(f"Invalid --set (empty section/key): {raw}")
            continue
        if not cfg.has_section(section):
            cfg.add_section(section)
        cfg.set(section, key, rhs)
    return warnings


@dataclass(frozen=True)
class InventoryMetaCoverageSettings:
    # Run
    solver: str = "gpu_full"
    inventory_cap: int = 100
    seed: int = 1
    restarts: int = 1
    element: Optional[str] = None
    secondary_element: Optional[str] = None
    song_limit: Optional[int] = None
    profile: bool = False

    # Witness pool / K controls
    partitions_per_song: int = 32
    adaptive_rounds: int = 3
    adaptive_keep_per_song: int = 8
    gpu_full_witness_anchor_patterns: int = 128
    gpu_full_witness_seed_streams: int = 1
    gpu_full_witness_palettes: int = 1
    gpu_full_witness_pattern_profile: int = 1
    gpu_full_counter_stripes: int = 1

    # LNS / repack budgets
    gpu_repack_passes: int = 3
    gpu_lns_destroy: int = 6
    lns_time_sec: float = 0.0
    lns_attempts: int = 200

    # Candidate pool widening / selection
    gpu_full_top_candidates: int = 1
    gpu_full_candidate_score_delta: int = 0
    gpu_full_candidate_limit_per_song: int = 0

    # Biases / tie-breakers
    gpu_full_variant_freq_mode: str = "song_support"
    gpu_full_wildcard_freq_bonus: int = 40
    gpu_full_wildcard_palette_size: int = 0
    gpu_full_wildcard_palette_min_count: int = 2
    gpu_full_wildcard_palette_scan: int = 8
    gpu_full_wildcard_palette_tail_slots: int = 3
    gpu_full_new_gear_penalty: int = 0

    # Optional modes (expert; default off)
    gpu_full_human_mode: bool = False
    gpu_full_human_gear_penalty_step: int = 0
    gpu_full_human_gear_free: int = 2
    gpu_full_human_colored_penalty: int = 0

    # Synergy (expert; default off)
    gpu_full_synergy_weight: int = 0
    gpu_full_synergy_top_offsets: int = 128
    gpu_full_synergy_min_pair_count: int = 2
    gpu_full_synergy_scale: int = 256
    gpu_full_synergy_max_bonus: int = 4095

    # Universe shaping / scan limits (expert)
    gpu_full_k_scan_select: int = 0
    gpu_full_k_scan_repack: int = 0
    gpu_full_v_pad_bin: int = 4096

    # LNS variants (expert)
    gpu_full_repack_rarity_weighted: bool = False
    gpu_full_lns_freq_weighted: bool = False
    gpu_full_lns_random_destroy_prob: float = 0.0
    gpu_full_lns_restore_after: int = 12
    gpu_full_lns_restore_drop: int = 4

    # ALNS/PT (expert)
    gpu_full_alns_enabled: bool = False
    gpu_full_alns_islands: int = 1
    gpu_full_pt_enabled: bool = False
    gpu_full_pt_t_min: float = 1.0
    gpu_full_pt_t_max: float = 10.0
    gpu_full_pt_swap_interval: int = 8
    gpu_full_pt_destroy_beta: float = 0.0
    gpu_full_pt_cap_slack_max: int = 0

    # Repair (enabled by default; production behavior)
    gpu_full_repair_enabled: bool = True
    gpu_full_repair_attempts: int = 128
    gpu_full_repair_max_cands_per_slot: int = 16
    gpu_full_repair_song_limit: int = 512

    # Seed inventory (optional)
    seed_inventory_variants_path: str = ""
    seed_inventory_mode: str = "hard"

    # Optional universe restriction for witness pool
    gpu_full_restricted_universe_path: str = ""

    def to_run_kwargs(self) -> Dict[str, Any]:
        return {
            "solver": "gpu_full",  # hard-enforced (GPU-only policy + standardization)
            "inventory_cap": int(self.inventory_cap),
            "element": self.element,
            "secondary_element": self.secondary_element,
            "partitions_per_song": int(self.partitions_per_song),
            "seed": int(self.seed),
            "restarts": int(self.restarts),
            "gpu_repack_passes": int(self.gpu_repack_passes),
            "gpu_lns_destroy": int(self.gpu_lns_destroy),
            "adaptive_rounds": int(self.adaptive_rounds),
            "adaptive_keep_per_song": int(self.adaptive_keep_per_song),
            "lns_time_sec": float(self.lns_time_sec),
            "lns_attempts": int(self.lns_attempts),
            "song_limit": int(self.song_limit) if self.song_limit is not None else None,
            "profile": bool(self.profile),
            "seed_inventory_variants_path": str(self.seed_inventory_variants_path or ""),
            "seed_inventory_mode": str(self.seed_inventory_mode or "hard"),
            "gpu_full_wildcard_freq_bonus": int(self.gpu_full_wildcard_freq_bonus),
            "gpu_full_wildcard_palette_size": int(self.gpu_full_wildcard_palette_size),
            "gpu_full_wildcard_palette_min_count": int(self.gpu_full_wildcard_palette_min_count),
            "gpu_full_wildcard_palette_scan": int(self.gpu_full_wildcard_palette_scan),
            "gpu_full_wildcard_palette_tail_slots": int(self.gpu_full_wildcard_palette_tail_slots),
            "gpu_full_new_gear_penalty": int(self.gpu_full_new_gear_penalty),
            "gpu_full_variant_freq_mode": str(self.gpu_full_variant_freq_mode),
            "gpu_full_witness_anchor_patterns": int(self.gpu_full_witness_anchor_patterns),
            "gpu_full_witness_seed_streams": int(self.gpu_full_witness_seed_streams),
            "gpu_full_witness_palettes": int(self.gpu_full_witness_palettes),
            "gpu_full_witness_pattern_profile": int(self.gpu_full_witness_pattern_profile),
            "gpu_full_counter_stripes": int(self.gpu_full_counter_stripes),
            "gpu_full_top_candidates": int(self.gpu_full_top_candidates),
            "gpu_full_candidate_score_delta": int(self.gpu_full_candidate_score_delta),
            "gpu_full_candidate_limit_per_song": int(self.gpu_full_candidate_limit_per_song),
            "gpu_full_human_mode": bool(self.gpu_full_human_mode),
            "gpu_full_human_gear_penalty_step": int(self.gpu_full_human_gear_penalty_step),
            "gpu_full_human_gear_free": int(self.gpu_full_human_gear_free),
            "gpu_full_human_colored_penalty": int(self.gpu_full_human_colored_penalty),
            "gpu_full_synergy_weight": int(self.gpu_full_synergy_weight),
            "gpu_full_synergy_top_offsets": int(self.gpu_full_synergy_top_offsets),
            "gpu_full_synergy_min_pair_count": int(self.gpu_full_synergy_min_pair_count),
            "gpu_full_synergy_scale": int(self.gpu_full_synergy_scale),
            "gpu_full_synergy_max_bonus": int(self.gpu_full_synergy_max_bonus),
            "gpu_full_k_scan_select": int(self.gpu_full_k_scan_select),
            "gpu_full_k_scan_repack": int(self.gpu_full_k_scan_repack),
            "gpu_full_v_pad_bin": int(self.gpu_full_v_pad_bin),
            "gpu_full_repack_rarity_weighted": bool(self.gpu_full_repack_rarity_weighted),
            "gpu_full_lns_freq_weighted": bool(self.gpu_full_lns_freq_weighted),
            "gpu_full_lns_random_destroy_prob": float(self.gpu_full_lns_random_destroy_prob),
            "gpu_full_lns_restore_after": int(self.gpu_full_lns_restore_after),
            "gpu_full_lns_restore_drop": int(self.gpu_full_lns_restore_drop),
            "gpu_full_alns_enabled": bool(self.gpu_full_alns_enabled),
            "gpu_full_alns_islands": int(self.gpu_full_alns_islands),
            "gpu_full_pt_enabled": bool(self.gpu_full_pt_enabled),
            "gpu_full_pt_t_min": float(self.gpu_full_pt_t_min),
            "gpu_full_pt_t_max": float(self.gpu_full_pt_t_max),
            "gpu_full_pt_swap_interval": int(self.gpu_full_pt_swap_interval),
            "gpu_full_pt_destroy_beta": float(self.gpu_full_pt_destroy_beta),
            "gpu_full_pt_cap_slack_max": int(self.gpu_full_pt_cap_slack_max),
            "gpu_full_repair_enabled": bool(self.gpu_full_repair_enabled),
            "gpu_full_repair_attempts": int(self.gpu_full_repair_attempts),
            "gpu_full_repair_max_cands_per_slot": int(self.gpu_full_repair_max_cands_per_slot),
            "gpu_full_repair_song_limit": int(self.gpu_full_repair_song_limit),
            "gpu_full_restricted_universe_path": str(self.gpu_full_restricted_universe_path or ""),
        }

    def to_effective_config_dict(self, *, quality: str, config_path: str, set_overrides: List[str]) -> Dict[str, Any]:
        return {
            "meta": {
                "config_path": str(config_path),
                "quality": str(quality),
                "set_overrides": list(set_overrides),
            },
            "run": {
                "inventory_cap": int(self.inventory_cap),
                "seed": int(self.seed),
                "restarts": int(self.restarts),
                "element": self.element,
                "secondary_element": self.secondary_element,
                "song_limit": self.song_limit,
                "profile": bool(self.profile),
                "solver": "gpu_full",
            },
            "witness_pool": {
                "partitions_per_song": int(self.partitions_per_song),
                "adaptive_rounds": int(self.adaptive_rounds),
                "adaptive_keep_per_song": int(self.adaptive_keep_per_song),
                "witness_anchor_patterns": int(self.gpu_full_witness_anchor_patterns),
                "witness_seed_streams": int(self.gpu_full_witness_seed_streams),
                "witness_palettes": int(self.gpu_full_witness_palettes),
                "witness_pattern_profile": int(self.gpu_full_witness_pattern_profile),
                "wildcard_freq_bonus": int(self.gpu_full_wildcard_freq_bonus),
                "wildcard_palette_size": int(self.gpu_full_wildcard_palette_size),
                "wildcard_palette_min_count": int(self.gpu_full_wildcard_palette_min_count),
                "wildcard_palette_scan": int(self.gpu_full_wildcard_palette_scan),
                "wildcard_palette_tail_slots": int(self.gpu_full_wildcard_palette_tail_slots),
                "counter_stripes": int(self.gpu_full_counter_stripes),
            },
            "lns": {
                "gpu_repack_passes": int(self.gpu_repack_passes),
                "gpu_lns_destroy": int(self.gpu_lns_destroy),
                "lns_time_sec": float(self.lns_time_sec),
                "lns_attempts": int(self.lns_attempts),
                "repack_rarity_weighted": bool(self.gpu_full_repack_rarity_weighted),
                "lns_freq_weighted": bool(self.gpu_full_lns_freq_weighted),
                "lns_random_destroy_prob": float(self.gpu_full_lns_random_destroy_prob),
                "lns_restore_after": int(self.gpu_full_lns_restore_after),
                "lns_restore_drop": int(self.gpu_full_lns_restore_drop),
            },
            "candidates": {
                "top_candidates": int(self.gpu_full_top_candidates),
                "score_delta": int(self.gpu_full_candidate_score_delta),
                "limit_per_song": int(self.gpu_full_candidate_limit_per_song),
            },
            "biases": {
                "variant_freq_mode": str(self.gpu_full_variant_freq_mode),
                "new_gear_penalty": int(self.gpu_full_new_gear_penalty),
                "synergy_weight": int(self.gpu_full_synergy_weight),
            },
            "repair": {
                "enabled": bool(self.gpu_full_repair_enabled),
                "attempts": int(self.gpu_full_repair_attempts),
                "max_cands_per_slot": int(self.gpu_full_repair_max_cands_per_slot),
                "song_limit": int(self.gpu_full_repair_song_limit),
            },
            "seed_inventory": {
                "variants_path": str(self.seed_inventory_variants_path or ""),
                "mode": str(self.seed_inventory_mode or "hard"),
            },
            "expert": {
                "synergy_top_offsets": int(self.gpu_full_synergy_top_offsets),
                "synergy_min_pair_count": int(self.gpu_full_synergy_min_pair_count),
                "synergy_scale": int(self.gpu_full_synergy_scale),
                "synergy_max_bonus": int(self.gpu_full_synergy_max_bonus),
                "k_scan_select": int(self.gpu_full_k_scan_select),
                "k_scan_repack": int(self.gpu_full_k_scan_repack),
                "v_pad_bin": int(self.gpu_full_v_pad_bin),
                "alns_enabled": bool(self.gpu_full_alns_enabled),
                "alns_islands": int(self.gpu_full_alns_islands),
                "pt_enabled": bool(self.gpu_full_pt_enabled),
                "pt_t_min": float(self.gpu_full_pt_t_min),
                "pt_t_max": float(self.gpu_full_pt_t_max),
                "pt_swap_interval": int(self.gpu_full_pt_swap_interval),
                "pt_destroy_beta": float(self.gpu_full_pt_destroy_beta),
                "pt_cap_slack_max": int(self.gpu_full_pt_cap_slack_max),
                "human_mode": bool(self.gpu_full_human_mode),
                "human_gear_penalty_step": int(self.gpu_full_human_gear_penalty_step),
                "human_gear_free": int(self.gpu_full_human_gear_free),
                "human_colored_penalty": int(self.gpu_full_human_colored_penalty),
                "restricted_universe_path": str(self.gpu_full_restricted_universe_path or ""),
            },
        }


QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
    # Fast sanity checks / debugging
    "low": {
        "restarts": 1,
        "partitions_per_song": 16,
        "adaptive_rounds": 1,
        "adaptive_keep_per_song": 4,
        "lns_attempts": 50,
        "gpu_repack_passes": 1,
        "gpu_lns_destroy": 4,
        "gpu_full_repair_attempts": 64,
    },
    # Balanced defaults (matches historical CLI defaults)
    "medium": {},
    # Production-ish (higher K + more restarts)
    "high": {
        "restarts": 5,
        "partitions_per_song": 256,
        "adaptive_rounds": 0,
        "adaptive_keep_per_song": 0,
        "lns_attempts": 600,
        "gpu_repack_passes": 3,
        "gpu_lns_destroy": 8,
        "gpu_full_repair_attempts": 256,
    },
}


def _apply_quality(settings: InventoryMetaCoverageSettings, *, quality: str) -> InventoryMetaCoverageSettings:
    q = str(quality or "").strip().lower() or "medium"
    if q not in QUALITY_PRESETS:
        raise ValueError(f"Unknown quality preset: {quality!r}. Expected one of: {sorted(QUALITY_PRESETS)}")
    updates = dict(QUALITY_PRESETS[q])
    return replace(settings, **updates) if updates else settings


def load_inventory_meta_coverage_settings(
    *,
    config_path: str = "",
    quality: str = "",
    set_overrides: Optional[Iterable[str]] = None,
) -> Tuple[InventoryMetaCoverageSettings, Dict[str, Any], List[str]]:
    """
    Load Inventory Meta Coverage settings from an ini file, apply a quality preset, and then apply `--set` overrides.

    Precedence (last wins):
    - Hardcoded defaults (kept in sync with historical CLI defaults)
    - Quality preset (`quality` or config's [InventoryMetaCoverage].Quality)
    - Ini file values
    - `--set Section.Key=Value` overrides
    """
    set_overrides_list = [str(x) for x in (set_overrides or []) if str(x or "").strip()]

    effective_path = str(config_path).strip()
    if not effective_path:
        # Prefer the inventory-meta default ini when present; otherwise fall back to the global config.ini behavior.
        default_path = default_inventory_meta_config_path()
        effective_path = default_path if Path(default_path).exists() else get_config_path()

    cfg = load_config(effective_path)

    warnings: List[str] = []
    warnings.extend(_apply_set_overrides(cfg, set_overrides_list))

    settings = InventoryMetaCoverageSettings()

    quality_cfg = _get_str(cfg, "InventoryMetaCoverage", "Quality", "")
    effective_quality = (str(quality).strip() or quality_cfg or "medium").lower()
    settings = _apply_quality(settings, quality=effective_quality)

    # Run
    settings = replace(
        settings,
        inventory_cap=_get_int(cfg, "InventoryMetaCoverage", "InventoryCap", settings.inventory_cap),
        seed=_get_int(cfg, "InventoryMetaCoverage", "Seed", settings.seed),
        restarts=_get_int(cfg, "InventoryMetaCoverage", "Restarts", settings.restarts),
        element=(_get_str(cfg, "InventoryMetaCoverage", "Element", "") or "").strip() or None,
        secondary_element=(_get_str(cfg, "InventoryMetaCoverage", "SecondaryElement", "") or "").strip() or None,
        song_limit=(
            None
            if _get_int(cfg, "InventoryMetaCoverage", "SongLimit", 0) <= 0
            else _get_int(cfg, "InventoryMetaCoverage", "SongLimit", 0)
        ),
        profile=_get_bool(cfg, "InventoryMetaCoverage", "Profile", settings.profile),
    )

    # WitnessPool
    settings = replace(
        settings,
        partitions_per_song=_get_int(cfg, "WitnessPool", "PartitionsPerSong", settings.partitions_per_song),
        adaptive_rounds=_get_int(cfg, "WitnessPool", "AdaptiveRounds", settings.adaptive_rounds),
        adaptive_keep_per_song=_get_int(cfg, "WitnessPool", "AdaptiveKeepPerSong", settings.adaptive_keep_per_song),
        gpu_full_witness_anchor_patterns=_get_int(
            cfg, "WitnessPool", "AnchorPatterns", settings.gpu_full_witness_anchor_patterns
        ),
        gpu_full_witness_seed_streams=_get_int(
            cfg, "WitnessPool", "SeedStreams", settings.gpu_full_witness_seed_streams
        ),
        gpu_full_witness_palettes=_get_int(cfg, "WitnessPool", "Palettes", settings.gpu_full_witness_palettes),
        gpu_full_witness_pattern_profile=_get_int(
            cfg, "WitnessPool", "PatternProfile", settings.gpu_full_witness_pattern_profile
        ),
        gpu_full_wildcard_freq_bonus=_get_int(
            cfg, "WitnessPool", "WildcardFreqBonus", settings.gpu_full_wildcard_freq_bonus
        ),
        gpu_full_wildcard_palette_size=_get_int(
            cfg, "WitnessPool", "WildcardPaletteSize", settings.gpu_full_wildcard_palette_size
        ),
        gpu_full_wildcard_palette_min_count=_get_int(
            cfg, "WitnessPool", "WildcardPaletteMinCount", settings.gpu_full_wildcard_palette_min_count
        ),
        gpu_full_wildcard_palette_scan=_get_int(
            cfg, "WitnessPool", "WildcardPaletteScan", settings.gpu_full_wildcard_palette_scan
        ),
        gpu_full_wildcard_palette_tail_slots=_get_int(
            cfg, "WitnessPool", "WildcardPaletteTailSlots", settings.gpu_full_wildcard_palette_tail_slots
        ),
        gpu_full_counter_stripes=_get_int(cfg, "WitnessPool", "CounterStripes", settings.gpu_full_counter_stripes),
    )

    # Candidates
    settings = replace(
        settings,
        gpu_full_top_candidates=_get_int(cfg, "Candidates", "TopCandidates", settings.gpu_full_top_candidates),
        gpu_full_candidate_score_delta=_get_int(
            cfg, "Candidates", "ScoreDelta", settings.gpu_full_candidate_score_delta
        ),
        gpu_full_candidate_limit_per_song=_get_int(
            cfg, "Candidates", "LimitPerSong", settings.gpu_full_candidate_limit_per_song
        ),
    )

    # LNS
    settings = replace(
        settings,
        gpu_repack_passes=_get_int(cfg, "LNS", "RepackPasses", settings.gpu_repack_passes),
        gpu_lns_destroy=_get_int(cfg, "LNS", "Destroy", settings.gpu_lns_destroy),
        lns_time_sec=_get_float(cfg, "LNS", "TimeSec", settings.lns_time_sec),
        lns_attempts=_get_int(cfg, "LNS", "Attempts", settings.lns_attempts),
        gpu_full_repack_rarity_weighted=_get_bool(
            cfg, "LNS", "RepackRarityWeighted", settings.gpu_full_repack_rarity_weighted
        ),
        gpu_full_lns_freq_weighted=_get_bool(cfg, "LNS", "FreqWeighted", settings.gpu_full_lns_freq_weighted),
        gpu_full_lns_random_destroy_prob=_get_float(
            cfg, "LNS", "RandomDestroyProb", settings.gpu_full_lns_random_destroy_prob
        ),
        gpu_full_lns_restore_after=_get_int(cfg, "LNS", "RestoreAfter", settings.gpu_full_lns_restore_after),
        gpu_full_lns_restore_drop=_get_int(cfg, "LNS", "RestoreDrop", settings.gpu_full_lns_restore_drop),
    )

    # Biases
    settings = replace(
        settings,
        gpu_full_variant_freq_mode=_get_str(cfg, "Biases", "VariantFreqMode", settings.gpu_full_variant_freq_mode),
        gpu_full_new_gear_penalty=_get_int(cfg, "Biases", "NewGearPenalty", settings.gpu_full_new_gear_penalty),
        gpu_full_synergy_weight=_get_int(cfg, "Biases", "SynergyWeight", settings.gpu_full_synergy_weight),
    )

    # Repair
    settings = replace(
        settings,
        gpu_full_repair_enabled=_get_bool(cfg, "Repair", "Enabled", settings.gpu_full_repair_enabled),
        gpu_full_repair_attempts=_get_int(cfg, "Repair", "Attempts", settings.gpu_full_repair_attempts),
        gpu_full_repair_max_cands_per_slot=_get_int(
            cfg, "Repair", "MaxCandsPerSlot", settings.gpu_full_repair_max_cands_per_slot
        ),
        gpu_full_repair_song_limit=_get_int(cfg, "Repair", "SongLimit", settings.gpu_full_repair_song_limit),
    )

    # Seed inventory
    settings = replace(
        settings,
        seed_inventory_variants_path=_get_str(
            cfg, "SeedInventory", "VariantsPath", settings.seed_inventory_variants_path
        ),
        seed_inventory_mode=_get_str(cfg, "SeedInventory", "Mode", settings.seed_inventory_mode) or "hard",
    )

    # Expert (optional; kept out of primary docs)
    settings = replace(
        settings,
        gpu_full_synergy_top_offsets=_get_int(
            cfg, "Expert", "SynergyTopOffsets", settings.gpu_full_synergy_top_offsets
        ),
        gpu_full_synergy_min_pair_count=_get_int(
            cfg, "Expert", "SynergyMinPairCount", settings.gpu_full_synergy_min_pair_count
        ),
        gpu_full_synergy_scale=_get_int(cfg, "Expert", "SynergyScale", settings.gpu_full_synergy_scale),
        gpu_full_synergy_max_bonus=_get_int(cfg, "Expert", "SynergyMaxBonus", settings.gpu_full_synergy_max_bonus),
        gpu_full_k_scan_select=_get_int(cfg, "Expert", "KScanSelect", settings.gpu_full_k_scan_select),
        gpu_full_k_scan_repack=_get_int(cfg, "Expert", "KScanRepack", settings.gpu_full_k_scan_repack),
        gpu_full_v_pad_bin=_get_int(cfg, "Expert", "VPadBin", settings.gpu_full_v_pad_bin),
        gpu_full_alns_enabled=_get_bool(cfg, "Expert", "ALNS", settings.gpu_full_alns_enabled),
        gpu_full_alns_islands=_get_int(cfg, "Expert", "ALNSIslands", settings.gpu_full_alns_islands),
        gpu_full_pt_enabled=_get_bool(cfg, "Expert", "PT", settings.gpu_full_pt_enabled),
        gpu_full_pt_t_min=_get_float(cfg, "Expert", "PT_T_Min", settings.gpu_full_pt_t_min),
        gpu_full_pt_t_max=_get_float(cfg, "Expert", "PT_T_Max", settings.gpu_full_pt_t_max),
        gpu_full_pt_swap_interval=_get_int(cfg, "Expert", "PT_SwapInterval", settings.gpu_full_pt_swap_interval),
        gpu_full_pt_destroy_beta=_get_float(cfg, "Expert", "PT_DestroyBeta", settings.gpu_full_pt_destroy_beta),
        gpu_full_pt_cap_slack_max=_get_int(cfg, "Expert", "PT_CapSlackMax", settings.gpu_full_pt_cap_slack_max),
        gpu_full_human_mode=_get_bool(cfg, "Expert", "Human", settings.gpu_full_human_mode),
        gpu_full_human_gear_penalty_step=_get_int(
            cfg, "Expert", "HumanGearPenaltyStep", settings.gpu_full_human_gear_penalty_step
        ),
        gpu_full_human_gear_free=_get_int(cfg, "Expert", "HumanGearFree", settings.gpu_full_human_gear_free),
        gpu_full_human_colored_penalty=_get_int(
            cfg, "Expert", "HumanColoredPenalty", settings.gpu_full_human_colored_penalty
        ),
        gpu_full_restricted_universe_path=_get_str(
            cfg, "Expert", "RestrictedUniversePath", settings.gpu_full_restricted_universe_path
        ),
    )

    meta = settings.to_effective_config_dict(
        quality=effective_quality, config_path=effective_path, set_overrides=set_overrides_list
    )
    return settings, meta, warnings


__all__ = [
    "InventoryMetaCoverageSettings",
    "default_inventory_meta_config_path",
    "load_inventory_meta_coverage_settings",
]
