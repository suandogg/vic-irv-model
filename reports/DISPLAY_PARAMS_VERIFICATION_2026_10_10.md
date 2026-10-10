# Presentation controls verification

Target: October testing branch `codex/october-testing-2026-10-08` only.
Testing spreadsheet: `1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968`.
New tab: DISPLAY PARAMS, sheetId 1692949477; authored range A1:G76.

- All 75 settings and defaults match the native Sheet readback exactly.
- Existing spreadsheet cells and model settings were not changed.
- Header and key columns are frozen, Value is highlighted, rows wrap,
  choices use dropdowns, booleans use checkboxes and numeric values have bounds.
- Native Google Sheets visual check completed at normal zoom. Explanation is
  at the right of this wide settings grid and may require horizontal scrolling.
- Local browser checks completed for the dashboard and custom forecast seat
  intervals/event bars. Number input contrast and SVG rendering issues caught
  during visual inspection were fixed before committing.
- AppTest: Dashboard, Assembly, Council and Forecast views render without
  exceptions. Interval, histogram, both and table forecast modes render.
- Changing display settings preserves the saved forecast timestamp/results;
  display controls are excluded from the simulation fingerprint.
- 14 focused display/forecast/sheet-isolation tests pass. Full suite: 101 pass,
  one pre-existing legacy workbook fixture failure (ALP maximum difference
  0.030807616248605896 share). No engine code changed in this presentation task.
- An additional browser attempt to simulate the 2022 baseline scenario stopped
  with `float division by zero`. This is recorded for the next engine review;
  no engine fix was attempted while the user has paused engine work. Chart
  visual checks used the previously archived central-scenario 200-draw results;
  forecast UI smoke tests used successful two-draw central-scenario runs.
- Live-hosted styling is subject to Streamlit rebuild and the browser's native
  theme. Local render checked; hosted deployment needs confirmation after push.

User guide: DISPLAY_PARAMS_GUIDE.md, also downloadable from the app's sidebar
Formatting controls expander. Main, Original and reference apps remain untouched.
