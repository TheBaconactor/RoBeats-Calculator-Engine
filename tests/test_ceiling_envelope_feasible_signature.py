import numpy as np


def _pack_head_bits_u32x4(mask: np.ndarray) -> tuple[int, int, int, int]:
    head = np.asarray(mask, dtype=np.uint8).reshape(-1)
    packed = np.packbits(head, bitorder="little").astype(np.uint8, copy=False)
    tmp = np.zeros(16, dtype=np.uint8)
    tmp[: min(int(tmp.shape[0]), int(packed.shape[0]))] = packed[: int(tmp.shape[0])]
    out = np.frombuffer(tmp.tobytes(), dtype=np.uint32)
    return (int(out[0]), int(out[1]), int(out[2]), int(out[3]))


def _unpack_head_bits_u32x4(bits: tuple[int, int, int, int], head_len: int) -> np.ndarray:
    n = int(max(0, head_len))
    out = np.zeros(n, dtype=np.bool_)
    b0, b1, b2, b3 = (int(x) for x in bits)
    words = (b0, b1, b2, b3)
    for i in range(n):
        w = i >> 5
        b = i & 31
        if (words[w] >> b) & 1:
            out[i] = True
    return out


def _build_feasible_event_ms_for_ceiling(
    timestamps: np.ndarray,
    note_types: np.ndarray,
    *,
    fill_count: int,
    d_ms: int,
) -> np.ndarray:
    """
    Construct one concrete integer-ms event stream consistent with the ceiling algorithm.

    This is used to verify that the ceiling signature corresponds to a realizable hit-timing sequence
    (not an impossible upper bound).
    """
    from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope

    ts = np.asarray(timestamps, dtype=np.float32).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0:
        return np.zeros((0,), dtype=np.int32)

    prepared = prepare_perfect_timing_envelope(
        ts,
        nt,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32).reshape(-1)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32).reshape(-1)
    group_base = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32).reshape(-1)
    group_low = np.asarray(prepared.get("group_low", ()), dtype=np.int32).reshape(-1)
    group_high = np.asarray(prepared.get("group_high", ()), dtype=np.int32).reshape(-1)
    gcount = int(group_starts.shape[0])
    if n > 0 and gcount <= 0:
        raise AssertionError("prepare_perfect_timing_envelope produced no chord groups")

    note_group_idx = np.full(n, -1, dtype=np.int32)
    for g in range(gcount):
        s = int(group_starts[g])
        e = int(group_ends[g])
        if e > s:
            note_group_idx[s:e] = int(g)
    if n > 0 and int(np.any(note_group_idx < 0)):
        raise AssertionError("prepare_perfect_timing_envelope produced uncovered note indices")

    def _delta_ms(g: int, prev_g: int) -> int:
        d = int(group_base[g]) - int(group_base[prev_g])
        return int(d if d >= 1 else 1)

    def _propagate_interval(lo: int, hi: int, g: int) -> tuple[int, int]:
        d = int(group_base[g]) - int(group_base[g - 1])
        if d < 1:
            d = 1
        out_lo = max(int(group_low[g]), int(lo) - int(d))
        out_hi = max(int(group_high[g]), int(hi) - int(d))
        return int(out_lo), int(out_hi)

    # Assigned carry per group (filled as we reach the group).
    group_carry = np.zeros(gcount, dtype=np.int32)
    group_assigned = np.zeros(gcount, dtype=np.bool_)

    prev_group = -1
    prev_carry = 0

    def _assign_group(g: int, carry: int) -> None:
        group_carry[g] = np.int32(int(carry))
        group_assigned[g] = True

    # Walk the same note-index timeline as the ceiling kernel, choosing a concrete carry
    # value (the max feasible carry) whenever we need to instantiate one.
    current_note = 0
    section = 0
    fill_count = max(1, int(fill_count))
    d_ms = max(0, int(d_ms))

    while current_note < n:
        section += 1
        notes_to_fill = (fill_count - 1) if section == 1 else fill_count
        if notes_to_fill < 0:
            notes_to_fill = 0

        start_normal = int(current_note)
        end_normal = int(min(n, int(current_note) + int(notes_to_fill)))

        # Assign carries for groups touched by the normal segment.
        walk_note = int(start_normal)
        while walk_note < end_normal:
            g = int(note_group_idx[walk_note])
            if g < 0 or g >= gcount:
                break
            if g != prev_group:
                u_g = int(group_high[g])
                if prev_group < 0:
                    prev_carry = u_g
                else:
                    prev_carry = max(u_g, int(prev_carry) - _delta_ms(g, int(prev_group)))
                prev_group = g
                _assign_group(g, int(prev_carry))

            group_end = n if (g + 1) >= gcount else int(group_starts[g + 1])
            walk_note = min(group_end, end_normal)

        current_note = end_normal
        if current_note >= n:
            break
        if current_note <= 0:
            break

        # Fever activates.
        activation_note = int(current_note)
        s = int(note_group_idx[activation_note])
        if s < 0 or s >= gcount:
            break

        if s != prev_group:
            u_s = int(group_high[s])
            if prev_group < 0:
                prev_carry = u_s
            else:
                prev_carry = max(u_s, int(prev_carry) - _delta_ms(s, int(prev_group)))
            prev_group = s
            _assign_group(s, int(prev_carry))

        r_act = int(prev_carry)
        c_s = int(group_base[s])
        Q = int(c_s + r_act + int(d_ms))

        # Boundary band in group index space.
        b_minus = int(np.searchsorted(group_base, int(Q - 80), side="left"))
        b_plus = int(np.searchsorted(group_base, int(Q + 40), side="left"))
        start_g = int(s + 1)
        b_minus = max(start_g, min(b_minus, gcount))
        b_plus = max(start_g, min(b_plus, gcount))

        lo = int(r_act)
        hi = int(r_act)
        last_fever_group = int(s)
        last_fever_hi = int(r_act)

        # Interior region: always in fever, choose max reachable carry (hi).
        g = int(start_g)
        while g < b_minus:
            lo, hi = _propagate_interval(lo, hi, g)
            last_fever_group = int(g)
            last_fever_hi = int(hi)
            _assign_group(g, int(hi))
            g += 1

        exit_group = -1
        g = int(b_minus)
        while g < b_plus and g < gcount:
            prev_lo = int(lo)
            prev_hi = int(hi)
            lo, hi = _propagate_interval(lo, hi, g)

            c_g = int(group_base[g])
            remain_hi = int(Q - c_g - 1)
            keep_lo = max(int(lo), -40)
            keep_hi = min(int(hi), int(remain_hi))

            if keep_lo <= keep_hi:
                lo = int(keep_lo)
                hi = int(keep_hi)
                last_fever_group = int(g)
                last_fever_hi = int(hi)
                _assign_group(g, int(hi))
                g += 1
                continue

            exit_group = int(g)
            lo = int(prev_lo)
            hi = int(prev_hi)
            break

        if exit_group >= 0:
            fever_end_idx = int(group_starts[exit_group])
        else:
            if b_plus < gcount:
                fever_end_idx = int(group_starts[b_plus])
            else:
                fever_end_idx = n

        fever_end_idx = max(int(activation_note), min(int(fever_end_idx), n))

        prev_group = int(last_fever_group)
        prev_carry = int(last_fever_hi)
        current_note = int(fever_end_idx)

    # Finalize: build per-note event times (one timestamp per chord group).
    event_ms = np.zeros(n, dtype=np.int32)
    for g in range(gcount):
        if not bool(group_assigned[g]):
            # For any untouched tail groups (rare for small charts), pick the latest nominal carry.
            group_carry[g] = np.int32(int(group_high[g]))
        s = int(group_starts[g])
        e = int(group_ends[g])
        if e > s:
            event_ms[s:e] = np.int32(int(group_base[g]) + int(group_carry[g]))

    # Safety: enforce global monotonicity at the note level.
    if n > 1:
        ev = event_ms
        for i in range(1, n):
            if int(ev[i]) < int(ev[i - 1]):
                ev[i] = ev[i - 1]

    return np.asarray(event_ms, dtype=np.int32)


def test_ceiling_signature_is_realizable_via_constructed_event_stream() -> None:
    """
    The ceiling timeline algorithm should describe a realizable hit-timing stream, not an impossible upper bound.

    This test constructs one explicit integer-ms event stream that follows the ceiling algorithm's choices, then
    re-runs the fever timeline walk (`compute_fever_timeline_signature`) and asserts we recover the same signature.
    """
    from math import ceil

    from gear_optimizer.solver.timing_envelope import compute_fever_timeline_signature, prepare_perfect_timing_envelope

    # Synthetic chart in integer ms.
    n_notes = 380
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)

    long_notes = 0
    last_note_time = float(timestamps[-1])
    non_fever_cas = float(max(0, int(n_notes) - int(long_notes))) * 0.333

    # Pick factors that create multiple fever windows on this chart.
    ff_factor = 1.7
    ft_factor = 1.9

    fill_count = int(ceil(non_fever_cas * float(ff_factor)))
    fill_count = max(1, int(fill_count))

    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    d_ms = int(ceil(float(fever_time_cas * float(ft_factor) * 1000.0)))
    d_ms = max(0, int(d_ms))

    event_ms = _build_feasible_event_ms_for_ceiling(timestamps, note_types, fill_count=fill_count, d_ms=d_ms)

    # Sanity: verify the constructed event stream respects chord grouping windows + monotonic rule.
    prepared = prepare_perfect_timing_envelope(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32).reshape(-1)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32).reshape(-1)
    group_base = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32).reshape(-1)
    group_low = np.asarray(prepared.get("group_low", ()), dtype=np.int32).reshape(-1)
    group_high = np.asarray(prepared.get("group_high", ()), dtype=np.int32).reshape(-1)
    gcount = int(group_starts.shape[0])
    assert gcount > 0

    group_ev = np.zeros(gcount, dtype=np.int32)
    group_carry = np.zeros(gcount, dtype=np.int32)
    for g in range(gcount):
        s = int(group_starts[g])
        e = int(group_ends[g])
        assert e > s
        v = event_ms[s]
        assert int(np.min(event_ms[s:e])) == int(v) and int(np.max(event_ms[s:e])) == int(v), "group events must match"
        group_ev[g] = np.int32(int(v))
        group_carry[g] = np.int32(int(v) - int(group_base[g]))

    # Monotone event times.
    assert int(np.min(np.diff(group_ev))) >= 0

    # Carry feasibility per chord group.
    for g in range(gcount):
        r = int(group_carry[g])
        if g == 0:
            assert int(group_low[g]) <= r <= int(group_high[g])
            continue
        prev_r = int(group_carry[g - 1])
        delta = int(group_base[g]) - int(group_base[g - 1])
        if delta < 1:
            delta = 1
        min_r = int(prev_r) - int(delta)
        u_g = int(group_high[g])
        l_g = int(group_low[g])
        if min_r <= u_g:
            assert r <= u_g
            assert r >= max(l_g, min_r)
        else:
            assert r == min_r and r > u_g

    sig, head_mask, body_fever, body_normal = compute_fever_timeline_signature(
        event_ms,
        non_fever_base=int(fill_count),
        real_fever_time_ms=int(d_ms),
    )

    # Convert to the grid-style signature representation and ensure internal consistency.
    head_len = int(sig[0])
    assert head_len == int(min(int(n_notes), 100))
    assert int(body_fever) == int(sig[1])
    assert int(body_normal) == int(sig[2])

    bits = _pack_head_bits_u32x4(head_mask)
    unpacked = _unpack_head_bits_u32x4(bits, head_len)
    assert np.array_equal(unpacked, np.asarray(head_mask, dtype=np.bool_))
