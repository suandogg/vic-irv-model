# Subregion forecast trials — 28 October 2026

## Status

Implemented forecast-only geographic grouping selection and read-only SUB-REGIONS
sync support in October testing. Default is unchanged: upper-house-region primary
errors. No Sheet values, memberships, central calculator, Main or Council changes.
Regional preference patterns are not part of this implementation.

Settings expander now offers Upper-house regions (current), Blend upper-house and
sub-regions, and Sub-regions only. Blend uses independent upper/subgroup shocks,
each multiplied by sqrt(0.5); total geographic variance before balancing stays
REGION_PRIMARY_SD_PP squared. Existing local SD stays unchanged. The group
choice combines with the existing structural uncertainty selector.

The strict loader checks complete canonical seat coverage, duplicate/blank
memberships and extra seats. Source labels, mapping hash/invalidation and mapping
in the JSON run manifest are included. The mapping is loaded only for opt-in
subregion modes. A synced SUB-REGIONS.csv takes precedence; without it the
committed 28 October JSON snapshot is explicitly labelled. A malformed present
CSV errors rather than falling back. Refresh Google Sheet inputs to fetch edits.
The hosted sync/rebuild has not been independently verified here.

## Comparison

Three seeds (20261010/11/12), 100 draws each per trial: 300 pooled draws per
method, 1,200 simulated elections in total. Saved scenario ALP 24.6, LNP 29.1,
GRN 13.3, ON 22, IND 5.5, OTH 5.5; committed model inputs and mapping snapshot,
corrected exact-field VEC trial. Not a live poll or Sheet-settings snapshot.

| Trial | Seats with at least 98% wins | Seats winning all 300 draws |
|---|---:|---:|
| Upper-house only | 40 | 29 |
| Equal-variance blend | 40 | 29 |
| Sub-regions only | 38 | 29 |
| Sub-regions + added local preferences + t5 | 37 | 23 |

The earlier upper-house grouping plus added local preferences/t5 gave 36 seats
at least 98%, not 37. Subregions do not uniformly soften probabilities or prove
more accurate. The 98% cutoff is sensitive to a small number of sampled losses.
300 draws still have maximum binomial Monte Carlo standard error about 2.89 pp;
small changes should not be treated as calibration improvements.

## Five demonstration seats: fixed-party win probabilities

| Seat (party) | Upper only | Blend | Subregions | Subregions + structural trial |
|---|---:|---:|---:|---:|
| Pakenham (LNP) | 70.0 | 70.0 | 69.3 | 69.7 |
| Morwell (ON) | 71.7 | 72.3 | 72.3 | 70.7 |
| Pascoe Vale (ALP) | 61.0 | 58.7 | 57.7 | 55.7 |
| Ashwood (LNP) | 79.3 | 78.7 | 79.3 | 79.0 |
| Yan Yean (ON) | 51.7 | 52.0 | 52.7 | 52.7 |

Party ranges are also similar. Baseline 5th–95th ranges ALP 17–41, LNP 31–50,
ON 4–26; subregions alone ALP 17–41, LNP 31–50, ON 3–25. Combining the structural
trial gives ALP 16–41, LNP 31–50, ON 4–26.

## Interpretation

This tests a different spatial **covariance structure** at an unchanged input
geographic-error scale. Smaller groups may improve the realism of shared local
movement, but they do not by themselves represent an alternative ON strength
map, stronger party-specific geographic errors, or uncertain preference regimes.
Post-balancing variance can differ from input variance and between groupings.
No empirical within-group covariance calibration is claimed by this experiment.

Retain the grouping as opt-in. Next implement and test all-party concentration /
alternative-pattern factors and regional preference uncertainty with explicit
variance budgets; do not stack another full regional error on top. Calibrate
group relationships where comparable historical evidence supports it. Keep
membership confidence labels as qualitative metadata, not arbitrary numeric SDs.

## Verification

- 18 targeted forecast/pattern/subregion tests pass.
- Full suite: 113 pass, one unchanged pre-existing legacy-workbook fixture
  failure (ALP difference 0.030807616248605896).
- Zero/off parity, paired statewide targets, reproducibility, totals and
  structural zeros checked. Default seed first 100 draws exactly match the
  previous archived baseline.
- UI smoke test passes for running the subregion mode, mapping storage and
  stale-result hiding when the geographic selector changes.

Raw outputs and reproduction manifest: `forecast_subregions_2026_10_28/`.
Run `python tools/trial_forecast_subregions.py` in the project environment.
