from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ModelConfig:
    d_model: int
    n_heads: int
    n_layers: int
    dropout: float


class SongSetTransformer(nn.Module):
    def __init__(self, *, n_songs: int, n_variants: int, cfg: ModelConfig):
        super().__init__()
        self.n_songs = int(n_songs)
        self.n_variants = int(n_variants)
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


def _resolve_device(name: str) -> torch.device:
    name = str(name or "").strip().lower()
    if name in {"dml", "directml"}:
        try:
            import torch_directml as dml
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise SystemExit("torch-directml is not installed (pip install torch-directml).") from exc
        return dml.device()
    return torch.device(name or "cpu")


def _aggregate_logits(
    model: SongSetTransformer,
    song_ids_all: List[int],
    *,
    subset_size: int,
    samples: int,
    batch_size: int,
    rng: random.Random,
    device: torch.device,
) -> torch.Tensor:
    if samples <= 0:
        raise SystemExit("--samples must be positive.")
    if subset_size <= 0 or subset_size > len(song_ids_all):
        raise SystemExit(f"--subset-size must be in [1, {len(song_ids_all)}].")
    agg = torch.zeros((model.n_variants,), dtype=torch.float32, device=device)
    pending: List[List[int]] = []
    with torch.no_grad():
        for i in range(samples):
            pending.append(rng.sample(song_ids_all, subset_size))
            if len(pending) >= batch_size or i == samples - 1:
                x = torch.tensor(pending, dtype=torch.long, device=device)
                logits = model(x)
                agg += logits.sum(dim=0)
                pending = []
    return agg / float(samples)


def _gumbel_topk(logits: torch.Tensor, *, k: int, temperature: float, seed: int) -> List[int]:
    if temperature <= 0:
        raise SystemExit("--temperature must be > 0.")
    torch.manual_seed(int(seed))
    noise = -torch.log(-torch.log(torch.rand_like(logits)))
    scores = logits / float(temperature) + noise
    idx = torch.topk(scores, k=min(int(k), int(logits.numel()))).indices.detach().cpu().tolist()
    return [int(i) for i in idx]


def _topk(logits: torch.Tensor, *, k: int) -> List[int]:
    idx = torch.topk(logits, k=min(int(k), int(logits.numel()))).indices.detach().cpu().tolist()
    return [int(i) for i in idx]


def _write_seed(
    idx: List[int], universe_variants: List[dict], out_path: Path, *, cap: int
) -> None:
    out_variants: List[dict] = []
    for i in idx[: int(cap)]:
        v = universe_variants[int(i)]
        if not isinstance(v, dict):
            continue
        name = str(v.get("gear_name") or "").strip()
        off = v.get("offset")
        if not name or off is None:
            continue
        out_variants.append({"gear_name": name, "offset": int(off)})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"variants": out_variants}, indent=2, sort_keys=True), encoding="utf-8")


def _sample_allowlist(song_names: List[str], *, count: int, seed: int) -> List[str]:
    rng = random.Random(int(seed))
    if count <= 0 or count >= len(song_names):
        return list(song_names)
    return rng.sample(list(song_names), count)


def _run_solver(
    *,
    db_path: Path,
    seed_path: Path,
    allowlist_path: Path,
    out_path: Path,
    inventory_cap: int,
    k: int,
    restarts: int,
    lns_time_sec: float,
    lns_attempts: int,
    seed_inventory_mode: str,
    seed: int,
) -> int:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "inventory_meta_coverage_main.py"),
        "--db-path",
        str(db_path),
        "--solver",
        "gpu_full",
        "--inventory-cap",
        str(int(inventory_cap)),
        "--partitions-per-song",
        str(int(k)),
        "--adaptive-rounds",
        "0",
        "--adaptive-keep-per-song",
        "0",
        "--seed",
        str(int(seed)),
        "--restarts",
        str(int(restarts)),
        "--lns-time-sec",
        str(float(lns_time_sec)),
        "--lns-attempts",
        str(int(lns_attempts)),
        "--seed-inventory-variants",
        str(seed_path),
        "--seed-inventory-mode",
        str(seed_inventory_mode),
        "--song-allowlist-file",
        str(allowlist_path),
        "--output",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    stats = payload.get("stats") or {}
    return int(stats.get("songs_covered") or 0)


def _run_full_solver(
    *,
    db_path: Path,
    seed_path: Path,
    out_path: Path,
    inventory_cap: int,
    k: int,
    restarts: int,
    lns_time_sec: float,
    lns_attempts: int,
    seed_inventory_mode: str,
    seed: int,
) -> int:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "inventory_meta_coverage_main.py"),
        "--db-path",
        str(db_path),
        "--solver",
        "gpu_full",
        "--inventory-cap",
        str(int(inventory_cap)),
        "--partitions-per-song",
        str(int(k)),
        "--adaptive-rounds",
        "0",
        "--adaptive-keep-per-song",
        "0",
        "--seed",
        str(int(seed)),
        "--restarts",
        str(int(restarts)),
        "--lns-time-sec",
        str(float(lns_time_sec)),
        "--lns-attempts",
        str(int(lns_attempts)),
        "--seed-inventory-variants",
        str(seed_path),
        "--seed-inventory-mode",
        str(seed_inventory_mode),
        "--output",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    stats = payload.get("stats") or {}
    return int(stats.get("songs_covered") or 0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Search seed sets via model sampling + GPU solver eval.")
    ap.add_argument("--model", type=str, required=True, help="Model .pt from train_transformer_seed.py.")
    ap.add_argument("--data", type=str, required=True, help="Dataset .pt (for vocab + song list).")
    ap.add_argument("--db-path", type=str, required=True, help="SQLite snapshot path (DO NOT use live evolution.db).")
    ap.add_argument("--out-dir", type=str, required=True, help="Output directory for candidates and summary.")
    ap.add_argument("--seed-cap", type=int, default=50, help="How many variants to emit in the seed set (default: 50).")
    ap.add_argument(
        "--inventory-cap",
        type=int,
        default=100,
        help="Solver inventory cap (default: 100).",
    )
    ap.add_argument("--candidates", type=int, default=10, help="How many candidate seed sets (default: 10).")
    ap.add_argument("--subset-size", type=int, default=128, help="Subset size used at inference (default: 128).")
    ap.add_argument("--samples", type=int, default=64, help="Subsets to average per aggregation (default: 64).")
    ap.add_argument("--batch-size", type=int, default=32, help="Inference batch size (default: 32).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    ap.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda/dml; default: cpu).")
    ap.add_argument(
        "--strict-no-cpu",
        action="store_true",
        help="DirectML only: fail if any operator falls back to CPU (best-effort via warning-as-error).",
    )
    ap.add_argument(
        "--strategy",
        type=str,
        default="gumbel",
        choices=["topk", "gumbel"],
        help="Seed sampling strategy (default: gumbel).",
    )
    ap.add_argument("--temperature", type=float, default=1.0, help="Gumbel temperature (default: 1.0).")
    ap.add_argument(
        "--aggregate-per-candidate",
        action="store_true",
        help="Recompute aggregation per candidate (slower but more diverse).",
    )
    ap.add_argument("--skip-eval", action="store_true", help="Only emit candidates; do not run GPU eval.")
    ap.add_argument("--eval-song-count", type=int, default=256, help="Songs per eval allowlist (default: 256).")
    ap.add_argument("--eval-k", type=int, default=128, help="Eval partitions per song (default: 128).")
    ap.add_argument("--eval-restarts", type=int, default=3, help="Eval restarts (default: 3).")
    ap.add_argument("--eval-lns-time-sec", type=float, default=0.0, help="Eval LNS time (default: 0).")
    ap.add_argument("--eval-lns-attempts", type=int, default=200, help="Eval LNS attempts (default: 200).")
    ap.add_argument(
        "--eval-seed-inventory-mode",
        type=str,
        default="hard",
        choices=["hard", "soft"],
        help="Eval seed mode (hard/soft; default: hard).",
    )
    ap.add_argument("--eval-seed", type=int, default=1, help="Eval RNG seed (default: 1).")
    ap.add_argument(
        "--run-full",
        action="store_true",
        help="After eval, run full solve for top candidates (default: off).",
    )
    ap.add_argument("--full-top", type=int, default=1, help="How many top candidates to fully run (default: 1).")
    ap.add_argument("--full-k", type=int, default=256, help="Full partitions per song (default: 256).")
    ap.add_argument("--full-restarts", type=int, default=5, help="Full restarts (default: 5).")
    ap.add_argument("--full-lns-time-sec", type=float, default=0.0, help="Full LNS time (default: 0).")
    ap.add_argument("--full-lns-attempts", type=int, default=200, help="Full LNS attempts (default: 200).")
    ap.add_argument(
        "--full-seed-inventory-mode",
        type=str,
        default="hard",
        choices=["hard", "soft"],
        help="Full run seed mode (hard/soft; default: hard).",
    )
    ap.add_argument("--full-seed", type=int, default=1, help="Full run RNG seed (default: 1).")
    args = ap.parse_args()

    model_ckpt = torch.load(Path(args.model), map_location="cpu")
    payload: Dict = torch.load(Path(args.data), map_location="cpu")

    song_names: List[str] = list(payload["song_names"])
    universe_variants: List[dict] = list(payload["universe_variants"])

    n_songs = int(model_ckpt["n_songs"])
    n_variants = int(model_ckpt["n_variants"])
    cfg = ModelConfig(**model_ckpt["cfg"])
    if n_songs != len(song_names):
        raise SystemExit(f"Model expects n_songs={n_songs}, but dataset has {len(song_names)} song names.")
    if n_variants != len(universe_variants):
        raise SystemExit(f"Model expects n_variants={n_variants}, but dataset has {len(universe_variants)} variants.")

    device_name = str(args.device or "").strip().lower()
    device = _resolve_device(device_name)
    if bool(args.strict_no_cpu) and device_name in {"dml", "directml"}:
        warnings.filterwarnings("error", message=r".*fall back to run on the CPU.*", category=UserWarning)
        try:
            torch.backends.mha.set_fastpath_enabled(False)
        except Exception:
            pass

    model = SongSetTransformer(n_songs=n_songs, n_variants=n_variants, cfg=cfg).to(device)
    model.load_state_dict(model_ckpt["model_state"])
    model.eval()

    out_dir = Path(args.out_dir)
    cand_dir = out_dir / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(int(args.seed))
    song_ids_all = list(range(1, len(song_names) + 1))  # 1..n_songs

    agg_logits = None
    if not args.aggregate_per_candidate:
        agg_logits = _aggregate_logits(
            model,
            song_ids_all,
            subset_size=int(args.subset_size),
            samples=int(args.samples),
            batch_size=int(args.batch_size),
            rng=rng,
            device=device,
        )

    results: List[Dict[str, object]] = []
    for i in range(int(args.candidates)):
        if args.aggregate_per_candidate or agg_logits is None:
            agg_logits = _aggregate_logits(
                model,
                song_ids_all,
                subset_size=int(args.subset_size),
                samples=int(args.samples),
                batch_size=int(args.batch_size),
                rng=random.Random(rng.randint(0, 2**31 - 1)),
                device=device,
            )

        if str(args.strategy) == "topk":
            idx = _topk(agg_logits, k=int(args.seed_cap))
        else:
            idx = _gumbel_topk(
                agg_logits,
                k=int(args.seed_cap),
                temperature=float(args.temperature),
                seed=int(args.seed) + i,
            )

        seed_path = cand_dir / f"seed_{i:03d}.json"
        _write_seed(idx, universe_variants, seed_path, cap=int(args.seed_cap))

        entry: Dict[str, object] = {
            "candidate": int(i),
            "seed_path": str(seed_path),
            "eval_covered": None,
        }

        if not bool(args.skip_eval):
            allowlist = _sample_allowlist(song_names, count=int(args.eval_song_count), seed=int(args.eval_seed) + i)
            allow_path = cand_dir / f"allow_{i:03d}.json"
            allow_path.write_text(json.dumps(allowlist, indent=0), encoding="utf-8")
            sol_path = cand_dir / f"eval_{i:03d}.json"

            covered = _run_solver(
                db_path=Path(args.db_path),
                seed_path=seed_path,
                allowlist_path=allow_path,
                out_path=sol_path,
                inventory_cap=int(args.inventory_cap),
                k=int(args.eval_k),
                restarts=int(args.eval_restarts),
                lns_time_sec=float(args.eval_lns_time_sec),
                lns_attempts=int(args.eval_lns_attempts),
                seed_inventory_mode=str(args.eval_seed_inventory_mode),
                seed=int(args.eval_seed) + i,
            )
            entry["eval_covered"] = int(covered)
            entry["eval_result_path"] = str(sol_path)
        results.append(entry)

    if results and results[0].get("eval_covered") is not None:
        results.sort(key=lambda r: int(r.get("eval_covered") or 0), reverse=True)

    summary = {
        "meta": {
            "model": str(args.model),
            "data": str(args.data),
            "db_path": str(args.db_path),
            "seed_cap": int(args.seed_cap),
            "inventory_cap": int(args.inventory_cap),
            "candidates": int(args.candidates),
            "strategy": str(args.strategy),
            "temperature": float(args.temperature),
            "subset_size": int(args.subset_size),
            "samples": int(args.samples),
            "aggregate_per_candidate": bool(args.aggregate_per_candidate),
            "eval": not bool(args.skip_eval),
            "eval_song_count": int(args.eval_song_count),
            "eval_k": int(args.eval_k),
            "eval_restarts": int(args.eval_restarts),
            "eval_lns_time_sec": float(args.eval_lns_time_sec),
            "eval_lns_attempts": int(args.eval_lns_attempts),
            "eval_seed_inventory_mode": str(args.eval_seed_inventory_mode),
        },
        "candidates": results,
    }

    if bool(args.run_full) and results:
        top_n = max(1, int(args.full_top))
        summary["full_runs"] = []
        for entry in results[:top_n]:
            seed_path = Path(str(entry["seed_path"]))
            out_path = cand_dir / f"full_{seed_path.stem}.json"
            covered = _run_full_solver(
                db_path=Path(args.db_path),
                seed_path=seed_path,
                out_path=out_path,
                inventory_cap=int(args.inventory_cap),
                k=int(args.full_k),
                restarts=int(args.full_restarts),
                lns_time_sec=float(args.full_lns_time_sec),
                lns_attempts=int(args.full_lns_attempts),
                seed_inventory_mode=str(args.full_seed_inventory_mode),
                seed=int(args.full_seed),
            )
            summary["full_runs"].append(
                {
                    "seed_path": str(seed_path),
                    "full_covered": int(covered),
                    "full_result_path": str(out_path),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
