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
