"""datasources.py
================
Single source of truth for *fetching* the raw inputs of the study.

Every number used in this project must be traceable to one of the two
endpoints below. Downloads are cached per calendar day in ``data/raw/``
together with a SHA-256 digest, which is what the manuscript cites as
"snapshot <date>, sha256 <digest>".

Sources
-------
Y (target)  Stanford DAM Memory Prices
            https://dam.stanford.edu/memory-prices.html
            CSV: https://dam.stanford.edu/assets/memory-prices/memory-prices.csv
            (McCallum historical series + Keepa/Amazon monthly listings since 2024-08)

X (exogenous)  Yahoo Finance monthly adjusted close, via the public chart endpoint
               https://query1.finance.yahoo.com/v8/finance/chart/{symbol}
               Symbols: SOXX (iShares Semiconductor ETF), MU (Micron), NVDA (NVIDIA)
"""

from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

STANFORD_URL = "https://dam.stanford.edu/assets/memory-prices/memory-prices.csv"
YAHOO_TMPL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={p1}&period2={p2}&interval=1mo&events=div,splits"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Analysis windows, fixed by the methodology (no cross-regime backfill).
WINDOW_B_START = "2024-08-01"   # first month with per-module DDR4/DDR5 listings
WINDOW_B_END = "2026-10-01"     # last complete month in the Stanford snapshot
MASTER_START = "2022-01-01"     # start of the long context series
MASTER_END = WINDOW_B_END
DRAM_GENERIC_END = "2024-07-01"  # last month of the generic DRAM series

STOCKS = ["SOXX", "MU", "NVDA"]


# --------------------------------------------------------------------------- #
# low-level fetching
# --------------------------------------------------------------------------- #
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _download(url: str, cache_name: str, refresh: bool = False,
              retries: int = 3) -> tuple[bytes, Path, str, bool]:
    """Fetch ``url``, caching the bytes to ``data/raw/<cache_name>``.

    Returns ``(bytes, path, sha256, used_cache)``. Reuses today's cached copy
    unless ``refresh`` is True.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / cache_name
    if path.exists() and not refresh:
        blob = path.read_bytes()
        return blob, path, _sha256(blob), True

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                blob = resp.read()
            if not blob:
                raise ValueError("empty response body")
            path.write_bytes(blob)
            return blob, path, _sha256(blob), False
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            last_err = err
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}: {last_err}")


# --------------------------------------------------------------------------- #
# Stanford DAM memory prices
# --------------------------------------------------------------------------- #
def stanford_raw(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    """Return the full Stanford table plus fetch metadata."""
    blob, path, sha, cached = _download(
        STANFORD_URL, f"stanford_memory-prices_{_today()}.csv", refresh=refresh
    )
    df = pd.read_csv(io.BytesIO(blob))
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    meta = {
        "url": STANFORD_URL,
        "path": str(path.relative_to(ROOT)),
        "sha256": sha,
        "bytes": len(blob),
        "rows": int(len(df)),
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "used_cache": cached,
        "last_date_in_source": df["date"].max().strftime("%Y-%m-%d"),
    }
    return df, meta


def stanford_monthly(df: pd.DataFrame, mapping: dict[str, str],
                     allow_duplicates: bool = False,
                     agg: str = "mean") -> pd.DataFrame:
    """Pivot ``series`` -> month-start index using ``mapping {source: column}``.

    The McCallum historical series contains several device generations in the
    same month, so it is averaged (``allow_duplicates=True``). The Keepa series
    must be one listing per month; duplicates there are treated as an error.
    """
    sub = df[df["series"].isin(mapping)].copy()
    if sub.empty:
        raise ValueError(f"none of the series {list(mapping)} found in source")

    sub["month"] = sub["date"].dt.to_period("M").dt.to_timestamp()
    sub["col"] = sub["series"].map(mapping)
    sub = sub.dropna(subset=["value"])

    dup = sub.duplicated(subset=["month", "col"], keep=False)
    if dup.any() and not allow_duplicates:
        bad = sub.loc[dup, ["month", "col", "value"]].head(20).to_string(index=False)
        raise ValueError(f"duplicate month/series rows in source:\n{bad}")
    if dup.any():
        print(f"      [info] averaging {int(dup.sum())} duplicate month/series rows "
              f"({sorted(sub.loc[dup, 'col'].unique())})")

    wide = sub.pivot_table(index="month", columns="col", values="value", aggfunc=agg)
    wide = wide.reindex(columns=list(mapping.values()))
    wide.columns.name = None
    wide.index.name = "month"
    return wide.sort_index()


# --------------------------------------------------------------------------- #
# Yahoo Finance monthly series
# --------------------------------------------------------------------------- #
def yahoo_monthly(symbol: str, start: str = "2021-11-01",
                  end: str | None = None, refresh: bool = False
                  ) -> tuple[pd.Series, dict]:
    """Monthly adjusted close for ``symbol``, indexed by month start."""
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int(pd.Timestamp(end or (_today() + " 00:00:00"),
                          tz="UTC").timestamp())
    url = YAHOO_TMPL.format(symbol=symbol, p1=p1, p2=p2)
    key = symbol.replace("/", "-")
    blob, path, sha, cached = _download(
        url, f"yahoo_{key}_1mo_{_today()}.json", refresh=refresh
    )

    payload = json.loads(blob)
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"yahoo error for {symbol}: {chart['error']}")
    result = chart["result"][0]
    stamps = result.get("timestamp") or []
    if not stamps:
        raise RuntimeError(f"no monthly bars returned for {symbol}")

    adj = result["indicators"].get("adjclose")
    closes = adj[0]["adjclose"] if adj else result["indicators"]["quote"][0]["close"]

    idx, vals = [], []
    for ts, val in zip(stamps, closes):
        if val is None:
            continue
        idx.append(pd.Timestamp(ts, unit="s", tz="UTC").tz_convert(None)
                   .to_period("M").to_timestamp())
        vals.append(float(val))

    serie = pd.Series(vals, index=pd.DatetimeIndex(idx, name="month"),
                      name=symbol, dtype="float64").sort_index()
    serie = serie[~serie.index.duplicated(keep="last")]

    # Drop the current, still-running month: Yahoo returns a partial bar.
    current = (pd.Timestamp.now(tz="UTC").tz_localize(None)
               .to_period("M").to_timestamp())
    dropped_partial = bool((serie.index == current).any())
    serie = serie[serie.index < current]

    meta = {
        "symbol": symbol,
        "url": url,
        "path": str(path.relative_to(ROOT)),
        "sha256": sha,
        "bytes": len(blob),
        "used_cache": cached,
        "first_month": serie.index.min().strftime("%Y-%m-%d"),
        "last_month": serie.index.max().strftime("%Y-%m-%d"),
        "dropped_partial_current_month": dropped_partial,
        "price_kind": "adjusted_close" if adj else "close",
    }
    return serie, meta
