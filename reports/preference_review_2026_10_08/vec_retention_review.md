# Retention sensitivity and process status

Tested retention0,0.5,0.75,1 with identical primary estimates per scenario.
Zero uses the eliminated holder's preference behaviour; one retains each
parcel's original-party behaviour; intermediate values blend the two. This is
sensitivity, not calibration against observed ballot rankings. Each corrected
method is also compared with reference at the identical retention setting.

## Corrected-method counts

| Scenario | Retention | ALP | LNP | GRN | ON | IND |
|---|---:|---:|---:|---:|---:|---:|
| ON18 | 0 | 35 | 46 | 5 | 2 | 0 |
| ON18 | .5 | 37 | 43 | 5 | 3 | 0 |
| ON18 | .75 | 38 | 42 | 5 | 3 | 0 |
| ON18 | 1 | 37 | 43 | 5 | 3 | 0 |
| ON20 | 0 | 31 | 45 | 5 | 7 | 0 |
| ON20 | .5 | 30 | 45 | 5 | 8 | 0 |
| ON20 | .75 | 30 | 45 | 5 | 8 | 0 |
| ON20 | 1 | 31 | 44 | 5 | 8 | 0 |
| ON24 | 0 | 24 | 40 | 5 | 19 | 0 |
| ON24 | .5 | 24 | 40 | 5 | 19 | 0 |
| ON24 | .75 | 25 | 38 | 5 | 20 | 0 |
| ON24 | 1 | 25 | 38 | 5 | 20 | 0 |

## Five examples: corrected-method ALP forced 2PP at ON18

| Seat | Retention0 | .5 | .75 | 1 |
|---|---:|---:|---:|---:|
| Pakenham | 38.45 | 39.93 | 40.63 | 41.31 |
| Morwell | 35.20 | 36.68 | 37.39 | 38.10 |
| Pascoe Vale | 65.82 | 64.64 | 63.96 | 63.21 |
| Ashwood | 50.25 | 49.71 | 49.43 | 49.16 |
| Yan Yean | 45.61 | 47.17 | 47.87 | 48.51 |

Pakenham, Morwell, Pascoe Vale and Yan Yean retain winners; Ashwood changes
ALP to LNP between0 and0.5. Ringwood's ALP share is50.98,50.43,50.14,49.84,
changing ALP to LNP at1. Forced ALP–LNP shares must not be interpreted as an
actual final-two forecast where finalists differ.

## Where we are

Completed: isolate original/backup/experimental apps and copy testing Sheet;
audit synthetic row construction and OTH parameter drift; test source selection,
geography, siphon, floors/caps and shrinkage sensitivities; identify historical
field provenance; implement opt-in exact-field VEC evidence; independent
seat-held-out conditional flow tests; isolate synthetic ON coverage selection;
implement narrow opt-in coverage correction; verify live app and27-tab sync;
audit holder and origin activations, including1879 protected flow checks;
run retention sensitivity.

Current app: reference remains the default on a new session. Corrected VEC
coverage is selectable. Own-seat exact-field evidence is attached only in that
mode; pooled holdout experiments are diagnostics, not live pooled forecasts.
Original Sheet/reference app and backup remain separate. No settings changed
for this retention diagnostic; current retention remains1.

Established: exact-field pooled evidence improves held-out reconstructed flow
shares versus legacy fallback; narrow coverage correction avoids unnecessary
prior blending on complete non-ON fields. Not established: accurate high-ON
forecasts, optimal retention, independent candidate-origin ballot flows, or
universal pooled evidence superiority in election reconstruction.

Next priorities: separate candidate/category elimination artefacts from flow
accuracy; test whether retaining candidate/subtype structure resolves artificial
OTH finals; decide an evidence hierarchy and shrinkage for own-seat versus pooled
exact fields. Do not select settings by desired ALP seats. Keep ON special
priors unchanged unless separately reviewed. Retention should remain sensitivity
reporting until identifiable evidence supports a different setting.

This session concerns Assembly preference logic; Council methodology unchanged.
Detailed outputs: `vec_retention_sensitivity.json`.
