# Exact historical-field VEC trial

238 extracted non-ON category-exit records are attached as separate field-keyed metadata. They are not rewritten into the general-purpose matrices. At a preference call, a record is eligible only when its historical field equals the current field after removing synthetic ON. Native historical ON records and fields are excluded from this first comparison. A special ON prior's field is never replaced. Unmatched fields retain reference rules.

For an eligible row, replace only the historical non-ON conditional split using extracted primary-origin pass-through shares. Preserve the existing row's stored ON allocation and scale historical shares by 1-stored_ON, just as in the original synthetic construction. No new ON extrapolation rule is introduced. Source selection, federal blending, geography, siphoning, constraints, primary calculations and incumbent settings remain unchanged. Their effective outcomes can still change in response to the altered non-ON split; unchanged ON rules do not guarantee identical final ON votes.

Fixed-primary results:

| Scenario | Reference ALP/LNP/GRN/ON | Exact-field trial | Changed winners |
|---|---|---|---:|
| ON18 | 38/42/5/3 | unchanged | 0 |
| ON20 | 31/44/5/8 | unchanged | 0 |
| ON24 | 26/38/5/19 | 25/38/5/20 | 2 |

At ON24, Monbulk changes LNP→ON and Mordialloc changes ALP→LNP. The baseline-input scenario also has no changed winners. ON finalist counts are 22 unchanged at ON18, 34→33 at ON20 and 49→50 at ON24.

For ON18, all demonstration winners and final pairs are unchanged. Forced ALP–LNP 2PP changes: Pakenham -.000022 pp, Morwell 0, Pascoe Vale +.001572 pp, Ashwood +.000593 pp and Yan Yean +.033211 pp. Morwell remains unchanged by design because its extracted non-ON-origin fields contain native ON and were excluded. Other seats may also have no eligible exact field in some count calls, so small changes are not a validation of all historical data.

Actual-primary 2022 reconstruction MAE improves 1.827→1.782 pp over the same 85 comparable final pairs. Winner and final-pair accuracy are unchanged. This uses the same seat's extracted evidence and is an in-sample consistency check, not forecast validation. The strict leave-one-seat-out mode deliberately does not insert these own-seat records. Do not report an independent VEC-field holdout improvement until a separate pooled-field test excludes all held-out seat evidence.

28 regression tests pass, including exact-field eligibility, preservation of stored ON share before transforms, unmatched-field invariance, special-prior invariance and non-mutating metadata attachment. Original/reference spreadsheet matrices remain unchanged. The laboratory switch is optional and default remains Current reference.

Recommendation: retain the exact-field design as a development candidate, not a production switch yet. Its explicit field provenance is methodologically preferable to using a compressed historical row indiscriminately. Next establish pooled exact-field leave-one-seat-out behaviour and report activation coverage before combining with the OTH PARAMS rebuild or adjustment changes.
