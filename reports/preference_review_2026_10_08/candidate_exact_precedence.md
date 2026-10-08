# Exact candidate recipient precedence

The endogenous shadow now preserves candidate-to-candidate shares when exact
continuing-candidate-field evidence exists. Proportional allocation remains a
fallback only when matching category evidence exists but candidate shares do
not. Unmatched fields still stop explicitly. No nearest-field or new ON rule.

With actual historical primaries, all88 seats complete versus54 when known
recipient shares were replaced by proportional allocation. All final candidate
pairs match recorded replay; final share differences are numerical rounding
only. No proportional fallback is needed in this historical run.

This is an implementation/data reconciliation test, not independent validation:
the same election supplies the exact transfers. It establishes that the34
earlier stops were caused by replacing observed recipient allocations, not
inherent missing historical data. It does not establish how proportional
fallback performs on unseen fields, or forecast accuracy with synthetic ON.

Laverton, Kororoit and all five demonstration seats now reconstruct their
recorded candidate finals. The candidate engine remains development-only.
Live app count, Sheet inputs, ON allocations and defaults remain unchanged.

Next design decision: supply evidence for unseen candidate fields, especially
same-category recipients, without silently adding nearest-field projections.
An exact broad-field subtype pool is one possible shadow fallback; its use,
minimum evidence and unresolved handling need explicit review before expansion.
