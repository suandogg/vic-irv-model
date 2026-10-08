# ON evidence provenance and holdout findings

## Evidence inventory

The frozen Victorian federal source contains 283 destination records from 38
electorates, representing 76 seat-scenarios in 11 exact continuing fields.
All are proportional primary-origin pass-through reconstructions from AEC
candidate-round category exits. They are not observed complete ballot rankings.
Validation rejects duplicate keys, missing destinations, conflicting totals,
non-Victorian rows and inconsistent vote/share values. All checks passed.

Two fields have only one seat and cannot be held out. Nine fields support
seat holdout, but one has only two seats: its training set falls below the
production minimum of two evidence seats after holding one out.

## Seat-blocked federal consistency test

Every held-out seat is removed before estimating its exact-field pool. The
production-eligible subset contains 72 held-out seat-scenarios across 38 seats.
Errors are averaged over destinations within each scenario, over scenarios
within each seat, then equally over seats.

| Comparator | Seat-balanced absolute flow-share error |
| --- | ---: |
| Equal-seat pool | 5.04 percentage points |
| Vote-weighted pool | 5.13 percentage points |
| Equal-seat pool shrunk toward uniform with 20 prior seats | 10.62 percentage points |
| Uniform destinations | 14.23 percentage points |

This supports equal-seat pooling as a reasonable baseline within this source.
The small difference from vote pooling is not a demonstrated statistically
significant advantage. Shrinking toward uniform performs worse, but this does
not discredit production shrinkage: production shrinks toward the Victorian
rule, not uniform. That comparator intentionally tests an uninformed prior.
Zero average signed error for unshrunk equal-seat leave-one-out predictions is
a mathematical property of this design, not evidence of unbiased forecasting.

Neither state-election transfer nor reconstruction assumptions are validated.
The per-seat predictions and exact fields are retained in federal_holdout.json.

## Consequential evidence gaps

Most coverage concerns ON as the eliminated origin or OTH sending preferences
with ON alive. GRN recipient-ON fields have three seats each. There is one
ALP→IND+LNP+ON seat. There are no LNP-eliminated fields and no multi-seat
ALP-eliminated fields in this source. The crucial final ALP/ON and LNP/ON
contests therefore remain governed by specified priors, not empirical evidence
from these federal observations. Absence of a field is not a zero flow.

## ON assumption overlap in current code

1. The matrix loader reads the synthetic side of SYNTH PREF MATRIX, but the
   engine calls it a raw/full AEC row. Across 88 seats, 244 non-ON origin rows
   have positive ON entries. Those labels do not establish observed provenance.
2. Generic paths select a matrix/posterior/prior, may anchor to that same
   synthetic matrix, then apply additive geography, generic ON siphon, floors
   and caps. Multiple layers can encode ON support. This is an overlap risk,
   not proof that any particular coefficient is duplicated.
3. Exact federal evidence wraps the complete Victorian rule and blends toward
   the federal pool. The active config removes the generic siphon from that
   underlying rule, but retains its synthetic matrix and geography assumptions.
   Thus federal-supported flows are not evidence-only predictions.
4. When a special prior is selected in the ordinary path, later geography,
   siphon, floors and caps are bypassed. The federal wrapper has earlier
   priority if a matching evidence record exists. The current source fields
   do not include final ALP+ON or LNP+ON, so those final special fields are not
   displaced by this frozen federal table. That protection should be an
   explicit invariant before adding more evidence fields.

## Recommended next design trial

Create provenance-aware basis selection rather than calling all complete
synthetic rows AEC evidence. Trial one explicit ON extrapolation rule on
unsupported fields, and estimate its residual geography independently.
Keep special priors locked. Compare the full current rule against alternatives
on held-out federal flows only where sources, origin semantics and fields are
comparable. Do not use a Victorian district as a proxy for a federal seat, or
claim a federal holdout establishes state accuracy.

Before a production change, agree whether synthetic ON support should be the
single fallback baseline or whether an explicit recipient-ON prior should
replace it. The existing special-prior values need not change for either
option. No production or Sheet settings were changed by this audit.
