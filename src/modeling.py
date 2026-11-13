"""modeling.py
=============
Phase 2: forecast DDR4 and DDR5 with the four-model ladder agreed in the plan.

    Naive  ->  ARIMA  ->  SARIMAX  ->  XGBoost

Everything is fitted on **log** prices and scored back on the USD/GB scale.

Evaluation regimes (all chronological, never shuffled)
-----------------------------------------------------
``holdout_1step``   one-step-ahead over the last 6 months, expanding window,
                    parameters re-estimated at every origin.
``holdout_h6``      one static 6-month forecast fitted on the first 21 months.
``cv_rolling``      expanding-window rolling origin over the whole sample
                    (14 one-step errors per model), used as the stable ranking.

Design rules
------------
* The specification (ARIMA order, trend, exog subset, XGBoost preset) is chosen
  on the training window only. It is then held fixed while parameters are
  re-estimated at each rolling origin, so no test information leaks.
* Two SARIMAX variants are reported: with contemporaneous exog (the textbook
  specification) and with exog lagged one month (no look-ahead: month ``t``'s
  stock return is not known when month ``t`` starts).
* For multi-step forecasts the future exogen is a random walk (last observed
  value carried forward). Using the realised future stock prices is reported as
  a separate, optimistic row so the size of that assumption is visible.

Outputs
-------
outputs/tables/model_metrics.csv
outputs/tables/model_selection.csv
outputs/tables/predictions.csv
outputs/tables/forecast_6m.csv
outputs/tables/model_summary.md
outputs/figures/fig04_actual_vs_predicted.png
outputs/figures/fig05_forecast_6m.png
"""

from __future__ import annotations

import itertools
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import metrics, md_table, FIG_DPI  # noqa: E402

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

TARGETS = ["DDR4", "DDR5"]
EXOG = ["SOXX", "MU", "NVDA"]
COLOURS = {"Naive": "#9e9e9e", "ARIMA": "#1f4e79",
           "ARIMA (no drift)": "#4c72b0", "SARIMAX": "#2e7d32",
           "SARIMAX (exog lag-1)": "#8d6e63", "XGBoost": "#c00000"}

TEST_MONTHS = 6
ORDERS = [(0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1),
          (2, 1, 0), (1, 1, 2), (2, 1, 1)]
# statsmodels is asymmetric here and it matters:
#   ARIMA(d=1)   rejects trend='c'; the drift is `trend='t'` (constant in the
#                differenced equation).
#   SARIMAX(d=1) treats `trend='t'` as a linear time trend *inside* the
#                differenced equation, i.e. a quadratic level path. That is
#                explosive and wrong for this purpose; the drift is `trend='c'`.
ARIMA_TRENDS = ["n", "t"]
SARIMAX_TRENDS = ["n", "c"]
XGB_PRESETS = [
    {"n_estimators": 200, "max_depth": 1, "learning_rate": 0.05},
    {"n_estimators": 100, "max_depth": 2, "learning_rate": 0.05},
    {"n_estimators": 300, "max_depth": 1, "learning_rate": 0.03},
]


@dataclass
class Spec:
    kind: str
    order: tuple[int, int, int] | None = None
    trend: str | None = None
    drift: bool = False
    exog: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    info: dict = field(default_factory=dict)
    label: str = ""


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def load_window_b() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "window_B_ai_shock_period_monthly.csv",
                       index_col=0, parse_dates=True)


def aligned(y_log: pd.Series, X_log: pd.DataFrame, lag_exog: int
            ) -> tuple[pd.Series, pd.DataFrame]:
    """Align target and (possibly lagged) exogen; drop only leading gaps."""
    X = X_log.shift(lag_exog) if lag_exog else X_log.copy()
    joined = pd.concat([y_log.rename("__y"), X], axis=1).dropna()
    return joined["__y"], joined.drop(columns="__y")


# --------------------------------------------------------------------------- #
# ARIMA / SARIMAX
# --------------------------------------------------------------------------- #
def _fit_arima(y: pd.Series, order, trend):
    return ARIMA(y, order=order, trend=trend).fit()


def _fit_sarimax(y: pd.Series, X: pd.DataFrame | None, order, trend):
    return SARIMAX(
        y, exog=X, order=order, trend=trend,
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False)


def select_arima(y: pd.Series, trends: list[str] | None = None,
                 label: str = "ARIMA") -> Spec:
    trends = trends or ARIMA_TRENDS
    best = None
    for order in ORDERS:
        for trend in trends:
            try:
                aic = _fit_arima(y, order, trend).aic
            except Exception:
                continue
            if np.isfinite(aic) and (best is None or aic < best[0]):
                best = (aic, order, trend)
    if best is None:
        raise RuntimeError("no ARIMA specification converged")
    aic, order, trend = best
    return Spec("arima", order=order, trend=trend, drift=(trend == "t"),
                label=label, info={"aic": round(float(aic), 2)})


def select_sarimax(y: pd.Series, X: pd.DataFrame, label: str,
                   trends: list[str] | None = None) -> Spec:
    trends = trends or SARIMAX_TRENDS
    best = None
    subsets = [list(c) for r in range(1, 4)
               for c in itertools.combinations(X.columns, r)]
    for cols in subsets:
        for order in ORDERS:
            for trend in trends:
                try:
                    aic = _fit_sarimax(y, X[cols], order, trend).aic
                except Exception:
                    continue
                if np.isfinite(aic) and (best is None or aic < best[0]):
                    best = (aic, order, trend, cols)
    if best is None:
        raise RuntimeError("no SARIMAX specification converged")
    aic, order, trend, cols = best
    return Spec("sarimax", order=order, trend=trend, drift=(trend == "c"),
                exog=cols, label=label,
                info={"aic": round(float(aic), 2), "exog": "+".join(cols)})


def arima_one(y: pd.Series, spec: Spec) -> float:
    res = _fit_arima(y, spec.order, spec.trend)
    return float(res.get_forecast(1).predicted_mean.iloc[0])


def sarimax_one(y: pd.Series, X: pd.DataFrame, x_next: pd.DataFrame,
                spec: Spec) -> float:
    res = _fit_sarimax(y, X[spec.exog], spec.order, spec.trend)
    return float(res.get_forecast(1, exog=x_next[spec.exog])
                 .predicted_mean.iloc[0])


def sarimax_forecast(y: pd.Series, X: pd.DataFrame, x_future: pd.DataFrame,
                     spec: Spec) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    res = _fit_sarimax(y, X[spec.exog], spec.order, spec.trend)
    fc = res.get_forecast(len(x_future), exog=x_future[spec.exog])
    ci = fc.conf_int(alpha=0.10)
    return (np.asarray(fc.predicted_mean), np.asarray(ci.iloc[:, 0]),
            np.asarray(ci.iloc[:, 1]))


def arima_forecast(y: pd.Series, h: int, spec: Spec
                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    res = _fit_arima(y, spec.order, spec.trend)
    fc = res.get_forecast(h)
    ci = fc.conf_int(alpha=0.10)
    return (np.asarray(fc.predicted_mean), np.asarray(ci.iloc[:, 0]),
            np.asarray(ci.iloc[:, 1]))


# --------------------------------------------------------------------------- #
# XGBoost
# --------------------------------------------------------------------------- #
def feature_names(exog_cols: list[str]) -> list[str]:
    names = [f"y_lag{k}" for k in (1, 2, 3)]
    for c in exog_cols:
        names += [f"{c}_lag{k}" for k in (0, 1, 2, 3)]
    return names


def design_matrix(y: pd.Series, X: pd.DataFrame, exog_cols: list[str]
                  ) -> tuple[pd.DataFrame, pd.Series]:
    X = X.reindex(y.index)
    cols = {f"y_lag{k}": y.shift(k) for k in (1, 2, 3)}
    for c in exog_cols:
        for k in (0, 1, 2, 3):
            cols[f"{c}_lag{k}"] = X[c].shift(k)
    df = pd.DataFrame(cols)
    df["__target"] = y
    df = df.dropna()
    return df.drop(columns="__target"), df["__target"]


def _xgb_model(params: dict) -> XGBRegressor:
    return XGBRegressor(random_state=0, n_jobs=1, subsample=0.9,
                        colsample_bytree=0.9, reg_lambda=1.0,
                        objective="reg:squarederror", **params)


def xgb_one(y: pd.Series, X: pd.DataFrame, spec: Spec) -> float:
    names = feature_names(spec.exog)
    Xmat, target = design_matrix(y, X, spec.exog)
    model = _xgb_model(spec.params).fit(Xmat[names], target)
    row = {f"y_lag{k}": y.iloc[-k] for k in (1, 2, 3)}
    for c in spec.exog:
        for k in (0, 1, 2, 3):
            row[f"{c}_lag{k}"] = X[c].iloc[-1 - k]
    return float(model.predict(pd.DataFrame([row])[names])[0])


def xgb_forecast(y: pd.Series, X: pd.DataFrame, h: int, spec: Spec
                 ) -> np.ndarray:
    """Recursive multi-step; the future exogen is carried forward."""
    names = feature_names(spec.exog)
    Xmat, target = design_matrix(y, X, spec.exog)
    model = _xgb_model(spec.params).fit(Xmat[names], target)

    yv = list(y.to_numpy())
    xv = {c: list(X[c].to_numpy()) for c in spec.exog}
    preds = []
    for _ in range(h):
        row = {f"y_lag{k}": yv[-k] for k in (1, 2, 3)}
        for c in spec.exog:
            for k in (0, 1, 2, 3):
                row[f"{c}_lag{k}"] = xv[c][-1 - k]
        p = float(model.predict(pd.DataFrame([row])[names])[0])
        preds.append(p)
        yv.append(p)
    return np.asarray(preds)


def xgb_forecast_interval(y: pd.Series, X: pd.DataFrame, h: int, spec: Spec,
                          n_boot: int = 400, seed: int = 0
                          ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Recursive forecast with a residual-bootstrap band.

    The point forecast is the deterministic recursive path. The band comes from
    re-simulating the path ``n_boot`` times, adding a residual drawn from the
    in-sample errors at each step, so it reflects how error compounds across the
    horizon rather than a one-step noise level.
    """
    names = feature_names(spec.exog)
    Xmat, target = design_matrix(y, X, spec.exog)
    model = _xgb_model(spec.params).fit(Xmat[names], target)
    resid = (target - model.predict(Xmat[names])).to_numpy()

    def path(yv: list[float], xv: dict[str, list[float]]) -> list[float]:
        out = []
        for _ in range(h):
            row = {f"y_lag{k}": yv[-k] for k in (1, 2, 3)}
            for c in spec.exog:
                for k in (0, 1, 2, 3):
                    row[f"{c}_lag{k}"] = xv[c][-1 - k]
            out.append(float(model.predict(pd.DataFrame([row])[names])[0]))
            yv = yv + [out[-1]]
        return out

    base_y = list(y.to_numpy())
    base_x = {c: list(X[c].to_numpy()) for c in spec.exog}
    point = np.asarray(path(base_y, base_x))

    rng = np.random.default_rng(seed)
    sims = []
    for _ in range(n_boot):
        yv, preds = list(base_y), []
        for _h in range(h):
            row = {f"y_lag{k}": yv[-k] for k in (1, 2, 3)}
            for c in spec.exog:
                for k in (0, 1, 2, 3):
                    row[f"{c}_lag{k}"] = base_x[c][-1 - k]
            p = float(model.predict(pd.DataFrame([row])[names])[0])
            preds.append(p)
            yv.append(p + float(rng.choice(resid)))
        sims.append(preds)
    sims = np.asarray(sims)
    return (point, np.percentile(sims, 5, axis=0),
            np.percentile(sims, 95, axis=0))


def select_xgb(y: pd.Series, X: pd.DataFrame, inner_start: int) -> Spec:
    """Choose exog set and tree preset on an inner holdout inside the train set."""
    best = None
    for exog_cols in ([], EXOG):
        for params in XGB_PRESETS:
            spec = Spec("xgb", exog=exog_cols, params=params, label="XGBoost")
            try:
                preds = [xgb_one(y.iloc[:t], X.iloc[:t + 1], spec)
                         for t in range(inner_start, len(y))]
            except Exception:
                continue
            score = float(np.mean(np.abs(np.exp(preds)
                                         - np.exp(y.iloc[inner_start:].to_numpy()))))
            if best is None or score < best[0]:
                best = (score, spec)
    if best is None:
        raise RuntimeError("no XGBoost preset could be fitted")
    score, spec = best
    spec.info = {"inner_holdout_mae": round(score, 4),
                 "exog": "+".join(spec.exog) or "none",
                 "preset": str(spec.params)}
    return spec


# --------------------------------------------------------------------------- #
# evaluation
# --------------------------------------------------------------------------- #
def one_step_predictions(spec: Spec, y: pd.Series, X: pd.DataFrame,
                         start: int, end: int) -> np.ndarray:
    preds = []
    for t in range(start, end):
        if spec.kind == "naive":
            preds.append(float(y.iloc[t - 1]))
        elif spec.kind == "arima":
            preds.append(arima_one(y.iloc[:t], spec))
        elif spec.kind == "sarimax":
            preds.append(sarimax_one(y.iloc[:t], X.iloc[:t],
                                     X.iloc[[t]], spec))
        elif spec.kind == "xgb":
            preds.append(xgb_one(y.iloc[:t], X.iloc[:t + 1], spec))
        else:
            raise ValueError(spec.kind)
    return np.asarray(preds)


def static_forecast(spec: Spec, y: pd.Series, X: pd.DataFrame, h: int,
                    x_future: pd.DataFrame) -> np.ndarray:
    if spec.kind == "naive":
        return np.repeat(float(y.iloc[-1]), h)
    if spec.kind == "arima":
        return arima_forecast(y, h, spec)[0]
    if spec.kind == "sarimax":
        return sarimax_forecast(y, X, x_future, spec)[0]
    if spec.kind == "xgb":
        return xgb_forecast(y, X, h, spec)
    raise ValueError(spec.kind)


def rw_future(X: pd.DataFrame, h: int) -> pd.DataFrame:
    last = X.iloc[[-1]]
    return pd.concat([last] * h, ignore_index=True).set_axis(
        pd.date_range(X.index[-1], periods=h + 1, freq="MS")[1:], axis=0)


def paired_bootstrap_p(err_a: np.ndarray, err_b: np.ndarray,
                       n_boot: int = 4000, seed: int = 0) -> float:
    """Two-sided bootstrap p-value for the difference in mean absolute error."""
    diff = np.asarray(err_a) - np.asarray(err_b)
    n = len(diff)
    rng = np.random.default_rng(seed)
    boots = diff[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    p = 2 * min((boots <= 0).mean(), (boots >= 0).mean())
    return float(min(max(p, 0.0), 1.0))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    df = load_window_b()
    y_log = np.log(df[TARGETS])
    X_log = np.log(df[EXOG])

    rows_metrics, rows_specs, rows_predictions = [], [], []
    rows_sig: list[dict] = []
    forecasts = {}

    for target in TARGETS:
        y = y_log[target]
        X = X_log.copy()

        # ---- specification selection on the training window only ------ #
        split = len(y) - TEST_MONTHS
        arima_main = select_arima(y.iloc[:split])
        specs = [Spec("naive", label="Naive"), arima_main]
        if arima_main.drift:
            specs.append(select_arima(y.iloc[:split], trends=["n"],
                                      label="ARIMA (no drift)"))
        specs += [select_sarimax(y.iloc[:split], X.iloc[:split], "SARIMAX"),
                  select_xgb(y.iloc[:split], X.iloc[:split],
                             inner_start=split - TEST_MONTHS)]

        y_lag, X_lag = aligned(y, X, lag_exog=1)
        split_lag = len(y_lag) - TEST_MONTHS
        specs.append(select_sarimax(y_lag.iloc[:split_lag],
                                    X_lag.iloc[:split_lag],
                                    "SARIMAX (exog lag-1)"))

        for spec in specs:
            rows_specs.append({
                "target": target, "model": spec.label,
                "order": str(spec.order) if spec.order else "-",
                "drift": "yes" if spec.drift else "no",
                "trend_code": spec.trend or "-",
                "exog": "+".join(spec.exog) or "-",
                "preset": str(spec.params) if spec.params else "-",
                "aic": spec.info.get("aic", "-"),
                "inner_mae": spec.info.get("inner_holdout_mae", "-"),
            })

        def series_for(spec: Spec):
            """Return the aligned (y, X, split) triple for this model."""
            if spec.label.endswith("lag-1)"):
                return y_lag, X_lag, split_lag
            return y, X, split

        # ---- regime A: holdout, one step ------------------------------ #
        for spec in specs:
            yy, XX, sp = series_for(spec)
            pred = np.exp(one_step_predictions(spec, yy, XX, sp, len(yy)))
            actual = np.exp(yy.iloc[sp:].to_numpy())
            m = metrics(actual, pred)
            rows_metrics.append({"target": target, "model": spec.label,
                                 "regime": "holdout_1step", "n": len(actual), **m})
            for month, a, p in zip(yy.index[sp:], actual, pred):
                rows_predictions.append({"target": target, "model": spec.label,
                                         "regime": "holdout_1step",
                                         "month": month, "actual": a, "pred": p})

        # ---- regime B: static 6-month forecast ------------------------ #
        for spec in specs:
            yy, XX, sp = series_for(spec)
            x_fut = rw_future(XX.iloc[:sp], TEST_MONTHS)
            pred = np.exp(static_forecast(spec, yy.iloc[:sp], XX.iloc[:sp],
                                          TEST_MONTHS, x_fut))
            actual = np.exp(yy.iloc[sp:sp + TEST_MONTHS].to_numpy())
            m = metrics(actual, pred)
            rows_metrics.append({"target": target, "model": spec.label,
                                 "regime": "holdout_h6", "n": len(actual), **m})

        # SARIMAX with realised future exogen: optimistic reference only
        sari = next(s for s in specs if s.label == "SARIMAX")
        pred_real = np.exp(static_forecast(
            sari, y.iloc[:split], X.iloc[:split], TEST_MONTHS,
            X.iloc[split:split + TEST_MONTHS]))
        actual_real = np.exp(y.iloc[split:split + TEST_MONTHS].to_numpy())
        rows_metrics.append({
            "target": target, "model": "SARIMAX (realised exog)",
            "regime": "holdout_h6", "n": len(actual_real),
            **metrics(actual_real, pred_real)})

        # ---- regime C: rolling-origin CV on the full sample ----------- #
        cv_start = 13
        cv_errors: dict[str, pd.Series] = {}
        for spec in specs:
            yy, XX, _ = series_for(spec)
            pred = np.exp(one_step_predictions(spec, yy, XX, cv_start, len(yy)))
            actual = np.exp(yy.iloc[cv_start:].to_numpy())
            cv_errors[spec.label] = pd.Series(np.abs(actual - pred),
                                              index=yy.index[cv_start:])
            rows_metrics.append({"target": target, "model": spec.label,
                                 "regime": "cv_rolling", "n": len(actual),
                                 **metrics(actual, pred)})

        # significance of the difference against the random walk
        base = cv_errors["Naive"]
        for model, err in cv_errors.items():
            if model == "Naive":
                continue
            common = err.index.intersection(base.index)
            ea, eb = err.loc[common].to_numpy(), base.loc[common].to_numpy()
            rows_sig.append({
                "target": target, "model": model,
                "mae_cv_vs_naive": round(float(ea.mean() - eb.mean()), 4),
                "bootstrap_p": round(paired_bootstrap_p(ea, eb), 4),
                "n": len(common),
            })

        # ---- 6-month forward forecast from the full sample ------------ #
        x_ahead = rw_future(X, 6)
        ahead_index = pd.date_range(df.index[-1], periods=7, freq="MS")[1:]
        arima_spec = next(s for s in specs if s.label == "ARIMA")
        nodrift_spec = next((s for s in specs
                             if s.label == "ARIMA (no drift)"), None)
        mean_l, lo_l, hi_l = arima_forecast(y, 6, arima_spec)
        mean_s, lo_s, hi_s = sarimax_forecast(y, X, x_ahead, sari)
        forecasts[target] = {
            "index": ahead_index,
            "ARIMA": (np.exp(mean_l), np.exp(lo_l), np.exp(hi_l)),
            "SARIMAX": (np.exp(mean_s), np.exp(lo_s), np.exp(hi_s)),
        }
        if nodrift_spec is not None:
            mean_n, lo_n, hi_n = arima_forecast(y, 6, nodrift_spec)
            forecasts[target]["ARIMA (no drift)"] = (
                np.exp(mean_n), np.exp(lo_n), np.exp(hi_n))
        xgb_spec = next(s for s in specs if s.label == "XGBoost")
        mean_x, lo_x, hi_x = xgb_forecast_interval(y, X, 6, xgb_spec)
        forecasts[target]["XGBoost"] = (
            np.exp(mean_x), np.exp(lo_x), np.exp(hi_x))

    # ---------------- write tables ---------------- #
    metrics_df = pd.DataFrame(rows_metrics)
    metrics_df[["rmse", "mae", "mape"]] = metrics_df[["rmse", "mae", "mape"]].round(4)
    metrics_df.to_csv(TABLES / "model_metrics.csv", index=False)

    specs_df = pd.DataFrame(rows_specs)
    specs_df.to_csv(TABLES / "model_selection.csv", index=False)

    preds_df = pd.DataFrame(rows_predictions)
    preds_df[["actual", "pred"]] = preds_df[["actual", "pred"]].round(5)
    preds_df.to_csv(TABLES / "predictions.csv", index=False)

    sig_df = pd.DataFrame(rows_sig)
    sig_df.to_csv(TABLES / "model_significance.csv", index=False)

    fc_rows = []
    for target, block in forecasts.items():
        for model in block:
            if model == "index":
                continue
            mean, lo, hi = block[model]
            for month, m_, l_, h_ in zip(block["index"], mean, lo, hi):
                fc_rows.append({"target": target, "model": model,
                                "month": month, "point": m_,
                                "low_90": l_, "high_90": h_})
    pd.DataFrame(fc_rows).round(5).to_csv(TABLES / "forecast_6m.csv", index=False)

    # ---------------- figures ---------------- #
    fig_actual_vs_pred(df, preds_df)
    fig_forecast(df, forecasts, y_log)
    write_summary(metrics_df, specs_df, forecasts, sig_df)

    # ---------------- console ---------------- #
    print("=== selected specifications ===")
    print(specs_df.to_string(index=False))
    print("\n=== metrics ===")
    print(metrics_df.pivot_table(index=["target", "model"],
                                 columns="regime",
                                 values=["rmse", "mape"]).round(3).to_string())
    print("\n=== 6-month forward forecast (USD/GB) ===")
    for target, block in forecasts.items():
        mean, lo, hi = block["SARIMAX"]
        print(f"{target}: " + ", ".join(
            f"{m_:%Y-%m}={v:.2f} [{l:.2f},{h:.2f}]"
            for m_, v, l, h in zip(block["index"], mean, lo, hi)))
    return 0


def fig_actual_vs_pred(df: pd.DataFrame, preds: pd.DataFrame) -> None:
    hold = preds[preds["regime"] == "holdout_1step"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, target in zip(axes, TARGETS):
        ax.plot(df.index, df[target], color="black", lw=2.0, label="actual",
                marker="o", ms=3)
        for model, g in hold[hold["target"] == target].groupby("model"):
            ax.plot(g["month"], g["pred"], lw=1.4, marker="s", ms=3.5,
                    color=COLOURS.get(model, "gray"), label=model)
        ax.axvline(df.index[-TEST_MONTHS - 1], color="grey", ls="--", lw=1)
        ax.set_title(f"{target}: one-step-ahead over the last {TEST_MONTHS} months",
                     fontsize=10, fontweight="bold")
        ax.set_ylabel("USD/GB", fontsize=9)
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=7, ncol=2)
    fig.suptitle("Out-of-sample one-step forecasts (dashed line = train/test boundary)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig04_actual_vs_predicted.png", dpi=FIG_DPI)
    plt.close(fig)


def fig_forecast(df: pd.DataFrame, forecasts: dict, y_log: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, target in zip(axes, TARGETS):
        hist = df[target].iloc[-18:]
        ax.plot(hist.index, hist, color="black", lw=2.0, marker="o", ms=3,
                label="observed")
        block = forecasts[target]
        for model in block:
            if model == "index":
                continue
            mean, lo, hi = block[model]
            colour = COLOURS.get(model, "grey")
            ax.plot(block["index"], mean, color=colour, lw=1.6, marker="s",
                    ms=3.5, label=f"{model} forecast")
            ax.fill_between(block["index"], lo, hi, color=colour, alpha=0.12)
        ax.set_title(f"{target}: 6-month ahead (90% interval)", fontsize=10,
                     fontweight="bold")
        ax.set_ylabel("USD/GB", fontsize=9)
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=7)
    fig.suptitle("Forward forecast from the full sample (Nov 2026 - Apr 2027)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig05_forecast_6m.png", dpi=FIG_DPI)
    plt.close(fig)


def write_summary(metrics_df: pd.DataFrame, specs_df: pd.DataFrame,
                  forecasts: dict, sig_df: pd.DataFrame) -> None:
    lines = ["# Modelling results - Window B (n=27, 21 train / 6 test)\n",
             "All models fitted on log prices; metrics on USD/GB.\n",
             "## 1. Selected specifications (chosen on the training window only)\n",
             md_table(specs_df, index=False), ""]

    lines.append("## 2. Accuracy\n")
    for regime, title in (("holdout_1step", "Out-of-sample, one-step (6 months)"),
                          ("holdout_h6", "Out-of-sample, static 6-month forecast"),
                          ("cv_rolling", "Rolling-origin CV, one-step (14 origins)")):
        sub = metrics_df[metrics_df["regime"] == regime].copy()
        if sub.empty:
            continue
        pivot = sub.pivot_table(index="model", columns="target",
                                values=["rmse", "mape"])
        pivot.columns = [f"{b}_{a}" for a, b in pivot.columns]
        lines.append(f"### {title}\n")
        lines.append(md_table(pivot.round(3), index=True))
        lines.append("")

    lines.append("## 3. Is any model better than the random walk?\n")
    lines.append("Paired bootstrap (4000 resamples) of the difference in mean "
                 "absolute error on the rolling-origin CV, one step ahead. "
                 "Positive means the model is worse than the random walk.\n")
    lines.append(md_table(sig_df, index=False))
    lines.append("")

    lines.append("## 4. Six-month forward forecast (USD/GB)\n")
    for target, block in forecasts.items():
        for model in block:
            if model == "index":
                continue
            mean, lo, hi = block[model]
            lines.append(f"**{target} - {model}**\n")
            lines.append(md_table(pd.DataFrame({
                "month": [f"{m:%Y-%m}" for m in block["index"]],
                "point": np.round(mean, 3),
                "low_90": np.round(lo, 3),
                "high_90": np.round(hi, 3),
            }), index=False))
            lines.append("")

    (TABLES / "model_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
