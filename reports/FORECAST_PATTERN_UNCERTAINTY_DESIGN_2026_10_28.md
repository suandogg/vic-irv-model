# Forecast pattern uncertainty — proposed design

## Purpose and status

Broaden what the Victorian Assembly forecast considers possible, for **all six
party categories**, without changing the central calculator or manufacturing a
desired number of competitive seats. A conditional probability under one spatial
and preference architecture should not be mistaken for robustness across plausible
architectures.

This document is an implementation design, not a calibrated forecast. Deterministic
research primitives have been built in `SRC/forecast_patterns.py` and tested, but
are **not connected to the app's simulation loop**. No Sheet, live forecast,
central values or defaults have been changed. Existing opt-in trials remain as
previously implemented. Numerical widths/mixture probabilities below are not
silently invented or adopted.

## 1. Separate four questions

1. What statewide support is plausible? Existing statewide primary uncertainty,
   eventually informed by polling error and the election horizon.
2. At that statewide support, where might votes be concentrated? New spatial
   pattern uncertainty plus regional/local residual variation.
3. Given that field, how might preferences behave? A coherent hierarchy of shared,
   regional and local flow uncertainty, plus targeted alternative flow regimes.
4. Who is actually contesting and how strong are local candidates? Existing
   known inputs; later explicit candidate/contest scenarios where evidence supports
   them. Do not infer candidate absence from a rounded zero vote estimate.

More variance is not automatically better. The objective is defensible predictive
coverage, assessed separately for statewide outcomes and individual seats.

## 2. Draw a coherent election, not 88 unrelated surprises

For each simulated election:

1. Draw statewide primaries using the existing mechanism initially. Label its
   provisional covariance assumptions; do not add another independent whole-state
   polling error on top without specifying the variance budget.
2. Draw election-wide coefficients describing persistence/concentration of each
   party's existing support, and any justified alternative spatial pattern.
3. Draw regional deviations and local residuals, shared/correlated appropriately.
4. Construct seat primaries through the existing production builder, then apply
   spatial pattern tilts and balance to the actual production table's party totals
   and seat totals. Respect intentional existing precollapse adjustments.
5. Draw preference latent factors once at statewide, regional and seat levels;
   keep them stable across counts/continuing fields for the same party/recipient.
6. Apply approved field-specific flow scenarios where relevant. Run the existing
   parcel-aware count. Do not replace central evidence selection or pass-through.
7. Record both the sampled pattern and result. All seats must be counted.

## 3. Primary vote dispersion for each party

### A. Strength persistence: continuous, all-party coefficients

Use a standardised log-strength contrast for each party across eligible seats.
Positive coefficients concentrate support in existing stronger seats; negative
ones flatten it. Coefficients are drawn once per election, not per seat.

The existing ON alpha is already one concentration mechanism. In the integrated
version, **replace/reparameterise its uncertainty**, rather than independently
adding another ON concentration factor to it. Keep the central ON construction
unchanged. Similarly avoid double-counting any GRN PVI-persistence uncertainty.

For other parties, compare using their historical relative support versus the
current projected support as the contrast source. The latter is available now,
but partly embeds the current model's assumptions; it is a prototype, not
independent evidence. Record the chosen source.

### B. Regional pattern changes, not just regional labels

Give each party a vector of regional deviations, drawn coherently each election.
For example, ON can overperform its current pattern across western Melbourne
while underperforming elsewhere, with unchanged statewide ON support.

Initially use the eight existing region assignments as a transparent grouping.
Audit their boundaries before treating them as ideal: Council regions are
administrative groupings, not automatically optimal voting-pattern regions.
Alternative groupings can be compared later, not layered on simultaneously by
default. Seat class and region are correlated; their effects must not both be
treated as independent full-sized errors.

Regional shocks currently exist. The new version should **replace/refactor**
that mechanism into party-specific, evidence-informed regional covariance, not
silently stack a second copy of generic regional noise.

### C. Genuinely different geographic signals

Concentration changes keep the underlying strength signal largely the same.
Where defensible data exist, add alternative spatial contrasts: e.g. previous
state upper-house ON performance against the federal-SA1-derived ON index.
Check boundaries, vote types, candidate coverage and cross-election transferability.

For a source with enough coverage, a centred log-ratio contrast between two
normalised strength maps can represent disagreement. If the new source is
missing, do not fill the hole as zero support. Flag missingness and shrink or
omit the contrast transparently.

Initially show alternative-map runs separately. Only assign a distribution over
their relative influence once there is a substantive/evidence basis. Equal
weights are still assumptions; do not present them as neutral or calibrated.

### D. Local residuals and party relationships

Party-specific local residuals represent variation not explained by the factors
above. Estimate them from historical comparable-seat errors where possible,
with shrinkage and a defensible floor rather than falsely precise seat-by-seat
SDs from a tiny history. ON transport uncertainty needs separate justification.

Avoid treating all party changes as unrelated. Prefer estimated/shrunk covariance
in log-ratio space. Composition already forces trade-offs, but compositional
normalisation alone is not an estimate of political substitution relationships.
For initial experiments, compare simple declared covariance assumptions without
pretending they are empirically fitted.

### Spatial transform and constraints

For base share b(i,p), apply a log tilt h(i,p):

`provisional(i,p) = b(i,p) * exp(h(i,p))`

where h contains strength-persistence, regional and justified alternative-map
contrasts, plus the chosen residual model. Use iterative balancing to preserve
each party's total and every seat total. Zeros remain zero in the prototype;
candidate presence must be audited before making that a definitive eligibility rule.

All diagnostic spreads must be measured **after** balancing. A coefficient's
input SD is not automatically a final primary-vote PP SD. Extreme/infeasible
draws must fail transparently; do not silently discard them until a run looks good.

## 4. Preference patterns for every origin and continuing field

### A. A hierarchical variance budget

Replace the current ad-hoc layering with a declared source-dependent total
log-weight SD, partitioned across statewide, regional and local components:

`error = total_SD * (sqrt(f_state)*Z_state + sqrt(f_region)*Z_region + sqrt(f_local)*Z_local)`

with non-negative fractions summing to one. Retain recipient/origin dependence
within components as specified. This first changes correlation without increasing
the total variance. Additional uncertainty for cross-election transport is a
separately documented component, not an accidental duplicate of sampling error.

This applies to ALP, LNP, GRN, ON, IND and OTH as origins and to all continuing
recipients. The existing seat-class ON-recipient shock must be absorbed into or
explicitly distinguished from this budget—not retained unnoticed on top.

### B. Evidence strength is not just the source label

Use actual across-seat flow dispersion and count of independent observed seats
where available, not ballot count as though every vote were an independent
sample of next election's behaviour. Distinguish:

- Uncertainty about the pooled average flow.
- Genuine differences between seats/candidates.
- Cross-election transfer/transport error.
- Uncertainty in a synthetic or subjective prior.

Exact local evidence may reduce uncertainty but should not imply that its next
election flow is known. Sparse scenarios should shrink to broader estimates
and retain wider predictive uncertainty. Metadata gaps must be reported.

### C. Field-specific structural alternatives

A generic origin/recipient tilt cannot represent every how-to-vote or final-field
change. Add explicit scenario rows keyed by origin, exact continuing field and,
where justified, region or seat class. The obvious first audit is Coalition
preferences in an ALP–GRN final pair; also review consequential ON-related
special fields and heterogeneous IND/OTH flows.

Where multiple source elections give materially different observations, estimate
the disagreement rather than taking one source as certain. Source-election
comparability matters as well as sample size. Keep alternative regimes separately
labelled until weights are justified. Do not assume an observed how-to-vote
recommendation implies a particular voter-compliance rate.

These are simulation-only changes around the selected engine. In particular,
**ON_SPECIAL_SCENARIO_PRIORS source rows remain unchanged**. Their forecast
uncertainty can be explicitly specified, but neither their central values nor
the hierarchy selecting them should be rewritten under this project.

### D. Stable flows within a draw

Draw regional/seat preference factors once and reuse them across continuing
fields. Apply field-specific factors only to their named fields, then normalise
positive weights across actual continuing recipients. Preserve impossible
destinations; distinguish a genuine structural zero from missing evidence.

This remains an aggregate flow model, not proof of a single joint ballot-ranking
distribution consistent with every possible field. Existing parcel-origin logic
and pass-through remain in force; audit path consistency explicitly before any
claim of a full ranking model.

## 5. Other structural uncertainties worth including

| Component | Proposed treatment | Guardrail |
|---|---|---|
| ON donor/source mix | Coherent alternative donor matrices, if evidence supports them | Preserve totals and avoid duplicating existing donor-strength SD |
| IND/OTH composition | Candidate/subtype composition scenarios, separate from total primary variation | Do not assume every IND or OTH voter is interchangeable |
| Candidate strength/retirements | Shared default-effect uncertainty plus justified local residuals | Known flags remain fixed; avoid counting local candidate error twice |
| Candidate field | Explicit contesting/non-contesting scenarios only where genuinely unresolved | No unsupported invented candidates; distinguish data zero from absence |
| Election-day movement/polling miss | A clearly budgeted statewide predictive component, possibly time-dependent | Do not duplicate existing statewide primary SDs |
| Preference architecture | Separate stress tests first | No arbitrary automatic switch to previously rejected nearest-field methods |

No blanket probability cap, forced minimum upset chance or renormalisation of
seat-win probabilities will be used to make the forecast look less certain.

## 6. Proposed Sheet controls

Retain ordinary PARAMS as central assumptions. Forecast settings change simulated
variation only. The following is a **proposed schema**, not tabs already created:

1. **FORECAST PARAMS:** run/seed/reporting controls and existing uncertainty scales.
   New pattern mode off/current by default during testing. Version the schema;
   preserve compatibility rather than making a new required key break live sync.
2. **FORECAST PATTERN PARAMS:** Section, Component, Party/Origin, Parameter, Value,
   Units, Evidence status, Explanation. Covers concentration widths, regional/local
   variance fractions, source/transport scales and supported covariance parameters.
3. **FORECAST REGION MAP:** Electorate, Region, Seat class, Mapping version, Notes.
   One validated district assignment; no duplicate/missing seats or silent spelling
   fallbacks. Seat class is metadata, not an independent error layer by default.
4. **FORECAST FLOW PATTERNS:** Pattern ID, Origin, AliveSet, Geographic scope,
   Recipient, Central/log-tilt value, Uncertainty, Evidence reference, Status.
   Scenario groups/alternative weights must be validated coherently, not one
   independent random probability per recipient.
5. **FORECAST PATTERN EVIDENCE** (audit/support tab): component, source election,
   comparable seats, observed dispersion, transport assumption, fitting method,
   holdout result and limitations. It records provenance; it is not a second
   competing settings table.

Avoid one knob per seat/flow unless evidence or a deliberate manual override
justifies it. More controls do not imply more knowledge. Existing seat-level
overrides remain in their established tab.

## 7. Testing and reporting plan

Build in October testing and keep Main untouched. Test:

1. Pattern strengths zero/off exactly reproduce current draws and calculator
   outputs. Test source immutability, deterministic seeding, cache isolation,
   all-seat allocation, totals, bounds and eligibility constraints.
2. Isolated primary concentration, regional covariance, alternate map and
   preference components; then deliberate combinations. Keep shared draws paired
   where possible and test multiple seeds.
3. An interaction grid: current, primary patterns only, preference patterns only,
   both. Repeat over central/lower/higher ON scenarios using the user's declared
   inputs, without changing one component's central values to obtain preferred
   seat outcomes.
4. Report five demonstration seats, all-seat probability changes, pattern-sensitive
   seats, statewide ranges, faction/party covariance and how much variance each
   layer contributes. Export sampled coefficients/pattern IDs so an unusual
   result can be reconstructed.
5. Historical holdouts where valid: geographic blocks/candidate changes and
   election-to-election residuals, not only same-election reconstruction. Compare
   probability scores and interval coverage. Historical tests cannot establish
   today's high-ON accuracy; retain explicit transport limitations.

Report two separate objects until weights are defensible:

- Conditional probabilities within each tested pattern.
- Sensitivity across patterns (an envelope, **not** a calibrated probability band).

After calibration/assumption review, integrate justified pattern distributions
within draws. Explain that nonlinear transformations can move average/median
results even if latent coefficients are centred at zero; do not promise a fixed
forecast median. The central deterministic calculator itself remains unchanged.

## 8. Implementation delivered at this stage

`SRC/forecast_patterns.py` provides deterministic building blocks for:

- Balanced all-party spatial log tilts preserving supplied production totals.
- Standardised existing-strength contrasts for every party.
- Equal-seat-centred regional contrasts.
- Recipient tilts on a specified preference row, preserving zeros and source data.

Five new tests pass alongside the ten existing forecast tests. These primitives
do not draw coefficients, assign model weights, read new Sheets or run inside
the live forecast. Evidence fitting, all-party variance budgets, the new Sheet
schemas and combined trials are the next implementation stage. Current numerical
uncertainty defaults have not been presented as calibrated or replaced.
