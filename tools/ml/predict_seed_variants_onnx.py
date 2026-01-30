from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List

import numpy as np
import onnxruntime as ort
import torch


def _resolve_provider(name: str) -> List[str]:
    name = str(name or "").strip().lower()
    available = ort.get_available_providers()
    if name in {"dml", "directml"}:
        if "DmlExecutionProvider" not in available:
            raise SystemExit(f"DirectML provider not available. Providers: {available}")
        return ["DmlExecutionProvider"]
    if name in {"cpu"}:
        return ["CPUExecutionProvider"]
    raise SystemExit(f"Unknown provider: {name}. Available providers: {available}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Predict seed variants using an ONNX model.")
    ap.add_argument("--model", type=str, required=True, help="ONNX model path.")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt (for vocab + song list).")
    ap.add_argument("--out", type=str, required=True, help="Output JSON path (gear_name+offset list).")
    ap.add_argument("--cap", type=int, default=100, help="Number of variants to emit (default: 100).")
    ap.add_argument(
        "--caps",
        type=str,
        default="",
        help="Optional comma list of caps to emit (overrides --cap). Example: 30,50,70.",
    )
    ap.add_argument("--subset-size", type=int, default=128, help="Subset size used at training/inference.")
    ap.add_argument("--samples", type=int, default=64, help="How many random subsets to average (default: 64).")
    ap.add_argument("--batch-size", type=int, default=32, help="Inference batch size (default: 32).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    ap.add_argument("--provider", type=str, default="dml", help="Execution provider: dml or cpu (default: dml).")
    args = ap.parse_args()

    payload: Dict = torch.load(Path(args.data), map_location="cpu")
    song_names: List[str] = list(payload["song_names"])
    universe_variants: List[dict] = list(payload["universe_variants"])

    subset_size = int(args.subset_size)
    if subset_size <= 0 or subset_size > len(song_names):
        raise SystemExit(f"--subset-size must be in [1, {len(song_names)}].")
    samples = int(args.samples)
    if samples <= 0:
        raise SystemExit("--samples must be positive.")

    providers = _resolve_provider(args.provider)
    sess = ort.InferenceSession(str(args.model), providers=providers)
    input_name = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name

    rng = random.Random(int(args.seed))
    song_ids_all = list(range(1, len(song_names) + 1))  # 1..n_songs

    agg = np.zeros((len(universe_variants),), dtype=np.float64)
    batch_size = max(1, int(args.batch_size))
    pending: List[List[int]] = []
    for i in range(samples):
        pending.append(rng.sample(song_ids_all, subset_size))
        if len(pending) >= batch_size or i == samples - 1:
            x = np.asarray(pending, dtype=np.int64)
            logits = sess.run([output_name], {input_name: x})[0]
            agg += logits.sum(axis=0)
            pending = []
    agg = agg / max(1, samples)

    caps: List[int]
    if str(args.caps or "").strip():
        caps = []
        for part in str(args.caps).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                caps.append(int(part))
            except Exception:
                raise SystemExit(f"Invalid cap in --caps: {part}")
        if not caps:
            raise SystemExit("--caps provided but no valid entries found.")
    else:
        caps = [int(args.cap)]

    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    for cap in caps:
        if cap <= 0:
            raise SystemExit("--cap/--caps values must be positive.")
        idx = np.argpartition(-agg, kth=min(cap, agg.size) - 1)[: min(cap, agg.size)]
        idx = idx[np.argsort(-agg[idx])]

        out_variants: List[dict] = []
        for i in idx.tolist():
            v = universe_variants[int(i)]
            if not isinstance(v, dict):
                continue
            name = str(v.get("gear_name") or "").strip()
            off = v.get("offset")
            if not name or off is None:
                continue
            out_variants.append({"gear_name": name, "offset": int(off)})

        if len(caps) == 1:
            out_path = out_base
        else:
            out_path = out_base.with_name(f"{out_base.stem}_top{cap}{out_base.suffix}")
        out_path.write_text(json.dumps({"variants": out_variants}, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote seed variants: {out_path} (n={len(out_variants)})")


if __name__ == "__main__":
    main()
