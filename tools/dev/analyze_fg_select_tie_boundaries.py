"""Diagnose GA->FG select tie boundaries on captured candidate pools.

Slice 1 (GPU effective-dedup) is bit-exact-gated: before swapping the GPU
select kernel's dedup key from raw item ids to the effective signature, we must
prove that, on REAL captured pools, the host selection and the reference
selection agree, and quantify how close any base-score ties at the top-N
boundary are (the only place the host's hash tie-break vs the GPU's
canonical-id tie-break could diverge).

Input schema (JSON or JSONL). Each pool is::

    {
      "limit": 51,
      "gear_name_rank": [ ... int per gear id ... ],
      "mini_sig_id":    [ ... int per mini id ... ],
      "candidates": [
        {"score": <int>, "gear_ids": [6 ints], "mini_ids": [3 ints]},
        ...
      ]
    }

- JSON input: a single pool object OR a list of pool objects.
- JSONL input: one pool object per line.

The ``gear_name_rank`` / ``mini_sig_id`` tables are the SAME tables
``build_gear_name_rank`` / ``build_mini_sig_id`` produce (capture them once per
registry/color-combo alongside the pool).

This script does NOT touch the GPU, Taichi, or production select call sites. It
is a pure offline analysis tool meant to be run against pools captured during a
GPU window.

Reported per pool and in aggregate:
- effective-key collisions: how many candidates collapse under the effective
  key (i.e. raw-id-distinct rows that are effective-duplicates - the rows the
  GPU's raw-id dedup would wrongly keep apart).
- base-score ties at the top-N boundary: among the deduped survivors, how many
  share the boundary base score (the score of the last kept survivor). A nonzero
  count means the final tie-break rule is load-bearing for THIS pool.
- host-vs-reference selection mismatch: whether the reference selector's
  selected SET differs from the host ``select_top_base_ga_candidates`` set.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

# Allow running as a standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gear_optimizer.helpers.song_helpers.fg_candidate_selector import (  # noqa: E402
    select_top_base_ga_candidates,
)
from gear_optimizer.solver.fg_effective_dedup import (  # noqa: E402
    select_top_base_fg_candidates_reference,
)


def _load_pools(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    obj = json.loads(text)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [obj]
    raise ValueError(f"unsupported JSON top-level type: {type(obj).__name__}")


def _pool_arrays(pool: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cands = pool.get("candidates")
    if not isinstance(cands, list):
        raise ValueError("pool missing 'candidates' list")
    scores = np.asarray([int(c["score"]) for c in cands], dtype=np.int64)
    gear = np.asarray([list(c["gear_ids"]) for c in cands], dtype=np.int64)
    minis = np.asarray([sorted(int(x) for x in c["mini_ids"]) for c in cands], dtype=np.int64)
    if gear.size and gear.shape[1] != 6:
        raise ValueError("each candidate needs exactly 6 gear_ids")
    if minis.size and minis.shape[1] != 3:
        raise ValueError("each candidate needs exactly 3 mini_ids")
    return scores, gear, minis


def _effective_key(
    gear_row: np.ndarray,
    mini_row: np.ndarray,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
) -> tuple:
    g = tuple(sorted(int(gear_name_rank[int(x)]) for x in gear_row))
    m = tuple(sorted(int(mini_sig_id[int(x)]) for x in mini_row))
    return (g, m)


def _host_candidates(pool: dict[str, Any]) -> list[dict]:
    """Build host-shaped candidate dicts keyed directly by the effective key.

    The host selector resolves an effective hash via gear NAMES + mini
    signatures. For an offline pool we don't have the registry's names, so we
    feed the host pre-resolved ``loadout_hash`` strings derived from the same
    effective key the reference uses. This exercises the host's dedup + ordering
    logic on identical equivalence classes.
    """
    import hashlib

    gear_name_rank = np.asarray(pool["gear_name_rank"], dtype=np.int64)
    mini_sig_id = np.asarray(pool["mini_sig_id"], dtype=np.int64)
    out: list[dict] = []
    for c in pool["candidates"]:
        key = _effective_key(
            np.asarray(c["gear_ids"]),
            np.asarray(c["mini_ids"]),
            gear_name_rank,
            mini_sig_id,
        )
        g = "|".join(str(x) for x in key[0])
        m = "|".join(str(x) for x in key[1])
        digest = hashlib.md5(f"GEAR:{g}::MINIS:{m}".encode("utf-8")).hexdigest()
        out.append({"BaseScore": int(c["score"]), "Score": int(c["score"]), "loadout_hash": digest})
    return out


def analyze_pool(pool: dict[str, Any]) -> dict[str, Any]:
    limit = int(pool.get("limit", 51))
    gear_name_rank = np.asarray(pool["gear_name_rank"], dtype=np.int64)
    mini_sig_id = np.asarray(pool["mini_sig_id"], dtype=np.int64)
    scores, gear, minis = _pool_arrays(pool)
    n = int(scores.shape[0])

    # Effective-key collisions: rows sharing an effective key (positive scores).
    key_counts: Counter = Counter()
    for i in range(n):
        if int(scores[i]) <= 0:
            continue
        key_counts[_effective_key(gear[i], minis[i], gear_name_rank, mini_sig_id)] += 1
    collisions = sum(c - 1 for c in key_counts.values() if c > 1)

    # Reference selection.
    ref_idx = select_top_base_fg_candidates_reference(
        base_scores=scores,
        gear_ids=gear,
        mini_ids=minis,
        gear_name_rank=gear_name_rank,
        mini_sig_id=mini_sig_id,
        limit=limit,
    )
    ref_scores = sorted((int(scores[i]) for i in ref_idx), reverse=True)

    # Base-score ties at the top-N boundary among deduped survivors.
    boundary_ties = 0
    if ref_scores:
        boundary_score = ref_scores[-1]
        boundary_ties = sum(1 for s in ref_scores if s == boundary_score) - 1

    # Host selection on identical equivalence classes (pre-resolved hashes).
    host_cands = _host_candidates(pool)
    host_selected = select_top_base_ga_candidates(host_cands, limit=limit)
    host_scores = sorted((int(c["BaseScore"]) for c in host_selected), reverse=True)

    mismatch = host_scores != ref_scores

    return {
        "n_candidates": n,
        "unique_effective_keys": len(key_counts),
        "effective_key_collisions": collisions,
        "selected_count_reference": len(ref_scores),
        "selected_count_host": len(host_scores),
        "boundary_base_score_ties": boundary_ties,
        "host_vs_reference_mismatch": bool(mismatch),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSON or JSONL pool file")
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON instead of text"
    )
    args = parser.parse_args(argv)

    pools = _load_pools(args.path)
    results = [analyze_pool(p) for p in pools]

    agg = {
        "pools": len(results),
        "total_candidates": sum(r["n_candidates"] for r in results),
        "total_effective_key_collisions": sum(r["effective_key_collisions"] for r in results),
        "pools_with_boundary_ties": sum(1 for r in results if r["boundary_base_score_ties"] > 0),
        "pools_with_mismatch": sum(1 for r in results if r["host_vs_reference_mismatch"]),
    }

    if args.json:
        print(json.dumps({"aggregate": agg, "pools": results}, indent=2))
        return 1 if agg["pools_with_mismatch"] else 0

    print("=== GA->FG select tie-boundary analysis ===")
    print(f"pools analyzed: {agg['pools']}  total candidates: {agg['total_candidates']}")
    print(f"total effective-key collisions: {agg['total_effective_key_collisions']}")
    print(f"pools with top-N boundary base-score ties: {agg['pools_with_boundary_ties']}")
    print(f"pools with host vs reference mismatch: {agg['pools_with_mismatch']}")
    for i, r in enumerate(results):
        flag = "  <-- MISMATCH" if r["host_vs_reference_mismatch"] else ""
        tie = f" boundary_ties={r['boundary_base_score_ties']}" if r["boundary_base_score_ties"] else ""
        print(
            f"  pool[{i}]: n={r['n_candidates']} keys={r['unique_effective_keys']} "
            f"collisions={r['effective_key_collisions']} "
            f"selected={r['selected_count_reference']}{tie}{flag}"
        )
    return 1 if agg["pools_with_mismatch"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
