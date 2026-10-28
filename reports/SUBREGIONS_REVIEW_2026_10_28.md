# SUB-REGIONS: forecast integration review

Read 28 October from testing spreadsheet 1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968,
SUB-REGIONS (sheet ID 1018258823), A1:D100. Snapshot saved alongside this report.
No Sheet edits made. Compared with the committed LEGACY_PRIMARY_INPUTS roster.

## Coverage

88 rows, 88 unique districts: no missing, extra or duplicate seats. There are
25 groups, each with 2–5 seats. Confidence labels: 72 High, 12 Medium, 4 Low.
Low-confidence assignments: Eildon, Lowan, Mildura and Murray Plains. These labels
describe classification confidence, not measured forecast reliability; do not
convert them directly to numerical variance weights.

## Crossed rather than strictly nested groups

Nine groups span multiple upper-house regions in current model metadata:

| Sub-region | Upper-house regions |
|---|---|
| Eastern Middle Suburbs | North-Eastern Metro; Southern Metro |
| Inner West | Northern Metro; Western Metro |
| North-Western Fringe | Northern Victoria; Western Metro |
| Northern Growth Corridor | North-Eastern Metro; Northern Metro |
| Northern Middle Suburbs | North-Eastern Metro; Northern Metro |
| Outer Eastern Suburbs | North-Eastern Metro; South-Eastern Metro |
| South-Eastern Growth Corridor | Eastern Victoria; South-Eastern Metro |
| Western Growth Corridor | Western Metro; Western Victoria |
| Yarra Ranges Fringe | Eastern Victoria; Northern Victoria |

This is not necessarily an error: functional voting communities can cross
Council boundaries. Preserve the user's memberships rather than silently
splitting groups to enforce nesting. This checks current model metadata,
not an independent audit of official boundaries.

## Recommended fixed-budget experiments

1. Existing upper-house-region shocks only (baseline).
2. Sub-region shocks only: replace the grouping rather than add another SD.
3. A crossed blend: `SD_geo * (sqrt(1-f)*Z_upper + sqrt(f)*Z_subregion)`.
   Trial f=0, 0.5 and 1 as sensitivity choices, not fitted probabilities.

Independent latent group effects are reused by every member seat. Pre-centring
marginal geographic variance stays SD_geo squared; overlap changes cross-seat
covariance. Remove the statewide mean and rebalance to actual production totals.
Measure realised post-balancing variation rather than claiming it equals the
input SD. Smaller blocks can cancel in statewide totals, so more groups do not
necessarily widen party seat ranges or soften every seat probability.

For primaries this replaces/refactors existing regional noise. Local residuals,
concentration and alternative-map factors need their own declared variance
budget, not unacknowledged stacking. For preferences, test group effects inside
the planned statewide/geographic/local source-dependent budget. Membership alone
does not establish different preference behaviour; use evidence where available
and label other effects as provisional.

## Live-integration requirements

- Bounded Sheet sync and a strict loader with canonical district matching;
  reject missing/duplicate assignments, preserve confidence/notes and hash mapping.
- Do not infer a single parent Council region from a sub-region name.
- Stable label ordering for reproducible random draws and cache invalidation
  when mappings change.
- Zero/off settings must reproduce current outputs; no central calculator,
  primary total, source-prior or Council changes.
- Compare upper-only/sub-only/blended patterns, then interactions with strength
  and preference patterns. Report five demonstration seats, certainty counts,
  party ranges and within/across-group correlations.
- Review uncertain memberships using historical swing similarity, without
  choosing classifications to manufacture desired election outcomes.

## Status

Subsequent implementation on 28 October adds read-only sync and a forecast-only
loader, plus opt-in upper-only/sub-only/blended primary geographic uncertainty.
The default still does not use the mapping. Memberships, Sheet values, central
calculator and Main remain unchanged. See SUBREGIONS_TRIAL_RESULTS_2026_10_28.md
for the controlled comparison; this does not yet add regional preference effects.
