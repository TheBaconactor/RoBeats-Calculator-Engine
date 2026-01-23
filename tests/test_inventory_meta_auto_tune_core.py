from __future__ import annotations

from pathlib import Path
from typing import Optional

from inventory_optimizer.auto_tune import run_tuning_loop


class _CycleRng:
    def __init__(self) -> None:
        self._i = 0

    def randrange(self, start: int, stop: Optional[int] = None, step: int = 1) -> int:  # noqa: D401
        # Minimal subset of random.Random API used by the tuner.
        if stop is None:
            stop = start
            start = 0
        span = max(1, int(stop) - int(start))
        out = int(start) + (self._i % span)
        self._i += 1
        return out


def test_auto_tune_chooses_best_override_and_records_seeds(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "evolution.db"
    repo_root.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"")  # not used by the stub runner

    seeds = iter([101, 202, 303, 404])

    def seed_gen() -> int:
        return int(next(seeds))

    # Stub runner: coverage increases with anchor patterns. This lets us verify the tuner picks it.
    def run_label(label: str, element: Optional[str], kwargs: dict) -> dict:
        anchor = int(kwargs.get("gpu_full_witness_anchor_patterns") or 0)
        covered = 10
        if label == "All":
            covered = 100 + anchor
        return {
            "ok": True,
            "label": label,
            "time_sec": 0.01,
            "wall_time_sec": 0.02,
            "seed": int(kwargs.get("seed") or 0),
            "solver": str(kwargs.get("solver") or ""),
            "stats": {
                "songs_total": 500 if label == "All" else 100,
                "songs_covered": int(covered),
                "gear_variants_used": int(kwargs.get("inventory_cap") or 100),
                "gear_variants_cap": int(kwargs.get("inventory_cap") or 100),
                "unique_gears_used": 10,
            },
            "solver_stats": {},
        }

    summary = run_tuning_loop(
        repo_root=repo_root,
        db_path=db_path,
        inventory_cap=100,
        mode="fast",
        base_seed=1,
        trials=4,
        timeout_sec=1.0,
        search_space={"gpu_full_witness_anchor_patterns": [0, 24]},
        rng=_CycleRng(),  # alternates 0,24,0,24
        seed_generator=seed_gen,
        run_label=run_label,
    )

    assert len(summary.trials) == 4
    assert [t.seed for t in summary.trials] == [101, 202, 303, 404]

    # Best override should be the one that increases "All" coverage (anchor=24).
    assert summary.best_overrides.get("gpu_full_witness_anchor_patterns") == 24
