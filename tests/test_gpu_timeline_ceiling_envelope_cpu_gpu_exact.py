import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


def _compare_proxy_score(
    head_bits: tuple[int, int, int, int],
    body_fever: int,
    body_normal: int,
    *,
    head_len: int,
) -> int:
    base_f = np.float32(10000.0)
    combo_mul_f = np.float32(2.6)
    fever_mul_f = np.float32(5.25)

    combo_val_per_note = int(base_f * combo_mul_f)
    fever_val_per_note = int(base_f * combo_mul_f * fever_mul_f)
    body_score = (int(body_fever) * int(fever_val_per_note)) + (int(body_normal) * int(combo_val_per_note))

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    total_head = 0
    for i in range(int(head_len)):
        current_ramp_val = base_f + (np.float32(i + 1) * factor)
        w = int(i) >> 5
        b = int(i) & 31
        is_fever = (int(head_bits[w]) >> int(b)) & 1
        if is_fever:
            total_head += int(current_ramp_val * fever_mul_f)
        else:
            total_head += int(current_ramp_val)
    return int(body_score + int(total_head))


def _cpu_ceiling_sig_for_cell(
    chart_timestamps: np.ndarray,
    note_types: np.ndarray,
    *,
    long_notes: int,
    last_note_time: float,
    ff_factor: float,
    ft_factor: float,
) -> tuple[int, tuple[int, int, int, int], int, int, int, int]:
    """
    CPU reference implementation of `compute_timeline_grid_ceiling_envelope_kernel` for one (FT, FF) cell.

    Returns a signature tuple:
      (head_len, head_bits_u32x4, body_fever, body_normal, fever_activations, gap)
    """
    from math import ceil

    from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope

    ts = np.asarray(chart_timestamps, dtype=np.float32).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int16).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0:
        return (0, (0, 0, 0, 0), 0, 0, 0, 0)

    non_fever_cas = float(max(0, n - int(long_notes))) * 0.333
    fill_count = int(ceil(non_fever_cas * float(ff_factor)))
    fill_count = max(1, int(fill_count))

    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    d_ms = int(ceil(float(fever_time_cas * float(ft_factor) * 1000.0)))
    d_ms = max(0, int(d_ms))

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

    MAX_HEAD = 100
    head_len = int(min(n, MAX_HEAD))

    def _delta_ms_to(prev_g: int, g: int) -> int:
        d = int(group_base[g]) - int(group_base[prev_g])
        return int(d if d >= 1 else 1)

    def _propagate_interval(lo: int, hi: int, g: int) -> tuple[int, int]:
        d = int(group_base[g]) - int(group_base[g - 1])
        if d < 1:
            d = 1
        out_lo = max(int(group_low[g]), int(lo) - int(d))
        out_hi = max(int(group_high[g]), int(hi) - int(d))
        return int(out_lo), int(out_hi)

    def _simulate(*, pick_high: bool, end_mode: int) -> tuple[int, tuple[int, int, int, int], int, int, int, int]:
        m = [0, 0, 0, 0]  # uint32 bits as Python ints
        body_fever = 0
        body_normal = 0
        fever_activations = 0
        last_fever_end_idx = 0

        current_note = 0
        fever_section = 0

        prev_group = -1
        prev_carry = 0

        def _anchor(g: int) -> int:
            return int(group_high[g]) if pick_high else int(group_low[g])

        def _or_head_mask_range(start: int, end: int) -> None:
            s = max(0, int(start))
            e = min(int(end), int(head_len))
            for i in range(s, e):
                w = i >> 5
                b = i & 31
                m[w] |= 1 << b

        while current_note < n:
            fever_section += 1
            notes_to_fill = (fill_count - 1) if fever_section == 1 else fill_count
            if notes_to_fill < 0:
                notes_to_fill = 0

            start_normal_idx = int(current_note)
            end_normal_idx = int(min(n, int(current_note) + int(notes_to_fill)))

            body_normal_start = max(int(current_note), MAX_HEAD)
            if end_normal_idx > body_normal_start:
                body_normal += int(end_normal_idx - body_normal_start)

            walk_note = int(start_normal_idx)
            while walk_note < end_normal_idx:
                g = int(note_group_idx[walk_note])
                if g < 0:
                    g = 0
                if g >= gcount:
                    break

                if g != prev_group:
                    anchor = _anchor(int(g))
                    if prev_group < 0:
                        prev_carry = anchor
                    else:
                        prev_carry = max(anchor, int(prev_carry) - _delta_ms_to(int(prev_group), int(g)))
                    prev_group = g

                group_end = n if (g + 1) >= gcount else int(group_starts[g + 1])
                walk_note = min(int(group_end), int(end_normal_idx))

            current_note = int(end_normal_idx)
            if current_note >= n:
                break

            if current_note <= 0:
                break

            fever_activations += 1
            activation_note = int(current_note)
            if activation_note >= n:
                break

            s = int(note_group_idx[activation_note])
            if s < 0:
                s = 0
            if s >= gcount:
                break

            if s != prev_group:
                anchor = _anchor(int(s))
                if prev_group < 0:
                    prev_carry = anchor
                else:
                    prev_carry = max(anchor, int(prev_carry) - _delta_ms_to(int(prev_group), int(s)))
                prev_group = s

            r_act = int(prev_carry)
            c_s = int(group_base[s])
            Q = int(c_s + r_act + int(d_ms))

            b_minus = int(np.searchsorted(group_base, int(Q - 80), side="left"))
            b_plus = int(np.searchsorted(group_base, int(Q + 40), side="left"))

            start_g = int(s + 1)
            b_minus = max(start_g, min(b_minus, gcount))
            b_plus = max(start_g, min(b_plus, gcount))

            if int(end_mode) != 0:
                # End fever as early as possible: first reachable out-group in the swing band.
                lo = int(r_act)
                hi = int(r_act)

                g = int(start_g)
                while g < b_minus:
                    lo, hi = _propagate_interval(lo, hi, g)
                    g += 1

                out_group = -1
                out_carry = 0

                g = int(b_minus)
                while g < b_plus and g < gcount:
                    lo, hi = _propagate_interval(lo, hi, g)

                    c_g = int(group_base[g])
                    out_threshold = int(Q - c_g)
                    if int(hi) >= int(out_threshold):
                        out_group = int(g)
                        out_carry = max(int(lo), int(out_threshold))
                        break

                    remain_hi = int(out_threshold - 1)
                    lo = max(int(lo), -40)
                    hi = min(int(hi), int(remain_hi))
                    g += 1

                if out_group >= 0:
                    fever_end_idx = int(group_starts[out_group])
                else:
                    if b_plus < gcount:
                        out_group = int(b_plus)
                        out_lo, _out_hi = _propagate_interval(lo, hi, out_group)
                        out_carry = int(out_lo)
                        fever_end_idx = int(group_starts[out_group])
                    else:
                        fever_end_idx = n

                fever_end_idx = max(int(activation_note), min(int(fever_end_idx), n))

                _or_head_mask_range(int(activation_note), int(fever_end_idx))

                body_fever_start = max(int(activation_note), MAX_HEAD)
                if fever_end_idx > body_fever_start:
                    body_fever += int(fever_end_idx - body_fever_start)

                if 0 <= int(out_group) < int(gcount):
                    prev_group = int(out_group)
                    prev_carry = int(out_carry)
                else:
                    prev_group = int(s)
                    prev_carry = int(r_act)

                last_fever_end_idx = int(fever_end_idx)
                current_note = int(fever_end_idx)
                continue

            lo = int(r_act)
            hi = int(r_act)
            last_fever_group = int(s)
            last_fever_hi = int(r_act)

            g = int(start_g)
            while g < b_minus:
                lo, hi = _propagate_interval(lo, hi, g)
                last_fever_group = int(g)
                last_fever_hi = int(hi)
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
                    g = int(b_plus)
                    _ = _propagate_interval(lo, hi, g)  # One-step propagate to the always-out group (debug parity).
                    fever_end_idx = int(group_starts[g])
                else:
                    fever_end_idx = n

            fever_end_idx = max(int(activation_note), min(int(fever_end_idx), n))

            _or_head_mask_range(int(activation_note), int(fever_end_idx))

            body_fever_start = max(int(activation_note), MAX_HEAD)
            if fever_end_idx > body_fever_start:
                body_fever += int(fever_end_idx - body_fever_start)

            prev_group = int(last_fever_group)
            prev_carry = int(last_fever_hi)
            last_fever_end_idx = int(fever_end_idx)
            current_note = int(fever_end_idx)

        body_normal_start = max(int(current_note), MAX_HEAD)
        if n > body_normal_start:
            body_normal += int(n - body_normal_start)

        gap = int(n - int(last_fever_end_idx))
        head_bits = tuple(int(x & 0xFFFFFFFF) for x in m)  # type: ignore[assignment]
        return (int(head_len), head_bits, int(body_fever), int(body_normal), int(fever_activations), int(gap))

    candidates = [
        _simulate(pick_high=True, end_mode=0),
        _simulate(pick_high=True, end_mode=1),
        _simulate(pick_high=False, end_mode=0),
        _simulate(pick_high=False, end_mode=1),
    ]

    best = None
    best_key = None
    for sig in candidates:
        score = int(_compare_proxy_score(sig[1], sig[2], sig[3], head_len=sig[0]))
        bits = tuple(int(x) for x in sig[1])
        key = (score, int(sig[2]), int(bits[3]), int(bits[2]), int(bits[1]), int(bits[0]))
        if best_key is None or key > best_key:
            best_key = key
            best = sig

    assert best is not None
    return best


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ceiling_timeline_matches_cpu_reference(monkeypatch) -> None:
    """
    Ensure the Taichi ceiling kernel matches a CPU reference implementation on a synthetic chart.

    This is the main regression guard for ceiling-mode correctness: CPU and GPU must produce
    identical per-cell signatures (mask bits, counts, gap, activations).
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    # Integer-ms chart to avoid float boundary issues.
    n_notes = 420
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)  # held tails widen carry window

    calc_song = {
        "metadata": {
            "Song Name": "CeilingEnvelope CPU/GPU Exact",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(n_notes),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.2, 2.2, rows, dtype=np.float32),
        "Fever Time": np.linspace(0.8, 2.6, rows, dtype=np.float32),
    }

    cells = [(10, 10), (80, 80), (160, 40), (120, 30)]

    monkeypatch.setenv("GPU_TIMELINE_CEILING_ENVELOPE", "1")
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy()[0], dtype=np.int32)
    gap_grid = np.asarray(gpu_fields.grid_gap.to_numpy()[0], dtype=np.int32)
    act_grid = np.asarray(gpu_fields.grid_fever_activations.to_numpy()[0], dtype=np.int32)

    long_notes = int(calc_song["metadata"].get("Long Notes", 0) or 0)
    last_note_time = float(calc_song["metadata"].get("Last Note Time", 0.0) or 0.0)

    for ft_idx, ff_idx in cells:
        ft_factor = float(ref_arrays["Fever Time"][ft_idx])
        ff_factor = float(ref_arrays["Fever Fill Rate"][ff_idx])

        cpu_sig = _cpu_ceiling_sig_for_cell(
            timestamps,
            note_types,
            long_notes=long_notes,
            last_note_time=last_note_time,
            ff_factor=ff_factor,
            ft_factor=ft_factor,
        )

        head_len = int(head_len_grid[ft_idx, ff_idx])
        bits = tuple(int(x) for x in bits_grid[ft_idx, ff_idx, :].tolist())
        body_fever = int(body_fever_grid[ft_idx, ff_idx])
        body_normal = int(body_normal_grid[ft_idx, ff_idx])
        gap = int(gap_grid[ft_idx, ff_idx])
        acts = int(act_grid[ft_idx, ff_idx])
        gpu_sig = (head_len, bits, body_fever, body_normal, acts, gap)

        assert gpu_sig == cpu_sig, (
            f"CPU/GPU ceiling mismatch for cell (ft={ft_idx},ff={ff_idx}): cpu={cpu_sig} gpu={gpu_sig}"
        )


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ceiling_timeline_dedup_matches_baseline(monkeypatch) -> None:
    """
    Ensure deduplicated ceiling-grid execution produces identical grid outputs.

    This guards the optimization that computes only unique (fill_count, d_ms) cells and
    scatters representative results across the full 161×161 grid.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    n_notes = 420
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)

    calc_song = {
        "metadata": {
            "Song Name": "CeilingEnvelope Dedup Parity",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(n_notes),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        # Force maximal deduplication: all cells share one (fill_count, d_ms) pair.
        "Fever Fill Rate": np.full((rows,), 1.0, dtype=np.float32),
        "Fever Time": np.full((rows,), 1.0, dtype=np.float32),
    }

    monkeypatch.setenv("GPU_TIMELINE_CEILING_ENVELOPE", "1")

    monkeypatch.setenv("GPU_TIMELINE_CEILING_DEDUP", "0")
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    monkeypatch.setenv("GPU_TIMELINE_CEILING_DEDUP", "1")
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=1)

    def _eq(field) -> bool:
        arr = field.to_numpy()
        return bool(np.array_equal(arr[0], arr[1]))

    assert _eq(gpu_fields.grid_head_len)
    assert _eq(gpu_fields.grid_fever_masks_bits)
    assert _eq(gpu_fields.grid_count_body_fever)
    assert _eq(gpu_fields.grid_count_body_normal)
    assert _eq(gpu_fields.grid_gap)
    assert _eq(gpu_fields.grid_fever_activations)
    assert _eq(gpu_fields.grid_sig0)
    assert _eq(gpu_fields.grid_sig1)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ceiling_exact_frontier_beats_heuristic_on_bounded_cell(monkeypatch) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.timeline_exact_dp import solve_timeline_signature_exact_scoremax

    init_taichi()

    n_notes = 120
    gap_ms = 24
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)
    note_types[::17] = np.int16(3)

    def _calc_song(max_windows: int) -> dict:
        return {
            "metadata": {
                "Song Name": "Base Exact Frontier Production",
                "Difficulty": "Hard",
                "Primary Color": "Beat",
                "Secondary Color": "Flow",
                "Long Notes": 0,
                "Last Note Time": float(timestamps[-1]),
                "Total Notes": int(n_notes),
                "TimelineAnalysisMaxWindows": int(max_windows),
            },
            "song_data": {
                "timestamps": timestamps,
                "chart_timestamps": timestamps,
                "note_types": note_types,
            },
        }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        "Perfect Points": np.full((rows,), 100.0, dtype=np.float32),
        "Combo Multiplier": np.full((rows,), 2.6, dtype=np.float32),
        "Fever Multiplier": np.full((rows,), 5.25, dtype=np.float32),
        "Fever Fill Rate": np.full((rows,), 1.0, dtype=np.float32),
        "Fever Time": np.full((rows,), 0.8, dtype=np.float32),
    }

    heuristic_sig = _cpu_ceiling_sig_for_cell(
        timestamps,
        note_types,
        long_notes=0,
        last_note_time=float(timestamps[-1]),
        ff_factor=1.0,
        ft_factor=0.8,
    )
    exact_sig = solve_timeline_signature_exact_scoremax(
        timestamps,
        note_types,
        long_notes=0,
        last_note_time=float(timestamps[-1]),
        ff_factor=1.0,
        ft_factor=0.8,
        base_value=10000.0,
        combo_mul=2.6,
        fever_mul=5.25,
    )

    heuristic_score = _compare_proxy_score(heuristic_sig[1], heuristic_sig[2], heuristic_sig[3], head_len=heuristic_sig[0])
    exact_score = _compare_proxy_score(
        exact_sig.head_bits,
        exact_sig.body_fever,
        exact_sig.body_normal,
        head_len=exact_sig.head_len,
    )
    assert exact_score - heuristic_score >= 159120

    monkeypatch.setenv("GPU_TIMELINE_CEILING_ENVELOPE", "1")
    monkeypatch.setenv("GPU_TIMELINE_EXACT_OVERRIDES", "1")

    precompute_timeline_gpu(_calc_song(0), ref_arrays, song_slot=0)
    precompute_timeline_gpu(_calc_song(3), ref_arrays, song_slot=1)

    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy(), dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy(), dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy(), dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy(), dtype=np.int32)

    slot0_sig = (
        int(head_len_grid[0, 0, 0]),
        tuple(int(x) for x in bits_grid[0, 0, 0]),
        int(body_fever_grid[0, 0, 0]),
        int(body_normal_grid[0, 0, 0]),
    )
    slot1_sig = (
        int(head_len_grid[1, 0, 0]),
        tuple(int(x) for x in bits_grid[1, 0, 0]),
        int(body_fever_grid[1, 0, 0]),
        int(body_normal_grid[1, 0, 0]),
    )

    assert slot0_sig == heuristic_sig[:4]
    assert slot1_sig == (
        int(exact_sig.head_len),
        tuple(int(x) for x in exact_sig.head_bits),
        int(exact_sig.body_fever),
        int(exact_sig.body_normal),
    )
