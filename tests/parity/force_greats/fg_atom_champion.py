from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.solver.scoring.fg_policy import compute_great_penalty_base, is_single_color_song
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _score_response_group_meta_gpu


@dataclass(frozen=True, slots=True)
class ChampionAtom:
    surface_index: int
    g_pp: int
    g_cm: int
    g_fm: int
    g_ov: int


@dataclass(frozen=True, slots=True)
class ChampionProof:
    full_rows: np.ndarray
    restricted_rows: np.ndarray
    atom_rows: np.ndarray
    champion_atoms: tuple[ChampionAtom, ...]
    champion_surfaces: tuple[int, ...]
    restricted_to_full_surface: np.ndarray


def _score_single_frontier_domain(
    *,
    group_meta: np.ndarray,
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_head_coeffs: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict,
) -> np.ndarray:
    rows = np.ascontiguousarray(group_meta, dtype=np.int32)
    group_offsets = np.zeros((int(rows.shape[0]),), dtype=np.int32)
    group_lengths = np.full((int(rows.shape[0]),), int(surface_words.shape[0]), dtype=np.int32)
    scored, _logical_rows = _score_response_group_meta_gpu(
        group_meta=rows,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
        surface_words=np.ascontiguousarray(surface_words, dtype=np.uint32),
        surface_counts=np.ascontiguousarray(surface_counts, dtype=np.int32),
        surface_head_coeffs=np.ascontiguousarray(surface_head_coeffs, dtype=np.int32),
    )
    return np.ascontiguousarray(scored, dtype=np.int32)


def _atom_from_row(row: np.ndarray, *, surface_index: int) -> ChampionAtom:
    return ChampionAtom(
        surface_index=int(surface_index),
        g_pp=int(row[2]),
        g_cm=int(row[3]),
        g_fm=int(row[4]),
        g_ov=int(row[5]),
    )


def _lookup_ref(ref: np.ndarray, idx: int) -> float:
    safe_idx = max(0, min(int(idx), TOTAL_ROWS))
    return float(ref[safe_idx])


def _score_floor(value: float | int) -> int:
    return int(floor(float(value)))


def _bit(word: int, bit_idx: int) -> int:
    return int((int(word) >> int(bit_idx)) & 1)


def _score_surface_atom(
    *,
    words: np.ndarray,
    counts: np.ndarray,
    head_len: int,
    body_total: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    single_color: bool,
) -> int:
    fever_words = tuple(int(v) for v in np.asarray(words[:4], dtype=np.uint32))
    great_words = tuple(int(v) for v in np.asarray(words[4:8], dtype=np.uint32))
    body_fever = int(counts[0])
    body_great = int(counts[1])
    body_fever_great = int(counts[2])
    body_normal = max(0, int(body_total) - int(body_fever))

    base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)
    combo_val = _score_floor(base_value * combo_f)
    fever_val = _score_floor(base_value * combo_f * fever_f)
    score = int(body_fever) * int(fever_val) + int(body_normal) * int(combo_val)

    great_head_base = compute_great_penalty_base(primary_val, secondary_val, single_color=bool(single_color))
    great_base = float(great_head_base)

    if int(body_great) > 0:
        body_normal_great = max(0, int(body_great) - int(body_fever_great))
        body_normal_penalty = max(0, int(combo_val) - _score_floor(great_base * combo_f))
        body_fever_penalty = max(0, int(fever_val) - _score_floor(great_base * combo_f * fever_f))
        score -= int(body_normal_great) * int(body_normal_penalty)
        score -= int(body_fever_great) * int(body_fever_penalty)

    combo_slope = (combo_f - 1.0) / 100.0
    for i in range(max(0, min(int(head_len), 100))):
        word_idx = int(i // 32)
        bit_idx = int(i % 32)
        is_fever = _bit(fever_words[word_idx], bit_idx) != 0
        is_great = _bit(great_words[word_idx], bit_idx) != 0
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_value * scaling
        perfect_val = _score_floor(perfect_value * fever_f) if is_fever else _score_floor(perfect_value)
        if is_great:
            great_value = float(great_head_base) * scaling
            great_score = _score_floor(great_value * fever_f) if is_fever else _score_floor(great_value)
            perfect_val -= max(0, int(perfect_val) - int(great_score))
        score += int(perfect_val)
    return int(score)


def _color_deltas(primary_color: str, secondary_color: str, selected_color: str) -> tuple[bool, tuple[int, ...]]:
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = str(selected_color or "")
    is_primary_pp = int(primary == "Chill")
    is_secondary_pp = int(secondary == "Chill")
    is_primary_cm = int(primary == "Flow")
    is_secondary_cm = int(secondary == "Flow")
    is_primary_fm = int(primary == "Rush")
    is_secondary_fm = int(secondary == "Rush")
    is_primary_ov = int(primary == selected and bool(selected))
    is_secondary_ov = int(secondary == selected and bool(selected))
    allow_pp = bool(is_primary_pp or is_secondary_pp)
    return allow_pp, (
        GEM_STAT_TO_ELEMENT_SCALE * is_primary_pp,
        GEM_STAT_TO_ELEMENT_SCALE * is_secondary_pp,
        GEM_STAT_TO_ELEMENT_SCALE * is_primary_cm,
        GEM_STAT_TO_ELEMENT_SCALE * is_secondary_cm,
        GEM_STAT_TO_ELEMENT_SCALE * is_primary_fm,
        GEM_STAT_TO_ELEMENT_SCALE * is_secondary_fm,
        ELEMENTAL_GEM_SCALE * is_primary_ov,
        ELEMENTAL_GEM_SCALE * is_secondary_ov,
    )


def _max_gems(cur_stat: int, scale: int, residual_budget: int) -> int:
    if int(cur_stat) >= MAX_STAT_INDEX:
        return 0
    rem = int(MAX_STAT_INDEX) - int(cur_stat)
    count = int(rem // int(scale))
    if int(rem % int(scale)) != 0:
        count += 1
    return min(int(count), max(0, int(residual_budget)))


def _valid_atom_for_group(atom: ChampionAtom, row: np.ndarray, *, allow_pp: bool) -> bool:
    residual = int(row[0])
    if min(int(atom.g_pp), int(atom.g_cm), int(atom.g_fm), int(atom.g_ov)) < 0:
        return False
    if int(atom.g_pp) + int(atom.g_cm) + int(atom.g_fm) + int(atom.g_ov) != int(residual):
        return False
    if not bool(allow_pp) and int(atom.g_pp) != 0:
        return False
    max_pp = _max_gems(int(row[1]), GEM_SCALE_NORMAL, residual) if bool(allow_pp) else 0
    max_cm = _max_gems(int(row[2]), GEM_SCALE_NORMAL, residual)
    max_fm = _max_gems(int(row[3]), GEM_SCALE_FEVER, residual)
    return int(atom.g_pp) <= max_pp and int(atom.g_cm) <= max_cm and int(atom.g_fm) <= max_fm


def _score_atom_for_group(
    *,
    atom: ChampionAtom,
    row: np.ndarray,
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> np.ndarray | None:
    allow_pp, deltas = _color_deltas(primary_color, secondary_color, selected_color)
    if not _valid_atom_for_group(atom, row, allow_pp=allow_pp):
        return None
    pp_p_delta, pp_s_delta, cm_p_delta, cm_s_delta, fm_p_delta, fm_s_delta, ov_p_delta, ov_s_delta = deltas
    cur_pp = int(row[1])
    cur_cm = int(row[2])
    cur_fm = int(row[3])
    cur_primary = int(row[4])
    cur_secondary = int(row[5])

    final_pp = int(cur_pp) + int(atom.g_pp) * GEM_SCALE_NORMAL
    final_cm = int(cur_cm) + int(atom.g_cm) * GEM_SCALE_NORMAL
    final_fm = int(cur_fm) + int(atom.g_fm) * GEM_SCALE_FEVER
    final_primary = (
        int(cur_primary)
        + int(atom.g_pp) * int(pp_p_delta)
        + int(atom.g_cm) * int(cm_p_delta)
        + int(atom.g_fm) * int(fm_p_delta)
        + int(atom.g_ov) * int(ov_p_delta)
    )
    final_secondary = (
        int(cur_secondary)
        + int(atom.g_pp) * int(pp_s_delta)
        + int(atom.g_cm) * int(cm_s_delta)
        + int(atom.g_fm) * int(fm_s_delta)
        + int(atom.g_ov) * int(ov_s_delta)
    )
    surface_idx = int(atom.surface_index)
    score = _score_surface_atom(
        words=np.asarray(surface_words[surface_idx], dtype=np.uint32),
        counts=np.asarray(surface_counts[surface_idx], dtype=np.int32),
        head_len=int(row[6]),
        body_total=int(row[7]),
        primary_val=int(final_primary),
        secondary_val=int(final_secondary),
        pp_factor=_lookup_ref(np.asarray(ref_arrays["Perfect Points"], dtype=np.float64), int(final_pp)),
        combo_mul=_lookup_ref(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float64), int(final_cm)),
        fever_mul=_lookup_ref(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float64), int(final_fm)),
        single_color=is_single_color_song(primary_color, secondary_color),
    )
    return np.asarray(
        [
            int(score),
            int(surface_idx),
            int(atom.g_pp),
            int(atom.g_cm),
            int(atom.g_fm),
            int(atom.g_ov),
            int(final_pp),
            int(final_cm),
            int(final_fm),
            int(final_primary),
            int(final_secondary),
        ],
        dtype=np.int32,
    )


def _atom_tie_key(row: np.ndarray) -> tuple[int, int, int, int, int]:
    # Production keeps the first surface on score ties and, within a surface,
    # prefers lower CM, then FM, then PP gem counts.
    return (-int(row[0]), int(row[1]), int(row[3]), int(row[4]), int(row[2]))


def _score_champion_atoms(
    *,
    group_meta: np.ndarray,
    champion_atoms: tuple[ChampionAtom, ...],
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> np.ndarray:
    rows = np.ascontiguousarray(group_meta, dtype=np.int32)
    out = np.zeros((int(rows.shape[0]), 11), dtype=np.int32)
    for group_idx, row in enumerate(rows):
        best: np.ndarray | None = None
        for atom in champion_atoms:
            candidate = _score_atom_for_group(
                atom=atom,
                row=row,
                surface_words=surface_words,
                surface_counts=surface_counts,
                primary_color=primary_color,
                secondary_color=secondary_color,
                selected_color=selected_color,
                ref_arrays=ref_arrays,
            )
            if candidate is None:
                continue
            if best is None or _atom_tie_key(candidate) < _atom_tie_key(best):
                best = candidate
        if best is None:
            raise ValueError("champion atom proof domain has no valid atom for a group")
        out[group_idx] = best
    return out


def prove_single_frontier_champions(
    *,
    group_meta: np.ndarray,
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_head_coeffs: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict,
) -> ChampionProof:
    """Build a non-production champion proof over one declared scorer domain.

    The oracle is the current production inner scorer. The proof first records the
    exact winning atoms over ``group_meta`` and then scores only the projected
    champion surfaces, verifying callers can compare full/restricted rows.
    """

    full_rows = _score_single_frontier_domain(
        group_meta=group_meta,
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=selected_color,
        ref_arrays=ref_arrays,
    )
    atoms = {
        _atom_from_row(row, surface_index=int(row[1]))
        for row in np.asarray(full_rows, dtype=np.int32)
    }
    champion_atoms = tuple(sorted(atoms, key=lambda atom: (atom.surface_index, atom.g_cm, atom.g_fm, atom.g_pp, atom.g_ov)))
    champion_surfaces = tuple(sorted({int(atom.surface_index) for atom in champion_atoms}))
    if not champion_surfaces:
        raise ValueError("champion proof domain produced no winning surfaces")

    restricted_words = np.ascontiguousarray(surface_words[np.asarray(champion_surfaces, dtype=np.int32)], dtype=np.uint32)
    restricted_counts = np.ascontiguousarray(
        surface_counts[np.asarray(champion_surfaces, dtype=np.int32)],
        dtype=np.int32,
    )
    restricted_coeffs = np.ascontiguousarray(
        surface_head_coeffs[np.asarray(champion_surfaces, dtype=np.int32)],
        dtype=np.int32,
    )
    restricted_rows = _score_single_frontier_domain(
        group_meta=group_meta,
        surface_words=restricted_words,
        surface_counts=restricted_counts,
        surface_head_coeffs=restricted_coeffs,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=selected_color,
        ref_arrays=ref_arrays,
    )
    restricted_to_full_surface = np.asarray(
        [champion_surfaces[int(row[1])] for row in np.asarray(restricted_rows, dtype=np.int32)],
        dtype=np.int32,
    )
    atom_rows = _score_champion_atoms(
        group_meta=group_meta,
        champion_atoms=champion_atoms,
        surface_words=np.ascontiguousarray(surface_words, dtype=np.uint32),
        surface_counts=np.ascontiguousarray(surface_counts, dtype=np.int32),
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=selected_color,
        ref_arrays=ref_arrays,
    )
    return ChampionProof(
        full_rows=full_rows,
        restricted_rows=restricted_rows,
        atom_rows=atom_rows,
        champion_atoms=champion_atoms,
        champion_surfaces=champion_surfaces,
        restricted_to_full_surface=restricted_to_full_surface,
    )
