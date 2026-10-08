# Missing fields and evidence-threshold sensitivity

Inventory is the first unresolved field per seat under minimum-three strict
holdout. It is not an exhaustive inventory of fields later rounds might need.

-22 seats have exactly two other-seat subtype-field observations.
-14 have exactly one other-seat observation.
-12 have no matching subtype-field observations elsewhere.
-5 encounter ON fields deliberately excluded from this historical diagnostic.

Frequent combinations include OTH_LTP and OTH_REASON with ALP+GRN+IND+LNP+OTH,
OTH_DHJP with ALP+GRN+LNP+OTH, and OTH_AJP with ALP+GRN+LNP. Each stops3 seats.
This is partly small-party sparsity, not just exotic final-two fields.

## Threshold sensitivity, diagnostic only

| Minimum other seats | Complete /88 | Correct winners among complete | Correct pairs among complete |
|---|---:|---:|---:|
| 1 | 66 | 64 | 66 |
| 2 | 51 | 50 | 51 |
| Approved3 | 35 | 34 | 35 |
| 5 | 23 | 23 | 23 |

Completed samples differ, so these accuracy fractions cannot rank methods
fairly. Missing seats are not correct predictions. Lower minimums let more
seats progress, but can expose further missing fields or alter count paths.
At minimum-one, Laverton, Kororoit, Ashwood and Pascoe Vale complete; Pakenham,
Morwell and Yan Yean still stop. At minimum-two Kororoit still stops.

## Recommendation

Retain minimum-three as the approved shadow rule for now. Do not make a
single-seat observation a confident fallback just to finish a count. Next
use matched-parcel held-out tests to evaluate evidence-weighted shrinkage of
sparse subtype pools toward broader exact-field pools, clearly separating
same-category recipient cases. That is a new fallback choice and must be
reviewed before integration. Zero-evidence combinations and ON cases need
separate treatment; these threshold tests cannot solve them.

Original/live model, Sheet inputs and ON rules unchanged. Detailed first-stop
inventory: `candidate_missing_fields.json`; threshold counts:
`candidate_subtype_count_min1.json`, `candidate_subtype_count_min2.json`,
`candidate_subtype_count_min5.json`.
