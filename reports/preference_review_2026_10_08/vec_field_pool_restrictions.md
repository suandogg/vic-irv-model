# Pool restrictions and final-pair regressions

These are held-out historical reconstruction diagnostics, not new production
settings. No Sheet cells, default app selections or ON special priors changed.

## What happened

Both seats retain Labor as winner. Their primary totals are identical across
variants. The consequential change is whether combined OTH or LNP survives
after IND and GRN elimination:

| Seat | Reference LNP / OTH after GRN | Pooled VEC LNP / OTH after GRN |
|---|---|---|
| Laverton | 23.29% / 22.63% | 23.37% / 24.20% |
| Kororoit | 25.85% / 25.31% | 25.57% / 26.04% |

Pooled evidence therefore eliminates LNP, yielding ALP–OTH rather than the
historical ALP–LNP pairing. Multiple rounds contribute; this is not solely
a change to the Greens row. Seat-class pooling with three training seats
restores Laverton's ALP–LNP pairing; Kororoit still yields ALP–OTH.

## Restrictions tested

All pools exclude the held-out seat and use equal-seat weights. Minimums
apply to each eliminated-category / exact-field combination. A failed
minimum or absent matching field retains the same legacy fallback.

| VEC pool | Correct winners | Correct pairs | Common-pair MAE | Reference MAE on same seats |
|---|---:|---:|---:|---:|
| All classes, minimum 1 | 87/88 | 83/88 | 1.673 | 1.815 |
| All classes, minimum 3 | 87/88 | 83/88 | 1.673 | 1.815 |
| All classes, minimum 5 | 87/88 | 83/88 | 1.686 | 1.815 |
| Same class, minimum 1 | 87/88 | 84/88 | 1.775 | 1.818 |
| Same class, minimum 3 | 87/88 | 84/88 | 1.768 | 1.818 |
| Same class, minimum 5 | 87/88 | 84/88 | 1.813 | 1.818 |

MAE units are percentage points. Common sets are 83 seats for all-class
variants and 84 for class-restricted variants; do not compare them as
identical samples. The untouched reference has 85 correct final pairs.

## Interpretation

Laverton's OTH bucket comprises six separate minor candidates with combined
primary 21.62%; Kororoit's comprises five with combined primary 23.47%.
Their largest individual OTH candidates have only 5.94% and 6.86% respectively.
The six-category count treats those heterogeneous candidates as one contender,
so its elimination ordering is not the statutory candidate count. An ALP–OTH
final can therefore be a grouping artefact. These observations do not prove
the pooled flows themselves are inaccurate, nor establish them as better.

Recommendation: no global pool replacement yet. Same-class minimum-three is
a useful further trial, not a validated optimum. Before choosing a method,
compare conditional flow prediction on actual historical continuing fields,
or retain candidate/subtype-level elimination in validation. That separates
preference-estimation error from category-count artefacts. High-ON performance
still needs separate evidence and sensitivity assessment.

Full round traces: `vec_field_holdout_regression_traces.json`.
