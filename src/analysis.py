import pandas as pd
from data import build

# yfinance reports the whole company's share count for every share class, so a
# second class would double count the company. We keep one class per company, whose
# total shares priced at that class already give the full market cap.
SECOND_CLASS = ["GOOG", "FOX", "NWS"]


# Market value of every company on every day
def market_caps(closes, shares):
    caps = closes * shares
    return caps.drop(columns=SECOND_CLASS, errors="ignore")

# Each company's share of total index market value
def weights(caps):
    return caps.div(caps.sum(axis=1), axis=0)   # axis=1 totals each row, axis=0 divides row-wise


# Weighted average of constituent returns, using the prior day's weights
def index_returns(closes, w):
    stock_returns = closes.pct_change().reindex(columns=w.columns)   # Match the deduplicated universe
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


# ----- diagnostics -----

# Each stock's contribution to the index return, in basis points
def contributions(closes, w):
    returns = closes.pct_change().reindex(columns=w.columns)
    return w.shift(1) * returns             # Same product index_returns sums, kept per stock

# Where the panel has holes, and which holes silently drop a stock from the index
def coverage(closes, shares):
    dropped = closes.notna() & shares.isna()   # Priced but no share count, so market cap is NaN
    return pd.DataFrame({
        "nan_closes": closes.isna().sum(),
        "nan_shares": shares.isna().sum(),
        "priced_but_dropped": dropped.sum(),
    }).query("nan_closes > 0 or nan_shares > 0").sort_values("priced_but_dropped", ascending=False)

# First day each ticker has a price, for names that start after the window opens
def late_entrants(closes):
    first = closes.apply(lambda c: c.first_valid_index())
    return first[first > closes.index[0]].sort_values()

# Tracking quality split by year, since errors grow the further back we go
def tracking_by_year(ours, theirs):
    diff = (ours - theirs).dropna() * 10000
    compound = lambda s: (1 + s.fillna(0)).prod() - 1
    tbl = pd.DataFrame({
        "ours_%": ours.groupby(ours.index.year).apply(compound) * 100,
        "published_%": theirs.groupby(theirs.index.year).apply(compound) * 100,
        "te_stdev_bp": diff.groupby(diff.index.year).std(),
        "mean_bp": diff.groupby(diff.index.year).mean(),
    })
    return tbl.assign(gap_pp=tbl["ours_%"] - tbl["published_%"])

# Days we diverge most from the published index, and the stocks responsible
def worst_days(closes, w, ours, theirs, n=5, top=3):
    diff = (ours - theirs).dropna() * 10000
    contrib = contributions(closes, w)
    rows = []
    for date in diff.abs().sort_values(ascending=False).head(n).index:
        drivers = contrib.loc[date].dropna().sort_values(key=abs, ascending=False).head(top)
        rows.append({
            "date": date.date(),
            "diff_bp": round(diff[date], 1),
            "drivers": ", ".join(f"{t} {v * 10000:+.1f}bp" for t, v in drivers.items()),
        })
    return pd.DataFrame(rows)

# Days a share count moved, found without any external data
def corporate_action_days(caps, ours, threshold_bp=5):
    aggregate = caps.sum(axis=1).pct_change()   # Moves on issuance, unlike a weighted return
    gap = (ours - aggregate).dropna() * 10000
    return gap[gap.abs() > threshold_bp].sort_values(key=abs, ascending=False)


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

    print("\nTracking by year:")
    print(tracking_by_year(returns, benchmark.pct_change()).round(2))

    print("\nWorst days:")
    print(worst_days(closes, w, returns, benchmark.pct_change()).to_string(index=False))

    gaps = coverage(closes, shares)
    print(f"\nCoverage holes in {len(gaps)} tickers "
          f"({int(gaps.priced_but_dropped.sum())} ticker-days priced but dropped for want of shares):")
    print(gaps.head(8))

    print("\nTickers starting after the window opens:")
    print(late_entrants(closes).head(8).to_string())

    actions = corporate_action_days(caps, returns)
    print(f"\n{len(actions)} days where share counts moved (weighted vs aggregate return, bp):")
    print(actions.head(5).round(1).to_string())
