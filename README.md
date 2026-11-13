# RAM Price Forecasting & AI Infrastructure Expansion

Reproducibility repository for the undergraduate thesis:

> **Multivariate Time-Series Forecasting and Correlation Analysis of Global AI
> Infrastructure Expansion on RAM Market Price Volatility**
> School of Computing, Telkom University, Bandung, Indonesia

The study links semiconductor / AI-infrastructure market indicators to DDR4 and
DDR5 spot-price movements, then compares **SARIMAX** against **XGBoost** for
monthly price forecasting and translates the forecasts into a COGS simulation
for three PC build profiles.

---

## 1. Environment

Python **3.12** (isolated conda environment; Python 3.14 has poor wheel support
for `statsmodels`, `scipy` and `xgboost`).

```bash
conda create -n ram-env python=3.12 -y
conda run -n ram-env pip install -r requirements.txt
```

## 2. Reproduce the datasets

```bash
conda run -n ram-env python src/preprocess.py            # uses today's cache
conda run -n ram-env python src/preprocess.py --refresh  # re-downloads sources
conda run -n ram-env python src/verify_data.py           # provenance checks
```

`verify_data.py` must print `ALL CHECKS PASSED` before any result is reported.

## 3. Data

| Role | Source | Granularity |
|---|---|---|
| Target (`DDR4`, `DDR5`; `NAND` context) | [Stanford DAM Memory Prices](https://dam.stanford.edu/memory-prices.html) - McCallum historical + Keepa/Amazon monthly cheapest listing (USD/GB) | monthly |
| Exogenous (`SOXX`, `MU`, `NVDA`) | Yahoo Finance monthly adjusted close | monthly |

Raw snapshots are stored per fetch date in `data/raw/` with their SHA-256 in
`data/processed/fetch_manifest.json`. Both are tracked in git so the analysis can
be re-run against an immutable copy.

### Two analysis windows (regime change, not missing data)

Per-module DDR4/DDR5 listings do not exist before **August 2024**; the source
switches from a generic DRAM series to per-generation modules. That is a change
of measurement regime, so the data is split instead of backfilled:

- **Window A** `2022-01 .. 2024-07` - generic DRAM baseline, context charts only
  (`DRAM_generic` is intentionally empty afterwards).
- **Window B** `2024-08 .. 2026-10`, **n = 27** - the only dataset used for
  correlation, Granger causality and model training.

## 4. Repository layout

```
src/
  datasources.py   fetch + cache + parse both primary sources
  preprocess.py    build window_B / master / scaled datasets
  verify_data.py   provenance, equality and integrity checks
  eda_stats.py     stationarity, correlation, lag CCF, Granger causality
  modeling.py      Naive / ARIMA / SARIMAX / XGBoost ladder, forecasts
  evaluate.py      RMSE / MAE / MAPE, rolling-origin folds
  cogs_sim.py      BOM + COGS scenarios for 3 build profiles
data/raw/          immutable source snapshots (sha256 in manifest)
data/processed/    analysis-ready datasets
outputs/tables/    verification report and result tables
outputs/figures/   manuscript figures (300 dpi)
```

The `manuscript/` folder exists locally but is git-ignored; see section 9.

## 5. Statistical stance

Window B has 27 monthly observations. The analysis therefore:

- reports correlations on **both** levels and first differences, because the
  level correlations are dominated by a shared trend;
- reports the **full** lag profile (0-6) with CCF confidence bands instead of a
  single "best" lag;
- leaves the direction of causality entirely to the Granger test and states the
  low statistical power openly;
- never fits a scaler or selects a feature set on the test split.

## 6. Status

| Phase | Scope | State |
|---|---|---|
| 0 | environment, data acquisition, provenance verification | done |
| 1 | stationarity, correlation, lag profile, Granger | done |
| 2 | model ladder, metrics, rolling-origin CV, 6-month forecast | done |
| 3 | COGS simulation for three build profiles | done |
| 4 | manuscript (IMRAD, RESTI/Kinetik) | withheld pending publication (section 9) |

## 7. Modelling protocol

```bash
conda run -n ram-env python src/modeling.py
```

One ladder per target (DDR4 and DDR5 modelled separately): **Naive -> ARIMA ->
SARIMAX -> XGBoost**. All models are fitted on log prices and scored on the
USD/GB scale.

Three chronological regimes, no shuffling:

| Regime | Meaning |
|---|---|
| `holdout_1step` | one-step-ahead over the last 6 months, parameters re-estimated at every origin |
| `holdout_h6` | one static 6-month forecast fitted on the first 21 months |
| `cv_rolling` | expanding-origin CV, one step ahead, 14 origins (the stable ranking) |

Safeguards:

- specification selection (ARIMA order/trend, SARIMAX exog subset, XGBoost
  preset) happens **only on the training window** and is then frozen while
  parameters are re-estimated at each origin;
- SARIMAX is reported twice: contemporaneous exogen (textbook) and exogen lagged
  one month (no look-ahead), because month `t`'s stock return is not known when
  month `t` begins;
- multi-step forecasts carry the last observed exogen forward (random walk);
  fitting on realised future stock prices is reported only as an optimistic
  reference row, which quantifies how much that assumption buys;
- `trend` handling differs between the two statsmodels classes and both are
  encoded explicitly: `ARIMA(d=1)` uses `trend='t'` for drift, whereas
  `SARIMAX(d=1)` treats `trend='t'` as a linear-in-time term inside the
  differenced equation, i.e. a quadratic - explosive - level path, so drift is
  `trend='c'`.

Result: **no model beats the random walk out of sample**. On the 14-origin CV
the paired bootstrap p-values against Naive are 0.09-0.88; Naive wins or ties on
MAPE for both targets. Reporting this is the point - the model comparison is the
contribution, not a claimed accuracy win.

## 8. COGS simulation

```bash
conda run -n ram-env python src/cogs_sim.py
```

Three build profiles - Entry/Office (16 GB DDR4), Mainstream/Gaming (32 GB
DDR5), Workstation/AI-Ready (64 GB DDR5) - are priced at the observed anchors
and at the end of the forecast horizon. The scenario->model mapping was fixed
before the simulation ran:

| Scenario | Model | Rationale |
|---|---|---|
| `base` | Naive | best rolling-origin CV MAPE on both targets (price frozen) |
| `moderate` | XGBoost | best static 6-month holdout, nearest CV runner-up |
| `high` | SARIMAX | extrapolates the fitted drift; 90% band kept as a stress case |

Every non-RAM component is held constant in nominal USD, so all movement in the
results is attributable to memory. Storage is derived from the dataset's own
NAND series (USD/GB x capacity x a 1.3x retail markup) rather than hard-coded.
Both a DRAM-only share and a DRAM+NAND share are reported, because the public
guidance used for validation quotes the bundle.

The pre-shock BOM reconstruction (Aug 2024) lands at 12.9-15.2% memory share and
the Oct 2026 reconstruction at 34.4-40.2%, which brackets the independently
disclosed HP figures of 15-18% and ~35% without any fitting to them. That is an
external check on the assumption set, not an input to it.

## 9. Manuscript (withheld)

The manuscript sources are **not part of this repository**. `manuscript/` holds
the IEEEtran draft (`manuscript.tex`), its markdown source and the Indonesian
abstract, and the whole folder is git-ignored until the paper is accepted. The
work is under submission, so the sources and the compiled PDF stay private;
they can be shared on request for review.

What the repository does contain is everything the paper is built from: the raw
and processed datasets, the analysis scripts, the result tables and the eight
300 dpi figures in `outputs/figures/` that the draft embeds. Running the
pipeline therefore reproduces every number and every figure in the paper.

A LaTeX toolchain is **not** a Python dependency and is deliberately absent from
`requirements.txt`. Locally the draft was compiled with `tectonic` kept in
`tools/` (git-ignored): the conda-forge build crashes on start with `0xC0000139`
(`STATUS_ENTRYPOINT_NOT_FOUND`), so the upstream static release is used instead
(<https://github.com/tectonic-typesetting/tectonic/releases>).

## 10. License

Code and data in this repository are released under the [MIT License](LICENSE).
The manuscript text is not covered: it stays private until publication, and
copyright is transferred to the journal of record on acceptance.


