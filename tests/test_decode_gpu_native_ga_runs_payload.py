from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_top_base_ga_candidates
from gear_optimizer.solver import genetic_pipeline_decode as genetic_decode
from gear_optimizer.solver.genetic_pipeline_decode import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.item_registry import ItemRegistry
if not getattr(genetic_decode, "_GPU_NATIVE_AVAILABLE", False):
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


def test_decode_gpu_native_ga_runs_payload_caps_raw_rows_to_fg_candidate_limit():
    # Decode no longer applies the host effective-select (that moved to the single
    # canonical FG-prep funnel select). It returns the RAW GPU-deduped pool: the
    # header best candidate prepended, plus the candidate rows capped at
    # fg_candidate_limit. With 81 distinct input rows whose global-best is beyond
    # the cap, decode returns best + fg_limit rows = fg_limit + 1.
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    base_stats = {
        "Perfect Points": 1,
        "Combo Multiplier": 1,
        "Fever Multiplier": 1,
        "Fever Time": 1,
        "Fever Fill Rate": 1,
        "Rush": 1,
        "Flow": 1,
    }
    gear_pool = {slot: [_item(f"{slot}0", **base_stats)] for slot in slots}
    mini_pool = [_item(f"M{i}", **base_stats) for i in range(14)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    fg_limit = int(LOADOUTS_PER_SONG_LIMIT)
    payload_limit = fg_limit + 30
    n_slots = 9
    packed_width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((payload_limit + 1, 2 + packed_width), dtype=np.int32)
    selected_payload[0, 0] = int(payload_limit)

    slot_start = np.asarray(registry.slot_start, dtype=np.int32)
    mini_start = int(slot_start[6])
    best_score = -1
    best_ids = None
    best_res = None
    row = 1
    for a in range(14):
        for b in range(a + 1, 14):
            for c in range(b + 1, 14):
                if row > payload_limit:
                    break
                ids = np.asarray([int(slot_start[i]) for i in range(6)] + [mini_start + a, mini_start + b, mini_start + c], dtype=np.int32)
                score = 10_000 + row
                res = np.asarray([score, row % 7, row % 5, 1, 2, 3, 4], dtype=np.int32)
                packed = np.zeros((packed_width,), dtype=np.int32)
                packed[0] = score
                packed[1 : 1 + n_slots] = ids
                packed[1 + n_slots : 1 + n_slots + 7] = res
                selected_payload[row, 0] = 0
                selected_payload[row, 1] = row
                selected_payload[row, 2 : 2 + packed_width] = packed
                if score > best_score:
                    best_score = score
                    best_ids = ids.copy()
                    best_res = res.copy()
                row += 1
            if row > payload_limit:
                break
        if row > payload_limit:
            break

    assert best_ids is not None
    assert best_res is not None
    selected_payload[0, 1] = int(best_score)
    selected_payload[0, 2 : 2 + n_slots] = best_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = best_res

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data={
            "selected_color": "Rush",
            "primary_color": "Rush",
            "secondary_color": "Flow",
            "fg_candidate_limit": int(fg_limit),
        },
        base_stats_fixed={},
        fg_candidate_limit=int(fg_limit),
    )

    # best candidate (header, the global-best beyond the row cap) + fg_limit rows.
    assert len(decoded) == fg_limit + 1


def test_decode_gpu_native_ga_runs_payload_includes_header_best_candidate():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}") for i in range(3)] for slot in slots}
    mini_pool = [_item(f"M{i}") for i in range(5)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    n_slots = 9
    packed_width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((3, 2 + packed_width), dtype=np.int32)
    selected_payload[0, 0] = 2

    slot_start = np.asarray(registry.slot_start, dtype=np.int32)
    header_ids = np.asarray(
        [slot_start[i] + 2 for i in range(6)] + [slot_start[6] + 0, slot_start[6] + 1, slot_start[6] + 2],
        dtype=np.int32,
    )
    header_res = np.asarray([1000, 3, 4, 1, 2, 3, 4], dtype=np.int32)
    selected_payload[0, 1] = 1000
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = header_res

    for row, score in ((1, 900), (2, 800)):
        ids = np.asarray(
            [slot_start[i] for i in range(6)]
            + [slot_start[6] + row, slot_start[6] + row + 1, slot_start[6] + row + 2],
            dtype=np.int32,
        )
        res = np.asarray([score, row, row, 0, 0, 0, 0], dtype=np.int32)
        packed = np.zeros((packed_width,), dtype=np.int32)
        packed[0] = score
        packed[1 : 1 + n_slots] = ids
        packed[1 + n_slots : 1 + n_slots + 7] = res
        selected_payload[row, 0] = 0
        selected_payload[row, 1] = row
        selected_payload[row, 2 : 2 + packed_width] = packed

    best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data={"selected_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert int(best_data["BaseScore"]) == 1000
    assert _candidate_key(decoded[0], registry) == _canon_ids_key(header_ids)
    assert int(decoded[0]["BaseScore"]) == 1000


def test_decode_gpu_native_ga_runs_payload_prefers_header_best_shape_on_tie():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}") for i in range(3)] for slot in slots}
    mini_pool = [_item(f"M{i}") for i in range(5)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    n_slots = 9
    packed_width = 1 + n_slots + 7 + 7
    selected_payload = np.zeros((2, 2 + packed_width), dtype=np.int32)
    selected_payload[0, 0] = 1

    slot_start = np.asarray(registry.slot_start, dtype=np.int32)
    header_ids = np.asarray(
        [slot_start[i] + 2 for i in range(6)] + [slot_start[6] + 0, slot_start[6] + 1, slot_start[6] + 2],
        dtype=np.int32,
    )
    header_res = np.asarray([1000, 3, 4, 1, 2, 3, 4], dtype=np.int32)
    selected_payload[0, 1] = 1000
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = header_res

    packed = np.zeros((packed_width,), dtype=np.int32)
    packed[0] = 1000
    packed[1 : 1 + n_slots] = header_ids
    packed[1 + n_slots : 1 + n_slots + 7] = header_res
    selected_payload[1, 0] = 0
    selected_payload[1, 1] = 0
    selected_payload[1, 2 : 2 + packed_width] = packed

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data={"selected_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
        base_stats_fixed={},
        fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
    )

    assert _candidate_key(decoded[0], registry) == _canon_ids_key(header_ids)
    assert "Stats" in decoded[0]["Data"]
    assert "BaseStats" not in decoded[0]["Data"]


def test_decode_gpu_native_ga_runs_payload_rejects_legacy_raw_runs_payload():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    registry = ItemRegistry({slot: [_item(f"{slot}0")] for slot in slots}, [_item(f"M{i}") for i in range(3)], slots)
    legacy_payload = np.zeros((1, 2, 24), dtype=np.int32)

    with pytest.raises(ValueError, match="2D selected payload"):
        decode_gpu_native_ga_runs_payload(
            runs_payload=legacy_payload,
            registry=registry,
            cfg_data={"selected_color": "Rush"},
            base_stats_fixed={},
            fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        )


def test_decode_raw_pool_then_fg_prep_select_matches_canonical_selector():
    # Decode returns the RAW GPU-deduped pool (no effective-fold); the single
    # canonical color-folded select runs downstream at the FG-prep funnel layer.
    # This pins the funnel composition: select(decode(payload)) == the canonical
    # host select over the same candidates. The payload candidate rows here are the
    # canonical-selected set, so feeding decode's output back through the selector
    # must reproduce it exactly (the selector is idempotent on its own output).
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
    # canonical bounded compaction helper.
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

    expected = select_top_base_ga_candidates(
        stub_candidates,
        limit=int(fg_candidate_limit),
        registry=registry,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
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

    # Funnel composition: the canonical color-folded select over decode's RAW pool
    # reproduces the canonical-selected set (matches what FG-prep does in production
    # via prepare_ga_candidate_surface_for_fg). Compare as SETS of canonical ids.
    funnel = select_top_base_ga_candidates(
        list(decoded),
        limit=int(fg_candidate_limit),
        registry=registry,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
    )
    assert {_candidate_key(c, registry) for c in funnel} == {
        _candidate_key(c, registry) for c in expected
    }


def test_decode_gpu_native_ga_runs_payload_rejects_candidate_score_above_header_best():
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

    with pytest.raises(RuntimeError, match="candidate score exceeds header best score"):
        decode_gpu_native_ga_runs_payload(
            runs_payload=selected_payload,
            registry=registry,
            cfg_data=cfg_data,
            base_stats_fixed={},
            fg_candidate_limit=int(LOADOUTS_PER_SONG_LIMIT),
        )


def test_decode_gpu_native_selected_payload_dedups_duplicate_exact_rows():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_item(f"{slot}{i}") for i in range(2 if slot == "Hat" else 1)] for slot in slots}
    mini_pool = [_item(f"M{i}") for i in range(4)]
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

    header_ids = dup_ids_a.copy()
    header_ids[8] = registry.slot_start[6] + 3

    selected_payload[0, 0] = 3
    selected_payload[0, 1] = 160
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = np.asarray([160, 3, 4, 1, 1, 1, 1], dtype=np.int32)
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

    assert len(decoded) == 3
    assert [int(cand.get("Score", 0)) for cand in decoded] == [160, 150, 120]
    assert int(decoded[1]["Data"]["_ga_gpu_row_idx"]) == 2
    assert int(best_data.get("Score", 0)) == 160


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
    header_ids = genome_ids.copy()
    header_ids[8] = registry.slot_start[6] + 3
    header_res = np.asarray([101, 3, 4, 1, 1, 1, 1], dtype=np.int32)
    selected_payload[0, 1] = 101
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = header_res
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
    data = decoded[1]["Data"]
    assert isinstance(data.get("BaseStats"), dict)
    assert data["BaseStats"]["Perfect Points"] > 0
    assert "Stats" not in data
    assert decoded[1].get("GenomeIDs")
    assert not decoded[1].get("Gear")
    assert not decoded[1].get("Minis")


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
    header_ids = genome_ids.copy()
    header_ids[8] = registry.slot_start[6] + 3
    header_res = np.asarray([101, 3, 4, 1, 1, 1, 1], dtype=np.int32)
    selected_payload[0, 1] = 101
    selected_payload[0, 2 : 2 + n_slots] = header_ids
    selected_payload[0, 2 + n_slots : 2 + n_slots + 7] = header_res
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
    data = decoded[1]["Data"]
    assert isinstance(data.get("BaseStats"), dict)
    assert isinstance(data.get("Stats"), dict)
    assert data["Stats"]["Perfect Points"] >= data["BaseStats"]["Perfect Points"]
