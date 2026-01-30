from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

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

        # Token ids: 0=PAD, 1..n_songs=songs, n_songs+1=CLS.
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
        """
        song_ids: int64[B, L] with 0 as PAD.
        Returns logits: float32[B, V]
        """
        if song_ids.dtype != torch.long:
            song_ids = song_ids.long()

        bsz = song_ids.shape[0]
        cls = torch.full((bsz, 1), self.cls_id, device=song_ids.device, dtype=torch.long)
        x = torch.cat([cls, song_ids], dim=1)  # [B, 1+L]

        pad_mask = x.eq(0)  # [B, 1+L]
        h = self.embed(x)
        h = self.encoder(h, src_key_padding_mask=pad_mask)
        cls_h = h[:, 0, :]
        return self.head(cls_h)


def _resolve_device(name: str) -> torch.device:
    name = str(name or "").strip().lower()
    if name in {"dml", "directml"}:
        try:
            import torch_directml as dml
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise SystemExit("torch-directml is not installed (pip install torch-directml).") from exc
        return dml.device()
    return torch.device(name or "cpu")


def _batch_iter(
    songs: torch.Tensor, labels: torch.Tensor, *, batch_size: int, seed: int
) -> Tuple[torch.Tensor, torch.Tensor]:
    n = int(songs.shape[0])
    gen = torch.Generator()
    gen.manual_seed(int(seed))
    perm = torch.randperm(n, generator=gen)
    for start in range(0, n, batch_size):
        idx = perm[start : start + batch_size]
        yield songs[idx], labels[idx]


def main() -> None:
    ap = argparse.ArgumentParser(description="Train a small transformer to predict seed variants from song subsets.")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt path from generate_transformer_dataset.py.")
    ap.add_argument("--out", type=str, required=True, help="Output model .pt path.")
    ap.add_argument("--epochs", type=int, default=5, help="Epochs (default: 5).")
    ap.add_argument("--batch-size", type=int, default=16, help="Batch size (default: 16).")
    ap.add_argument("--lr", type=float, default=3e-4, help="Learning rate (default: 3e-4).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    ap.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda/dml; default: cpu).")
    ap.add_argument(
        "--loss",
        type=str,
        default="bce",
        choices=["bce", "bce_custom", "mse"],
        help="Loss function (bce=BCEWithLogitsLoss, bce_custom=GPU-safe formula, mse=sigmoid MSE; default: bce).",
    )
    ap.add_argument("--pos-weight", type=float, default=1.0, help="Positive class weight for MSE (default: 1.0).")
    ap.add_argument("--neg-weight", type=float, default=1.0, help="Negative class weight for MSE (default: 1.0).")
    ap.add_argument(
        "--strict-no-cpu",
        action="store_true",
        help="DirectML only: fail if any operator falls back to CPU (best-effort via warning-as-error).",
    )
    ap.add_argument(
        "--optimizer",
        type=str,
        default="adamw",
        choices=["adamw", "sgd", "rmsprop", "adamw_manual", "adamw_safe", "adamw_safe_oop"],
        help="Optimizer (default: adamw).",
    )
    ap.add_argument("--weight-decay", type=float, default=0.01, help="Weight decay (default: 0.01).")
    ap.add_argument("--momentum", type=float, default=0.9, help="SGD momentum (default: 0.9).")
    ap.add_argument("--adam-beta1", type=float, default=0.9, help="AdamW beta1 (default: 0.9).")
    ap.add_argument("--adam-beta2", type=float, default=0.999, help="AdamW beta2 (default: 0.999).")
    ap.add_argument("--adam-eps", type=float, default=1e-8, help="AdamW eps (default: 1e-8).")
    ap.add_argument("--rms-alpha", type=float, default=0.99, help="RMSprop alpha (default: 0.99).")
    ap.add_argument("--rms-eps", type=float, default=1e-8, help="RMSprop eps (default: 1e-8).")
    ap.add_argument("--grad-clip", type=float, default=1.0, help="Gradient norm clip (default: 1.0).")
    ap.add_argument("--d-model", type=int, default=128, help="Transformer width (default: 128).")
    ap.add_argument("--n-heads", type=int, default=4, help="Attention heads (default: 4).")
    ap.add_argument("--n-layers", type=int, default=2, help="Transformer layers (default: 2).")
    ap.add_argument("--dropout", type=float, default=0.1, help="Dropout (default: 0.1).")
    args = ap.parse_args()

    data_path = Path(args.data)
    payload: Dict = torch.load(data_path, map_location="cpu")
    songs = payload["songs"].long()
    labels = payload["labels"].float()

    n_songs = int(len(payload["song_names"]))
    n_variants = int(labels.shape[1])

    cfg = ModelConfig(
        d_model=int(args.d_model),
        n_heads=int(args.n_heads),
        n_layers=int(args.n_layers),
        dropout=float(args.dropout),
    )

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
    opt_name = str(args.optimizer or "adamw").strip().lower()
    use_manual = False
    use_adamw_safe = False
    use_adamw_safe_oop = False
    if opt_name == "adamw":
        opt_kwargs = {"lr": float(args.lr), "weight_decay": float(args.weight_decay)}
        if device_name in {"dml", "directml"}:
            opt_kwargs["foreach"] = False
        opt = torch.optim.AdamW(model.parameters(), **opt_kwargs)
    elif opt_name == "sgd":
        opt = torch.optim.SGD(
            model.parameters(),
            lr=float(args.lr),
            momentum=float(args.momentum),
            weight_decay=float(args.weight_decay),
        )
    elif opt_name == "rmsprop":
        opt = torch.optim.RMSprop(
            model.parameters(),
            lr=float(args.lr),
            alpha=float(args.rms_alpha),
            eps=float(args.rms_eps),
            weight_decay=float(args.weight_decay),
            momentum=float(args.momentum),
        )
    elif opt_name == "adamw_manual":
        opt = None
        use_manual = True
    elif opt_name == "adamw_safe":
        opt = None
        use_adamw_safe = True
    elif opt_name == "adamw_safe_oop":
        opt = None
        use_adamw_safe_oop = True
    else:
        raise SystemExit(f"Unknown optimizer: {opt_name}")
    loss_name = str(args.loss or "bce").strip().lower()
    if device_name in {"dml", "directml"} and loss_name == "bce":
        raise SystemExit("DirectML: BCEWithLogitsLoss uses log_sigmoid which falls back to CPU. Use --loss bce_custom.")
    loss_fn = None
    if loss_name == "bce":
        loss_fn = nn.BCEWithLogitsLoss()
    elif loss_name == "bce_custom":
        loss_fn = None
    elif loss_name == "mse":
        loss_fn = nn.MSELoss()
    else:
        raise SystemExit(f"Unknown loss: {loss_name}")

    model.train()
    for epoch in range(int(args.epochs)):
        total = 0.0
        batches = 0
        for xb, yb in _batch_iter(songs, labels, batch_size=int(args.batch_size), seed=int(args.seed) + epoch):
            xb = xb.to(device)
            yb = yb.to(device)

            logits = model(xb)
            if loss_name == "bce_custom":
                # Stable BCEWithLogits formula, optionally weighted.
                # For sparse multi-label tasks, pos/neg weighting helps avoid the all-zeros trivial solution.
                w_pos = float(args.pos_weight)
                w_neg = float(args.neg_weight)
                softplus_pos = torch.nn.functional.softplus(-logits)
                softplus_neg = torch.nn.functional.softplus(logits)
                loss = (yb * w_pos * softplus_pos + (1.0 - yb) * w_neg * softplus_neg).mean()
            elif loss_name == "mse":
                pred = torch.sigmoid(logits)
                if float(args.pos_weight) != 1.0 or float(args.neg_weight) != 1.0:
                    w_pos = float(args.pos_weight)
                    w_neg = float(args.neg_weight)
                    weight = yb * w_pos + (1.0 - yb) * w_neg
                    loss = (weight * (pred - yb).pow(2)).mean()
                else:
                    loss = loss_fn(pred, yb)
            else:
                loss = loss_fn(logits, yb)
            if opt is not None:
                opt.zero_grad(set_to_none=True)
            else:
                model.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), float(args.grad_clip))
            if use_manual or use_adamw_safe or use_adamw_safe_oop:
                beta1 = float(args.adam_beta1)
                beta2 = float(args.adam_beta2)
                eps = float(args.adam_eps)
                lr = float(args.lr)
                weight_decay = float(args.weight_decay)
                if not hasattr(model, "_manual_adamw_state"):
                    setattr(model, "_manual_adamw_state", {})
                state = getattr(model, "_manual_adamw_state")
                with torch.no_grad():
                    for p in model.parameters():
                        if p.grad is None:
                            continue
                        grad = p.grad
                        st = state.get(p)
                        if st is None:
                            st = {
                                "m": torch.zeros_like(p),
                                "v": torch.zeros_like(p),
                                "step": 0,
                            }
                            state[p] = st
                        m = st["m"]
                        v = st["v"]
                        st["step"] = int(st["step"]) + 1
                        step = int(st["step"])
                        if use_adamw_safe_oop:
                            # Some DML builds are fragile with chained in-place ops (mul_+add_/addcmul_).
                            # Prefer explicit out-of-place math + copy_ for stability.
                            m_new = m * beta1 + grad * (1.0 - beta1)
                            v_new = v * beta2 + (grad * grad) * (1.0 - beta2)
                            m.copy_(m_new)
                            v.copy_(v_new)
                        else:
                            m.mul_(beta1).add_(grad, alpha=1.0 - beta1)
                            v.mul_(beta2).addcmul_(grad, grad, value=1.0 - beta2)
                        if weight_decay != 0.0:
                            p.mul_(1.0 - lr * weight_decay)
                        bias_c1 = 1.0 - (beta1**step)
                        bias_c2 = 1.0 - (beta2**step)
                        m_hat = m / bias_c1
                        v_hat = v / bias_c2
                        if use_adamw_safe or use_adamw_safe_oop:
                            m_hat = torch.where(m_hat == m_hat, m_hat, torch.zeros_like(m_hat))
                            v_hat = torch.where(v_hat == v_hat, v_hat, torch.zeros_like(v_hat))
                            v_hat = torch.clamp(v_hat, min=eps)
                            denom = v_hat.sqrt()
                        else:
                            denom = v_hat.sqrt().add_(eps)
                        p.addcdiv_(m_hat, denom, value=-lr)
            else:
                opt.step()

            total += float(loss.detach().cpu().item())
            batches += 1
        avg = total / max(1, batches)
        print(f"epoch {epoch + 1}/{int(args.epochs)} loss={avg:.6f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "cfg": cfg.__dict__,
            "n_songs": n_songs,
            "n_variants": n_variants,
            "dataset_meta": payload.get("meta", {}),
        },
        out_path,
    )
    print(f"Wrote model: {out_path}")


if __name__ == "__main__":
    main()
