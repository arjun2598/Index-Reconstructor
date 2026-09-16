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
        earlier = factors.index < row.date      # Days on or after the split are already adjusted
        factors.loc[earlier, row.ticker] *= row.ratio

    return factors


# Yahoo does not switch to post-split counts on the effective date. BKNG's April 2026
# split shows post-split counts from early February, and pre-split ones again in late
# March, so no single boundary is right. Scaling those already-adjusted counts by 25
# gave BKNG a $4tn market cap and 6% of the index.
#
# So after scaling, look near each split for counts that came out a whole split ratio
# too large and divide them back down. The window is narrow so genuine share changes
# elsewhere, which the issuance signal depends on, are untouched.
def repair_double_adjusted(adjusted, splits, window=150, tolerance=0.2):
    for row in splits.itertuples():
        if row.ticker not in adjusted.columns or row.ratio <= 1:
            continue

        column = adjusted[row.ticker]
        after = column[(column.index >= row.date)
                       & (column.index < row.date + pd.Timedelta(days=30))].dropna()
        if after.empty:
            continue

        settled = after.median()                # What the count really is once the split lands
        near = (column.index > row.date - pd.Timedelta(days=window)) & (column.index < row.date)
        too_big = near & (column / settled > row.ratio * (1 - tolerance))
        adjusted.loc[too_big, row.ticker] = column[too_big] / row.ratio

    return adjusted


# Restate share counts onto the same basis as the prices
def adjust_shares(shares, splits):
    scaled = shares * split_factors(splits, shares.index, shares.columns)
    return repair_double_adjusted(scaled, splits)


# Reduce the benchmark to a single Close series on our trading calendar
def clean_benchmark(raw_benchmark, index):
    return raw_benchmark["Close"].reindex(index)


# Point-in-time membership, walked backwards from today's list through the change log.
# A change on date d means that before d the index held the removed name and not the
# added one, so stepping back over it undoes both sides.
def membership_timeline(current, changes):
    members = set(current)
    timeline = []                               # (valid_from, members) newest first

    for date, group in sorted(changes.groupby("date"), reverse=True):
        timeline.append((date, frozenset(members)))
        for row in group.itertuples():
            if isinstance(row.added, str):
                members.discard(row.added)      # Was not a member before this date
                
            if isinstance(row.removed, str):
                members.add(row.removed)        # Still a member before this date

    timeline.append((pd.Timestamp.min, frozenset(members)))
    return timeline                             # Last entry covers everything earlier


# Turn the timeline into a dates x tickers boolean frame
def build_membership(stocks, changes, index, columns):
    timeline = membership_timeline(stocks["Ticker"], changes)
    member = pd.DataFrame(False, index=index, columns=columns)

    # Oldest first, so each later entry overwrites the tail it applies to
    for valid_from, members in reversed(timeline):
        rows = member.index >= valid_from
        if not rows.any():
            continue
        held = [t for t in members if t in member.columns]
        member.loc[rows, held] = True
        member.loc[rows, [c for c in member.columns if c not in members]] = False

    return member


# Build every clean dataframe and write it to data/clean
def build_clean(stocks, changes, prices, raw_shares, raw_benchmark, splits):
    index = prices.index                    # The trading calendar everything else aligns to

    closes = clean_closes(prices)
    shares = adjust_shares(clean_shares(raw_shares, index), splits)
    benchmark = clean_benchmark(raw_benchmark, index)
    membership = build_membership(stocks, changes, index, closes.columns)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    closes.to_parquet(CLEAN_DIR / "closes.parquet")
    shares.to_parquet(CLEAN_DIR / "shares.parquet")
    benchmark.to_frame().to_parquet(CLEAN_DIR / "benchmark.parquet")  # parquet stores tables, not series
    membership.to_parquet(CLEAN_DIR / "membership.parquet")

    return closes, shares, benchmark, membership
