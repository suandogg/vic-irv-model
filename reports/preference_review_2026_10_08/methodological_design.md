# Methodological design and separated geography tests

Primaries, other rules and special-prior values are fixed.

| Scenario | Reference ON seats | No ON-recipient addition | No non-ON-recipient additions |
| --- | ---: | ---: | ---: |
| ON18 | 3 | 2 | 3 |
| ON20 | 8 | 7 | 8 |
| ON24 | 19 | 17 | 21 |

Changed winners number 1/1/2 for the first ablation and 4/5/6 for the second.
Equal party totals can conceal different seat winners. These are sensitivity
results, not accuracy claims.

Actual-primary conditional 2022 holdout MAE is 1.820 points for reference,
1.820 without ON additions and 1.719 without non-ON additions. Historical
improvement concerns established-party geography, not validation of ON flows.

## Mechanism

Geography currently adds party-specific amounts, clips negative weights and
normalises the result. Removing non-ON additions therefore still changes ON's
share. Additive adjustments have different relative impacts on small and large
base shares. Clipping and elimination thresholds introduce non-linear effects.
Applying a class adjustment to already local evidence may double-count a
pattern; that requires a source-specific audit, not an assumption.

## Rigorous direction — proposed, not production changes

1. Separate observed, compressed, synthetic and user-specified evidence.
   Preserve election, electorate, field and ballot-origin provenance. Synthetic
   ON entries should not inherit the confidence of observed complete rows.
2. Audit overlapping ON assumptions in matrices, geography and siphon. Aim for
   one explicit extrapolation layer. Keep ON_SPECIAL_SCENARIO_PRIORS outside
   additional transforms.
3. Estimate residual class effects using held-out observations, controlling
   for source composition. Do not automatically add class effects to exact
   local evidence. Sparse ON data warrants shrinkage and sensitivity.
4. Trial normalised relative-weight/log-odds adjustments against additive
   adjustments. Estimate coefficients rather than reusing additive values.
   A relative-weight rule cannot create ON support from a zero baseline;
   unsupported destinations need an explicit extrapolation prior first.
5. Validate components separately: Victorian history for non-ON flows;
   Victorian federal seat holdouts for ON relationships. Measure flow errors
   as well as count paths. Federal-to-state transfer remains an assumption.
6. Report uncertain fields, unstable seats and thresholds under plausible ON
   assumptions. Do not label sensitivity frequencies calibrated probabilities.

Next diagnostic: inventory source provenance and overlapping ON adjustments,
then identify observations suitable for held-out ON-flow tests. Present a
specific alternative transformation and its coefficients for approval before
changing the reference model. Do not tune to increase ALP seats or match
another commentator's seat count.

The trial does not change production defaults, Sheets, special-prior values,
primaries or Council rules.
