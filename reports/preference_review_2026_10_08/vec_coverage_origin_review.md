# Primary-origin activation audit

The previous holder-only inventory understated reach. A holder can use its
unchanged rule while a parcel originating from another party uses corrected
exact-field evidence. This is existing parcel-origin retention, not a new ON
rule. Audit uses the same fixed primaries and corrected count trajectory;
each affected lookup is compared with correction disabled on the same field.

| Scenario | Holder-affected seats | Origin-affected seats | Corrected parcels | Of those held by ON |
|---|---:|---:|---:|---:|
| ON18 | 17 | 64 | 81 | 64 |
| ON20 | 8 | 53 | 61 | 53 |
| ON24 | 5 | 37 | 42 | 37 |

These are parcel lookup counts, not individual ballots or separate winners.
They include positive numerical residuals. Requiring parcel mass above1e-6 of
the seat total leaves79,60,41 corrected parcels respectively. The 2022
statewide-input scenario has188 corrected parcels, none held by ON.

## Ringwood mechanism

At ON elimination, the corrected lookup belongs to OTH-origin votes comprising
1.546% of the total seat vote. Its flow to LNP increases9.299 percentage points
and to GRN decreases9.336 points; ALP increases0.037 points. This reallocates
approximately0.144 points of the seat total to LNP. ON-primary-origin lookup
is not corrected. At subsequent GRN elimination, GRN-primary votes (16.319%
of seat vote) send2.616 points less of their parcel to ALP. This explains why
both earlier parcel composition and the final transfer contribute to the flip.

## Protected invariants

1,879 evaluated parcel comparisons across all four scenarios had identical
flow dictionaries with correction on/off whenever ON remained continuing or
the holder selected a locked ON special prior. Assertions also cover the
special-prior path where other origins must inherit the holder's locked rule.
This is empirical invariant coverage on these scenarios, not exhaustive proof
for all possible inputs. Stored ON allocations remain unmodified by the code.

## Assessment

The correction is operating consistently with retained primary-origin logic.
Its reach is materially wider than17 seats, so do not present it as a17-seat
change. Retain the opt-in experimental option. Before default adoption, compare
candidate/subtype reconstruction and check sensitivity of parcel retention:
the exact category-origin targets themselves rely on proportional reconstruction
of origin holdings, not observed ballot rankings. No settings/defaults changed
in this audit; high-ON accuracy remains unestablished.
