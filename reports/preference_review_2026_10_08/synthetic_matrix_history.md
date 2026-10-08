# Synthetic matrix construction recovered and checked

The reference brief section 5.3 records the original construction recovered
from historical discussions: copy the five-party manually compiled Victorian
row; insert an ON share from a seat-class/origin prior; scale all existing
destinations by 1 minus that share. The ON elimination row is a separate
seat-class prior. Primary-vote donor settings are a different mechanism.

For illustration, an original 80% ALP / 20% LNP row with a 20% inserted ON
share becomes 64% ALP / 16% LNP / 20% ON. This example is not a seat observation.

The frozen input audit finds:

- 88 seats and 528 synthetic rows.
- 244 non-empty five-party historical rows. All 244 match proportional scaling
  using the ON share stored in the synthetic matrix, within 0.01 percentage
  points. This establishes numerical consistency, not exclusive provenance.
- 196 empty historical rows remain empty in the synthetic side.
- All 88 ON distribution rows match the current ON-row prior table.
- 448 total rows match the formula using current prior-table values. The 80
  mismatches are all OTH-origin rows, not general failures of the scaling rule.

| Seat | Stored synthetic OTH→ON | Current ON-column OTH prior |
| --- | ---: | ---: |
| Pakenham | 55% | 50% |
| Morwell | 50% | 50% |
| Pascoe Vale | 40% | 35% |
| Ashwood | 40% | 35% |
| Yan Yean | 55% | 50% |

The Python matrix loader reads the synthetic values. It does not rebuild them
from the current ON-column/row settings at runtime. Consequently a prior-table
edit is not by itself proof that the effective synthetic row changed. The
frozen CSV cannot show whether the live Sheet difference comes from a deliberate
formula adjustment, stale values or another rule; inspect formulas/history
before labelling it a bug. No values were repaired by this audit.

## Why this can be problematic

The scaling preserves zero non-ON destinations. A historical zero could reflect
an already-eliminated candidate, an absent candidate, candidate compression or
an actual zero flow. The flattened row alone cannot distinguish these cases.
Treating that zero as voter aversion when the candidate is now continuing is
not justified without field provenance.

ON shares are assumed by seat class, not observed for each reconstructed
state field. Later geography and siphoning can add further assumptions. The
engine's historical "AEC row" label does not convert the synthetic row into
direct empirical evidence. Exact-field scenario evidence and federal blending
can mitigate these limitations, but still anchor or shrink toward this matrix.

Recommendation: treat this construction as a prior, not a universal observed
transfer matrix. Preserve/reconstruct actual continuing fields from candidate
data, identify unknown destinations explicitly, and use one documented ON
insertion layer. First trial rebuilding the stored rows from current prior
settings separately from a field-aware redesign; do not conflate the changes.
Special priors should remain locked. No reference, app result or Sheet setting
changed in this audit.
