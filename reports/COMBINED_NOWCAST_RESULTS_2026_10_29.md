# Continuing the concentration trial, not replacing it

The user's requested direction is to retain plausible spatial-pattern uncertainty and extend it with district-lean and preference-applicability uncertainty. History informs these assumptions; it does not cap what can happen in 2026. No seat-probability caps or targeted party bonuses are applied.

## Matched comparison

Primaries: ALP 24.2, LNP 30.2, GRN 14.7, ON 21.9, IND 4.5, OTH 4.5. Each run has 500 draws, seed 20261010, identical core inputs and preference architecture. The combined runs retain the previous positive-bounded all-party concentration width 0.30 and blended upper-house/subregion geography. Structured residuals replace ordinary local/regional residuals, not duplicate them. ON concentration replaces ordinary ON-alpha noise as before.

| Method | Average district favourite | Above 90% | Above 98% | Showing 100% | Mean district ALP–LNP 2PP SD |
|---|---:|---:|---:|---:|---:|
| Current default | 83.34% | 46 | 33 | 23 | 2.92 pp |
| Previous concentration trial | 79.43% | 40 | 17 | 3 | 4.18 pp |
| Initial standalone structured mode | 81.72% | 44 | 31 | 19 | 3.61 pp |
| Concentration + structured leans | 78.02% | 35 | 18 | 2 | 4.71 pp |
| Combined + source applicability | 76.73% | 33 | 12 | 0 | 4.99 pp |

Thresholds are strict greater-than, not greater-than-or-equal. The final package has 13 seats at least 98%, of which 12 are above 98%. At 500 draws, threshold counts are noisy; zero observed losses is not proof a seat is certain. The old concentration run reproduces the earlier 79.425% audit exactly.

The last run adds source-applicability log-weight SDs VEC 0.15, federal 0.25, special 0.35, generic 0.35. These are explicit judgment-based 2026 assumptions, not fitted estimates. The rationale is smaller uncertainty for state evidence, more for federal-to-state transfer, and greater uncertainty for hypothetical/synthetic sources. They apply to all origins and recipients, not only One Nation. They do not rewrite special-prior source rows or the central calculator. Because log-weight normalisation and counting are nonlinear, mean simulated flows/outcomes need not equal central deterministic outputs.

## All-party and all-seat check

Compared with the previous concentration trial, the final package lowers the district favourite in 72 seats, raises it in 14, and leaves two unchanged. A broader model need not make every probability smaller.

| Party | Seats above 90%, old → final | Seats above 98%, old → final |
|---|---:|---:|
| ALP | 11 → 6 | 2 → 0 |
| LNP | 27 → 25 | 15 → 12 |
| GRN | 2 → 2 | 0 → 0 |
| ON | 0 → 0 | 0 → 0 |
| IND | 0 → 0 | 0 → 0 |
| OTH | 0 → 0 | 0 → 0 |

Examples, not selected tuning targets: Lowan LNP 98.0 → 97.2%; Bass LNP 93.6 → 86.6%; Hastings LNP 92.8 → 82.6%; Pakenham LNP 70.6 → 59.8%; Ashwood LNP 75.0 → 68.6%; Yan Yean LNP 47.0 → 44.2%. Morwell ON rises 63.0 → 65.6%, illustrating non-monotonicity. Pascoe Vale goes from ALP 49.2/GRN 49.4 to ALP 46.2/GRN 48.2, allowing small additional outcomes.

## What is implemented

An additional opt-in app mode, Concentration + structured nowcast (development), starts at bounded 0.30. Select Blend upper-house and sub-regions to reproduce the combined comparison. Four source-applicability SDs are editable in the testing workbook NOWCAST BUDGET C20:C23 and matching CSV; setting them to zero recovers the lean-only combined package. The original Current mode and Main are untouched. Existing structured mode also reads these new source settings, so its new runs will differ from its initial zero-source comparison here.

## Limits and direction

This is a coherent judgment-based development package, not validated election probability calibration. Concentration and historical residuals are not proven statistically independent; their combination is a declared assumption. Candidate contexts remain disabled pending review, exact zero cells stay zero, and aggregate IND/OTH support does not invent new named candidates. Thus the almost absent IND/OTH winning pathways remain an unresolved candidate-field issue, not something to disguise with arbitrary upset probabilities. Lowan remains highly favoured and needs a substantive alternative pathway if it is to become less certain, not a probability cap.

The comparisons use the frozen 28 October live core snapshot, committed preference evidence, and explicit nowcast configs—not a complete recapture of the hosted app today. Files in combined_nowcast_comparison_2026_10_29 preserve every result, configuration and engine/input hash. Reproduce with tools/compare_structured_nowcast.py.
