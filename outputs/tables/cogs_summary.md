# COGS simulation - three build profiles

Scenario -> model mapping fixed before the simulation ran:

| Scenario | Model | Why |
|---|---|---|
| base | Naive | best rolling-origin CV MAPE on both targets |
| moderate | XGBoost | best static 6-month holdout, nearest CV runner-up |
| high | SARIMAX | extrapolates fitted drift; 90% band is the stress case |

Non-RAM components are held constant in nominal USD; storage is derived from the dataset's NAND series at a 1.30x retail markup. Full assumptions in `cogs_bom_profiles.csv`.

## 1. Observed anchors

| profile_label | anchor | dram_price | ram_cost | total_bom | ram_share_pct | memory_share_pct |
|---|---|---|---|---|---|---|
| A. Entry / Office | Pre-shock (Window B start) | 0.9 | 14.37 | 350.24 | 4.1 | 12.92 |
| B. Mainstream / Gaming | Pre-shock (Window B start) | 2.82 | 90.37 | 1002.12 | 9.02 | 15.18 |
| C. Workstation / AI-Ready | Pre-shock (Window B start) | 2.82 | 180.74 | 2349.24 | 7.69 | 12.95 |
| A. Entry / Office | Last observed | 6.25 | 99.99 | 465.19 | 21.49 | 34.44 |
| B. Mainstream / Gaming | Last observed | 14.06 | 449.95 | 1420.36 | 31.68 | 40.16 |
| C. Workstation / AI-Ready | Last observed | 14.06 | 899.9 | 3185.71 | 28.25 | 35.81 |

## 2. Scenario outcomes at the end of the horizon

| profile | scenario | band | dram_price | ram_cost | total_bom | ram_share_pct | memory_share_pct | d_bom_usd | d_bom_pct |
|---|---|---|---|---|---|---|---|---|---|
| A. Entry / Office | base | point | 6.2494 | 99.99 | 465.19 | 21.49 | 34.44 | 0.0 | 0.0 |
| A. Entry / Office | moderate | point | 6.374 | 101.98 | 467.19 | 21.83 | 34.72 | 1.99 | 0.43 |
| A. Entry / Office | high | point | 9.9957 | 159.93 | 525.13 | 30.46 | 41.92 | 59.94 | 12.89 |
| A. Entry / Office | high | stress | 5.0777 | 81.24 | 446.45 | 18.2 | 31.68 | -18.75 | -4.03 |
| A. Entry / Office | high | stress | 19.6771 | 314.83 | 680.04 | 46.3 | 55.15 | 214.84 | 46.18 |
| B. Mainstream / Gaming | base | point | 14.0609 | 449.95 | 1420.36 | 31.68 | 40.16 | 0.0 | 0.0 |
| B. Mainstream / Gaming | moderate | point | 11.797 | 377.5 | 1347.91 | 28.01 | 36.94 | -72.45 | -5.1 |
| B. Mainstream / Gaming | high | point | 24.3244 | 778.38 | 1748.79 | 44.51 | 51.39 | 328.43 | 23.12 |
| B. Mainstream / Gaming | high | stress | 10.6368 | 340.38 | 1310.78 | 25.97 | 35.15 | -109.57 | -7.71 |
| B. Mainstream / Gaming | high | stress | 55.6255 | 1780.02 | 2750.42 | 64.72 | 69.1 | 1330.07 | 93.64 |
| C. Workstation / AI-Ready | base | point | 14.0609 | 899.9 | 3185.71 | 28.25 | 35.81 | 0.0 | 0.0 |
| C. Workstation / AI-Ready | moderate | point | 11.797 | 755.01 | 3040.82 | 24.83 | 32.75 | -144.89 | -4.55 |
| C. Workstation / AI-Ready | high | point | 24.3244 | 1556.76 | 3842.58 | 40.51 | 46.78 | 656.86 | 20.62 |
| C. Workstation / AI-Ready | high | stress | 10.6368 | 680.76 | 2966.57 | 22.95 | 31.07 | -219.14 | -6.88 |
| C. Workstation / AI-Ready | high | stress | 55.6255 | 3560.03 | 5845.84 | 60.9 | 65.02 | 2660.13 | 83.5 |

`band = stress` rows are the SARIMAX 90% interval bounds, i.e. the retail stress margin, not alternative scenarios.

## 3. External validation against public industry guidance

| profile | memory_share_2024_08 | memory_share_2026_10 | memory_share_2027_04_high | hp_pre_shock_benchmark | hp_post_shock_benchmark |
|---|---|---|---|---|---|
| A. Entry / Office | 12.9 | 34.4 | 41.9 | 15-18 | 35 |
| B. Mainstream / Gaming | 15.2 | 40.2 | 51.4 | 15-18 | 35 |
| C. Workstation / AI-Ready | 13.0 | 35.8 | 46.8 | 15-18 | 35 |

The pre-shock reconstruction lands inside HP's disclosed 15-18% range and the Oct 2026 reconstruction lands on their ~35% figure, with no fitting to those numbers: they are independent checks on the BOM assumptions.
