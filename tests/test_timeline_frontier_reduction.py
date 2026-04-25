from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _Surface:
    masks: tuple[int, int, int, int]
    body_fever: int
    body_normal: int


def _equal(a: _Surface, b: _Surface) -> bool:
    return a == b


def _dominates(a: _Surface, b: _Surface) -> bool:
    return all((am | bm) == am for am, bm in zip(a.masks, b.masks, strict=True)) and (
        a.body_fever >= b.body_fever and a.body_normal <= b.body_normal
    )


def _reduce_surfaces(surfaces: list[_Surface]) -> list[_Surface]:
    retained: list[_Surface] = []
    for idx, cand in enumerate(surfaces):
        drop = False
        for other_idx, other in enumerate(surfaces):
            if other_idx == idx:
                continue
            if _equal(other, cand):
                drop = other_idx < idx
            elif _dominates(other, cand):
                drop = True
            if drop:
                break
        if not drop:
            retained.append(cand)
    return retained


def _score(surface: _Surface, *, head_len: int, normal: int, fever: int) -> int:
    fever_head = 0
    for note_idx in range(head_len):
        word = note_idx // 32
        bit = note_idx % 32
        fever_head += (surface.masks[word] >> bit) & 1
    normal_head = head_len - fever_head
    return fever * (fever_head + surface.body_fever) + normal * (normal_head + surface.body_normal)


def test_timeline_surface_dominance_reduction_is_lossless_for_positive_score_weights() -> None:
    surfaces = [
        _Surface((0b0001, 0, 0, 0), body_fever=3, body_normal=7),
        _Surface((0b0001, 0, 0, 0), body_fever=3, body_normal=7),  # exact duplicate
        _Surface((0b0011, 0, 0, 0), body_fever=4, body_normal=6),  # dominates the first two
        _Surface((0b0101, 0, 0, 0), body_fever=4, body_normal=6),  # incomparable head mask
        _Surface((0b0111, 0, 0, 0), body_fever=5, body_normal=6),  # dominates both incomparable children
    ]
    retained = _reduce_surfaces(surfaces)

    assert retained == [_Surface((0b0111, 0, 0, 0), body_fever=5, body_normal=6)]

    for normal in range(1, 14):
        for fever in range(normal, normal * 8 + 1):
            before = max(_score(surface, head_len=4, normal=normal, fever=fever) for surface in surfaces)
            after = max(_score(surface, head_len=4, normal=normal, fever=fever) for surface in retained)
            assert after == before


def test_ceiling_envelope_kernels_share_exact_frontier_compactor() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "gear_optimizer"
        / "solver"
        / "taichi_gem"
        / "kernels"
        / "kernels_timeline.py"
    )
    source = source_path.read_text(encoding="utf-8")

    direct_start = source.index("def compute_timeline_grid_ceiling_envelope_kernel")
    reps_start = source.index("def compute_timeline_grid_ceiling_envelope_reps_kernel")
    scatter_start = source.index("def scatter_timeline_grid_ceiling_envelope_from_reps_kernel")

    direct_body = source[direct_start:reps_start]
    reps_body = source[reps_start:scatter_start]

    assert direct_body.count("_write_exact_timeline_frontier4(") == 1
    assert reps_body.count("_write_exact_timeline_frontier4(") == 1
    assert "grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(4, ti.i8)" not in direct_body
    assert "grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(4, ti.i8)" not in reps_body
