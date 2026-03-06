import numpy as np
import pytest

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.solver import genetic
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.item_registry import ItemRegistry


pytestmark = pytest.mark.gpu


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


def test_gpu_ga_fg_selection_matches_cpu_candidate_selector():
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_download_fg_selected_payload
    from gear_optimizer.solver.taichi_gem import fields

    ensure_ready()

    rng = np.random.default_rng(1234)

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

    # Build a synthetic GA->FG candidate table slice for a single song slot.
    table_slot = 0
    n_runs = 3
    K = int(fields.GA_FG_CANDIDATES_PER_RUN)
    cols = int(fields.GA_FG_CANDIDATE_COLS)  # 24

    # Use the registry's dense item_stats table to compute base_stats7 like the pack kernel does.
    item_stats = np.asarray(registry.to_gpu_arrays()["item_stats"], dtype=np.int32)
    slot_start = np.asarray(registry.slot_start, dtype=np.int32)
    slot_count = np.asarray(registry.slot_count, dtype=np.int32)

    def sample_genome_ids() -> np.ndarray:
        ids = np.zeros((9,), dtype=np.int32)
        for slot_idx in range(9):
            c = int(slot_count[slot_idx])
            if c <= 0:
                ids[slot_idx] = 0
                continue
            ids[slot_idx] = int(slot_start[slot_idx]) + int(rng.integers(0, c))
        # Ensure mini uniqueness + permutations.
        if int(slot_count[6]) >= 3:
            picks = rng.choice(int(slot_count[6]), size=3, replace=False).astype(np.int32)
            ids[6:9] = int(slot_start[6]) + picks
            ids[6:9] = ids[6:9][rng.permutation(3)]
        return ids

    base_genomes = [sample_genome_ids() for _ in range(12)]
    dup_genome = base_genomes[0].copy()

    table = np.zeros((n_runs, K + 1, cols), dtype=np.int32)
    # Colors for proxy (matches default behavior in genetic decode).
    primary_color = "Rush"
    secondary_color = "Flow"
    color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    p_idx = int(color_to_idx[primary_color])
    s_idx = int(color_to_idx[secondary_color])

    for r in range(n_runs):
        best_row = 1
        best_score = -1

        for j in range(K):
            row = 1 + j

            if j % 7 == 0:
                genome_ids = dup_genome.copy()
                genome_ids[6:9] = genome_ids[6:9][rng.permutation(3)]
                score = int(50_000 + (r * 10_000) + rng.integers(0, 500))
            else:
                genome_ids = base_genomes[int(rng.integers(0, len(base_genomes)))].copy()
                score = int(rng.integers(1, 80_000))

            ft = int(rng.integers(0, 100))
            ff = int(rng.integers(0, 100))
            pp_g = int(rng.integers(0, 60))
            cm_g = int(rng.integers(0, 60))
            fm_g = int(rng.integers(0, 60))
            ov_g = int(rng.integers(0, 60))

            # Base stats (sum of per-item stats; fixed base offsets are irrelevant for ordering in this test).
            stats10 = item_stats[genome_ids].sum(axis=0).astype(np.int32, copy=False)
            pp = int(stats10[0])
            cm = int(stats10[1])
            fm = int(stats10[2])
            ft_stat = int(stats10[3])
            ff_stat = int(stats10[4])
            p_val = int(stats10[p_idx])
            s_val = int(stats10[s_idx])

            table[r, row, 0] = int(score)
            table[r, row, 1 : 1 + 9] = genome_ids
            # result_row(7): [score, ft, ff, pp, cm, fm, ov]
            table[r, row, 1 + 9 : 1 + 9 + 7] = np.asarray([score, ft, ff, pp_g, cm_g, fm_g, ov_g], dtype=np.int32)
            # base_stats7(7): [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
            table[r, row, 1 + 9 + 7 : 1 + 9 + 7 + 7] = np.asarray(
                [pp, cm, fm, p_val, s_val, ft_stat, ff_stat], dtype=np.int32
            )

            if score > best_score:
                best_score = score
                best_row = row

        # Row 0: per-run best (used by header).
        table[r, 0, :] = table[r, best_row, :]

    # Upload into the full field shape (fill only the prefix we use).
    full = np.zeros(fields.ga_fg_candidates_packed.shape, dtype=np.int32)
    full[table_slot, :n_runs, : K + 1, :cols] = table
    fields.ga_fg_candidates_packed.from_numpy(full)

    limit = int(LOADOUTS_PER_SONG_LIMIT) + 25
    top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
    base_budget = min(limit, max(top_base_keep, int(limit * 0.55)))
    fg_budget_end = min(limit, base_budget + int(limit * 0.30))

    selected_payload = ga_download_fg_selected_payload(
        table_slot=int(table_slot),
        n_runs=int(n_runs),
        limit=int(limit),
        top_base_keep=int(top_base_keep),
        base_budget=int(base_budget),
        fg_budget_end=int(fg_budget_end),
    )

    cfg_data = {
        "selected_color": "Rush",
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "fg_candidate_limit": int(limit),
    }

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed={},
        fg_candidate_limit=int(limit),
    )

    # Reference selection: build unique stubs from the same candidate table and call CPU selector.
    best_stub_by_key: dict[tuple[int, ...], tuple[int, int, int]] = {}
    for r in range(n_runs):
        for row in range(1, K + 1):
            score_val = int(table[r, row, 0])
            if score_val <= 0:
                continue
            genome_ids = np.asarray(table[r, row, 1 : 1 + 9], dtype=np.int32)
            ids_key = _canon_ids_key(genome_ids)
            prev = best_stub_by_key.get(ids_key)
            if prev is None or score_val > prev[0]:
                best_stub_by_key[ids_key] = (score_val, int(r), int(row))

    stub_candidates: list[dict] = []
    for _ids_key, (score_val, run_idx, row) in best_stub_by_key.items():
        genome_ids = np.asarray(table[int(run_idx), int(row), 1 : 1 + 9], dtype=np.int32)
        genome = registry.decode_genome(genome_ids)
        res_row = np.asarray(table[int(run_idx), int(row), 1 + 9 : 1 + 9 + 7], dtype=np.int32)
        stub_candidates.append(
            {
                "Score": int(score_val),
                "BaseScore": int(score_val),
                "Genome": genome,
                "Gear": genome[:6],
                "Minis": genome[6:9],
                "Data": {"FT": int(res_row[1]), "FF": int(res_row[2])},
            }
        )

    expected = select_fg_candidates(
        stub_candidates,
        limit=int(limit),
        primary_color=str(primary_color),
        secondary_color=str(secondary_color),
    )

    assert [_candidate_key(c, registry) for c in decoded] == [_candidate_key(c, registry) for c in expected]
