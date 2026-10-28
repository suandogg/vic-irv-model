# Forecast performance: first optimisation pass

October testing only; no methodology or uncertainty-default changes.

Changes:
- Load LNP pre-collapse inputs once per simulation run, rather than once per draw.
  This is not a persistent cache: subsequent runs still read refreshed inputs.
- Replace scalar pandas reads/writes inside the ON donor allocation with array
  access. Allocation loops, caps, party iteration and arithmetic are unchanged.

Same-process paired benchmark, 30 draws per configuration, committed inputs,
central primaries ALP 24.6 / LNP 29.1 / GRN 13.3 / ON 22 / IND 5.5 / OTH 5.5:

| Configuration | Old donor function | Array donor function | Speed-up |
| --- | ---: | ---: | ---: |
| Current | 3.487 s | 3.036 s | 1.15x |
| Positive bounded concentration, width 0.3 | 3.543 s | 3.137 s | 1.13x |

Both sides of this paired benchmark already preload the static input, so the
comparison isolates the donor array change. All returned DataFrames and arrays
were exactly equal, including seat results, margins and primary outputs.
Separate-process comparisons can differ at floating-point round-off because
the existing donor loop uses a set whose iteration order varies by process;
the optimisation does not change that existing behaviour.

25 targeted forecast/pattern/subregion tests passed, including a regression test
for once-per-run loading and preloaded versus ordinary pipeline equivalence.
These are local timings, not a promise of hosted Streamlit performance. Changes
have not yet been pushed or deployed. Further work should target primary
calibration/seat-adjustment overhead before considering preference shortcuts.

## Second pass

Moved both iterative calibration loops from repeated pandas construction to
NumPy arrays, retaining the same iteration limits, convergence tolerance,
normalisation and scaling order. Calculator diagnostic output remains the
default; forecasts now skip assembling the unused final seat-adjustment report.
The adjustments themselves are still applied in full.

Paired 30-draw comparison against the first-pass calibration implementation:

| Configuration | First pass | Array calibration | Throughput increase |
| --- | ---: | ---: | ---: |
| Current | 2.954 s | 2.400 s | 23% |
| Positive bounded, width 0.3 | 3.025 s | 2.411 s | 25% |

All returned DataFrames/arrays matched exactly in these paired runs. Added
reference tests pinning the original calibration implementation to commit
25587bd, covering ON targets 0/19/22/25/50 for the corrected primary builder,
three alpha values, GRN persistence, component calibration and existing failure
behaviour. The component helper's existing zero-target division error is
deliberately not fixed as part of this performance-only change.

27 targeted tests passed, including diagnostic-on/off primary equivalence.
Still local and not deployed; no change to priors, uncertainty or counting.

## Third pass: compile static pre-collapse rules

Forecasts now validate and compile enabled pre-collapse rules once per run,
then apply the same per-party arithmetic to arrays per draw. Rules are not
cached across runs. The plan checks district identity/order before applying,
and each affected seat retains the vote-conservation check. Ordinary calculator
calls retain the existing code path. The source fingerprint now also includes
the pre-collapse module.

Paired 30-draw checks: Current 2.046 to 1.774 seconds; positive bounded width
0.3, 2.167 to 1.785 seconds. All returned DataFrames matched exactly. This is
13–18% less elapsed time for this pass, not a hosted-runtime guarantee.
28 targeted tests passed, including empty rules, malformed shares, plan district
order and exact ordinary/compiled equivalence. Not pushed or deployed.

Further preference caching is deferred: source selection and final flows can
depend on each draw. No cross-draw preference cache or diagnostic suppression
has been introduced in the preference engine.

## Fourth pass: reuse identical ALP–LNP counts

If the actual final pair is ALP/LNP, neither party was excluded, so the forced
ALP/LNP count has the same exclusions and transfers. Forecasts reuse the actual
final parcel totals for this case only; other matchups still run forced 2PP.

Paired 30-draw checks (all returned DataFrames exactly equal): Current 1.804 to
1.774 seconds, bounded width 0.3 1.840 to 1.756 seconds, regional preference
patterns 1.725 to 1.691 seconds. These small improvements are timing-sensitive.
The existing comparison against the full calculator count also passes.
No preference-source or cross-draw flow caching changes were made. Further
optimisation should be weighed against increasing complexity and regression
risk; the larger safe primary-pipeline gains are already implemented locally.
