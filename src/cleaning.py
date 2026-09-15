"""Pure transforms from raw downloads into aligned dataframes.

Every output is indexed by trading date with one column per ticker, so the dataframes
multiply together elementwise.
"""

import pandas as pd

from config import CLEAN_DIR


# Flatten the (ticker, field) columns down to one close price per ticker
def clean_closes(prices):
    return prices.xs("Close", axis=1, level=1).sort_index()


# Spread sparse filing dates across every trading day in the window
def clean_shares(raw_shares, index):
    return (
        raw_shares.reindex(raw_shares.index.union(index))  # Add the price dates as empty rows
        .ffill()                                           # Each filed value holds until the next filing
        .reindex(index)                                    # Keep only the price calendar
    )


# Prices come back split-adjusted all the way down their history, while share counts
# are as filed. Before a split the two disagree by its ratio, so we put shares on the
# same post-split basis by scaling each day up by every split that came after it.
def split_factors(splits, index, columns):
    factors = pd.DataFrame(1.0, index=index, columns=columns)

    for row in splits.itertuples():
        if row.ticker not in factors.columns:
            continue
        earlier = factors.index < row.date      # Days on or after the split are already on the new basis
        factors.loc[earlier, row.ticker] *= row.ratio

    return factors


# Restate share counts onto the same basis as the prices
def adjust_shares(shares, splits):
    return shares * split_factors(splits, shares.index, shares.columns)


# Reduce the benchmark to a single Close series on our trading calendar
def clean_benchmark(raw_benchmark, index):
    return raw_benchmark["Close"].reindex(index)


# Build every clean dataframe and write it to data/clean
def build_clean(prices, raw_shares, raw_benchmark, splits):
    index = prices.index                    # The trading calendar everything else aligns to

    closes = clean_closes(prices)
    shares = adjust_shares(clean_shares(raw_shares, index), splits)
    benchmark = clean_benchmark(raw_benchmark, index)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    closes.to_parquet(CLEAN_DIR / "closes.parquet")
    shares.to_parquet(CLEAN_DIR / "shares.parquet")
    benchmark.to_frame().to_parquet(CLEAN_DIR / "benchmark.parquet")  # parquet stores tables, not series

    return closes, shares, benchmark
