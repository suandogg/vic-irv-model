# Party-specific concentration width review — 28 October 2026

## Scope and status

Added per-party research concentration controls to October testing. Current stays
default; no Main, central calculator or Sheet values change. These controls are
not calibrated estimates or a recommended production preset. They allow the
same model component to be varied separately for each of the six categories.

Eleven profiles, two seeds (20261010/11), 100 draws per seed: 200 draws per profile,
2,200 simulated elections overall. Saved central scenario ALP 24.6 / LNP 29.1 /
GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5; committed inputs, corrected exact-field VEC
trial, upper-house regional grouping, regional-preference trial off. Not a live
polling forecast or current Sheet snapshot. Do not compare threshold counts
unqualified with earlier 300-draw profiles.

## One-party-at-a-time effects

Each party-only profile has log-tilt SD 0.20 for that party and zero for other
concentration factors; all ordinary uncertainty remains in place. Positive ON
concentration width replaces alpha uncertainty; at zero the original alpha
uncertainty remains. Changing another party does not inadvertently freeze ON.

| Profile | Average leading-party win % | Seats at least 98% |
|---|---:|---:|
| Current | 85.01 | 40 |
| ALP only 0.20 | 84.92 | 38 |
| LNP only 0.20 | 83.92 | 32 |
| GRN only 0.20 | 84.00 | 35 |
| ON only 0.20 | 84.05 | 37 |
| IND only 0.20 | 84.82 | 39 |
| OTH only 0.20 | 85.02 | 40 |

At this test width, LNP and Greens assumptions have substantial effects, not just
ON. OTH's small effect on this metric does not show its flows or votes are
irrelevant: the trial changes spatial concentration, not every aspect of OTH.
Compositional balancing means changing one party's pattern can affect other
parties' seat shares/results, even while every party's statewide total is held.

The differences are sensitivities, not independent additive contributions or
evidence that one party deserves a particular uncertainty width.

## Combined widths

| Profile | Average leading-party win % | Median leading-party win % | Seats at least 98% | All 200 wins |
|---|---:|---:|---:|---:|
| Current | 85.01 | 94.25 | 40 | 30 |
| Uniform 0.10 | 84.23 | 92.75 | 37 | 23 |
| Uniform 0.20 | 81.77 | 90.25 | 24 | 11 |
| Uniform 0.30 | 78.57 | 86.75 | 12 | 2 |
| Differentiated stress | 82.10 | 90.25 | 30 | 17 |

Differentiated widths are ALP/LNP 0.10, GRN 0.15, ON 0.30, IND/OTH 0.20. These
were declared stress values, not fitted or selected by optimising output certainty.
They are not a recommended preset pending evidence review.

For each profile, select its own highest-probability party in each seat, then
average those 88 probabilities. This is not forecast accuracy. The fixed baseline
favourite's average probability is also recorded in raw summary: 85.01% current,
81.64% uniform 0.20, 78.28% uniform 0.30, 82.02% differentiated. Favourite changes
affect two seats in each of those wider profiles, so the main reduction is not
merely a switch in which party is named favourite.

The uniform 0.20 >=98% count is 24 here versus 26 in the earlier 300-draw run.
The matched first two seeds reproduce the earlier counts exactly; this is a
different sample size, not an implementation change. Maximum binomial MC standard
error at 200 draws is approximately 3.54 pp. The 98% cutoff is particularly
sensitive to a few sampled losses; small profile differences need more draws.

## Party seat ranges

5th–95th percentiles, median in brackets:

| Party | Current | Uniform 0.20 | Uniform 0.30 | Differentiated |
|---|---|---|---|---|
| ALP | 17–41 (28) | 17–41 (29) | 16–41 (30) | 17–40 (29) |
| LNP | 31–49 (40) | 30–51 (40) | 28–54 (39) | 28–51 (40) |
| GRN | 5–8 (5) | 2–9 (5) | 0–9 (5) | 3–8 (5) |
| ON | 4–26 (13) | 1–26 (12) | 0–28 (11) | 1–28 (12) |

The Greens' lower tail, particularly at uniform 0.30, needs scrutiny. These
outputs demonstrate how much the assumed spatial persistence matters, not that
such outcomes have the reported real-world probability. Zero-centred pattern
coefficients can shift mean/median seat counts through nonlinear balancing and
IRV counts; the central deterministic result itself is unchanged.

## Five demonstration seats: fixed-party win frequencies

| Seat (party) | Current | Uniform 0.20 | Uniform 0.30 | Differentiated |
|---|---:|---:|---:|---:|
| Pakenham (LNP) | 69.0 | 63.5 | 61.0 | 65.5 |
| Morwell (ON) | 70.0 | 62.5 | 63.5 | 60.0 |
| Pascoe Vale (ALP) | 64.5 | 63.0 | 60.0 | 63.5 |
| Ashwood (LNP) | 82.0 | 76.5 | 71.5 | 80.0 |
| Yan Yean (ON) | 52.5 | 52.5 | 50.5 | 51.0 |

Not every wider trial softens every probability: elimination-order changes,
balancing and finite sampling can produce non-monotonic effects.

## App controls and safeguards

Select All-party concentration patterns or Concentration + regional preferences
in the forecast settings expander, then tick Use party-specific concentration
widths (research). Six controls override the common width. Existing Sheet SDs
still control other components. Changing widths hides stale results; manifests
and coefficient downloads retain the chosen values. Narrower/wider comparisons
scale both the common and override widths.

Internally `concentration_by_party` is optional. Missing entries inherit the
common width, or zero when no common width is supplied. Unknown party codes,
nonfinite/negative values and values over 1 fail validation. Ordinary no-trial
and all-zero-width runs are unchanged. No special-prior rows or central
preference rules are edited.

## Verification

- 21 targeted tests pass, including scalar/uniform-vector equality, one-party
  coefficient isolation, immutable inputs, totals, pairing and invalid settings.
- Baseline and uniform 0.20 draws exactly reproduce all earlier matched seed
  results. This change adds configurability without changing existing modes.
- UI smoke test passes for per-party overrides, manifests and correctly scaled
  narrower/wider comparisons.
- Full suite: 116 pass, same pre-existing legacy-workbook fixture failure
  (ALP difference 0.030807616248605896). Hosted rebuild not independently verified.

## Recommendation

Do not promote uniform 0.30 because it produces fewer high-confidence seats.
Do not promote the differentiated case merely because ON intuitively seems
less predictable. Use the controls to inspect plausible spatial outcomes and
fit/review party-specific concentration variation against comparable historical
data, with a separate transport allowance for ON. Large shifts in Greens and
LNP strongholds need evidence review as well as ON geography.

The next substantive refinement should be checking that spatial-pattern evidence
and consequential field-specific preference alternatives, not another round of
arbitrary widening. Stable controls can then be exposed in a versioned testing
Sheet schema. No numerical default is changed by this report.

Raw outputs: `party_widths_2026_10_28/`; reproduce with
`python tools/trial_party_concentration_widths.py` in the project environment.
