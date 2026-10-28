# Independent primary-lean evidence — 29 October 2026

## Outcome

Assembled official 2014 and 2018 Victorian Lower House candidate primary votes for all 88 districts at each election. There are 1,052 candidate records across 176 district-election observations. Original official labels, counts, displayed percentages, exact count-derived shares and source URLs are retained. All candidate totals reconcile to district formal votes, statewide formal totals and the official six-category aggregation of statewide party totals.

- 2014: 545 candidates; 3,355,707 formal votes.
- 2018: 507 candidates; 3,514,474 formal votes.
- Both elections used the 2013-redivision districts. These are not automatically the current districts.

This replaces reliance on model-generated scenario ranges with independent evidence of geographic change. It does not finish calibration of the nowcast.

## What was measured

For each party and district:

`lean change = (2018 district share − 2018 statewide share) − (2014 district share − 2014 statewide share)`.

This removes the statewide primary swing. Statewide shares here use official formal-vote weights. This is a descriptive convention, not an authorised change to the production calculator's equal-seat balancing.

The comparison describes realised geographic movement over one four-year electoral transition. It combines regional, local, candidate and contest-field changes. It is not polling sampling error, not movement from today to election day, and not an out-of-sample test of a fitted present-day forecast. The relevance is that the current model's historical district template can age and be wrong by more than a small local perturbation.

## Main results

SD is the cross-district standard deviation of lean changes, in percentage points. It must not be assigned independently to every uncertainty layer.

| Party/category | All 88 districts: SD | Defined major-field subset: SD |
|---|---:|---:|
| ALP | 5.58 | 3.71 |
| LNP | 5.52 | 3.69 |
| GRN | 2.07 | 1.83 |
| IND, official-label aggregate | 8.44 | 3.21 |
| OTH, official-label aggregate | 4.66 | 4.21 |

The 65-district subset requires all three established parties to contest both elections, no multiple Coalition candidates, and no individual independent reaching 10% in either election. The 10% cut is an explicit descriptive split, not an estimated threshold or a production classification rule. This subset is not automatically a list of “ordinary” current seats.

Twenty-six districts had absolute ALP lean movement of at least five points; five exceeded ten points. For LNP, 23 reached five and seven reached ten. No Greens district reached five in this transition. None of these counts establishes an appropriate probability ceiling or proves a safe current seat is misestimated.

Examples of large realised changes:

| Historical district | Party | Lean change, pp |
|---|---|---:|
| Melton | ALP | −20.29 |
| Lowan | LNP | +19.65 |
| Benambra | ALP | −18.02 |
| South-West Coast | LNP | −17.79 |
| Werribee | ALP | −15.97 |
| Pascoe Vale | ALP | −14.73 |
| Morwell | LNP | −14.60 |

Large changes often occur alongside different candidate/independent contexts, but those flags do not prove causation. In particular, Lowan's large historic movement shows that a strong Coalition district lean is not a timeless constant. It does not establish today's ON win probability.

## Party relationships

In the 65-district subset, empirical lean-change correlations are:

- ALP/LNP: −0.416.
- ALP/GRN: −0.179.
- LNP/GRN: +0.352.

These are correlations of geographic deviations after statewide change, not voter-transition estimates. A positive LNP/GRN error correlation need not mean the two draw votes from the same individual voters. Do not replace the structured nowcast's entire six-party correlation matrix with this small three-party estimate. Further elections, shrinkage and context treatment are needed.

## Important classification and boundary safeguards

1. Raw independent candidates remain individually identifiable. The descriptive IND column aggregates official-label independents; it does NOT reproduce the production policy retaining a principal independent and moving some minor independents to OTH. Multi-independent fields and candidate-name changes are flagged.
2. Candidate changes are determined by normalised names, not inferred incumbent retirement. A new challenger is not the same event as a retiring incumbent. Coalition multiple-candidate fields are flagged separately.
3. Party absence is recorded. LNP contested both elections in 87 districts, not 88. Do not interpret a disappearance from the ballot as ordinary vote-share noise.
4. ON has no observations in these primary tables. Its descriptive zero variance means no data, not zero uncertainty. The output explicitly prohibits using this comparison to calibrate ON.
5. The available local 2022 extraction contains 88 districts and 742 candidates, but the 2021 redistribution prevents automatic joins to 2018 by name. Original reported 2022 candidate shares are rounded; count-derived shares should be used when that panel is incorporated. Narracan's supplementary-election context also needs explicit treatment.

## Implications for the approved nowcast framework

The independent evidence supports modelling uncertainty in district leans, distinguishing party scales, modelling correlated errors, and explicitly handling exceptional local candidate fields. It does not support simply raising a universal local SD or drawing more simulations.

The new framework should own one primary-error budget. Do not add the historical 5.5-pp spread on top of the existing local, region and concentration terms. Part of that spread reflects context changes that require candidate scenarios rather than ordinary residual noise. The direct size of each new component remains provisional until those effects and additional transitions are examined.

Next, use the panel to estimate and assess a shrunk established-party error structure, while separately designing ON transport assumptions and candidate-field inputs. Keep observed four-year lean movement distinct from uncertainty about today's latent lean. Add boundary-compatible 2022 evidence only where defensible, rather than treating same names as unchanged districts. No app settings, default probabilities, Main model or Sheet source rows were changed at this stage.

## Files and validation

- Evidence: `data/research/historical_primaries_2026_10_29/` contains candidate rows, district shares, official statewide controls, source-page caches and SHA-256 manifest.
- Analysis: `reports/historical_lean_evidence_2026_10_29/` contains all 528 party/district lean changes, context flags, summaries and empirical correlations.
- Importer: `tools/assemble_historical_primaries.py`; can reproduce the panel offline from the cache.
- Analysis: `tools/analyse_historical_lean_changes.py`.
- Three importer tests pass, covering party-label mapping, selecting primary rather than final-pair data, percentage/count mismatch rejection, unique candidate keys, complete district coverage and exact official totals. Offline full-panel reconstruction also passes.

## Independent sources

- VEC 2014 result index: https://itsitecoreblobvecprd01.blob.core.windows.net/public-files/historical-results/state2014/summary.html
- VEC 2018 result index: https://itsitecoreblobvecprd01.blob.core.windows.net/public-files/historical-results/state2018/summary.html
- Each candidate record links to its own official district page.
- Victorian Parliamentary Library 2022 election research paper, section 11.2, documents the previous 2013 boundaries used in both 2014 and 2018: https://www.parliament.vic.gov.au/49950e/globalassets/sections-shared/about/publications/research-papers/the2022victorianstateelection_rp_2023_2.pdf
- VEC confirms the 2021 redivision came into effect for 2022: https://www.vec.vic.gov.au/electoral-boundaries/state-boundary-reviews
