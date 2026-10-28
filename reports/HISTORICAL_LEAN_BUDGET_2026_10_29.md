# First evidence-informed district-lean budget — 29 October 2026

## Decision

There is now a concrete historical estimate for the **established-party, ordinary-field component** of the structured nowcast. It is a useful starting budget, not an activated or fully calibrated forecast. No new win-probability claims are made in this stage.

Do not apply the historical all-seat spread as independent local noise on top of existing regional and concentration uncertainty. The regional and local components below are estimated jointly from one historical transition and should replace the corresponding existing budget when used.

## Inputs and geography

The input is the independent official candidate-primary panel assembled for 2014/2018. Both elections used the same historical district boundaries. The regional grouping is now independently sourced as well: VEC's 2018 Election Service Plan, Appendix 2, printed page 34, lists all 88 districts in eight groups of 11.

Source: https://www.vec.vic.gov.au/-/media/d8a664a8c6554fccbd9329d100ee32a4.pdf?sc_lang=en

The historical membership file is separate from current region and SUB-REGIONS assignments. No current district vote shares were inferred by joining old/current names. Transferring the resulting component scales to modern regions would still be an assumption; there is no fitted subregion variance in this work.

The 65-district estimation subset requires ALP/LNP/GRN to contest both elections, no multiple Coalition candidates, and no individual independent at 10% or more in either election. It is a descriptive major-field subset, not an objective definition of every “ordinary” current seat.

## Component estimates

| Party | Within-region local SD | Shared regional SD | Combined SD |
|---|---:|---:|---:|
| ALP | 3.50 pp | 1.31 pp | 3.74 pp |
| LNP | 3.24 pp | 1.89 pp | 3.75 pp |
| GRN | 1.79 pp | 0.41 pp | 1.83 pp |

The existing live settings inspected on 28 October assigned every party local SD 2.5 pp and regional SD 0.75 pp, or 2.61 pp in quadrature before balancing. The historical component proxy is therefore larger for ALP/LNP and smaller for GRN. This is not an argument that every party's probability must become less certain: evidence can justify different directions for different components.

These are historical **lean-change** components after removing statewide primary movements, not direct estimates of today's latent-primary error. They include remaining candidate and contextual effects, and are not pure sampling error. They describe scales before nonnegative clipping and statewide balancing. The realised forecast variance will differ.

## Method

For each party, fit one-way random-intercept method-of-moments components to historical district lean changes, with an overall mean and region effects. For unequal group sizes:

- Within-region variance = within sum of squares / (N − G).
- Effective group size = (N − sum(group size²)/N) / (G − 1).
- Regional variance = max(0, (between-region mean square − within-region mean square) / effective group size).

Negative between-region variance estimates are set to zero and are not interpreted as evidence that regional uncertainty is impossible. There are only eight historical regions, with subset sizes ranging from four to eleven. Component estimates have substantial uncertainty.

No historical average lean change is added to today's central predictions. Positive or negative subset means are not silently converted into party-favouring adjustments.

## Correlated party errors

Within-region established-party correlation is shrunk toward independence. The identity weight is selected from 0–1 in 0.01 increments by a leave-one-district-out conditional Gaussian score. Each held district's regional mean and covariance are estimated without that district; prediction variance accounts for uncertainty in the training-region mean.

Selected identity weight: **0.23**. Resulting correlations:

| Pair | Shrunk correlation |
|---|---:|
| ALP / LNP | −0.361 |
| ALP / GRN | −0.174 |
| LNP / GRN | +0.191 |

This tunes covariance regularisation, not election forecast accuracy. Districts share a single electoral transition, so these 65 folds are not 65 independent elections. Do not claim held-out forecast calibration from these scores. The positive Coalition/Greens correlation is a geographic-error relationship, not a claim that individual voters transfer in that direction.

The present implementation uses a single party-correlation matrix for local and regional errors. The partial configuration borrows the local correlation for the regional component, explicitly an unestimated assumption given only eight regions. Separate regional covariance remains future work.

## Why this is not yet the complete configuration

1. **Post-outcome subset selection:** excluding an independent who reached 10% uses knowledge of the historical result. We cannot know today which future challenger will meet that threshold. Applying the subset's budget to every current district would leave out the exceptional-contest risk the user is concerned about. Current candidate/context inputs must be prospective.
2. **ON:** there are no ON observations in the historical panel. The partial configuration retains the inspected existing ON residual scales rather than inventing a fitted ON number. Existing ON-alpha/donor uncertainty is unchanged. This is a placeholder, not completion of the requested structural ON uncertainty.
3. **IND and OTH:** the large historical aggregate variation mixes candidate entry/exit, different named candidates and composition changes. It should not be converted into a uniform extra 8-point IND shock everywhere. The partial configuration retains old residual assumptions while field/context modelling is specified.
4. **Preferences:** the new source-transport mechanism exists but its new scales remain zero in this partial proposal. Existing source SDs remain provisional; no special-prior row is rewritten. Evidence precision and transferability must be budgeted separately before activation.
5. **Historical movement versus nowcast error:** four-year geographic movement informs template uncertainty, but is not automatically the correct present-day error around a template that already incorporates later evidence. Additional boundary-compatible transitions and contemporaneous information should inform how much of it to retain.

Candidate replacement alone is not a reliable exceptional-context rule. In the subset, LNP lean-change SD is about 2.88 pp for unchanged candidate sets and 4.15 pp for changed sets, but ALP shows the opposite ordering (4.38 versus 3.03). Do not infer an incumbent-retirement uncertainty coefficient from this small descriptive split.

## Proposal and next implementation boundary

`reports/historical_lean_budget_2026_10_29/partial_config_proposal.json` contains one explicit, validated candidate for the established-party core, with all inherited/unestimated components listed. It is marked NOT_ACTIVE. It is not a claim to have solved the complete six-party nowcast and is not exposed as another app trial.

Next complete the prospective candidate/context input and explicit ON/IND/OTH assumptions, then stage the complete unified settings through Sheets. Review that one coherent configuration against the preserved forecast. Do not return to a grid of arbitrary widths or adjust parameters to meet a target number of seats below 95%.

Main, live apps, Sheets, deterministic source data and special-prior rows remain unchanged. No new election-day time-drift uncertainty is introduced.

## Reproduction and checks

- `tools/fit_historical_lean_budget.py` produces component estimates, covariance scores, historical region/context rows and the partial proposal.
- `data/research/historical_primaries_2026_10_29/region_membership.json` records the official historical geography and source.
- Tests cover balanced-design moment identities, nonnegative region variance, valid covariance regularisation, held-out scoring and group-label invariance.
- All input hashes and explicit limitations are recorded with the proposal. Engineering tests do not establish empirical forecast coverage.
