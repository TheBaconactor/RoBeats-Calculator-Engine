from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from ..core.gem_defs import GEM_KEYS, STAT_KEYS

logger = logging.getLogger(__name__)

try:
    import orjson as _orjson
except Exception:  # pragma: no cover - optional dependency
    _orjson = None


def _json_dumps_compact(value: Any) -> str:
    """Serialize JSON using compact separators, with optional orjson acceleration."""
    if _orjson is not None:
        return _orjson.dumps(value).decode("utf-8")
    return json.dumps(value, separators=(",", ":"))


def _json_loads(value: Any) -> Any:
    """Deserialize JSON with optional orjson acceleration."""
    if value is None or value == "":
        return None
    if _orjson is not None:
        return _orjson.loads(value)
    return json.loads(value)


def _encode_uvarint(value: int) -> bytes:
    """Encode an unsigned integer as base-128 varint (little-endian groups)."""
    x = int(value)
    if x < 0:
        raise ValueError("uvarint cannot encode negative values")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(int(b | 0x80))
        else:
            out.append(int(b))
            break
    return bytes(out)


def _decode_uvarints(blob: bytes) -> list[int]:
    """Decode a sequence of base-128 varints from a bytes blob."""
    if not blob:
        return []
    out: list[int] = []
    x = 0
    shift = 0
    for b in blob:
        x |= (int(b) & 0x7F) << shift
        if int(b) & 0x80:
            shift += 7
            if shift > 63:
                raise ValueError("uvarint too large")
            continue
        out.append(int(x))
        x = 0
        shift = 0
    if shift:
        raise ValueError("truncated uvarint stream")
    return out


def _pack_id_list(ids: Sequence[int]) -> bytes:
    """Pack a list of positive integer IDs into a compact varint blob."""
    if not ids:
        return b""
    buf = bytearray()
    for v in ids:
        iv = int(v)
        if iv <= 0:
            continue
        buf += _encode_uvarint(iv)
    return bytes(buf)


def _unpack_id_list(blob: Any) -> list[int]:
    """Unpack a varint blob produced by `_pack_id_list`."""
    if not blob:
        return []
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return []
    try:
        return [int(v) for v in _decode_uvarints(bytes(blob)) if int(v) > 0]
    except Exception as e:
        logger.warning(f"database:_unpack_id_list: {e}")
        return []


def _pack_id_groups(groups: Sequence[Sequence[int]]) -> bytes:
    """
    Pack list-of-lists IDs using 0 as a group separator.

    IDs are expected to be positive (>=1). Separator is encoded as uvarint(0) i.e. one byte 0.
    """
    if not groups:
        return b""
    buf = bytearray()
    for g0 in groups:
        if not g0:
            continue
        for v in g0:
            iv = int(v)
            if iv <= 0:
                continue
            buf += _encode_uvarint(iv)
        buf += b"\x00"
    return bytes(buf)


def _unpack_id_groups(blob: Any) -> list[list[int]]:
    """Inverse of `_pack_id_groups`."""
    if not blob:
        return []
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return []
    try:
        values = _decode_uvarints(bytes(blob))
    except Exception as e:
        logger.warning(f"database:_unpack_id_groups: {e}")
        return []
    out: list[list[int]] = []
    cur: list[int] = []
    for v in values:
        iv = int(v)
        if iv == 0:
            if cur:
                out.append(cur)
            cur = []
            continue
        if iv > 0:
            cur.append(iv)
    if cur:
        out.append(cur)
    return out


def _pack_stats_for_storage(details: Any) -> Any:
    """
    Reduce JSON size by storing Stats as a short array under `details["st"]`.

    - Input: details["Stats"] is a dict with verbose keys.
    - Output: details["st"] is a fixed-order int list, and "Stats" is removed.
    """
    if not isinstance(details, dict) or not details:
        return details
    out = dict(details)
    stats = details.get("Stats")
    if isinstance(stats, dict) and stats and out.get("st") is None:
        arr: list[int] = []
        for k in STAT_KEYS:
            try:
                arr.append(int(stats.get(k, 0) or 0))
            except Exception as e:
                logger.warning(f"database:_pack_stats_for_storage: {e}")
                arr.append(0)
        out.pop("Stats", None)
        out["st"] = arr

    gems = details.get("GemCounts")
    if isinstance(gems, dict) and gems and out.get("gc") is None:
        packed_gems: list[int] = []
        gem_key_mask = 0
        for i, k in enumerate(GEM_KEYS):
            if k in gems:
                gem_key_mask |= 1 << i
            try:
                packed_gems.append(int(gems.get(k, 0) or 0))
            except Exception as e:
                logger.warning(f"database:_pack_stats_for_storage: {e}")
                packed_gems.append(0)
        out.pop("GemCounts", None)
        out["gc"] = packed_gems
        if gem_key_mask != (1 << len(GEM_KEYS)) - 1:
            out["gk"] = int(gem_key_mask)

    selected = out.pop("Selected Element", None)
    selected = out.pop("SelectedElement", selected)
    if selected:
        out["se"] = str(selected)

    primary = out.pop("Primary Color", None)
    primary = out.pop("PrimaryColor", primary)
    if primary:
        out["pc"] = str(primary)

    secondary = out.pop("Secondary Color", None)
    secondary = out.pop("SecondaryColor", secondary)
    if secondary:
        out["sc"] = str(secondary)

    if not out.get("ForceGreats"):
        out.pop("ForceGreats", None)
    out.pop("Difficulty", None)
    return out


def _unpack_stats_after_load(details: Any) -> Any:
    """Inverse of `_pack_stats_for_storage` (best-effort)."""
    if not isinstance(details, dict) or not details:
        return details
    out = dict(details)
    stats = details.get("Stats")
    st = details.get("st")
    if not (isinstance(stats, dict) and stats) and isinstance(st, (list, tuple)) and len(st) >= len(STAT_KEYS):
        out_stats: dict[str, int] = {}
        for i, k in enumerate(STAT_KEYS):
            try:
                out_stats[k] = int(st[i] or 0)
            except Exception as e:
                logger.warning(f"database:_unpack_stats_after_load: {e}")
                out_stats[k] = 0
        out["Stats"] = out_stats

    gems = details.get("GemCounts")
    gc = details.get("gc")
    if not (isinstance(gems, dict) and gems) and isinstance(gc, (list, tuple)) and len(gc) >= len(GEM_KEYS):
        try:
            gem_key_mask = int(details.get("gk", (1 << len(GEM_KEYS)) - 1) or 0)
        except Exception as e:
            logger.warning(f"database:_unpack_stats_after_load: {e}")
            gem_key_mask = (1 << len(GEM_KEYS)) - 1
        out_gems: dict[str, int] = {}
        for i, k in enumerate(GEM_KEYS):
            if (gem_key_mask & (1 << i)) == 0:
                continue
            try:
                out_gems[k] = int(gc[i] or 0)
            except Exception as e:
                logger.warning(f"database:_unpack_stats_after_load: {e}")
                out_gems[k] = 0
        out["GemCounts"] = out_gems

    if "SelectedElement" not in out and "Selected Element" not in out and out.get("se"):
        out["SelectedElement"] = str(out.get("se") or "")
    if "PrimaryColor" not in out and "Primary Color" not in out and out.get("pc"):
        out["PrimaryColor"] = str(out.get("pc") or "")
    if "SecondaryColor" not in out and "Secondary Color" not in out and out.get("sc"):
        out["SecondaryColor"] = str(out.get("sc") or "")

    return out


def _strip_computed_details_fields(details: Any) -> Any:
    """Return details without large recomputable payloads."""
    return details
