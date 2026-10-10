# Forecast uncertainty: first sensitivity review

October testing only. Main unchanged. Central primaries: ALP 24.6, LNP 29.1,
GRN 13.3, ON 22, IND 5.5, OTH 5.5. Corrected exact-field VEC trial;
committed model-input snapshot, not a full live-Sheet snapshot. FORECAST PARAMS
A1:E22 was checked against the live testing Sheet on 10 October and matches the
committed settings. No Sheet values were changed.

Each profile uses 200 draws and seed 20261010. Narrower halves every SD; wider
multiplies every SD by 1.5. Central model parameters, percentile endpoints,
architecture and primaries stay fixed. Common random numbers make comparisons
paired. This is sensitivity analysis, not evidence any profile is calibrated.

## Seat-count ranges (5th–95th percentile; median in brackets)

| Party | Narrower | Current | Wider |
|---|---|---|---|
| ALP | 21–35 (29) | 17–41 (29) | 12–44 (29) |
| LNP | 36–46 (40) | 32–49 (40) | 28–53 (39) |
| GRN | 5–6 (5) | 5–8 (5) | 4–9 (6) |
| ON | 7–20 (13) | 4–24 (13) | 1–28 (12) |

## Parliamentary arithmetic (% of draws)

| Event | Narrower | Current | Wider |
|---|---:|---:|---:|
| ALP majority | 0 | 0.5 | 5 |
| LNP majority | 11.5 | 22.5 | 27 |
| ALP minority: GRN or IND support assumed | 0 | 8 | 10.5 |
| Deadlock: ALP+GRN 44; LNP+ON 44 | 0 | 2 | 2 |
| LNP+ON reach 45, neither alone | 88.5 | 64.5 | 51.5 |

Support routes are assumptions, not predictions of negotiations. Minority and
deadlock rows overlap the hung-parliament total. Zero sampled occurrences is
not impossibility. At 200 draws the maximum binomial MC standard error is
3.54 percentage points; model uncertainty is additional.

## Five demonstration seats (% ALP / LNP / GRN / ON)

| Seat | Narrower | Current | Wider |
|---|---|---|---|
| Pakenham | 0 / 93.5 / 0 / 6.5 | 0 / 71 / 0 / 29 | 0 / 60.5 / 0 / 39.5 |
| Morwell | 0 / 18 / 0 / 82 | 0 / 28 / 0 / 72 | 0 / 30 / 0 / 70 |
| Pascoe Vale | 82.5 / 0 / 17.5 / 0 | 62 / 0 / 38 / 0 | 56.5 / 0 / 42.5 / 1 |
| Ashwood | 2.5 / 97.5 / 0 / 0 | 18.5 / 81.5 / 0 / 0 | 25 / 75 / 0 / 0 |
| Yan Yean | 0 / 31 / 0 / 69 | 6.5 / 36.5 / 0 / 57 | 18.5 / 38.5 / 0 / 43 |

## Interpretation and next decision

Medians are relatively stable; tails and marginal-seat probabilities are not.
Do not choose narrower settings just to make outputs look more confident, or
wider ones to increase a party's chance. Keep the current values provisional.
Next isolate statewide polling uncertainty, local/geographic uncertainty and
preference uncertainty separately, then justify each from data and explicit
cross-election assumptions. In particular, the independent pre-projection
statewide party errors are not a fitted covariance model. More simulations
cannot fix that limitation. Council probabilities should wait for this review.

## Performance and verification

Current 200 draws: 25.15 seconds locally, versus approximately 33.2 seconds for
the previous archived implementation (about 24% less elapsed time; not a
controlled hosted benchmark). Narrower 24.87 seconds; wider 24.54 seconds.
All 200 current seat-count draws exactly match the previous archive. The
88-seat fast count also matches original winners, margins and ALP–LNP 2PP
exactly with preference shocks enabled. The central calculator is unchanged.

Seven forecast tests pass. Full suite: 96 pass and one pre-existing legacy
workbook fixture failure remains (ALP difference 0.030807616248605896 share),
also observed before these changes. App smoke checks pass for running and
comparing three profiles. Hosted rebuild/runtime has not been verified here.

Raw outputs and reproduction settings: `forecast_uncertainty_2026_10_10/`.
