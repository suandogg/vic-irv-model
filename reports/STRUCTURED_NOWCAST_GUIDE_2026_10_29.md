# Structured nowcast development mode

## Status

An opt-in configuration for October testing, not a calibrated replacement default. The current calculator, Main app, existing forecast default and ON special-prior source rows remain unchanged. This stage makes the approved framework usable while exposing the assumptions still unresolved.

Select **Forecast → Current forecast settings and methodology → Structural uncertainty trial → Structured nowcast (development)**. Start with **Upper-house regions (current)**: the fitted historical regional component was not estimated on the user's subregions. A blend remains selectable but is an explicit extra assumption.

Statewide primary inputs still come from the Streamlit controls. The new tabs control the uncertainty around those inputs. Existing FORECAST PARAMS continues to control simulations, seed, statewide error and existing preference uncertainty.

## Testing workbook inputs

The three new tabs are in the testing workbook `1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968`. Existing workbook tabs were not overwritten.

### NOWCAST BUDGET

Edit the SD column. Component meanings:

- `local_sd_pp`: party-specific uncertainty in district primary leans.
- `region_sd_pp`: party-specific geographic uncertainty shared across districts in the selected group.
- `class_sd_pp`: shared seat-class uncertainty, initially zero to avoid an unjustified second geographic term.
- `transport_log_sd`: additional uncertainty about applying a preference source to the present field. Sources are vec/federal/special/generic. These start at zero because the new transport component has not yet been estimated or elicited. Existing source SDs in FORECAST PARAMS remain active.
- `tail_df`: zero selects a normal distribution. A positive value must exceed two. This shape is not historically fitted.

Historical-proxy starting values:

| Party | Local SD | Regional SD |
|---|---:|---:|
| ALP | 3.50 pp | 1.31 pp |
| LNP | 3.24 pp | 1.89 pp |
| GRN | 1.79 pp | 0.41 pp |

ON/IND/OTH retain the previously inspected 2.5-pp local and 0.75-pp geographic assumptions, labelled INHERITED. They are not estimated from the 2014/2018 panel. Ordinary ON-alpha/donor uncertainty remains active. The old all-party concentration experiment is not stacked on this mode.

This new budget replaces REGION_PRIMARY_SD_PP and SEAT_PRIMARY_SD_PP in structured mode. Do not increase both sets expecting independent effects. Narrower/wider comparison scales all applicable new and old SDs consistently; it does not scale correlations or context multipliers.

### NOWCAST CORRELATION

Six-party symmetric correlation matrix. Diagonal entries must equal one; the matrix must be positive semidefinite. Both halves must be edited consistently. Invalid matrices stop the forecast instead of being silently repaired.

The ALP/LNP/GRN block uses regularised historical within-region error correlations. Other off-diagonal values start at zero, an assumption of no additional raw-factor correlation, not a finding of political independence. Nonnegative vote constraints and statewide balancing still induce relationships in realised shares.

### NOWCAST CONTEXTS

One row for each of the 88 districts. Every row starts UNREVIEWED, Enabled=FALSE, LocalMultiplier=1 and candidate-strength SDs=0.

- `LocalMultiplier` changes that seat's local lean SD for all six categories. Two doubles local SD; it does not double every uncertainty component.
- The six party SD columns add zero-centred candidate-strength uncertainty, in primary percentage points, for the existing field. Five means a 5-pp input SD—not a five-point bonus or a 5% chance of winning.
- Set ReviewStatus=REVIEWED, explain the prospective context in Notes, and check Enabled to activate a row. A checked but unreviewed/undocumented row is rejected.
- These inputs do not simulate a new candidate appearing or disappearing. Do not use an aggregate IND/OTH row as if it automatically represents a named challenger.

These rows are deliberately not filled from historical outcomes or labelled future challengers without evidence. Retirement/sophomore effects in LOWER_SEAT_ADJUSTMENTS remain separate central effects. Avoid assigning the same unexplained candidate variation twice.

Refresh Google Sheet inputs after editing. Local CSV copies provide fallback when sync is unavailable. The app's source banner still needs to be checked; fallback is not proof that live Sheet changes were downloaded.

## Independent ON signal work

`reports/on_independent_signals_2026_10_29/regional_signals.csv` compares the existing federal-derived ON strength signal (alpha 0.6, before calibration/donor adjustments) with the 2022 Upper House regional ON lean. Both are normalised to equal-region mean one for a like-for-like signal comparison, not a new statewide vote model.

The signals correlate about 0.897 across eight regions, but differ in concentration. Relative to the federal-derived signal, the Upper House signal is stronger in Eastern/Northern Victoria and weaker in Northern/Southern Metro. The comparison is genuinely independent evidence of geographic disagreement, unlike the model-generated scenario-grid lean ranges.

The comparison uses committed input tables, not a freshly rebuilt SA1 allocation. Different years, chambers, campaign conditions and candidate fields limit transferability. No mixture weight, probability distribution, district-level state ON map or active forecast adjustment has been assigned from this comparison.

## Limits and next work

The current mode is a working partial configuration, not completion of exceptional candidate-field uncertainty or ON structural uncertainty. The historical core estimates one four-year transition on a subset defined partly by realised independent results; they are not validated current-error coverage. Do not optimise settings to force nearly every seat below 95%.

Next specify prospective local contexts and source-applicability ranges, then compare the single coherent configuration across all 88 districts and all six parties. Assess which outcomes become possible and why, not just whether average leading-party probability falls. Council probabilities remain out of scope.

## Verification

41 targeted engine/loader/pattern tests pass, plus a Streamlit app smoke test for selecting the new mode, running it, scaling uncertainty and hiding stale output. Native Sheet readback confirms 24 budget rows including header, a 7×7 correlation table and 89 context rows including header, with all 88 contexts disabled and UNREVIEWED. All three tabs were visually inspected in Google Sheets. Reproducibility exports include the active normalised structured configuration.
