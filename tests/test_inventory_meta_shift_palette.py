import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pytest

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer import run_inventory_meta_coverage


ELEMENTS: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _details(selected_element: str, *, pp: int, cm: int, fm: int, ft: int, ff: int, ov: int) -> Dict[str, Any]:
    return {
        "FT": int(ft),
        "FF": int(ff),
        "GemCounts": {
            "Perfect Points": int(pp),
            "Combo Multiplier": int(cm),
            "Fever Multiplier": int(fm),
            "Element": int(ov),
        },
        "SelectedElement": str(selected_element),
        "PrimaryColor": str(selected_element),
        "SecondaryColor": "Flow",
    }


def _insert_loadout(
    conn,
    *,
    song_name: str,
    score: int,
    gear_names: List[str],
    minis_groups: List[List[str]],
    details: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(best_score, excluded.best_score),
            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
            last_updated = excluded.last_updated
        """,
        (song_name, int(score), 0, time.time()),
    )
    conn.execute(
        """
        INSERT INTO loadouts (
            song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            song_name,
            f"{song_name}-{score}-{random.getrandbits(32)}",
            int(score),
            0,
            json.dumps(list(gear_names), ensure_ascii=False),
            json.dumps(list(minis_groups), ensure_ascii=False),
            json.dumps(details, ensure_ascii=False),
            None,
            time.time(),
        ),
    )


def _sum6(vecs: Iterable[Tuple[int, int, int, int, int]]) -> Tuple[int, int, int, int, int]:
    pp = cm = fm = ft = ff = 0
    for v in vecs:
        pp += int(v[0])
        cm += int(v[1])
        fm += int(v[2])
        ft += int(v[3])
        ff += int(v[4])
    return pp, cm, fm, ft, ff


def _make_shift_workload(db_path: Path, *, songs: int, seed: int) -> None:
    """
    Small synthetic "shift-piece" workload (exact-peak-only) to validate that the learned
    wildcard palette increases coverage by exposing additional common 15-gem vectors.
    """
    rnd = random.Random(int(seed))
    os.makedirs(db_path.parent, exist_ok=True)
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    score = 100

    core_gear = ["HatCore", "NeckCore", "FaceCore", "ShirtCore", "BackCore", "PantCore"]

    vocab: List[Tuple[int, int, int, int, int]] = [
        (15, 0, 0, 0, 0),
        (0, 15, 0, 0, 0),
        (0, 0, 15, 0, 0),
        (10, 5, 0, 0, 0),
        (0, 10, 5, 0, 0),
        (0, 5, 10, 0, 0),
        (7, 3, 5, 0, 0),
        (6, 0, 6, 3, 0),  # includes FT
        (6, 0, 6, 0, 3),  # includes FF
    ]

    core_package = [(15, 0, 0, 0, 0), (0, 15, 0, 0, 0), (0, 0, 15, 0, 0), (10, 5, 0, 0, 0)]
    cluster_a_tail = [(0, 10, 5, 0, 0), (6, 0, 6, 3, 0)]
    cluster_b_tail = [(0, 5, 10, 0, 0), (6, 0, 6, 0, 3)]

    conn = get_db_connection(str(db_path))
    try:
        for i in range(int(songs)):
            song_name = f"S{i:04d}"
            selected_element = rnd.choice(ELEMENTS)

            vecs = list(core_package) + (list(cluster_a_tail) if (i % 2) == 0 else list(cluster_b_tail))

            # Light perturbations: swap last vector to a nearby mixed vector and keep sum==90.
            if rnd.random() < 0.35:
                vecs[-1] = rnd.choice(vocab)
                pp, cm, fm, ft, ff = _sum6(vecs)
                target = 90
                delta = target - (pp + cm + fm + ft + ff)
                v0 = list(vecs[0])
                v0[0] = max(0, min(15, v0[0] + delta))
                v0[1] = 15 - (v0[0] + v0[2] + v0[3] + v0[4])
                if v0[1] < 0:
                    vecs[-1] = cluster_a_tail[-1] if (i % 2) == 0 else cluster_b_tail[-1]
                else:
                    vecs[0] = tuple(int(x) for x in v0)

            pp, cm, fm, ft, ff = _sum6(vecs)
            details = _details(selected_element, pp=pp, cm=cm, fm=fm, ft=ft, ff=ff, ov=0)

            _insert_loadout(
                conn, song_name=song_name, score=score, gear_names=list(core_gear), minis_groups=minis, details=details
            )

        conn.commit()
    finally:
        conn.close()


@pytest.mark.gpu
def test_wildcard_palette_improves_shift_workload(monkeypatch, tmp_path):
    db_path = tmp_path / "shift.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    _make_shift_workload(db_path, songs=240, seed=123)

    common = dict(
        solver="gpu_full",
        # Keep the cap tight so witness quality dominates coverage.
        inventory_cap=12,
        seed=123,
        restarts=1,
        partitions_per_song=32,
        adaptive_rounds=0,
        lns_time_sec=0.0,
        lns_attempts=50,
        gpu_repack_passes=2,
        gpu_full_top_candidates=1,
        gpu_full_candidate_score_delta=0,  # exact-peak-only
        profile=False,
    )

    base = run_inventory_meta_coverage(**common, gpu_full_wildcard_palette_size=0)
    pal = run_inventory_meta_coverage(**common, gpu_full_wildcard_palette_size=64)

    base_cov = int(base["stats"]["songs_covered"])
    pal_cov = int(pal["stats"]["songs_covered"])
    # Robust delta: palette should unlock more exact totals without regressing baseline coverage.
    assert pal_cov >= base_cov + 25
    assert int(pal["solver_stats"]["run_params"]["gpu_full_candidate_score_delta"]) == 0
