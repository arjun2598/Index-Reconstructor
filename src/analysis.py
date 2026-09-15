import pandas as pd
from data import build


# Market value of every company on every day
def market_caps(closes, shares):
    return closes * shares

# Each company's share of total index market value
def weights(caps):
    return caps.div(caps.sum(axis=1), axis=0)   # axis=1 totals each row, axis=0 divides row-wise


# Weighted average of constituent returns, using the prior day's weights
def index_returns(closes, w):
    stock_returns = closes.pct_change()
    lagged = w.shift(1)                         # Yesterday's weights earn today's returns
    return (lagged * stock_returns).sum(axis=1, min_count=1)


# Turn the return series into an index level, starting at `base`
def index_level(returns, base=100.0):
    return base * (1 + returns.fillna(0)).cumprod()


# Rebase a series so it starts at `base`, making two levels comparable
def rebase(series, base=100.0):
    return series / series.iloc[0] * base


# Line up our reconstruction against the published index
def compare(level, benchmark):
    return pd.DataFrame({
        "reconstructed": level,
        "published": rebase(benchmark, level.iloc[0]),   # Same starting point, so only the paths differ
        "our_return": level.pct_change() * 100,
        "their_return": benchmark.pct_change() * 100,
    }).assign(diff_bp=lambda d: (d.our_return - d.their_return) * 100)


if __name__ == "__main__":
    _, closes, shares, benchmark = build()

    caps = market_caps(closes, shares)
    w = weights(caps)
    returns = index_returns(closes, w)
    level = index_level(returns)

    print(f"\nTotal market cap: ${caps.iloc[-1].sum() / 1e12:.2f}T")

    print("\nTop 10 weights:")
    print((w.iloc[-1].sort_values(ascending=False).head(10) * 100).round(2))

    print("\nIndex returns:")
    print((returns * 100).round(3).tail())

    print("\nIndex level:")
    print(level.round(2).tail())

    cmp = compare(level, benchmark)
    print("\nVs published (^GSPC):")
    print(cmp.round(3).tail())

    daily = cmp["diff_bp"].dropna()
    total = (level.iloc[-1] / level.iloc[0] - 1) * 100
    published = (benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100
    print(f"\nOver {len(level)} days: ours {total:+.2f}%, published {published:+.2f}%, gap {(total - published) * 100:+.1f} bp")
    print(f"Daily tracking error: mean {daily.mean():+.2f} bp, stdev {daily.std():.2f} bp, worst {daily.abs().max():.1f} bp")
    print(f"Correlation of daily returns: {cmp.our_return.corr(cmp.their_return):.5f}")
