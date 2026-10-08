# Approved subtype fallback integrated into candidate shadow

Hierarchy now accepts exact candidate-field evidence first, then a callback
supplying same-subtype evidence on an exact continuing broad-category field,
minimum3 distinct other seats, with proportional allocation to candidates.
Insufficient evidence stops explicitly. Exact candidate data retain precedence.

Validation removes all own-seat evidence and chooses eliminations endogenously
using actual historical candidate primaries. Native ON fields/origins remain
outside the pool; no new ON insertion. This is a sparse conditional count
diagnostic, not a high-ON forecast or a new live app mode.

Results:35 of88 complete;34 correct winners,35 correct final candidate pairs.
Northcote's winner changes toGRN instead ofALP.53 unresolved seats must not be
omitted when assessing coverage or presented as correct.48 stop while excluding
an OTH candidate,3 LNP,2 IND;31 of53 have another same-category candidate alive.

Ashwood completes ALP–LNP. Laverton, Kororoit, Pakenham, Morwell, Pascoe Vale
and Yan Yean stop for missing compatible training fields. With own-seat exact
observations available, the earlier88-seat reconstruction remains the reference
implementation test; the held-out count deliberately does not use those records.

Strong conditional parcel coverage (466/537 observed targets) does not imply
strong full-count coverage: changed elimination paths request unobserved field
combinations, and a single unresolved round stops a seat. This is a useful
finding, not a reason to silently add nearest-field extrapolation.

Recommendation: retain the current live six-category engine and corrected
exact-field option. Candidate shadow needs a reviewed policy for sparse unseen
fields before it can become a complete alternative. First inventory missing
subtype/field combinations and candidate-count differences; then choose whether
to gather more evidence or design an explicit shrinkage/fallback model. Do not
lower evidence minimums or add broad-category/nearest-field fallback by default.

No Sheet, app default or ON prior changed. Detailed output:
`candidate_subtype_count.json`.
