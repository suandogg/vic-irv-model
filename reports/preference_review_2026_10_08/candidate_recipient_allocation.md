# Proportional candidate recipients: first isolated test

Implemented the approved split by current candidate tallies in a development
allocator. It preserves each supplied category's flow mass and does not invent
inter-category preferences or ON allocation. Invalid shares and zero-mass
recipient groups raise an explicit error instead of silently using equal shares.

First test uses recorded candidate elimination order and recorded category
transfer proportions, replacing only recipient allocations within categories.
Transferred parcel size is the shadow candidate's current tally. Votes are
conserved across88 seats. This is an in-sample controlled diagnostic, NOT a
candidate-level forecast, independent validation, or statutory result replication.

In34 seats the shadow's lowest candidate differs from the recorded exclusion
at least once. The test continues on recorded order, so its final outcomes
cannot establish unconstrained count accuracy. Laverton has no such divergence;
ALP share68.45% versus recorded68.39%. Kororoit diverges at round4; ALP64.57%
versus recorded64.52% on the forced historical sequence.

This supports proportional allocation as a transparent starting approximation,
not as observed preference behaviour. Next implement an endogenous count that
uses exact candidate evidence only on matching fields; when a changed field
still includes the eliminated candidate's category, inter-category transfers
need evidence or an explicitly approved fallback. The six-category engine does
not supply own-category flow. Do not assume100% same-category retention or
reintroduce nearest-field projections without approval.

Live app, Sheets, ON rules and default six-category count remain unchanged.
