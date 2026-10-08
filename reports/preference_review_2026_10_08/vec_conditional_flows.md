# Conditional-flow validation on recorded fields

## Design

For each extracted category-origin flow, predict its recipient shares on its
recorded continuing category field. Exclude all preference rows from that seat
when constructing either the legacy reference matrix or the VEC evidence pool.
Disable aggregate posterior/federal evidence. Exclude ON-origin and native-ON
fields and trivial one-recipient targets. Use exact field matches only.

The target is the compiler's reconstructed category-origin allocation, not a
literal single-candidate elimination parcel. Category aggregation and the
compiler's proportional origin-accounting assumptions remain limitations.
This test avoids simulated elimination ordering; it does not validate candidate
count outcomes, ON insertion, high-ON scenarios or the upper house.

Metric: half the summed absolute recipient-share differences, in percentage
points. For a two-party destination field this is the absolute share error;
for larger fields it measures misallocated flow mass. Equal weight per target
category/field, not ballot weighted. No tuning to ALP seat totals.

## Results

| Pool | Matched / eligible fields | Reference error | Engine with VEC pool | Direct VEC pool |
|---|---:|---:|---:|---:|
| All classes, minimum 1 | 234/238 | 16.43 | 13.48 | 11.70 |
| All classes, minimum 3 | 234/238 | 16.43 | 13.48 | 11.70 |
| All classes, minimum 5 | 222/238 | 16.24 | 13.31 | 11.40 |
| Same class, minimum 1 | 224/238 | 16.42 | 13.40 | 11.23 |
| Same class, minimum 3 | 185/238 | 15.68 | 13.36 | 10.54 |
| Same class, minimum 5 | 116/238 | 16.60 | 13.50 | 10.96 |

Each row compares methods on identical targets, but rows have different coverage.
On the 116 targets shared by every variant, all-class engine error is 13.53
versus same-class 13.50; direct pool error is 11.08 versus 10.96. Thus the apparent
large advantage of stricter class minimums in the full table is mostly not a
like-for-like advantage. No clear evidence here supports making class effects
or minimum-five mandatory.

## Interpretation and next step

Field-matched VEC evidence improves conditional share prediction relative to the
legacy reference on held-out seats. The engine's transformations collectively
move these predictions further from the extracted target than direct pooling.
This does not identify the responsible transformation, nor justify removing
ON transforms or special priors. Isolate non-ON transformations next, on the
same held-out targets, before selecting any application rule.

No model default, app option, Sheet cell, ON special prior or forecast changed
in this diagnostic. The five demonstration seats therefore have no new forecast
changes to display. Per-target errors are in `vec_conditional_flows.json`.
