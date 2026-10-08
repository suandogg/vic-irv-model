# Live OTH construction audit — 8 October 2026

Read-only inspection of PARAMS A1:G25 and SYNTH PREF MATRIX I1:O880 in spreadsheet 1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro confirmed the frozen audit's OTH-to-ON values. There are no formulas in the inspected synthetic blocks: these are stored numeric values, not live PARAMS references.

| Matrix seat class | Seats differing | Stored OTH→ON | Current PARAMS |
|---|---:|---:|---:|
| Inner Ring | 13 | 30% | 25% |
| Middle Ring | 18 | 40% | 35% |
| Outer Metro | 19 | 50% | 45% |
| Peri-urban | 14 | 55% | 50% |
| Regional | 16 | 60% | 50% |

All 80 discrepancies follow these class-wide patterns. Seven Provincial seats match at 50%; Narracan has an empty OTH row and was excluded from the discrepancies. The frozen construction audit also confirms non-ON destinations match proportional scaling using the stored ON share, within rounding tolerance. This is a coherent alternative set of assumed priors, not 80 unrelated arithmetic errors.

We cannot determine from current cells whether PARAMS was subsequently reduced or the stored matrix deliberately used different priors. No spreadsheet settings or production preference values were changed by this audit. Stored OTH→ON percentages are full-row inputs, not necessarily the effective transfer after field projection, evidence blending, depletion, geography, caps and special priors.

Recommendation: retain historical evidence where the continuing field supports it; make synthetic ON assumptions an explicit, reproducible fallback, with missing historical recipients distinguished from observed zeros. Before broad redesign, isolate a trial rebuilding only OTH rows from current PARAMS, leaving ON_SPECIAL_SCENARIO_PRIORS and every other transformation unchanged. Compare the established fixed-primary scenarios and five demonstration seats. Historical reconstruction can test non-ON behaviour, but cannot establish accuracy in high-ON Victorian scenarios.
