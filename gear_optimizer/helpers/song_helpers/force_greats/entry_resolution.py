from __future__ import annotations

from typing import Any
import logging

from ..fg_config import extract_fg_config, has_valid_fg_config, is_nonzero_fg_config
from ..ga_entry_utils import candidate_genome_ids, entry_loadout_hash, ga_candidate_key



logger = logging.getLogger(__name__)
def entry_fg_score(entry: dict) -> int:
    try:
        return int(entry.get("fg_score", 0) or 0)
    except Exception as e:
        logger.debug(f"entry_resolution:entry_fg_score: {e}")
        return 0


def entry_base_score(entry: dict) -> int:
    try:
        return int(entry.get("base_score") or entry.get("score", 0) or 0)
    except Exception as e:
        logger.debug(f"entry_resolution:entry_base_score: {e}")
        return 0


def entry_fg_config_dict(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {}
    return extract_fg_config(entry.get("force"))


def is_valid_fg_config(cfg: dict) -> bool:
    return is_nonzero_fg_config(cfg)


def entry_has_valid_fg_config(entry: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    return has_valid_fg_config(entry.get("force"))


def build_direct_ga_entry_items(ga_candidates, *, ga_registry=None) -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for idx, candidate in enumerate(ga_candidates or []):
        if not isinstance(candidate, dict):
            continue
        eval_data = candidate.get("Data") or {}
        if not isinstance(eval_data, dict) or not eval_data:
            continue
        genome_ids = candidate_genome_ids(candidate)
        registry_obj = ga_registry if ga_registry is not None else candidate.get("_ga_registry")
        entry = {
            "gear": list(candidate.get("Gear") or []),
            "minis": list(candidate.get("Minis") or []),
            "score": int(candidate.get("BaseScore") or candidate.get("Score", 0) or 0),
            "base_score": int(candidate.get("BaseScore") or candidate.get("Score", 0) or 0),
            "details": {},
            "fg_score": int(candidate.get("fg_score", 0) or 0),
            "force": candidate.get("force"),
            "eval_data": eval_data,
            "_source": "ga",
            "_fg_direct_ga": True,
            "_candidate_ref": candidate,
        }
        try:
            entry["selected_element"] = str(eval_data.get("Selected Element", "") or "")
        except Exception as e:
            logger.debug(f"entry_resolution:build_direct_ga_entry_items: {e}")
            entry["selected_element"] = ""
        if genome_ids is not None:
            entry["ga_genome_ids"] = list(genome_ids)
        if registry_obj is not None:
            entry["_ga_registry"] = registry_obj

        key = None
        if entry.get("gear") or entry.get("minis"):
            try:
                key = str(entry_loadout_hash(entry) or "")
            except Exception as e:
                logger.debug(f"entry_resolution:build_direct_ga_entry_items: {e}")
                key = None
        if not key and genome_ids is not None:
            key = ga_candidate_key(genome_ids)
        if not key:
            key = f"ga-direct:{int(idx)}"
        items.append((str(key), entry))
    return items


def sig_results_has_fg_improvement(*, sig_results: dict, sigs: list[str]) -> bool:
    if not isinstance(sig_results, dict) or not sigs:
        return False
    for sig in sigs:
        row = sig_results.get(str(sig))
        if not isinstance(row, dict):
            continue
        force_obj = row.get("force")
        if not isinstance(force_obj, dict):
            continue
        if has_valid_fg_config(force_obj):
            try:
                if int(row.get("fg_score", 0) or 0) > int(row.get("base_score", 0) or 0):
                    return True
            except Exception as e:
                logger.debug(f"entry_resolution:sig_results_has_fg_improvement: {e}")
                continue
    return False


def selected_count(selected_indices: Any) -> int:
    if selected_indices is None:
        return 0
    try:
        return int(len(selected_indices))
    except Exception as e:
        logger.debug(f"entry_resolution:selected_count: {e}")
        try:
            return int(getattr(selected_indices, "shape", (0,))[0] or 0)
        except Exception as e:
            logger.debug(f"entry_resolution:selected_count: {e}")
            return 0
