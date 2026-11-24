# October testing: native frozen v6

Authorised target only: `suandogg/vic-irv-model`, branch `codex/october-testing-2026-10-08`, entrypoint **snapshot_app.py**. Main, main-repairs, model-backup and preference-review branches are separate apps and are unchanged.

Run `streamlit run snapshot_app.py`. The native v6 defaults and initial polling targets match the website's 24 November interim model. Forecasts are on demand; the UI defaults to 200 draws, with up to 50,000 available. Matching a saved forecast also requires identical targets, seed, draw count and input generation. It does not load or modify website outputs.

For the former ddfaf34 behaviour: `streamlit run snapshot_app.py -- --legacy`. For scripts set `PRISM_MODEL_VERSION=legacy` **before importing SRC**. Original inputs and switches are preserved. No hot switching between cached generations.

Inventory, exact-match evidence, versioned test results and limitations: `reports/v6_engine_port_2026-11-25/REPORT.md` and `INVENTORY.md`. All future changes require owner review; do not tune towards saved results. Model-bearing Sheet tabs are frozen through the sync guard; changing them needs a reviewed Git release. No Sheet write permissions or new secrets.

Run `python3 tools/test_model_versions.py`: the original 219 behavioural tests explicitly exercise legacy semantics; new v6 tests exercise the new defaults. This preserves historical assertions rather than weakening them to accommodate a different model. Use `PYTHONHASHSEED=0` for exact reproduction.
