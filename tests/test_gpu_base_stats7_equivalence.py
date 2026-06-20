"""Slice 2 equivalence + bit-exactness proofs (GPU / Vulkan).

Two proofs on REAL device data produced by the production GPU-native GA entrypoint
(run_gpu_native_ga_runs_payload_prebuilt):

1. INPUT equivalence: the packed payload ``base_stats7`` (cols 19..25 of each
   candidate row) is bit-exact equal to the 7-vector the host FG path derives from
   each candidate's ``BaseStats`` dict
   ([pp, cm, fm, base[primary], base[secondary], ft, ff]). This is the design claim
   the fused GA->FG handoff rests on.

2. OUTPUT bit-exactness: scoring the SAME real GA candidates through the FG response
   frontier with the device ``base_stats7`` (Slice 2) vs the host dict-derivation
   (pre-Slice-2) produces IDENTICAL fg scores per candidate. This isolates the
   Slice 2 source swap from the unseeded production GA's run-to-run drift: it proves
   the swap itself changes nothing, deterministically.

If proof 1 fails the design claim is falsified and Slice 2 must not proceed; if proof
2 fails the swap is not bit-exact.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.solver import genetic_pipeline as genetic
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.force_greats_common import FG_BASE_STATS7_KEY
from gear_optimizer.solver.genetic_pipeline import (
    decode_gpu_native_ga_runs_payload,
    run_gpu_native_ga_runs_payload_prebuilt,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu


# base_stats7 packed column layout (cols 19..25 of a 26-wide candidate row):
#   row = [run_idx, row_idx, score, ids(9), results(7), base_stats7(7)]
#   base_stats7 = [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
_BASE_STATS7_COL0 = 2 + 1 + 9 + 7  # run_idx,row_idx + score + ids(9) + results(7) = 19
_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _build_registry() -> ItemRegistry:
    """Real registry with varied, nonzero item stats across all elemental colors."""
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool: dict[str, list[dict]] = {}
    for s_idx, slot in enumerate(slots):
        items = []
        for i in range(4):
            items.append(
                _item(
                    f"{slot}{i}",
                    **{
                        "Perfect Points": 7 + s_idx + i,
                        "Combo Multiplier": 3 + i,
                        "Fever Multiplier": 2 + s_idx,
                        "Fever Time": 4 + i,
                        "Fever Fill Rate": 5 + s_idx,
                        "Beat": 6 + i,
                        "Vibe": 2 + s_idx,
                        "Rush": 3 + i,
                        "Flow": 4 + s_idx,
                        "Chill": 1 + i,
                    },
                )
            )
        gear_pool[slot] = items

    mini_pool = []
    for i in range(12):
        mini_pool.append(
            _item(
                f"M{i}",
                **{
                    "Perfect Points": 2 + (i % 5),
                    "Combo Multiplier": 1 + (i % 3),
                    "Fever Multiplier": 1 + (i % 4),
                    "Fever Time": 1 + (i % 2),
                    "Fever Fill Rate": 2 + (i % 3),
                    "Beat": 1 + (i % 4),
                    "Vibe": 2 + (i % 2),
                    "Rush": 1 + (i % 5),
                    "Flow": 3 + (i % 2),
                    "Chill": 1 + (i % 3),
                },
            )
        )
    return ItemRegistry(gear_pool, mini_pool, slots)


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.4, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(*, n_notes: int = 400) -> dict:
    timestamps = np.linspace(0, 90, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "Slice2 base_stats7 equivalence song",
            "Difficulty": "Hard",
            "Primary Color": _PRIMARY_COLOR,
            "Secondary Color": _SECONDARY_COLOR,
            "Total Notes": int(n_notes),
            "Long Notes": 10,
            "Last Note Time": float(timestamps[-1]),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": timestamps},
    }


def _host_base_components_from_dict(base_stats: dict, *, primary: str, secondary: str) -> tuple[int, ...]:
    """The EXACT 7-vector prepare_force_greats_response_frontier_scoring_batch builds."""
    return (
        int(base_stats.get("Perfect Points", 0) or 0),
        int(base_stats.get("Combo Multiplier", 0) or 0),
        int(base_stats.get("Fever Multiplier", 0) or 0),
        int(base_stats.get(primary, 0) or 0) if primary else 0,
        int(base_stats.get(secondary, 0) or 0) if secondary else 0,
        int(base_stats.get("Fever Time", 0) or 0),
        int(base_stats.get("Fever Fill Rate", 0) or 0),
    )


@pytest.fixture(scope="module")
def real_ga_run():
    """Run the production GPU-native GA once on Vulkan; return decoded artifacts.

    Yields (decoded_candidates, payload_base_stats7, calc_song, ref_arrays).
    """
    if not _has_taichi():
        pytest.skip("Taichi not available")
    if not getattr(genetic, "_GPU_NATIVE_AVAILABLE", False):
        pytest.skip("GPU-native GA modules not available")

    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )

    registry = _build_registry()
    gpu_arrays = registry.to_gpu_arrays()
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(gpu_arrays["slot_count"], dtype=np.int32)

    base_stats_fixed: dict[str, int] = {}
    cfg_data = {
        "selected_color": _SELECTED_COLOR,
        "primary_color": _PRIMARY_COLOR,
        "secondary_color": _SECONDARY_COLOR,
        "TotalBudget": 90,
        "GemScaleFever": 3,
        "fg_candidate_limit": 51,
    }
    base_fixed_stats_arr, _sel = genetic.build_base_fixed_stats_array(base_stats_fixed, cfg_data)
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=_PRIMARY_COLOR,
        secondary_color=_SECONDARY_COLOR,
        selected_color=_SELECTED_COLOR,
    )

    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    color_flags = build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)

        selected_payload = run_gpu_native_ga_runs_payload_prebuilt(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=6,
            initial_populations=None,
            num_runs=2,
            n_genomes=64,
            color_flags=color_flags,
            cfg_data=cfg_data,
            ga_seed=20260612,
            fg_gear_name_rank=gear_name_rank,
            fg_mini_sig_id=mini_sig_id,
        )

    selected_payload = np.asarray(selected_payload, dtype=np.int32)
    assert selected_payload.ndim == 2
    selected_n = int(selected_payload[0, 0])
    assert selected_n > 0, "real GA produced an empty selected payload"

    cand_rows = selected_payload[1 : 1 + selected_n]
    payload_base_stats7 = np.asarray(cand_rows[:, _BASE_STATS7_COL0 : _BASE_STATS7_COL0 + 7], dtype=np.int32)

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed=base_stats_fixed,
        fg_candidate_limit=51,
    )
    return decoded, payload_base_stats7, calc_song, ref_arrays


def test_payload_base_stats7_matches_host_base_components_on_real_ga(real_ga_run) -> None:
    decoded, payload_base_stats7, _calc_song_d, _ref_arrays_d = real_ga_run
    selected_n = int(payload_base_stats7.shape[0])

    # At least one candidate row must carry a nonzero base_stats7 (otherwise the proof
    # is vacuous: zeros would trivially "match" a zero dict).
    assert int(np.count_nonzero(payload_base_stats7)) > 0, (
        "payload base_stats7 is all zeros; the equivalence proof would be vacuous"
    )

    # decoded[0] is the header global-best candidate (no candidate-row base_stats7).
    # decoded[1:] correspond 1:1 (post identical dedup) to cand_rows order.
    candidate_decoded = decoded[1:]
    assert len(candidate_decoded) == selected_n, (
        f"decode candidate count {len(candidate_decoded)} != payload selected_n {selected_n}; "
        "the row-order/dedup assumption is broken"
    )

    mismatches: list[str] = []
    for i, cand in enumerate(candidate_decoded):
        data = cand.get("Data") or {}
        base_stats = data.get("BaseStats")
        assert isinstance(base_stats, dict) and base_stats, (
            f"decoded candidate {i} is missing the BaseStats dict (decode contract changed)"
        )
        # decode must also attach the device base_stats7 to every candidate (Slice 2).
        attached = data.get(FG_BASE_STATS7_KEY)
        assert attached is not None and tuple(int(v) for v in attached) == tuple(
            int(v) for v in payload_base_stats7[i].tolist()
        ), f"decoded candidate {i} did not carry the payload base_stats7 on its Data"

        host_vec = _host_base_components_from_dict(base_stats, primary=_PRIMARY_COLOR, secondary=_SECONDARY_COLOR)
        payload_vec = tuple(int(v) for v in payload_base_stats7[i].tolist())
        if host_vec != payload_vec:
            mismatches.append(
                f"row {i}: payload={payload_vec} host_dict={host_vec} "
                f"(ids={[int(x) for x in cand.get('GenomeIDs', [])]})"
            )

    assert not mismatches, (
        "base_stats7 != host base_components on real device data — design claim FALSIFIED; "
        "Slice 2 must not proceed.\n" + "\n".join(mismatches[:20])
    )


def _raw_fg_scores(plan) -> list[list[int]]:
    """Per-batch, per-row raw FG best_score (before the winner-emit gate)."""
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine

    prepared_results, _timings = GpuScoreEngine.score_plan(plan, gpu_client=None)
    return [[int(r.best_score) for r in batch_results] for batch_results in prepared_results]


def test_fg_scores_identical_device_base_stats7_vs_host_dict(real_ga_run) -> None:
    """Scoring the real GA candidates with device base_stats7 (Slice 2) equals scoring
    them with the host BaseStats-dict derivation (pre-Slice-2) — bit-exact fg scores.

    Compares RAW per-row solve scores (before the FG winner-emit gate), so the proof
    holds even when no candidate's FG beats its base on this synthetic song.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    decoded, _payload_base_stats7, calc_song, ref_arrays = real_ga_run

    device_candidates = [copy.deepcopy(c) for c in decoded]
    assert device_candidates, "no GA candidates decoded"
    assert any(
        isinstance(c.get("Data"), dict) and c["Data"].get(FG_BASE_STATS7_KEY) is not None for c in device_candidates
    ), "fixture produced no candidate carrying device base_stats7"

    # Pre-Slice-2 behaviour: strip the device vector so the planner derives
    # base_components from each candidate's BaseStats dict instead.
    dict_candidates = [copy.deepcopy(c) for c in decoded]
    for cand in dict_candidates:
        data = cand.get("Data")
        if isinstance(data, dict):
            data.pop(FG_BASE_STATS7_KEY, None)

    with _GPU_LOCK:
        # Build the candidate-independent FG response-frontier bundle for this song
        # (the startup prebuild's job in production) so the sync scoring path has it.
        reset_fg_response_frontier_payload_cache()
        build_or_load_response_frontier_payload(
            calc_song,
            ref_arrays,
            stat_keys=tuple((ft, ff) for ft in range(TOTAL_ROWS + 1) for ff in range(TOTAL_ROWS + 1)),
        )

        device_plan = FgPlanner.plan_many(device_candidates, calc_song, ref_arrays, _PRIMARY_COLOR)
        dict_plan = FgPlanner.plan_many(dict_candidates, calc_song, ref_arrays, _PRIMARY_COLOR)

        # Sanity: the device plan must actually be sourced from base_stats7 (differs from
        # the dict-derived array only if they were ever unequal; here they are equal, so
        # assert the source wiring instead — device batches carry the payload vectors).
        device_components = np.concatenate(
            [np.asarray(p.batch.base_components, dtype=np.int64) for p in device_plan.prepared_batches]
        )
        dict_components = np.concatenate(
            [np.asarray(p.batch.base_components, dtype=np.int64) for p in dict_plan.prepared_batches]
        )
        assert device_components.shape == dict_components.shape
        assert np.array_equal(device_components, dict_components), (
            "device base_stats7 and host dict base_components disagree (input equivalence broken)"
        )

        device_scores = _raw_fg_scores(device_plan)
        dict_scores = _raw_fg_scores(dict_plan)

    assert any(row for row in device_scores), "device scoring produced no solve results"
    assert device_scores == dict_scores, (
        "FG raw scores differ between device base_stats7 and host dict derivation — Slice 2 swap is NOT bit-exact"
    )
