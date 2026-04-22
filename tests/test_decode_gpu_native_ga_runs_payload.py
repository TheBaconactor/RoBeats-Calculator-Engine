from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.utils import stats_signature
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.solver import genetic
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params


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


def _candidate_key(cand: dict, registry: ItemRegistry) -> tuple[int, ...]:
    genome_ids = cand.get("GenomeIDs")
    if genome_ids is not None:
        return _canon_ids_key(np.asarray(genome_ids, dtype=np.int32))
    genome = cand.get("Genome")
    if genome:
        return _canon_ids_key(registry.encode_genome(genome))
    gear = cand.get("Gear") or []
    minis = cand.get("Minis") or []
    return _canon_ids_key(registry.encode_genome(list(gear) + list(minis)))


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
    width = 1 + n_slots + 7 + 7
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
            runs_payload[r, row, 1 + n_slots + 7 : 1 + n_slots + 7 + 7] = 0

            if score > best_score:
                best_score = score
                best_ids = genome_ids.copy()
                best_res = res.copy()

        assert best_ids is not None
        assert best_res is not None
        runs_payload[r, 0, 0] = int(best_score)
        runs_payload[r, 0, 1 : 1 + n_slots] = best_ids
        runs_payload[r, 0, 1 + n_slots : 1 + n_slots + 7] = best_res
        runs_payload[r, 0, 1 + n_slots + 7 : 1 + n_slots + 7 + 7] = 0

    # decode_gpu_native_ga_runs_payload clamps candidate limits to at least
    # LOADOUTS_PER_SONG_LIMIT for DB/leaderboard stability.
    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT) + 25
    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": fg_candidate_limit,
    }

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

    # Build the GPU-selected payload format expected by decode_gpu_native_ga_runs_payload.
    best_run_idx = int(np.argmax(runs_payload[:, 0, 0]))
    best_score = int(runs_payload[best_run_idx, 0, 0])
    best_ids = np.asarray(runs_payload[best_run_idx, 0, 1 : 1 + n_slots], dtype=np.int32)
    best_res = np.asarray(runs_payload[best_run_idx, 0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32)

    selected_payload = np.zeros((len(expected) + 1, 26), dtype=np.int32)
    selected_payload[0, 0] = int(len(expected))
    selected_payload[0, 1] = int(best_score)
    selected_payload[0, 2 : 2 + n_slots] = best_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = best_res
    selected_payload[0, 2 + n_slots + 7] = int(best_run_idx)

    for i, cand in enumerate(expected):
        run_idx = int(cand.get("_run_idx", 0))
        pop_idx = int(cand.get("_pop_idx", 0))
        row = 1 + pop_idx
        selected_payload[i + 1, 0] = run_idx
        selected_payload[i + 1, 1] = row
        selected_payload[i + 1, 2 : 2 + width] = runs_payload[run_idx, row, :width]

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=fg_candidate_limit,
    )

    assert [_candidate_key(c, registry) for c in decoded] == [_candidate_key(c, registry) for c in expected]


def test_decode_gpu_native_ga_runs_payload_prefers_max_candidate_over_header():
    """
    Regression test:
    If the GPU-selected payload header best score is out-of-sync with the candidate
    rows, decoding must still return the true best score/loadout.
    """
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}") for i in range(4)] for slot in slots}
    mini_pool = [_item(f"M{i}") for i in range(6)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
    }

    # Build a GPU-selected payload: 1 candidate row with a higher score than the header best.
    n_slots = 9
    width = 1 + n_slots + 7 + 7  # packed row width inside candidate rows (24)
    selected_payload = np.zeros((2, 26), dtype=np.int32)

    # Header row: selected_count=1, best_score=50 (intentionally wrong), best_ids, best_res, best_run_idx
    selected_payload[0, 0] = 1
    selected_payload[0, 1] = 50
    # Use any valid genome ids for the header best.
    header_ids = np.asarray([registry.slot_start[i] for i in range(9)], dtype=np.int32)
    header_res = np.asarray([50, 1, 2, 0, 0, 0, 0], dtype=np.int32)
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = header_res
    selected_payload[0, 2 + n_slots + 7] = 0  # best_run_idx

    # Candidate row: run_idx=0, row_idx=1, packed_row with score=100
    cand_ids = np.asarray([registry.slot_start[i] + 1 for i in range(9)], dtype=np.int32)
    cand_res = np.asarray([100, 3, 4, 1, 1, 1, 1], dtype=np.int32)
    packed = np.zeros((width,), dtype=np.int32)
    packed[0] = 100
    packed[1 : 1 + n_slots] = cand_ids
    packed[1 + n_slots : 1 + n_slots + 7] = cand_res
    packed[1 + n_slots + 7 : 1 + n_slots + 7 + 7] = 0

    selected_payload[1, 0] = 0  # run_idx
    selected_payload[1, 1] = 1  # row_idx
    selected_payload[1, 2 : 2 + width] = packed

    best_data, best_gear, best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert int(best_data.get("Score", 0)) == 100
    assert best_gear and best_minis
    assert int(decoded[0].get("Score", 0)) == 100
    assert decoded[0].get("GenomeIDs")


def test_decode_gpu_native_selected_payload_dedups_duplicate_exact_rows():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}") for i in range(2 if slot == "Hat" else 1)] for slot in slots}
    mini_pool = [_item(f"M{i}") for i in range(3)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
    }

    n_slots = 9
    width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((4, 26), dtype=np.int32)

    dup_ids_a = np.asarray(
        [
            registry.slot_start[0],
            registry.slot_start[1],
            registry.slot_start[2],
            registry.slot_start[3],
            registry.slot_start[4],
            registry.slot_start[5],
            registry.slot_start[6] + 0,
            registry.slot_start[6] + 1,
            registry.slot_start[6] + 2,
        ],
        dtype=np.int32,
    )
    dup_ids_better = np.asarray(
        [
            registry.slot_start[0],
            registry.slot_start[1],
            registry.slot_start[2],
            registry.slot_start[3],
            registry.slot_start[4],
            registry.slot_start[5],
            registry.slot_start[6] + 2,
            registry.slot_start[6] + 0,
            registry.slot_start[6] + 1,
        ],
        dtype=np.int32,
    )
    unique_ids = dup_ids_a.copy()
    unique_ids[0] = registry.slot_start[0] + 1

    selected_payload[0, 0] = 3
    selected_payload[0, 1] = 110
    selected_payload[0, 2 : 2 + n_slots] = dup_ids_a
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = np.asarray([110, 1, 2, 0, 0, 0, 0], dtype=np.int32)
    selected_payload[0, 2 + n_slots + 7] = 0

    packed1 = np.zeros((width,), dtype=np.int32)
    packed1[0] = 110
    packed1[1 : 1 + n_slots] = dup_ids_a
    packed1[1 + n_slots : 1 + n_slots + 7] = np.asarray([110, 1, 2, 0, 0, 0, 0], dtype=np.int32)
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 1
    selected_payload[1, 2 : 2 + width] = packed1

    packed2 = np.zeros((width,), dtype=np.int32)
    packed2[0] = 150
    packed2[1 : 1 + n_slots] = dup_ids_better
    packed2[1 + n_slots : 1 + n_slots + 7] = np.asarray([150, 3, 4, 1, 1, 1, 1], dtype=np.int32)
    selected_payload[2, 0] = 0
    selected_payload[2, 1] = 2
    selected_payload[2, 2 : 2 + width] = packed2

    packed3 = np.zeros((width,), dtype=np.int32)
    packed3[0] = 120
    packed3[1 : 1 + n_slots] = unique_ids
    packed3[1 + n_slots : 1 + n_slots + 7] = np.asarray([120, 5, 6, 0, 0, 0, 0], dtype=np.int32)
    selected_payload[3, 0] = 0
    selected_payload[3, 1] = 3
    selected_payload[3, 2 : 2 + width] = packed3

    best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert len(decoded) == 2
    assert [int(cand.get("Score", 0)) for cand in decoded] == [150, 120]
    assert int(decoded[0]["Data"]["_ga_gpu_row_idx"]) == 2
    assert int(best_data.get("Score", 0)) == 150


def test_decode_gpu_native_selected_payload_emits_base_stats_without_full_stats(monkeypatch):
    monkeypatch.delenv("GA_DECODE_INCLUDE_STATS", raising=False)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _item(
                f"{slot}{i}",
                **{
                    "Perfect Points": 10 + i,
                    "Combo Multiplier": 20 + i,
                    "Fever Multiplier": 30 + i,
                    "Fever Time": 40 + i,
                    "Fever Fill Rate": 50 + i,
                    "Rush": 60 + i,
                    "Flow": 70 + i,
                },
            )
            for i in range(2)
        ]
        for slot in slots
    }
    mini_pool = [
        _item(
            f"M{i}",
            **{
                "Perfect Points": 5 + i,
                "Combo Multiplier": 6 + i,
                "Fever Multiplier": 7 + i,
                "Fever Time": 8 + i,
                "Fever Fill Rate": 9 + i,
                "Rush": 10 + i,
                "Flow": 11 + i,
            },
        )
        for i in range(4)
    ]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
        "fg_require_stats": True,
    }

    n_slots = 9
    width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((2, 26), dtype=np.int32)

    genome_ids = np.asarray(
        [
            registry.slot_start[0] + 1,
            registry.slot_start[1] + 1,
            registry.slot_start[2] + 1,
            registry.slot_start[3] + 1,
            registry.slot_start[4] + 1,
            registry.slot_start[5] + 1,
            registry.slot_start[6] + 0,
            registry.slot_start[6] + 1,
            registry.slot_start[6] + 2,
        ],
        dtype=np.int32,
    )
    res = np.asarray([100, 3, 4, 1, 1, 1, 1], dtype=np.int32)

    selected_payload[0, 0] = 1
    selected_payload[0, 1] = 100
    selected_payload[0, 2 : 2 + n_slots] = genome_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = res
    selected_payload[0, 2 + n_slots + 7] = 0

    packed = np.zeros((width,), dtype=np.int32)
    packed[0] = 100
    packed[1 : 1 + n_slots] = genome_ids
    packed[1 + n_slots : 1 + n_slots + 7] = res
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 1
    selected_payload[1, 2 : 2 + width] = packed

    best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert isinstance(best_data.get("Stats"), dict)
    assert decoded
    data = decoded[0]["Data"]
    assert isinstance(data.get("BaseStats"), dict)
    assert data["BaseStats"]["Perfect Points"] > 0
    assert "Stats" not in data
    assert decoded[0].get("GenomeIDs")
    assert not decoded[0].get("Gear")
    assert not decoded[0].get("Minis")


def test_decode_gpu_native_selected_payload_emits_full_stats_when_ga_requires_it(monkeypatch):
    monkeypatch.delenv("GA_DECODE_INCLUDE_STATS", raising=False)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _item(
                f"{slot}{i}",
                **{
                    "Perfect Points": 10 + i,
                    "Combo Multiplier": 20 + i,
                    "Fever Multiplier": 30 + i,
                    "Fever Time": 40 + i,
                    "Fever Fill Rate": 50 + i,
                    "Rush": 60 + i,
                    "Flow": 70 + i,
                },
            )
            for i in range(2)
        ]
        for slot in slots
    }
    mini_pool = [
        _item(
            f"M{i}",
            **{
                "Perfect Points": 5 + i,
                "Combo Multiplier": 6 + i,
                "Fever Multiplier": 7 + i,
                "Fever Time": 8 + i,
                "Fever Fill Rate": 9 + i,
                "Rush": 10 + i,
                "Flow": 11 + i,
            },
        )
        for i in range(4)
    ]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
        "ga_require_full_stats": True,
    }

    n_slots = 9
    width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((2, 26), dtype=np.int32)

    genome_ids = np.asarray(
        [
            registry.slot_start[0] + 1,
            registry.slot_start[1] + 1,
            registry.slot_start[2] + 1,
            registry.slot_start[3] + 1,
            registry.slot_start[4] + 1,
            registry.slot_start[5] + 1,
            registry.slot_start[6] + 0,
            registry.slot_start[6] + 1,
            registry.slot_start[6] + 2,
        ],
        dtype=np.int32,
    )
    res = np.asarray([100, 3, 4, 1, 1, 1, 1], dtype=np.int32)

    selected_payload[0, 0] = 1
    selected_payload[0, 1] = 100
    selected_payload[0, 2 : 2 + n_slots] = genome_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = res
    selected_payload[0, 2 + n_slots + 7] = 0

    packed = np.zeros((width,), dtype=np.int32)
    packed[0] = 100
    packed[1 : 1 + n_slots] = genome_ids
    packed[1 + n_slots : 1 + n_slots + 7] = res
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 1
    selected_payload[1, 2 : 2 + width] = packed

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert decoded
    data = decoded[0]["Data"]
    assert isinstance(data.get("BaseStats"), dict)
    assert isinstance(data.get("Stats"), dict)
    assert data["Stats"]["Perfect Points"] >= data["BaseStats"]["Perfect Points"]


def test_decode_gpu_native_ga_runs_payload_stamps_fg_group_meta_when_song_context_present(monkeypatch):
    monkeypatch.setenv("FG_BASELINE_GRID", "1")

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _item(
                f"{slot}0",
                **{
                    "Perfect Points": 10,
                    "Combo Multiplier": 4,
                    "Fever Multiplier": 6,
                    "Fever Time": 8,
                    "Fever Fill Rate": 7,
                    "Rush": 12,
                    "Flow": 9,
                },
            )
        ]
        for slot in slots
    }
    mini_pool = [_item(f"M{i}", **{"Rush": 3, "Flow": 2}) for i in range(4)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
        "fg_require_stats": True,
    }

    timestamps = np.linspace(0.0, 60.0, 256, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "decode_fg_group_meta",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps, "fg_timestamps": timestamps},
    }
    ref_arrays = {
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }

    n_slots = 9
    width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((2, 26), dtype=np.int32)
    genome_ids = np.asarray(registry.encode_genome([f"{slot}0" for slot in slots] + ["M0", "M1", "M2"]), dtype=np.int32)
    genome_ids_b = np.asarray(registry.encode_genome([f"{slot}0" for slot in slots] + ["M0", "M1", "M3"]), dtype=np.int32)
    result_row = np.asarray([1234, 5, 7, 1, 2, 3, 0], dtype=np.int32)

    selected_payload[0, 0] = 1
    selected_payload[0, 1] = 1234
    selected_payload[0, 2 : 2 + n_slots] = genome_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = result_row
    selected_payload[0, 2 + n_slots + 7] = 0

    packed = np.zeros((width,), dtype=np.int32)
    packed[0] = 1234
    packed[1 : 1 + n_slots] = genome_ids
    packed[1 + n_slots : 1 + n_slots + 7] = result_row
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 1
    selected_payload[1, 2 : 2 + width] = packed

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    assert len(decoded) == 1
    data = decoded[0]["Data"]
    base_stats = data["BaseStats"]
    meta = data.get("_fg_group_meta")
    assert isinstance(meta, dict)
    assert meta["selected_element"] == "Rush"
    assert meta["center_ft"] == 5
    assert meta["center_ff"] == 7
    assert meta["ga_run_idx"] == 0
    assert meta["ga_row_idx"] == 1
    assert meta["signature"] == stats_signature(base_stats, calc_song, "Rush")
    n_sections, non_fever_base = fg_baseline_params(base_stats, calc_song, ref_arrays)
    assert meta["group_key"] == ("Rush", int(n_sections), min(int(non_fever_base), 15))


def test_decode_gpu_native_ga_runs_payload_limits_fg_group_meta_stamping(monkeypatch):
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _item(
                f"{slot}0",
                **{
                    "Perfect Points": 10,
                    "Combo Multiplier": 4,
                    "Fever Multiplier": 6,
                    "Fever Time": 8,
                    "Fever Fill Rate": 7,
                    "Rush": 12,
                    "Flow": 9,
                },
            )
        ]
        for slot in slots
    }
    mini_pool = [_item(f"M{i}", **{"Rush": 3, "Flow": 2}) for i in range(3)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "fg_candidate_limit": int(LOADOUTS_PER_SONG_LIMIT),
        "fg_require_stats": True,
    }
    calc_song = {
        "metadata": {
            "Song Name": "decode_fg_group_meta_limit",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 60.0,
        },
        "song_data": {"timestamps": np.linspace(0.0, 60.0, 64, dtype=np.float32)},
    }
    ref_arrays = {
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }

    calls = {"count": 0}

    def _fake_build_fg_group_meta(**kwargs):
        calls["count"] += 1
        return {
            "signature": f"sig-{calls['count']}",
            "selected_element": kwargs["selected_element"],
            "center_ft": int(kwargs["center_ft"]),
            "center_ff": int(kwargs["center_ff"]),
        }

    monkeypatch.setattr(genetic, "build_fg_group_meta", _fake_build_fg_group_meta)

    n_slots = 9
    width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((3, 26), dtype=np.int32)
    genome_ids = np.asarray(registry.encode_genome([f"{slot}0" for slot in slots] + ["M0", "M1", "M2"]), dtype=np.int32)
    genome_ids_b = np.asarray(registry.encode_genome([f"{slot}0" for slot in slots] + ["M0", "M1", "M3"]), dtype=np.int32)

    packed_a = np.zeros((width,), dtype=np.int32)
    packed_a[0] = 1234
    packed_a[1 : 1 + n_slots] = genome_ids
    packed_a[1 + n_slots : 1 + n_slots + 7] = np.asarray([1234, 5, 7, 1, 2, 3, 0], dtype=np.int32)

    packed_b = np.zeros((width,), dtype=np.int32)
    packed_b[0] = 1200
    packed_b[1 : 1 + n_slots] = genome_ids_b
    packed_b[1 + n_slots : 1 + n_slots + 7] = np.asarray([1200, 6, 8, 2, 3, 4, 0], dtype=np.int32)

    selected_payload[0, 0] = 2
    selected_payload[0, 1] = 1234
    selected_payload[0, 2 : 2 + n_slots] = genome_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = packed_a[1 + n_slots : 1 + n_slots + 7]
    selected_payload[0, 2 + n_slots + 7] = 0
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 1
    selected_payload[1, 2 : 2 + width] = packed_a
    selected_payload[2, 0] = 0
    selected_payload[2, 1] = 2
    selected_payload[2, 2 : 2 + width] = packed_b

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        fg_group_meta_limit=1,
    )

    assert len(decoded) == 2
    assert decoded[0]["Data"]["_fg_group_meta"]["signature"] == "sig-1"
    assert "_fg_group_meta" not in decoded[1]["Data"]
    assert calls["count"] == 1
