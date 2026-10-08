# Subtype-to-broad shrinkage: rejected diagnostic

Strict held-out seat exclusion; subtype and broad pools match identical
continuing category fields. Equal-seat weights. Blend subtype weight n/(n+k)
for prior strengths1,3,5,10. Comparisons use identical516 targets; sparse subset
is50 targets supported by only1 or2 other seats. Metric: half-L1 share error,
percentage points. Broad pool includes subtype observations and is correlated
with subtype pool; this is a sensitivity test, not a fitted Bayesian model.

| Method | All516 parcels | Sparse50 parcels |
|---|---:|---:|
| Subtype only | 13.38 | 13.39 |
| Broad only | 19.06 | 23.78 |
| Prior strength1 | 13.61 | 15.05 |
| Prior strength3 | 14.17 | 18.26 |
| Prior strength5 | 14.57 | 19.82 |
| Prior strength10 | 15.29 | 21.50 |

All tested blends worsen aggregate errors; same-category-alive subset also
worsens (subtype14.86; blends15.20 to17.29). This does not mean every individual
target worsens, or establish no other prior could help. Hyperparameters were
compared on the same holdout dataset, not independently selected/confirmed.

Recommendation: do NOT integrate shrinkage toward undifferentiated OTH/broad
category evidence. Candidate subtype distinctions are predictive and this
target erases them. Retain the approved minimum-three shadow rule. Treat sparse
subtype-only evidence as a separately labelled sensitivity, not reliable by
default. If further shrinkage is pursued, evaluate a conceptually closer prior
(e.g. independently reviewed ideological family) with paired holdouts before
integration. This would require a new conceptual choice, not automatic adoption.

The candidate count still lacks a complete unseen-field policy. No ON inference,
live model, Sheet or shadow fallback changed. Detailed paired errors:
`candidate_subtype_shrinkage.json`.
