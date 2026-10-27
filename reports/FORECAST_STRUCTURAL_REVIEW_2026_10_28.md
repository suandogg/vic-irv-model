# Local preferences and heavy-tail trials — 28 October 2026

## Decision summary

Built five opt-in methods in October testing and tested each with three seeds.
Current remains the default; no Sheet settings, central preference rows, ordinary
calculator or Main changes. These are controlled sensitivity trials, not fitted
uncertainty. They make a modest difference, not a solution to forecast certainty.

## Design

Saved scenario ALP 24.6 / LNP 29.1 / GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5;
committed input snapshot and corrected exact-field VEC trial. Not a current poll
average or live-Sheet snapshot. Seeds 20261010/11/12, 100 draws each, pooled to
300 per method (1,500 simulated elections in total).

| Trial | Definition |
|---|---|
| Current | Existing normal local primary errors and shared preference errors |
| Preference split | Replace half of shared origin/recipient variance with seat-specific variance; retain marginal variance before log-weight transformation |
| Preference added | Retain shared errors and add an equally scaled independent local component; origin/recipient variance doubles |
| Heavy tails t5 | Variance-matched Student t with 5 degrees of freedom for local primary errors only |
| Added preferences + t5 | Combine added local preferences with the t5 local primary errors |

Shared seat-class ON preference errors remain unchanged. Local preference shocks
are source-scaled by the same provenance hierarchy as existing shocks and fixed
across continuing fields for each seat/origin/recipient in a draw. This tests
local preference heterogeneity without changing central preference rules. It
does not provide newly calibrated evidence weights or a new ballot-ranking model.
Special-prior source rows remain untouched; simulation copies can vary as before.

For t5, multiply the baseline local normal error by sqrt(3 / Q), independently
Q ~ chi-square(5). This retains the same theoretical variance before positivity
constraints and raking. It changes neither statewide nor regional error shape.
Separate random streams keep national targets and parameter draws paired across
trials; the ordinary RNG stream is not consumed by the extra local components.
Final post-balancing marginal variances are not guaranteed identical.

## Pooled results

| Trial | Seats at least 98% | Seats winning all 300 draws |
|---|---:|---:|
| Current | 40 | 29 |
| Preference split | 40 | 28 |
| Preference added | 39 | 24 |
| Heavy tails t5 | 40 | 26 |
| Added preferences + t5 | 36 | 22 |

Do not compare all-draw counts directly with the previous 200-draw audit: more
draws alone reveal more rare losses. These rows all use the same 300 draws per
method. Even at 300, maximum binomial MC standard error is about 2.89 pp.
The 98% threshold is especially sensitive to a few simulated outcomes.

Across the three individual seeds, counts at least 98% were Current 40/40/42;
split 40/41/41; added 38/38/39; t5 40/39/40; combined 36/37/38. Pooled threshold
counts need not equal averages of the per-seed counts. This is a stability check,
not evidence of historical probability calibration.

Party seat ranges remain broadly similar. Current ALP 5th–95th range is 17–41,
LNP 31–50, ON 4–26. Combined is ALP 17–41, LNP 30–50, ON 3–26. This illustrates
that reducing individual-seat certainty does not necessarily produce dramatically
wider statewide seat totals.

## Five demonstration seats: win probability for a fixed party

| Seat (party) | Current | Split | Added | t5 | Combined |
|---|---:|---:|---:|---:|---:|
| Pakenham (LNP) | 70.0 | 69.0 | 67.7 | 69.7 | 67.3 |
| Morwell (ON) | 71.7 | 71.3 | 71.3 | 70.3 | 71.7 |
| Pascoe Vale (ALP) | 61.0 | 59.0 | 56.3 | 61.7 | 56.3 |
| Ashwood (LNP) | 79.3 | 79.7 | 79.3 | 77.7 | 79.3 |
| Yan Yean (ON) | 51.7 | 52.7 | 51.7 | 53.0 | 51.0 |

Small differences must be interpreted with simulation noise in mind. Heavier
tails at fixed variance also concentrate more probability near the centre;
they are not a uniform probability softener. Nonlinear preference/elimination
and balancing effects mean individual win probabilities need not move toward 50.

## Access in the app

Forecast → Current forecast settings and methodology → Structural uncertainty
trial (unvalidated). Choose a method and rerun. Current remains selected by
default. This is a temporary research selector, not a new Sheet parameter;
settled definitions can be made Sheet-controlled after review. Changing the
method hides stale results. Downloads record the experimental flags, and the
narrower/wider comparison keeps the selected method rather than reverting to
Current. Existing Sheet SDs still control the scales.

## Verification

- Ten forecast tests pass, including all-zero-SD parity, repeated-seed
  reproducibility, paired national targets, t5 balancing/structural zeros and
  variance experiment validation.
- Current seed 20261010 first 100 seat-count draws exactly match the original
  archived baseline. No change to default forecast draws.
- UI smoke test passes for default isolation, switching trial, stale-result
  hiding and running the combined method.
- Full suite: 105 pass, same pre-existing legacy-workbook fixture failure
  (ALP difference 0.030807616248605896). Not caused or repaired here.
- A 500,000-sample numerical check gives normal SD 0.9984 versus t5 SD 0.9978;
  frequencies beyond three input SDs are 0.284% and 1.163%, respectively. This
  verifies the distributional construction, not election calibration.
- Hosted rebuild/visual presentation has not been independently verified here.

## Recommendation and remaining direction

Do not adopt the combined method merely because 36 looks preferable to 40.
Keep it an opt-in stress test. The variance-preserving split and t5 tests show
that these changes alone do not meaningfully resolve the broader concern.

Next focus on **coherent ON-geography alternatives and prediction-error
calibration**, rather than further arbitrary noise inflation. A local error
around one assumed ON pattern cannot cover a wrong underlying pattern. Likewise,
systematic election-day/polling misses need an explicit correlated variance budget,
not another unaccounted-for statewide error added on top of current SDs.

Historical paired results and boundary/candidate mappings are still needed to
fit party-specific regional/local errors. The current PVI input file alone is
not suitable evidence. Candidate-field uncertainty, evidence-specific transport
error and architecture scenarios remain outside these trials. No automatic
mixture weights, polling-time model or Council probabilities have been added.

Raw per-seed draws, party summaries, events, seat probabilities and reproduction
settings are in `forecast_structural_2026_10_28/`. Reproduce with
`python tools/trial_forecast_structural_uncertainty.py` in the project environment.
