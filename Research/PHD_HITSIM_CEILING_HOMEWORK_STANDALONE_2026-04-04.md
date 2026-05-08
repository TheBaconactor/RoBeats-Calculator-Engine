# Standalone Homework Package: Analytical HitSim Ceiling Timeline vs Monte Carlo and Exact Interval DP

This is a self-contained research handoff for the Analytical HitSim ceiling timeline model used in RoBeats MetaFinder.
It includes the exact mechanics, constants, and concrete counterexamples needed for independent research without repository access.

## Snapshot metadata

- Project: RoBeats MetaFinder
- Git branch: codex/verdict-research-validation-20260403
- Git HEAD: 688c453
- Date: 2026-04-04
- Hardware profile assumed by the production system: AMD Ryzen 8840HS CPU, AMD Radeon RX 7900 XTX GPU, Taichi Vulkan backend

## Scope of this document

The only phenomenon modeled here is fever boundary sensitivity to Perfect-window hit timing jitter under a monotone integer-millisecond event time rule.
The only way timing affects the objective is by moving notes in or out of fever at window boundaries and cascading that shift to later windows.

## Constants and domains

- Time quantization unit: integer milliseconds
- Head region length for scoring: 100 notes
- Perfect timing window for regular notes: [-20, +40] ms
- Held-tail note type identifier: 3
- Held-tail timing window multiplier: 2
- Therefore the global feasible carry domain is [-40, +80] ms

## Timestamp quantization

Chart timestamps are float seconds but are treated as integer milliseconds after quantization.
Quantization uses float32-first math and snaps values close to an integer boundary within 0.1ms before flooring.

Definition in Python form:

```python
ms = float32(timestamps_sec) * 1000
rounded = rint(ms)
snapped = where(abs(ms-rounded) <= 0.1, rounded, floor(ms))
ts_ms = int32(snapped)
```

## Chord groups and per-group Perfect windows

Notes are partitioned into chord groups by their quantized chart time ts_ms.
All notes in a chord group share one event time and therefore one offset.

For each note i with type nt_i, define its Perfect offset window in ms as:
- If nt_i != 3 then delta_i is in [-20, +40]
- If nt_i == 3 then delta_i is in [-40, +80]

For a chord group g with note index set I_g, the feasible shared offset window is the intersection:
- group_low_g = max over i in I_g of lower_i
- group_high_g = min over i in I_g of upper_i

The group base time is group_base_t_ms_g = ts_ms at the first note of the group.

## Feasible event time streams and the carry model

Let the realized event time for group g be e_g in integer ms.
Define carry r_g = e_g - group_base_t_ms_g in integer ms.

Carry feasibility constraints:
- r_g is in [group_low_g, group_high_g]
- Event times are monotone: e_g >= e_{g-1}

With delta_g = group_base_t_ms_g - group_base_t_ms_{g-1} and delta_g >= 1, the carry transition is:
- If r_{g-1} - delta_g <= group_high_g then r_g is in [max(group_low_g, r_{g-1} - delta_g), group_high_g]
- Else r_g = r_{g-1} - delta_g

Interval propagation identity used by both the GPU ceiling kernel and the exact DP reference solver:
If the feasible carries at group g-1 form an interval [p, q], then the feasible carries at group g form an interval
T_g([p, q]) = [max(group_low_g, p - delta_g), max(group_high_g, q - delta_g)].

## Fever mechanics reduced to two integers per cell

For a song with N total notes and L long notes, define
- non_fever_cas = (N - L) * 0.333
- fever_time_cas = last_note_time_sec * 0.15 + 0.15

For each Fever Fill Rate factor FF and Fever Time factor FT, the cell parameters are
- raw_fill = non_fever_cas * FF
- fill_count = ceil(raw_fill) with a minimum of 1
- fever_duration_sec = fever_time_cas * FT
- d_ms = ceil(fever_duration_sec * 1000) with a minimum of 0

These two integers fill_count and d_ms are sufficient to define the boundary-flip timing problem for a fixed chart and fixed per-note weights.

## Fever timeline walk on an event time stream

The fever timeline is constructed by an index walk that alternates non-fever fill segments and fever windows.
Let current_note be the next note index to process.

For fever section number s starting at 1:
- notes_to_fill = fill_count - 1 for s = 1 and notes_to_fill = fill_count for s >= 2
- activation_note = current_note + notes_to_fill
- fever_start_ms = event_ms at activation_note
- fever_end_ms = fever_start_ms + real_fever_time_ms
- fever_end_idx = lower_bound(event_ms, fever_end_ms) using side left
- Notes in [activation_note, fever_end_idx) are fever notes
- Set current_note = fever_end_idx and continue

The cascade dependency is that fever_end_idx determines the next activation_note.

## Score function and score proxy

A fever timeline is summarized by a signature consisting of head fever bits and body counts, and that signature is score-complete for fixed scoring multipliers.

Score-relevant signature fields:
- head_len = min(N, 100)
- head_bits_u32x4 = 128 bits storing fever membership for note indices 0..head_len-1 in little-endian bit order
- body_fever = count of fever notes with index >= 100
- body_normal = count of non-fever notes with index >= 100
- fever_activations = number of fever windows activated
- gap = N - last_fever_end_idx where last_fever_end_idx is the end index of the final fever window

The score proxy used in the ceiling kernel selection logic fixes constants
- base = 10000.0
- combo_mul = 2.6
- fever_mul = 5.25

Score computation matches fast_calculate_score with float32-first semantics:
- Body normal per note value is int(base * combo_mul)
- Body fever per note value is int(base * combo_mul * fever_mul)
- Head note i in [0, head_len) has ramp value base + (i+1) * (combo_mul - 1) * base / 100 computed in float32 and then truncated to int
- Fever multiplies the ramp before truncation

The scoreproxy objective can be written as maximizing sum of nonnegative per-note fever bonuses w_i where
- w_i is body_bonus for i >= 100
- w_i is int(ramp_i * fever_mul) - int(ramp_i) for i < 100

## Monte Carlo HitSim baseline

Monte Carlo sampling generates a feasible event_ms stream by sampling a carry in each chord group uniformly from the feasible integer window after applying monotonicity.
Sampling rule for each group g with base time base_t and window [group_low, group_high]:
- required_off = prev_event_ms - base_t
- eff_low = max(group_low, required_off)
- If eff_low <= group_high then sample off uniformly from integers in [eff_low, group_high]
- Else set off = group_high and if base_t + off < prev_event_ms then set off = prev_event_ms - base_t
- Set event_ms for all notes in the group to base_t + off and continue

For a fixed cell the MC-best-of-S value is the maximum scoreproxy score across seeds 1..S.

## Production GPU ceiling kernel

The production Analytical HitSim ceiling mode computes a full 161 by 161 grid of signatures per song on the GPU.
It evaluates four fully-feasible greedy variants and selects the best by the deterministic score proxy plus fixed tie-breakers.

Variant dimensions:
- normal-hi vs normal-lo selects how a concrete carry is instantiated during non-fever fill segments
  - normal-hi uses group_high as the per-group anchor
  - normal-lo uses group_low as the per-group anchor
- fever-max vs fever-min selects how fever end is chosen inside the swing band
  - fever-max keeps swing groups in fever as long as feasible
  - fever-min ends fever at the earliest reachable out-group in the swing band

Selection order inside the kernel:
- Primary: compare scoreproxy score
- Secondary: higher body_fever
- Tertiary: lexicographic compare of head bits interpreted as a 128-bit integer with m3 most significant then m2 then m1 then m0

Swing band definition for a fever activation at group s with activation carry r_act:
- d_ms is fixed for the cell
- Threshold Q = base_s + r_act + d_ms
- A later group g is in fever iff base_g + r_g < Q
- Using global carry bounds [-40, 80], membership can vary only for base_g in [Q - 80, Q + 40)

## Exact interval DP reference solver

A CPU reference solver computes the exact Q1 optimum over all feasible carry paths for a fixed chart and fixed cell parameters.
It exists for validation and for constructing counterexamples to greedy policies.

Two objective variants are supported:
- countmax maximizes the total number of fever notes
- scoreproxy maximizes the sum of per-note fever bonus weights w_i from the fixed score proxy

The DP enumerates activation carry values explicitly within the bounded carry domain and enumerates feasible fever exits by scanning the swing band using interval propagation.
The DP state is a boundary state consisting of
- start_note index for the next non-fever fill segment
- start_group index and a carry interval [lo, hi] representing feasible carries at that group when the segment begins
- section index which determines whether notes_to_fill is fill_count - 1 or fill_count

## Empirical results on real charts

### Ceiling vs Monte Carlo best of S on real charts

All scores below use the fixed score proxy constants base 10000.0 combo_mul 2.6 fever_mul 5.25.

Bopeebo Hard at ft_idx 0 ff_idx 160 with 2000 Monte Carlo seeds:
- MC best score 47904375
- Ceiling score 47904375
- Fever notes in best signature 347
- Window trace from MC best and ceiling matched on this cell with 5 fever windows
- Wall times observed on this machine: MC best of 2000 about 10.9 seconds, GPU ceiling about 2.1 seconds, CPU ceiling about 4.2 ms

Baby I Don't Care Hard at ft_idx 0 ff_idx 160 with 500 Monte Carlo seeds:
- MC best score 54486075
- Ceiling score 54486075
- Fever notes in best signature 376
- Wall times observed on this machine: MC best of 500 about 2.3 seconds, GPU ceiling about 2.1 seconds, CPU ceiling about 5.3 ms

### Greedy ceiling vs exact DP on a real chart

A sampled-cell comparison against the exact DP shows that the greedy ceiling kernel is not globally optimal over the full feasible carry space.
Concrete real-song counterexamples were found on Mark Twain Hard.

Mark Twain Hard exact counterexample cells and signatures:
```json
{
  "song": "Mark Twain (Hard) by Half an Orange [Monstercat].txt",
  "notes": 382,
  "groups": 258,
  "cells": [
    {
      "ft_idx": 38,
      "ff_idx": 59,
      "fill_count": 40,
      "d_ms": 29531,
      "greedy": {
        "sig": [
          100,
          [
            0,
            4294967168,
            4294967295,
            15
          ],
          223,
          59,
          2,
          19
        ],
        "countmax_obj": 284,
        "scoreproxy_obj": 39277595
      },
      "dp_countmax": {
        "sig": [
          100,
          [
            0,
            4294967168,
            4294967295,
            15
          ],
          225,
          57,
          2,
          17
        ],
        "countmax_obj": 286,
        "scoreproxy_obj": 39498595
      },
      "dp_scoreproxy": {
        "sig": [
          100,
          [
            0,
            4294967168,
            4294967295,
            15
          ],
          225,
          57,
          2,
          17
        ],
        "countmax_obj": 286,
        "scoreproxy_obj": 39498595
      },
      "dp_minus_greedy": {
        "countmax": 2,
        "scoreproxy": 221000
      }
    },
    {
      "ft_idx": 50,
      "ff_idx": 104,
      "fill_count": 29,
      "d_ms": 31241,
      "greedy": {
        "sig": [
          100,
          [
            4026531840,
            4294967295,
            4294967295,
            15
          ],
          226,
          56,
          2,
          27
        ],
        "countmax_obj": 298,
        "scoreproxy_obj": 40330915
      },
      "dp_countmax": {
        "sig": [
          100,
          [
            4026531840,
            4294967295,
            4294967295,
            15
          ],
          230,
          52,
          2,
          23
        ],
        "countmax_obj": 302,
        "scoreproxy_obj": 40772915
      },
      "dp_scoreproxy": {
        "sig": [
          100,
          [
            4026531840,
            4294967295,
            4294967295,
            15
          ],
          230,
          52,
          2,
          23
        ],
        "countmax_obj": 302,
        "scoreproxy_obj": 40772915
      },
      "dp_minus_greedy": {
        "countmax": 4,
        "scoreproxy": 442000
      }
    }
  ]
}
```

For both listed cells, the greedy ceiling signature is strictly dominated by the exact DP optimum under both countmax and scoreproxy objectives.
The head fever bitmasks match and the difference is entirely in body_fever and body_normal counts.

### Runtime evidence that exact DP is not production-feasible

Exact DP runtime depends strongly on note density and on how many unique pairs of fill_count and d_ms are encountered.
Two measurements from this machine are included to bound the practical cost.

Mark Twain Hard with 60 sampled cells and both objectives:
- Notes 382
- GPU ceiling precompute about 768 ms
- Exact DP wall time about 6.43 seconds for 118 cached pairs, about 54.5 ms per cached pair
- Mismatch and greedy-worse rates about 0.0333 for both objectives
- Maximum scoreproxy objective delta observed 442000

Everything Will Freeze Vocal Extended Cut Hard with 10 sampled cells and scoreproxy objective only:
- Notes 4387
- GPU ceiling precompute about 752 ms
- Exact DP wall time about 36.8 seconds for 10 cached pairs, about 3.68 seconds per cached pair
- No mismatches were observed in this sample

## Regime theorem and dataset-wide scan

The union swing band argument provides an exact regime in which fever boundaries are deterministic and therefore all methods produce the same fever mask for a window.

For a window activated at group s with duration d_ms and activation carry r_s, the threshold is Q = base_s + r_s + d_ms.
Using global carry bounds r in [-40, 80], the swing band for a fixed Q is base_g in [Q - 80, Q + 40).
The union of those swing bands across all feasible activation carries produces a fixed-width interval
[base_s + d_ms - 120, base_s + d_ms + 120).

If there are no chord groups with base time in that interval then the fever end group for that window is carry-independent and therefore boundary flips cannot occur in that window.

A scan of this condition on the Hard dataset in this snapshot produced the following aggregate statistics:
```json
{
  "songs_scanned": 957,
  "total_cells": 24806397,
  "cert_cells": 1540692,
  "cert_cell_frac": 0.062108656892010554,
  "per_song_frac_p50": 0.027005130974885227,
  "per_song_frac_p10": 0.0010416264804598589,
  "per_song_frac_p90": 0.17095019482273058,
  "elapsed_sec": 87.89398350002011
}
```

## Appendix A: FT and FF factor tables for indices 0..160

These arrays are taken directly from Stats.txt in this snapshot and are included so that ft_idx and ff_idx are fully defined offline.
```json
{
  "stats_fp": "<redacted-user-home>\\Desktop\\RoBeats-Calculator-Engine\\Data\\Gear\\Stats.txt",
  "Fever Fill Rate": [
    1.0,
    0.9820353098,
    0.9638454088,
    0.9454694842,
    0.9280532945,
    0.9112024693,
    0.8942906187,
    0.8773467828,
    0.8618034877,
    0.8464382264,
    0.8311142118,
    0.8158531692,
    0.8014982504,
    0.787451647,
    0.7735139088,
    0.7597025926,
    0.7462337736,
    0.7332371535,
    0.7204053778,
    0.7077540713,
    0.6952988589,
    0.6830992982,
    0.6711361664,
    0.6594136819,
    0.6479472582,
    0.6366810768,
    0.6254204764,
    0.6144830839,
    0.6038858878,
    0.5936458766,
    0.583225146,
    0.5730549899,
    0.5633616375,
    0.5541663591,
    0.5447974869,
    0.5356419665,
    0.5272190362,
    0.5195599713,
    0.5113048006,
    0.5042462408,
    0.4984984985,
    0.4947616616,
    0.4891878488,
    0.4837600706,
    0.477831301,
    0.4711952987,
    0.4651741067,
    0.4589573022,
    0.4524109517,
    0.4457424273,
    0.4395336251,
    0.4331603593,
    0.4266503765,
    0.4200406941,
    0.4137889345,
    0.4074889415,
    0.4011632772,
    0.3948345043,
    0.3886054389,
    0.3824832004,
    0.3764217821,
    0.3704422022,
    0.3645654788,
    0.358762331,
    0.353105032,
    0.3476170896,
    0.342320106,
    0.3371833403,
    0.3322184682,
    0.3275230221,
    0.3231202538,
    0.3190334147,
    0.3152519588,
    0.3118398775,
    0.3088213145,
    0.3062201924,
    0.3041158537,
    0.3024775865,
    0.3012817774,
    0.3005491182,
    0.3003003003,
    0.2989801371,
    0.297660399,
    0.296341511,
    0.2950238983,
    0.2937079858,
    0.2923941988,
    0.2910829621,
    0.2897785169,
    0.2885057557,
    0.2872366227,
    0.2859715125,
    0.2847108194,
    0.2834549379,
    0.2822042624,
    0.2809591872,
    0.2797215442,
    0.2785265597,
    0.2773379372,
    0.276156036,
    0.2749812153,
    0.2738138343,
    0.2726542523,
    0.2715028285,
    0.270359922,
    0.269244746,
    0.2681464485,
    0.2670572812,
    0.2659775781,
    0.2649076735,
    0.2638479016,
    0.2627985966,
    0.2617600926,
    0.2607342878,
    0.2597279091,
    0.2587331086,
    0.2577502111,
    0.2567795413,
    0.2558214242,
    0.2548761845,
    0.253944147,
    0.2530256365,
    0.2521164399,
    0.2512177806,
    0.2503338997,
    0.2494651313,
    0.2486118093,
    0.2477742678,
    0.2469528407,
    0.246147862,
    0.2453596629,
    0.2445648313,
    0.2437885659,
    0.2430312328,
    0.2422931983,
    0.2415748286,
    0.2408764899,
    0.2401985484,
    0.2395413703,
    0.2388805583,
    0.2382335904,
    0.237611006,
    0.2370132353,
    0.2364407087,
    0.2358938564,
    0.2353731089,
    0.2348788965,
    0.2343801657,
    0.2339083408,
    0.2334690557,
    0.2330628526,
    0.2326902739,
    0.2323518619,
    0.2320481588,
    0.2317645766,
    0.2315128663,
    0.231305299,
    0.2311425983,
    0.2310254877,
    0.2309546907,
    0.2309309309
  ],
  "Fever Time": [
    1.0,
    1.04776241,
    1.096123584,
    1.144979335,
    1.191283457,
    1.236084453,
    1.281047696,
    1.326095979,
    1.367420667,
    1.408272021,
    1.449013712,
    1.489587981,
    1.527753155,
    1.565098615,
    1.602154638,
    1.638874544,
    1.674683859,
    1.709237748,
    1.743353367,
    1.776989176,
    1.810103633,
    1.842538393,
    1.874344564,
    1.90551093,
    1.935996511,
    1.965949712,
    1.995888075,
    2.02496713,
    2.053141712,
    2.080366651,
    2.108072067,
    2.135111284,
    2.160882832,
    2.185330159,
    2.210239017,
    2.23458064,
    2.256974539,
    2.277337561,
    2.29928544,
    2.318051911,
    2.333333333,
    2.339618014,
    2.348992153,
    2.358120689,
    2.368091802,
    2.379252351,
    2.389378901,
    2.399834436,
    2.410844208,
    2.422059453,
    2.43250153,
    2.443220204,
    2.454168811,
    2.465285095,
    2.475799418,
    2.486394861,
    2.497033478,
    2.507677324,
    2.518153479,
    2.528449971,
    2.538644175,
    2.548700741,
    2.558584321,
    2.568344161,
    2.577858709,
    2.58708843,
    2.595996994,
    2.604636099,
    2.612986112,
    2.620882998,
    2.628287654,
    2.635160974,
    2.641520696,
    2.647259196,
    2.65233587,
    2.656710485,
    2.6602496,
    2.663004867,
    2.665016001,
    2.6662482,
    2.666666667,
    2.668886941,
    2.671106501,
    2.67332463,
    2.675540616,
    2.677753741,
    2.679963292,
    2.682168554,
    2.684362393,
    2.686502946,
    2.688637397,
    2.690765083,
    2.692885339,
    2.694997503,
    2.697100912,
    2.699194902,
    2.701276393,
    2.70328614,
    2.705285187,
    2.707272929,
    2.709248764,
    2.711212087,
    2.713162293,
    2.715098778,
    2.717020939,
    2.718896463,
    2.720743599,
    2.722575381,
    2.724391245,
    2.72619063,
    2.727972974,
    2.729737714,
    2.731484289,
    2.733209506,
    2.734902052,
    2.736575125,
    2.73822818,
    2.73986067,
    2.741472049,
    2.743061771,
    2.744629288,
    2.746174056,
    2.747703159,
    2.749214541,
    2.750701068,
    2.752162178,
    2.753597311,
    2.755005903,
    2.756387394,
    2.757741222,
    2.75906683,
    2.760403592,
    2.761709129,
    2.762982826,
    2.764224065,
    2.765432233,
    2.766606711,
    2.767746886,
    2.76885214,
    2.769963506,
    2.771051588,
    2.772098662,
    2.773104003,
    2.774066889,
    2.774986595,
    2.775862398,
    2.776693573,
    2.777532348,
    2.778325871,
    2.779064669,
    2.779747829,
    2.780374438,
    2.780943586,
    2.781454359,
    2.781931293,
    2.782354624,
    2.782703714,
    2.782977347,
    2.783174306,
    2.783293374,
    2.783333333
  ]
}
```

## Appendix B: Raw chart files embedded for offline reproduction

### Mark Twain (Hard)
```text
Song Name	Mark Twain (Hard) by Half an Orange [Monstercat]
Difficulty	10
Primary Color	Beat
Secondary Color	Vibe
Last Note Time	84.621
Total Notes	382
Fever Fill	105
Fever Time	12.693150
Long Notes	68
BPM	115
Song Length	91.323968254

Timing Points
0.100	521.7391


Song Data
0.100	1	1	1
0.491	2	3	1
0.882	3	1	1
1.143	4	1	1
1.665	5	4	1
2.186	6	1	1
2.578	7	3	1
2.969	8	1	1
3.491	9	2	1
3.621	10	4	1
3.752	11	2	1
4.013	12	3	1
4.273	13	1	1
4.665	14	3	1
5.056	15	1	1
5.317	16	1	1
5.839	17	4	1
6.360	18	1	1
6.752	19	3	1
7.143	20	1	1
7.665	21	4	1
7.926	22	3	1
8.186	23	2	1
8.447	24	4	1
8.839	25	3	1
9.230	26	2	1
9.491	27	2	1
10.013	28	4	1
10.534	29	1	1
10.926	30	3	1
11.317	31	1	1
11.839	32	2	1
11.969	33	4	1
12.100	34	2	1
12.360	35	3	1
12.621	36	4	1
13.143	37	3	1
13.404	38	1	1
13.665	39	2	1
14.186	40	2	1
14.708	41	4	1
15.100	42	4	1
15.230	43	3	1
15.360	44	2	1
15.491	45	1	1
15.752	46	3	1
16.013	47	3	1
16.273	48	1	1
16.273	49	2	1
16.534	50	3	1
16.795	51	2	2
17.186	52	3	1
17.317	53	4	2
17.317	54	2	3
17.839	55	1	2
17.839	56	4	3
18.230	57	3	1
18.882	58	3	1
18.882	59	1	3
19.273	60	3	1
19.404	61	2	1
19.665	62	4	1
19.926	63	2	1
20.186	64	2	1
20.317	65	3	1
20.447	66	1	1
20.708	67	2	1
20.969	68	3	2
21.360	69	1	1
21.491	70	2	2
21.491	71	3	3
22.013	72	3	2
22.013	73	2	3
22.404	74	2	1
23.056	75	2	1
23.056	76	3	3
23.447	77	2	1
23.708	78	4	2
24.100	79	2	1
24.100	80	4	3
24.360	81	2	1
24.491	82	3	1
24.621	83	1	1
24.752	84	2	2
25.143	85	3	2
25.143	86	2	3
25.534	87	2	1
25.665	88	4	2
25.665	89	3	3
26.186	90	3	1
26.447	91	2	1
26.447	92	4	3
26.578	93	3	1
26.708	94	2	1
26.969	95	1	2
27.230	96	3	1
27.621	97	3	1
27.752	98	1	3
28.013	99	1	1
28.273	100	2	1
28.404	101	4	2
28.665	102	3	1
28.795	103	2	1
28.795	104	4	3
28.926	105	3	2
29.317	106	2	2
29.317	107	3	3
29.708	108	3	1
30.360	109	3	1
30.360	110	2	3
30.752	111	3	1
31.404	112	3	1
31.795	113	3	1
32.186	114	2	2
32.447	115	3	1
32.447	116	4	1
32.447	117	2	3
32.969	118	4	2
33.491	119	1	2
33.491	120	3	1
33.491	121	4	3
34.273	122	3	1
34.534	123	3	1
34.534	124	4	1
34.795	125	2	1
34.795	126	1	3
35.056	127	4	2
35.578	128	1	2
35.578	129	3	1
35.578	130	4	3
35.969	131	3	1
36.621	132	3	1
36.621	133	4	1
36.621	134	1	3
36.882	135	2	1
37.143	136	3	2
37.404	137	2	2
37.404	138	3	3
37.665	139	3	1
38.447	140	3	1
38.708	141	3	1
38.708	142	4	1
39.230	143	1	1
39.230	144	2	3
39.491	145	3	2
39.752	146	2	1
40.143	147	2	1
40.795	148	1	1
40.795	149	2	1
40.795	150	3	3
41.317	151	2	1
41.578	152	2	1
41.839	153	1	1
41.839	154	3	1
42.100	155	3	1
42.360	156	4	1
42.621	157	2	1
42.882	158	2	2
42.882	159	3	1
43.404	160	1	1
43.404	161	3	1
43.404	162	2	3
43.665	163	4	1
43.795	164	1	1
43.926	165	3	1
44.708	166	3	1
44.969	167	2	1
44.969	168	3	1
45.230	169	4	1
45.491	170	1	1
45.491	171	3	2
45.882	172	2	1
45.882	173	3	3
46.013	174	1	2
46.013	175	4	1
46.534	176	2	1
47.056	177	3	1
47.056	178	4	1
47.056	179	1	3
47.578	180	2	1
48.100	181	1	1
48.100	182	4	1
48.621	183	2	1
48.882	184	2	2
49.143	185	3	1
49.143	186	4	1
49.143	187	2	3
49.404	188	4	2
49.665	189	3	2
49.665	190	4	3
49.926	191	1	2
49.926	192	3	3
50.186	193	2	2
50.186	194	4	1
50.186	195	1	3
50.447	196	3	1
50.447	197	2	3
50.708	198	4	2
50.969	199	3	1
50.969	200	4	3
51.230	201	1	1
51.230	202	2	1
51.621	203	1	1
51.621	204	2	1
52.013	205	3	1
52.273	206	2	2
52.273	207	4	1
52.534	208	3	1
52.534	209	2	3
52.795	210	4	2
53.056	211	3	1
53.056	212	4	3
53.317	213	1	1
53.317	214	2	1
53.839	215	1	2
53.839	216	2	2
54.360	217	3	2
54.360	218	4	1
54.360	219	1	3
54.360	220	2	3
54.621	221	2	1
54.621	222	3	3
54.882	223	4	2
55.143	224	2	1
55.143	225	4	3
55.404	226	1	1
55.404	227	2	1
55.795	228	1	1
55.795	229	2	1
56.186	230	3	1
56.447	231	2	2
56.447	232	4	1
56.708	233	3	1
56.708	234	2	3
56.969	235	4	2
57.230	236	3	1
57.230	237	4	3
57.491	238	1	1
57.491	239	2	1
57.882	240	1	1
57.882	241	2	1
58.013	242	4	1
58.143	243	3	1
58.273	244	1	2
58.273	245	2	1
58.534	246	2	2
58.534	247	4	1
58.534	248	1	3
58.795	249	3	1
58.795	250	2	3
59.056	251	4	2
59.317	252	3	1
59.317	253	4	3
59.578	254	1	1
59.578	255	2	1
59.969	256	1	1
59.969	257	2	1
60.360	258	3	1
60.621	259	2	2
60.621	260	4	1
60.882	261	3	1
60.882	262	2	3
61.143	263	4	2
61.404	264	3	1
61.404	265	4	3
61.665	266	1	1
61.665	267	2	1
62.186	268	1	2
62.186	269	2	2
62.708	270	3	2
62.708	271	4	1
62.708	272	1	3
62.708	273	2	3
62.969	274	2	1
62.969	275	3	3
63.230	276	4	2
63.491	277	2	1
63.491	278	4	3
63.752	279	1	1
63.752	280	2	1
64.143	281	1	1
64.143	282	2	1
64.534	283	3	1
64.795	284	2	2
64.795	285	4	1
65.056	286	3	1
65.056	287	2	3
65.317	288	4	2
65.578	289	3	1
65.578	290	4	3
65.839	291	1	1
65.839	292	2	1
66.360	293	1	2
66.360	294	3	1
66.360	295	4	2
66.621	296	2	1
66.882	297	2	1
66.882	298	3	2
66.882	299	1	3
66.882	300	4	3
67.665	301	2	1
67.665	302	3	3
67.926	303	2	2
67.926	304	4	1
68.447	305	1	1
68.447	306	2	3
68.708	307	2	1
68.969	308	1	1
68.969	309	3	1
69.230	310	3	1
69.491	311	2	1
69.752	312	2	1
70.013	313	3	1
70.013	314	4	1
70.273	315	3	1
70.534	316	1	1
70.534	317	2	1
70.795	318	2	1
71.056	319	1	1
71.056	320	4	2
71.839	321	3	1
71.839	322	4	3
72.100	323	2	1
72.100	324	3	2
72.621	325	1	1
72.621	326	3	3
72.882	327	2	1
73.143	328	1	1
73.143	329	3	1
73.404	330	3	1
73.665	331	2	1
73.926	332	2	1
74.186	333	3	1
74.186	334	4	1
74.447	335	3	1
74.708	336	2	1
74.969	337	2	1
75.230	338	1	1
75.230	339	3	2
75.752	340	3	3
76.013	341	4	1
76.273	342	2	2
76.273	343	3	1
76.534	344	1	2
76.534	345	2	3
77.056	346	4	2
77.056	347	1	3
77.317	348	2	1
77.578	349	4	3
78.230	350	2	1
78.360	351	1	1
78.360	352	3	1
78.621	353	3	1
78.882	354	3	2
78.882	355	4	1
79.404	356	4	1
79.665	357	2	1
79.665	358	3	3
79.926	359	2	2
80.447	360	3	1
80.447	361	4	1
80.447	362	2	3
80.839	363	2	1
81.491	364	2	2
81.491	365	4	1
81.752	366	3	1
81.752	367	2	3
82.013	368	4	2
82.273	369	3	1
82.273	370	4	3
82.534	371	1	1
82.534	372	4	2
82.795	373	3	1
82.795	374	4	3
82.926	375	4	1
83.056	376	3	2
83.447	377	4	1
83.447	378	3	3
83.578	379	1	2
83.578	380	2	2
84.621	381	1	3
84.621	382	2	3
```

### Bopeebo (Hard)
```text
Song Name	Bopeebo (Hard) by Kawai Sprite
Difficulty	14
Primary Color	Vibe
Secondary Color	Vibe
Last Note Time	76.609
Total Notes	471
Fever Fill	108
Fever Time	11.491350
Long Notes	148
BPM	100
Song Length	81.246621315

Timing Points
0.109	600.0000


Song Data
0.109	1	3	1
0.709	2	1	2
1.009	3	3	1
1.309	4	2	2
1.309	5	1	3
1.609	6	3	1
1.909	7	1	1
1.909	8	4	1
1.909	9	2	3
2.509	10	4	1
3.109	11	1	1
3.109	12	2	2
3.409	13	4	1
3.709	14	3	2
3.709	15	2	3
4.009	16	1	1
4.159	17	2	1
4.309	18	1	2
4.309	19	4	2
4.309	20	3	3
4.609	21	1	3
4.609	22	4	3
4.909	23	3	2
5.359	24	3	3
5.509	25	2	2
5.509	26	4	1
5.809	27	3	1
5.959	28	2	3
6.109	29	1	2
6.409	30	2	1
6.709	31	3	1
6.709	32	4	1
6.709	33	1	3
7.309	34	4	2
7.759	35	4	3
7.909	36	1	1
7.909	37	3	2
8.209	38	4	1
8.359	39	3	3
8.509	40	2	2
8.809	41	4	1
8.959	42	3	1
9.109	43	1	2
9.109	44	4	2
9.109	45	2	3
9.409	46	1	3
9.409	47	4	3
9.709	48	2	2
10.009	49	2	3
10.159	50	1	1
10.309	51	3	1
10.309	52	4	1
10.609	53	1	1
10.909	54	2	2
11.209	55	3	1
11.509	56	1	1
11.509	57	4	1
11.509	58	2	3
11.659	59	3	1
12.109	60	3	2
12.409	61	3	3
12.559	62	2	1
12.709	63	1	1
12.709	64	4	1
13.009	65	2	1
13.309	66	3	2
13.609	67	1	1
13.759	68	2	1
13.909	69	1	2
13.909	70	4	2
13.909	71	3	3
14.059	72	2	1
14.209	73	1	3
14.209	74	4	3
14.509	75	3	1
14.809	76	2	2
14.959	77	1	1
15.109	78	3	1
15.109	79	4	1
15.109	80	2	3
15.409	81	1	1
15.709	82	2	2
16.009	83	3	1
16.309	84	1	1
16.309	85	4	1
16.309	86	2	3
16.459	87	3	1
16.909	88	4	1
17.209	89	3	2
17.359	90	2	1
17.509	91	1	1
17.509	92	4	1
17.509	93	3	3
17.809	94	2	1
18.109	95	3	2
18.409	96	1	1
18.559	97	2	1
18.709	98	1	2
18.709	99	4	2
18.709	100	3	3
19.009	101	2	1
19.309	102	3	2
19.309	103	1	3
19.309	104	4	3
19.459	105	3	3
19.609	106	2	1
19.909	107	1	2
19.909	108	4	1
20.209	109	2	2
20.359	110	2	3
20.809	111	4	2
20.809	112	1	3
20.959	113	4	3
21.109	114	1	1
21.109	115	3	1
21.259	116	4	2
21.409	117	4	3
21.709	118	3	2
21.859	119	3	3
22.009	120	4	1
22.309	121	1	1
22.309	122	2	2
22.609	123	1	2
22.759	124	1	3
23.209	125	4	2
23.209	126	2	3
23.359	127	3	1
23.359	128	4	3
23.509	129	1	2
23.509	130	4	2
23.809	131	1	3
23.809	132	4	3
24.109	133	3	2
24.259	134	3	3
24.409	135	4	1
24.709	136	1	1
24.709	137	2	2
25.009	138	1	2
25.159	139	1	3
25.609	140	4	2
25.609	141	2	3
25.759	142	4	3
25.909	143	1	1
25.909	144	3	1
26.059	145	4	2
26.209	146	4	3
26.509	147	3	2
26.659	148	3	3
26.809	149	4	1
27.109	150	1	1
27.109	151	3	2
27.409	152	1	2
27.559	153	1	3
28.009	154	2	2
28.009	155	3	3
28.159	156	3	1
28.159	157	2	3
28.309	158	1	2
28.309	159	4	2
28.459	160	1	3
28.459	161	4	3
28.609	162	1	2
28.609	163	4	2
28.759	164	1	3
28.759	165	4	3
28.909	166	3	2
29.059	167	3	3
29.209	168	2	1
29.509	169	1	2
29.509	170	4	1
29.809	171	2	2
29.959	172	2	3
30.409	173	4	2
30.559	174	4	3
30.709	175	2	1
30.709	176	3	1
30.709	177	1	3
30.859	178	4	2
31.009	179	4	3
31.309	180	3	2
31.459	181	3	3
31.609	182	2	1
31.909	183	1	1
31.909	184	2	2
32.209	185	1	2
32.359	186	1	3
32.809	187	4	2
32.959	188	3	1
32.959	189	4	3
33.109	190	1	2
33.109	191	4	2
33.109	192	2	3
33.409	193	2	1
33.409	194	1	3
33.409	195	4	3
33.709	196	3	2
33.859	197	3	3
34.009	198	2	1
34.309	199	1	1
34.309	200	4	1
34.609	201	3	2
34.909	202	2	2
34.909	203	3	3
35.209	204	4	2
35.359	205	4	3
35.509	206	1	1
35.509	207	3	1
35.659	208	4	2
35.809	209	1	1
35.809	210	2	3
35.809	211	4	3
36.109	212	3	2
36.259	213	3	3
36.409	214	2	1
36.709	215	1	1
36.709	216	3	1
37.009	217	4	2
37.309	218	3	2
37.309	219	4	3
37.609	220	1	2
37.759	221	2	1
37.759	222	1	3
37.909	223	1	2
37.909	224	4	2
38.059	225	2	2
38.059	226	1	3
38.059	227	4	3
38.209	228	1	1
38.209	229	4	1
38.209	230	2	3
38.209	231	3	3
38.509	232	3	2
39.109	233	2	2
39.109	234	4	1
39.109	235	3	3
39.409	236	3	1
39.559	237	2	3
39.709	238	1	2
40.009	239	2	1
40.309	240	3	1
40.309	241	4	1
40.309	242	1	3
40.909	243	4	2
41.509	244	1	1
41.509	245	3	2
41.509	246	4	3
41.809	247	4	1
41.959	248	3	3
42.109	249	2	2
42.409	250	4	1
42.559	251	3	1
42.709	252	1	2
42.709	253	4	2
42.709	254	2	3
43.009	255	1	3
43.009	256	4	3
43.309	257	1	2
43.609	258	1	3
43.909	259	2	1
43.909	260	3	2
44.209	261	4	1
44.209	262	3	3
44.509	263	1	1
44.659	264	1	1
44.809	265	1	1
45.109	266	2	1
45.109	267	3	2
45.409	268	3	3
45.709	269	2	2
46.009	270	2	3
46.309	271	1	1
46.309	272	4	2
46.609	273	3	1
46.609	274	4	3
46.909	275	2	1
47.059	276	2	1
47.209	277	2	1
47.359	278	3	1
47.509	279	1	2
47.509	280	4	2
47.809	281	1	3
47.809	282	4	3
48.109	283	3	2
48.559	284	1	1
48.709	285	2	2
48.709	286	4	1
48.709	287	3	3
49.009	288	3	1
49.159	289	2	3
49.309	290	1	2
49.609	291	3	1
49.909	292	2	1
49.909	293	4	1
49.909	294	1	3
50.059	295	3	1
50.509	296	4	2
50.959	297	2	1
51.109	298	1	1
51.109	299	3	2
51.109	300	4	3
51.409	301	4	1
51.559	302	3	3
51.709	303	2	2
52.009	304	4	1
52.159	305	3	1
52.309	306	1	2
52.309	307	4	2
52.309	308	2	3
52.459	309	3	1
52.609	310	1	3
52.609	311	4	3
52.909	312	3	2
53.359	313	4	1
53.509	314	1	1
53.509	315	2	1
53.809	316	4	1
54.409	317	4	1
54.709	318	1	1
54.709	319	2	1
54.859	320	4	1
54.859	321	3	3
55.309	322	4	2
55.759	323	1	1
55.909	324	2	1
55.909	325	3	1
56.209	326	1	1
56.809	327	1	1
56.959	328	2	1
56.959	329	4	3
57.109	330	1	2
57.109	331	4	2
57.409	332	3	1
57.709	333	3	2
57.709	334	1	3
57.709	335	4	3
57.859	336	3	3
58.009	337	2	1
58.309	338	1	2
58.309	339	4	1
58.609	340	2	2
58.759	341	2	3
59.209	342	4	2
59.209	343	1	3
59.359	344	4	3
59.509	345	1	1
59.509	346	3	1
59.659	347	4	2
59.809	348	4	3
60.109	349	3	2
60.259	350	3	3
60.409	351	4	1
60.709	352	1	1
60.709	353	2	2
61.009	354	1	2
61.159	355	1	3
61.609	356	4	2
61.609	357	2	3
61.759	358	3	1
61.759	359	4	3
61.909	360	1	2
61.909	361	4	2
62.209	362	2	1
62.209	363	1	3
62.209	364	4	3
62.509	365	3	2
62.659	366	3	3
62.809	367	4	1
63.109	368	1	1
63.109	369	2	1
63.409	370	1	2
63.559	371	1	3
63.709	372	2	2
64.009	373	4	2
64.159	374	4	3
64.309	375	1	1
64.309	376	3	1
64.309	377	2	3
64.459	378	4	2
64.609	379	2	1
64.609	380	4	3
64.909	381	3	2
65.059	382	3	3
65.209	383	4	1
65.509	384	1	1
65.509	385	2	1
65.809	386	1	2
65.959	387	1	3
66.109	388	3	2
66.409	389	1	2
66.559	390	2	1
66.559	391	1	3
66.709	392	1	2
66.709	393	4	2
66.709	394	3	3
66.859	395	3	2
66.859	396	1	3
66.859	397	4	3
67.009	398	1	2
67.009	399	4	2
67.009	400	3	3
67.159	401	1	3
67.159	402	4	3
67.309	403	3	2
67.459	404	3	3
67.609	405	2	1
67.909	406	1	1
67.909	407	4	1
68.209	408	1	2
68.359	409	1	3
68.509	410	2	2
68.809	411	4	2
68.959	412	4	3
69.109	413	1	1
69.109	414	3	1
69.109	415	2	3
69.259	416	4	2
69.409	417	4	3
69.709	418	3	2
69.859	419	3	3
70.009	420	2	1
70.309	421	1	1
70.309	422	4	1
70.609	423	1	2
70.759	424	1	3
70.909	425	3	2
71.209	426	4	2
71.359	427	2	1
71.359	428	4	3
71.509	429	1	2
71.509	430	4	2
71.509	431	3	3
71.809	432	2	1
71.809	433	1	3
71.809	434	4	3
72.109	435	3	2
72.259	436	3	3
72.409	437	2	1
72.709	438	1	1
72.709	439	4	1
73.009	440	3	2
73.309	441	2	2
73.309	442	3	3
73.609	443	4	2
73.759	444	4	3
73.909	445	1	1
73.909	446	3	1
74.059	447	4	2
74.209	448	1	1
74.209	449	2	3
74.209	450	4	3
74.509	451	3	2
74.659	452	3	3
74.809	453	2	1
74.959	454	3	2
75.109	455	1	1
75.109	456	2	1
75.109	457	3	3
75.409	458	4	2
75.709	459	3	2
75.709	460	4	3
76.009	461	1	2
76.159	462	2	1
76.159	463	1	3
76.309	464	1	2
76.309	465	4	2
76.459	466	2	1
76.459	467	1	3
76.459	468	3	3
76.459	469	4	3
76.609	470	1	1
76.609	471	4	1
```

### Baby I Don't Care (Hard)
```text
Song Name	Baby I Don't Care (Hard) by Johnny / Michiko Hamada [Nash Music Library]
Difficulty	16
Primary Color	Chill
Secondary Color	Beat
Last Note Time	106.016
Total Notes	575
Fever Fill	170
Fever Time	15.902400
Long Notes	67
BPM	100
Song Length	108.177664399

Timing Points
0.416	600.0000


Song Data
0.416	1	4	2
1.016	2	1	2
1.016	3	4	3
1.316	4	4	2
1.316	5	1	3
1.916	6	1	2
1.916	7	4	3
2.216	8	1	3
2.816	9	2	2
3.416	10	4	2
3.416	11	2	3
3.716	12	3	1
3.716	13	4	3
3.866	14	1	2
4.616	15	1	3
5.216	16	3	2
5.816	17	1	2
5.816	18	3	3
6.116	19	3	2
6.116	20	1	3
6.716	21	4	2
6.716	22	3	3
7.316	23	3	2
7.316	24	4	3
7.616	25	1	2
7.616	26	3	3
9.416	27	4	2
9.416	28	1	3
10.916	29	3	2
10.916	30	4	3
12.416	31	1	1
12.416	32	2	1
12.416	33	3	3
13.016	34	3	1
13.466	35	2	1
13.916	36	1	1
14.216	37	3	1
14.216	38	4	1
14.366	39	2	1
14.666	40	3	1
14.816	41	1	1
14.816	42	2	1
15.416	43	3	1
15.866	44	2	1
16.316	45	1	1
16.616	46	3	1
16.616	47	4	1
17.216	48	1	1
17.216	49	2	1
17.816	50	3	1
18.266	51	2	1
18.716	52	1	1
19.016	53	3	1
19.016	54	4	1
19.166	55	2	1
19.466	56	3	1
19.616	57	1	1
19.616	58	2	1
20.216	59	3	1
20.666	60	2	1
21.116	61	1	1
21.416	62	3	1
21.416	63	4	1
22.016	64	1	1
22.016	65	2	1
22.616	66	3	1
23.066	67	2	1
23.516	68	1	1
23.816	69	3	1
23.816	70	4	1
23.966	71	2	1
24.266	72	3	1
24.416	73	1	1
24.416	74	2	1
25.016	75	3	1
25.466	76	2	1
25.916	77	1	1
26.216	78	3	1
26.216	79	4	1
26.816	80	1	1
26.816	81	2	1
27.416	82	3	1
27.866	83	2	1
28.316	84	1	1
28.616	85	3	1
28.616	86	4	1
28.766	87	2	1
29.066	88	3	1
29.216	89	1	1
29.816	90	3	1
30.266	91	2	1
30.716	92	1	1
31.016	93	2	2
31.466	94	3	1
31.616	95	1	1
31.616	96	4	1
31.616	97	2	3
31.766	98	3	1
31.916	99	2	1
32.066	100	1	1
32.216	101	2	1
32.216	102	4	1
32.366	103	3	1
32.516	104	2	1
32.666	105	1	1
32.816	106	4	1
33.016	107	3	1
33.116	108	1	1
33.216	109	2	1
33.416	110	1	1
33.416	111	4	1
33.566	112	3	1
33.716	113	2	1
33.866	114	3	1
34.016	115	1	1
34.016	116	4	1
34.216	117	3	1
34.466	118	1	1
34.616	119	2	1
34.616	120	4	1
34.766	121	3	1
34.916	122	2	1
35.066	123	1	1
35.216	124	4	1
35.416	125	3	1
35.516	126	1	1
35.616	127	2	1
35.816	128	1	1
35.816	129	4	1
36.266	130	2	1
36.416	131	1	1
36.416	132	4	1
36.566	133	3	1
36.716	134	2	1
36.866	135	1	1
37.016	136	2	1
37.016	137	4	1
37.166	138	3	1
37.316	139	2	1
37.466	140	1	1
37.616	141	4	1
37.816	142	3	1
37.916	143	1	1
38.016	144	2	1
38.216	145	1	1
38.216	146	4	1
38.366	147	3	1
38.516	148	2	1
38.666	149	3	1
38.816	150	1	1
38.816	151	4	1
38.966	152	3	1
39.116	153	2	1
39.266	154	1	1
39.416	155	4	1
39.516	156	3	1
39.716	157	2	1
40.016	158	4	1
40.216	159	3	1
40.316	160	1	1
40.416	161	2	1
40.616	162	1	1
40.616	163	4	1
41.066	164	1	1
41.216	165	2	1
41.216	166	4	1
41.366	167	3	1
41.516	168	1	1
41.666	169	2	1
41.816	170	1	1
41.816	171	4	1
41.966	172	3	1
42.116	173	1	1
42.266	174	2	1
42.416	175	4	1
42.516	176	3	1
42.716	177	2	1
42.816	178	1	1
43.016	179	3	1
43.016	180	4	1
43.166	181	1	1
43.466	182	1	1
43.616	183	2	1
43.616	184	4	1
43.766	185	3	1
43.916	186	1	1
44.066	187	2	1
44.216	188	1	1
44.216	189	4	1
44.366	190	3	1
44.516	191	1	1
44.666	192	2	1
44.816	193	4	1
44.916	194	3	1
45.116	195	2	1
45.416	196	3	1
45.416	197	4	1
45.566	198	1	1
46.016	199	2	1
46.016	200	4	1
46.116	201	3	1
46.316	202	1	1
46.466	203	2	1
46.616	204	1	1
46.616	205	4	1
46.766	206	3	1
46.916	207	1	1
47.216	208	4	1
47.366	209	3	1
47.516	210	2	1
47.816	211	1	1
47.816	212	4	1
47.966	213	3	1
48.266	214	1	1
48.416	215	2	1
48.416	216	4	1
48.566	217	3	1
48.716	218	1	1
48.866	219	2	1
49.016	220	1	1
49.016	221	4	1
49.166	222	3	1
49.316	223	1	1
49.466	224	2	1
49.616	225	4	1
49.716	226	3	1
49.916	227	2	1
50.016	228	1	1
50.216	229	3	1
50.216	230	4	1
50.666	231	2	1
50.816	232	3	1
50.816	233	4	1
51.416	234	2	1
51.416	235	4	1
51.566	236	3	1
51.716	237	1	1
51.866	238	2	1
52.016	239	3	1
52.166	240	1	1
52.316	241	2	1
52.466	242	3	1
52.616	243	2	1
52.616	244	4	1
52.766	245	1	1
52.916	246	3	1
53.066	247	1	1
53.216	248	2	1
53.216	249	4	1
53.366	250	3	1
53.516	251	1	1
53.666	252	2	1
53.816	253	3	1
53.816	254	4	1
53.966	255	1	1
54.116	256	2	1
54.266	257	3	1
54.416	258	4	1
54.716	259	3	1
54.866	260	1	1
55.016	261	2	1
55.016	262	4	1
55.616	263	2	1
55.616	264	4	1
55.766	265	3	1
55.916	266	1	1
56.066	267	2	1
56.216	268	3	1
56.216	269	4	1
56.366	270	1	1
56.516	271	2	1
56.666	272	3	1
56.816	273	4	1
57.116	274	3	1
57.266	275	1	1
57.416	276	2	1
57.416	277	4	1
57.566	278	3	1
57.716	279	1	1
58.016	280	2	1
58.016	281	4	1
58.166	282	3	1
58.316	283	1	1
58.466	284	2	1
58.616	285	3	1
58.616	286	4	1
58.766	287	1	1
59.216	288	4	1
59.516	289	3	1
59.666	290	1	1
59.816	291	2	1
59.816	292	4	1
60.416	293	1	1
60.416	294	4	1
60.566	295	3	1
60.716	296	2	1
60.866	297	1	1
61.016	298	2	1
61.016	299	4	1
61.166	300	3	1
61.316	301	1	1
61.466	302	2	1
61.616	303	4	1
61.766	304	3	1
61.916	305	2	1
62.066	306	1	1
62.216	307	3	1
62.216	308	4	1
62.366	309	2	1
62.516	310	4	1
62.666	311	2	1
62.816	312	1	1
62.816	313	4	1
62.966	314	3	1
63.116	315	2	1
63.266	316	1	1
63.416	317	2	1
63.566	318	3	1
63.716	319	1	1
63.866	320	2	1
64.016	321	4	1
64.316	322	3	1
64.466	323	1	1
64.616	324	2	1
64.616	325	4	1
64.766	326	1	1
64.916	327	3	1
65.216	328	1	1
65.216	329	4	1
65.366	330	3	1
65.516	331	2	1
65.816	332	2	1
65.816	333	4	1
65.966	334	3	1
66.116	335	1	1
66.266	336	2	1
66.416	337	4	1
66.716	338	3	1
66.866	339	1	1
67.016	340	2	1
67.016	341	4	1
67.166	342	1	1
67.316	343	3	1
67.616	344	1	1
67.616	345	4	1
67.766	346	3	1
67.916	347	2	1
68.066	348	1	1
68.216	349	2	1
68.216	350	4	1
68.516	351	1	1
68.666	352	2	1
68.816	353	4	1
68.966	354	3	1
69.116	355	2	1
69.416	356	3	1
69.416	357	4	1
69.566	358	2	1
69.716	359	4	1
69.866	360	2	1
70.016	361	1	1
70.016	362	4	1
70.316	363	3	1
70.616	364	1	1
70.616	365	2	1
71.066	366	1	1
71.216	367	2	1
71.366	368	3	1
71.516	369	1	1
71.666	370	3	2
71.816	371	1	1
71.816	372	2	1
72.116	373	4	2
72.116	374	3	3
72.416	375	1	1
72.416	376	2	2
72.416	377	4	3
73.016	378	3	1
73.016	379	4	1
73.016	380	2	3
73.616	381	4	2
73.916	382	3	2
73.916	383	4	3
74.216	384	2	2
74.216	385	4	1
74.216	386	3	3
74.516	387	1	2
74.516	388	2	3
74.816	389	2	1
74.816	390	4	2
74.816	391	1	3
75.266	392	3	2
75.266	393	4	3
75.416	394	1	1
75.416	395	2	1
75.716	396	2	2
75.716	397	3	3
76.166	398	2	3
76.316	399	3	1
76.616	400	1	1
76.616	401	4	1
76.766	402	2	1
77.066	403	2	1
77.216	404	3	1
77.216	405	4	1
77.366	406	1	2
77.666	407	2	2
77.666	408	1	3
77.816	409	1	1
77.816	410	3	1
77.966	411	4	2
77.966	412	2	3
78.266	413	3	2
78.266	414	4	3
78.566	415	1	2
78.566	416	3	3
78.716	417	4	1
78.866	418	2	2
78.866	419	1	3
79.016	420	3	1
79.016	421	4	1
79.166	422	1	2
79.166	423	2	3
79.466	424	4	1
79.466	425	1	3
79.616	426	2	1
79.616	427	3	2
79.916	428	4	1
80.216	429	1	1
80.216	430	2	1
80.216	431	3	3
80.816	432	2	1
80.966	433	3	1
81.116	434	1	1
81.266	435	3	2
81.416	436	1	1
81.416	437	2	1
81.716	438	4	2
81.716	439	3	3
82.016	440	1	1
82.016	441	2	2
82.016	442	4	3
82.616	443	3	1
82.616	444	4	1
82.616	445	2	3
83.066	446	3	1
83.216	447	2	1
83.516	448	4	1
83.666	449	2	2
83.816	450	3	1
83.816	451	4	1
84.116	452	1	2
84.116	453	2	3
84.416	454	3	1
84.416	455	4	2
84.416	456	1	3
84.716	457	2	1
84.716	458	4	3
84.866	459	1	2
85.016	460	3	1
85.016	461	4	1
85.316	462	1	3
85.916	463	4	1
86.216	464	1	1
86.216	465	3	1
86.366	466	2	1
86.816	467	1	1
86.816	468	4	1
87.416	469	1	1
87.416	470	3	1
88.316	471	2	1
88.616	472	1	1
88.616	473	3	1
88.916	474	1	1
89.066	475	2	1
89.216	476	3	1
89.216	477	4	1
89.816	478	2	1
89.816	479	4	1
90.266	480	2	1
90.416	481	3	1
90.716	482	1	1
90.866	483	3	2
91.016	484	1	1
91.016	485	2	1
91.316	486	4	2
91.316	487	3	3
91.616	488	1	2
91.616	489	2	1
91.616	490	4	3
91.916	491	3	1
91.916	492	1	3
92.066	493	4	2
92.216	494	1	1
92.216	495	2	1
92.516	496	4	3
92.816	497	4	2
93.116	498	3	2
93.116	499	4	3
93.416	500	2	2
93.416	501	3	3
93.716	502	1	2
93.716	503	2	3
94.016	504	3	1
94.016	505	4	2
94.016	506	1	3
94.316	507	2	1
94.316	508	4	3
94.466	509	3	2
94.616	510	2	1
94.616	511	4	1
94.766	512	1	2
94.766	513	3	3
95.066	514	4	2
95.066	515	1	3
95.516	516	2	1
95.516	517	4	3
95.816	518	1	1
95.816	519	3	1
95.966	520	2	1
96.266	521	2	1
96.416	522	3	1
96.416	523	4	1
96.566	524	1	2
96.866	525	3	2
96.866	526	1	3
97.016	527	1	1
97.016	528	2	1
97.166	529	4	2
97.166	530	3	3
97.466	531	2	2
97.466	532	4	3
97.916	533	3	2
97.916	534	2	3
98.216	535	1	2
98.216	536	4	1
98.216	537	3	3
98.666	538	4	1
98.666	539	1	3
98.816	540	2	1
98.816	541	3	2
99.116	542	4	1
99.416	543	1	1
99.416	544	2	1
99.416	545	3	3
99.866	546	1	1
100.016	547	2	1
100.166	548	3	1
100.316	549	1	1
100.466	550	3	2
100.616	551	1	1
100.616	552	2	1
100.916	553	4	2
100.916	554	3	3
101.216	555	1	1
101.216	556	2	2
101.216	557	4	3
101.816	558	3	1
101.816	559	4	1
101.816	560	2	3
102.416	561	4	1
102.716	562	3	1
102.866	563	2	2
103.016	564	3	1
103.016	565	4	1
103.316	566	1	2
103.316	567	2	3
103.616	568	4	2
103.616	569	1	3
103.916	570	2	1
103.916	571	4	3
104.066	572	3	2
104.816	573	3	3
106.016	574	1	1
106.016	575	4	1
```

Open question: What superseded mathematical formulation can solve the full cascading fever-window problem, compute the Q1 optimal boundary-flip fever signature for every cell, and remain GPU-friendly enough to replace the current four-variant ceiling kernel while avoiding Monte Carlo sampling?
