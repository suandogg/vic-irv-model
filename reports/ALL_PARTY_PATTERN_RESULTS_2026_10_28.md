# All-party concentration and regional preference patterns

## Status

Implemented opt-in October-testing prototypes for all-party vote concentration,
regional preferences and their combination, compatible with the upper-house /
subregion grouping selector. Current remains the default. Main, central
calculator and Sheet parameter values are unchanged. No new stable Sheet schema
has been introduced; the concentration stress width is a research app control.

This is a first integrated pattern-uncertainty prototype, not completion of all
components in the pattern design. Alternative evidence maps, candidate-field
uncertainty and field-specific preference regimes are not implemented here.

## Trial definitions

**Concentration:** for each draw and each of ALP/LNP/GRN/ON/IND/OTH, compute the
standardised log of positive support in that draw's production primary table.
Draw one election-wide coefficient per party, independently normal with SD 0.20,
and apply it as a log-weight tilt against that party's strength contrast. Positive
coefficients concentrate support, negative flatten it. Balance back to the
actual production table's party totals and seat totals, preserving structural
zeros. This uses the model's existing positive-support pattern, not independent
historical evidence or a wholly new spatial map. The coefficients are recorded.

For this trial only, fix ON alpha at its active central value, replacing its
existing uncertainty rather than stacking two concentration mechanisms. The
ordinary RNG draw is still consumed so the other original errors remain paired.
Other regional/local errors are retained, so the prototype adds all-party
structural uncertainty relative to baseline; its overlap with residual historical
error still requires calibration. Do not describe the total error budget as fitted.

0.20 is a provisional log-tilt stress width, **not 20 percentage points** or a
recommended empirical value. Users can change it from 0 to 1 in the research UI.
At zero the concentration component is off and current ON-alpha uncertainty is
retained. All-zero/off parity includes setting this additional research width
to zero, not only zeroing the original Sheet SDs.

**Regional preferences:** partition existing source-scaled origin/recipient
variance into 50% statewide, 25% geographic and 25% local. Reuse the sampled
origin/recipient factors across continuing fields. Every origin and recipient
category is covered; central source selection and pass-through stay unchanged.
No extra origin/recipient variance is added. The separate class-ON shock remains
explicitly unchanged, not absorbed into this first partition. New fractions
cannot be stacked with the older added/split local-preference mechanisms.

The geographic component uses the selected upper-house groups, sub-regions, or
their fixed-variance crossed blend. A grouping's existence is not evidence its
preference behaviours actually differ. These allocations are uncalibrated tests.
Source matrices and ON_SPECIAL_SCENARIO_PRIORS rows are unchanged; simulation
copies are perturbed according to the existing uncertainty mechanism.

## Experiment

Saved central scenario ALP 24.6 / LNP 29.1 / GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5.
Committed model/mapping snapshot, corrected exact-field VEC trial, not a live
poll or Sheet-settings snapshot. Three seeds, 100 draws each per profile: 300
pooled draws per profile and 1,500 simulated elections overall. Independent
additional RNG streams retain paired statewide targets and other original errors.

| Trial | Seats at least 98% | Seats winning all 300 draws |
|---|---:|---:|
| Current | 40 | 29 |
| Concentration only | 26 | 11 |
| Regional preferences only (upper regions) | 39 | 30 |
| Both (upper regions) | 26 | 11 |
| Both (sub-regions) | 26 | 9 |

Near-certainty counts over individual seeds were concentration 29/24/29,
both-upper 27/26/27 and both-subregion 26/26/28. The threshold is sensitive to a
few draws. At 300 draws, maximum binomial MC standard error is about 2.89 pp;
uncertainty about the model is additional. No sampled losses is not impossibility.

## Five demonstration seats: fixed-party win frequency (%)

| Seat (party) | Current | Concentration | Regional preferences | Both upper | Both subregions |
|---|---:|---:|---:|---:|---:|
| Pakenham (LNP) | 70.0 | 65.3 | 71.3 | 64.7 | 67.3 |
| Morwell (ON) | 71.7 | 64.0 | 71.3 | 66.3 | 63.7 |
| Pascoe Vale (ALP) | 61.0 | 59.0 | 61.3 | 59.0 | 57.3 |
| Ashwood (LNP) | 79.3 | 73.0 | 79.0 | 72.7 | 75.3 |
| Yan Yean (ON) | 51.7 | 53.0 | 52.0 | 51.7 | 50.7 |

Some baseline near-certain seats are more sensitive. Combined subregion trial
versus Current: Prahran GRN 79.0 versus 100; Richmond GRN 89.0 versus 100;
Glen Waverley LNP 90.3 versus 98.7; Ivanhoe ALP 93.0 versus 98.7. These are
assumption-sensitive preview frequencies, not validated revised probabilities.

## Party seat ranges

5th–95th percentiles, median in brackets:

| Party | Current | Both upper | Both subregions |
|---|---|---|---|
| ALP | 17–41 (28) | 17–41 (29) | 17–41 (29) |
| LNP | 31–50 (39) | 30–51 (39) | 30–51 (40) |
| GRN | 5–8 (5) | 2–9 (5) | 2–9 (5) |
| ON | 4–26 (13) | 2–26 (12) | 2–25 (12) |

Lower individual-seat certainty need not produce much wider statewide ranges.
The broadened Greens range is particularly worth reviewing: varying concentration
can make a fixed statewide primary much less reliably translate into strongholds.
Nonlinear balancing/counting can shift means and medians despite zero-centred
latent coefficients. No requirement forces probabilities toward 50 or preserves
the original seat-count median.

## App access and reproducibility

Forecast → Current forecast settings and methodology → Structural uncertainty
trial: Regional preference patterns, All-party concentration patterns, or
Concentration + regional preferences. Choose Geographic uncertainty grouping
independently. Concentration width is explicitly visible/editable where relevant.
Current stays default and central calculator output remains unchanged.

Narrower/wider comparisons also scale the concentration width while leaving
variance fractions/grouping fixed. Input/width/trial/mapping changes hide stale
results. Manifests record flags and mapping; concentration coefficients can be
downloaded. The regional/local preference factors can be reconstructed from
seed, source version and group ordering. Special-prior source rows are never written.

## Verification

- 20 targeted tests pass: combined reproducibility, paired national targets,
  immutable inputs, zero/off identity, conserved primary totals/structural zeros,
  regional shock reuse, subregion validation and conflicting variance-model guards.
- All 300 baseline seat-count draws match the prior archived baseline exactly.
- UI smoke checks pass for combined patterns/subregions, coefficient controls and
  correctly scaled narrower/wider comparisons.
- Full suite: 115 pass, same pre-existing legacy-workbook fixture failure
  (ALP difference 0.030807616248605896). Hosted rebuild not independently checked.

## Recommendation

Keep these opt-in. The concentration trial addresses an uncertainty source that
the previous local-noise adjustments missed, but choosing its width because it
reduces the 98% count would not establish accuracy. Review stronghold dispersion
and candidate situations, particularly Greens contests, before any promotion.

Next: test a range of party-specific concentration widths against realistic
historical spatial residuals/transport assumptions; then expose settled controls
in the testing Sheet. Audit consequential field-specific preference alternatives
and alternative strength maps separately. Retain the distinction between sampling
uncertainty, cross-election transport error and model-choice uncertainty. Do not
reactivate rejected preference extrapolation or rewrite priors under this label.

Raw output: `all_party_patterns_2026_10_28/`. Reproduce with
`python tools/trial_all_party_patterns.py` in the project environment.
