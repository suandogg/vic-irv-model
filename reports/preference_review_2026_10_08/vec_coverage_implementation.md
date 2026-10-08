# Exact-field coverage correction implemented

Experimental option: **VEC exact fields with corrected coverage**.

Only when VEC evidence matches the historical continuing field exactly and ON
is not continuing, recognise coverage as one. Stored synthetic ON allocation
is not changed. Existing positive-recipient checks, geography, floors/caps,
posterior hierarchy and federal blending remain. Special ON priors are excluded
from VEC matching and remain locked. Legacy/unmatched rows are unaffected.

This is opt-in, not a default switch; the reference app and Sheets are untouched.
On the 234 held-out conditional-flow targets, mean half-L1 error improves from
13.477 to 11.535 percentage points. This is conditional category-origin accuracy,
not independent validation of high-ON forecasts or candidate elimination order.

Fixed scenarios versus reference:

- 2022 statewide-input scenario: no winners change (not actual historical reconstruction).
- ON18: Ringwood ALP to LNP; totals ALP37, LNP43, GRN5, ON3.
- ON20: no winners change.
- ON24: Monbulk LNP to ON, Mordialloc ALP to LNP, as in the prior exact-field trial.

ON18 ALP forced-2PP changes versus reference: Pakenham -0.033 points,
Morwell zero, Pascoe Vale +0.003, Ashwood -0.288, Yan Yean -0.179.
All five retain their forecast winners.

The correction is deliberately inactive while ON is continuing, avoiding
reinterpreting synthetic ON evidence strength from a non-ON historical target.
Direct ON-containing scenario weights stay the same as the prior exact-field
option; downstream results can change following earlier non-ON rounds.
