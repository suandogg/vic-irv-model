# Main preference-assumption review — 10 October 2026

## What changed

An optional sensitivity panel was added to Main. Its central count, primary-vote
construction, Sheet sync, special priors and production weights are unchanged.
The panel compares eight alternative configurations on identical seat primaries.
It lists changed winners, five demonstration seats and actual primary-origin
preference parcels with their source, federal sample size, blend weight and flows.
Both the central and alternative configurations can be inspected seat by seat.

These archived reports use committed CSV inputs, not a claim about the current
live Sheet. The app recomputes from its currently loaded inputs. The manifest
hashes the CSV snapshot. `tools/report_main_sensitivity.py` reuses the actual
app primary-construction function without running UI or Google sync, asserts
central-count equality, and produces the three scenario reports.

## Results

ALP/LNP/GRN primaries remain 24.6/29.1/13.3 in all scenarios. Lower ON uses
ON/IND/OTH 19/7/7; central uses 22/5.5/5.5; higher ON uses 25/4/4.

| Preference configuration | Lower ON: ALP/LNP/GRN/ON/IND | Central: ALP/LNP/GRN/ON/IND | Higher ON: ALP/LNP/GRN/ON/IND |
|---|---|---|---|
| Unchanged Main | 31/44/5/8/0 | 30/37/5/15/1 | 23/40/5/20/0 |
| Two sparse federal pools off | 31/44/5/8/0 | 30/37/5/15/1 | 23/40/5/20/0 |
| Generic pass-through | 36/38/6/8/0 | 30/36/6/15/1 | 26/37/6/19/0 |
| Pass-through + sparse pools off | 36/38/6/8/0 | 30/36/6/15/1 | 27/36/6/19/0 |
| OTH preference depletion off | 31/44/5/8/0 | 30/37/5/15/1 | 23/40/5/20/0 |
| All three architecture changes | 36/38/6/8/0 | 30/36/6/15/1 | 27/36/6/19/0 |
| Special priors: ON minus 5 pp | 33/44/5/6/0 | 33/37/5/12/1 | 28/40/5/15/0 |
| Special priors: ON plus 5 pp | 31/43/5/9/0 | 27/37/5/18/1 | 23/38/5/22/0 |

OTH wins no seats in these counts. Equal aggregate counts do not guarantee
identical seat winners. Consult the seat CSVs for changes and elimination pairs.
The illustrative ±5 pp changes are not calibrated plausible limits or probabilities.
Only their separate comparison copies alter ON_SPECIAL_SCENARIO_PRIORS; neither
the central model nor generic-pass-through configurations change those rows.

Central-scenario consequential seats across these alternatives: Bellarine,
Frankston, Narre Warren North, Narre Warren South, Pascoe Vale, Point Cook,
Sydenham and Wendouree. `central_consequential_assumptions.csv` shows their actual
central preference parcels. The panel can also trace each alternative's count.

## Federal endpoint check

The adjacent `federal_endpoint_audit_2026_10_10` report checks 202 non-finalist
candidates in 38 Victorian federal divisions. Aggregate DOP counts reconcile
cell-for-cell with the official download; original-voter endpoints do not always
match Antony Green's February 2026 compilation of AEC endpoint counts.

Across all 38 ON candidates the mean absolute discrepancy is 8.24 preference
percentage points. This is NOT an 8.24-point error in Victorian seat votes.
Many of those observed finalist pairs/fields are not used by the state model.
In the three-seat active ON→ALP/LNP pool, reconstructed ALP shares exceed
published endpoints by 1.09, 4.32 and 1.10 pp (mean +2.17 pp). The one-seat
Indi ON→IND/LNP pool is below the configured minimum sample size.
The other sparse pool, GRN→ALP/LNP/ON, is an intermediate field: this final-pair
report cannot validate it directly. No endpoint is invented for a hypothetical
Victorian ON contest. The endpoint document previously informed classification
metadata, so this audit is not a pristine held-out forecasting test.

## Recommendation

Keep central rules unchanged pending review of the consequential assumptions.
Prioritise special ON final-pair flows and the generic ranking assumption:
these have material effects and are not established by 2022 reconstruction.
The sparse-pool and OTH-depletion switches have smaller outcome effects here.
The combined higher-ON result demonstrates interaction: removing sparse pools
changes one additional winner when pass-through is also enabled, despite no
winner changes when sparse pools are removed alone.

The dashboard's 2PP remains Main's unweighted mean of seat 2PP, not a
turnout-weighted statewide measure. Preference sensitivity is not total forecast
uncertainty: primary geography, polling and candidate uncertainty are held fixed.

## Verification

Five new sensitivity unit tests and four Main-repair tests pass. Streamlit
AppTest checks the central scenario, panel calculation, alternative parcel
inspection, 100% flow sums and unchanged headline metrics when comparisons are
enabled. All three archived central counts exactly match Main's existing count.
The full suite has one pre-existing legacy primary-workbook fixture failure
(maximum ALP difference 0.0000006615 against a 0.0000000001 tolerance); the
primary-vote code and that fixture were not changed in this work.
