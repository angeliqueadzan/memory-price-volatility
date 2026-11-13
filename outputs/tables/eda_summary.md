# Statistical analysis - Window B (n=27)

Period 2024-08 .. 2026-10. All tests use alpha = 0.05.

## 1. Integration order

| series | I(d) suggested by ADF |
|---|---|
| DDR4 | I(1) |
| DDR5 | I(1) |
| NAND | I(1) |
| SOXX | I(1) |
| MU | I(1) |
| NVDA | I(1) |

The ADF decision uses no augmentation (`adf_p_lag0`) because the sample is short (n=26 first differences); the lag-1 and AIC-selected variants are reported in the table for transparency and, as expected, lose power as extra lags consume degrees of freedom. KPSS is the complementary test.

| series | transform | n | adf_stat | adf_p_lag0 | adf_p_lag1 | adf_p_aic | adf_lags_aic | kpss_stat | kpss_p | adf_stationary_5pct | kpss_stationary_5pct | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DDR4 | level | 27 | -1.016 | 0.7474 | 0.8618 | 0.7474 | 0 | 0.684 | 0.015 | False | False | non-stationary (both tests agree) |
| DDR4 | first difference | 26 | -5.739 | 0.0 | 0.0001 | 0.0 | 0 | 0.163 | 0.1 | True | True | stationary (both tests agree) |
| DDR5 | level | 27 | -2.249 | 0.9553 | 0.947 | 0.189 | 8 | 0.666 | 0.0166 | False | False | non-stationary (both tests agree) |
| DDR5 | first difference | 26 | -2.605 | 0.0001 | 0.0835 | 0.0919 | 5 | 0.154 | 0.1 | True | True | stationary (both tests agree) |
| NAND | level | 27 | -0.692 | 0.8489 | 0.8996 | 0.8489 | 0 | 0.622 | 0.0206 | False | False | non-stationary (both tests agree) |
| NAND | first difference | 26 | -9.504 | 0.0 | 0.05 | 0.0 | 0 | 0.156 | 0.1 | True | True | stationary (both tests agree) |
| SOXX | level | 27 | 0.228 | 0.8243 | 0.7929 | 0.9738 | 7 | 0.646 | 0.0185 | False | False | non-stationary (both tests agree) |
| SOXX | first difference | 26 | -1.023 | 0.0013 | 0.0011 | 0.7447 | 9 | 0.159 | 0.1 | True | True | stationary (both tests agree) |
| MU | level | 27 | -2.16 | 0.8923 | 0.857 | 0.2211 | 8 | 0.639 | 0.0191 | False | False | non-stationary (both tests agree) |
| MU | first difference | 26 | -2.002 | 0.0017 | 0.0 | 0.2855 | 8 | 0.189 | 0.1 | True | True | stationary (both tests agree) |
| NVDA | level | 27 | -2.673 | 0.6925 | 0.6421 | 0.0788 | 9 | 0.699 | 0.0137 | False | False | non-stationary (both tests agree) |
| NVDA | first difference | 26 | -3.409 | 0.0011 | 0.0018 | 0.0107 | 5 | 0.078 | 0.1 | True | True | stationary (both tests agree) |

## 2. Level vs. returns correlation

| target | exogenous | level_pearson_r | level_pearson_p | level_spearman_rho | level_spearman_p | returns_pearson_r | returns_pearson_p | returns_spearman_rho | returns_spearman_p |
|---|---|---|---|---|---|---|---|---|---|
| DDR4 | SOXX | 0.872 | 0.0 | 0.887 | 0.0 | -0.236 | 0.2452 | -0.114 | 0.5797 |
| DDR4 | MU | 0.842 | 0.0 | 0.871 | 0.0 | -0.305 | 0.1296 | -0.237 | 0.2439 |
| DDR4 | NVDA | 0.791 | 0.0 | 0.837 | 0.0 | -0.145 | 0.4812 | -0.085 | 0.6793 |
| DDR5 | SOXX | 0.794 | 0.0 | 0.736 | 0.0 | -0.184 | 0.3686 | -0.085 | 0.6793 |
| DDR5 | MU | 0.8 | 0.0 | 0.759 | 0.0 | -0.108 | 0.6009 | 0.019 | 0.9274 |
| DDR5 | NVDA | 0.709 | 0.0 | 0.614 | 0.0007 | -0.435 | 0.0264 | -0.451 | 0.0208 |

Level correlations are large and positive for every pair, which is the expected signature of two trending series. Removing the trend (log returns) reverses or destroys the relationship, so the level figures cannot be read as predictive association.
With 24 correlation tests in this table, the Bonferroni threshold is alpha/24 = 0.0021; only results below that survive.

## 3. Lag profile, exogenous leading the RAM price

**DDR4, levels** (k>0: exogenous leads)

| lag | MU | NVDA | SOXX |
|---|---|---|---|
| 0 | 0.8417 | 0.7908 | 0.8716 |
| 1 | 0.8229 | 0.797 | 0.8625 |
| 2 | 0.7829 | 0.8137 | 0.8106 |
| 3 | 0.7081 | 0.8116 | 0.7537 |
| 4 | 0.6289 | 0.8306 | 0.6761 |
| 5 | 0.6369 | 0.8732 | 0.7018 |
| 6 | 0.7332 | 0.9042 | 0.7491 |

**DDR4, returns** (k>0: exogenous leads)

| lag | MU | NVDA | SOXX |
|---|---|---|---|
| 0 | -0.3051 | -0.1445 | -0.2363 |
| 1 | 0.2997 | 0.1929 | 0.3644 |
| 2 | 0.3724 | 0.2108 | 0.0894 |
| 3 | -0.1067 | -0.213 | -0.0489 |
| 4 | -0.2781 | -0.2271 | -0.3712 |
| 5 | 0.2342 | 0.2136 | 0.1754 |
| 6 | 0.2173 | 0.2403 | 0.2211 |

**DDR5, levels** (k>0: exogenous leads)

| lag | MU | NVDA | SOXX |
|---|---|---|---|
| 0 | 0.8003 | 0.7085 | 0.7945 |
| 1 | 0.8206 | 0.7585 | 0.8085 |
| 2 | 0.8061 | 0.8091 | 0.8129 |
| 3 | 0.7818 | 0.8539 | 0.815 |
| 4 | 0.7574 | 0.8845 | 0.8092 |
| 5 | 0.7432 | 0.941 | 0.83 |
| 6 | 0.7516 | 0.9243 | 0.8079 |

**DDR5, returns** (k>0: exogenous leads)

| lag | MU | NVDA | SOXX |
|---|---|---|---|
| 0 | -0.1076 | -0.435 | -0.1839 |
| 1 | 0.0868 | -0.1438 | -0.0957 |
| 2 | 0.3963 | -0.0637 | 0.242 |
| 3 | 0.0206 | 0.2624 | 0.0372 |
| 4 | -0.0517 | 0.0273 | 0.0071 |
| 5 | 0.2211 | 0.4767 | 0.4535 |
| 6 | 0.084 | 0.6632 | 0.1836 |

## 4. Granger causality (maxlag=3, stationary series)

| target | exogenous | direction | series_used | lag | n_obs | ssr_chi2_p | ssr_f_p | significant_5pct | min_p | bonferroni_alpha |
|---|---|---|---|---|---|---|---|---|---|---|
| DDR4 | SOXX | exogenous -> RAM | first difference | 1 | 25 | 0.0471 | 0.0759 | False | 0.0759 | 0.00139 |
| DDR4 | SOXX | exogenous -> RAM | first difference | 2 | 24 | 0.2041 | 0.3068 | False | 0.0759 | 0.00139 |
| DDR4 | SOXX | exogenous -> RAM | first difference | 3 | 23 | 0.1462 | 0.3257 | False | 0.0759 | 0.00139 |
| DDR4 | SOXX | RAM -> exogenous | first difference | 1 | 25 | 0.6689 | 0.6922 | False | 0.0775 | 0.00139 |
| DDR4 | SOXX | RAM -> exogenous | first difference | 2 | 24 | 0.0406 | 0.1056 | False | 0.0775 | 0.00139 |
| DDR4 | SOXX | RAM -> exogenous | first difference | 3 | 23 | 0.008 | 0.0775 | False | 0.0775 | 0.00139 |
| DDR4 | MU | exogenous -> RAM | first difference | 1 | 25 | 0.1104 | 0.1485 | False | 0.1485 | 0.00139 |
| DDR4 | MU | exogenous -> RAM | first difference | 2 | 24 | 0.0968 | 0.1847 | False | 0.1485 | 0.00139 |
| DDR4 | MU | exogenous -> RAM | first difference | 3 | 23 | 0.2229 | 0.4113 | False | 0.1485 | 0.00139 |
| DDR4 | MU | RAM -> exogenous | first difference | 1 | 25 | 0.9408 | 0.9451 | False | 0.157 | 0.00139 |
| DDR4 | MU | RAM -> exogenous | first difference | 2 | 24 | 0.0756 | 0.157 | False | 0.157 | 0.00139 |
| DDR4 | MU | RAM -> exogenous | first difference | 3 | 23 | 0.3108 | 0.4968 | False | 0.157 | 0.00139 |
| DDR4 | NVDA | exogenous -> RAM | first difference | 1 | 25 | 0.3377 | 0.3782 | False | 0.3782 | 0.00139 |
| DDR4 | NVDA | exogenous -> RAM | first difference | 2 | 24 | 0.4369 | 0.5306 | False | 0.3782 | 0.00139 |
| DDR4 | NVDA | exogenous -> RAM | first difference | 3 | 23 | 0.5574 | 0.7003 | False | 0.3782 | 0.00139 |
| DDR4 | NVDA | RAM -> exogenous | first difference | 1 | 25 | 0.7264 | 0.7458 | False | 0.3477 | 0.00139 |
| DDR4 | NVDA | RAM -> exogenous | first difference | 2 | 24 | 0.3666 | 0.4663 | False | 0.3477 | 0.00139 |
| DDR4 | NVDA | RAM -> exogenous | first difference | 3 | 23 | 0.1647 | 0.3477 | False | 0.3477 | 0.00139 |
| DDR5 | SOXX | exogenous -> RAM | first difference | 1 | 25 | 0.6297 | 0.6555 | False | 0.3063 | 0.00139 |
| DDR5 | SOXX | exogenous -> RAM | first difference | 2 | 24 | 0.2036 | 0.3063 | False | 0.3063 | 0.00139 |
| DDR5 | SOXX | exogenous -> RAM | first difference | 3 | 23 | 0.3779 | 0.5564 | False | 0.3063 | 0.00139 |
| DDR5 | SOXX | RAM -> exogenous | first difference | 1 | 25 | 0.4569 | 0.4926 | False | 0.2219 | 0.00139 |
| DDR5 | SOXX | RAM -> exogenous | first difference | 2 | 24 | 0.4482 | 0.5407 | False | 0.2219 | 0.00139 |
| DDR5 | SOXX | RAM -> exogenous | first difference | 3 | 23 | 0.0709 | 0.2219 | False | 0.2219 | 0.00139 |
| DDR5 | MU | exogenous -> RAM | first difference | 1 | 25 | 0.6576 | 0.6816 | False | 0.1252 | 0.00139 |
| DDR5 | MU | exogenous -> RAM | first difference | 2 | 24 | 0.0532 | 0.1252 | False | 0.1252 | 0.00139 |
| DDR5 | MU | exogenous -> RAM | first difference | 3 | 23 | 0.1253 | 0.2996 | False | 0.1252 | 0.00139 |
| DDR5 | MU | RAM -> exogenous | first difference | 1 | 25 | 0.6763 | 0.6991 | False | 0.3823 | 0.00139 |
| DDR5 | MU | RAM -> exogenous | first difference | 2 | 24 | 0.2786 | 0.3823 | False | 0.3823 | 0.00139 |
| DDR5 | MU | RAM -> exogenous | first difference | 3 | 23 | 0.2008 | 0.388 | False | 0.3823 | 0.00139 |
| DDR5 | NVDA | exogenous -> RAM | first difference | 1 | 25 | 0.4248 | 0.462 | False | 0.462 | 0.00139 |
| DDR5 | NVDA | exogenous -> RAM | first difference | 2 | 24 | 0.5544 | 0.6339 | False | 0.462 | 0.00139 |
| DDR5 | NVDA | exogenous -> RAM | first difference | 3 | 23 | 0.3106 | 0.4966 | False | 0.462 | 0.00139 |
| DDR5 | NVDA | RAM -> exogenous | first difference | 1 | 25 | 0.7161 | 0.7362 | False | 0.6918 | 0.00139 |
| DDR5 | NVDA | RAM -> exogenous | first difference | 2 | 24 | 0.6222 | 0.6918 | False | 0.6918 | 0.00139 |
| DDR5 | NVDA | RAM -> exogenous | first difference | 3 | 23 | 0.8281 | 0.8907 | False | 0.6918 | 0.00139 |

Bonferroni-corrected threshold for this table is 0.00139.
