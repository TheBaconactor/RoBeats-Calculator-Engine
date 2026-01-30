from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch


def _gini(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=np.float64).reshape(-1)
    if x.size == 0:
        return 0.0
    if np.all(x == 0):
        return 0.0
    x = np.sort(x)
    cum = np.cumsum(x)
    total = float(cum[-1])
    if total <= 0.0:
        return 0.0
    n = float(x.size)
    return float((n + 1.0 - 2.0 * float(np.sum(cum)) / total) / n)


def _corr(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return None
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _variant_bucket(v: dict) -> str:
    gems = v.get("gems") if isinstance(v, dict) else None
    gems = gems if isinstance(gems, dict) else {}
    ov = int(gems.get("OV") or 0)
    if ov <= 0:
        return "ANY"
    name = v.get("ov_color_name")
    return str(name) if name else "UNKNOWN"


def _summarize(
    payload: Dict[str, Any],
    *,
    topk: List[int],
) -> Dict[str, Any]:
    meta = dict(payload.get("meta") or {})

    labels_t = payload.get("labels")
    if not isinstance(labels_t, torch.Tensor):
        raise SystemExit("Dataset missing 'labels' tensor.")
    labels = labels_t.detach().cpu().numpy().astype(np.float64, copy=False)

    covered_t = payload.get("covered")
    covered = None
    if isinstance(covered_t, torch.Tensor):
        covered = covered_t.detach().cpu().numpy().astype(np.float64, copy=False)

    nnz = (labels > 0).sum(axis=1).astype(np.int64, copy=False)
    mass = labels.sum(axis=1).astype(np.float64, copy=False)

    variant_mass = labels.sum(axis=0).astype(np.float64, copy=False)
    total_mass = float(variant_mass.sum())
    variant_seen = int(np.count_nonzero(variant_mass > 0))

    order = np.argsort(-variant_mass)
    topk_cum: Dict[str, float] = {}
    if total_mass > 0:
        cum = np.cumsum(variant_mass[order])
        for k in topk:
            k_i = int(k)
            if k_i <= 0:
                continue
            k_i = min(k_i, int(cum.size))
            topk_cum[str(k_i)] = float(cum[k_i - 1] / total_mass)

    out: Dict[str, Any] = {
        "meta": meta,
        "shape": {"examples": int(labels.shape[0]), "variants": int(labels.shape[1])},
        "covered": None
        if covered is None
        else {
            "min": float(np.min(covered)),
            "p50": float(np.percentile(covered, 50)),
            "p90": float(np.percentile(covered, 90)),
            "max": float(np.max(covered)),
            "mean": float(np.mean(covered)),
        },
        "labels": {
            "nnz_per_example": {
                "min": int(np.min(nnz)),
                "p50": int(np.percentile(nnz, 50)),
                "p90": int(np.percentile(nnz, 90)),
                "max": int(np.max(nnz)),
                "mean": float(np.mean(nnz)),
            },
            "mass_per_example": {
                "min": float(np.min(mass)),
                "p50": float(np.percentile(mass, 50)),
                "p90": float(np.percentile(mass, 90)),
                "max": float(np.max(mass)),
                "mean": float(np.mean(mass)),
            },
            "variants_seen": int(variant_seen),
            "variant_mass_gini": float(_gini(variant_mass)),
            "topk_cum_mass": topk_cum,
            "corr_covered_nnz": None if covered is None else _corr(covered, nnz),
            "corr_covered_mass": None if covered is None else _corr(covered, mass),
        },
    }

    universe = payload.get("universe_variants")
    if isinstance(universe, list) and universe and universe[0] and isinstance(universe[0], dict):
        buckets = Counter()
        for v, m in zip(universe, variant_mass, strict=False):
            if m <= 0:
                continue
            buckets[_variant_bucket(v)] += float(m)
        out["labels"]["mass_by_bucket"] = dict(sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0])))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze a transformer dataset .pt from tools/ml/generate_transformer_dataset.py")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt path.")
    ap.add_argument("--out", type=str, default="", help="Optional output JSON path (prints to stdout if omitted).")
    ap.add_argument(
        "--topk",
        type=str,
        default="10,30,50,100,500,1000",
        help="Comma-separated ks for cumulative mass (default: 10,30,50,100,500,1000).",
    )
    args = ap.parse_args()

    topk: List[int] = []
    for part in str(args.topk or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            topk.append(int(part))
        except Exception:
            raise SystemExit(f"Invalid --topk entry: {part}")
    if not topk:
        topk = [10, 30, 50, 100, 500, 1000]

    payload: Dict[str, Any] = torch.load(Path(args.data), map_location="cpu")
    summary = _summarize(payload, topk=topk)

    out_json = json.dumps(summary, indent=2, sort_keys=True)
    if str(args.out or "").strip():
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        print(f"Wrote analysis: {out_path}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()

