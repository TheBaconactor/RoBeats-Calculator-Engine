from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import torch
import torch.nn as nn


@dataclass(frozen=True)
class ModelConfig:
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 2
    dropout: float = 0.1


class SongSetTransformer(nn.Module):
    def __init__(self, *, n_songs: int, n_variants: int, cfg: ModelConfig):
        super().__init__()
        self.n_songs = int(n_songs)
        self.n_variants = int(n_variants)
        self.cfg = cfg

        self.cls_id = int(self.n_songs + 1)
        self.embed = nn.Embedding(self.n_songs + 2, cfg.d_model, padding_idx=0)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_model * 4,
            dropout=cfg.dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=cfg.n_layers)
        self.head = nn.Linear(cfg.d_model, self.n_variants)

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


def main() -> None:
    ap = argparse.ArgumentParser(description="Export a transformer seed model to ONNX.")
    ap.add_argument("--model", type=str, required=True, help="Model .pt from train_transformer_seed.py.")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt (for vocab + subset size).")
    ap.add_argument("--out", type=str, required=True, help="Output .onnx path.")
    ap.add_argument("--opset", type=int, default=17, help="ONNX opset version (default: 17).")
    ap.add_argument("--subset-size", type=int, default=0, help="Override subset size (default: from dataset meta).")
    ap.add_argument("--device", type=str, default="cpu", help="Device for export (default: cpu).")
    args = ap.parse_args()

    model_ckpt = torch.load(Path(args.model), map_location="cpu")
    payload: Dict = torch.load(Path(args.data), map_location="cpu")

    n_songs = int(model_ckpt["n_songs"])
    n_variants = int(model_ckpt["n_variants"])
    cfg = ModelConfig(**model_ckpt["cfg"])

    subset_size = int(args.subset_size or 0)
    if subset_size <= 0:
        subset_size = int(payload.get("meta", {}).get("subset_size", 0) or 0)
    if subset_size <= 0:
        raise SystemExit("--subset-size must be provided or present in dataset meta.")

    device = torch.device(str(args.device))
    model = SongSetTransformer(n_songs=n_songs, n_variants=n_variants, cfg=cfg).to(device)
    model.load_state_dict(model_ckpt["model_state"])
    model.eval()

    dummy = torch.zeros((1, subset_size), dtype=torch.long, device=device)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy,
        out_path,
        opset_version=int(args.opset),
        input_names=["song_ids"],
        output_names=["logits"],
        dynamic_axes={"song_ids": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
        do_constant_folding=True,
    )
    print(f"Wrote ONNX model: {out_path}")


if __name__ == "__main__":
    main()
