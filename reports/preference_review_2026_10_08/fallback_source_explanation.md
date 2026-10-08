# Which fallback was replaced?

The ordinary engine chooses a complete matrix row, otherwise an exact-field
posterior, otherwise a special prior, otherwise the generic IDEOLOGY prior,
then a partial matrix or uniform fallback. It can anchor the selected vector
to the matrix and apply later transformations. Exact federal evidence wraps
that rule and blends with it. Special priors bypass later transforms when
selected. This is not the candidate-level IdeologyFamily classification.

The matrix-source-only trial replaces the generic selection in ON-related
calls with the matrix, while retaining geography, siphon, floors and caps.
Special priors are locked and exact federal blending remains. It changes
ballot-origin calls as well as eliminated-holder calls, because parcels retain
their primary-party origin.

## First meaningful flow change in each ON18 example

| Seat | Reference round | What was displaced |
| --- | --- | --- |
| Pakenham | 1, IND eliminated | Generic IND ideology prior |
| Morwell | 2, OTH eliminated | Generic OTH prior, plus the underlying GRN prior on transferred GRN-origin votes |
| Pascoe Vale | 1, OTH eliminated | Generic OTH prior underneath the retained federal blend |
| Ashwood | 2, IND eliminated | Generic IND prior |
| Yan Yean | 3, OTH eliminated | Underlying GRN prior on Greens-origin votes; the OTH-origin matrix flow itself is unchanged |

Ashwood has a numerically positive but negligible OTH primary pile in round 1.
Its first flow-share difference therefore has effectively zero vote impact.
The table uses the first round where a recipient's seat-vote change exceeds
0.00001 percentage points, so it does not mistake numerical dust for a driver.

For Pakenham's IND pile, reference effective flows to ALP/LNP/GRN/ON/OTH are
24.41/26.97/9.89/30.01/8.73 percent. Matrix-source-only gives
30.16/33.82/0.50/35.03/0.50 percent. It reallocates support away from GRN and
OTH to both major parties and ON. A higher initial ALP transfer does not imply
a higher final ALP 2PP: later parcel redistributions and elimination order matter.

These are counterfactual calculations on identical reference-path parcels.
The trial's actual path is retained separately in five_seat_source_trace.json.
After paths diverge, counterfactual round effects must not be presented as the
trial's actual count or summed into a causal final-margin decomposition.

## Interpretation and next step

In these examples the main contrast is generic-prior versus synthetic-matrix
behaviour, not removal of an observed historical posterior. The synthetic rows
can have zero support for continuing destinations; this is not automatically
evidence that those voters would never preference those destinations.

Next inspect provenance of those zero/missing entries and the generic prior's
construction. A field-aware hybrid should preserve credible observed flows,
use explicit assumptions for unsupported destinations, and avoid treating a
compressed synthetic matrix as fully observed evidence. Neither generic prior
nor synthetic row is established as more accurate by this trace alone.

No reference or Sheet defaults changed.
