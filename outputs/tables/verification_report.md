# Data verification report

Generated: 2026-11-12 13:51 UTC

## 1. Snapshot identity

| source | file | bytes | SHA-256 |
|---|---|---|---|
| Stanford DAM memory prices | `data\raw\stanford_memory-prices_2026-11-12.csv` | 207,221 | `dcb1aa5e1adbfd6e238b6960ceaab8489c95a9a16ff5a0bd15e8ba9242c52682` |
| Yahoo Finance SOXX (monthly adj. close) | `data\raw\yahoo_SOXX_1mo_2026-11-12.json` | 9,408 | `33ea4fbb400b2a34818e9191d28c088dff648cb88183a528df3385a9a603f3f6` |
| Yahoo Finance MU (monthly adj. close) | `data\raw\yahoo_MU_1mo_2026-11-12.json` | 8,741 | `8a718e31296f4147e5406395efe817761f697f8a3879f323e63513cddc818bd7` |
| Yahoo Finance NVDA (monthly adj. close) | `data\raw\yahoo_NVDA_1mo_2026-11-12.json` | 9,262 | `e7ce3296cf883b14be0788e585800be5e7233ab8400a0d6fb36ace6aa5381884` |

Source URLs: `https://dam.stanford.edu/assets/memory-prices/memory-prices.csv`; `https://query1.finance.yahoo.com/v8/finance/chart/<symbol>`

## 2. Cell-level equality against the primary sources

| series | n | exact match | max abs diff | tolerance | out of tolerance |
|---|---|---|---|---|---|
| DDR4 | 27 | 27 | 0.00e+00 | 5e-05 | 0 |
| DDR5 | 27 | 27 | 0.00e+00 | 5e-05 | 0 |
| NAND | 27 | 27 | 0.00e+00 | 5e-05 | 0 |
| SOXX | 27 | 27 | 4.83e-03 | 5e-03 | 0 |
| MU | 27 | 27 | 4.89e-03 | 5e-03 | 0 |
| NVDA | 27 | 27 | 4.98e-03 | 5e-03 | 0 |

**Verdict: PASS** — every Window B value is reproduced from its primary source.

## 3. Structural integrity (Window B)

- months: **27** (2024-08 .. 2026-10)
- continuous monthly index: **True**
- missing cells: **0**
- non-positive prices: **0**
- repeated consecutive observations (real, from source): DDR4: ['2026-01'], DDR5: ['2026-02'], NAND: ['2025-04', '2025-05', '2025-06', '2025-11'], SOXX: ['2024-09'], MU: -, NVDA: -

## 4. Regime-change handling (context series)

- master series: **58** months (2022-01 .. 2026-10), continuous: **True**
- `DRAM_generic` last valid month: **2024-07**
- `DRAM_generic` empty after 2024-07 (no cross-regime backfill): **True**

## 5. Basket size behind each RAM observation

Stanford reports the number of Amazon listings used for the monthly 'cheapest listing'. A small basket means a noisier estimate; months with fewer than 15 listings are flagged because they drive part of the month-on-month volatility.

| series | months | min_n | median_n | max_n | months_with_n_lt_15 | which |
|---|---|---|---|---|---|---|
| DDR4 | 27 | 8 | 55 | 267 | 5 | 2024-12 (n=10), 2025-02 (n=8), 2025-03 (n=9), 2025-04 (n=12), 2025-05 (n=12) |
| DDR5 | 27 | 17 | 86 | 310 | 0 | - |
| NAND | 27 | 93 | 117 | 200 | 0 | - |

## 6. Largest month-on-month moves (Window B)

**DDR4**

| month | value | mom_pct |
|---|---|---|
| 2024-09 | 1.625 | 81.0 |
| 2026-02 | 6.2475 | 54.8 |
| 2025-11 | 3.6738 | 50.3 |

**DDR5**

| month | value | mom_pct |
|---|---|---|
| 2025-11 | 4.9688 | 70.1 |
| 2025-01 | 2.7556 | 50.0 |
| 2026-01 | 9.8738 | 44.2 |

**SOXX**

| month | value | mom_pct |
|---|---|---|
| 2026-04 | 153.64 | 40.4 |
| 2026-05 | 189.48 | 23.3 |
| 2026-07 | 168.19 | -21.2 |

**MU**

| month | value | mom_pct |
|---|---|---|
| 2026-05 | 970.7 | 87.8 |
| 2026-04 | 517.0 | 53.1 |
| 2026-01 | 414.58 | 45.4 |

**NVDA**

| month | value | mom_pct |
|---|---|---|
| 2025-05 | 134.79 | 24.1 |
| 2025-06 | 157.6 | 16.9 |
| 2026-04 | 199.11 | 14.4 |

## 7. Descriptive statistics (Window B)

| index | DDR4 | DDR5 | NAND | SOXX | MU | NVDA |
|---|---|---|---|---|---|---|
| count | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 | 27.0 |
| mean | 3.7708 | 5.8658 | 0.0608 | 107.877 | 360.0219 | 166.8526 |
| std | 2.2926 | 4.1996 | 0.0221 | 45.6628 | 359.0341 | 37.0393 |
| min | 0.898 | 1.8372 | 0.0356 | 60.82 | 76.74 | 108.11 |
| 25% | 1.8209 | 2.5229 | 0.0452 | 72.035 | 96.525 | 133.17 |
| 50% | 2.75 | 2.9166 | 0.0475 | 90.08 | 167.03 | 176.58 |
| 75% | 6.2484 | 9.8738 | 0.0861 | 135.435 | 465.79 | 199.49 |
| max | 7.8656 | 14.0609 | 0.0995 | 213.45 | 1153.93 | 228.38 |
