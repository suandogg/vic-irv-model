# Positive persistence comparison — 28 October 2026

## Status and decision

Two positive concentration mappings are implemented as opt-in research controls
in October testing. Existing linear trial and Current default remain available
and unchanged. Main, central calculator, priors and Sheet values are unchanged.
No draw is filtered, clipped or resampled based on its seat outcome, and no
minimum/maximum number of Greens seats has been imposed.

The bounded positive form is a useful next candidate for evidence review: it
removes the silent negative-power reversal and moderates the upper concentration
tail. It is not a calibrated replacement. Its power bound of two is an explicit
research prior that needs justification, not a statistically neutral repair.

## Mapping definitions

Let c be the drawn party concentration coefficient and s the SD of the log of
positive base support across seats. Let d=c/s. The old spatial tilt is equivalent
to applying initial power k=1+d, up to a party-specific multiplicative constant
removed by balancing. Negative k reverses initial strength ordering.

New forms:

- **Positive softplus:** k=log(1+exp(a+b*d)), a=log(e-1),
  b=1/(1-exp(-1)). Always positive, no upper bound.
- **Positive bounded (0–2):** k=1+tanh(d), evaluated with a stable logistic
  expression. Always positive mathematically, with an upper bound of two.

Both give k=1 at c=0 and match the old local derivative there. They do **not**
have the same global variance, mean or tails at the same numeric input width.
Softplus is convex and can increase average concentration; bounded is symmetric
in power around one under a symmetric coefficient distribution. Finite samples
need not have median/mean exactly one. None of these properties guarantees
preservation of average/median seat counts after balancing and IRV.

For uniform/zero-support columns the concentration term has no spatial effect.
Zeros remain zero; infeasible numerical transformations fail transparently rather
than silently discarding the draw. Final seat rankings can still change through
other party patterns, balancing, regional/local effects and candidate conditions.
Positive powers preserve initial single-party strength ordering only.

## Controlled comparison

Seven profiles; seeds 20261010/11; 100 draws per seed, 200 per profile and 1,400
simulated elections overall. Same saved central scenario ALP 24.6 / LNP 29.1 /
GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5, committed inputs, corrected exact-field
VEC preference trial, upper-house regional grouping, no new regional-preference
trial. This is not current polling or a live Sheet-settings snapshot.

Raw normal coefficients, statewide targets and other sampled conditions remain
paired across forms. Positive ON concentration replaces alpha uncertainty as in
the previous trial; no double concentration mechanism is introduced.

| Profile | Average leading-party win % | Seats at least 98% | All 200 wins |
|---|---:|---:|---:|
| Current | 85.01 | 40 | 30 |
| Linear 0.20 | 81.77 | 24 | 11 |
| Linear 0.30 | 78.57 | 12 | 2 |
| Positive softplus 0.20 | 82.52 | 27 | 13 |
| Positive softplus 0.30 | 80.59 | 23 | 10 |
| Positive bounded 0.20 | 82.53 | 30 | 13 |
| Positive bounded 0.30 | 80.73 | 23 | 9 |

Leading probability is each profile's own maximum party probability in each seat,
averaged across 88 seats. It is not forecast accuracy. Counts near 98% are
sensitive to a handful of sampled losses. Maximum binomial Monte Carlo SE at
200 draws is about 3.54 pp; small differences should not determine model selection.

## Greens tails

| Profile | 5th–95th seats | Observed min–max | Zero-seat draws | Negative initial powers |
|---|---|---|---:|---:|
| Current | 5–8 | 4–9 | 0 | 0 |
| Linear 0.20 | 2–9 | 0–12 | 4 | 2 |
| Linear 0.30 | 0–9 | 0–14 | 16 | 13 |
| Positive softplus 0.20 | 3–9 | 0–13 | 1 | 0 |
| Positive softplus 0.30 | 2–9 | 0–14 | 5 | 0 |
| Positive bounded 0.20 | 3–8 | 0–12 | 1 | 0 |
| Positive bounded 0.30 | 1–9 | 0–12 | 7 | 0 |

Zero and nine seats remain possible. Positive bounded 0.30 produced seven
zero-seat draws (3.5% of this sample), so zero lies below the displayed 5th
percentile rather than being prohibited. This is a model-conditional sample
frequency, not a validated real-world probability.

At width 0.30, the highest observed district Greens primary was 84.49% under
linear, 90.92% under softplus and 75.69% under bounded. The 95th percentile of
each draw's highest district Greens primary was 72.70%, 77.31% and 68.87%,
respectively. Thus merely forcing positive persistence does not guarantee a
gentler upper tail: softplus can make it more extreme. These figures warrant
historical/candidate scrutiny rather than automatic approval or rejection.

The sample's Greens power 5th/median/95th percentiles at width 0.30 were:

- Linear: -0.052 / 0.807 / 1.904.
- Softplus: 0.282 / 0.818 / 2.102.
- Bounded: 0.218 / 0.809 / 1.718.

These distributions demonstrate that matching the centre/local derivative does
not match tail spread. A future calibrated comparison needs defensible power or
share-error distributions, not simply reuse a width because its label is the same.

## Five demonstration seats: fixed-party win probability (%)

| Seat (party) | Current | Linear 0.30 | Softplus 0.30 | Bounded 0.30 |
|---|---:|---:|---:|---:|
| Pakenham (LNP) | 69.0 | 61.0 | 56.5 | 63.0 |
| Morwell (ON) | 70.0 | 63.5 | 67.0 | 64.0 |
| Pascoe Vale (ALP) | 64.5 | 60.0 | 59.5 | 62.0 |
| Ashwood (LNP) | 82.0 | 71.5 | 73.5 | 75.5 |
| Yan Yean (ON) | 52.5 | 50.5 | 55.0 | 52.0 |

Party 5th–95th ranges under bounded 0.30: ALP 17–41, LNP 29–51, Greens 1–9,
ON 1–27. Current: ALP 17–41, LNP 31–49, Greens 5–8, ON 4–26. Individual-seat
certainty can fall appreciably without dramatic expansion of all statewide ranges.

## App access

Forecast → settings/methodology expander → select a concentration trial, then
Concentration mapping (research). Choose Linear, Positive softplus or Positive
bounded (0–2). The common and party-specific input widths remain available.
The form is stored in the run manifest, invalidates stale results and remains
selected in narrower/wider comparisons. Downloads include raw coefficients,
actual initial-power diagnostics and per-draw party primary min/max/means.

These are temporary research controls. Neither positive form is made the default
or written into the Sheet. Existing special-prior and preference-flow rules are
unchanged. The same mapping can be combined with regional preference/subregion
trials, but this comparison did not re-estimate their combined effects.

## Verification and remaining work

24 targeted tests pass, including positivity, initial order preservation,
zero/off identity, matching local derivative, balancing constraints and paired
statewide draws. All Current, linear 0.20 and linear 0.30 draw counts exactly
match the earlier matched-seed archives. UI checks pass for form selection,
metadata and stale-result hiding. Full suite: 119 pass, same pre-existing
legacy-workbook fixture failure. Hosted rebuild has not been independently checked.

No historical widths were fitted here. Next review the positive models' spatial
primary distributions against comparable past elections and candidate changes,
then fit/review party-specific widths. Keep the power-two bound explicit in that
review; do not choose it simply because it gives a preferred confidence level.
Alternative strength maps and field-specific preference regimes remain separate
research components, not solved by changing this transform.

Raw outputs and manifest: `positive_persistence_2026_10_28/`. Reproduce with
`python tools/trial_positive_persistence.py` in the project environment.
