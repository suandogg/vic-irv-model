# Preference review: recommended configuration and decision point

## Scope and separation

Original reference app and original Sheet are unchanged. Experimental branch:
codex/preference-review-2026-10-08. Testing app:
https://vic-irv-model-testing.streamlit.app/. It syncs the separate testing Sheet
1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968. Frozen backup remains separate.
All current live forecasts still count six categories; candidate/subtype tools
are offline diagnostics. Legislative Council is outside these experiments.

## Recommended working option

Use **VEC exact fields with corrected coverage** for further six-category
testing. It attaches own-seat reconstructed category-origin evidence only where
the historical non-ON continuing field matches. Recognise that evidence as
complete when ON is absent from the continuing field; stored synthetic ON
allocation is unchanged. Unmatched fields retain reference logic. Special
priors remain locked. Retention remains1; do not alter geography, caps, siphon,
primary geography, candidate inputs or donor settings as part of this option.

This is an opt-in recommendation, not a production switch or an independently
validated high-ON forecast. A new session still defaults to Current reference.
Do not automatically combine with the separate OTH-row rebuild, shrinkage or
source-selection sensitivities; their interactions have not been established.

## What the tests support

- Held-out exact-field pooled VEC category-origin predictions improve versus
  legacy fallback. Corrected coverage error11.53 points versus13.48 before
  correction on the same234 conditional targets. Those targets are reconstructed
  origins, not observed ballot rankings, and are not election outcome errors.
- Native/continuing ON and locked-special flow comparisons stayed identical
  in1879 audited calls. Aggregate ON-held parcel transfers can change through
  other retained origins; unchanged rules do not mean unchanged aggregate flows.
- Candidate subtype predictions outperform broad category pooling on matching
  fields. Both broad-category and tested family shrinkage worsened average
  held-out parcel errors; neither should be adopted on this evidence.
- Exact candidate transfer precedence reproduces recorded88-seat counts but
  uses own-election transfers: implementation reconciliation, not forecasting.

## What the tests do not establish

- Accuracy for a large hypothetical ON vote in2026.
- An optimum origin-retention level (sensitivity is not calibration).
- A fully evidenced candidate-level count on unseen fields. Strict minimum-three
  subtype holdout completes35/88; incomplete coverage must not be omitted.
- Correct elimination order for combined heterogeneous OTH groups. Laverton
  and Kororoit expose this limitation of the six-category representation.

## Recommended stop/continue decisions

Stop searching for a weak generic prior merely to complete candidate counts.
Keep candidate diagnostics for reliability warnings and identifying evidence
gaps. Further substantive candidate forecast work needs additional election
evidence or an explicitly approved extrapolation model, not silent nearest-field
matching. More historical evidence still cannot alone identify hypothetical ON
behaviour; that remains a separate scenario assumption.

The immediate decision is whether to make corrected exact-field coverage the
testing-app default, while preserving selectable reference and leaving the
original reference app intact. This has NOT been done. If approved, label
category aggregation and high-ON uncertainty clearly, rerun fixed scenarios,
verify live startup/sync, and record the release. Production adoption remains
separate from changing the experimental app default.
