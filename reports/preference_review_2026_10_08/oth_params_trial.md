# Isolated OTH→ON PARAMS rebuild

The selectable `oth_params_rebuild` variant changes exactly 80 OTH synthetic rows, rebuilding the five historical destination shares times (1-current OTH ON prior), and inserting that prior into ON. Seven matching Provincial rows and Narracan's empty row remain byte-for-value unchanged. Other matrix rows, primary inputs, source hierarchy, federal evidence blending, geography, siphon, constraints and ON_SPECIAL_SCENARIO_PRIORS are unchanged. Parameters and original matrices are deep-copied rather than mutated. The copied Google spreadsheet has not been rewritten: the switch computes this trial from its inputs.

Fixed-primary tests:

| Scenario | Reference ALP/LNP/GRN/ON | Trial ALP/LNP/GRN/ON | Changed winners |
|---|---|---|---:|
| ON18: 29/32/12/18/4.5/4.5 | 38/42/5/3 | 38/43/5/2 | 1 |
| ON20: 25/30/14/20/5.5/5.5 | 31/44/5/8 | unchanged | 0 |
| ON24: 25/28/12/24/5.5/5.5 | 26/38/5/19 | unchanged | 0 |

Eureka changes ON→LNP in ON18. ON reaches the final two in 20 rather than 22 seats in ON18, 34 unchanged in ON20, and 48 rather than 49 in ON24. All five demonstration seats retain their winner and final pair in ON18. Forced ALP–LNP 2PP changes are under .003 percentage points in all five seats; that is not a claim that their ON-inclusive final margins are unchanged.

Actual-primary 2022 conditional reconstruction MAE moves 1.827→1.786 pp. Seat-class matrix leave-one-seat-out MAE moves 1.820→1.809 pp. Comparable final pairs remain 85/88 and winner accuracy is unchanged. The gain is small and cannot validate high-ON Victorian predictions; these are matrix-conditional checks, not fully independent historical validation.

Interpretation: reducing a full-row ON assumption need not materially change forced ALP–LNP outcomes because projection/pass-through and later transfer rules can preserve the historical non-ON balance. It can change elimination order or an ON finalist in close contests. This narrow repair has a substantially smaller effect than replacing the engine's source-selection hierarchy. It is a consistency trial, not an assertion that current PARAMS values are empirically optimal.
