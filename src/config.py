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

# Yahoo keeps price history under a renamed ticker but files share counts only from the
# rename date, so we fetch the old symbol too and use it for the earlier period.
RENAMES = {
    "META": "FB",       # Meta, was Facebook
    "ELV": "ANTM",      # Elevance Health, was Anthem
    "BALL": "BLL",      # Ball Corporation
    "WBD": "DISCA",     # Warner Bros. Discovery, was Discovery
    "WTW": "WLTW",      # Willis Towers Watson
    "RVTY": "PKI",      # Revvity, was PerkinElmer
    "EG": "RE",         # Everest Group, was Everest Re
    "CPAY": "FLT",      # Corpay, was FLEETCOR
    "XYZ": "SQ",        # Block, was Square
    "PSKY": "PARA",     # Paramount Skydance, was Paramount Global
    "EXE": "CHK",       # Expand Energy, was Chesapeake
    "MRSH": "MMC",      # Marsh McLennan
    "VMRK": "AVB",      # Vivmark Residential, was AvalonBay
    "TKO": "WWE",       # TKO Group, was WWE
    "SW": "WRK",        # Smurfit Westrock, was WestRock
}

MIN_UNIVERSE = 500          # The index holds 500+ names, fewer means we silently dropped some
TOP_N = 50                  # Largest names, where a silent drop does the most damage
SHARE_JUMP_RATIO = 1.5      # A real issuance rarely moves shares this far in a day, so it flags split-boundary noise

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"      # Exact data from yfinance, never edited
CLEAN_DIR = DATA_DIR / "clean"  # Derived dataframes, rebuilt from raw 

MAX_WORKERS = 16            # yfinance has no bulk endpoint for shares, so we parallelise per ticker
