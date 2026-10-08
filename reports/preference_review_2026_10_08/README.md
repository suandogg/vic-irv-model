# Preference review: initial trials, 8 October 2026

The reference is the full Desktop working model, including uncommitted source
and input changes, copied before the trial. Existing testing/main branches
were not modified. Input hashes and fixed primaries are saved beside this report.

Four scenarios compare reference, no generic ON siphon, no additive preference
geography, no floors/caps, no complete-matrix priority for ON-related rounds,
and their combined simplified variant. Primaries are identical across methods
within each scenario; special-prior values are unchanged.

The hierarchy trial is deliberately broad: it removes complete-row priority
whenever ON is alive or eliminated. It does not yet distinguish observed ON
entries from synthetic ones. It is a sensitivity bound, not a finished
provenance-aware evidence hierarchy. Existing partial historical anchoring
continues to operate.

Initial findings: geography changes 5–6 winners in the three high-ON scenarios;
the siphon changes 0–1. Constraints change no winners. The hierarchy change
changes one winner in each high-ON scenario without changing ON's seat total.
The combined variant reduces ON wins from 3 to 1, 8 to 7 and 19 to 17.
Those shifts do not establish better accuracy. Historical held-out margin
validation, rule-use diagnostics and actual provenance must precede selection
of a production configuration. Full per-seat outcomes are in seat_results.csv.

The actual primary scenarios are preserved in primaries_*.csv. ON18 uses
29/32/12/18/4.5/4.5; ON20 uses 25/30/14/20/5.5/5.5; ON24 uses
25/28/12/24/5.5/5.5, in ALP/LNP/GRN/ON/IND/OTH order.

Streamlit deployment: repository suandogg/vic-irv-model. Frozen backup branch
codex/model-backup-2026-10-08, entrypoint snapshot_app.py. Trial branch
codex/preference-review-2026-10-08, entrypoint snapshot_app.py. The snapshot
entrypoint disables live Sheet synchronization to preserve comparison inputs.

## Historical validation

The new historical test uses actual candidate-level 2022 primary totals, not
projected primaries. It excludes pooled posterior and federal evidence because
their current metadata cannot reliably remove a held-out seat. Existing
seat-specific LNP pre-collapse corrections remain. This is therefore a
conditional matrix holdout, not fully independent validation of the engine.
Margin errors below apply to the 85 seats with matching final pairs.

| Test | Reference mean absolute error | No preference geography |
| --- | ---: | ---: |
| Own-seat matrix reconstruction | 1.827 percentage points | 1.601 percentage points |
| Held-out seat, other-seat class matrices | 1.820 percentage points | 1.719 percentage points |

Removing geography modestly improves this historical metric. It does not
validate high-ON contests, which were largely absent in 2022. See
historical_validation_summary.csv and historical_validation_seats.csv.

## Rule-use audit

In the reference high-ON scenarios, all available holder-level special priors
were selected: 22 of 22 for ON18, 33 of 33 for ON20 and 47 of 47 for ON24.
This narrows the concern about those priors being displaced in these paths;
it is not proof for every possible scenario or parcel-origin subcall.
ON_SPECIAL_SCENARIO_PRIORS values are unchanged in all trial variants.
round_rule_audit.csv records the selected sources and contest gaps.
parcel_stage_audit.csv records local changes at each transformation stage;
summing them is not a causal statewide effect because paths and later blends
can differ.

## Seat-count reliability sensitivity

Three additional variants replace the existing posterior reliability with
n/(n+k), where n is the recorded evidence-seat count and k is 5, 10 or 20.
They retain federal evidence and do not invent missing variance or membership.
These are sensitivity tests, not calibrated production recommendations.

All three change one ON18 winner from ALP to LNP, leaving ON at three seats.
None changes winners in ON20 or ON24. The projected 2022-input scenario also
changes, but must not be confused with the actual-primary historical test.

## Interactive testing

The testing app's Preference trial selector exposes the reference and eight
alternatives. Reference remains the default. Only Assembly preferences are
varied; primaries, special-prior values and Council logic are preserved.
Inputs remain frozen for reproducibility.

Recommended next step: separate ON-recipient geography from non-ON geography,
then test those independently before selecting a production setting. Improve
scenario provenance and per-seat evidence membership before calibrating
posterior shrinkage. No production configuration is selected by this report.
