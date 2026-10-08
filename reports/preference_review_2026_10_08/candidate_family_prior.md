# Existing IdeologyFamily prior diagnostic

Use existing LEFT,CENTRE_LEFT,CENTRE,CENTRE_RIGHT,RIGHT labels only. UNKNOWN
and unlabelled records excluded, not assigned new labels. Match same broad
origin category and exact continuing categories. Both subtype and family pools
exclude all held-out seat records; family minimum3 other seats. Equal-seat
weights; paired comparisons use identical301 targets. Family pool includes
same-subtype evidence, so the estimates are correlated, not independent priors.

| Method | All301 parcels | Sparse24 parcels |
|---|---:|---:|
| Subtype only | 13.19 | 12.71 |
| Family only | 15.89 | 19.01 |
| Prior strength1 | 13.27 | 13.73 |
| Prior strength3 | 13.49 | 15.55 |
| Prior strength5 | 13.67 | 16.35 |
| Prior strength10 | 14.08 | 17.41 |

Metric: mean half-L1 category-flow difference in percentage points. Sparse
targets have only1 or2 contributing subtype seats. Small sparse sample and
within-seat dependence mean these are descriptive results, not significance
claims. Do not compare301-target errors directly to earlier516-target results.
Current ideological labels partly encode party-level judgments; those judgments
were not reclassified here. This does not establish that all ideology-based
models are unhelpful, only that this tested shrinkage fails to improve average
prediction on the available held-out observations.

Recommendation: do not integrate family shrinkage. Keep exact candidate
evidence first and subtype exact-field shadow pools with explicit uncertainty.
Do not broaden the live candidate count to unseen fields just to complete
outputs. The candidate experiment remains limited by evidence, while the narrow
VEC coverage correction is a separate implemented six-category improvement.
Prioritise additional multi-election candidate evidence or retain six-category
production with candidate aggregation warnings rather than inventing a prior.

No live app, fallback setting, Sheet classification, ON rule or default changed.
Detailed paired results: `candidate_family_prior.json`.
