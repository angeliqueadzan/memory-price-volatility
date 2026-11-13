"""eda_stats.py
==============
Stationarity, correlation and Granger causality for Window B (n=27).

Why this script is written the way it is
----------------------------------------
DDR4, DDR5, SOXX, MU and NVDA all trend upwards over 2024-08..2026-10. Two
trending series will always show a large Pearson r, so a level correlation is
evidence of *co-movement*, not of a leading relationship. This script therefore
reports, side by side:

* correlations on **levels** (what the previous session reported),
* correlations on **monthly log returns** (trend removed),
* Spearman rank correlations on both, which are immune to monotone transforms,
* the **full** lag profile -6..+6 instead of one hand-picked lag,
* Granger tests only on stationary series, with the caveat about power.

Outputs
-------
outputs/tables/stationarity_results.csv
outputs/tables/correlation_levels_pearson.csv
outputs/tables/correlation_levels_spearman.csv
outputs/tables/correlation_returns_pearson.csv
outputs/tables/correlation_returns_spearman.csv
outputs/tables/correlation_summary.csv
outputs/tables/lag_ccf.csv
outputs/tables/granger_results.csv
outputs/tables/eda_summary.md
outputs/figures/fig01_window_b_series.png
outputs/figures/fig02_correlation_heatmaps.png
outputs/figures/fig03_ccf_DDR4.png
outputs/figures/fig03_ccf_DDR5.png
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import (
    adfuller,
    grangercausalitytests,
    kpss,
)

# statsmodels 0.15 warns about upcoming result-object defaults and about KPSS
# p-values that sit on the edge of the lookup table; both are noise here.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=InterpolationWarning)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import FIG_DPI  # noqa: E402

TARGETS = ["DDR4", "DDR5"]
EXOG = ["SOXX", "MU", "NVDA"]
ALL_COLS = ["DDR4", "DDR5", "NAND", "SOXX", "MU", "NVDA"]
MAXLAG = 6
ALPHA = 0.05

PALETTE = {"DDR4": "#1f4e79", "DDR5": "#c00000", "NAND": "#7f7f7f",
           "SOXX": "#2e7d32", "MU": "#b26a00", "NVDA": "#6a1b9a"}


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_window_b() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "window_B_ai_shock_period_monthly.csv",
                     index_col=0, parse_dates=True)
    df.index.name = "month"
    return df


def log_returns(df: pd.DataFrame) -> pd.DataFrame:
    return np.log(df).diff().dropna()


# --------------------------------------------------------------------------- #
# stationarity
# --------------------------------------------------------------------------- #
def stationarity_table(levels: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    """ADF + KPSS on levels and first differences.

    With n=26 first differences, ADF with AIC-selected augmentation (5-9 lags)
    exhausts the sample and loses all power, so the decision uses ADF at 0 and 1
    augmentation lags - the usual choice for monthly data of this length - and
    keeps the AIC variant only as a reference column.
    """
    rows = []
    for col in ALL_COLS:
        for transform, serie in (("level", levels[col]),
                                 ("first difference", rets[col])):
            adf_p0 = adfuller(serie, maxlag=0, autolag=None)[1]
            adf_p1 = adfuller(serie, maxlag=1, autolag=None)[1]
            adf_stat, adf_p, adf_lags, _, _, _ = adfuller(serie, autolag="AIC")
            try:
                kpss_stat, kpss_p, _, _ = kpss(serie, regression="c", nlags="auto")
            except Exception:  # very short / degenerate series
                kpss_stat, kpss_p = np.nan, np.nan
            rows.append({
                "series": col,
                "transform": transform,
                "n": int(serie.notna().sum()),
                "adf_stat": round(adf_stat, 3),
                "adf_p_lag0": round(adf_p0, 4),
                "adf_p_lag1": round(adf_p1, 4),
                "adf_p_aic": round(adf_p, 4),
                "adf_lags_aic": int(adf_lags),
                "kpss_stat": round(kpss_stat, 3) if pd.notna(kpss_stat) else np.nan,
                "kpss_p": round(kpss_p, 4) if pd.notna(kpss_p) else np.nan,
            })
    out = pd.DataFrame(rows)
    out["adf_stationary_5pct"] = out["adf_p_lag0"] < ALPHA
    out["kpss_stationary_5pct"] = out["kpss_p"] > ALPHA
    out["verdict"] = np.where(
        out["adf_stationary_5pct"] & out["kpss_stationary_5pct"],
        "stationary (both tests agree)",
        np.where(~out["adf_stationary_5pct"] & ~out["kpss_stationary_5pct"],
                 "non-stationary (both tests agree)", "conflicting"))
    return out


def integration_order(station: pd.DataFrame) -> dict[str, int]:
    order = {}
    for col in ALL_COLS:
        s = station[station["series"] == col].set_index("transform")
        level_stat = bool(s.loc["level", "adf_stationary_5pct"])
        diff_stat = bool(s.loc["first difference", "adf_stationary_5pct"])
        order[col] = 0 if level_stat else (1 if diff_stat else 2)
    return order


# --------------------------------------------------------------------------- #
# correlation
# --------------------------------------------------------------------------- #
def correlation_summary(levels: pd.DataFrame,
                        rets: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        for x in EXOG:
            lp, lpv = stats.pearsonr(levels[x], levels[target])
            ls, lsp = stats.spearmanr(levels[x], levels[target])
            rp, rpv = stats.pearsonr(rets[x], rets[target])
            rs, rsp = stats.spearmanr(rets[x], rets[target])
            rows.append({
                "target": target,
                "exogenous": x,
                "level_pearson_r": round(lp, 3),
                "level_pearson_p": round(lpv, 4),
                "level_spearman_rho": round(ls, 3),
                "level_spearman_p": round(lsp, 4),
                "returns_pearson_r": round(rp, 3),
                "returns_pearson_p": round(rpv, 4),
                "returns_spearman_rho": round(rs, 3),
                "returns_spearman_p": round(rsp, 4),
            })
    return pd.DataFrame(rows)


def lag_profile(x: pd.Series, y: pd.Series,
                maxlag: int = MAXLAG) -> pd.DataFrame:
    """corr(x_t, y_{t+k}); k>0 means x leads y by k months.

    Sign convention: positive ``lag`` = exogenous variable leads the RAM price.
    """
    rows = []
    for k in range(-maxlag, maxlag + 1):
        if k >= 0:
            a, b = x.iloc[:len(x) - k], y.iloc[k:]
        else:
            a, b = x.iloc[-k:], y.iloc[:len(y) + k]
        n = len(a)
        r, p = stats.pearsonr(a, b)
        rows.append({
            "lag": k,
            "n": n,
            "r": r,
            "p_value": p,
            "ci_band": 1.96 / np.sqrt(n),
            "significant_5pct": bool(p < ALPHA),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Granger causality
# --------------------------------------------------------------------------- #
def granger_pair(y: pd.Series, x: pd.Series, maxlag: int = 3) -> pd.DataFrame:
    """Test whether ``x`` Granger-causes ``y`` (statsmodels wants [y, x])."""
    data = pd.concat([y, x], axis=1).dropna()
    res = grangercausalitytests(data.to_numpy(), maxlag=maxlag)
    rows = []
    for lag, tests in res.items():
        rows.append({
            "lag": lag,
            "ssr_ftest_p": tests[0]["ssr_ftest"][1],
            "ssr_chi2test_p": tests[0]["ssr_chi2test"][1],
            "lrtest_p": tests[0]["lrtest"][1],
            "params_ftest_p": tests[0]["params_ftest"][1],
            "n_obs": int(len(data) - lag),
        })
    return pd.DataFrame(rows)


def granger_table(levels: pd.DataFrame,
                  rets: pd.DataFrame, order: dict[str, int]) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        for x in EXOG:
            y_stat = rets[target] if order[target] >= 1 else levels[target]
            x_stat = rets[x] if order[x] >= 1 else levels[x]
            for direction, (yy, xx) in {
                "exogenous -> RAM": (y_stat, x_stat),
                "RAM -> exogenous": (x_stat, y_stat),
            }.items():
                g = granger_pair(yy, xx, maxlag=3)
                for _, r in g.iterrows():
                    rows.append({
                        "target": target,
                        "exogenous": x,
                        "direction": direction,
                        "series_used": "first difference" if order[target] >= 1 else "level",
                        "lag": int(r["lag"]),
                        "n_obs": int(r["n_obs"]),
                        "ssr_chi2_p": round(float(r["ssr_chi2test_p"]), 4),
                        "ssr_f_p": round(float(r["ssr_ftest_p"]), 4),
                        "significant_5pct": bool(float(r["ssr_ftest_p"]) < ALPHA),
                    })
    out = pd.DataFrame(rows)
    out["min_p"] = out.groupby(["target", "exogenous", "direction"])["ssr_f_p"] \
                      .transform("min")
    # Bonferroni across all lag tests in this table.
    out["bonferroni_alpha"] = round(ALPHA / max(len(out), 1), 5)
    return out


# --------------------------------------------------------------------------- #
# figures
# --------------------------------------------------------------------------- #
def fig_series(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(11, 8.5), sharex=True)
    for ax, col in zip(axes.flat, ALL_COLS[:6]):
        ax.plot(df.index, df[col], color=PALETTE[col], lw=1.8, marker="o", ms=2.6)
        ax.set_title(col, fontsize=10, fontweight="bold", loc="left")
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        unit = "USD/GB" if col in ("DDR4", "DDR5", "NAND") else "USD"
        ax.set_ylabel(unit, fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("month", fontsize=8)
    fig.suptitle("Window B: AI-shock period, 2024-08 to 2026-10 (n=27)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig01_window_b_series.png", dpi=FIG_DPI)
    plt.close(fig)


def fig_heatmaps(mats: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    titles = {
        "levels_pearson": "Pearson - levels (trend-driven)",
        "levels_spearman": "Spearman - levels",
        "returns_pearson": "Pearson - monthly log returns",
        "returns_spearman": "Spearman - monthly log returns",
    }
    for ax, (key, mat) in zip(axes.flat, mats.items()):
        sns.heatmap(mat, ax=ax, annot=True, fmt=".2f", cmap="RdBu_r",
                    vmin=-1, vmax=1, square=True, cbar_kws={"shrink": .8},
                    annot_kws={"size": 8})
        ax.set_title(titles[key], fontsize=11, fontweight="bold")
        ax.tick_params(labelsize=8)
    fig.suptitle("Correlation structure, Window B (n=27)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig02_correlation_heatmaps.png", dpi=FIG_DPI)
    plt.close(fig)


def fig_ccf(levels: pd.DataFrame, rets: pd.DataFrame, target: str) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.2), sharey=True)
    for row, (label, df) in enumerate([("levels", levels),
                                       ("monthly log returns", rets)]):
        for col, x in enumerate(EXOG):
            ax = axes[row, col]
            prof = lag_profile(df[x], df[target])
            band = float(prof.loc[prof["lag"] == 0, "ci_band"].iloc[0])
            colors = ["#c00000" if p < ALPHA else "#9e9e9e"
                      for p in prof["p_value"]]
            ax.vlines(prof["lag"], 0, prof["r"], color=colors, lw=1.6)
            ax.scatter(prof["lag"], prof["r"], color=colors, s=22, zorder=3)
            ax.axhline(0, color="black", lw=0.8)
            ax.axhspan(-band, band, color="#4c72b0", alpha=0.15, lw=0)
            ax.set_title(f"{x} -> {target}  ({label})", fontsize=9.5,
                         fontweight="bold")
            ax.grid(alpha=0.25, lw=0.6)
            ax.set_xticks(range(-MAXLAG, MAXLAG + 1))
            ax.set_ylim(-1.05, 1.05)
            ax.tick_params(labelsize=8)
            if col == 0:
                ax.set_ylabel("correlation", fontsize=9)
            if row == 1:
                ax.set_xlabel("lag k (months); k>0 = exogenous leads RAM", fontsize=8)
    fig.suptitle(
        f"{target}: cross-correlation profile - red = p<0.05, band = +/-1.96/sqrt(n)",
        fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / f"fig03_ccf_{target}.png", dpi=FIG_DPI)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def md_table(df: pd.DataFrame, index: bool = False) -> str:
    df = df.copy()
    if index:
        df = df.reset_index()
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    body = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in rec) + " |"
            for rec in df.itertuples(index=False, name=None)]
    return "\n".join([head, sep, *body])


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    levels = load_window_b()
    rets = log_returns(levels)

    station = stationarity_table(levels, rets)
    order = integration_order(station)

    mats = {
        "levels_pearson": levels[ALL_COLS].corr(method="pearson"),
        "levels_spearman": levels[ALL_COLS].corr(method="spearman"),
        "returns_pearson": rets[ALL_COLS].corr(method="pearson"),
        "returns_spearman": rets[ALL_COLS].corr(method="spearman"),
    }

    corr_sum = correlation_summary(levels, rets)

    lag_frames = []
    for target in TARGETS:
        for x in EXOG:
            for basis, df in (("levels", levels), ("returns", rets)):
                p = lag_profile(df[x], df[target])
                p.insert(0, "basis", basis)
                p.insert(0, "exogenous", x)
                p.insert(0, "target", target)
                lag_frames.append(p)
    lag_all = pd.concat(lag_frames, ignore_index=True)
    lag_all = lag_all[["target", "exogenous", "basis", "lag", "n", "r",
                       "p_value", "ci_band", "significant_5pct"]].round(
        {"r": 4, "p_value": 4, "ci_band": 4})

    granger = granger_table(levels, rets, order)

    # ---------------- write tables ---------------- #
    station.round(4).to_csv(TABLES / "stationarity_results.csv", index=False)
    for key, mat in mats.items():
        mat.round(4).to_csv(TABLES / f"correlation_{key}.csv")
    corr_sum.to_csv(TABLES / "correlation_summary.csv", index=False)
    lag_all.to_csv(TABLES / "lag_ccf.csv", index=False)
    granger.to_csv(TABLES / "granger_results.csv", index=False)

    fig_series(levels)
    fig_heatmaps(mats)
    for target in TARGETS:
        fig_ccf(levels, rets, target)

    # ---------------- summary ---------------- #
    lines: list[str] = []
    add = lines.append
    add("# Statistical analysis - Window B (n=27)\n")
    add("Period 2024-08 .. 2026-10. All tests use alpha = 0.05.\n")

    add("## 1. Integration order\n")
    add(md_table(pd.DataFrame({
        "series": list(order),
        "I(d) suggested by ADF": [f"I({d})" for d in order.values()],
    }), index=False))
    add("")
    add("The ADF decision uses no augmentation (`adf_p_lag0`) because the sample "
        "is short (n=26 first differences); the lag-1 and AIC-selected variants "
        "are reported in the table for transparency and, as expected, lose power "
        "as extra lags consume degrees of freedom. KPSS is the complementary "
        "test.\n")
    add(md_table(station, index=False))
    add("")

    add("## 2. Level vs. returns correlation\n")
    add(md_table(corr_sum, index=False))
    add("")
    add("Level correlations are large and positive for every pair, which is the "
        "expected signature of two trending series. Removing the trend "
        "(log returns) reverses or destroys the relationship, so the level "
        "figures cannot be read as predictive association.")
    add(f"With 24 correlation tests in this table, the Bonferroni threshold is "
        f"alpha/24 = {ALPHA / 24:.4f}; only results below that survive.\n")

    add("## 3. Lag profile, exogenous leading the RAM price\n")
    for target in TARGETS:
        for basis in ("levels", "returns"):
            sub = lag_all[(lag_all["target"] == target)
                          & (lag_all["basis"] == basis)
                          & (lag_all["lag"] >= 0)]
            pivot = sub.pivot(index="lag", columns="exogenous", values="r")
            add(f"**{target}, {basis}** (k>0: exogenous leads)\n")
            add(md_table(pivot, index=True))
            add("")

    add("## 4. Granger causality (maxlag=3, stationary series)\n")
    add(md_table(granger, index=False))
    add("")
    add("Bonferroni-corrected threshold for this table is "
        f"{granger['bonferroni_alpha'].iloc[0]}.\n")

    (TABLES / "eda_summary.md").write_text("\n".join(lines), encoding="utf-8")

    # ---------------- console ---------------- #
    print("=== integration order ===")
    print(order)
    print("\n=== correlation, levels vs returns ===")
    print(corr_sum.to_string(index=False))
    print("\n=== lag profile (levels), exogenous -> target ===")
    for target in TARGETS:
        sub = lag_all[(lag_all["target"] == target) & (lag_all["basis"] == "levels")
                      & (lag_all["lag"] >= 0)]
        print(f"\n{target}")
        print(sub.pivot(index="lag", columns="exogenous", values="r").round(3).to_string())
    print("\n=== lag profile (returns) ===")
    for target in TARGETS:
        sub = lag_all[(lag_all["target"] == target) & (lag_all["basis"] == "returns")
                      & (lag_all["lag"] >= 0)]
        print(f"\n{target}")
        print(sub.pivot(index="lag", columns="exogenous", values="r").round(3).to_string())
    print("\n=== Granger (exogenous -> RAM) ===")
    print(granger[granger["direction"] == "exogenous -> RAM"]
          .pivot_table(index=["target", "exogenous"], columns="lag",
                       values="ssr_f_p").round(3).to_string())
    print(f"\nwrote tables to {TABLES.relative_to(ROOT)} and figures to "
          f"{FIGURES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
