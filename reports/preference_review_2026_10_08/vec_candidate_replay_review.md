# Candidate replay: distinguish aggregation from preference error

Replayed recorded candidate-level transfers for all88 seats. Total votes are
conserved after every recorded distribution; eliminated parcel tallies reconcile
within the extraction's existing tolerance (max25 votes or0.5%). This is a
data reconciliation, not predictive validation: it follows known eliminations
and known transfers rather than estimating either. No ON insertion or nearest
field matching is used. Indicative source records retain their existing status.

Laverton: ten candidates, including six OTH. Five OTH candidates leave before
the last OTH candidate; all OTH candidates leave before GRN. After the final
OTH elimination the real continuing field is ALP52.15%, LNP27.80%, GRN20.06%.
The final recorded result is ALP68.39%, LNP31.61%. Immediately after IND leaves,
combined OTH22.27% marginally exceeds LNP22.25%, but this does not eliminate
LNP: six separate OTH candidates remain, many with much smaller individual tallies.

Kororoit: nine candidates, including five OTH. Three OTH candidates have already
left by the time GRN leaves. Following GRN elimination, LNP has27.57% and the
two remaining OTH candidates together have22.75%. They then leave separately.
The final recorded result is ALP64.52%, LNP35.48%.

This confirms why keeping the entire original OTH pool alive as one candidate
changes the field and elimination sequence. It does not establish that all
pooled share errors are aggregation artefacts, nor validate a new forecast count.

The older candidate-shadow script was inspected but not reused: it introduces
nearest candidate-field projection, same-category fallback and an ON-origin
allocation rule as well as changing the counting units. Those would confound
the current isolation trial and conflict with keeping the ON method constant.

Next candidate-shadow design needs an explicit within-category recipient rule:
the existing six-party engine cannot distinguish transfers to two candidates
of the same category, including when the eliminated category remains alive.
Recorded exact candidate transfers can supply historical reconstruction, but
unseen fields and hypotheticalON contests need stated modelling assumptions.
Do not silently invent that rule or claim a candidate-level forecast already
exists. Candidate/subtype shadow should remain non-production until approved.

No app, Sheet or default changed. Full per-seat round replays are in
`vec_candidate_replay.json`.
