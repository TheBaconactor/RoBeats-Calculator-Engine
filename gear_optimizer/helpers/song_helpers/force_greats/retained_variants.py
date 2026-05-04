from __future__ import annotations

from collections.abc import Callable

from ..ga_entry_utils import entry_loadout_hash, materialize_entry_names
from ..retention import select_retained_hashes
from . import result_application
from .entry_resolution import (
    entry_fg_config_dict,
    entry_fg_score,
    entry_has_valid_fg_config,
    is_valid_fg_config,
    merge_retained_direct_ga_entries,
)


def _resolved_sig_result(entry: dict, *, sig_results: dict, entry_sig: dict[int, str]) -> dict | None:
    try:
        return sig_results.get(str(entry_sig.get(int(id(entry)), "") or ""))
    except Exception:
        return None


def _resolved_fg_score(entry: dict, *, sig_results: dict, entry_sig: dict[int, str]) -> int:
    current = entry_fg_score(entry)
    if current > 0:
        return int(current)
    sig_row = _resolved_sig_result(entry, sig_results=sig_results, entry_sig=entry_sig)
    if not isinstance(sig_row, dict):
        return 0
    try:
        return int(sig_row.get("fg_score", 0) or 0)
    except Exception:
        return 0


def _resolved_fg_valid(entry: dict, *, sig_results: dict, entry_sig: dict[int, str]) -> bool:
    if entry_has_valid_fg_config(entry):
        return True
    sig_row = _resolved_sig_result(entry, sig_results=sig_results, entry_sig=entry_sig)
    if not isinstance(sig_row, dict):
        return False
    force_obj = sig_row.get("force")
    if not isinstance(force_obj, dict):
        return False
    return bool(entry_has_valid_fg_config({"force": force_obj}))


def retain_and_build_fg_variants(
    *,
    entry_items,
    sig_results: dict,
    entry_sig: dict[int, str],
    loadout_entries,
    direct_ga_items: list[tuple[str, dict]],
    loadouts_per_song_limit: int,
    entry_base_score_fn: Callable[[dict], int],
) -> list[dict]:
    items = list(entry_items)

    retained_hashes = select_retained_hashes(
        items,
        limit=int(loadouts_per_song_limit),
        base_score_fn=entry_base_score_fn,
        fg_score_fn=lambda entry: _resolved_fg_score(entry, sig_results=sig_results, entry_sig=entry_sig),
        fg_valid_fn=lambda entry: _resolved_fg_valid(entry, sig_results=sig_results, entry_sig=entry_sig),
    )

    for h, entry in items:
        if str(h) not in retained_hashes or not isinstance(entry, dict):
            continue
        sig_row = _resolved_sig_result(entry, sig_results=sig_results, entry_sig=entry_sig)
        if not isinstance(sig_row, dict):
            continue
        result_application.apply_signature_result_to_entry(entry=entry, sig_result=sig_row)

    merge_retained_direct_ga_entries(loadout_entries, direct_ga_items, retained_hashes)

    fg_variants: list[dict] = []
    seen_variant_hashes: set[str] = set()
    for h, entry in items:
        if str(h) not in retained_hashes:
            continue

        base_score_best = entry_base_score_fn(entry)
        fg_score = entry_fg_score(entry)

        try:
            fg_base_score_i = int((entry.get("fg_base_score") if isinstance(entry, dict) else 0) or 0)
        except Exception:
            fg_base_score_i = 0
        if fg_base_score_i <= 0:
            fg_base_score_i = int(base_score_best or 0)

        force_obj = entry.get("force") if isinstance(entry, dict) else None
        if not isinstance(force_obj, dict):
            continue
        cfg = entry_fg_config_dict(entry)
        if not is_valid_fg_config(cfg):
            continue
        gear_names, mini_names = materialize_entry_names(entry, mutate=True)
        loadout_hash = str(entry_loadout_hash(entry) or h)
        if loadout_hash in seen_variant_hashes:
            continue
        seen_variant_hashes.add(loadout_hash)
        fg_variants.append(
            {
                "data": force_obj,
                "gear": gear_names,
                "minis": mini_names,
                "score": fg_base_score_i,
                "fg_score": fg_score,
                "base_score": fg_base_score_i,
                "_entry_ref": entry,
                "_is_ga": str(entry.get("_source") or "") == "ga",
            }
        )

    try:
        fg_variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
    except Exception:
        pass

    return fg_variants
