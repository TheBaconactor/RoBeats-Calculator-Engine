from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

import torch
import torch.nn as nn
import warnings


class SongSetTransformer(nn.Module):
    def __init__(self, *, n_songs: int, n_variants: int, cfg: Dict):
        super().__init__()
        self.n_songs = int(n_songs)
        self.n_variants = int(n_variants)
        self.cls_id = int(self.n_songs + 1)

        d_model = int(cfg["d_model"])
        n_heads = int(cfg["n_heads"])
        n_layers = int(cfg["n_layers"])
        dropout = float(cfg["dropout"])

        self.embed = nn.Embedding(self.n_songs + 2, d_model, padding_idx=0)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=n_layers)
        self.head = nn.Linear(d_model, self.n_variants)

    def forward(self, song_ids: torch.Tensor) -> torch.Tensor:
        if song_ids.dtype != torch.long:
            song_ids = song_ids.long()
        bsz = song_ids.shape[0]
        cls = torch.full((bsz, 1), self.cls_id, device=song_ids.device, dtype=torch.long)
        x = torch.cat([cls, song_ids], dim=1)
        pad_mask = x.eq(0)
        h = self.embed(x)
        h = self.encoder(h, src_key_padding_mask=pad_mask)
        return self.head(h[:, 0, :])


def _resolve_device(name: str) -> torch.device:
    name = str(name or "").strip().lower()
    if name in {"dml", "directml"}:
        try:
            import torch_directml as dml
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise SystemExit("torch-directml is not installed (pip install torch-directml).") from exc
        return dml.device()
    return torch.device(name or "cpu")


def main() -> None:
    ap = argparse.ArgumentParser(description="Predict a seed-variants JSON using a trained transformer.")
    ap.add_argument("--model", type=str, required=True, help="Model .pt from train_transformer_seed.py.")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt (for vocab + song list).")
    ap.add_argument("--out", type=str, required=True, help="Output JSON path (gear_name+offset list).")
    ap.add_argument("--cap", type=int, default=100, help="Number of variants to emit (default: 100).")
    ap.add_argument(
        "--caps",
        type=str,
        default="",
        help="Optional comma list of caps to emit (overrides --cap). Example: 30,50,70.",
    )
    ap.add_argument("--subset-size", type=int, default=128, help="Subset size used at training/inference (default: 128).")
    ap.add_argument("--samples", type=int, default=64, help="How many random subsets to average (default: 64).")
    ap.add_argument("--batch-size", type=int, default=32, help="Inference batch size (default: 32).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    ap.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda/dml; default: cpu).")
    ap.add_argument(
        "--strict-no-cpu",
        action="store_true",
        help="DirectML only: fail if any operator falls back to CPU (best-effort via warning-as-error).",
    )
    args = ap.parse_args()

    model_ckpt = torch.load(Path(args.model), map_location="cpu")
    payload: Dict = torch.load(Path(args.data), map_location="cpu")

    song_names: List[str] = list(payload["song_names"])
    universe_variants: List[dict] = list(payload["universe_variants"])

    n_songs = int(model_ckpt["n_songs"])
    n_variants = int(model_ckpt["n_variants"])
    cfg = dict(model_ckpt["cfg"])

    if n_songs != len(song_names):
        raise SystemExit(f"Model expects n_songs={n_songs}, but dataset has {len(song_names)} song names.")
    if n_variants != len(universe_variants):
        raise SystemExit(f"Model expects n_variants={n_variants}, but dataset has {len(universe_variants)} variants.")

    device_name = str(args.device or "").strip().lower()
    device = _resolve_device(device_name)
    if bool(args.strict_no_cpu) and device_name in {"dml", "directml"}:
        warnings.filterwarnings("error", message=r".*fall back to run on the CPU.*", category=UserWarning)
        # Avoid fused transformer fastpaths that may not be implemented on DirectML.
        try:
            torch.backends.mha.set_fastpath_enabled(False)
        except Exception:
            pass
    model = SongSetTransformer(n_songs=n_songs, n_variants=n_variants, cfg=cfg).to(device)
    model.load_state_dict(model_ckpt["model_state"])
    model.eval()

    subset_size = int(args.subset_size)
    if subset_size <= 0 or subset_size > len(song_names):
        raise SystemExit(f"--subset-size must be in [1, {len(song_names)}].")

    rng = random.Random(int(args.seed))
    song_ids_all = list(range(1, len(song_names) + 1))  # 1..n_songs

    agg = torch.zeros((n_variants,), dtype=torch.float32, device=device)
    batch_size = max(1, int(args.batch_size))
    pending: List[List[int]] = []
    with torch.no_grad():
        samples = int(args.samples)
        if samples <= 0:
            raise SystemExit("--samples must be positive.")
        for i in range(samples):
            pending.append(rng.sample(song_ids_all, subset_size))
            if len(pending) >= batch_size or i == samples - 1:
                x = torch.tensor(pending, dtype=torch.long, device=device)
                logits = model(x)
                agg += logits.sum(dim=0)
                pending = []
    agg = agg / max(1, int(args.samples))

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
        idx = torch.topk(agg, k=min(cap, n_variants)).indices.detach().cpu().tolist()

        out_variants: List[dict] = []
        for i in idx:
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
