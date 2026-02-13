"""
Decision-grade quality drop declaration for FG_CandidateLimit A/B tests.

This script sits on top of `tools/bench/ab_fg_candidate_limit_quality.py` and
adds explicit statistical decision gates.

Primary declaration target:
- Whether variant B (typically lower FG_CandidateLimit) has a *real* quality
  drop relative to variant A.

Core metric:
- Per paired run, delta_fg_gain_total = sum(max(0, best_fg_score - best_score))_A
  - sum(max(0, best_fg_score - best_score))_B

Interpretation:
- Positive deltas => A preserves more FG gain than B (evidence of drop in B).
- Negative deltas => B preserves more FG gain than A.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecisionThresholds:
    alpha: float = 0.05
    min_pairs: int = 12
    bootstrap_iters: int = 20_000
    bootstrap_seed: int = 20260212
    min_effect_mean: float = 0.0
    min_song_support_frac: float = 0.10
    min_song_support_count: int = 3


def _parse_int_list(raw: str) -> list[int]:
    vals: list[int] = []
    for tok in str(raw or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            vals.append(int(tok))
        except Exception:
            pass
    return vals


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def _sign_test_one_sided(positive: int, negative: int, *, tail: str) -> float:
    """
    Exact one-sided sign test under H0: p=0.5, ignoring zero-delta pairs.

    tail:
    - "positive": P(X >= positive)
    - "negative": P(X >= negative)
    """
    nz = int(positive) + int(negative)
    if nz <= 0:
        return 1.0
    if tail == "positive":
        k = int(positive)
    elif tail == "negative":
        k = int(negative)
    else:
        raise ValueError(f"Unsupported tail: {tail!r}")
    numer = 0
    for i in range(k, nz + 1):
        numer += _comb(nz, i)
    return float(numer) / float(2**nz)


def _bootstrap_mean_ci(values: list[float], *, alpha: float, iters: int, seed: int) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    n = len(values)
    rng = random.Random(int(seed))
    samples: list[float] = []
    for _ in range(max(100, int(iters))):
        s = 0.0
        for __ in range(n):
            s += float(values[rng.randrange(n)])
        samples.append(s / float(n))
    samples.sort()
    lo_idx = int((float(alpha) * 0.5) * float(len(samples) - 1))
    hi_idx = int((1.0 - (float(alpha) * 0.5)) * float(len(samples) - 1))
    lo_idx = max(0, min(lo_idx, len(samples) - 1))
    hi_idx = max(0, min(hi_idx, len(samples) - 1))
    return (float(samples[lo_idx]), float(samples[hi_idx]))


def decide_quality_drop(
    *,
    pair_deltas: list[float],
    song_median_deltas: list[float],
    thresholds: DecisionThresholds,
) -> dict:
    """
    Declare REAL_DROP / NO_DROP / INCONCLUSIVE using explicit gates.

    pair_deltas:
      List of per-paired-run (A-B) aggregate FG gain deltas.
    song_median_deltas:
      Per-song median(A-B) FG gain deltas across all paired runs.
    """
    vals = [float(v) for v in pair_deltas]
    pair_count = len(vals)
    pos = sum(1 for v in vals if v > 0.0)
    neg = sum(1 for v in vals if v < 0.0)
    zer = sum(1 for v in vals if v == 0.0)
    p_drop = _sign_test_one_sided(pos, neg, tail="positive")
    p_no_drop = _sign_test_one_sided(pos, neg, tail="negative")
    mean_delta = float(statistics.mean(vals)) if vals else 0.0
    median_delta = float(statistics.median(vals)) if vals else 0.0
    ci_lo, ci_hi = _bootstrap_mean_ci(
        vals,
        alpha=float(thresholds.alpha),
        iters=int(thresholds.bootstrap_iters),
        seed=int(thresholds.bootstrap_seed),
    )

    song_vals = [float(v) for v in song_median_deltas]
    song_count = len(song_vals)
    song_drop_count = sum(1 for v in song_vals if v > 0.0)
    song_no_drop_count = sum(1 for v in song_vals if v < 0.0)
    song_tie_count = sum(1 for v in song_vals if v == 0.0)
    required_song_support = max(
        int(thresholds.min_song_support_count),
        int(math.ceil(float(thresholds.min_song_support_frac) * float(max(1, song_count)))),
    )

    drop_pair_gate = (
        pair_count >= int(thresholds.min_pairs)
        and p_drop < float(thresholds.alpha)
        and ci_lo > float(thresholds.min_effect_mean)
    )
    drop_song_gate = song_drop_count >= required_song_support and song_drop_count > song_no_drop_count

    no_drop_pair_gate = (
        pair_count >= int(thresholds.min_pairs)
        and p_no_drop < float(thresholds.alpha)
        and ci_hi < -float(thresholds.min_effect_mean)
    )
    no_drop_song_gate = song_no_drop_count >= required_song_support and song_no_drop_count > song_drop_count

    if drop_pair_gate and drop_song_gate:
        declaration = "REAL_QUALITY_DROP_FOR_B"
    elif no_drop_pair_gate:
        # Song-level median deltas are often 0 due to ties/noise; pair-level
        # evidence should be sufficient to declare "no drop" when it's decisive.
        declaration = "NO_REAL_QUALITY_DROP_FOR_B"
    else:
        declaration = "INCONCLUSIVE"

    return {
        "declaration": declaration,
        "pair_count": pair_count,
        "pair_sign_counts": {"positive": pos, "negative": neg, "zero": zer},
        "pair_delta_mean": mean_delta,
        "pair_delta_median": median_delta,
        "pair_delta_mean_ci95": [ci_lo, ci_hi],
        "p_drop_one_sided": p_drop,
        "p_no_drop_one_sided": p_no_drop,
        "song_count": song_count,
        "song_support_required": required_song_support,
        "song_drop_count": song_drop_count,
        "song_no_drop_count": song_no_drop_count,
        "song_tie_count": song_tie_count,
        "gates": {
            "drop_pair_gate": bool(drop_pair_gate),
            "drop_song_gate": bool(drop_song_gate),
            "no_drop_pair_gate": bool(no_drop_pair_gate),
            "no_drop_song_gate": bool(no_drop_song_gate),
        },
    }


def _read_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fg_gain(scores: dict) -> int:
    try:
        best_score = int((scores or {}).get("best_score", 0) or 0)
        best_fg_score = int((scores or {}).get("best_fg_score", 0) or 0)
        return max(0, best_fg_score - best_score)
    except Exception:
        return 0


def _collect_from_reports(reports: list[dict]) -> dict:
    pair_rows: list[dict] = []
    song_delta_gain: dict[str, list[int]] = {}

    for rep in reports:
        meta = rep.get("meta") or {}
        seed = meta.get("ga_seed")
        runs_a = list((rep.get("runs") or {}).get("A") or [])
        runs_b = list((rep.get("runs") or {}).get("B") or [])
        for idx, (a_run, b_run) in enumerate(zip(runs_a, runs_b), start=1):
            a_scores = dict(a_run.get("scores") or {})
            b_scores = dict(b_run.get("scores") or {})
            songs = sorted(set(a_scores) | set(b_scores))
            delta_gain_total = 0
            delta_best_fg_total = 0
            delta_best_total = 0
            for song in songs:
                a_s = dict(a_scores.get(song) or {})
                b_s = dict(b_scores.get(song) or {})
                a_best = int(a_s.get("best_score", 0) or 0)
                b_best = int(b_s.get("best_score", 0) or 0)
                a_fg = int(a_s.get("best_fg_score", 0) or 0)
                b_fg = int(b_s.get("best_fg_score", 0) or 0)
                d_gain = int(_fg_gain(a_s) - _fg_gain(b_s))
                delta_gain_total += d_gain
                delta_best_fg_total += int(a_fg - b_fg)
                delta_best_total += int(a_best - b_best)
                song_delta_gain.setdefault(song, []).append(int(d_gain))
            pair_rows.append(
                {
                    "seed": seed,
                    "rep_index": idx,
                    "songs": len(songs),
                    "a_wall_s": float(a_run.get("wall_s", 0.0) or 0.0),
                    "b_wall_s": float(b_run.get("wall_s", 0.0) or 0.0),
                    "delta_gain_total": int(delta_gain_total),
                    "delta_best_fg_total": int(delta_best_fg_total),
                    "delta_best_total": int(delta_best_total),
                }
            )

    song_rows: list[dict] = []
    for song, deltas in sorted(song_delta_gain.items()):
        med = float(statistics.median(deltas)) if deltas else 0.0
        gt = sum(1 for v in deltas if v > 0)
        lt = sum(1 for v in deltas if v < 0)
        eq = sum(1 for v in deltas if v == 0)
        song_rows.append(
            {
                "song": song,
                "delta_fg_gain_median": med,
                "positive_pairs": gt,
                "negative_pairs": lt,
                "zero_pairs": eq,
                "pair_count": len(deltas),
            }
        )

    return {"pair_rows": pair_rows, "song_rows": song_rows}


def _run_one_harness(
    *,
    outdir: Path,
    config: str,
    song_limit: int,
    reps: int,
    seed: int,
    hitsim_seed: int,
    a: int,
    b: int,
    inflight_songs: int,
    fg_download_topk: int,
    allow_sequential: bool,
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "tools/bench/ab_fg_candidate_limit_quality.py",
        "--config",
        str(config),
        "--song-limit",
        str(int(song_limit)),
        "--reps",
        str(int(reps)),
        "--a",
        str(int(a)),
        "--b",
        str(int(b)),
        "--ga-seed",
        str(int(seed)),
        "--song-repeats",
        "1",
        "--hitsim-seed",
        str(int(hitsim_seed)),
        "--inflight-songs",
        str(int(inflight_songs)),
        "--fg-download-topk",
        str(int(fg_download_topk)),
        "--outdir",
        str(outdir),
    ]
    if allow_sequential:
        cmd.append("--allow-sequential")

    print(
        "[declare] running seed={} reps={} song_limit={} A={} B={}".format(
            int(seed),
            int(reps),
            int(song_limit),
            int(a),
            int(b),
        )
    )
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(Path.cwd()))
    (outdir / "declare_driver.log").write_text(proc.stdout or "", encoding="utf-8", errors="replace")
    if int(proc.returncode) != 0:
        raise SystemExit(
            "[declare] harness failed for seed={} (exit={}). See {}".format(
                int(seed),
                int(proc.returncode),
                outdir / "declare_driver.log",
            )
        )
    report_path = outdir / "analysis_report.json"
    if not report_path.exists():
        raise SystemExit(f"[declare] missing harness output: {report_path}")
    return report_path


def _build_report(
    *,
    source_reports: list[Path],
    pair_rows: list[dict],
    song_rows: list[dict],
    decision: dict,
    a_label: str,
    b_label: str,
) -> dict:
    a_walls = [float(r.get("a_wall_s", 0.0) or 0.0) for r in pair_rows]
    b_walls = [float(r.get("b_wall_s", 0.0) or 0.0) for r in pair_rows]
    a_med = float(statistics.median(a_walls)) if a_walls else 0.0
    b_med = float(statistics.median(b_walls)) if b_walls else 0.0

    strong_cut = max(1, int(math.ceil(0.75 * float(max(1, int(decision.get("pair_count", 0) or 0))))))
    strong_a = [
        s
        for s in song_rows
        if int(s.get("positive_pairs", 0) or 0) >= strong_cut and int(s.get("negative_pairs", 0) or 0) == 0
    ]
    strong_b = [
        s
        for s in song_rows
        if int(s.get("negative_pairs", 0) or 0) >= strong_cut and int(s.get("positive_pairs", 0) or 0) == 0
    ]

    top_drop = sorted(
        [s for s in song_rows if float(s.get("delta_fg_gain_median", 0.0) or 0.0) > 0.0],
        key=lambda x: float(x.get("delta_fg_gain_median", 0.0) or 0.0),
        reverse=True,
    )[:10]
    top_no_drop = sorted(
        [s for s in song_rows if float(s.get("delta_fg_gain_median", 0.0) or 0.0) < 0.0],
        key=lambda x: float(x.get("delta_fg_gain_median", 0.0) or 0.0),
    )[:10]

    return {
        "meta": {
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_reports": [str(p) for p in source_reports],
            "variant_a": str(a_label),
            "variant_b": str(b_label),
        },
        "decision": decision,
        "pair_rows": pair_rows,
        "song_rows": song_rows,
        "song_summary": {
            "strong_cut_pairs": strong_cut,
            "strong_a_count": len(strong_a),
            "strong_b_count": len(strong_b),
            "top_drop_songs": top_drop,
            "top_no_drop_songs": top_no_drop,
        },
        "throughput": {
            "a_wall_s_median": a_med,
            "b_wall_s_median": b_med,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.ini")
    ap.add_argument("--song-limit", type=int, default=50)
    ap.add_argument("--a", type=int, default=200, help="Variant A FG_CandidateLimit (baseline).")
    ap.add_argument("--b", type=int, default=100, help="Variant B FG_CandidateLimit (candidate).")
    ap.add_argument("--seeds", default="1337,4242,98765", help="Comma-separated GA seeds for fresh runs.")
    ap.add_argument("--reps-per-seed", type=int, default=3, help="Reps per seed for fresh runs.")
    ap.add_argument("--hitsim-seed", type=int, default=12345)
    ap.add_argument("--inflight-songs", type=int, default=0)
    ap.add_argument("--fg-download-topk", type=int, default=0)
    ap.add_argument("--allow-sequential", action="store_true")
    ap.add_argument("--source-report", action="append", default=[], help="Use existing analysis_report.json (repeat flag).")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--min-pairs", type=int, default=12)
    ap.add_argument("--bootstrap-iters", type=int, default=20000)
    ap.add_argument("--bootstrap-seed", type=int, default=20260212)
    ap.add_argument("--min-effect-mean", type=float, default=0.0)
    ap.add_argument("--min-song-support-frac", type=float, default=0.10)
    ap.add_argument("--min-song-support-count", type=int, default=3)
    ap.add_argument(
        "--outdir",
        default="",
        help="Output dir (default artifacts/analysis/fg_quality_drop_decision_<ts>).",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir) if str(args.outdir or "").strip() else None
    if outdir is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        outdir = Path("artifacts") / "analysis" / f"fg_quality_drop_decision_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    source_reports: list[Path] = []
    if args.source_report:
        for raw in args.source_report:
            p = Path(str(raw))
            if not p.exists():
                raise SystemExit(f"--source-report not found: {p}")
            source_reports.append(p)
    else:
        seeds = _parse_int_list(str(args.seeds))
        if not seeds:
            raise SystemExit("No valid seeds. Pass --seeds or --source-report.")
        for seed in seeds:
            seed_out = outdir / f"seed_{seed}"
            report_path = _run_one_harness(
                outdir=seed_out,
                config=str(args.config),
                song_limit=max(1, int(args.song_limit)),
                reps=max(1, int(args.reps_per_seed)),
                seed=int(seed),
                hitsim_seed=int(args.hitsim_seed),
                a=int(args.a),
                b=int(args.b),
                inflight_songs=int(args.inflight_songs),
                fg_download_topk=int(args.fg_download_topk),
                allow_sequential=bool(args.allow_sequential),
            )
            source_reports.append(report_path)

    reports = [_read_report(p) for p in source_reports]
    collected = _collect_from_reports(reports)
    pair_rows = list(collected["pair_rows"])
    song_rows = list(collected["song_rows"])

    thresholds = DecisionThresholds(
        alpha=float(args.alpha),
        min_pairs=max(1, int(args.min_pairs)),
        bootstrap_iters=max(100, int(args.bootstrap_iters)),
        bootstrap_seed=int(args.bootstrap_seed),
        min_effect_mean=float(args.min_effect_mean),
        min_song_support_frac=max(0.0, float(args.min_song_support_frac)),
        min_song_support_count=max(1, int(args.min_song_support_count)),
    )

    pair_deltas = [float(r.get("delta_gain_total", 0.0) or 0.0) for r in pair_rows]
    song_medians = [float(r.get("delta_fg_gain_median", 0.0) or 0.0) for r in song_rows]
    decision = decide_quality_drop(pair_deltas=pair_deltas, song_median_deltas=song_medians, thresholds=thresholds)

    report = _build_report(
        source_reports=source_reports,
        pair_rows=pair_rows,
        song_rows=song_rows,
        decision=decision,
        a_label=f"FG_CandidateLimit={int(args.a)}",
        b_label=f"FG_CandidateLimit={int(args.b)}",
    )
    report["thresholds"] = {
        "alpha": float(thresholds.alpha),
        "min_pairs": int(thresholds.min_pairs),
        "bootstrap_iters": int(thresholds.bootstrap_iters),
        "bootstrap_seed": int(thresholds.bootstrap_seed),
        "min_effect_mean": float(thresholds.min_effect_mean),
        "min_song_support_frac": float(thresholds.min_song_support_frac),
        "min_song_support_count": int(thresholds.min_song_support_count),
    }

    out_json = outdir / "quality_drop_declaration.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[declare] wrote {out_json}")
    print(f"[declare] declaration={decision['declaration']}")
    print(
        "[declare] pairs={} pos={} neg={} zero={} p_drop={:.6f} p_no_drop={:.6f}".format(
            int(decision["pair_count"]),
            int(decision["pair_sign_counts"]["positive"]),
            int(decision["pair_sign_counts"]["negative"]),
            int(decision["pair_sign_counts"]["zero"]),
            float(decision["p_drop_one_sided"]),
            float(decision["p_no_drop_one_sided"]),
        )
    )
    print(
        "[declare] mean_delta={:.2f} ci95=[{:.2f}, {:.2f}] songs(drop/no_drop/tie)={}/{}/{}".format(
            float(decision["pair_delta_mean"]),
            float(decision["pair_delta_mean_ci95"][0]),
            float(decision["pair_delta_mean_ci95"][1]),
            int(decision["song_drop_count"]),
            int(decision["song_no_drop_count"]),
            int(decision["song_tie_count"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
