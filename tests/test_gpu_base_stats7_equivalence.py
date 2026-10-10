"""The GA's device base_stats7 equals the host's pre-gem totals (GPU / Vulkan).

On REAL device data from the production GPU-native GA entrypoint (run_gpu_native_ga_runs_payload_prebuilt): each
selected row's packed base_stats7 (cols 19..25) is bit-exact equal to the 7-vector the FG stage derives on the host
from the row's genome ids ([pp, cm, fm, base[primary], base[secondary], ft, ff] of the song's fixed stats plus the
items). The FG stage scores the device vectors in the GA turn and looks each selected loadout's row up by its host
vector, so this equality is what makes the lookup exact.
"""

from __future__ import annotations

from tests.curves_support import synthetic_curves

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.solver.base_stats import build_stats_array, build_stats_dict
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
from gear_optimizer.solver.genetic_pipeline import (
    run_gpu_native_ga_runs_payload_prebuilt,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.gamedata import Gear, SongMini
from tests.items_support import make_gear, make_song_mini
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
from tests.songs_support import make_song

pytestmark = pytest.mark.gpu


# base_stats7 packed column layout (cols 19..25 of a 26-wide candidate row):
#   row = [run_idx, row_idx, score, ids(9), results(7), base_stats7(7)]
#   base_stats7 = [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
_BASE_STATS7_COL0 = 2 + 1 + 9 + 7  # run_idx,row_idx + score + ids(9) + results(7) = 19
_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"


def _item(name: str, **stats: int) -> Gear:
    return make_gear(name, **stats)


def _mini_item(name: str, **stats: int) -> SongMini:
    return make_song_mini(name, **stats)


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
            _mini_item(
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


def _curves() -> dict[str, np.ndarray]:
    rows = 161
    return synthetic_curves({
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.4, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64) * 0.333,
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64) * 0.15,
    })


def _song(*, n_notes: int = 400):
    return make_song(
        np.linspace(0, 90, int(n_notes)),
        name="Slice2 base_stats7 equivalence song",
        primary=_PRIMARY_COLOR,
        secondary=_SECONDARY_COLOR,
        long_notes=10,
    )


@pytest.fixture(scope="module")
def real_ga_run():
    """Run the production GPU-native GA once on Vulkan: (selected genome ids, their payload base_stats7, item stats,
    fixed stats)."""
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
    selected_color = _SELECTED_COLOR
    base_fixed_stats_arr = build_stats_array(base_stats_fixed)
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=_PRIMARY_COLOR,
        secondary_color=_SECONDARY_COLOR,
        selected_color=_SELECTED_COLOR,
    )

    song = _song()
    curves = _curves()
    color_flags = build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(song, curves)
        precompute_timeline_gpu(song, curves, song_slot=0, prebuilt_frontier=prebuilt)

        selected_payload = run_gpu_native_ga_runs_payload_prebuilt(
            song=song,
            curves=curves,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=6,
            num_runs=2,
            n_genomes=64,
            color_flags=color_flags,
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

    return cand_rows[:, 3:12], payload_base_stats7, item_stats, base_fixed_stats_arr


def test_payload_base_stats7_matches_host_base_components_on_real_ga(real_ga_run) -> None:
    genomes, payload_base_stats7, item_stats, fixed = real_ga_run
    # At least one row must carry a nonzero base_stats7, or zeros would trivially match.
    assert int(np.count_nonzero(payload_base_stats7)) > 0
    host = [
        response_frontier_base_components_row(
            build_stats_dict(fixed + item_stats[list(ids)].sum(axis=0)), None, primary_color=_PRIMARY_COLOR,
            secondary_color=_SECONDARY_COLOR,
        )
        for ids in genomes.tolist()
    ]
    assert host == [tuple(row) for row in payload_base_stats7.tolist()]
