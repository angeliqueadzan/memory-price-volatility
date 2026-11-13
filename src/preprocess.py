"""preprocess.py
===============
Rebuild every analysis dataset from the two primary sources.

Run from the repository root::

    conda run -n ram-env python src/preprocess.py            # use today's cache
    conda run -n ram-env python src/preprocess.py --refresh  # force re-download

Outputs (``data/processed/``)
-----------------------------
window_B_ai_shock_period_monthly.csv   main modelling dataset, 2024-08..2026-10 (n=27)
master_raw_monthly.csv                 long context series, 2022-01..2026-10, raw
master_interpolated_monthly.csv        same, linear interpolation of internal gaps only
window_B_scaled_monthly.csv            MinMax 0-1 of Window B (visualisation only)
fetch_manifest.json                    snapshot dates + SHA-256 of every source

Design rules
------------
* No cross-regime backfill: ``DRAM_generic`` ends in 2024-07 and stays empty
  afterwards; DDR4/DDR5 start in 2024-08. The split is a source-regime change,
  not a missing value.
* Window B is the only dataset used for correlation, Granger and modelling.
* Interpolation is ``limit_area="inside"`` per column, i.e. it can only fill a
  hole that is bracketed by two real observations of the *same* series.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datasources import (  # noqa: E402
    DRAM_GENERIC_END,
    MASTER_END,
    MASTER_START,
    STOCKS,
    WINDOW_B_END,
    WINDOW_B_START,
    stanford_monthly,
    stanford_raw,
    yahoo_monthly,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

RAM_SERIES = {
    "DDR4 (Keepa)": "DDR4",
    "DDR5 (Keepa)": "DDR5",
    "NAND cheapest (Keepa)": "NAND",
}
GENERIC_SERIES = {"McCallum DRAM (historical)": "DRAM_generic"}

WINDOW_B_COLS = ["DDR4", "DDR5", "NAND", "SOXX", "MU", "NVDA"]
MASTER_COLS = ["DRAM_generic", "DDR4", "DDR5", "NAND", "MU", "NVDA", "SOXX"]


def month_index(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="MS")


def fetch_stocks(refresh: bool) -> tuple[pd.DataFrame, dict]:
    frames, metas = [], {}
    for symbol in STOCKS:
        serie, meta = yahoo_monthly(symbol, start="2021-11-01", refresh=refresh)
        frames.append(serie)
        metas[symbol] = meta
    return pd.concat(frames, axis=1), metas


def build_window_b(stanford: pd.DataFrame, stocks: pd.DataFrame) -> pd.DataFrame:
    ram = stanford_monthly(stanford, RAM_SERIES)
    ram = ram.reindex(month_index(WINDOW_B_START, WINDOW_B_END))
    wide = ram.join(stocks.reindex(ram.index), how="left")[WINDOW_B_COLS]

    missing = wide.isna()
    if missing.any().any():
        detail = wide[missing.any(axis=1)].to_string()
        raise ValueError(
            "Window B contains missing cells; refusing to interpolate across "
            f"the modelling window:\n{detail}"
        )
    return wide


def build_master(stanford: pd.DataFrame,
                 stocks: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    generic = stanford_monthly(stanford, GENERIC_SERIES,
                               allow_duplicates=True, agg="mean")
    generic = generic.loc[:DRAM_GENERIC_END]

    ram = stanford_monthly(stanford, RAM_SERIES)
    ram = ram.loc[MASTER_START:MASTER_END]

    idx = month_index(MASTER_START, MASTER_END)
    raw = (generic.reindex(idx)
           .join(ram.reindex(idx), how="left")
           .join(stocks.reindex(idx), how="left"))[MASTER_COLS]

    interpolated = pd.DataFrame(
        {col: _interpolate_inside(raw[col]) for col in raw.columns}, index=idx
    )

    after_regime = interpolated.loc[
        pd.Timestamp(DRAM_GENERIC_END) + pd.offsets.MonthBegin(1):, "DRAM_generic"
    ]
    assert after_regime.isna().all(), \
        "DRAM_generic must not be carried past the regime change"
    return raw, interpolated


def _interpolate_inside(serie: pd.Series) -> pd.Series:
    """Linear interpolation restricted to a series' own valid span."""
    first, last = serie.first_valid_index(), serie.last_valid_index()
    if first is None or last is None:
        return serie
    span = serie.loc[first:last]
    filled = span.interpolate(method="linear", limit_area="inside")
    out = serie.copy()
    out.loc[first:last] = filled
    return out


def write_csv(df: pd.DataFrame, path: Path, decimals: dict[str, int]) -> str:
    out = df.copy()
    for col, d in decimals.items():
        if col in out.columns:
            out[col] = out[col].round(d)
    out.to_csv(path, index_label="month", date_format="%Y-%m-%d")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="ignore today's cache and re-download the sources")
    args = ap.parse_args()

    PROCESSED.mkdir(parents=True, exist_ok=True)

    print("[1/4] Stanford DAM memory prices ...")
    stanford, stanford_meta = stanford_raw(refresh=args.refresh)
    print(f"      rows={stanford_meta['rows']}  last={stanford_meta['last_date_in_source']}"
          f"  cache={stanford_meta['used_cache']}")

    print("[2/4] Yahoo Finance monthly adjusted close ...")
    stocks, stock_meta = fetch_stocks(refresh=args.refresh)
    for sym, meta in stock_meta.items():
        print(f"      {sym:5s} {meta['first_month']} .. {meta['last_month']}"
              f"  cache={meta['used_cache']}")

    print("[3/4] Building datasets ...")
    window_b = build_window_b(stanford, stocks)
    master_raw, master_interp = build_master(stanford, stocks)
    scaled = (window_b - window_b.min()) / (window_b.max() - window_b.min())

    ram_decimals = {"DDR4": 5, "DDR5": 5, "NAND": 5, "DRAM_generic": 5}
    stock_decimals = {s: 2 for s in STOCKS}
    decimals = {**ram_decimals, **stock_decimals}

    digests = {
        "window_B_ai_shock_period_monthly.csv": write_csv(
            window_b, PROCESSED / "window_B_ai_shock_period_monthly.csv", decimals),
        "master_raw_monthly.csv": write_csv(
            master_raw, PROCESSED / "master_raw_monthly.csv", decimals),
        "master_interpolated_monthly.csv": write_csv(
            master_interp, PROCESSED / "master_interpolated_monthly.csv", decimals),
        "window_B_scaled_monthly.csv": write_csv(
            scaled, PROCESSED / "window_B_scaled_monthly.csv",
            {c: 6 for c in WINDOW_B_COLS}),
    }

    print("[4/4] Writing manifest ...")
    manifest = {
        "generated_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "windows": {
            "window_B": {"start": WINDOW_B_START, "end": WINDOW_B_END,
                         "n_months": int(len(window_b))},
            "master": {"start": MASTER_START, "end": MASTER_END,
                       "n_months": int(len(master_interp))},
            "dram_generic_last_month": DRAM_GENERIC_END,
        },
        "sources": {"stanford_dam": stanford_meta, "yahoo": stock_meta},
        "outputs": digests,
        "notes": [
            "DDR4/DDR5/NAND come from the Keepa basket (cheapest listing per month, USD/GB).",
            "SOXX/MU/NVDA are monthly adjusted closes in USD (Yahoo Finance).",
            "window_B_scaled_monthly.csv is MinMax over the whole window and is for "
            "visualisation only; modelling must fit any scaler on the training split.",
        ],
    }
    (PROCESSED / "fetch_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nWindow B" + f"  n={len(window_b)}  {window_b.index[0]:%Y-%m} .. {window_b.index[-1]:%Y-%m}")
    print(window_b.round(4).to_string())
    print("\nMaster: "
          f"n={len(master_interp)}  DRAM_generic valid until "
          f"{master_interp['DRAM_generic'].last_valid_index():%Y-%m}")
    print(f"NaN counts (interpolated master): "
          f"{master_interp.isna().sum().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
