# Each fetch returns exactly what the source gave us. Reshaping is done in cleaning.py.

from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

from config import (
    BENCHMARK,
    INDEX_URL,
    MAX_WORKERS,
    RAW_DIR,
    RENAMES,
    SHARES_LOOKBACK_DAYS,
    START,
)

# Read the parquet if we already have it, otherwise fetch, save, and return
def cached(path, fetch, refresh=False):
    if path.exists() and not refresh:
        print(f"  load  {path.name}")
        return pd.read_parquet(path)

    print(f"  fetch {path.name}")
    df = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df

# yfinance returns tz-aware timestamps, our price calendar is reset to tz-naive at midnight
def to_naive_days(index):
    if index.tz is not None:
        index = index.tz_localize(None)

    return index.normalize()

# Scrape the current constituent list from Wikipedia
def fetch_constituents():
    response = requests.get(INDEX_URL, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    # pandas >= 3.0 no longer accepts a raw HTML string, only a file-like object
    table = pd.read_html(StringIO(response.text))[0]

    stocks = table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    stocks["Ticker"] = stocks["Symbol"].str.replace(".", "-", regex=False)  # Yahoo writes BRK.B as BRK-B
    return stocks


# Daily OHLCV for every ticker, columns are a (ticker, field) MultiIndex
def fetch_prices(tickers, start=START):
    return yf.download(
        tickers,
        start=start,
        end=None,               # Until present
        auto_adjust=False,      # S&P is a price-return index, so we want raw closes
        group_by="ticker",
        threads=True,
    )


# The published index level we compare our reconstruction against
def fetch_benchmark(start=START):
    h = yf.Ticker(BENCHMARK).history(start=start, end=None, auto_adjust=False)[["Close"]]
    h.index = to_naive_days(h.index)
    return h


# Shares implied by the quarterly valuation table, used to patch gaps in filing data
def implied_shares(ticker):
    t = yf.Ticker(ticker)
    try:
        caps = t.get_valuation_measures().loc["Market Cap"]
    except Exception:
        return None

    caps = caps.drop("Current", errors="ignore")    # Undated, can't place it on the calendar
    caps.index = pd.to_datetime(caps.index)
    caps = caps.dropna().sort_index()
    if caps.empty:
        return None

    # Quarter-ends usually predate our price window, so pull this ticker's own history
    try:
        px = t.history(start=caps.index.min(), end=None, auto_adjust=False)["Close"]
    except Exception:
        return None
    
    if px.empty:
        return None

    px.index = to_naive_days(px.index)
    px = px.reindex(px.index.union(caps.index)).ffill().reindex(caps.index)  # Close on/before each quarter-end
    return (caps / px).dropna()                     # Market cap / price = shares


# One ticker's filed share counts, cleaned but still only on filing dates
def _filed_shares(ticker, start):
    try:
        s = yf.Ticker(ticker).get_shares_full(start=start, end=None)
    except Exception:
        return None
    
    if s is None or len(s) == 0:
        return None                                 # No filings in the window

    s.index = to_naive_days(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()  # One row per date, latest wins


# Shares outstanding for every ticker, sparse: one row per filing date
def fetch_shares(tickers, window_start):
    # get_shares_full only returns points on filing dates, so start early enough
    # that every ticker has at least one observation before the price history begins
    start = (window_start - pd.Timedelta(days=SHARES_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    # Renamed tickers file only from the rename date, so fetch the old symbol as well
    old_symbols = [old for new, old in RENAMES.items() if new in tickers]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        series = dict(ex.map(lambda t: (t, _filed_shares(t, start)), list(tickers) + old_symbols))

    for new, old in RENAMES.items():
        current, previous = series.get(new), series.pop(old, None)
        if previous is None:
            continue
        # Filings under the current symbol win, the old one only covers earlier dates
        series[new] = previous if current is None else current.combine_first(previous)

    # A ticker is short if it has no filings at all, or none before our window opens
    gaps = [t for t, s in series.items() if s is None or s.index.min() > window_start]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        derived = dict(ex.map(lambda t: (t, implied_shares(t)), gaps)) # Calculate implied shares for missing ones

    for ticker, extra in derived.items():
        if extra is None:
            continue
        
        filed = series.get(ticker)
        # Real filings win, derived values only fill where filings are absent
        series[ticker] = extra if filed is None else filed.combine_first(extra)

    return pd.DataFrame({t: s for t, s in series.items() if s is not None})


# Fetch or load every raw input, and write each to data/raw
def load_raw(refresh=False):
    stocks = cached(RAW_DIR / "constituents.parquet", fetch_constituents, refresh)
    tickers = stocks["Ticker"].tolist()

    prices = cached(RAW_DIR / "prices.parquet", lambda: fetch_prices(tickers), refresh)
    window_start = prices.index.min()

    shares = cached(RAW_DIR / "shares.parquet", lambda: fetch_shares(tickers, window_start), refresh)
    benchmark = cached(RAW_DIR / "benchmark.parquet", fetch_benchmark, refresh)

    return stocks, prices, shares, benchmark
