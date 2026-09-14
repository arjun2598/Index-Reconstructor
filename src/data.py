from io import StringIO

import pandas as pd
import requests
import yfinance as yf

INDEX_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
START = "2026-08-01"

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


stocks = fetch_constituents()
tickers = stocks["Ticker"].tolist()
print(f"Fetched {len(stocks)} constituents")
print(stocks.head())

df = fetch_prices(tickers)
print(df.head())
aapl = df["AAPL"]
print(f"Period: {aapl.index.min().date()} to {aapl.index.max().date()}")
