"""Measurements of where the reconstruction goes wrong.

Nothing here changes the index. These functions answer why our series and the
published one disagree.
"""

import pandas as pd

# Each stock's contribution to the index return on each day
def contributions(closes, w):
    returns = closes.pct_change().reindex(columns=w.columns)
    return w.shift(1) * returns             # Same product index_returns sums, kept per stock


# Where the dataframe has holes, counted only while a company is an index member
def coverage(closes, shares, membership):
    return pd.DataFrame({
        "no_price": (membership & closes.isna()).sum(),
        "no_shares": (membership & shares.isna()).sum(),
        "priced_but_dropped": (membership & closes.notna() & shares.isna()).sum(),
    }).query("no_price > 0 or no_shares > 0").sort_values("priced_but_dropped", ascending=False)


# Tracking quality split by year, since errors grow the further back we go
def tracking_by_year(ours, theirs):
    diff = (ours - theirs).dropna() * 10000 # 1 bp = 0.01% = 0.0001
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
