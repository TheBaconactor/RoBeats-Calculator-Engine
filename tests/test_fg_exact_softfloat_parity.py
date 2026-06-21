"""Parity oracle for the macOS-exact GPU FG scorer (Task A.2, Approach A).

Proves the integer soft-float reproduction of the f64 FG inner scorer is bit-for-bit
identical to a native-float transcription of the same kernel logic. This is the
regression gate the eventual Taichi i64 kernel must also pass.

CPU-only (no GPU), so it runs in the normal `-m "not gpu"` sweep. During development the
primitive checks were run to 2,000,000 samples and the full-scorer check to 300,000 with
0 mismatches; the counts here are trimmed for suite speed.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "fg_gpu_port"))
import fg_exact_ref as ref  # noqa: E402


def _bits(x):
    return int(np.float64(x).view(np.uint64))


def test_constants_match_ieee():
    assert ref.BITS_4_3 == _bits(4.0 / 3.0)
    assert ref.BITS_2_3 == _bits(2.0 / 3.0)
    assert ref.ONE == ref.decode_bits(_bits(1.0))


def test_softfloat_primitives_bit_exact():
    rng = np.random.default_rng(1)
    n = 50_000
    xs = rng.uniform(2.0, 5.5, n)
    ys = rng.uniform(1.0, 1100.0, n)
    for i in range(n):
        x = float(xs[i]); y = float(ys[i])
        # fmul(f64,f64)
        got = ref.fmul(ref.decode_bits(_bits(x)), ref.decode_bits(_bits(y)))
        # compare value, not bits, by reconstructing the float exactly
        assert float(got[0]) * (2.0 ** got[1]) == x * y
        # fmul(int, f64) and floor compositions
        B = int(ys[i])
        bc = ref.fmul(ref.fval(B), ref.decode_bits(_bits(x)))
        assert ref.ffloor(bc) == int(np.floor(np.float64(B) * x))
        f = float(rng.uniform(3.0, 5.425))
        assert ref.ffloor(ref.fmul(bc, ref.decode_bits(_bits(f)))) == int(
            np.floor((np.float64(B) * x) * f)
        )


def test_fadd_one_bit_exact():
    rng = np.random.default_rng(2)
    for _ in range(50_000):
        x = float(rng.uniform(0.0, 6.0))
        got = ref.fadd(ref.decode_bits(_bits(x)), ref.ONE)
        assert _encode(got) == _bits(x + 1.0)


def _encode(a):
    m, e = a
    E = e + 1075
    return ((E & 0x7FF) << 52) | (m & ref.MASK52)


def test_full_scorer_int_matches_float():
    rng = np.random.default_rng(7)
    n = 20_000
    mismatches = 0
    for _ in range(n):
        head_len = int(rng.integers(0, 129))
        fw = [int(rng.integers(0, 1 << 32, dtype=np.uint64)) for _ in range(4)]
        gw = [int(rng.integers(0, 1 << 32, dtype=np.uint64)) for _ in range(4)]
        body_total = int(rng.integers(0, 900))
        body_fever = int(rng.integers(0, body_total + 1))
        body_great = int(rng.integers(0, body_total + 1))
        body_fever_great = int(rng.integers(0, body_great + 1))
        primary = int(rng.integers(0, 330))
        secondary = int(rng.integers(0, 330))
        pp = int(rng.integers(200, 486))
        combo = float(rng.uniform(2.0, 2.67))
        fever = float(rng.uniform(3.0, 5.425))
        isc = int(rng.integers(0, 2))
        a = ref.score_device_f(fw, gw, body_fever, body_great, body_fever_great, head_len,
                               body_total, primary, secondary, float(pp), combo, fever, isc)
        slope_bits = _bits((combo - 1.0) / 100.0)
        b = ref.score_device_i(fw, gw, body_fever, body_great, body_fever_great, head_len,
                               body_total, primary, secondary, pp, _bits(combo), _bits(fever),
                               slope_bits, isc)
        if a != b:
            mismatches += 1
    assert mismatches == 0, f"{mismatches}/{n} scorer mismatches"
