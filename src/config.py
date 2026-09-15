# Every tunable constant and path

from pathlib import Path

INDEX_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies" # Source to fetch constituent stock information
BENCHMARK = "^GSPC"         # The published price-return index, no dividends, matching auto_adjust=False

START = "2022-01-01" # Start of time period
SHARES_LOOKBACK_DAYS = 400  # Filings are usually quarterly, so look back far enough to catch one before START

# yfinance reports the whole company's share count against every share class, so a
# second class would double count the company. We keep one class per company, whose
# total shares priced at that class already give the full market cap.
SECOND_CLASS = ["GOOG", "FOX", "NWS"]

MIN_UNIVERSE = 500          # The index holds 500+ names, fewer means we silently dropped some
TOP_N = 50                  # Largest names, where a silent drop does the most damage

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"      # Exact data from yfinance, never edited
CLEAN_DIR = DATA_DIR / "clean"  # Derived dataframes, rebuilt from raw 

MAX_WORKERS = 16            # yfinance has no bulk endpoint for shares, so we parallelise per ticker
