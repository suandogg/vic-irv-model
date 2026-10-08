# Single ON baseline implementation trial

The testing app exposes two distinct comparisons, with reference still default.
Primaries and Council rules are unchanged.

**Single synthetic ON fallback baseline** applies when ON is alive or is the
eliminated ballot origin. It locks special priors first. Otherwise it uses the
synthetic row projected to the continuing field, without generic posterior
selection, extra matrix anchoring, geography or siphoning. Existing floors and
caps remain. Missing usable matrix rows have labelled generic/uniform fallbacks.
Exact federal records still blend toward this underlying rule with the existing
evidence weights. Special priors are protected even against future matching
federal records. Projection to continuing parties is unchanged here; this trial
does not add a new ranking/pass-through method.

**Keep ON source selection, remove extra transforms** retains today's basis
selection and federal blending. It removes geography and siphoning only in
ON-related calls. Non-ON calls retain current geography. This isolates layered
adjustments from the broader change in source selection.

| Scenario | Reference ALP/LNP/GRN/ON | Matrix-direct ALP/LNP/GRN/ON | Source-preserving ALP/LNP/GRN/ON |
| --- | --- | --- | --- |
| ON18 | 38/42/5/3 | 34/47/4/3 | 41/41/5/1 |
| ON20 | 31/44/5/8 | 26/49/5/8 | 30/46/5/7 |
| ON24 | 26/38/5/19 | 23/41/5/18 | 24/40/5/18 |

Both ON24 alternatives also elect one IND. Matrix-direct changes 6/5/4 seat
winners; source-preserving changes 4/5/5. Both preserve winners in the projected
2022-input scenario. Actual-primary 2022 conditional matrix holdout MAE is
1.819 points for matrix-direct versus 1.820 for reference, an effectively
uninformative difference for this ON-specific question.

## Interpretation

Replacing generic basis selection is a materially different intervention from
removing overlapping adjustments. In ON18 these interventions move ALP totals
in opposite directions. Matrix-direct need not be less biased or more accurate
merely because it is simpler. Existing exact-field Victorian evidence and prior
selection may contain useful non-ON relationships that a full synthetic row
does not represent. The federal holdout pooling results do not validate either
whole state engine.

Recommendation: do not adopt matrix-direct wholesale. Retain it as a diagnostic
bound. Next separate matrix-direct selection from adjustment removal, using
parcel traces for the changed seats, then design a provenance-aware fallback
that preserves genuine observed non-ON relationships. No Sheet or reference
defaults have changed.

Regression tests cover locked special priors (including future matching federal
evidence), retained federal blending, unchanged non-ON rounds and absence of
extra transforms in the matrix-direct path. Sixteen tests pass.
