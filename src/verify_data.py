"""verify_data.py
================
Provenance and integrity checks for every number that ends up in the paper.

What is checked
---------------
1. Snapshot identity: URL, fetch date and SHA-256 of each raw source, so the
   results are reproducible against an immutable copy.
2. Cell-level equality: every DDR4/DDR5/NAND value in Window B is re-derived
   from the Stanford CSV and must match; every SOXX/MU/NVDA value is re-derived
   from Yahoo Finance and must match within rounding tolerance.
3. Structural integrity: monthly continuity, absent values, zero/negative
   prices, duplicated consecutive observations.
4. Extreme points: the largest month-on-month moves, which the manuscript
   explicitly flags (MU in May/June 2026) and which reviewers usually question.

Output: ``outputs/tables/verification_report.md`` (+ console summary).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datasources import (  # noqa: E402
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
TABLES = ROOT / "outputs" / "tables"

RAM_SERIES = {
    "DDR4 (Keepa)": "DDR4",
    "DDR5 (Keepa)": "DDR5",
    "NAND cheapest (Keepa)": "NAND",
}

TOL_RAM = 5e-5      # values are stored with 5 decimals
TOL_STOCK = 0.005   # values are stored with 2 decimals


def load_processed() -> dict[str, pd.DataFrame]:
    out = {}
    for name in [
        "window_B_ai_shock_period_monthly",
        "master_raw_monthly",
        "master_interpolated_monthly",
        "window_B_scaled_monthly",
    ]:
        path = PROCESSED / f"{name}.csv"
        out[name] = pd.read_csv(path, index_col=0, parse_dates=True)
    return out


def compare(name: str, ours: pd.Series, ref: pd.Series, tol: float) -> dict:
    ref = ref.reindex(ours.index)
    missing_ref = ref.isna()
    diff = (ours - ref).abs()
    bad = diff[(diff > tol) | diff.isna()].dropna()
    return {
        "series": name,
        "n": int(len(ours)),
        "matched": int((diff <= tol).sum()),
        "max_abs_diff": float(diff.max()) if diff.notna().any() else float("nan"),
        "tolerance": tol,
        "missing_in_source": int(missing_ref.sum()),
        "n_out_of_tolerance": int(len(bad)),
        "worst": bad.sort_values(ascending=False).head(5).round(6).to_dict(),
    }


def basket_summary(stanford: pd.DataFrame) -> pd.DataFrame:
    """Per-series coverage of the Amazon listing basket used by Stanford."""
    sub = stanford[stanford["series"].isin(RAM_SERIES)].copy()
    sub["month"] = sub["date"].dt.to_period("M").dt.to_timestamp()
    sub = sub.loc[sub["month"].between(pd.Timestamp(WINDOW_B_START),
                                       pd.Timestamp(WINDOW_B_END))]
    sub["col"] = sub["series"].map(RAM_SERIES)
    sub["n_samples"] = pd.to_numeric(sub["n_samples"], errors="coerce")

    rows = []
    for col in ["DDR4", "DDR5", "NAND"]:
        s = sub[sub["col"] == col].set_index("month")["n_samples"].sort_index()
        thin = [f"{m:%Y-%m} (n={int(v)})" for m, v in s.items() if v < 15]
        rows.append({
            "series": col,
            "months": int(s.notna().sum()),
            "min_n": int(s.min()),
            "median_n": int(s.median()),
            "max_n": int(s.max()),
            "months_with_n_lt_15": len(thin),
            "which": ", ".join(thin) if thin else "-",
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, index: bool = False) -> str:
    """Minimal markdown table writer (avoids a tabulate dependency)."""
    df = df.copy()
    if index:
        df = df.reset_index()
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    rows = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in rec) + " |"
            for rec in df.itertuples(index=False, name=None)]
    return "\n".join([head, sep, *rows])


def extremes(df: pd.DataFrame, col: str, k: int = 3) -> pd.DataFrame:
    r = df[col].pct_change() * 100
    order = r.abs().sort_values(ascending=False).head(k).index
    out = pd.DataFrame({
        "month": [f"{i:%Y-%m}" for i in order],
        "value": df.loc[order, col].round(4).to_numpy(),
        "mom_pct": r.loc[order].round(1).to_numpy(),
    })
    return out.reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-download sources instead of using today's snapshot")
    args = ap.parse_args()

    TABLES.mkdir(parents=True, exist_ok=True)
    ds = load_processed()
    win_b = ds["window_B_ai_shock_period_monthly"]

    stanford, stanford_meta = stanford_raw(refresh=args.refresh)
    ram_ref = stanford_monthly(stanford, RAM_SERIES)
    stock_ref = {s: yahoo_monthly(s, refresh=args.refresh) for s in STOCKS}

    # ---------------- 2. cell-level equality ---------------- #
    ram_checks = [compare(c, win_b[c], ram_ref[c], TOL_RAM) for c in
                  ["DDR4", "DDR5", "NAND"]]
    stock_checks = [compare(c, win_b[c], stock_ref[c][0], TOL_STOCK) for c in STOCKS]
    checks = pd.DataFrame(ram_checks + stock_checks)

    # ---------------- 3. structural integrity ---------------- #
    expected_idx = pd.date_range(pd.Timestamp(WINDOW_B_START),
                                 pd.Timestamp(WINDOW_B_END), freq="MS")
    structural = {
        "n_months": int(len(win_b)),
        "index_is_continuous": bool(win_b.index.equals(expected_idx)),
        "n_missing_cells": int(win_b.isna().sum().sum()),
        "n_nonpositive_prices": int((win_b <= 0).sum().sum()),
        "duplicated_consecutive": {
            c: [f"{d:%Y-%m}" for d in win_b.index[1:][
                win_b[c].to_numpy()[1:] == win_b[c].to_numpy()[:-1]]]
            for c in win_b.columns
        },
    }

    # ---------------- 5. context series integrity ---------------- #
    master = ds["master_interpolated_monthly"]
    master_idx = pd.date_range(pd.Timestamp(MASTER_START),
                               pd.Timestamp(MASTER_END), freq="MS")
    generic_valid_until = master["DRAM_generic"].last_valid_index()
    regime_ok = bool(master.loc[pd.Timestamp("2024-08-01"):, "DRAM_generic"].isna().all())
    regime_row = {
        "n_months": int(len(master)),
        "index_is_continuous": bool(master.index.equals(master_idx)),
        "dram_generic_last_valid": f"{generic_valid_until:%Y-%m}",
        "dram_generic_empty_after_2024_07": regime_ok,
        "n_missing_in_master": master.isna().sum().to_dict(),
    }

    manifest = json.loads((PROCESSED / "fetch_manifest.json").read_text(encoding="utf-8"))

    # ---------------- report ---------------- #
    all_ok = bool((checks["n_out_of_tolerance"] == 0).all()
                  and checks["missing_in_source"].sum() == 0
                  and structural["index_is_continuous"]
                  and structural["n_missing_cells"] == 0
                  and structural["n_nonpositive_prices"] == 0
                  and regime_ok)

    lines: list[str] = []
    add = lines.append
    add("# Data verification report\n")
    add(f"Generated: {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC\n")
    add("## 1. Snapshot identity\n")
    add("| source | file | bytes | SHA-256 |")
    add("|---|---|---|---|")
    add(f"| Stanford DAM memory prices | `{stanford_meta['path']}` | "
        f"{stanford_meta['bytes']:,} | `{stanford_meta['sha256']}` |")
    for sym in STOCKS:
        m = stock_ref[sym][1]
        add(f"| Yahoo Finance {sym} (monthly adj. close) | `{m['path']}` | "
            f"{m['bytes']:,} | `{m['sha256']}` |")
    add("")
    add(f"Source URLs: `{stanford_meta['url']}`; "
        f"`https://query1.finance.yahoo.com/v8/finance/chart/<symbol>`\n")

    add("## 2. Cell-level equality against the primary sources\n")
    add("| series | n | exact match | max abs diff | tolerance | out of tolerance |")
    add("|---|---|---|---|---|---|")
    for _, r in checks.iterrows():
        add(f"| {r['series']} | {r['n']} | {r['matched']} | {r['max_abs_diff']:.2e} | "
            f"{r['tolerance']:.0e} | {r['n_out_of_tolerance']} |")
    add("")
    add(f"**Verdict: {'PASS' if (checks['n_out_of_tolerance'] == 0).all() else 'FAIL'}** - "
        "every Window B value is reproduced from its primary source.\n")

    add("## 3. Structural integrity (Window B)\n")
    add(f"- months: **{structural['n_months']}** "
        f"({win_b.index[0]:%Y-%m} .. {win_b.index[-1]:%Y-%m})")
    add(f"- continuous monthly index: **{structural['index_is_continuous']}**")
    add(f"- missing cells: **{structural['n_missing_cells']}**")
    add(f"- non-positive prices: **{structural['n_nonpositive_prices']}**")
    dup_txt = ", ".join(f"{c}: {v or '-'}" for c, v in
                        structural["duplicated_consecutive"].items())
    add(f"- repeated consecutive observations (real, from source): {dup_txt}\n")

    add("## 4. Regime-change handling (context series)\n")
    add(f"- master series: **{regime_row['n_months']}** months "
        f"({MASTER_START[:7]} .. {MASTER_END[:7]}), continuous: "
        f"**{regime_row['index_is_continuous']}**")
    add(f"- `DRAM_generic` last valid month: **{regime_row['dram_generic_last_valid']}**")
    add(f"- `DRAM_generic` empty after 2024-07 (no cross-regime backfill): "
        f"**{regime_row['dram_generic_empty_after_2024_07']}**\n")

    add("## 5. Basket size behind each RAM observation\n")
    add("Stanford reports the number of Amazon listings used for the monthly "
        "'cheapest listing'. A small basket means a noisier estimate; months "
        "with fewer than 15 listings are flagged because they drive part of the "
        "month-on-month volatility.\n")
    add(md_table(basket_summary(stanford), index=False))
    add("")

    add("## 6. Largest month-on-month moves (Window B)\n")
    for col in ["DDR4", "DDR5", "SOXX", "MU", "NVDA"]:
        add(f"**{col}**\n")
        add(md_table(extremes(win_b, col), index=False))
        add("")

    add("## 7. Descriptive statistics (Window B)\n")
    add(md_table(win_b.describe().round(4), index=True))
    add("")

    report_path = TABLES / "verification_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[:40]))
    print(f"\n... full report: {report_path.relative_to(ROOT)}")
    print(f"\nALL CHECKS {'PASSED' if all_ok else 'FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
