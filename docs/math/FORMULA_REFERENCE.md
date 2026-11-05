# Fever Fill and Duration Formula Reference

This page is a plain-language companion to
[FEVER_TIMELINE_MATH.md](FEVER_TIMELINE_MATH.md) and
[TIMING_ENVELOPE_EXACT_FRONTIER.md](TIMING_ENVELOPE_EXACT_FRONTIER.md).
Those documents define the complete scoring and timing contracts.

## Fever fill

Fever fill uses the chart's key-hit count rather than its raw hit-object count:

$$
N_{\text{keys}} = N_{\text{total}} - N_{\text{long}}
$$

Conceptually, the independently verified reference formula is:

$$
\operatorname{fill}_{\text{perfect}}
=
\frac{1}{N_{\text{keys}} B_{\text{perfect}}}
$$

$$
\operatorname{fill}_{\text{great}}
=
\frac{1}{N_{\text{keys}} B_{\text{great}}}
\qquad\text{where}\qquad
B_{\text{great}} = 2B_{\text{perfect}}
$$

A Great therefore contributes half as much fever fill as a Perfect. The base
point `0.333` comes from the Fever Fill Rate stat curve; it is not an
optimizer-specific tuning constant.

For an all-Perfect section, the notes required to reach the activation
threshold are:

$$
\operatorname{notes\ to\ fill}
=
\left\lceil N_{\text{keys}} \times 0.333 \times \operatorname{FF} \right\rceil
$$

## Activation and transition notes

The hit that crosses the threshold is scored inside Fever. Consequently, the
number of non-Fever scored notes before the first window is:

$$
\operatorname{nonfever}_{1}
=
\operatorname{notes\ to\ fill} - 1
$$

After a Fever window, the transition note is scored outside Fever but does not
contribute fill because the fill/drain update occurs while Fever is still
active. Later sections therefore use:

$$
\operatorname{nonfever}_{2+}
=
\operatorname{notes\ to\ fill}
$$

## Fever duration

The chart-derived base duration is:

$$
\operatorname{duration}_{\text{base}}
=
\left(0.15 \times t_{\text{last}}\right) + 0.15
$$

The Fever Time stat then scales that duration:

$$
\operatorname{duration}
=
\operatorname{duration}_{\text{base}} \times \operatorname{FT}
$$

Production code evaluates the full per-note integer scoring and exact timing
frontier; these equations are explanatory, not a replacement implementation.
