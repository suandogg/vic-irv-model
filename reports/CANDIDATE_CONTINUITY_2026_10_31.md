# Candidate continuity integration — 31 October 2026

Target: `codex/october-testing-2026-10-08`, `snapshot_app.py`, testing workbook
`1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968`. Based on `ab648d4`.
Main and its workbook are outside this change. Publication requires a GitHub
push; local verification is not live deployment verification.

## Connected inputs

- `LOWER_CANDIDATE_EFFECTS`: original 30-column sheet. Four provisional examples
  exported from the live testing sheet; all disabled. No candidate estimates fitted.
- `LOWER_CANDIDATE_FIELD`: full current roster for each affected district.
  Columns: district, candidate_id, candidate_name, model_group, baseline_weight,
  receiving_weight, preference_profile_id, enabled.
- `LOWER_CANDIDATE_PREFS`: district, profile_id, recipient_id, weight, enabled.
  Empty header-only field/profile templates are intentional. Sync writes cleared
  header-only tables rather than retaining stale saved records.
- `LOWER_CANDIDATE_GUIDE` remains documentation, not a calculation input.

`baseline_weight` divides the group's remaining baseline among actual candidates;
it is a nonnegative relative weight, not a vote share. The realised candidate
addition is reserved first and then added to that named candidate. For a genuinely
new candidate whose support is entirely the incremental effect, use weight zero.
Every positive baseline group needs positive allocation weight. Retired IDs must
be absent. `receiving_weight` divides the existing engine's incoming group flows
between continuing candidates in that group; it must be supplied explicitly.

Each current IND/OTH candidate needs an explicit preference profile. Its rows
give nonnegative relative weights over other candidate IDs in the same district;
the vector is restricted and normalised to each continuing field. These are
provisional conditional preference priors, not complete ballots or observed
rankings. Reject missing/empty profiles rather than inventing preferences.
Separate same-group candidates must have separate IDs and can have distinct
profiles. Major and ON candidate profiles cannot override the group engine.
Only one ALP/LNP/GRN/ON nominee per district is currently supported. Multiple
Liberal/National nominees require further reviewed field modelling.

## Primary pipeline

The existing October structural primary, party adjustments and LNP pre-collapse
stages run first. Candidate continuity then removes only the supplied embedded
component times (1-retention) from `previous_model_group`. The raw historical
primary is reference data, never directly subtracted. Release weights allocate
removed support to other groups. Returning, new, retired and switched statuses
are validated; Birchall's source group is IND, Bingham's is OTH in the current
2022 classification. Switching never automatically transfers the whole old vote.

Apply releases simultaneously, then fund additions simultaneously from donor
weights. Exhausted donors drop out and remaining capacity is redistributed.
Diagnostics report requested, sampled, realised and unfunded additions. Reject
overlapping/excess embedded components or duplicated party-level manual/candidate
effects. Districts with active candidate inputs are held fixed while the other
districts restore the unweighted statewide targets. Structural zeroes persist;
incompatible targets fail instead of undoing candidate effects. Polling target
definitions, including West Party within OTH, require review before calibration.

The forecast applies this stage after its ordinary local/geographic noise, once
per draw. A separate RNG stream `[SEED, draw, 808]` avoids changing the legacy
random stream when no candidate rows are active. Nonzero effect SD uses a normal
draw clipped to [0,100] pp; its realised mean/SD need not equal the input values.
No retention/component uncertainty or candidate-preference uncertainty is fitted.
Review existing local SDs before enabling extra candidate SD so risks are not
counted twice. This is a testing interface, not a calibrated candidate forecast.

## Count and display

Only reviewed affected districts use named candidates. All other districts keep
the previous count exactly. The group preference engine supplies major/ON-origin
flows; explicit profiles supply IND/OTH-origin flows. Keep primary-origin parcels
and the holder-level ON special-prior exception. Group flows are split using the
explicit receiving weights. All transfers conserve votes. Ordinary and forced
ALP/LNP and ALP/ON counts use the same implementation. A missing protected major
has a zero-vote hypothetical nominee only inside the forced count, matching the
old hypothetical 2CP convention; it does not enter the actual field.

Headline results retain group labels; the seat detail shows named primaries and
the actual named-candidate elimination trace for affected seats. The legacy
aggregate evidence trace is not shown for those seats. Forecast cache signatures
include all three input tables and the two new engine modules.

Candidate IDs in the legacy elimination-order display refer to real individuals;
the old six-category placement layout is not a complete candidate ranking when
there are more than six candidates. Use the seat detail for the full trace.

## Verification

- 15 new tests: disabled exact no-op, correct old OTH removal, vote conservation,
  statewide targets, permutation invariance, donor exhaustion, missing/overlapping
  input rejection, seeded uncertainty, incompatible targets, clearing input
  tables, separate IND eliminations, missing preference rejection, ON lock,
  calculator/forecast named-count parity, and hypothetical forced nominee.
- Broader suite: 147 tests executed on first run, with one pre-existing setup error:
  `test_legacy_primary_model` expects lowercase `tests/fixtures` on a Linux
  filesystem but the repository has `Tests/fixtures`. No assertion weakened.
- Streamlit AppTest loaded `snapshot_app.py` with no exceptions and showed
  `4 candidate records loaded; 0 enabled.` No credentials were provided locally;
  this validates saved-input startup, not the hosted service-account connection.

Before enabling: verify 2026 names/field, estimate embedded historical components,
effects and SDs, review donor/release assumptions, complete current roster and
minor-candidate profiles, then compare seat-level traces and forecast draws.

## Application verification — 31 October 2026

Applied cleanly to GitHub testing head `ab648d4872493c64a05392d88aadf1d287ecde6e`
in an isolated checkout, preserving existing local work and leaving Main unchanged.

- `python3 -m unittest discover -s Tests -v`: 162 tests, 158 passed,
  3 skipped, 1 failed. All 15 candidate continuity tests passed.
- The failure, `test_matches_legacy_workbook_for_all_seats`, reproduces on the
  unchanged base with the identical ALP maximum difference
  `0.030807616248605896`. It is an existing workbook fixture mismatch,
  not the Linux path setup error described in the earlier verification.
- Streamlit AppTest of `snapshot_app.py`: zero exceptions; caption confirmed
  `4 candidate records loaded; 0 enabled.` This checks local saved-input startup;
  hosted deployment and service-account access were not verified.
- `git diff --check` passed.
