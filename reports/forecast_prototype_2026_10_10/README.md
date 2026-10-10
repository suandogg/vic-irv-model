# Engineering smoke run only

These files demonstrate the provisional lower-house simulation framework.
They are NOT a calibrated forecast or evidence validating the default SDs.

The run uses committed October-testing CSV inputs, the corrected-VEC-coverage
trial, 200 draws and seed 20261010. Central primaries are ALP 24.6, LNP 29.1,
GRN 13.3, ON 22, IND 5.5, OTH 5.5. See manifest.json for all uncertainty settings
and the input fingerprint. The default preview took approximately 33 seconds
locally; hosted performance can differ.

All draws allocate 88 seats. Every seat's unrounded party win frequencies total
100%. The government table contains overlapping joint-majority arithmetic rows,
not a coalition or minority-government formation prediction.

See ../FORECAST_DESIGN_2026_10_10.md for limitations and the calibration plan.
