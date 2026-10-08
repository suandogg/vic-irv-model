# Endogenous candidate shadow: exact evidence coverage

Count chooses the lowest current candidate, uses recorded category shares only
when that candidate's exact remaining candidate set matches the historical
record, and allocates recipients proportionally by current tallies. Otherwise
stops and reports the unresolved field. No nearest-field projection, same-party
retention assumption or new ON allocation. Historic primaries only, not polling
scenarios. Evidence is held-in; this is structural sensitivity, not validation.

54/88 seats complete;34 stop after proportional recipient allocation changes
the next exclusion relative to historical records.30 of those34 still have
another candidate in the eliminated candidate's category. Existing broad engine
cannot supply preferences to own-category candidates, so cannot fill these gaps
without a separate evidence source or modelling choice.

Laverton completes with ALP68.45% versus recorded68.39%, ALP–LNP final. Kororoit
stops at its fourth exclusion: shadow chooses Family First's Melanie Milutinovic
while recorded exclusion is DLP's Zuzanna Brown. Exact evidence for Milutinovic
comes from a later field, so cannot be used without extrapolation.

Five requested examples on historical candidate primaries:

- Morwell completes: LNP–ALP, LNP54.61%.
- Pascoe Vale completes: ALP–GRN, ALP51.98%.
- Pakenham, Ashwood and Yan Yean stop on changed minor-candidate exclusions.

These are not forecasts at ON18 and not results of the live corrected VEC
option. Completed results use known candidate evidence; do not infer54-seat
forecast coverage or general accuracy.

Next recommendation: when exact within-candidate evidence exists, preserve it
rather than replacing it with proportional allocations. Retain proportional
allocation only as an explicitly uncertain fallback. For unseen same-category
fields, consider pooled subtype evidence on exact broad fields, with source
and coverage reporting, rather than100% same-category retention or nearest-field
renormalisation. That further fallback has NOT been implemented or approved.

Live app, Sheet inputs and ON rules unchanged. Per-seat stop diagnostics:
`candidate_endogenous_count.json`.
