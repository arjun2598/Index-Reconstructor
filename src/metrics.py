# Index construction: market caps, weights, returns, level

import pandas as pd

from config import SECOND_CLASS

# Market value of every company on every day
def market_caps(closes, shares):
    caps = closes * shares
    return caps.drop(columns=SECOND_CLASS, errors="ignore")  # One share class per company


# Each company's share of total index market value
def weights(caps):
    return caps.div(caps.sum(axis=1), axis=0)   # axis=1 totals each row, axis=0 divides row-wise


# Weighted average of constituent returns, using the prior day's weights
def index_returns(closes, w):
    stock_returns = closes.pct_change().reindex(columns=w.columns)  # Match the deduplicated universe
    lagged = w.shift(1)                         # Yesterday's weights earn today's returns - Prevent lookahead bias
    return (lagged * stock_returns).sum(axis=1, min_count=1)


# Turn the return series into an index level, starting at `base`
def index_level(returns, base=100.0):
    return base * (1 + returns.fillna(0)).cumprod()


# Rebase a series so it starts at `base`, making two levels comparable
def rebase(series, base=100.0):
    return series / series.iloc[0] * base


# Build every dataframe the reconstruction needs, in order
def reconstruct(closes, shares):
    caps = market_caps(closes, shares)
    w = weights(caps)
    returns = index_returns(closes, w)
    return caps, w, returns, index_level(returns)


# Line up our reconstruction against the published index
def compare(level, benchmark):
    return pd.DataFrame({
        "reconstructed": level,
        "published": rebase(benchmark, level.iloc[0]),   # Same starting point, so only the paths differ
        "our_return": level.pct_change() * 100,
        "their_return": benchmark.pct_change() * 100,
    }).assign(diff_bp=lambda d: (d.our_return - d.their_return) * 100)


# Headline tracking numbers over the whole window
def tracking_summary(level, benchmark):
    diff = compare(level, benchmark)["diff_bp"].dropna()
    ours = (level.iloc[-1] / level.iloc[0] - 1) * 100
    published = (benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100
    return {
        "days": len(level),
        "ours_%": ours,
        "published_%": published,
        "gap_bp": (ours - published) * 100,
        "te_mean_bp": diff.mean(),
        "te_stdev_bp": diff.std(),
        "te_worst_bp": diff.abs().max(),
        "correlation": level.pct_change().corr(benchmark.pct_change()),
    }
