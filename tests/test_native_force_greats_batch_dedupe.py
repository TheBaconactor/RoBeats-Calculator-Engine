from __future__ import annotations

import sys
import types
from typing import Any, Callable

import numpy as np

from gear_optimizer.solver import native_force_greats as nfg


def _install_fake_fg_gpu(
    monkeypatch: Any,
    solver: Callable[..., list[dict[str, Any]]],
    *,
    max_genomes: int = 4096,
) -> None:
    fields_mod = types.ModuleType("gear_optimizer.solver.taichi_gem.fields")
    fields_mod.MAX_GENOMES = int(max_genomes)

    api_mod = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")
    api_mod.solve_force_greats_finder_gpu = solver

    force_greats_pkg = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats")
    force_greats_pkg.__path__ = []  # type: ignore[attr-defined]
    force_greats_pkg.api = api_mod

    taichi_gem_pkg = types.ModuleType("gear_optimizer.solver.taichi_gem")
    taichi_gem_pkg.__path__ = []  # type: ignore[attr-defined]
    taichi_gem_pkg.fields = fields_mod
    taichi_gem_pkg.force_greats = force_greats_pkg

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", taichi_gem_pkg)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.fields", fields_mod)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats", force_greats_pkg)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", api_mod)


def _base_calc_song() -> dict[str, Any]:
    return {
        "metadata": {
            "Primary Color": "Power",
            "Secondary Color": "Rush",
            "Long Notes": 0,
            "Last Note Time": 1.0,
        },
        "song_data": {"timestamps": np.asarray([0.0, 1.0], dtype=np.float64)},
    }


def _stats(*, pp: int = 100) -> dict[str, int]:
    return {
        "Perfect Points": int(pp),
        "Combo Multiplier": 200,
        "Fever Multiplier": 300,
        "Power": 400,
        "Rush": 500,
        "Fever Time": 600,
        "Fever Fill Rate": 700,
    }


def test_native_fg_batch_dedupes_identical_local_gear_responses(monkeypatch: Any) -> None:
    calls: list[np.ndarray] = []
    section_calls: list[dict[str, int]] = []

    def fake_solve_force_greats_finder_gpu(genome_stats: Any, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        rows = np.asarray(genome_stats, dtype=np.int64)
        calls.append(rows.copy())
        out = []
        for row in rows:
            score = 1_000_000 + int(row[0])
            out.append(
                {
                    "cfg_idx": 0,
                    "base_score": score,
                    "final_score": score + 10,
                    "score_penalty": 3,
                    "fill_penalty": 7,
                    "gem_counts": {"Perfect Points": 1},
                    "FT": int(row[5]),
                    "FF": int(row[6]),
                }
            )
        return out

    def fake_section_summary(base_stats: dict[str, int], *_args: Any, **_kwargs: Any) -> tuple[int, int]:
        section_calls.append(dict(base_stats))
        return (2, 3)

    monkeypatch.setattr(nfg, "_section_summary", fake_section_summary)
    _install_fake_fg_gpu(monkeypatch, fake_solve_force_greats_finder_gpu)

    results, stats = nfg.solve_native_force_greats_gpu_batch(
        base_stats_list=[_stats(pp=100), _stats(pp=100), _stats(pp=101)],
        calc_song=_base_calc_song(),
        ref_arrays={},
        selected_colors=["Power", "Power", "Power"],
        center_fts=[0, 0, 0],
        center_ffs=[0, 0, 0],
        search_radius=0,
    )

    assert len(calls) == 1
    assert calls[0].tolist() == [
        [100, 200, 300, 400, 500, 600, 700],
        [101, 200, 300, 400, 500, 600, 700],
    ]
    assert stats == {
        "gpu_batches": 1,
        "groups": 1,
        "input_genomes": 3,
        "unique_genomes": 2,
        "deduped_genomes": 1,
        "dedupe_groups": 1,
        "section_summary_cache_hits": 2,
        "section_summary_cache_misses": 1,
    }
    assert len(section_calls) == 1
    assert results[0] == results[1]
    assert results[0] is not results[1]
    assert results[0] is not None
    assert results[2] is not None
    assert results[0]["final_score"] != results[2]["final_score"]


def test_native_fg_batch_keeps_selected_color_responses_separate(monkeypatch: Any) -> None:
    calls: list[np.ndarray] = []
    section_calls: list[dict[str, int]] = []

    def fake_solve_force_greats_finder_gpu(genome_stats: Any, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        rows = np.asarray(genome_stats, dtype=np.int64)
        calls.append(rows.copy())
        return [
            {
                "cfg_idx": 0,
                "base_score": 1,
                "final_score": 2,
                "score_penalty": 0,
                "fill_penalty": 0,
                "gem_counts": {},
                "FT": int(row[5]),
                "FF": int(row[6]),
            }
            for row in rows
        ]

    def fake_section_summary(base_stats: dict[str, int], *_args: Any, **_kwargs: Any) -> tuple[int, int]:
        section_calls.append(dict(base_stats))
        return (2, 3)

    monkeypatch.setattr(nfg, "_section_summary", fake_section_summary)
    _install_fake_fg_gpu(monkeypatch, fake_solve_force_greats_finder_gpu)

    results, stats = nfg.solve_native_force_greats_gpu_batch(
        base_stats_list=[_stats(pp=100), _stats(pp=100)],
        calc_song=_base_calc_song(),
        ref_arrays={},
        selected_colors=["Power", "Rush"],
        center_fts=[0, 0],
        center_ffs=[0, 0],
        search_radius=0,
    )

    assert len(calls) == 2
    assert all(call.tolist() == [[100, 200, 300, 400, 500, 600, 700]] for call in calls)
    assert stats == {
        "gpu_batches": 2,
        "groups": 2,
        "input_genomes": 2,
        "unique_genomes": 2,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
        "section_summary_cache_hits": 1,
        "section_summary_cache_misses": 1,
    }
    assert len(section_calls) == 1
    assert all(result is not None for result in results)
