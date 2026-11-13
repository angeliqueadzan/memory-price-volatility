# Modelling results - Window B (n=27, 21 train / 6 test)

All models fitted on log prices; metrics on USD/GB.

## 1. Selected specifications (chosen on the training window only)

| target | model | order | drift | trend_code | exog | preset | aic | inner_mae |
|---|---|---|---|---|---|---|---|---|
| DDR4 | Naive | - | no | - | - | - | - | - |
| DDR4 | ARIMA | (2, 1, 0) | yes | t | - | - | -3.92 | - |
| DDR4 | ARIMA (no drift) | (0, 1, 1) | no | n | - | - | -1.69 | - |
| DDR4 | SARIMAX | (0, 1, 0) | yes | c | MU | - | -8.46 | - |
| DDR4 | XGBoost | - | no | - | SOXX+MU+NVDA | {'n_estimators': 200, 'max_depth': 1, 'learning_rate': 0.05} | - | 0.9797 |
| DDR4 | SARIMAX (exog lag-1) | (0, 1, 0) | no | n | SOXX | - | -15.41 | - |
| DDR5 | Naive | - | no | - | - | - | - | - |
| DDR5 | ARIMA | (1, 1, 2) | no | n | - | - | -2.43 | - |
| DDR5 | SARIMAX | (0, 1, 1) | yes | c | MU+NVDA | - | -3.96 | - |
| DDR5 | XGBoost | - | no | - | SOXX+MU+NVDA | {'n_estimators': 100, 'max_depth': 2, 'learning_rate': 0.05} | - | 2.4007 |
| DDR5 | SARIMAX (exog lag-1) | (1, 1, 0) | yes | c | MU+NVDA | - | -1.98 | - |

## 2. Accuracy

### Out-of-sample, one-step (6 months)

| model | DDR4_mape | DDR5_mape | DDR4_rmse | DDR5_rmse |
|---|---|---|---|---|
| ARIMA | 25.266 | 32.12 | 2.034 | 3.527 |
| ARIMA (no drift) | 22.867 |  | 2.072 |  |
| Naive | 13.652 | 19.148 | 1.16 | 2.258 |
| SARIMAX | 17.198 | 48.429 | 1.293 | 6.989 |
| SARIMAX (exog lag-1) | 28.629 | 37.217 | 2.781 | 4.398 |
| XGBoost | 11.736 | 18.162 | 0.888 | 2.426 |

### Out-of-sample, static 6-month forecast

| model | DDR4_mape | DDR5_mape | DDR4_rmse | DDR5_rmse |
|---|---|---|---|---|
| ARIMA | 56.588 | 33.75 | 4.188 | 3.646 |
| ARIMA (no drift) | 15.953 |  | 1.138 |  |
| Naive | 11.58 | 20.706 | 0.826 | 2.375 |
| SARIMAX | 60.436 | 30.712 | 4.477 | 3.238 |
| SARIMAX (exog lag-1) | 11.58 | 30.795 | 0.826 | 3.138 |
| SARIMAX (realised exog) | 34.268 | 152.737 | 2.738 | 15.689 |
| XGBoost | 10.34 | 19.988 | 0.725 | 2.368 |

### Rolling-origin CV, one-step (14 origins)

| model | DDR4_mape | DDR5_mape | DDR4_rmse | DDR5_rmse |
|---|---|---|---|---|
| ARIMA | 21.026 | 23.643 | 1.49 | 2.636 |
| ARIMA (no drift) | 20.679 |  | 1.637 |  |
| Naive | 16.544 | 20.979 | 1.087 | 2.157 |
| SARIMAX | 18.108 | 35.74 | 1.082 | 4.927 |
| SARIMAX (exog lag-1) | 19.645 | 30.431 | 1.966 | 3.371 |
| XGBoost | 16.574 | 22.354 | 1.004 | 2.37 |

## 3. Is any model better than the random walk?

Paired bootstrap (4000 resamples) of the difference in mean absolute error on the rolling-origin CV, one step ahead. Positive means the model is worse than the random walk.

| target | model | mae_cv_vs_naive | bootstrap_p | n |
|---|---|---|---|---|
| DDR4 | ARIMA | 0.2624 | 0.245 | 14 |
| DDR4 | ARIMA (no drift) | 0.3308 | 0.09 | 14 |
| DDR4 | SARIMAX | 0.0435 | 0.7665 | 14 |
| DDR4 | XGBoost | 0.0116 | 0.8815 | 14 |
| DDR4 | SARIMAX (exog lag-1) | 0.4256 | 0.4295 | 13 |
| DDR5 | ARIMA | 0.2327 | 0.583 | 14 |
| DDR5 | SARIMAX | 1.0693 | 0.189 | 14 |
| DDR5 | XGBoost | 0.1075 | 0.6665 | 14 |
| DDR5 | SARIMAX (exog lag-1) | 0.6525 | 0.216 | 13 |

## 4. Six-month forward forecast (USD/GB)

**DDR4 - ARIMA**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 6.809 | 4.922 | 9.419 |
| 2026-12 | 7.536 | 4.842 | 11.73 |
| 2027-01 | 8.036 | 4.915 | 13.141 |
| 2027-02 | 8.557 | 4.977 | 14.71 |
| 2027-03 | 9.204 | 5.068 | 16.714 |
| 2027-04 | 9.897 | 5.193 | 18.86 |

**DDR4 - SARIMAX**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 6.758 | 5.126 | 8.911 |
| 2026-12 | 7.309 | 4.943 | 10.806 |
| 2027-01 | 7.904 | 4.896 | 12.759 |
| 2027-02 | 8.547 | 4.916 | 14.859 |
| 2027-03 | 9.243 | 4.981 | 17.153 |
| 2027-04 | 9.996 | 5.078 | 19.677 |

**DDR4 - ARIMA (no drift)**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 6.213 | 4.35 | 8.873 |
| 2026-12 | 6.213 | 3.651 | 10.571 |
| 2027-01 | 6.213 | 3.205 | 12.041 |
| 2027-02 | 6.213 | 2.876 | 13.422 |
| 2027-03 | 6.213 | 2.615 | 14.76 |
| 2027-04 | 6.213 | 2.4 | 16.079 |

**DDR4 - XGBoost**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 6.374 | 6.374 | 6.374 |
| 2026-12 | 6.374 | 6.356 | 6.374 |
| 2027-01 | 6.374 | 6.356 | 6.374 |
| 2027-02 | 6.374 | 6.015 | 6.374 |
| 2027-03 | 6.374 | 6.015 | 6.374 |
| 2027-04 | 6.374 | 6.015 | 6.374 |

**DDR5 - ARIMA**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 14.963 | 10.441 | 21.442 |
| 2026-12 | 15.16 | 9.207 | 24.962 |
| 2027-01 | 15.242 | 7.372 | 31.513 |
| 2027-02 | 15.276 | 5.942 | 39.272 |
| 2027-03 | 15.29 | 4.902 | 47.687 |
| 2027-04 | 15.295 | 4.133 | 56.608 |

**DDR5 - SARIMAX**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 15.474 | 10.927 | 21.913 |
| 2026-12 | 16.939 | 10.446 | 27.468 |
| 2027-01 | 18.543 | 10.294 | 33.4 |
| 2027-02 | 20.299 | 10.31 | 39.965 |
| 2027-03 | 22.22 | 10.433 | 47.325 |
| 2027-04 | 24.324 | 10.637 | 55.625 |

**DDR5 - XGBoost**

| month | point | low_90 | high_90 |
|---|---|---|---|
| 2026-11 | 10.651 | 10.651 | 10.651 |
| 2026-12 | 10.512 | 10.512 | 10.512 |
| 2027-01 | 12.753 | 11.797 | 12.753 |
| 2027-02 | 12.854 | 11.797 | 12.875 |
| 2027-03 | 11.89 | 10.595 | 11.954 |
| 2027-04 | 11.797 | 10.512 | 11.797 |
