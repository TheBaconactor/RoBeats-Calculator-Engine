from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.solver import genetic
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.item_registry import ItemRegistry


if not getattr(genetic, "_GPU_NATIVE_AVAILABLE", False):
    pytest.skip("GPU-native GA modules not available", allow_module_level=True)


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _canon_ids_key(genome_ids: np.ndarray) -> tuple[int, ...]:
    gear_ids = tuple(int(x) for x in genome_ids[:6])
    mini_ids = tuple(sorted(int(x) for x in genome_ids[6:9]))
    return gear_ids + mini_ids


def _key_by_name(cand: dict) -> tuple[str, ...]:
    gear_names = tuple((it or {}).get("Name", "") for it in (cand.get("Gear") or []))
    mini_names = tuple(sorted((it or {}).get("Name", "") for it in (cand.get("Minis") or [])))
    return gear_names + mini_names


def test_decode_gpu_native_ga_runs_payload_matches_fg_candidate_selector():
    rng = np.random.default_rng(12345)

    def rand_stats() -> dict:
        return {
            "Perfect Points": int(rng.integers(0, 50)),
            "Combo Multiplier": int(rng.integers(0, 20)),
            "Fever Multiplier": int(rng.integers(0, 20)),
            "Fever Time": int(rng.integers(0, 20)),
            "Fever Fill Rate": int(rng.integers(0, 20)),
            "Beat": int(rng.integers(0, 20)),
            "Vibe": int(rng.integers(0, 20)),
            "Rush": int(rng.integers(0, 20)),
            "Flow": int(rng.integers(0, 20)),
            "Chill": int(rng.integers(0, 20)),
        }

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}", **rand_stats()) for i in range(8)] for slot in slots}
    mini_pool = [_item(f"M{i}", **rand_stats()) for i in range(10)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    n_runs = 3
    n_genomes = 50
    n_slots = 9
    width = 1 + n_slots + 7
    runs_payload = np.zeros((n_runs, n_genomes + 1, width), dtype=np.int32)

    slot_start = np.asarray(registry.slot_start, dtype=np.int32)
    slot_count = np.asarray(registry.slot_count, dtype=np.int32)

    def sample_genome_ids() -> np.ndarray:
        ids = np.zeros((n_slots,), dtype=np.int32)
        for slot_idx in range(n_slots):
            c = int(slot_count[slot_idx])
            if c <= 0:
                ids[slot_idx] = 0
                continue
            ids[slot_idx] = int(slot_start[slot_idx]) + int(rng.integers(0, c))

        # Ensure mini uniqueness; also permute to produce permutations across rows.
        if int(slot_count[6]) >= 3:
            picks = rng.choice(int(slot_count[6]), size=3, replace=False).astype(np.int32)
            ids[6:9] = int(slot_start[6]) + picks
            ids[6:9] = ids[6:9][rng.permutation(3)]
        return ids

    for r in range(n_runs):
        best_score = -1
        best_ids: np.ndarray | None = None
        best_res: np.ndarray | None = None

        for i in range(n_genomes):
            row = 1 + i
            genome_ids = sample_genome_ids()
            score = int(rng.integers(1, 100_000))
            ft = int(rng.integers(0, 100))
            ff = int(rng.integers(0, 100))
            pp = int(rng.integers(0, 50))
            cm = int(rng.integers(0, 50))
            fm = int(rng.integers(0, 50))
            ov = int(rng.integers(0, 50))
            res = np.asarray([score, ft, ff, pp, cm, fm, ov], dtype=np.int32)

            runs_payload[r, row, 0] = score
            runs_payload[r, row, 1 : 1 + n_slots] = genome_ids
            runs_payload[r, row, 1 + n_slots : 1 + n_slots + 7] = res

            if score > best_score:
                best_score = score
                best_ids = genome_ids.copy()
                best_res = res.copy()

        assert best_ids is not None
        assert best_res is not None
        runs_payload[r, 0, 0] = int(best_score)
        runs_payload[r, 0, 1 : 1 + n_slots] = best_ids
        runs_payload[r, 0, 1 + n_slots : 1 + n_slots + 7] = best_res

    # decode_gpu_native_ga_runs_payload clamps candidate limits to at least
    # LOADOUTS_PER_SONG_LIMIT for DB/leaderboard stability.
    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT) + 25
    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": fg_candidate_limit,
    }

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=fg_candidate_limit,
    )

    # Reference path: construct full stub candidates and delegate selection to the
    # existing select_fg_candidates() implementation (the previous behavior).
    best_stub_by_key: dict[tuple[int, ...], tuple[int, int, int]] = {}
    for r in range(n_runs):
        run_pack = runs_payload[r]
        pop_snapshot = run_pack[1 : n_genomes + 1, 1 : 1 + n_slots]
        scores_snapshot = run_pack[1 : n_genomes + 1, 0]

        top_indices = np.argsort(scores_snapshot)[::-1]
        if top_indices.size:
            top_indices = top_indices[scores_snapshot[top_indices] > 0]

        for idx in top_indices:
            genome_ids = np.asarray(pop_snapshot[int(idx)], dtype=np.int32)
            ids_key = _canon_ids_key(genome_ids)
            score_val = int(scores_snapshot[int(idx)])
            prev = best_stub_by_key.get(ids_key)
            if prev is None or score_val > prev[0]:
                best_stub_by_key[ids_key] = (score_val, int(r), int(idx))

    stub_candidates: list[dict] = []
    for _ids_key, (score_val, run_idx, pop_idx) in best_stub_by_key.items():
        row = 1 + int(pop_idx)
        genome_ids = np.asarray(runs_payload[int(run_idx), row, 1 : 1 + n_slots], dtype=np.int32)
        genome = registry.decode_genome(genome_ids)
        res_row = np.asarray(runs_payload[int(run_idx), row, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32)
        stub_candidates.append(
            {
                "Score": int(score_val),
                "BaseScore": int(score_val),
                "Genome": genome,
                "Gear": genome[:6],
                "Minis": genome[6:9],
                "Data": {"FT": int(res_row[1]), "FF": int(res_row[2])},
                "_run_idx": int(run_idx),
                "_pop_idx": int(pop_idx),
            }
        )

    expected = select_fg_candidates(
        stub_candidates,
        limit=int(fg_candidate_limit),
        primary_color=str(cfg_data.get("primary_color", "") or ""),
        secondary_color=str(cfg_data.get("secondary_color", "") or ""),
    )

    assert [_key_by_name(c) for c in decoded] == [_key_by_name(c) for c in expected]
