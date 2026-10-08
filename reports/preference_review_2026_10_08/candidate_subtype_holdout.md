# Candidate subtype evidence for unseen fields

Strict seat holdout: exclude every candidate observation from the target seat.
Match exact continuing broad categories and eliminated candidate subtype.
Average candidate observations within each training seat, then weight seats
equally. Compare broad-category pooling on exactly the same targets. Metric is
mean half-L1 category-flow error in percentage points, equally weighted parcels.

| Minimum training seats | Matched / eligible parcels | Subtype error | Broad error on same parcels |
|---|---:|---:|---:|
| 1 | 516/537 | 13.38 | 19.06 |
| 3 | 466/537 | 13.38 | 18.55 |
| 5 | 449/537 | 13.42 | 18.55 |

Minimum-three includes261 parcels where another candidate of the eliminated
category remains continuing. It therefore supplies potential evidence for
same-category transfers, unlike the six-party engine. Coverage differs across
minimums; error comparisons across rows are not on identical samples.

Targets are actual eliminated candidate parcels, including previously received
votes, not primary-origin preference shares. This avoids origin reconstruction
assumptions for these targets but introduces dependence on parcel composition
and stage. Matching broad fields does not match specific continuing candidates,
within-category candidate counts, or electorate context. Holdout error is not
election outcome validation. Native ON fields/origins are excluded: no claim
about hypothetical ON insertion or high-ON accuracy.

Recommendation: use subtype exact-broad-field pooling with a minimum-three
threshold as the next candidate-shadow experiment, not production adoption.
Exact candidate evidence retains precedence; proportional recipient allocation
applies only where exact recipient data are unavailable; insufficient pool
coverage must remain explicitly unresolved. Minimum-three is a conservative
trial threshold, not an empirically proven optimum.

No fallback, app, Sheet input, ON prior or forecast changed in this diagnostic.
