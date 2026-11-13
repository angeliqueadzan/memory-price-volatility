# Dataset provenance and licensing

Every number in this repository comes from one of the two sources below. No
synthetic, imputed or hand-entered price series is used: the raw responses are
stored byte-for-byte in `data/raw/` and their digests are checked by
`src/verify_data.py` before any result is reported.

Snapshot date: **2026-11-12**.

## 1. Memory prices (target variables)

| Field | Value |
|---|---|
| Source | Stanford Digital Archive of Market Prices (DAM), *Memory Prices* |
| Page | <https://dam.stanford.edu/memory-prices.html> |
| Download | <https://dam.stanford.edu/assets/memory-prices/memory-prices.csv> |
| Local file | `data/raw/stanford_memory-prices_2026-11-12.csv` |
| Fetched | 2026-11-12T13:49:44Z |
| Size / rows | 207,221 bytes / 984 rows |
| SHA-256 | `dcb1aa5e1adbfd6e238b6960ceaab8489c95a9a16ff5a0bd15e8ba9242c52682` |
| Last date in source | 2026-10-01 |
| Series used | `DDR4 (Keepa)`, `DDR5 (Keepa)`, `NAND cheapest (Keepa)`, `DRAM cheapest (Keepa)`, `McCallum DRAM (historical)` |

The archive publishes one long DRAM history (McCallum's compilation) continued
after mid-2024 with Keepa/Amazon retail listings. Measured price is the
**cheapest listed retail price per gigabyte in nominal USD** - not a contract
price, not an average, not a confirmed sale.

Series availability is 27 monthly observations (2024-08 to 2026-10) for the
per-generation Keepa series; the McCallum history starts in 1957 and stops at
2024-07, where the measurement regime changes. The two regimes are never
spliced: see section 3 of `README.md`.

## 2. Equity prices (exogenous variables)

| Symbol | Download | Local file | Bytes | SHA-256 |
|---|---|---|---|---|
| `SOXX` | Yahoo Finance chart API, `interval=1mo` | `data/raw/yahoo_SOXX_1mo_2026-11-12.json` | 9,408 | `33ea4fbb400b2a34818e9191d28c088dff648cb88183a528df3385a9a603f3f6` |
| `MU` | idem | `data/raw/yahoo_MU_1mo_2026-11-12.json` | 8,741 | `8a718e31296f4147e5406395efe817761f697f8a3879f323e63513cddc818bd7` |
| `NVDA` | idem | `data/raw/yahoo_NVDA_1mo_2026-11-12.json` | 9,262 | `e7ce3296cf883b14be0788e585800be5e7233ab8400a0d6fb36ace6aa5381884` |

Endpoint template: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1=1635724800&period2=1794441600&interval=1mo&events=div,splits`

Value taken is the monthly **adjusted close** in USD, first month 2021-11, last
month 2026-10. The partial current month is dropped by the pipeline, so the last
observation is always a completed month.

`SOXX` is a first-generation timestamp in the response (`firstTradeDate`
2001-07-13); its adjusted close is retroactively rescaled by each distribution
and split, which is why the raw response is pinned by digest rather than
re-fetched silently.

## 3. Licensing status

| Source | Status | Consequence for this repository |
|---|---|---|
| Stanford DAM CSV | Publicly downloadable, **no explicit licence statement**; the page asks users to check before citing | Fine to cite and to publish derived aggregates; keep the raw snapshot out of any public repository until Stanford confirms terms |
| Keepa (behind the DDR4/DDR5/NAND series) | Commercial price-history API; terms prohibit redistribution of the data | The DDR4/DDR5 values are Keepa-derived; do not publish the raw or near-raw series |
| McCallum historical series | Long-standing public academic dataset (jcmit.net, mirrored by DAM); no formal licence | Safe to cite with attribution |
| Yahoo Finance | Terms prohibit redistribution or redisplay of the data | Do not publish the raw JSON responses |

Practical rule already applied here: `data/processed/` (27 monthly observations
per series, aggregated) is tracked; `data/raw/` holds the vendor responses and
must not be published while the repository is public.

## 4. Citation

Use these entries for the two dataset references. They replace the shorter
forms currently in the manuscript bibliography, which lack a URL and an access
date.

```bibtex
@misc{mccallum,
  author       = {McCallum, John C.},
  title        = {Memory Prices},
  howpublished = {Stanford Digital Archive of Market Prices, Stanford University},
  note         = {Historical compilation continued with Keepa/Amazon monthly
                  cheapest-listing data. [Dataset]},
  url          = {https://dam.stanford.edu/memory-prices.html},
  urldate      = {2026-11-12}
}
```

IEEE style, as required by the manuscript:

```
G. C. F. McCallum, Memory Prices, Stanford Digital Archive of Market Prices.
Stanford University. [Online]. Available:
https://dam.stanford.edu/memory-prices.html. Accessed: Nov. 12, 2026. [Dataset]

Yahoo Finance. [Online]. Available: https://finance.yahoo.com.
Accessed: Nov. 12, 2026. [Dataset]
```

## 5. Known caveats to state in the paper

- The measured price is the cheapest listed retail price, so it reflects
  consumer listings rather than contract or spot-market transactions.
- The Amazon basket behind each observation is not constant: DDR4 draws on only
  8-12 listings between Dec 2024 and May 2025 against a median of 55, so the
  +81% jump in Sep 2024 is partly basket noise. DDR5 (minimum 17 listings) and
  NAND (minimum 93) are far more stable.
- Adjusted closes are revised retroactively on dividends and splits; any
  re-fetch must be diffed against the digest above before results are compared.

## 6. Re-fetching

```bash
python src/preprocess.py --refresh   # re-downloads both sources into data/raw/
python src/verify_data.py            # must print ALL CHECKS PASSED
```

`data/processed/fetch_manifest.json` records the URL, byte size, digest and
date for every raw file, so a later fetch can be compared against this snapshot.
