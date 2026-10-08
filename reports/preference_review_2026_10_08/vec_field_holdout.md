# Exact-field VEC evidence: independent seat holdout

Each of 88 seats is reconstructed from its actual 2022 category primaries,
using the same existing LNP pre-collapse in both arms. Its own preference
evidence is removed from both training pools. Aggregate posteriors and federal
evidence are disabled because their training membership cannot be excluded here.

Reference: mean legacy matrix from other seats of the same class (all other
seats if necessary). Trial: that same fallback, with an equal-seat VEC pool
from other seats whenever eliminated category and non-ON continuing field match
exactly. The VEC pool spans classes: this is a deliberate test of field matching
without imposing another geographical adjustment. No nearest-field projection.
Existing synthetic ON shares, special priors and transformations are preserved;
native-ON extracted cases are excluded. This does not validate high-ON forecasts.

| Measure | Reference | Exact-field pool |
|---|---:|---:|
| Correct winners / 88 | 87 | 87 |
| Correct final pairs / 88 | 85 | 83 |
| Same comparable seats | 83 | 83 |
| Final-share MAE, percentage points | 1.815 | 1.673 |

Laverton and Kororoit lose correct final-pair reconstruction. Average error
therefore improves on a fixed common set, but final-pair performance worsens.
Errors are relative to each actual winning party, not an ALP-bias measure.

Recommendation: do not adopt pooled exact-field replacement globally. Next
inspect those two regressions and compare pooling restricted to seat class,
with minimum evidence thresholds. Keep the existing own-seat exact-field option
separate: that is a different application, and its historical fit is in-sample.
This holdout diagnostic is not activated in the app and changes no Sheet cells.

Machine-readable per-seat outcomes: `vec_field_holdout.json`.
