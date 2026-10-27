# Forecast certainty audit — 28 October 2026

## Scope

First stage of the approved uncertainty review: diagnose near-certain seats and
isolate the effects of existing uncertainty controls before introducing new
distributions. October testing only; no ordinary PARAMS, FORECAST PARAMS, live
Sheet, central calculator or Main changes.

Inputs are the committed snapshot, corrected exact-field VEC preference trial,
ALP 24.6 / LNP 29.1 / GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5. This is the user's
earlier saved scenario, not an October 28 poll average or current live Sheet
snapshot. All trials use 200 draws and seed 20261010. Random numbers remain
paired because these trials scale existing positive SDs without changing the
draw sequence. No claim of historical calibration is made.

## Results

| Trial | Seats at least 98% | Seats winning every draw |
|---|---:|---:|
| Current committed settings | 40 | 31 |
| Local primary SD 2.5 (from 1.5) | 34 | 27 |
| Local primary SD 3.0 | 33 | 25 |
| All preference SDs ×1.5 | 37 | 28 |
| All statewide primary SDs ×1.5 | 34 | 21 |
| Local SD 2.5 plus preference SDs ×1.5 | 33 | 24 |

33 seats remain at least 98% across all six trials. That is not proof those
seats are well calibrated: structural uncertainty has not yet been added.
Nor should the objective be to force every safe seat below 98%.

Some baseline probabilities worth auditing more closely:

| Seat | Leading party | Current win % | Central winning margin above 50 (pp) | Combined trial win % |
|---|---|---:|---:|---:|
| Ivanhoe | ALP | 99.5 | 4.85 | 95.5 |
| Glen Waverley | LNP | 99.5 | 4.92 | 95.5 |
| Oakleigh | ALP | 98.5 | 5.02 | 95.5 |
| Broadmeadows | ALP | 98.5 | 5.47 | 96.0 |
| Bundoora | ALP | 99.5 | 5.57 | 97.0 |
| Bass | LNP | 98.0 | 6.17 | 90.0 |
| Prahran | GRN | 100.0 | 6.56 | 98.5 |

The central winner's margin is share above 50, not the full winner–runner-up gap.
Holder-level evidence labels, central rounds and all 88-seat diagnostics are
included in `forecast_certainty_2026_10_28/`. Holder labels do not establish the
provenance of every retained parcel origin; that requires the detailed engine
trace. In particular, an internal `full AEC row` label must not be assumed to
mean contemporary federal ON evidence without inspecting its loader/provenance.

## Five demonstration seats

Each cell is leading party and its win percentage; probabilities for other
parties are available in the ordinary forecast outputs.

| Seat | Current | Local 2.5 | Local 3.0 | Preferences ×1.5 | Statewide ×1.5 | Combined |
|---|---|---|---|---|---|---|
| Pakenham | LNP 71 | LNP 65.5 | LNP 63 | LNP 64.5 | LNP 65 | LNP 61 |
| Morwell | ON 72 | ON 76 | ON 77 | ON 71.5 | ON 68 | ON 75 |
| Pascoe Vale | ALP 62 | ALP 59.5 | ALP 55 | ALP 59.5 | ALP 60 | ALP 56.5 |
| Ashwood | LNP 81.5 | LNP 78.5 | LNP 77 | LNP 81.5 | LNP 76.5 | LNP 79 |
| Yan Yean | ON 57 | ON 51.5 | ON 49.5 | ON 50.5 | ON 50 | ON 47.5 |

Morwell illustrates why increasing primary SD does not uniformly push every
probability toward 50%. Nonlinear final-field/elimination effects and balancing
can change which outcomes benefit. Finite-sample variation also matters. These
differences should not be interpreted as proof one trial is more accurate.

## What was implemented

Forecast → Seat probabilities now includes an uncertainty-diagnostics expander:

- Count/list of seats whose leading simulated win frequency is at least 98%.
- Leading party and win frequency, with a Wilson 95% interval for Monte Carlo
  precision. This avoids interpreting a zero estimated standard error at 100%
  as proof of certainty. It is not a model-error interval.
- Realised seat-level ALP and ON primary SDs after balancing.
- Forced ALP–LNP 2PP SD and 5th/95th percentiles. These do not describe every
  possible actual final pair.
- Parties with zero projected primary support throughout the run, and an
  all-seat diagnostic CSV download.

These diagnostics record existing draws and do not consume additional random
numbers. Source matrices, special priors and forecast probability logic are
unchanged. Tests: eight forecast tests and UI smoke test pass; full suite has
103 passes and the same pre-existing legacy-workbook comparison failure.

## Recommendation and remaining work

Keep defaults provisional and unchanged for now. Increasing local SD further
has diminishing returns in this scenario and cannot represent errors outside
the current model structure. These results supersede treating local SD 2.5 as
a sufficient answer to the overconfidence concern.

Next controlled experiments, not yet implemented:

1. **Local preference residual:** supplement shared errors with a seat-specific
   component. Specify its relationship to evidence strength and existing shared
   variance so that errors are not accidentally double-counted. Include full
   parcel-level provenance where consequential.
2. **Heavy-tailed local primary errors:** compare a variance-matched heavy-tail
   distribution with the current normal errors. Simply making its SD larger
   would confound tail shape and ordinary spread. Compare central behaviour,
   extreme seat swings and probability stability over multiple seeds.
3. **ON geography scenarios:** allow coherent alternative geographic patterns,
   not only random deviations around one pattern. Keep alternative model
   results labelled separately before assigning mixture weights.
4. **Election-day movement/common polling error:** define these separately from
   current-support uncertainty. Do not add a second statewide error term without
   a clear variance budget and election horizon.
5. **Historical regional/local residual calibration:** locate/build paired
   boundary-comparable primary results and candidate-presence mappings before
   fitting party/seat-specific widths. No paired 2018–2022 dataset was located
   in the current forecast checkout during this stage; current input files are
   PVI/strength inputs, not sufficient raw observations for this fit. Historical
   major-party results cannot calibrate today's ON geography on their own.

Parameterise new uncertainty components only after their definitions and tests
are clear; then expose them in the testing Sheet. Do not silently alter special
prior source rows, reinstate rejected preference extrapolation methods or change
production preference architecture under the label of uncertainty.

No live AE Forecast / Swing Is On range matching was performed here. The goal
is defensible coverage, not matching another model's numbers or a preferred
party's probability. Council probabilities remain deferred.
