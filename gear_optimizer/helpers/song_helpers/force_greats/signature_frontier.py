from __future__ import annotations

import os

import numpy as np

from gear_optimizer.core.fallback_monitor import warn_fallback


def resolve_signature_frontier_limit(*, loadouts_per_song_limit: int) -> int:
    raw = str(os.environ.get("FG_SIGNATURE_FRONTIER_LIMIT", "") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except Exception:
            return 0

    try:
        mult = int(os.environ.get("FG_SIGNATURE_FRONTIER_MULT", "2") or 2)
    except Exception:
        mult = 2
    mult = max(1, int(mult))
    return max(int(loadouts_per_song_limit), int(loadouts_per_song_limit) * int(mult))


def signature_timing_bucket(sig: object) -> tuple[str, str, str, int]:
    if not isinstance(sig, tuple) or len(sig) < 4:
        return ("", "", "", 0)

    try:
        apply_to = str(sig[-4] or "")
        distribution = str(sig[-3] or "")
        great_mode = str(sig[-2] or "")
        seed = int(sig[-1] or 0)
    except Exception:
        return ("", "", "", 0)

    if not apply_to:
        return ("", "", "", 0)
    return (apply_to, distribution, great_mode, int(seed))


def build_signature_frontier_metas_from_rows(
    rows: list[dict],
    *,
    keep_sigs: set[str] | None = None,
    center_bin: int = 2,
) -> list[dict]:
    try:
        center_bin_i = max(1, int(center_bin))
    except Exception:
        center_bin_i = 2

    force_keep = keep_sigs or set()
    metas: list[dict] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        sig = row.get("sig")
        if sig is None:
            continue
        center = row.get("center")
        if not (isinstance(center, (tuple, list)) and len(center) >= 2):
            center = (0, 0)
        try:
            center_ft = int(center[0] or 0)
        except Exception:
            center_ft = 0
        try:
            center_ff = int(center[1] or 0)
        except Exception:
            center_ff = 0

        timing_bucket = row.get("timing_bucket")
        if not (isinstance(timing_bucket, (tuple, list)) and len(timing_bucket) >= 4):
            timing_bucket = signature_timing_bucket(sig)

        metas.append(
            {
                "sig": sig,
                "base": int(row.get("base", 0) or 0),
                "proxy": int(row.get("proxy", 0) or 0),
                "priority": int(row.get("priority", 0) or 0),
                "center": (int(center_ft), int(center_ff)),
                "center_bucket": (int(center_ft // center_bin_i), int(center_ff // center_bin_i)),
                "timing_bucket": tuple(timing_bucket[:4]) if isinstance(timing_bucket, (tuple, list)) else ("", "", "", 0),
                "force_keep": str(sig) in force_keep,
                "idx": int(idx),
            }
        )
    return metas


def build_signature_frontier_metas(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
) -> list[dict]:
    try:
        center_bin_i = max(1, int(center_bin))
    except Exception:
        center_bin_i = 2

    force_keep = keep_sigs or set()
    metas: list[dict] = []
    for idx, sig in enumerate(sigs):
        rep = rep_map.get(sig)
        if not isinstance(rep, dict):
            continue
        try:
            base_i = int(base_score_map.get(sig, 0) or 0)
        except Exception:
            base_i = 0
        try:
            proxy_i = int(fg_proxy_map.get(sig, 0) or 0)
        except Exception:
            proxy_i = 0

        priority_i = 0
        try:
            rows = sig_map.get(sig) or []
        except Exception:
            rows = []
        for item in rows:
            entry = None
            if isinstance(item, (tuple, list)) and item:
                entry = item[0]
            elif isinstance(item, dict):
                entry = item
            if not isinstance(entry, dict):
                continue
            try:
                priority_i = max(priority_i, int(entry.get("_fg_priority", 0) or 0))
            except Exception:
                continue

        try:
            center_ft = int(rep.get("Fever Time", 0) or 0)
        except Exception:
            center_ft = 0
        try:
            center_ff = int(rep.get("Fever Fill Rate", 0) or 0)
        except Exception:
            center_ff = 0

        metas.append(
            {
                "sig": sig,
                "base": int(base_i),
                "proxy": int(proxy_i),
                "priority": int(priority_i),
                "center": (int(center_ft), int(center_ff)),
                "center_bucket": (int(center_ft // center_bin_i), int(center_ff // center_bin_i)),
                "timing_bucket": signature_timing_bucket(sig),
                "force_keep": str(sig) in force_keep,
                "idx": int(idx),
            }
        )

    return metas


def select_signature_frontier_cpu_from_metas(
    metas: list[dict],
    *,
    limit: int,
    loadouts_per_song_limit: int,
) -> list:
    try:
        limit_i = int(limit)
    except Exception:
        limit_i = 0
    if limit_i <= 0 or len(metas) <= limit_i:
        return [m["sig"] for m in metas]

    metas_by_base = sorted(metas, key=lambda m: (-m["base"], -m["proxy"], -m["priority"], m["idx"]))
    metas_by_fg = sorted(
        metas,
        key=lambda m: (
            -int(bool(m["force_keep"])),
            -m["priority"],
            -m["proxy"],
            -m["base"],
            m["idx"],
        ),
    )

    selected: list = []
    seen: set = set()
    seen_center_buckets: set[tuple[int, int]] = set()
    seen_timing_buckets: set[tuple[str, str, str, int]] = set()

    def _add(meta: dict) -> bool:
        sig = meta["sig"]
        if sig in seen:
            return False
        seen.add(sig)
        selected.append(sig)
        seen_center_buckets.add(meta["center_bucket"])
        if meta["timing_bucket"] != ("", "", ""):
            seen_timing_buckets.add(meta["timing_bucket"])
        return True

    top_base_keep = min(limit_i, int(loadouts_per_song_limit))
    extra_budget = max(0, int(limit_i - top_base_keep))
    keep_budget = min(extra_budget, max(2, extra_budget // 2)) if extra_budget > 0 else 0
    keep_budget_end = min(limit_i, top_base_keep + keep_budget)
    priority_budget = min(max(0, limit_i - keep_budget_end), max(2, min(5, extra_budget))) if extra_budget > 0 else 0
    priority_budget_end = min(limit_i, keep_budget_end + priority_budget)
    fg_budget_end = min(limit_i, max(priority_budget_end, top_base_keep + max(priority_budget, int(extra_budget * 0.85))))

    for meta in metas_by_base:
        if len(selected) >= top_base_keep:
            break
        _add(meta)

    for meta in metas_by_base:
        if len(selected) >= keep_budget_end:
            break
        if not meta["force_keep"]:
            continue
        _add(meta)

    for meta in metas_by_fg:
        if len(selected) >= priority_budget_end:
            break
        if not meta["priority"]:
            continue
        _add(meta)

    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        timing_bucket = meta["timing_bucket"]
        if timing_bucket != ("", "", "", 0) and timing_bucket not in seen_timing_buckets:
            _add(meta)

    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        if meta["center_bucket"] in seen_center_buckets:
            continue
        _add(meta)

    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        _add(meta)

    for meta in metas_by_base:
        if len(selected) >= limit_i:
            break
        _add(meta)

    return selected[:limit_i]


def select_signature_frontier_cpu(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
    loadouts_per_song_limit: int,
) -> list:
    metas = build_signature_frontier_metas(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_score_map,
        fg_proxy_map=fg_proxy_map,
        keep_sigs=keep_sigs,
        limit=limit,
        center_bin=center_bin,
    )
    return select_signature_frontier_cpu_from_metas(metas, limit=limit, loadouts_per_song_limit=loadouts_per_song_limit)


def select_signature_frontier(
    sigs: list,
    *,
    sig_map: dict,
    rep_map: dict,
    base_score_map: dict,
    fg_proxy_map: dict,
    keep_sigs: set[str] | None = None,
    limit: int,
    center_bin: int = 2,
    loadouts_per_song_limit: int,
    gpu_strict: bool,
) -> list:
    try:
        limit_i = int(limit)
    except Exception:
        limit_i = 0
    if limit_i <= 0 or len(sigs) <= limit_i:
        return list(sigs)

    metas = build_signature_frontier_metas(
        sigs,
        sig_map=sig_map,
        rep_map=rep_map,
        base_score_map=base_score_map,
        fg_proxy_map=fg_proxy_map,
        keep_sigs=keep_sigs,
        limit=limit_i,
        center_bin=center_bin,
    )
    if len(metas) <= limit_i:
        return [m["sig"] for m in metas]

    try:
        top_base_keep = min(int(limit_i), int(loadouts_per_song_limit))
    except Exception:
        top_base_keep = int(limit_i)

    timing_bucket_ids: dict[tuple[str, str, str, int], int] = {}
    next_timing_bucket_id = 1
    base_scores: list[int] = []
    proxy_scores: list[int] = []
    priorities: list[int] = []
    force_keep_flags: list[int] = []
    center_ft: list[int] = []
    center_ff: list[int] = []
    timing_buckets: list[int] = []
    for meta in metas:
        base_scores.append(int(meta["base"]))
        proxy_scores.append(int(meta["proxy"]))
        priorities.append(int(meta["priority"]))
        force_keep_flags.append(1 if bool(meta["force_keep"]) else 0)
        ft_bucket, ff_bucket = meta["center_bucket"]
        center_ft.append(int(ft_bucket))
        center_ff.append(int(ff_bucket))
        timing_bucket = meta["timing_bucket"]
        if timing_bucket == ("", "", ""):
            timing_buckets.append(0)
            continue
        bucket_id = timing_bucket_ids.get(timing_bucket)
        if bucket_id is None:
            bucket_id = int(next_timing_bucket_id)
            timing_bucket_ids[timing_bucket] = bucket_id
            next_timing_bucket_id += 1
        timing_buckets.append(int(bucket_id))

    try:
        from gear_optimizer.solver.taichi_gem.force_greats.api import fg_select_signature_frontier_indices

        selected_indices = fg_select_signature_frontier_indices(
            base_scores=np.asarray(base_scores, dtype=np.int32),
            proxy_scores=np.asarray(proxy_scores, dtype=np.int32),
            priorities=np.asarray(priorities, dtype=np.int32),
            force_keep=np.asarray(force_keep_flags, dtype=np.int32),
            center_bucket_ft=np.asarray(center_ft, dtype=np.int32),
            center_bucket_ff=np.asarray(center_ff, dtype=np.int32),
            timing_bucket=np.asarray(timing_buckets, dtype=np.int32),
            limit=int(limit_i),
            top_base_keep=int(top_base_keep),
        )
    except Exception as exc:
        warn_fallback(
            "fg.signature_frontier.gpu",
            "GPU FG signature frontier selection failed; falling back to host selector",
            exc=exc,
            fatal=False,
        )
        if gpu_strict:
            raise
        return select_signature_frontier_cpu_from_metas(metas, limit=limit_i, loadouts_per_song_limit=loadouts_per_song_limit)

    out: list = []
    seen: set = set()
    for idx in list(np.asarray(selected_indices, dtype=np.int32)):
        i = int(idx)
        if i < 0 or i >= len(metas):
            continue
        sig = metas[i]["sig"]
        if sig in seen:
            continue
        seen.add(sig)
        out.append(sig)
    expected_n = min(int(limit_i), int(len(metas)))
    if len(out) < expected_n:
        exc = RuntimeError(f"GPU FG frontier returned {len(out)} signatures; expected {expected_n}")
        warn_fallback(
            "fg.signature_frontier.gpu_short",
            "GPU FG signature frontier selection returned an incomplete surface",
            exc=exc,
            fatal=False,
        )
        if gpu_strict:
            raise exc
        return select_signature_frontier_cpu_from_metas(metas, limit=limit_i, loadouts_per_song_limit=loadouts_per_song_limit)
    return out[:limit_i]


__all__ = [
    "build_signature_frontier_metas",
    "build_signature_frontier_metas_from_rows",
    "resolve_signature_frontier_limit",
    "select_signature_frontier",
    "select_signature_frontier_cpu",
    "select_signature_frontier_cpu_from_metas",
    "signature_timing_bucket",
]
