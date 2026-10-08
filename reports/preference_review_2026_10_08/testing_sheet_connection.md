# Testing spreadsheet connection

The laboratory app at https://vic-irv-model-testing.streamlit.app/ now uses a native copy of the original spreadsheet:

https://docs.google.com/spreadsheets/d/1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968/edit

Copy title: vic-irv-model — Testing laboratory — 8 October 2026.

The existing model sync service account has Viewer access to the copy. The laboratory entrypoint explicitly sets VIC_IRV_SHEET_ID to the copy before loading app.py; this takes precedence over inherited Streamlit secrets. Local sync defaults also point to the copy. The reference and backup branches were not modified.

This connection change does not rebuild any matrices or alter preference settings. Saved comparison reports remain based on frozen 8 October inputs; interactive model calculations use the copied sheet following Refresh Google Sheet inputs. Re-run comparison generation after deliberate input changes before treating saved reports as comparisons of current settings.
