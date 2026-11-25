# Native v6 engine port — 25 November 2026

The approved website profile is now the default lower-house engine on work branch `codex/v6-engine-defaults-2026-11-25`, starting exactly from remote testing head `ddfaf342d76649f9e990d958550566a504a21443`. The authorised deployment target is `codex/october-testing-2026-10-08` / **snapshot_app.py**. Other app branches are unchanged. Website source, the running forecast and all saved outputs were read-only.

## Inventory and implementation

[INVENTORY.md](INVENTORY.md) maps every profile operation to native SRC modules/input CSVs. Preference execution is now native: base evidence/card layer → metro LNP targets → forecast perturbation (generic SD for targets) → regional four-donor reductions → evidence offsets. No runtime function monkey-patching or website import is used by the application. Candidate field, Labor taper, proportional Other and both card layers are mandatory v6 defaults. Structured-nowcast/concentration/subregion defaults match the website. Lower-house files are protected from Sheet sync; no Sheet writes occurred.

`--legacy` is startup-only and restores original ddfaf34 inputs, settings and former opt-in controls. This is needed for faithful historical reproduction; it is not an opt-in v6 switch. Original files are retained in `data/legacy_20261114/`. Native input defaults and `PARAMS.csv` agree on alpha 0.8 / special priors. NumPy 2.4.4 and pandas 3.0.2 are pinned to the website environment. Interactive previews remain 200 draws; the v6 validator permits up to 50,000 only when explicitly requested. Polling target defaults are the reviewed 23 November snapshot, not a live refresh.

## Exact match

Seed **20261010**, **1,000 draws**, all 88 seats, `PYTHONHASHSEED=0`, one BLAS/OpenMP thread. The independent reference restores the website run's source/input archive and its original profile adapter; the native run loads this engine's own defaults. `exact_match.json` binds results to current source/input SHA-256s.

**Byte-identical:** central per-seat primaries and counts, all win-probability/seat/party/government exports, all 88,000 final-pair records. **Array-identical:** each draw's per-seat primaries, winners, margins and forced Labor–Coalition shares. **Differing seats: none.** No parameters were adjusted for matching.

The published 50,000-draw run's first 1,000 aggregate seat draws also match exactly. Its original Python hash seed was not recorded: 38 published central CSV rows differ in the last floating-point bits from the controlled replay, at most **2.842170943040401e-14 percentage points**; all final pairs and displayed values match. Every affected seat/cause is in `published_central_roundoff.csv`; it is not hidden behind a tolerance or corrected by changing a model value. The paired reference/native CSVs themselves are byte-identical at full written precision. The complete website output manifest (12 files), profile and receipt remain unchanged.

## Streamlit and tests

`streamlit run snapshot_app.py --server.address 127.0.0.1 --server.port 8516` starts successfully; health returns 200. AppTest executes snapshot_app.py, not app.py directly. No exceptions/errors; the six starting targets, five mandatory layers, structured nowcast, positive-bounded concentration and blended subregions are verified. Seat displays match exact central results:

| Seat | Winner | Runner-up | Winner 2CP % |
|---|---|---|---:|
| Hawthorn | LNP | GRN | 63.55 |
| Ripon | ON | ALP | 58.91 |
| Narracan | LNP | ON | 63.99 |
| Ringwood | LNP | ALP | 54.12 |
| South Barwon | LNP | ALP | 57.22 |

`streamlit run snapshot_app.py -- --legacy` also passes an entrypoint check: original 2022 targets and all original opt-in switches off. `test-matrix-final.log`: **219 historical tests in legacy mode, OK with three baseline skips; nine native v6 tests, OK**. The unmodified ddfaf34 baseline has the same 219 tests/three skips. Existing historical assertions are preserved; the historical-workbook fixture explicitly reads its original input generation rather than the corrected Narracan input. Running those old-behaviour assertions against v6 directly is inappropriate; use `python3 tools/test_model_versions.py`. Native tests include sync protection, default experiment equivalence, prior/card/uncertainty corrections, legacy isolation, and current source/input binding to the 1,000-draw receipt. No failures remain in the versioned matrix.

## Reproduce / operate

1. `python3 tools/prepare_v6_reference.py --run /absolute/path/to/election-website/runs/polling-vic-interim-20261124-v6-50000` (new temporary destination required; source archive SHA verified; no website writes).
2. `PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B tools/verify_v6_port.py reference` then the same command with `native`.
3. `python3 tools/compare_v6_port.py`; `python3 tools/test_model_versions.py`; `PYTHONHASHSEED=0 python3 tools/check_snapshot_v6.py`.
4. Merge only this work branch into the authorised testing branch, push that branch, verify hosted v6 label. Retain ddfaf34 as the rollback reference; a future rollback/push is a separate owner decision. No main/main-repairs/model-backup/preference-review changes.

The app calculates scenarios on demand. It does not serve the website's saved 50,000-draw probabilities; identical Monte Carlo outputs require the same draw count, targets, seed, input generation and environment. The live website calculator still uses its older private image; rebuilding it is explicitly outside this task.

## Deployment completed

Code commit `2aca20f0177fb2d59caf1b1480f7f737fa7edf3c` was fast-forward merged into `codex/october-testing-2026-10-08` and pushed. Remote comparison confirms that this is the only changed branch. Existing untracked work in the target checkout remains intact. Streamlit Manage app independently confirms `suandogg/vic-irv-model` / `codex/october-testing-2026-10-08` / `snapshot_app.py`. Rebooted that specific app to replace its cached process. The hosted v6 label, six polling targets, all five mandatory layers and central result Coalition48/Labor20/ON14/Greens6 are verified. Live sync skips the protected lower-house files and synced16 other tabs without errors. Previous-process Council quota warnings were not reproduced after restart. See `hosted-deployment.json`, `hosted-v6.jpg`, and remote-ref evidence.
