# Candidate field comparison, 6 November 2026

Testing only. Development result, not a calibrated forecast. Roster is the ABC
list of 31 October, not final VEC nominations. Rerun after nominations close.

All runs use the inputs saved in `polling-vic-3b830b9e8c1e8fdc-5000`, seed
20261010 and paired random draws. Field-layer draws use stream 809.

| Folder | Meaning | Draws |
|---|---|---|
| `control` | Layer off. Draws equal the release. | 5,000 |
| `retained` | Version A: unsupported residual stays with minor candidates. | 5,000 |
| `released` | Version B: unsupported residual goes to ALP, LNP, GRN and ON. | 5,000 |
| `split` | Diagnostic: separate 5.46 IND and OTH targets kept. Not a candidate method. | 5,000 |
| `don_*` | Version A with alternative donor assumptions. | 2,000 |

## Decision

Version B (`released`, residual retention 0) is the working central case, chosen
by the project operator on 6 November. Version A stays as a comparison.

## ON_strength inputs

The release held Bundoora at 0.486108, a copy of Ivanhoe's row. `bund_*` folders
rerun with the older correct value, 0.907014. The live testing Sheet was then
found to hold a repaired column noted as approved on 5 November (Bundoora
0.930332). `data/raw/LEGACY_PRIMARY_INPUTS.csv` now uses all 88 live values, read
on 6 November; the other nine columns matched. `live_control` and `live_released`
are the current results and `live_released` is the working central case. Other
Sheet tabs were not re-read; those runs use the release's 31 October inputs.

`Tests/fixtures/LEGACY_PRIMARY_EXPECTED.csv` was recomputed from the model formula
because the source workbook is a different, older Sheet. That test now guards
against unintended change; it no longer proves parity with an independent workbook.

## Sheet refresh, 6 November

All 37 synced tabs of the testing Sheet were compared with these inputs through the
signed-in Sheet view, ignoring number formatting and checkboxes. No candidate record
or nowcast context is enabled. Three differed: `DISPLAY PARAMS` (presentation only,
not copied), `FORECAST PARAMS` (SIMULATIONS only, against the release snapshot) and `LOWER_CANDIDATE_EFFECTS` (a
disabled Yildiz record). `live_control` and `live_released` already reflect the Sheet,
so they were not rerun. `data/raw` now carries the verified forecast inputs, except
`FORECAST PARAMS.csv`, which a test keeps equal to the code's fallback defaults. The
runs take their settings from the release record, which matches the Sheet.

## Method limits

- `IND_pvi` construction could not be traced; no build script is in the repository.
  The whole IND surface is released per draw instead of a named debit.
- Seats with a listed but unreviewed independent keep the old IND surface.
- Candidate strengths in `data/development/candidate_field/REVIEWED_CANDIDATES.csv`
  are provisional judgements. One Nation donor affinity has no Victorian evidence.
- OTH is still counted as one group, so West and Victorian Socialists are not
  separately eliminated. Ava Adams is counted in OTH by the classification policy.
- The app has a sidebar switch, off by default, for the central count and forecast.
  It reads committed tables, not the Sheet. Elsewhere use the `candidate_field`
  forecast experiment or `tools/run_candidate_field_comparison.py`.

## To rerun with the final roster

Replace the roster JSON, run `tools/build_candidate_field_ballot.py`, review
`REVIEWED_CANDIDATES.csv`, then run the four scenarios.
