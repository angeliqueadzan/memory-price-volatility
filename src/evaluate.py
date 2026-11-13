"""evaluate.py
=============
Forecast accuracy metrics and split helpers shared by the modelling scripts.

All models are fitted on log prices; metrics are computed on the original
USD/GB scale so they are directly interpretable in the manuscript.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Print quality required by the target venues. Every figure is exported at this
# resolution so no second pass is needed before submission.
FIG_DPI = 300


def rmse(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def mae(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred)))


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


def metrics(actual: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return {"rmse": rmse(actual, pred), "mae": mae(actual, pred),
            "mape": mape(actual, pred)}


def chronological_split(index: pd.DatetimeIndex, test_months: int = 6
                        ) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    return index[:-test_months], index[-test_months:]


def expanding_folds(n: int, horizon: int = 1, n_folds: int = 3
                    ) -> list[tuple[int, int]]:
    """Expanding-window fold boundaries as ``(train_end, test_end)``."""
    folds = []
    for k in range(n_folds, 0, -1):
        test_end = n - (k - 1) * horizon
        train_end = test_end - horizon
        if train_end < 6:
            continue
        folds.append((train_end, test_end))
    return folds


def md_table(df: pd.DataFrame, index: bool = False) -> str:
    df = df.copy()
    if index:
        df = df.reset_index()
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    body = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in rec) + " |"
            for rec in df.itertuples(index=False, name=None)]
    return "\n".join([head, sep, *body])
