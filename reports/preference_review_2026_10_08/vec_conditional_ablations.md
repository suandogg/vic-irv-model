# Conditional-flow adjustment isolation

All comparisons use the same 234 exact-field targets with the held-out seat
excluded. The targets are reconstructed category-origin allocations, not raw
candidate transfer parcels. No production defaults, Sheet cells, ON priors or
app forecasts changed. Minimum-three all-class pools used throughout.

| Diagnostic | Mean flow-allocation error, points |
|---|---:|
| VEC pool through unchanged engine | 13.477 |
| Disable non-ON geography | 13.269 |
| Disable floors/caps | 13.477 |
| Skip incomplete-row anchoring | 13.477 |
| Disable all three | 13.269 |
| Historical-only coverage, geography retained | 11.535 |
| Historical-only coverage, geography disabled | 11.695 |

The last two are diagnostic-only copies of the input row with stored synthetic
ON mass set to zero, ONLY on these historical fields where ON is absent. They
are not proposed ON insertion settings and are not app options.

## Mechanism

The exact-field trial retains stored synthetic ON mass when reconstructing
the raw matrix row. When ON is absent from the requested field, `coverage`
equals continuing non-ON mass divided by total row mass, including synthetic
ON. Thus it is below one even when the VEC field is complete and exactly matched.
The engine does not select a full matrix row; with aggregate posterior disabled
it selects the generic ideology prior and blends back toward the matrix.
Skipping incomplete-row anchoring does not address this because it is triggered
by missing positive continuing recipients, not discarded synthetic ON mass.

This explains the residual error relative to direct pooling. Geography's small
apparent harm in the mixed-prior arm reverses once that selection issue is
isolated: retaining geography improves 11.695 to 11.535. Therefore this test
does not support simply disabling geographical adjustments.

## Recommendation

Next trial should distinguish historical field completeness from synthetic ON
allocation when selecting evidence, narrowly for confirmed exact-field VEC
records. Preserve existing ON allocation, special priors and transformations
in forecasting. Test the narrow rule against historical holdout and high-ON
scenario sensitivity before adoption. Do not globally reinterpret coverage
for legacy compressed rows or infer high-ON accuracy from 2022 results.

Detailed paired errors: `vec_conditional_ablations.json`.
