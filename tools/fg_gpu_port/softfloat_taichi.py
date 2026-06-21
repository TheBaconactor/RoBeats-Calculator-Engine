"""Taichi i64 soft-float64 + FG inner scorer (macOS/MoltenVK-exact, Task A.2 Approach A).

Mirrors tools/fg_gpu_port/fg_exact_ref.py (the CPU-validated blueprint) using only
ti.i64 integer ops, so it compiles+runs under ti.vulkan -> MoltenVK (no f64, no i64
atomics needed). A soft-float is a 2-vector [mantissa, exponent]; value = m * 2**e.
ti.func args are unannotated (inlined; types flow from call sites) because taichi 1.7.4
rejects ti.i64 arg annotations.  Run `default_ip=ti.i64` so int literals are 64-bit.

Validate:
    python tools/fg_gpu_port/softfloat_taichi.py cpu      # fast, no GPU, no prod contention
    python tools/fg_gpu_port/softfloat_taichi.py vulkan   # single parity run on the Mac GPU
"""
import os
import sys

import numpy as np
import taichi as ti

MASK52 = (1 << 52) - 1
IMPL = 1 << 52
TWO53 = 1 << 53

vec2 = ti.types.vector(2, ti.i64)


@ti.func
def bitlen(x):
    n = ti.i64(0)
    v = x
    if v >= (ti.i64(1) << 32):
        n += 32; v >>= 32
    if v >= (ti.i64(1) << 16):
        n += 16; v >>= 16
    if v >= (ti.i64(1) << 8):
        n += 8; v >>= 8
    if v >= (ti.i64(1) << 4):
        n += 4; v >>= 4
    if v >= (ti.i64(1) << 2):
        n += 2; v >>= 2
    if v >= (ti.i64(1) << 1):
        n += 1; v >>= 1
    out = ti.i64(0)
    if x > 0:
        out = n + 1
    return out


@ti.func
def rde(q, rbit, sticky):
    out = q
    if rbit != 0 and (sticky != 0 or (q & 1) != 0):
        out = q + 1
    return out


@ti.func
def sf_decode(bits):
    E = (bits >> 52) & 0x7FF
    m = (bits & ti.i64(MASK52)) | ti.i64(IMPL)
    return vec2(m, E - 1075)


@ti.func
def sf_mul_small(n, b):
    """n (small non-negative int) * b (normalized 53-bit f64) -> normalized f64."""
    res = vec2(0, 0)
    if n != 0:
        bm = b[0]
        bl = bm & ti.i64(0xFFFFFFFF)
        bh = bm >> 32
        plow = ti.i64(n) * bl
        lo32 = plow & ti.i64(0xFFFFFFFF)
        carry = plow >> 32
        hi = ti.i64(n) * bh + carry
        nb = bitlen(hi) + 32
        M = ti.i64(0)
        sh = ti.i64(0)
        if nb <= 53:
            M = (hi << 32) | lo32
            sh = ti.i64(0)
        else:
            drop = nb - 53
            Mtop = (hi << (32 - drop)) | (lo32 >> drop)
            rbit = (lo32 >> (drop - 1)) & 1
            sticky = lo32 & ((ti.i64(1) << (drop - 1)) - 1)
            M = rde(Mtop, rbit, sticky)
            sh = drop
        if M >= ti.i64(TWO53):
            M >>= 1
            sh += 1
        res = vec2(M, b[1] + sh)
    return res


@ti.func
def sf_mul_full(a, b):
    """a * b, both normalized 53-bit -> normalized 53-bit (product is 105 or 106 bits)."""
    am = a[0]
    bm = b[0]
    a0 = am & 0xFFFF; a1 = (am >> 16) & 0xFFFF; a2 = (am >> 32) & 0xFFFF; a3 = (am >> 48) & 0xFFFF
    b0 = bm & 0xFFFF; b1 = (bm >> 16) & 0xFFFF; b2 = (bm >> 32) & 0xFFFF; b3 = (bm >> 48) & 0xFFFF
    r0 = a0 * b0
    r1 = a0 * b1 + a1 * b0
    r2 = a0 * b2 + a1 * b1 + a2 * b0
    r3 = a0 * b3 + a1 * b2 + a2 * b1 + a3 * b0
    r4 = a1 * b3 + a2 * b2 + a3 * b1
    r5 = a2 * b3 + a3 * b2
    r6 = a3 * b3
    r1 += r0 >> 16; r0 &= 0xFFFF
    r2 += r1 >> 16; r1 &= 0xFFFF
    r3 += r2 >> 16; r2 &= 0xFFFF
    r4 += r3 >> 16; r3 &= 0xFFFF
    r5 += r4 >> 16; r4 &= 0xFFFF
    r6 += r5 >> 16; r5 &= 0xFFFF
    plo = r0 | (r1 << 16) | (r2 << 32) | ((r3 & 0x1F) << 48)
    phi = (r3 >> 5) | (r4 << 11) | (r5 << 27) | (r6 << 43)
    M = ti.i64(0)
    sh = ti.i64(0)
    if phi >= ti.i64(IMPL):
        rbit = (plo >> 52) & 1
        sticky = plo & ((ti.i64(1) << 52) - 1)
        M = rde(phi, rbit, sticky)
        sh = ti.i64(53)
    else:
        M = (phi << 1) | (plo >> 52)
        rbit = (plo >> 51) & 1
        sticky = plo & ((ti.i64(1) << 51) - 1)
        M = rde(M, rbit, sticky)
        sh = ti.i64(52)
    if M >= ti.i64(TWO53):
        M >>= 1
        sh += 1
    return vec2(M, a[1] + b[1] + sh)


@ti.func
def sf_add(a, b):
    e = ti.min(a[1], b[1])
    s = (a[0] << (a[1] - e)) + (b[0] << (b[1] - e))
    nb = bitlen(s)
    res = vec2(0, 0)
    if nb <= 53:
        res = vec2(s << (53 - nb), e - (53 - nb))
    else:
        drop = nb - 53
        Mtop = s >> drop
        rbit = (s >> (drop - 1)) & 1
        sticky = s & ((ti.i64(1) << (drop - 1)) - 1)
        M = rde(Mtop, rbit, sticky)
        if M >= ti.i64(TWO53):
            M >>= 1
            drop += 1
        res = vec2(M, e + drop)
    return res


@ti.func
def sf_floor(a):
    m = a[0]
    e = a[1]
    out = ti.i64(0)
    if m != 0:
        if e >= 0:
            out = m << e
        else:
            out = m >> (-e)
    return out


@ti.func
def word_bit(w0, w1, w2, w3, i):
    wi = i >> 5
    bi = i & 31
    w = w0
    if wi == 1:
        w = w1
    elif wi == 2:
        w = w2
    elif wi == 3:
        w = w3
    return (w >> bi) & 1


@ti.func
def head_score(base_int, cs, fm, note_idx, is_fever):
    one = vec2(ti.i64(IMPL), -52)
    scaling = sf_add(sf_mul_small(note_idx + 1, cs), one)
    bs = sf_mul_small(base_int, scaling)
    out = sf_floor(bs)
    if is_fever != 0:
        out = sf_floor(sf_mul_full(bs, fm))
    return out


@ti.func
def score_device(f0, f1, f2, f3, g0, g1, g2, g3,
                 body_fever, body_great, body_fever_great, head_len, body_total,
                 primary, secondary, pp, cm, fm, cs, is_single):
    base_int = ti.i64(primary) * 2 + secondary + pp
    base_cm = sf_mul_small(base_int, cm)
    combo_val = sf_floor(base_cm)
    fever_val = sf_floor(sf_mul_full(base_cm, fm))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = ti.i64(body_fever) * fever_val + ti.i64(body_normal) * combo_val
    for i in range(head_len):
        score += head_score(base_int, cs, fm, i, word_bit(f0, f1, f2, f3, i))
    great_bits = g0 | g1 | g2 | g3
    if body_great > 0 or great_bits != 0:
        great_head_base = ti.i64(0)
        if is_single != 0:
            great_head_base = ti.i64(primary) * 2 + 150
        else:
            great_head_base = (sf_floor(sf_mul_small(primary, sf_decode(ti.i64(0x3FF5555555555555))))
                               + sf_floor(sf_mul_small(secondary, sf_decode(ti.i64(0x3FE5555555555555))))
                               + 150)
        gb_cm = sf_mul_small(great_head_base, cm)
        great_combo_val = sf_floor(gb_cm)
        great_fever_val = sf_floor(sf_mul_full(gb_cm, fm))
        if body_great > 0:
            bng = body_great - body_fever_great
            if bng < 0:
                bng = 0
            bnp = combo_val - great_combo_val
            if bnp < 0:
                bnp = 0
            bfp = fever_val - great_fever_val
            if bfp < 0:
                bfp = 0
            score -= ti.i64(bng) * bnp
            score -= ti.i64(body_fever_great) * bfp
        if great_bits != 0:
            for i in range(head_len):
                if word_bit(g0, g1, g2, g3, i) != 0:
                    isf = word_bit(f0, f1, f2, f3, i)
                    pen = head_score(base_int, cs, fm, i, isf) - head_score(great_head_base, cs, fm, i, isf)
                    if pen > 0:
                        score -= pen
    return score


@ti.func
def surface_ub(base_int, cm, fm, cs, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf):
    """Integer OVER-ESTIMATE of the score (>= true score), used only for `ub > best_score`
    pruning, mirroring _fg_response_surface_upper_bound (f64). The body term is exact (same
    soft-float floors as the scorer); the head term uses integer ceilings of cm/fm so it is
    provably >= the real head bound and cannot overflow (cs is unused — kept for call compat).
    base_int is an integer (pp_factor is integer)."""
    base_cm = sf_mul_small(base_int, cm)
    combo_val = sf_floor(base_cm)
    fever_val = sf_floor(sf_mul_full(base_cm, fm))
    body_score = ti.i64(body_fever) * fever_val + ti.i64(body_normal) * combo_val
    fm_ceil = sf_floor(fm) + 1          # >= fever_mul
    cm_ceil = sf_floor(cm) + 1          # >= combo_mul
    # head_upper <= base*(n_hn + fm_ceil*n_hf) + base*(cm_ceil-1)/100*(sigma_hn + fm_ceil*sigma_hf)
    head1 = ti.i64(base_int) * (n_hn + fm_ceil * n_hf)
    factor_term = ti.i64(base_int) * (cm_ceil - 1) * (sigma_hn + fm_ceil * sigma_hf) // 100 + 1
    return body_score + head1 + factor_term + 1024


@ti.kernel
def score_batch(meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
                fever: ti.types.ndarray(dtype=ti.i64, ndim=2),
                great: ti.types.ndarray(dtype=ti.i64, ndim=2),
                cmb: ti.types.ndarray(dtype=ti.i64, ndim=1),
                fmb: ti.types.ndarray(dtype=ti.i64, ndim=1),
                csb: ti.types.ndarray(dtype=ti.i64, ndim=1),
                out: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    for t in range(meta.shape[0]):
        cm = sf_decode(cmb[t])
        fm = sf_decode(fmb[t])
        cs = sf_decode(csb[t])
        s = score_device(
            fever[t, 0], fever[t, 1], fever[t, 2], fever[t, 3],
            great[t, 0], great[t, 1], great[t, 2], great[t, 3],
            meta[t, 4], meta[t, 5], meta[t, 6], meta[t, 7], meta[t, 8],
            meta[t, 0], meta[t, 1], meta[t, 2], cm, fm, cs, meta[t, 3],
        )
        out[t] = ti.cast(s, ti.i32)


def _run(arch_name, n):
    sys.path.insert(0, os.path.dirname(__file__))
    import fg_exact_ref as ref

    arch = {"cpu": ti.cpu, "vulkan": ti.vulkan}[arch_name]
    ti.init(arch=arch, default_ip=ti.i64)
    rng = np.random.default_rng(99)
    meta = np.zeros((n, 9), np.int32)
    fever = np.zeros((n, 4), np.int64)
    great = np.zeros((n, 4), np.int64)
    cmb = np.zeros(n, np.int64); fmb = np.zeros(n, np.int64); csb = np.zeros(n, np.int64)
    expected = np.zeros(n, np.int64)
    for t in range(n):
        head_len = int(rng.integers(0, 129))
        fw = [int(rng.integers(0, 1 << 32, dtype=np.uint64)) for _ in range(4)]
        gw = [int(rng.integers(0, 1 << 32, dtype=np.uint64)) for _ in range(4)]
        bt = int(rng.integers(0, 900)); bf = int(rng.integers(0, bt + 1))
        bg = int(rng.integers(0, bt + 1)); bfg = int(rng.integers(0, bg + 1))
        pri = int(rng.integers(0, 330)); sec = int(rng.integers(0, 330)); pp = int(rng.integers(200, 486))
        combo = float(rng.uniform(2.0, 2.67)); fever_m = float(rng.uniform(3.0, 5.425))
        isc = int(rng.integers(0, 2))
        meta[t] = [pri, sec, pp, isc, bf, bg, bfg, head_len, bt]
        fever[t] = fw; great[t] = gw
        cmb[t] = int(np.float64(combo).view(np.uint64).astype(np.int64))
        fmb[t] = int(np.float64(fever_m).view(np.uint64).astype(np.int64))
        csb[t] = int(np.float64((combo - 1.0) / 100.0).view(np.uint64).astype(np.int64))
        expected[t] = ref.score_device_i(fw, gw, bf, bg, bfg, head_len, bt, pri, sec, pp,
                                         int(np.uint64(cmb[t])), int(np.uint64(fmb[t])),
                                         int(np.uint64(csb[t])), isc)
    out = np.zeros(n, np.int32)
    score_batch(meta, fever, great, cmb, fmb, csb, out)
    ti.sync()
    bad = int(np.sum(out.astype(np.int64) != expected))
    print(f"[{arch_name}] {n - bad}/{n} bit-exact vs CPU reference")
    if bad:
        idx = np.where(out.astype(np.int64) != expected)[0][:5]
        for i in idx:
            print("  mismatch t=", int(i), "got", int(out[i]), "exp", int(expected[i]),
                  "meta", meta[i].tolist())
    print("ALL OK" if bad == 0 else "FAILURES")
    return bad


if __name__ == "__main__":
    arch = sys.argv[1] if len(sys.argv) > 1 else "cpu"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    _run(arch, count)
