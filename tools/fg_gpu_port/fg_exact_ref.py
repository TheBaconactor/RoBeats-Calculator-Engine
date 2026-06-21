"""Validated reference for the macOS-exact GPU FG scorer (Task A.2, "Approach A").

Goal: reproduce the f64 force-greats inner scorer
(`gear_optimizer/solver/taichi_gem/force_greats/response_inner_kernels.py`,
`_fg_response_score_device` / `_fg_response_head_score`) **bit-for-bit** using only
integer arithmetic, so it can run on macOS/MoltenVK where the GPU has no f64
(`shaderFloat64`).

Key facts that make this tractable (verified 2026-06-21):
  * `base_value = primary*2 + secondary + pp_factor` is an EXACT INTEGER
    (Perfect Points are integers 200..485; primary/secondary are integers).
  * The only non-integers are Combo (2.0..2.67) and Fever (3.0..5.425), which are
    arbitrary f64 curve values from `ref_arrays`.
  * The kernel score is `floor(int_base * f64_combo [* f64_fever])` plus head/great
    terms that are the same shape.
  * This Mac's MoltenVK supports i64 *arithmetic* (mul / shift / floor-div); only
    i64 *atomics* are rejected. The kernel accumulates the score in i32, so i64 is
    needed only for intermediate products.

Strategy ("soft-float64"): pass every f64 multiplier to the GPU as its raw IEEE-754
bits, decode to (mantissa53, exponent) integers, and emulate IEEE round-to-nearest-even
multiply / add in integer arithmetic, then floor by an exact shift. Restricted to
POSITIVE NORMAL doubles (the only kind that occur here), which removes sign / inf /
nan / subnormal handling.

`combo_slope = (combo_mul - 1.0)/100.0` is precomputed on the HOST in f64 (bit-identical
to an in-kernel f64 divide) and passed to the kernel as bits, so the kernel needs only
multiply + add — no division emulation.

Validated against a native-float transcription of the same kernel logic over millions of
randomized inputs (see tests/test_fg_exact_softfloat_parity.py): 0 mismatches.

NOTE: the int functions here are the exact blueprint for the Taichi kernel. The one piece
the GPU adds is a 53x53 -> 106-bit product (Python ints are unbounded; on i64 use two
limbs with <=27-bit splits so partials stay < 2**54 < 2**63). See the design record
docs/Implementation Records/ZERO_MS_EXACT_GPU_FG_PLAN.md.
"""
from __future__ import annotations

import math

MASK52 = (1 << 52) - 1
IMPL = 1 << 52

# IEEE-754 bit patterns of the constants the kernel uses.
ONE = (1 << 52, -52)            # 1.0
BITS_4_3 = 0x3FF5555555555555    # fl(4.0/3.0)
BITS_2_3 = 0x3FE5555555555555    # fl(2.0/3.0)


# ---- soft-float64 (positive normals only), integer-exact vs IEEE doubles ----
def round_half_even(val: int, drop: int) -> int:
    if drop <= 0:
        return val
    q = val >> drop
    rem = val & ((1 << drop) - 1)
    half = 1 << (drop - 1)
    if rem > half or (rem == half and (q & 1)):
        q += 1
    return q


def norm53(val: int, e: int):
    if val == 0:
        return (0, 0)
    nb = val.bit_length()
    if nb > 53:
        drop = nb - 53
        val = round_half_even(val, drop)
        e += drop
        if val >> 53:          # carry into a 54th bit (val == 2**53)
            val >>= 1
            e += 1
    elif nb < 53:
        val <<= (53 - nb)
        e -= (53 - nb)
    return (val, e)


def decode_bits(bits: int):
    """Raw IEEE-754 double bits (positive normal) -> (m, e), value = m * 2**e."""
    E = (bits >> 52) & 0x7FF
    return ((bits & MASK52) | IMPL, E - 1075)


def fval(n: int):
    """A non-negative integer as a soft-float value (consumers normalize)."""
    return (n, 0)


def fmul(a, b):
    return norm53(a[0] * b[0], a[1] + b[1])


def fadd(a, b):
    e = a[1] if a[1] < b[1] else b[1]
    return norm53((a[0] << (a[1] - e)) + (b[0] << (b[1] - e)), e)


def ffloor(a) -> int:
    m, e = a
    return (m << e) if e >= 0 else (m >> (-e))


# ---- integer port of the FG inner scorer (the GPU kernel blueprint) ----
def head_score_i(base_int: int, combo_slope_v, fever_v, note_idx: int, is_fever: int) -> int:
    scaling = fadd(fmul(combo_slope_v, fval(note_idx + 1)), ONE)
    bs = fmul(fval(base_int), scaling)
    if is_fever != 0:
        return ffloor(fmul(bs, fever_v))
    return ffloor(bs)


def score_device_i(fw, gw, body_fever, body_great, body_fever_great, head_len, body_total,
                   primary_val, secondary_val, pp_factor_int, combo_bits, fever_bits,
                   combo_slope_bits, is_single_color) -> int:
    """Integer-exact reproduction of `_fg_response_score_device`.

    combo_slope_bits = IEEE bits of (combo_mul - 1.0)/100.0, precomputed on the host.
    """
    cm = decode_bits(combo_bits)
    fm = decode_bits(fever_bits)
    cs = decode_bits(combo_slope_bits)
    base_int = (primary_val * 2) + secondary_val + pp_factor_int
    base_cm = fmul(fval(base_int), cm)
    combo_val = ffloor(base_cm)
    fever_val = ffloor(fmul(base_cm, fm))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val

    def bit(words, i):
        return (words[i // 32] >> (i % 32)) & 1

    for i in range(head_len):
        score += head_score_i(base_int, cs, fm, i, bit(fw, i))

    great_bits = gw[0] | gw[1] | gw[2] | gw[3]
    if body_great > 0 or great_bits != 0:
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (ffloor(fmul(fval(primary_val), decode_bits(BITS_4_3)))
                               + ffloor(fmul(fval(secondary_val), decode_bits(BITS_2_3))) + 150)
        gb_cm = fmul(fval(great_head_base), cm)
        great_combo_val = ffloor(gb_cm)
        great_fever_val = ffloor(fmul(gb_cm, fm))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            bnp = combo_val - great_combo_val
            if bnp < 0:
                bnp = 0
            bfp = fever_val - great_fever_val
            if bfp < 0:
                bfp = 0
            score -= body_normal_great * bnp
            score -= body_fever_great * bfp
        if great_bits != 0:
            for i in range(head_len):
                if bit(gw, i) != 0:
                    isf = bit(fw, i)
                    pen = head_score_i(base_int, cs, fm, i, isf) - head_score_i(great_head_base, cs, fm, i, isf)
                    if pen > 0:
                        score -= pen
    return score


# ---- native-float twin (mirrors the CURRENT f64 kernel; used only for parity tests) ----
def head_score_f(base_value, combo_slope, fever_mul, note_idx, is_fever):
    scaling = combo_slope * float(note_idx + 1) + 1.0
    if is_fever != 0:
        return int(math.floor(base_value * scaling * fever_mul))
    return int(math.floor(base_value * scaling))


def score_device_f(fw, gw, body_fever, body_great, body_fever_great, head_len, body_total,
                   primary_val, secondary_val, pp_factor, combo_mul, fever_mul, is_single_color):
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = math.floor(base_value * combo_mul)
    fever_val = math.floor(base_value * combo_mul * fever_mul)
    body_normal = max(0, body_total - body_fever)
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0

    def bit(words, i):
        return (words[i // 32] >> (i % 32)) & 1

    for i in range(head_len):
        score += head_score_f(base_value, combo_slope, fever_mul, i, bit(fw, i))
    great_bits = gw[0] | gw[1] | gw[2] | gw[3]
    if body_great > 0 or great_bits != 0:
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (math.floor(primary_val * (4.0 / 3.0))
                               + math.floor(secondary_val * (2.0 / 3.0)) + 150)
        great_base = float(great_head_base)
        great_combo_val = math.floor(great_base * combo_mul)
        great_fever_val = math.floor(great_base * combo_mul * fever_mul)
        if body_great > 0:
            body_normal_great = max(0, body_great - body_fever_great)
            score -= body_normal_great * max(0, combo_val - great_combo_val)
            score -= body_fever_great * max(0, fever_val - great_fever_val)
        if great_bits != 0:
            for i in range(head_len):
                if bit(gw, i) != 0:
                    isf = bit(fw, i)
                    pen = head_score_f(base_value, combo_slope, fever_mul, i, isf) - \
                        head_score_f(great_base, combo_slope, fever_mul, i, isf)
                    if pen > 0:
                        score -= pen
    return int(score)
