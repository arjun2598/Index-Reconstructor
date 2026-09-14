from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

INDEX_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
START = "2026-08-01"
SHARES_LOOKBACK_DAYS = 400 # Filings are usually quarterly, so we look back far enough to catch one before START

# Scrapes current constituent stocks from Wikipedia
def fetch_constituents():
    response = requests.get(INDEX_URL, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    # pandas >= 3.0 no longer accepts a raw HTML string, only a file-like object
    table = pd.read_html(StringIO(response.text))[0] # Read latest stock table

    stocks = table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    # Yahoo uses "BRK-B" while Wikipedia uses "BRK.B".
    stocks["Ticker"] = stocks["Symbol"].str.replace(".", "-", regex=False)
    return stocks

# Download stock data from yfinance
def fetch_prices(tickers, start=START):
    return yf.download(
        tickers,
        start=start,
        end=None,               # Until present
        auto_adjust=False,      # adjusts OHLC for splits/dividends - False since S&P doesn't include dividends
        group_by="ticker",     
        threads=True,
    )


# Derive shares from the quarterly valuation table, used to patch gaps in filing outstanding shares data
def implied_shares(ticker):
    t = yf.Ticker(ticker)
    try:
        mc = t.get_valuation_measures().loc["Market Cap"]
    except Exception:
        return None

    mc = mc.drop("Current", errors="ignore")    # Remove undated 'current' column
    mc.index = pd.to_datetime(mc.index)
    mc = mc.dropna().sort_index()
    if mc.empty:
        return None

    # Quarter-ends might predate our price window, so we pull this ticker's own history
    try:
        px = t.history(start=mc.index.min(), end=None, auto_adjust=False)["Close"]
    except Exception:
        return None
    
    if px.empty:
        return None

    if px.index.tz is not None:
        px.index = px.index.tz_localize(None)
    px.index = px.index.normalize()

    px = px.reindex(px.index.union(mc.index)).ffill().reindex(mc.index)  # Close on/before each quarter-end
    return (mc / px).dropna()                   # Market cap / price = shares


# Download shares outstanding, aligned to the price window
def fetch_shares(tickers, index):
    # get_shares_full only returns points on filing dates, so we start early enough
    # that every ticker has at least one observation before the price history begins
    start = (index.min() - pd.Timedelta(days=SHARES_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    def one(ticker):
        try:
            s = yf.Ticker(ticker).get_shares_full(start=start, end=None)
        except Exception:
            return ticker, None                
        
        if s is None or len(s) == 0:
            return ticker, None                 # No filings in the window
        
        if s.index.tz is not None:
            s.index = s.index.tz_localize(None)  # Drop tz

        s.index = s.index.normalize()           # Snap to midnight so dates compare equal

        return ticker, s[~s.index.duplicated(keep="last")].sort_index()  # One row per date, latest wins

    with ThreadPoolExecutor(max_workers=16) as ex:
        series = dict(ex.map(one, tickers))     # 503 separate calls, run in parallel

    # A ticker is short if it has no filings at all, or none before our period starts
    gaps = [t for t, s in series.items() if s is None or s.index.min() > index.min()]

    def patch(ticker):
        return ticker, implied_shares(ticker)

    with ThreadPoolExecutor(max_workers=16) as ex:
        derived = dict(ex.map(patch, gaps))

    for ticker, extra in derived.items():
        if extra is None:
            continue

        filed = series.get(ticker)
        # Real filings win, derived values only fill where filings are absent
        series[ticker] = extra if filed is None else filed.combine_first(extra)

    df = pd.DataFrame({t: s for t, s in series.items() if s is not None})  # Union of all filing dates
    return (
        df.reindex(df.index.union(index))       # Merge any missing dates from our period as empty rows
        .ffill()                                # Each filed value holds until the next filing
        .reindex(index)                         # Keep only our period
    )


stocks = fetch_constituents()
tickers = stocks["Ticker"].tolist()
print(f"Fetched {len(stocks)} constituents")
print(stocks.head())

prices = fetch_prices(tickers)
print(prices.head())
aapl = prices["AAPL"]
print(f"Period: {aapl.index.min().date()} to {aapl.index.max().date()}")

shares = fetch_shares(tickers, aapl.index)
print(f"\nShares outstanding for {shares.shape[1]}/{len(tickers)} tickers")

missing = sorted(set(tickers) - set(shares.columns))
if missing:
    print(f"No shares data for: {missing}")

print(shares.iloc[:3, :4])


nan_cells = int(shares.isna().sum().sum())
nan_cols = shares.columns[shares.isna().any()].tolist()   # any() defaults to axis=0, so per column
nan_rows = int(shares.isna().any(axis=1).sum())           # axis=1 collapses across columns, so per row

if nan_cells == 0:
    print(f"No NaNs: all {shares.shape[0]} x {shares.shape[1]} cells filled")
else:
    print(f"{nan_cells} NaN cells across {nan_rows} rows, in: {nan_cols}")
    print(shares.loc[shares.isna().any(axis=1), nan_cols])  # Only the rows and columns at fault
