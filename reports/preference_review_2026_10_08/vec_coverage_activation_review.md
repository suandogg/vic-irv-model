# Coverage correction activation and Ringwood review

Fixed frozen 8 October inputs; identical primaries across all three methods.
Production federal evidence and parcel-origin retention are included, unlike
the independent conditional-flow validation. This is forecast sensitivity,
not independent accuracy validation. No new settings or defaults changed.

## Activation inventory

| Scenario | Corrected holder rounds | Seats |
|---|---:|---:|
| 2022 statewide-input scenario | 150 | 76 |
| ON18 | 17 | 17 |
| ON20 | 8 | 8 |
| ON24 | 5 | 5 |

Counts concern actual-contest holder diagnostics only. They exclude forced-2PP
counts and separately calculated primary-origin preference calls; they are
not an exhaustive count of every engine invocation affected. Lower activation
at higher ON reflects ON staying alive, where the correction is inactive.

## Ringwood at ON18

Same primary shares: ALP31.635%, LNP36.920%, GRN16.319%, ON11.558%,
OTH3.567%, IND effectively zero. Same elimination order in every variant:
IND, OTH, ON, GRN. IND is a tiny numerical residue, not meaningful support.

| Method | Effective final GRN-held parcel to ALP | Final ALP share |
|---|---:|---:|
| Reference | 77.945% | 50.339% |
| Exact-field VEC, original coverage | 77.942% | 50.338% |
| Exact-field VEC, corrected coverage | 75.935% | 49.837% |

The correction makes the final GRN-holder lookup select complete field-matched
VEC evidence rather than a posterior-based blend. Its historical primary-origin
GRN row projects to ALP80.553%, then geography increases this to83.553%.
However, the effective eliminated parcel sends only75.935% to ALP because it
also contains votes originally cast for other parties, whose origins are retained.
Do not interpret the effective parcel share as the share of Greens primary
voters preferring ALP.

There is also an earlier origin-accounting effect when ON is eliminated:
effective ON-held parcel to LNP changes from59.044% to60.142%. Holder-level
ON evidence selection is unchanged; re-evaluating other origins within that
parcel can use the corrected exact-field non-ON records. Thus unchanged ON
rules do not mean identical aggregate flows from an ON-held parcel.

ALP's final share falls0.502 points, flipping a very narrow result rather than
creating a large unexplained swing. This is methodologically explainable,
not proof either forecast is correct. The scenario has no known outcome.

## Recommendation

Keep the correction as the preferred exact-field experimental option, without
a production default switch yet. Complete the remaining provenance check on
primary-origin activations and candidate/category aggregation before expanding
its scope or introducing pooled evidence into live forecasting. No evidence
here supports changing ON special priors or tuning to preserve Ringwood for ALP.

Full inventory and traces: `vec_coverage_activations.json`.
