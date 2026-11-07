# Labor low-baseline taper, 7 November 2026

Testing only, off by default. Not an approved central method. Review evidence is in `~/Documents/State Model/alp_low_baseline_review_2026_11_07/`.

**What it does.** With the sidebar switch on, or `low_base_taper` in a forecast experiment:

1. Labor's seat component becomes `B + swing x min(1, B / 0.30)`, where `B = 0.3821 + ALP_pvi` and `swing = target - 0.3821`.
2. Labor's simulated lean error is multiplied by `min(1, share / 0.30)`, on both the structured nowcast and ordinary local-noise paths.

Seats at or above 30% keep the full additive swing. There is no floor. Other parties, the RNG streams and the -0.24 PVI inputs are unchanged. The code is in `SRC/low_base_taper.py`.

**Verified.** 5,000 draws, seed 20261010, release settings, Version B on. Switch off matches `live_released` draw for draw. Switch on matches the reviewed `hybrid_0.30@errtaper` run draw for draw.

| Version B | ALP | LNP | ON | GRN | IND | OTH |
|---|---|---|---|---|---|---|
| Off, average seats | 26.93 | 41.54 | 13.17 | 5.75 | 0.54 | 0.07 |
| On, average seats | 25.09 | 42.64 | 13.62 | 5.96 | 0.62 | 0.07 |

**Not covered.**

- Shepparton stays near 3.7% centrally, held down by the Provincial ON donor row and an unreviewed IND surface of about 31%.
- Seats with no Labor candidate still receive Labor votes. Recheck Euroa, Malvern and Ovens Valley after nominations close on 9 November.
- The website scripts do not pass this setting, so a release built from them has the taper off. The central PRISM path also needs it before publishing.
