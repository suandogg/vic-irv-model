# ON strength concentration versus geographic uncertainty

## Main conclusion

The current central ON distribution is already based on district-specific
`ON_strength`, not simply a regional/metro label. The code describes these as
SA1-derived inputs; their underlying construction was supplied earlier in the
project. This audit verifies how the model uses that column, not an independent
reconstruction or validation of the original SA1 data.

The analyst's suggestion is therefore closely related to how strongly that
existing signal should persist. It is separate from uncertainty about whether
the signal is right. Concentrating the central pattern more can make some ON
seats **more certain**, rather than solve overconfidence.

## Existing mechanics

Before the rest of primary construction and calibration:

`ON_weight_i = max(ON_strength_i, 0) ** alpha`

The weights are divided by their equal-seat mean and multiplied by the statewide
ON input. Then the production primary pipeline normalises/calibrates, applies
configured donor construction, candidate adjustments and LNP precollapse.

At alpha 0.6, differences in strength are flattened. At alpha 1.0, the raw input
ratios are retained at the weight stage. For example, a two-to-one strength
ratio becomes approximately 1.52-to-one at alpha 0.6 versus two-to-one at 1.0.
Those are initial weight ratios, not guaranteed final seat vote-share ratios.

The seat-class donor matrix is a separate mechanism specifying which parties
supply ON votes. It remains at the committed 0.35 blend in this experiment.
Its calibration feedback can also affect the final seat pattern; it is not
being removed here. Geography also features in preference adjustments and
regional simulation errors—different mechanisms again.

## Controlled trials

Compared alpha centres 0.4 (flatter), 0.6 (current), and 1.0 (strength concentrated).
These are illustrative scenarios, not fitted estimates. Existing alpha uncertainty
SD 0.08 remains around each centre during simulation. All other central settings,
preference architecture and uncertainty settings are held fixed.

Central scenario: ALP 24.6 / LNP 29.1 / GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5.
Committed inputs, not live Sheets or a new poll average. Three seeds, 100 draws
each per pattern, pooled to 300; 900 simulated elections. Statewide targets and
other underlying errors are paired across patterns. No mixture weights assigned.

The experiment verifies central ON averages exactly 22% under all patterns and
seat shares sum to 100%. Existing LNP precollapse can move ALP/LNP/IND aggregates
after primary calibration; it is retained, not silently recentered. Accordingly,
this is not a claim that all six post-precollapse means equal the original inputs.

| Pattern | Alpha centre | Lowest seat ON primary | Highest seat ON primary | Central ON seats | Forecast ON mean seats |
|---|---:|---:|---:|---:|---:|
| Flatter | 0.4 | 12.62% | 30.88% | 11 | 10.6 |
| Current | 0.6 | 9.33% | 35.89% | 15 | 13.4 |
| Strength concentrated | 1.0 | 4.86% | 46.25% | 21 | 18.2 |

Central seats are one deterministic outcome; forecast means average the simulations.
ON 5th–95th seat ranges are respectively 2–23, 4–26 and 7–30. The full central
winner map changes in eight seats under flatter and six under concentrated,
relative to Current. These scenario differences are not a calibrated interval.

## Five demonstration seats

| Seat | Central ON primary: flatter / current / concentrated | ON win probability: flatter / current / concentrated |
|---|---|---|
| Pakenham | 25.83 / 27.45 / 30.41% | 19.3 / 30.0 / 52.0% |
| Morwell | 30.88 / 35.89 / 46.25% | 34.0 / 71.7 / 99.0% |
| Pascoe Vale | 20.30 / 19.38 / 17.32% | 0 / 0 / 0% |
| Ashwood | 16.10 / 13.49 / 9.15% | 0 / 0 / 0% |
| Yan Yean | 23.36 / 23.89 / 24.58% | 47.3 / 51.7 / 59.3% |

Zero wins means none in these 300 draws, not impossibility. For Ashwood, Labor's
win frequency moves from 17.7% to 29.7% between flatter and concentrated; reduced
local ON strength can affect the major-party contest even where ON never wins.
Pascoe Vale Labor frequencies are approximately 59.7 / 61.0 / 61.0%.

Other large ON probability sensitivities include Mildura (11.0–78.3%),
Shepparton (3.7–52.7%) and Narre Warren North (31.0–70.0%). Finite simulation
noise remains; these ranges compare different assumptions, not a confidence band.

## Does this reduce certainty?

Separately run pattern forecasts have 40, 40 and 39 seats at or above 98%,
respectively. Changing the central concentration does not broadly soften
probabilities. It mostly changes which party is favoured and where.

The useful new information is **between-pattern sensitivity**. A forecast that
only samples alpha close to 0.6 may omit alternatives such as 1.0 unless their
plausibility is reflected in the uncertainty model. Equally, placing weight on
1.0 without evidence could overstate ON's prospects. Neither direction should
be selected to engineer desired seat totals or fewer high-confidence seats.

All three patterns use the same strength column and initial ranking. They do
not test a new regional ranking, alternative election data, candidate-field
uncertainty, or whether the input strength measure transfers well to this election.

## Recommendation

1. Keep the central alpha unchanged pending evidence/review. The analyst's
   suggestion is worth examining, but the model already contains a strength-based
   index. Ask whether they mean retaining its ratios more strongly, or using a
   different source of measured strength entirely.
2. Use these scenarios as a transparent sensitivity envelope. Flag seats whose
   calls depend on the pattern, rather than treating a conditional 99% result as
   robust to geography uncertainty. Do not average scenarios with arbitrary weights.
3. Next compare a genuinely different strength source/pattern if suitable
   district-comparable data exist—for example the previous state upper-house
   ON vote versus the existing federal-SA1-derived index. That requires checking
   ballot coverage, aggregation and transferability; no such replacement has
   been constructed here.
4. Once plausible concentration/pattern alternatives are justified, model their
   uncertainty as a coherent election-wide component. Avoid double-counting
   the alpha SD, regional shocks and a new pattern component. It should remain
   sheet-controlled if adopted, with clear central-versus-uncertainty settings.

## Artifacts and scope

`on_strength_patterns_2026_10_28/` contains central primary/winner tables,
per-seed probabilities, pooled seat probabilities, party ranges, a sensitivity
envelope and a reproduction manifest. Reproduce using
`python tools/trial_on_strength_patterns.py` in the project environment.

No app calculation, trial dropdown, Sheet, Main, default alpha, donor setting or
preference row was changed. This stage adds the audit script and results only.
