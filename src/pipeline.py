"""Ties the data stages together: download -> clean -> validate.

Run directly to refresh the dataframes.

"""

import sys

from cleaning import build_clean
from download import load_raw
from validation import report, validate


# Load every dataframe, fetching only what is not already cached
def build(refresh=False):
    print("raw:")
    stocks, prices, raw_shares, raw_benchmark, splits = load_raw(refresh)

    # Clean layer is cheap to rebuild, so we always redo it rather than caching a stale version
    print("clean:")
    closes, shares, benchmark, membership = build_clean(stocks, prices, raw_shares, raw_benchmark, splits)
    print(f"  wrote closes {closes.shape}, shares {shares.shape}, benchmark {benchmark.shape}")

    report(*validate(closes, shares, membership))

    return stocks, closes, shares, benchmark, membership


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv       # Force a re-fetch, ignoring whatever is cached
    stocks, closes, shares, benchmark, membership = build(refresh)

    print(f"\n{len(stocks)} constituents | {closes.index.min().date()} to {closes.index.max().date()}")
    print(closes.iloc[:3, :4])
