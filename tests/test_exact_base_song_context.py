from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver import exact_base_song_context as song_context


_GRID = 161


def _singleton_timeline_payload() -> SimpleNamespace:
    return SimpleNamespace(
        grid_frontier_count=np.ones((1, _GRID, _GRID), dtype=np.int32),
        grid_frontier_offset=np.zeros((1, _GRID, _GRID), dtype=np.int32),
        grid_frontier_body_fever_pool=np.zeros((1, 1), dtype=np.int32),
        grid_frontier_body_normal_pool=np.ones((1, 1), dtype=np.int32),
        grid_frontier_masks_bits_pool=np.zeros((1, 1, 4), dtype=np.uint32),
        grid_frontier_head_coeffs_pool=np.zeros((1, 1, 4), dtype=np.int32),
        grid_head_len=np.zeros((1, _GRID, _GRID), dtype=np.int32),
        frontier_pool_used=1,
    )


def _response_table_with_equivalent_rows() -> SimpleNamespace:
    return SimpleNamespace(
        cells=np.asarray([0, 1, 2], dtype=np.int32),
        offsets_by_row=np.asarray([0, 2, 5], dtype=np.int32),
        lengths_by_row=np.asarray([2, 3, 1], dtype=np.int32),
        flat_ft=np.asarray([0, 1, 1, 0, 0, 0], dtype=np.int32),
        flat_ff=np.zeros(6, dtype=np.int32),
    )


def _all_array_fields(instance: object) -> list[np.ndarray]:
    return [
        value
        for field in fields(instance)
        if isinstance(value := getattr(instance, field.name), np.ndarray)
    ]


def test_timing_program_classes_canonicalize_order_and_duplicates() -> None:
    response_table = _response_table_with_equivalent_rows()
    classes, class_count = song_context._timing_program_classes(
        response_table=response_table,
        cell_pack=np.zeros((_GRID, _GRID), dtype=np.int32),
        flags=song_context._validated_color_flags({}),
    )

    assert classes.tolist() == [0, 0, 1]
    assert class_count == 2


def test_program_class_bounds_preserve_physical_program_equivalence() -> None:
    response_table = _response_table_with_equivalent_rows()
    flags = song_context._validated_color_flags({})
    classes, _class_count = song_context._timing_program_classes(
        response_table=response_table,
        cell_pack=np.zeros((_GRID, _GRID), dtype=np.int32),
        flags=flags,
    )
    physical = song_context._timing_bound_programs(
        calc_song={"metadata": {"Total Notes": 1}},
        flags=flags,
        response_table=response_table,
        timeline=song_context._timeline_arrays(_singleton_timeline_payload()),
    )
    class_programs = song_context._program_class_bound_programs(classes, physical)

    assert physical.surface_offsets.tolist() == [0, 2, 4, 5]
    assert class_programs.program_offsets.tolist() == [0, 2, 3]
    assert class_programs.program_budget.tolist() == [89, 90, 90]
    assert np.all(
        class_programs.program_body_fever
        + class_programs.program_body_normal
        + class_programs.program_head_normal
        + class_programs.program_head_fever
        == 1
    )
    assert all(not array.flags.writeable for array in _all_array_fields(physical))
    assert all(not array.flags.writeable for array in _all_array_fields(class_programs))


def test_program_class_bounds_reject_false_equivalence() -> None:
    zeros = np.zeros(2, dtype=np.int32)
    physical = song_context.TimingBoundPrograms(
        surface_offsets=np.asarray([0, 1, 2], dtype=np.int32),
        surface_budget=np.asarray([90, 89], dtype=np.int16),
        surface_direct=zeros,
        surface_body_fever=zeros,
        surface_body_normal=np.ones(2, dtype=np.int32),
        surface_head_normal=zeros,
        surface_head_fever=zeros,
        surface_sigma_normal=zeros,
        surface_sigma_fever=zeros,
    )

    with pytest.raises(RuntimeError, match="disagree on physical score programs"):
        song_context._program_class_bound_programs(
            np.asarray([0, 0], dtype=np.int32),
            physical,
        )


def test_joint_multiplier_bound_spends_each_gem_once() -> None:
    ref_cm = np.asarray([1, 1, 10, 10, 10, 10, 10], dtype=np.float64)
    ref_fm = np.asarray([1, 1, 1, 20, 20, 20, 20], dtype=np.float64)

    bound = song_context._build_cm_fm_joint_multiplier_bound(ref_cm, ref_fm, 2)

    assert bound[0, 0, 1] == 20
    assert bound[0, 0, 2] == 200


def test_public_builder_uses_supplied_payload_and_returns_readonly_arrays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(song_context, "TOTAL_GEM_BUDGET", 0)

    def _unexpected_cache_reload(**_kwargs: object) -> None:
        raise AssertionError("song context must not reload the timeline frontier")

    monkeypatch.setattr(
        song_context.timing_response_antichain,
        "build_timing_response_antichain_table",
        _unexpected_cache_reload,
    )
    references = np.ones(_GRID, dtype=np.float32)
    inputs = song_context.ExactBaseSongContextInputs(
        calc_song={"metadata": {"Total Notes": 1}},
        ref_arrays={
            "Perfect Points": references,
            "Combo Multiplier": references,
            "Fever Multiplier": references,
        },
        color_flags={},
    )

    result = song_context.build_exact_base_song_context(
        inputs,
        _singleton_timeline_payload(),
    )

    assert result.program_map.program_count == 1
    assert result.program_map.program_by_cell.shape == (_GRID * _GRID,)
    assert result.class_programs.program_offsets.tolist() == [0, 1]
    assert result.multiplier_bounds.joint_cm_fm.shape == (_GRID, _GRID, 1)
    containers = (
        result.program_map,
        result.physical_programs,
        result.class_programs,
        result.multiplier_bounds,
    )
    assert all(
        not array.flags.writeable
        for container in containers
        for array in _all_array_fields(container)
    )
