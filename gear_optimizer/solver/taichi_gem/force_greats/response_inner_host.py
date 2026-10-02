from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import os
import threading
import weakref
from typing import Any

import numpy as np

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    MAX_STAT,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)
from gear_optimizer.core.jit_setup import jit


_SURFACE_HEAD_COEFF_CACHE_MAX = 4
# The CPU FG gem search scores each group independently (it writes only that group's output row),
# so contiguous group chunks scored on separate threads and concatenated in order equal one call.
_FG_CPU_SEARCH_WORKERS = max(1, min(8, (os.cpu_count() or 1)))
_FG_CPU_SEARCH_CHUNKS_PER_WORKER = 4
_FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK = 4
_fg_cpu_search_pool: ThreadPoolExecutor | None = None
_fg_cpu_search_pool_lock = threading.Lock()
_U16_HEAD_VALUES = np.arange(1 << 16, dtype=np.uint16)
_U16_HEAD_BITS = np.unpackbits(_U16_HEAD_VALUES.view(np.uint8).reshape(-1, 2), axis=1, bitorder="little").astype(
    np.int32,
    copy=False,
)
_U16_HEAD_COUNT = np.ascontiguousarray(np.sum(_U16_HEAD_BITS, axis=1, dtype=np.int32), dtype=np.int32)
_U16_HEAD_POS_SUM = np.ascontiguousarray(
    np.sum(_U16_HEAD_BITS * np.arange(1, 17, dtype=np.int32).reshape(1, 16), axis=1, dtype=np.int32),
    dtype=np.int32,
)
del _U16_HEAD_BITS
_SURFACE_HEAD_COEFF_CACHE: OrderedDict[tuple[int, int, tuple[int, ...], tuple[int, ...]], np.ndarray] = OrderedDict()
_SURFACE_HEAD_COEFF_CACHE_LOCK = threading.RLock()


def _color_flags(primary_color: str, secondary_color: str, selected_color: str) -> tuple[int, ...]:
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = str(selected_color or "")
    return (
        int(primary == "Chill"),
        int(secondary == "Chill"),
        int(primary == "Flow"),
        int(secondary == "Flow"),
        int(primary == "Rush"),
        int(secondary == "Rush"),
        int(primary == selected and bool(selected)),
        int(secondary == selected and bool(selected)),
    )


def _precompute_surface_head_coeffs(
    surface_words: np.ndarray,
    *,
    head_len: int,
) -> np.ndarray:
    source = np.asarray(surface_words)
    cacheable = bool(source.dtype == np.uint32 and source.flags.c_contiguous)
    words = source if cacheable else np.ascontiguousarray(source, dtype=np.uint32)
    key = (int(id(words)), int(head_len), tuple(int(v) for v in words.shape), tuple(int(v) for v in words.strides))
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            cached = _SURFACE_HEAD_COEFF_CACHE.get(key)
            if cached is not None:
                _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
                return cached
    row_count = int(words.shape[0])
    coeffs = np.zeros((row_count, 4), dtype=np.int32)
    head = max(0, min(int(head_len), 100))
    if row_count > 0 and head > 0:
        if int(words.ndim) != 2 or int(words.shape[1]) < 4:
            raise ValueError("response frontier GPU head-coeff precompute requires packed fever words")
        for block in range(4):
            start = int(block * 32)
            if start >= int(head):
                break
            take = min(32, int(head) - int(start))
            if take <= 0:
                continue
            block_words = np.asarray(words[:, block], dtype=np.uint32)
            low_take = min(16, int(take))
            low_mask = (1 << int(low_take)) - 1
            low = np.asarray(block_words & np.uint32(low_mask), dtype=np.uint16)
            fever_count = np.asarray(_U16_HEAD_COUNT[low], dtype=np.int32)
            local_sigma_hf = np.asarray(_U16_HEAD_POS_SUM[low], dtype=np.int32)
            if int(take) > 16:
                high_take = int(take) - 16
                high_mask = (1 << int(high_take)) - 1
                high = np.asarray((block_words >> np.uint32(16)) & np.uint32(high_mask), dtype=np.uint16)
                high_count = np.asarray(_U16_HEAD_COUNT[high], dtype=np.int32)
                fever_count = np.asarray(fever_count + high_count, dtype=np.int32)
                local_sigma_hf = np.asarray(
                    local_sigma_hf + _U16_HEAD_POS_SUM[high] + (16 * high_count),
                    dtype=np.int32,
                )
            coeffs[:, 1] += fever_count
            coeffs[:, 0] += int(take) - fever_count
            sigma_hf = np.asarray(local_sigma_hf + (int(start) * fever_count), dtype=np.int32)
            coeffs[:, 3] += sigma_hf
            sigma_total = int(take) * ((2 * int(start)) + int(take) + 1) // 2
            coeffs[:, 2] += int(sigma_total) - sigma_hf
    coeffs = np.ascontiguousarray(coeffs, dtype=np.int32)
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            _SURFACE_HEAD_COEFF_CACHE[key] = coeffs
            _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
            while len(_SURFACE_HEAD_COEFF_CACHE) > int(_SURFACE_HEAD_COEFF_CACHE_MAX):
                _SURFACE_HEAD_COEFF_CACHE.popitem(last=False)
        # The key embeds id(words): it identifies THIS array only while the array is alive.
        # Once the pool is garbage-collected the id can be reused by a new same-shaped pool
        # (stale-hit hazard) and the retained coeffs are unreachable dead weight (~370 MB per
        # 23M-row pool in prebuild workers). Evict the entry the moment the source dies.
        weakref.finalize(words, _evict_surface_head_coeff_entry, key)
    return coeffs


def _evict_surface_head_coeff_entry(key: tuple[int, int, tuple[int, ...], tuple[int, ...]]) -> None:
    with _SURFACE_HEAD_COEFF_CACHE_LOCK:
        _SURFACE_HEAD_COEFF_CACHE.pop(key, None)


@jit(nopython=True, cache=True)
def _fg_clamp_ref_idx_native(idx, total_rows):
    if idx < 0:
        return 0
    if idx > total_rows:
        return total_rows
    return idx


@jit(nopython=True, cache=True)
def _fg_response_upper_bound_native_f64(
    base_value,
    combo_mul,
    fever_mul,
    body_fever,
    body_normal,
    n_hn,
    n_hf,
    sigma_hn,
    sigma_hf,
):
    """f64 CPU port of ``_fg_response_surface_upper_bound`` (the gem-search prune bound)."""
    ub_eps = 1024.0
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_upper = base_value * (float(n_hn) + fever_mul * float(n_hf)) + factor * (
        float(sigma_hn) + fever_mul * float(sigma_hf)
    )
    return float(body_score) + head_upper + ub_eps


@jit(nopython=True, cache=True)
def _fg_response_surface_score_native_f64(
    surface_words,
    sr,
    body_fever,
    body_great,
    body_fever_great,
    head_len,
    body_total,
    primary_val,
    secondary_val,
    pp_factor,
    combo_mul,
    fever_mul,
):
    """f64 CPU port of ``_fg_response_score_device``: exact score of one surface for a fixed
    (gem-allocated) stat line. Same op order / per-term ``floor`` / i32 accumulation as the
    GPU device function, run in CPU doubles (no MoltenVK shaderFloat64 needed)."""
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0

    great_or = (
        int(surface_words[sr, 4])
        | int(surface_words[sr, 5])
        | int(surface_words[sr, 6])
        | int(surface_words[sr, 7])
    )
    great_base = 0.0
    if body_great > 0 or great_or != 0:
        great_head_base = (
            int(np.floor(float(primary_val) * (4.0 / 3.0)))
            + int(np.floor(float(secondary_val) * (2.0 / 3.0)))
            + 150
        )
        great_base = float(great_head_base)
        great_combo_val = int(np.floor(great_base * combo_mul))
        great_fever_val = int(np.floor(great_base * combo_mul * fever_mul))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty

    for i in range(head_len):
        wi = i >> 5
        b = i & 31
        is_fever = (int(surface_words[sr, wi]) >> b) & 1
        scaling = combo_slope * float(i + 1) + 1.0
        if is_fever != 0:
            perfect_val = int(np.floor(base_value * scaling * fever_mul))
        else:
            perfect_val = int(np.floor(base_value * scaling))

        if ((int(surface_words[sr, 4 + wi]) >> b) & 1) != 0:
            if is_fever != 0:
                great_val = int(np.floor(great_base * scaling * fever_mul))
            else:
                great_val = int(np.floor(great_base * scaling))
            perfect_val = min(perfect_val, great_val)
        score += perfect_val
    return score


@jit(nopython=True, cache=True)
def _score_fg_response_groups_native_f64(
    group_offsets,
    group_lengths,
    row_meta,
    surface_pattern_ids,
    surface_pattern_words,
    surface_counts,
    surface_pattern_head_coeffs,
    color_flags,
    ref_pp,
    ref_cm,
    ref_fm,
    allow_pp,
    total_rows,
):
    """The FG inner response scoring in native f64, INCLUDING the gem search.

    Bit-for-bit f64 port of the GPU owner kernel: per group it enumerates the same gem
    allocations (the g_cm/g_fm/g_pp partition of ``residual_budget``) with the identical
    upper-bound prune, lexicographic tie-break, and per-term ``floor`` op order, scores every
    candidate surface, and keeps the group argmax. Runs in CPU doubles so it needs no GPU
    shaderFloat64 (MoltenVK/Metal has none, where the f32 GPU search mis-floors the razor-thin
    greats argmax and drops every FG candidate). ``residual_budget == 0`` collapses to a single
    allocation == current stats, identical to the prior gems-fixed serving twin.

    Output columns: [best_score, best_surface, g_pp, g_cm, g_fm, g_ov,
    final_pp, final_cm, final_fm, final_primary, final_secondary].
    """
    group_count = int(row_meta.shape[0])
    out = np.zeros((group_count, 11), dtype=np.int64)

    is_p_pp = int(color_flags[0])
    is_s_pp = int(color_flags[1])
    is_p_cm = int(color_flags[2])
    is_s_cm = int(color_flags[3])
    is_p_fm = int(color_flags[4])
    is_s_fm = int(color_flags[5])
    is_p_ov = int(color_flags[6])
    is_s_ov = int(color_flags[7])

    pp_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_pp
    pp_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_pp
    cm_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_cm
    cm_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_cm
    fm_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_fm
    fm_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_fm
    ov_p_delta = ELEMENT_GEM_GAIN * is_p_ov
    ov_s_delta = ELEMENT_GEM_GAIN * is_s_ov
    w_pp = (pp_p_delta << 1) + pp_s_delta
    w_cm = (cm_p_delta << 1) + cm_s_delta
    w_fm = (fm_p_delta << 1) + fm_s_delta
    w_ov = (ov_p_delta << 1) + ov_s_delta
    delta_pp_vs_ov = w_pp - w_ov
    pp_primary_delta = pp_p_delta - ov_p_delta
    pp_secondary_delta = pp_s_delta - ov_s_delta

    for g in range(group_count):
        residual_budget = int(row_meta[g, 0])
        cur_pp = int(row_meta[g, 1])
        cur_cm = int(row_meta[g, 2])
        cur_fm = int(row_meta[g, 3])
        cur_primary = int(row_meta[g, 4])
        cur_secondary = int(row_meta[g, 5])
        head_len = int(row_meta[g, 6])
        body_total = int(row_meta[g, 7])
        if head_len > 100:
            head_len = 100

        max_pp_gems = 0
        if allow_pp and cur_pp < MAX_STAT:
            rem_pp = MAX_STAT - cur_pp
            max_pp_gems = rem_pp // STAT_GEM_GAIN_NORMAL
            if rem_pp % STAT_GEM_GAIN_NORMAL != 0:
                max_pp_gems += 1
        max_cm_gems = 0
        if cur_cm < MAX_STAT:
            rem_cm = MAX_STAT - cur_cm
            max_cm_gems = rem_cm // STAT_GEM_GAIN_NORMAL
            if rem_cm % STAT_GEM_GAIN_NORMAL != 0:
                max_cm_gems += 1
        max_fm_gems = 0
        if cur_fm < MAX_STAT:
            rem_fm = MAX_STAT - cur_fm
            max_fm_gems = rem_fm // STAT_GEM_GAIN_FEVER
            if rem_fm % STAT_GEM_GAIN_FEVER != 0:
                max_fm_gems += 1
        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        base_init = (cur_primary << 1) + cur_secondary
        pp_ref_base = ref_pp[_fg_clamp_ref_idx_native(cur_pp, total_rows)]
        cm_ref_cache = np.empty(max_cm_gems + 1, dtype=np.float64)
        for gc in range(max_cm_gems + 1):
            cm_ref_cache[gc] = ref_cm[_fg_clamp_ref_idx_native(cur_cm + gc * STAT_GEM_GAIN_NORMAL, total_rows)]
        fm_ref_cache = np.empty(max_fm_gems + 1, dtype=np.float64)
        for gf in range(max_fm_gems + 1):
            fm_ref_cache[gf] = ref_fm[_fg_clamp_ref_idx_native(cur_fm + gf * STAT_GEM_GAIN_FEVER, total_rows)]
        pp_ref_cache = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_bound_prefix_max = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_ref_cache[0] = pp_ref_base
        pp_bound_prefix_max[0] = pp_ref_base
        if allow_pp:
            running = -1.0e30
            for gp in range(max_pp_gems + 1):
                v = ref_pp[_fg_clamp_ref_idx_native(cur_pp + gp * STAT_GEM_GAIN_NORMAL, total_rows)]
                pp_ref_cache[gp] = v
                bound = float(gp * delta_pp_vs_ov) + v
                if bound > running:
                    running = bound
                pp_bound_prefix_max[gp] = running

        group_best_score = -1
        group_best_surface = 0
        group_best_pp = 0
        group_best_cm = 0
        group_best_fm = 0
        group_best_ov = residual_budget
        group_best_final_pp = cur_pp
        group_best_final_cm = cur_cm
        group_best_final_fm = cur_fm
        group_best_final_primary = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary = cur_secondary + group_best_ov * ov_s_delta

        start = int(group_offsets[g])
        length = int(group_lengths[g])
        for ls in range(length):
            sr = start + ls
            pattern_row = int(surface_pattern_ids[sr])
            body_fever = int(surface_counts[sr, 0])
            body_great = int(surface_counts[sr, 1])
            body_fever_great = int(surface_counts[sr, 2])
            body_normal = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
            n_hn = int(surface_pattern_head_coeffs[pattern_row, 0])
            n_hf = int(surface_pattern_head_coeffs[pattern_row, 1])
            sigma_hn = int(surface_pattern_head_coeffs[pattern_row, 2])
            sigma_hf = int(surface_pattern_head_coeffs[pattern_row, 3])

            best_score = group_best_score
            best_pp = group_best_pp
            best_cm = group_best_cm
            best_fm = group_best_fm
            best_ov = group_best_ov
            best_final_pp = group_best_final_pp
            best_final_cm = group_best_final_cm
            best_final_fm = group_best_final_fm
            best_final_primary = group_best_final_primary
            best_final_secondary = group_best_final_secondary

            g_cm = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat = cur_cm + g_cm * STAT_GEM_GAIN_NORMAL
                cm_mul = cm_ref_cache[g_cm]
                g_fm_max = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_stat = cur_fm + g_fm * STAT_GEM_GAIN_FEVER
                    fm_mul = fm_ref_cache[g_fm]
                    g_pp_max = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm

                    base_linear_common = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    if allow_pp:
                        max_base_value = float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                    else:
                        max_base_value = float(base_linear_common) + pp_ref_base
                    ub = _fg_response_upper_bound_native_f64(
                        max_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                    )

                    if ub > float(best_score):
                        primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        secondary_base = (
                            cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        )
                        if allow_pp and max_pp_gems > 0:
                            g_pp = 0
                            record_base_value = -1.0e30
                            while g_pp <= g_pp_max:
                                g_ov = leftover_after_fm - g_pp
                                pp_stat = cur_pp + g_pp * STAT_GEM_GAIN_NORMAL
                                primary_val = primary_base + g_pp * pp_primary_delta
                                secondary_val = secondary_base + g_pp * pp_secondary_delta
                                pp_base_value = float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                                # Great bases are nonincreasing only when both coordinates are.
                                if pp_primary_delta <= 0 and pp_secondary_delta <= 0:
                                    if pp_base_value <= record_base_value:
                                        g_pp += 1
                                        continue
                                    record_base_value = pp_base_value
                                pp_ub = _fg_response_upper_bound_native_f64(
                                    pp_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                                )
                                if pp_ub >= float(best_score):
                                    score = _fg_response_surface_score_native_f64(
                                        surface_pattern_words,
                                        pattern_row,
                                        body_fever,
                                        body_great,
                                        body_fever_great,
                                        head_len,
                                        body_total,
                                        primary_val,
                                        secondary_val,
                                        pp_ref_cache[g_pp],
                                        cm_mul,
                                        fm_mul,
                                    )
                                    if score > best_score or (
                                        score == best_score
                                        and (
                                            g_cm < best_cm
                                            or (
                                                g_cm == best_cm
                                                and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
                                            )
                                        )
                                    ):
                                        best_score = score
                                        best_pp = g_pp
                                        best_cm = g_cm
                                        best_fm = g_fm
                                        best_ov = g_ov
                                        best_final_pp = pp_stat
                                        best_final_cm = cm_stat
                                        best_final_fm = fm_stat
                                        best_final_primary = primary_val
                                        best_final_secondary = secondary_val
                                g_pp += 1
                        else:
                            pp_factor = pp_ref_cache[0] if allow_pp else pp_ref_base
                            score = _fg_response_surface_score_native_f64(
                                surface_pattern_words,
                                pattern_row,
                                body_fever,
                                body_great,
                                body_fever_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_factor,
                                cm_mul,
                                fm_mul,
                            )
                            if score > best_score or (
                                score == best_score
                                and (
                                    g_cm < best_cm
                                    or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                )
                            ):
                                best_score = score
                                best_pp = 0
                                best_cm = g_cm
                                best_fm = g_fm
                                best_ov = leftover_after_fm
                                best_final_pp = cur_pp
                                best_final_cm = cm_stat
                                best_final_fm = fm_stat
                                best_final_primary = primary_base
                                best_final_secondary = secondary_base
                    g_fm += 1
                g_cm += 1

            if best_score > group_best_score:
                group_best_score = best_score
                group_best_surface = ls
                group_best_pp = best_pp
                group_best_cm = best_cm
                group_best_fm = best_fm
                group_best_ov = best_ov
                group_best_final_pp = best_final_pp
                group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm
                group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary

        out[g, 0] = group_best_score
        out[g, 1] = group_best_surface
        out[g, 2] = group_best_pp
        out[g, 3] = group_best_cm
        out[g, 4] = group_best_fm
        out[g, 5] = group_best_ov
        out[g, 6] = group_best_final_pp
        out[g, 7] = group_best_final_cm
        out[g, 8] = group_best_final_fm
        out[g, 9] = group_best_final_primary
        out[g, 10] = group_best_final_secondary
    return out


def _score_response_group_meta_cpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    curves: StatCurves,
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_pattern_head_coeffs: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Score the FG response groups in exact native f64, for the gems-fixed (zero_ms / total_budget == 0) serving
    path and the gem-search (total_budget > 0) optimizer path: the gem-allocation enumeration, the upper-bound prune
    and the lexicographic tie-break, parallelized over CPU cores. Returns the per-group result rows and the number
    of logical surface rows scored."""
    group_count = int(group_meta.shape[0])
    if group_count != int(group_offsets.shape[0]) or group_count != int(group_lengths.shape[0]):
        raise ValueError("response frontier CPU group metadata arrays have inconsistent lengths")
    logical_surface_rows = int(np.sum(group_lengths, dtype=np.int64))
    if logical_surface_rows <= 0:
        return np.zeros((0, 11), dtype=np.int32), 0

    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    if int(group_meta_all.shape[1]) < 8:
        raise ValueError("response frontier CPU group metadata requires head/body columns")

    flags = _color_flags(primary_color, secondary_color, selected_color)
    color_flags_all = np.ascontiguousarray(np.asarray(flags, dtype=np.int32))
    # PP gems are the Chill element; the GPU search only enumerates PP gems when the song
    # carries a Chill color (flags[0]/[1]). Mirror that gate exactly.
    allow_pp = bool(int(flags[0]) != 0 or int(flags[1]) != 0)
    # CPU exact-rescore path stays float64 (the numba scorer is the f64 authority), independent
    # of the GPU search fp.
    ref_pp = np.ascontiguousarray(np.asarray(curves.f64["Perfect Points"], dtype=np.float64))
    ref_cm = np.ascontiguousarray(np.asarray(curves.f64["Combo Multiplier"], dtype=np.float64))
    ref_fm = np.ascontiguousarray(np.asarray(curves.f64["Fever Multiplier"], dtype=np.float64))
    surface_pattern_ids_all = np.ascontiguousarray(surface_pattern_ids, dtype=np.int32)
    surface_pattern_words_all = np.ascontiguousarray(surface_pattern_words, dtype=np.uint32)
    surface_counts_all = np.ascontiguousarray(surface_counts, dtype=np.int32)
    surface_pattern_head_coeffs_all = np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32)
    if int(surface_pattern_ids_all.shape[0]) != int(surface_counts_all.shape[0]):
        raise ValueError("response frontier CPU surface arrays have inconsistent lengths")
    if (
        int(surface_pattern_ids_all.ndim) != 1
        or int(surface_pattern_words_all.ndim) != 2
        or int(surface_pattern_words_all.shape[1]) != 8
        or int(surface_counts_all.ndim) != 2
        or int(surface_counts_all.shape[1]) != 3
        or int(surface_pattern_head_coeffs_all.ndim) != 2
        or int(surface_pattern_head_coeffs_all.shape[0]) != int(surface_pattern_words_all.shape[0])
        or int(surface_pattern_head_coeffs_all.shape[1]) != 4
    ):
        raise ValueError("response frontier CPU surface arrays have invalid shape")
    if bool(np.any(surface_pattern_ids_all < 0)) or bool(
        np.any(surface_pattern_ids_all >= int(surface_pattern_words_all.shape[0]))
    ):
        raise ValueError("response frontier CPU surface references an invalid head-pattern ID")
    if bool(np.any(surface_counts_all < 0)):
        raise ValueError("response frontier CPU surface counts must be nonnegative")

    head_lengths = np.unique(np.ascontiguousarray(group_meta_all[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier CPU group metadata has inconsistent head length")
    out_rows = _score_fg_response_groups_on_cpu_cores(
        np.ascontiguousarray(group_offsets, dtype=np.int64),
        np.ascontiguousarray(group_lengths, dtype=np.int64),
        group_meta_all,
        (
            surface_pattern_ids_all,
            surface_pattern_words_all,
            surface_counts_all,
            surface_pattern_head_coeffs_all,
            color_flags_all,
            ref_pp,
            ref_cm,
            ref_fm,
            bool(allow_pp),
            int(MAX_STAT),
        ),
    )
    return np.asarray(out_rows, dtype=np.int32), int(logical_surface_rows)


def _fg_cpu_search_executor() -> ThreadPoolExecutor:
    global _fg_cpu_search_pool
    with _fg_cpu_search_pool_lock:
        if _fg_cpu_search_pool is None:
            _fg_cpu_search_pool = ThreadPoolExecutor(
                max_workers=_FG_CPU_SEARCH_WORKERS, thread_name_prefix="fg-cpu-search"
            )
        return _fg_cpu_search_pool


def _score_fg_response_groups_on_cpu_cores(
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    group_meta: np.ndarray,
    shared_args: tuple[Any, ...],
) -> np.ndarray:
    """``_score_fg_response_groups_native_f64`` over contiguous group chunks on several cores.

    Chunks hold roughly equal surface rows (the search cost) and outnumber the workers so uneven
    groups still balance. Output rows come back in group order, identical to a single call.
    """
    group_count = int(group_meta.shape[0])
    chunk_count = min(
        _FG_CPU_SEARCH_WORKERS * _FG_CPU_SEARCH_CHUNKS_PER_WORKER,
        group_count // _FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK,
    )
    if _FG_CPU_SEARCH_WORKERS <= 1 or chunk_count <= 1:
        return _score_fg_response_groups_native_f64(group_offsets, group_lengths, group_meta, *shared_args)
    cumulative = np.cumsum(group_lengths, dtype=np.int64)
    targets = cumulative[-1] * np.arange(1, chunk_count, dtype=np.int64) // chunk_count
    cuts = np.unique(np.concatenate(([0], np.searchsorted(cumulative, targets, side="right"), [group_count])))
    futures = [
        _fg_cpu_search_executor().submit(
            _score_fg_response_groups_native_f64,
            group_offsets[start:stop],
            group_lengths[start:stop],
            group_meta[start:stop],
            *shared_args,
        )
        for start, stop in zip(cuts[:-1], cuts[1:])
        if stop > start
    ]
    return np.concatenate([future.result() for future in futures], axis=0)
