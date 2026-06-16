"""Issue #42 isolation mock: can a single early hit pull ONE note into fever,
with activation fixed at 0ms and every other note at perfect 0ms?

Server-order rule modeled: for each note the server corrects event time from the
hit offset, then is_fever := (activation_event <= event_time < activation_event + D).
Fever start/end are anchored to the ACTIVATION note's event time, so moving a later
boundary note does NOT move the window — only that note's own membership can change.
"""
from __future__ import annotations

FEVER_MULT = 2.0
COMBO_MULT = 1.0
BASE = 1000.0  # per-note base value (flat; head scaling omitted for clarity)


def replay(chart_ms, offsets_ms, activation_idx, D):
    """Return (event_ms, fever_flags, score) under the server-order fever rule."""
    ev = [int(c) + int(o) for c, o in zip(chart_ms, offsets_ms)]
    # monotonic hit order is a real constraint; assert we never reorder
    for i in range(1, len(ev)):
        assert ev[i] >= ev[i - 1], f"hit order violated at {i}: {ev}"
    fever_start = ev[activation_idx]
    fever_end = fever_start + int(D)
    flags, score = [], 0.0
    for i, e in enumerate(ev):
        is_fever = (i >= activation_idx) and (fever_start <= e < fever_end)
        flags.append(is_fever)
        score += BASE * (FEVER_MULT if is_fever else COMBO_MULT)
    return ev, flags, score, fever_start, fever_end


def main() -> int:
    # Activation at chart 200 (index 2). D = 1000 -> fever window [200, 1200).
    # Boundary note sits at chart 1210, i.e. 10ms AFTER the fever end.
    chart = [0, 100, 200, 400, 600, 800, 1000, 1210, 1400, 1600]
    activation_idx = 2
    D = 1000
    boundary_idx = 7  # chart 1210

    zeros = [0] * len(chart)

    # --- Scenario A: perfect play, everything at 0ms -------------------------
    evA, fA, sA, fs, fe = replay(chart, zeros, activation_idx, D)

    # --- Scenario B: identical, but the single boundary note hit -20ms early --
    offB = list(zeros)
    offB[boundary_idx] = -20
    evB, fB, sB, fsB, feB = replay(chart, offB, activation_idx, D)

    print(f"fever window (event-time anchored): [{fs}, {fe})   D={D}")
    print(f"activation note idx={activation_idx} chart={chart[activation_idx]} "
          f"-> event {evA[activation_idx]} (UNCHANGED in B: {evB[activation_idx]})")
    print(f"window in A == window in B? {(fs, fe) == (fsB, feB)}  "
          f"<- activation/fever end did not move\n")

    print("idx  chart   A:off A:event A:fever | B:off B:event B:fever")
    for i in range(len(chart)):
        print(f"{i:>3} {chart[i]:>6} {0:>6} {evA[i]:>7} {str(fA[i]):>7} |"
              f" {offB[i]:>5} {evB[i]:>7} {str(fB[i]):>7}"
              f"{'   <-- the only change' if i == boundary_idx else ''}")

    print(f"\nfever notes  A={sum(fA)}  B={sum(fB)}   (delta {sum(fB) - sum(fA):+d})")
    print(f"score        A={sA:,.0f}  B={sB:,.0f}   (delta {sB - sA:+,.0f})")
    gained = (not fA[boundary_idx]) and fB[boundary_idx]
    print(f"\n=> single -20ms early hit pulled the boundary note INTO fever: {gained}")

    # --- Controls: where does the early hit actually matter? -----------------
    print("\n--- sweep: place ONE isolated note at chart c, hit it -20ms early ---")
    print("    (fever end = 1200; predict inclusion iff 1200 <= c < 1220)")
    for c in (1100, 1199, 1200, 1205, 1219, 1220, 1240):
        # event at 0ms:
        in_at_0 = fs <= c < fe
        # event at -20ms:
        in_at_m20 = fs <= (c - 20) < fe
        flips = (not in_at_0) and in_at_m20
        print(f"  c={c:>5}: 0ms in-fever={in_at_0!s:>5}  "
              f"-20ms in-fever={in_at_m20!s:>5}  flips_in={flips}")

    # --- Negative controls ---------------------------------------------------
    print("\n--- negative controls (early hit changes nothing) ---")
    for idx, label in ((4, "deep inside fever (chart 600)"),
                       (8, "far past fever (chart 1400)")):
        off = list(zeros)
        off[idx] = -20
        _, f, s, _, _ = replay(chart, off, activation_idx, D)
        print(f"  early-hit {label}: score delta {s - sA:+,.0f}, "
              f"fever-count delta {sum(f) - sum(fA):+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
