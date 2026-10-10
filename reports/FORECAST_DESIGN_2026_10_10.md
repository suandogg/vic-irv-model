# October testing: lower-house forecast prototype

## Status

The first two stages are built: a shared simulation framework, editable
FORECAST PARAMS inputs and a separate Forecast view. It is an experimental
scenario-probability engine, not a calibrated election forecast. Main and the
reference deployment are untouched. The deterministic October calculator is
unchanged when no simulation shocks are supplied.

The app remains tethered to its selected preference trial, current primaries,
candidate/seat inputs and existing evidence. It does not fetch or average polls.

## How a draw works

1. Normalise the six input statewide primary shares. Add independent normal
   party errors using the six STATEWIDE_SD_*_PP settings, then project to a
   non-negative total of 100. This introduces compositional dependence but is
   not a fitted polling-error covariance model. These settings describe raw
   errors before the constraint, not marginal observed SDs after it.
2. Draw ON alpha, donor-matrix strength and default retirement/sophomore
   effects around the active calculator values. Bounds are implemented by
   clipping (not rejection sampling); means may shift near a boundary.
   Explicit seat-level effect overrides remain fixed.
3. Run the exact existing primary pipeline: PVI/ON strength, source geography,
   OTH depletion, seat/candidate adjustments, and LNP precollapse.
4. Add a shared party shock within each of the eight regions and independent
   seat/party residuals. Rake to restore each draw's underlying column totals
   and all seat totals; structural zero candidates remain zero. The equal-seat
   primary convention of the existing calculator is preserved, not silently
   replaced by turnout weighting. Large input SDs are stress tests, not precise
   post-balancing marginal SDs.
5. Draw origin/recipient log-weight deviations, shared across all seats and
   continuing fields. Scale these by source class: exact non-ON VEC field,
   federal-evidence blend, special prior, or generic/synthetic fallback. An
   additional ON-recipient deviation is shared within seat class. Multiply the
   final central flow weights by exp(deviation) and normalise once. Zero flows
   remain zero. This is a provisional correlated perturbation around the
   existing engine, not a new observed ballot-ranking model. Federal sample
   uncertainty is not yet fitted from sample sizes.
6. Run the existing parcel-aware IRV count, including forced 2PP outputs.
   Preference perturbations happen after central engine selection/transforms;
   the source matrices, evidence and ON_SPECIAL_SCENARIO_PRIORS rows are never
   rewritten. Special-prior uncertainty affects simulation copies only.

With every SD set to zero, simulation results reproduce the central calculator.
Any failed or incomplete draw stops the run; no partial probabilities are shown.
The seed is fixed and input changes invalidate displayed cached results.

## Outputs and interpretation

- Every party's win frequency in each of the 88 seats.
- Median winner margin above 50%, plus median forced ALP–LNP 2PP.
- Party median seat count, 25th/75th percentiles, editable lower/upper endpoints
  (5th/95th by default), and probability of 45 or more seats.
- Mutually exclusive single-party majority events and hung parliament.
- Separate overlapping LNP+ON joint-majority arithmetic; this is not a coalition
  agreement or minority-government formation forecast.
- Monte Carlo standard errors, full seat-count draws, statewide primary draws,
  and a run manifest. Zero simulated wins is not impossibility. Simulation
  error is not model error. Party medians/interval bounds need not sum to 88.

The default 200 draws are a preview. The approximate largest binomial Monte
Carlo standard error at 200 draws is 3.54 percentage points, before considering
any uncertainty about the model itself. Increasing draws reduces numerical
sampling noise, not model uncertainty. The app reports the actual sampled
primary means so boundary effects are visible.

## Sheet and app controls

Only the testing spreadsheet is changed:
https://docs.google.com/spreadsheets/d/1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968/edit

FORECAST PARAMS has Section, Parameter, Value, Units and Explanation columns.
Edit Value (column C), refresh Google Sheet inputs in October testing, select
Forecast (experimental), choose primaries and click Run lower-house forecast.
Inputs are validated for known keys, finite values, bounds and integer run/seed
settings. Missing/duplicate parameters produce errors rather than silent guesses.
The committed CSV is the fallback if Google sync is unavailable.

Settings do not yet include a date-based polling-drift schedule, fitted party
covariance, named-candidate uncertainty by seat, architecture-mixture weights,
Council simulation, or crossbench support probabilities. The local residual is
not a substitute for collecting candidate evidence when nominations are known.

## Next stages requiring review

1. Review SD assumptions together. Compare zero, narrower and wider uncertainty
   on Pakenham, Morwell, Pascoe Vale, Ashwood and Yan Yean. Do not choose SDs to
   obtain preferred ALP or ON seat totals.
2. Where feasible, evaluate historical election-time primary errors and held-out
   local residuals. Use Brier/log scores and interval coverage, not just winners.
   Historical 2022 tests cannot calibrate unprecedented Victorian ON strength.
3. Validate ON preference sensitivity with Victorian federal evidence and
   explicit stress scenarios. Separate sampling noise, cross-election transport
   error and alternative preference architectures; the first prototype does
   not claim to cover all these.
4. Review a polling covariance/temporal model and reasonable candidate-specific
   uncertainty. Only after those choices should probabilities be treated as a
   central forecast rather than exploratory scenario frequencies.
5. Connect Council counting to the same statewide draws, with separately
   reviewed upper-house preference and exhaustion uncertainty.
6. Add government formation only if explicit support assumptions are approved.

## Verification

Unit checks cover finite settings, simplex mass conservation, exact central
reproduction at zero uncertainty, no source-input mutation, region/local
rebalancing, reproducibility, all 88 seats allocated in each draw, per-seat
probabilities summing to 100%, and exhaustive government arithmetic. AppTest
covers the Forecast view, explicit run, tables/downloads and stale-result hiding.
The archived 200-draw run is an engineering smoke test, not calibration evidence.

The full regression suite passes 94 of 95 tests. The inherited legacy-workbook
fixture test fails on the unchanged historical helper (maximum ALP difference
0.0308076162 in vote-share units). That helper, its input CSV and fixture were
not edited by this feature. This is not described as a rounding difference.
The forecast-specific zero-uncertainty test separately verifies the active
calculator pipeline, rather than the older legacy-workbook fixture comparison.
The same fixture failure was reproduced in a separate archive of the unmodified
pre-feature commit, confirming it predates this change.

The new Sheet's values, validation rules, frozen panes and formatting were read
back through the Sheets connector. Native browser visual verification was not
available in this session.
