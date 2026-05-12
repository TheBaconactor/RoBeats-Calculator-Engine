from __future__ import annotations

import hashlib
from typing import Any


def fg_selection_array_sig(
    arr: Any,
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    """
    Stable signature for FG top-K selection inputs (base_scores / keep_mask).

    We hash only the active prefix `[0:n_active)` because FG top-K kernels only
    consume the first `n_genomes` rows.
    """
    try:
        import numpy as np

        a = np.asarray(arr, dtype=np.int32)
    except (ValueError, TypeError):
        return ("obj", id(arr))

    if a.ndim == 0:
        try:
            return ("scalar", int(a))
        except (ValueError, TypeError):
            return ("scalar", repr(a))

    if a.ndim != 1:
        try:
            a = np.ravel(a)
        except (ValueError, TypeError):
            return ("obj", id(arr))

    try:
        n_total = int(a.shape[0])
    except (ValueError, TypeError, AttributeError):
        return ("obj", id(arr))

    n = max(0, min(int(n_active), int(n_total)))
    if n <= 0:
        return ("empty", int(n_total))

    view = a[:n]
    try:
        ptr = int(view.__array_interface__["data"][0])
    except (ValueError, TypeError, KeyError, AttributeError):
        ptr = int(id(view))
    try:
        strides = tuple(int(x) for x in (view.strides or ()))
    except (ValueError, TypeError, AttributeError):
        strides = ()
    cache_key = (int(id(a)), int(ptr), int(n), strides, str(view.dtype))

    if sig_cache is not None:
        cached = sig_cache.get(cache_key)
        if cached is not None:
            return cached

    if not view.flags["C_CONTIGUOUS"]:
        view = np.ascontiguousarray(view, dtype=np.int32)

    h = hashlib.blake2b(digest_size=12)
    h.update(memoryview(view).cast("B"))
    sig = ("arr", int(n), h.digest())

    if sig_cache is not None:
        sig_cache[cache_key] = sig
    return sig


def fg_selection_upload_key(
    payload: dict[str, Any],
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    """
    Content key for deciding whether top-K selection inputs must be re-uploaded.

    Using content signatures (instead of object identity only) allows reuse even
    when callers rebuild equivalent numpy arrays across adjacent payloads.
    """
    topk = int(payload.get("fg_download_topk", 0) or 0)
    base_scores = payload.get("fg_download_base_scores")
    keep_mask = payload.get("fg_download_keep_mask")
    keep_sig = (
        ("none", int(n_active))
        if keep_mask is None
        else fg_selection_array_sig(keep_mask, n_active=int(n_active), sig_cache=sig_cache)
    )
    return (
        int(n_active),
        int(topk),
        fg_selection_array_sig(base_scores, n_active=int(n_active), sig_cache=sig_cache),
        keep_sig,
    )
