from __future__ import annotations

from gear_optimizer.core.utils import safe_int


def _attach_hitsim_delta_for_base(best_data: dict | None, calc_song: dict | None, ref_arrays: dict | None) -> None:
    if not isinstance(best_data, dict) or not best_data:
        return
    if "hitsim_offset_deltas_ms" in best_data:
        try:
            if best_data.get("hitsim_offset_deltas_ms") is not None:
                return
        except Exception:
            return
    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return
    try:
        from gear_optimizer.solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_base

        deltas = summarize_hitsim_offset_deltas_ms_for_base(calc_song, best_data, ref_arrays)
        if deltas:
            try:
                deltas_out = [int(x) for x in deltas]
            except Exception:
                deltas_out = []
            if deltas_out:
                best_data["hitsim_offset_deltas_ms"] = deltas_out
                best_data.pop("hitsim_offset_delta_ms", None)
    except Exception:
        return


def _nonfever_counts_from_config_for_hitsim(config: object) -> tuple[int, ...]:
    if not isinstance(config, dict) or not config:
        return ()
    pairs: list[tuple[int, int]] = []
    for key, val in config.items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "").strip()) - 1
        except Exception:
            continue
        pairs.append((idx, max(0, safe_int(val, 0))))
    if not pairs:
        return ()
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    if max_idx < 0:
        return ()
    out = [0] * (max_idx + 1)
    for idx, cnt in pairs:
        if 0 <= idx < len(out):
            out[idx] = int(cnt)
    if sum(out) <= 0:
        return ()
    return tuple(int(v) for v in out)


def _materialize_fg_stats_for_hitsim(fg_data: dict) -> dict:
    if not isinstance(fg_data, dict):
        return {}
    try:
        from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
    except Exception:
        return {}
    stats = materialize_stats_from_payload(fg_data, mutate_payload=True)
    return stats if isinstance(stats, dict) else {}


def _attach_hitsim_delta_for_fg_variant(
    fg_variants: list[dict] | None,
    calc_song: dict | None,
    ref_arrays: dict | None,
) -> None:
    if not fg_variants or not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return

    try:
        from gear_optimizer.solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_fg_variant
    except Exception:
        return

    delta_cache: dict[tuple[int, int, tuple[int, ...]], tuple[int, ...]] = {}
    for variant in fg_variants or []:
        if not isinstance(variant, dict):
            continue

        fg_score = safe_int(variant.get("fg_score", 0), 0)
        base_score = safe_int(variant.get("score", 0), 0)
        if fg_score <= base_score:
            continue

        fg_data = variant.get("data") or {}
        if not isinstance(fg_data, dict):
            continue
        fg_meta = fg_data.get("ForceGreats") or {}
        if not isinstance(fg_meta, dict):
            continue

        existing_deltas = fg_meta.get("hitsim_offset_deltas_ms")
        if isinstance(existing_deltas, (list, tuple)) and existing_deltas:
            if "hitsim_offset_delta_ms" in fg_meta:
                fg_meta_out = dict(fg_meta)
                fg_meta_out.pop("hitsim_offset_delta_ms", None)
                fg_data["ForceGreats"] = fg_meta_out
            continue

        forced_counts = _nonfever_counts_from_config_for_hitsim(fg_meta.get("config") or {})
        if not forced_counts:
            continue

        stats = fg_data.get("Stats") or {}
        if not isinstance(stats, dict) or not stats:
            stats = _materialize_fg_stats_for_hitsim(fg_data)
        if not isinstance(stats, dict) or not stats:
            continue

        ff_stat = safe_int(stats.get("Fever Fill Rate", 0), 0)
        ft_stat = safe_int(stats.get("Fever Time", 0), 0)
        cache_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in forced_counts))

        deltas_t = delta_cache.get(cache_key)
        if deltas_t is None:
            try:
                computed = summarize_hitsim_offset_deltas_ms_for_fg_variant(calc_song, fg_data, ref_arrays)
            except Exception:
                computed = None
            if not computed:
                continue
            try:
                deltas_t = tuple(int(x) for x in computed)
            except Exception:
                deltas_t = None
            if not deltas_t:
                continue
            delta_cache[cache_key] = deltas_t

        fg_meta_out = dict(fg_meta)
        if fg_meta_out.get("hitsim_offset_deltas_ms") is None:
            fg_meta_out["hitsim_offset_deltas_ms"] = list(deltas_t)
        fg_meta_out.pop("hitsim_offset_delta_ms", None)
        fg_data["ForceGreats"] = fg_meta_out

        details_obj = fg_data.get("details")
        if isinstance(details_obj, dict):
            fg_det = details_obj.get("ForceGreats")
            if isinstance(fg_det, dict) and (
                fg_det.get("hitsim_offset_deltas_ms") is None
            ):
                fg_det_out = dict(fg_det)
                if fg_det_out.get("hitsim_offset_deltas_ms") is None:
                    fg_det_out["hitsim_offset_deltas_ms"] = list(deltas_t)
                fg_det_out.pop("hitsim_offset_delta_ms", None)
                details_out = dict(details_obj)
                details_out["ForceGreats"] = fg_det_out
                fg_data["details"] = details_out

        variant["data"] = fg_data
