# Formatting the October testing app

Presentation only: these settings never change primaries, preferences, count
rules, forecast draws or government definitions. Main and other apps are unchanged.

## How to use

1. Open **DISPLAY PARAMS** in the October testing spreadsheet.
2. Change **Value (column C)**. Keep Parameter (B) unchanged. Default (D) is
   a reference, not a live setting. Allowed values (F) and Explanation (G)
   describe each control. Use the filter on Section to find related settings.
3. In October testing, click **Refresh Google Sheet inputs**. Formatting applies
   on the resulting rerun. A saved forecast need not be simulated again just
   to change its appearance; genuinely changed model inputs still invalidate it.
4. To undo a setting, copy that row's Default from D to C and refresh.

The sheet has 75 active controls. Blank, unknown, duplicate or invalid values
produce a **Display settings warnings** sidebar panel and safe defaults.
Missing Google credentials or failed sync means the committed CSV/last local
inputs are used, not your new Sheet edit. Check the sync message first.

## Quick recipes

| Goal | Settings in column B → values to enter in C |
|---|---|
| Warm editorial look from the references | THEME → warm; HEADING_FONT → serif |
| Dark app | THEME → dark |
| Your own palette | THEME → custom, then edit BACKGROUND / SURFACE / TEXT / MUTED_TEXT / BORDER / ACCENT |
| Change Labor red | ALP_COLOUR → #DF3347 (or your hex colour); ALP_TEXT_COLOUR → #FFFFFF |
| Rename Coalition in summaries | LNP_LABEL → Coalition or your preferred name |
| Reorder summary parties | PARTY_ORDER → ALP,LNP,GRN,ON,IND,OTH (all six, once each) |
| Bigger text | BODY_FONT_PX → 18; CHART_LABEL_FONT_PX → 18 |
| Wider content | PAGE_MAX_WIDTH_PX → 1700 |
| Square cards | CARD_RADIUS_PX → 0 |
| Stack chambers vertically | DASHBOARD_CHAMBERS_SIDE_BY_SIDE → FALSE |
| Show seat uncertainty bands | SEAT_CHART_MODE → intervals |
| Bands and histogram | SEAT_CHART_MODE → both |
| Tables without charts | SEAT_CHART_MODE → table; GOVERNMENT_CHART_MODE → table |
| Shorter scrolling tables | TABLE_MAX_HEIGHT_PX → 350 |
| One decimal for vote percentages | PERCENT_DECIMALS → 1 |
| One decimal for forecast probabilities | PROBABILITY_DECIMALS → 1 |
| Hide parties with no seats in the displayed interval | SHOW_ZERO_SEAT_PARTIES → FALSE |
| Hide the alternate 2CP headline | SHOW_DASHBOARD_ALTERNATE_2CP → FALSE |

## What the reference-inspired charts show

Seat intervals: pale band = the selected lower–upper range from FORECAST PARAMS;
strong inner band = 25th–75th percentiles; marker = median. The majority line
is always 45 seats. SEAT_AXIS_MAX changes the displayed scale, not that threshold,
and automatically expands if a party's interval exceeds it. These remain
provisional model-based intervals, not historically calibrated probabilities.

Government bars show existing event probabilities. They are intentionally not a
pie chart: majority, hung parliament and support-route rows overlap. Formatting
does not turn those rows into mutually exclusive government-formation forecasts.

## Scope and limits

- Colours and typography style the overall page, dashboard cards and custom
  charts. THEME warm/light/dark overrides the seven base palette rows; switch
  to custom to use those rows. Party and positive/negative colours remain editable.
- Party display names/order affect summary tables and custom charts, not
  internal party codes, model tie-breaking, named Council candidates or raw CSVs.
- Table row/scroll height applies across the app. Numeric precision applies to
  percentage-named numeric columns and dashboard headlines. Some legacy detailed
  traces have custom formats; canvas table fonts are not reliably CSS-editable.
  Higher precision cannot recover digits already rounded in older display tables.
- Some Streamlit controls follow its native light/dark browser theme; CSS hooks
  can change in future Streamlit versions. The custom chart/card styles are more
  directly controlled. No arbitrary CSS, HTML, JavaScript or remote font URLs
  are accepted from the Sheet. Labels are escaped in custom charts and cards.
- Provisional warnings, evidence labels, majority thresholds, simulated values,
  simulation count and interval percentiles are not cosmetic controls.
- Long charts scroll horizontally on narrow screens. Very long party labels
  may need shortening. Keep text/background contrast readable.

To change uncertainty widths or the lower/upper percentiles, use FORECAST PARAMS,
not DISPLAY PARAMS. Such changes require rerunning the forecast.
